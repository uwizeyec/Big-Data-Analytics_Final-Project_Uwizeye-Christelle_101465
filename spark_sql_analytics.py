"""Part 2 Spark SQL analytics over MongoDB-like and HBase-like DataFrames."""

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
SUMMARY_FILE = PROJECT_DIR / "spark_sql_summary.json"
RECOGNIZED_STATUSES = ["completed", "shipped", "delivered"]


def local_path(path: Path) -> str:
    return str(path.resolve())


def save_csv(dataframe, folder_name: str) -> str:
    path = ANALYTICS_DIR / folder_name
    dataframe.coalesce(1).write.mode("overwrite").option("header", "true").csv(local_path(path))
    return str(path)


def main() -> None:
    missing = [path for path in (PROCESSED_DIR, HBASE_SAMPLE_FILE) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing input(s): " + ", ".join(str(path) for path in missing)
            + ". Run spark_batch_recommendations.py and prepare_hbase_subset.py first."
        )

    started = perf_counter()
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName("EcommerceSparkSQLAnalytics")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("Loading normalized MongoDB-like DataFrames and HBase session sample ...")
    users = spark.read.parquet(local_path(PROCESSED_DIR / "users"))
    products = spark.read.parquet(local_path(PROCESSED_DIR / "products"))
    transaction_items = spark.read.parquet(local_path(PROCESSED_DIR / "transaction_items"))

    # This JSON sample is the same data loaded to HBase's user_sessions table.
    raw_hbase_sessions = spark.read.option("multiline", "true").json(local_path(HBASE_SAMPLE_FILE))
    hbase_sessions = raw_hbase_sessions.select(
        F.col("session_id"),
        F.col("user_id"),
        F.to_timestamp("start_time").alias("start_timestamp"),
        F.col("duration_seconds").cast("integer").alias("duration_seconds"),
        F.col("conversion_status"),
        F.col("device_profile.type").alias("device_type"),
        F.col("device_profile.os").alias("device_os"),
        F.size("page_views").alias("page_view_count"),
        F.col("page_views"),
    )
    hbase_page_views = hbase_sessions.select(
        "session_id",
        "user_id",
        F.explode_outer("page_views").alias("page_view"),
    ).select(
        "session_id",
        "user_id",
        F.col("page_view.page_type").alias("page_type"),
        F.trim("page_view.product_id").alias("product_id"),
        F.trim("page_view.category_id").alias("category_id"),
        F.col("page_view.view_duration").cast("integer").alias("view_duration_seconds"),
    )

    users.createOrReplaceTempView("mongo_users")
    products.createOrReplaceTempView("mongo_products")
    transaction_items.createOrReplaceTempView("mongo_transaction_items")
    hbase_sessions.createOrReplaceTempView("hbase_user_sessions")
    hbase_page_views.createOrReplaceTempView("hbase_page_views")

    statuses_sql = ", ".join(f"'{status}'" for status in RECOGNIZED_STATUSES)

    # Query 1: customer engagement and recognized value by profile state.
    customer_engagement_sql = f"""
    WITH hbase_engagement AS (
        SELECT
            user_id,
            COUNT(*) AS sampled_sessions,
            SUM(page_view_count) AS sampled_page_views,
            ROUND(AVG(duration_seconds), 1) AS average_session_seconds,
            SUM(CASE WHEN conversion_status = 'converted' THEN 1 ELSE 0 END) AS converted_sessions
        FROM hbase_user_sessions
        GROUP BY user_id
    ),
    mongo_purchase_value AS (
        SELECT
            user_id,
            COUNT(DISTINCT transaction_id) AS recognized_orders,
            ROUND(SUM(item_subtotal_usd), 2) AS recognized_item_revenue_usd
        FROM mongo_transaction_items
        WHERE status IN ({statuses_sql})
        GROUP BY user_id
    )
    SELECT
        u.state,
        CASE
            WHEN COALESCE(p.recognized_item_revenue_usd, 0) >= 1500 THEN 'high_value'
            WHEN COALESCE(p.recognized_item_revenue_usd, 0) >= 600 THEN 'regular'
            ELSE 'occasional_or_no_purchase'
        END AS value_segment,
        COUNT(DISTINCT u.user_id) AS users,
        COALESCE(SUM(e.sampled_sessions), 0) AS sampled_sessions,
        COALESCE(SUM(e.sampled_page_views), 0) AS sampled_page_views,
        ROUND(AVG(e.average_session_seconds), 1) AS average_session_seconds,
        COALESCE(SUM(e.converted_sessions), 0) AS converted_sessions,
        COALESCE(SUM(p.recognized_orders), 0) AS recognized_orders,
        ROUND(COALESCE(SUM(p.recognized_item_revenue_usd), 0), 2) AS recognized_item_revenue_usd
    FROM mongo_users u
    LEFT JOIN hbase_engagement e ON u.user_id = e.user_id
    LEFT JOIN mongo_purchase_value p ON u.user_id = p.user_id
    GROUP BY u.state,
             CASE
                WHEN COALESCE(p.recognized_item_revenue_usd, 0) >= 1500 THEN 'high_value'
                WHEN COALESCE(p.recognized_item_revenue_usd, 0) >= 600 THEN 'regular'
                ELSE 'occasional_or_no_purchase'
             END
    ORDER BY recognized_item_revenue_usd DESC, users DESC
    LIMIT 20
    """

    # Query 2: cross-store category funnel from HBase product-detail views to
    # MongoDB transaction-line purchases and item revenue.
    category_funnel_sql = f"""
    WITH hbase_views AS (
        SELECT
            COALESCE(v.category_id, p.category_id) AS category_id,
            COUNT(*) AS product_detail_views,
            COUNT(DISTINCT v.session_id) AS viewer_sessions
        FROM hbase_page_views v
        LEFT JOIN mongo_products p ON v.product_id = p.product_id
        WHERE v.page_type = 'product_detail'
          AND COALESCE(v.category_id, p.category_id) IS NOT NULL
        GROUP BY COALESCE(v.category_id, p.category_id)
    ),
    mongo_sales AS (
        SELECT
            t.category_id,
            COUNT(DISTINCT t.transaction_id) AS purchasing_transactions,
            SUM(t.quantity) AS units_purchased,
            ROUND(SUM(t.item_subtotal_usd), 2) AS item_revenue_usd
        FROM mongo_transaction_items t
        INNER JOIN (
            SELECT DISTINCT session_id
            FROM hbase_user_sessions
        ) h ON t.session_id = h.session_id
        WHERE t.status IN ({statuses_sql})
        GROUP BY t.category_id
    )
    SELECT
        COALESCE(v.category_id, s.category_id) AS category_id,
        COALESCE(v.product_detail_views, 0) AS product_detail_views,
        COALESCE(v.viewer_sessions, 0) AS viewer_sessions,
        COALESCE(s.purchasing_transactions, 0) AS purchasing_transactions,
        COALESCE(s.units_purchased, 0) AS units_purchased,
        COALESCE(s.item_revenue_usd, 0.0) AS item_revenue_usd,
        ROUND(
            100.0 * COALESCE(s.purchasing_transactions, 0) /
            NULLIF(COALESCE(v.product_detail_views, 0), 0),
            2
        ) AS purchases_per_100_product_views
    FROM hbase_views v
    FULL OUTER JOIN mongo_sales s ON v.category_id = s.category_id
    ORDER BY item_revenue_usd DESC, product_detail_views DESC
    """

    print("Running Spark SQL Query 1: customer engagement and purchase value ...")
    engagement = spark.sql(customer_engagement_sql)
    print("Running Spark SQL Query 2: category view-to-purchase funnel ...")
    category_funnel = spark.sql(category_funnel_sql)

    engagement_output = save_csv(engagement, "spark_sql_customer_engagement_csv")
    funnel_output = save_csv(category_funnel, "spark_sql_category_funnel_csv")
    engagement_rows = [row.asDict() for row in engagement.collect()]
    funnel_rows = [row.asDict() for row in category_funnel.collect()]

    summary = {
        "query_1": {
            "name": "Customer engagement and recognized purchase value by state",
            "sources": ["mongo_users", "mongo_transaction_items", "hbase_user_sessions"],
            "sql": customer_engagement_sql.strip(),
            "rows": engagement_rows,
            "csv_output": engagement_output,
        },
        "query_2": {
            "name": "Category funnel from HBase product-detail views to MongoDB purchases",
            "sources": ["hbase_page_views", "mongo_products", "mongo_transaction_items"],
            "sql": category_funnel_sql.strip(),
            "rows": funnel_rows,
            "csv_output": funnel_output,
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\nQuery 1 — customer engagement and recognized purchase value")
    engagement.show(20, truncate=32)
    print("\nQuery 2 — category view-to-purchase funnel")
    category_funnel.show(25, truncate=32)
    print(f"\nSaved SQL results: {SUMMARY_FILE.name}")
    print(f"Total seconds: {summary['elapsed_seconds']}")
    spark.stop()


if __name__ == "__main__":
    main()
