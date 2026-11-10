"""Part 3: cross-system funnel conversion analysis with Spark.

Business question
-----------------
Which device type and acquisition channel (referrer) produce the strongest
journey from product browsing to cart activity and a recognised purchase?

Logical data sources
--------------------
* HBase ``user_sessions``: browsing sessions, product views, cart contents,
  device type and referrer.  For this portable project we read the same JSON
  subset that was loaded into HBase.
* MongoDB ``transactions`` and ``products``: recognised transaction items,
  revenue and category information.  For this portable project we read the
  normalised Parquet exports built from those MongoDB-style documents.

Spark joins the two sources at session_id, aggregates the journey stages, and
calculates conversion rates.  No pre-computed answers are read.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

from pyspark.sql import SparkSession, functions as F


PROJECT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
HBASE_SAMPLE_FILE = PROJECT_DIR / "data" / "hbase" / "sessions_subset_10000.json"
ANALYTICS_DIR = PROJECT_DIR / "data" / "analytics"
SUMMARY_FILE = PROJECT_DIR / "spark_integrated_funnel_summary.json"
RECOGNIZED_STATUSES = ["completed", "shipped", "delivered"]


def local_path(path: Path) -> str:
    """Return an absolute Windows-safe path for Spark's local file source."""
    return str(path.resolve())


def save_csv(dataframe, name: str) -> str:
    """Write a human-readable one-part CSV result for the report."""
    output = ANALYTICS_DIR / name
    dataframe.coalesce(1).write.mode("overwrite").option("header", "true").csv(local_path(output))
    return str(output)


