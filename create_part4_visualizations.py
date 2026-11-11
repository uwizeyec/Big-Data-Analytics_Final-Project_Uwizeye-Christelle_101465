"""Create static, report-ready charts for Part 4 of the final project.

The chart inputs are the cleaned Parquet datasets created by the Part 2 Spark
job and the same reproducible session subset loaded into HBase in Part 1.
All monetary values are recognised item revenue in USD.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

import matplotlib

matplotlib.use("Agg")  # Write image files without opening a GUI window.
import matplotlib.pyplot as plt
from pyspark.sql import SparkSession, functions as F


PROJECT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
HBASE_SAMPLE_FILE = PROJECT_DIR / "data" / "hbase" / "sessions_subset_10000.json"
FIGURE_DIR = PROJECT_DIR / "data" / "visualizations"
SUMMARY_FILE = PROJECT_DIR / "part4_visualization_summary.json"
RECOGNIZED_STATUSES = ["completed", "shipped", "delivered"]


def local_path(path: Path) -> str:
    return str(path.resolve())


def save_figure(filename: str) -> str:
    """Apply a consistent report style and save a high-resolution PNG."""
    output = FIGURE_DIR / filename
    plt.tight_layout()
    plt.savefig(output, dpi=220, bbox_inches="tight")
    plt.close()
    return str(output)


def main() -> None:
    required = [PROCESSED_DIR, HBASE_SAMPLE_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing input(s): " + ", ".join(missing))

    started = perf_counter()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    spark = (
        SparkSession.builder.appName("EcommercePart4Visualizations")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("Loading cleaned transaction data and the HBase session sample ...")
    transactions = spark.read.parquet(local_path(PROCESSED_DIR / "transaction_items"))
    sessions_raw = spark.read.option("multiline", "true").json(local_path(HBASE_SAMPLE_FILE))
    sessions = sessions_raw.select(
        "session_id",
        F.col("conversion_status"),
        F.col("device_profile.type").alias("device_type"),
    )
    recognized = transactions.filter(F.col("status").isin(RECOGNIZED_STATUSES))
    generated: list[str] = []

    # Chart 1: recognised revenue and orders over time.
    monthly = (
        recognized.groupBy(F.date_format("transaction_timestamp", "yyyy-MM").alias("month"))
        .agg(
            F.round(F.sum("item_subtotal_usd"), 2).alias("revenue_usd"),
            F.countDistinct("transaction_id").alias("orders"),
        )
        .orderBy("month")
        .collect()
    )
    months = [row["month"] for row in monthly]
    revenue = [float(row["revenue_usd"]) for row in monthly]
    orders = [int(row["orders"]) for row in monthly]
    fig, revenue_axis = plt.subplots(figsize=(10, 5.2))
    revenue_axis.plot(months, revenue, marker="o", linewidth=2.5, color="#2166ac", label="Revenue (USD)")
    revenue_axis.set_ylabel("Recognised item revenue (USD)", color="#2166ac")
    revenue_axis.tick_params(axis="y", labelcolor="#2166ac")
    revenue_axis.set_title("Monthly recognised sales performance")
    revenue_axis.set_xlabel("Transaction month")
    revenue_axis.grid(axis="y", alpha=0.25)
    orders_axis = revenue_axis.twinx()
    orders_axis.bar(months, orders, alpha=0.28, color="#f4a261", label="Orders")
    orders_axis.set_ylabel("Recognised orders", color="#b35c00")
    orders_axis.tick_params(axis="y", labelcolor="#b35c00")
    fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.91))
    generated.append(save_figure("01_monthly_sales_performance.png"))

    # Chart 2: the ten categories contributing most recognised revenue.
    categories = (
        recognized.groupBy("category_id")
        .agg(F.round(F.sum("item_subtotal_usd"), 2).alias("revenue_usd"))
        .orderBy(F.desc("revenue_usd"))
        .limit(10)
        .collect()
    )
    category_ids = [row["category_id"] for row in categories][::-1]
    category_revenue = [float(row["revenue_usd"]) for row in categories][::-1]
    plt.figure(figsize=(9.5, 5.4))
    plt.barh(category_ids, category_revenue, color="#2a9d8f")
    plt.title("Top 10 product categories by recognised item revenue")
    plt.xlabel("Recognised item revenue (USD)")
    plt.ylabel("Category")
    plt.grid(axis="x", alpha=0.25)
    generated.append(save_figure("02_top_category_revenue.png"))

    # Chart 3: customers segmented by recognised purchase frequency.
    user_orders = recognized.groupBy("user_id").agg(F.countDistinct("transaction_id").alias("orders"))
    segments = (
        user_orders.select(
            F.when(F.col("orders") == 1, "one order")
            .when(F.col("orders").between(2, 4), "2-4 orders")
            .when(F.col("orders").between(5, 9), "5-9 orders")
            .otherwise("10+ orders")
            .alias("segment")
        )
        .groupBy("segment")
        .count()
        .collect()
    )
    segment_order = ["one order", "2-4 orders", "5-9 orders", "10+ orders"]
    segment_counts = {row["segment"]: row["count"] for row in segments}
    values = [segment_counts.get(segment, 0) for segment in segment_order]
    plt.figure(figsize=(8.8, 5.2))
    bars = plt.bar(segment_order, values, color=["#a8dadc", "#457b9d", "#1d3557", "#e63946"])
    plt.title("Customer segmentation by recognised purchase frequency")
    plt.xlabel("Recognised-order segment")
    plt.ylabel("Users")
    plt.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value, f"{value:,}", ha="center", va="bottom")
    generated.append(save_figure("03_customer_purchase_segments.png"))

    # Chart 4: joined funnel stage counts. A converted/abandoned session has
    # cart activity; joined recognised sale confirms a purchase event.
    sale_sessions = recognized.select("session_id").distinct()
    stage_counts = (
        sessions.join(sale_sessions.withColumn("has_purchase", F.lit(1)), "session_id", "left")
        .agg(
            F.count("session_id").alias("browsing"),
            F.sum(F.when(F.col("conversion_status").isin("abandoned", "converted"), 1).otherwise(0)).alias("cart"),
            F.sum(F.when(F.col("has_purchase") == 1, 1).otherwise(0)).alias("purchase"),
        )
        .first()
        .asDict()
    )
    stage_names = ["Browsing sessions", "Cart sessions", "Purchasing sessions"]
    stage_values = [int(stage_counts["browsing"]), int(stage_counts["cart"]), int(stage_counts["purchase"])]
    plt.figure(figsize=(9, 5.2))
    bars = plt.bar(stage_names, stage_values, color=["#8ecae6", "#ffb703", "#219ebc"])
    plt.title("Cross-system conversion funnel: HBase sessions to MongoDB purchases")
    plt.ylabel("Sessions")
    plt.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, stage_values):
        plt.text(bar.get_x() + bar.get_width() / 2, value, f"{value:,}", ha="center", va="bottom")
    generated.append(save_figure("04_cross_system_conversion_funnel.png"))

    summary = {
        "figures": generated,
        "monthly_sales": [row.asDict() for row in monthly],
        "top_categories": [row.asDict() for row in categories],
        "purchase_frequency_segments": {key: int(value) for key, value in segment_counts.items()},
        "funnel_stage_counts": {key: int(value) for key, value in stage_counts.items()},
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("\nPart 4 visualization job complete")
    for image in generated:
        print(f"- Created: {image}")
    print(f"- Funnel: browsing={stage_values[0]:,}, cart={stage_values[1]:,}, purchase={stage_values[2]:,}")
    print(f"- Saved summary: {SUMMARY_FILE.name}")
    print(f"- Total seconds: {summary['elapsed_seconds']}")
    spark.stop()


if __name__ == "__main__":
    main()