def main() -> None:
    required = [PROCESSED_DIR, HBASE_SAMPLE_FILE]
    missing = [str(item) for item in required if not item.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing input: " + ", ".join(missing)
            + ". Run spark_batch_recommendations.py and prepare_hbase_subset.py first."
        )

    started = perf_counter()
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName("EcommerceIntegratedFunnel")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("Loading HBase-session and MongoDB-transaction representations ...")
    # HBase source representation: exactly the reproducible JSON sample loaded
    # to HBase user_sessions in Part 1.
    raw_sessions = spark.read.option("multiline", "true").json(local_path(HBASE_SAMPLE_FILE))
    hbase_sessions = raw_sessions.select(
        F.col("session_id"),
        F.col("user_id"),
        F.col("device_profile.type").alias("device_type"),
        F.coalesce(F.col("referrer"), F.lit("unknown")).alias("referrer"),
        F.size(F.coalesce(F.col("page_views"), F.array())).alias("page_views"),
        # Spark infers cart_contents from JSON as a large STRUCT because each
        # product ID becomes a possible field. conversion_status is the
        # generator's stable cart indicator: browsed=no cart; abandoned or
        # converted=one or more products were placed in the cart.
        F.when(F.col("conversion_status").isin("abandoned", "converted"), F.lit(1))
        .otherwise(F.lit(0)).alias("has_cart"),
        F.col("conversion_status"),
    )

    # MongoDB source representation: cleaned transaction item documents.
    transaction_items = spark.read.parquet(local_path(PROCESSED_DIR / "transaction_items"))
    products = spark.read.parquet(local_path(PROCESSED_DIR / "products"))
    statuses_sql = ", ".join(f"'{status}'" for status in RECOGNIZED_STATUSES)

    hbase_sessions.createOrReplaceTempView("hbase_sessions")
    transaction_items.createOrReplaceTempView("mongo_transaction_items")
    products.createOrReplaceTempView("mongo_products")

    # HBase stages remain the denominator. The MongoDB sales CTE is restricted
    # to those exact session IDs, avoiding an invalid comparison between a
    # session sample and all transactions in the full data set.
    funnel_sql = f"""
    WITH mongo_sales AS (
        SELECT
            t.session_id,
            COUNT(DISTINCT t.transaction_id) AS recognized_orders,
            SUM(t.quantity) AS recognized_units,
            ROUND(SUM(t.item_subtotal_usd), 2) AS recognized_revenue_usd,
            COUNT(DISTINCT COALESCE(t.category_id, p.category_id)) AS categories_purchased
        FROM mongo_transaction_items t
        INNER JOIN (SELECT DISTINCT session_id FROM hbase_sessions) h
            ON h.session_id = t.session_id
        LEFT JOIN mongo_products p ON p.product_id = t.product_id
        WHERE t.status IN ({statuses_sql})
        GROUP BY t.session_id
    )
    SELECT
        h.device_type,
        h.referrer,
        COUNT(*) AS browsing_sessions,
        SUM(CASE WHEN h.page_views > 0 THEN 1 ELSE 0 END) AS sessions_with_views,
        SUM(CASE WHEN h.has_cart = 1 THEN 1 ELSE 0 END) AS cart_sessions,
        SUM(CASE WHEN s.recognized_orders IS NOT NULL THEN 1 ELSE 0 END) AS purchasing_sessions,
        COALESCE(SUM(s.recognized_orders), 0) AS recognized_orders,
        COALESCE(SUM(s.recognized_units), 0) AS recognized_units,
        ROUND(COALESCE(SUM(s.recognized_revenue_usd), 0), 2) AS recognized_revenue_usd,
        ROUND(100.0 * SUM(CASE WHEN h.has_cart = 1 THEN 1 ELSE 0 END) /
              NULLIF(COUNT(*), 0), 2) AS cart_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN s.recognized_orders IS NOT NULL THEN 1 ELSE 0 END) /
              NULLIF(COUNT(*), 0), 2) AS purchase_conversion_pct,
        ROUND(COALESCE(SUM(s.recognized_revenue_usd), 0) /
              NULLIF(SUM(CASE WHEN s.recognized_orders IS NOT NULL THEN 1 ELSE 0 END), 0), 2)
              AS revenue_per_purchasing_session_usd
    FROM hbase_sessions h
    LEFT JOIN mongo_sales s ON s.session_id = h.session_id
    GROUP BY h.device_type, h.referrer
    ORDER BY purchase_conversion_pct DESC, recognized_revenue_usd DESC, browsing_sessions DESC
    """

    print("Joining the sources by session_id and calculating funnel stages ...")
    funnel = spark.sql(funnel_sql)
    result_csv = save_csv(funnel, "integrated_funnel_by_device_referrer_csv")
    result_rows = [row.asDict() for row in funnel.collect()]

    # A compact overall check makes the denominator and the number of matched
    # purchases transparent for the report.
    overall = spark.sql(
        f"""
        SELECT
            (SELECT COUNT(*) FROM hbase_sessions) AS hbase_sample_sessions,
            (SELECT COUNT(DISTINCT session_id) FROM mongo_transaction_items
             WHERE status IN ({statuses_sql})
               AND session_id IN (SELECT session_id FROM hbase_sessions))
             AS matched_purchase_sessions
        """
    ).first().asDict()

    summary = {
        "business_question": "Which device/referrer journeys convert from browsing to recognised purchase?",
        "logical_sources": {
            "hbase": "user_sessions: browsing activity, cart content, device type and referrer",
            "mongodb": "transactions and products: recognised orders, units, revenue and categories",
        },
        "join_key": "session_id",
        "sql": funnel_sql.strip(),
        "overall_check": overall,
        "rows": result_rows,
        "csv_output": result_csv,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\nIntegrated funnel: HBase browsing -> cart -> MongoDB recognised purchase")
    funnel.show(30, truncate=28)
    print("\nCohort check:")
    print(f"- HBase sampled sessions: {overall['hbase_sample_sessions']:,}")
    print(f"- Matched recognised purchase sessions: {overall['matched_purchase_sessions']:,}")
    print(f"\nSaved results: {SUMMARY_FILE.name}")
    print(f"Saved table: {result_csv}")
    print(f"Total seconds: {summary['elapsed_seconds']}")
    spark.stop()


if __name__ == "__main__":
    main()
