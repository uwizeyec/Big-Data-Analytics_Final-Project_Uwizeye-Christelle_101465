"""Part 2 Spark batch processing: clean e-commerce data and find product pairs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

# Avoid hostname-resolution issues in local Windows Spark runs.
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

from pyspark.sql import SparkSession, functions as F


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
ANALYTICS_DIR = PROJECT_DIR / "data" / "analytics"
SUMMARY_FILE = PROJECT_DIR / "spark_batch_summary.json"
RECOGNIZED_STATUSES = ["completed", "shipped", "delivered"]


def output_path(path: Path) -> str:
    """Return a native absolute path; Spark on Windows handles this reliably."""
    return str(path.resolve())


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw data folder not found: {RAW_DIR}")

    started = perf_counter()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder.appName("EcommerceSparkBatchRecommendations")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("Reading raw JSON arrays with Spark ...")
    raw_users = spark.read.option("multiline", "true").json(output_path(RAW_DIR / "users.json"))
    raw_products = spark.read.option("multiline", "true").json(output_path(RAW_DIR / "products.json"))
    raw_transactions = spark.read.option("multiline", "true").json(
        output_path(RAW_DIR / "transactions.json")
    )

    # Standardize identifiers, convert ISO strings to timestamp columns, cast
    # numerical values, and discard only records missing a required identifier.
    users = (
        raw_users.select(
            F.trim("user_id").alias("user_id"),
            F.col("geo_data.city").alias("city"),
            F.col("geo_data.state").alias("state"),
            F.col("geo_data.country").alias("country"),
            F.to_timestamp("registration_date").alias("registration_timestamp"),
            F.to_timestamp("last_active").alias("last_active_timestamp"),
        )
        .filter(F.col("user_id").isNotNull())
        .dropDuplicates(["user_id"])
    )

    products = (
        raw_products.select(
            F.trim("product_id").alias("product_id"),
            F.trim("name").alias("product_name"),
            F.trim("category_id").alias("category_id"),
            F.col("base_price").cast("double").alias("base_price_usd"),
            F.col("current_stock").cast("integer").alias("current_stock"),
            F.col("is_active").cast("boolean").alias("is_active"),
            F.to_timestamp("creation_date").alias("creation_timestamp"),
        )
        .filter(F.col("product_id").isNotNull() & F.col("category_id").isNotNull())
        .dropDuplicates(["product_id"])
    )

    transaction_items = (
        raw_transactions.select(
            F.trim("transaction_id").alias("transaction_id"),
            F.trim("user_id").alias("user_id"),
            F.trim("session_id").alias("session_id"),
            F.to_timestamp("timestamp").alias("transaction_timestamp"),
            F.lower(F.trim("status")).alias("status"),
            F.lower(F.trim("payment_method")).alias("payment_method"),
            F.col("subtotal").cast("double").alias("transaction_subtotal_usd"),
            F.col("discount").cast("double").alias("discount_usd"),
            F.col("total").cast("double").alias("transaction_total_usd"),
            F.explode_outer("items").alias("item"),
        )
        .select(
            "transaction_id",
            "user_id",
            "session_id",
            "transaction_timestamp",
            "status",
            "payment_method",
            "transaction_subtotal_usd",
            "discount_usd",
            "transaction_total_usd",
            F.trim("item.product_id").alias("product_id"),
            F.col("item.quantity").cast("integer").alias("quantity"),
            F.col("item.unit_price").cast("double").alias("unit_price_usd"),
            F.col("item.subtotal").cast("double").alias("item_subtotal_usd"),
        )
        .filter(
            F.col("transaction_id").isNotNull()
            & F.col("user_id").isNotNull()
            & F.col("transaction_timestamp").isNotNull()
            & F.col("product_id").isNotNull()
            & (F.col("quantity") > 0)
            & (F.col("unit_price_usd") >= 0)
        )
        .dropDuplicates(["transaction_id", "product_id"])
    )

    # Referential cleaning: retain only transaction line items with a known product.
    transaction_items = transaction_items.join(
        products.select("product_id", "product_name", "category_id"), "product_id", "inner"
    )

    print("Writing cleaned and normalized Parquet datasets ...")
    users.write.mode("overwrite").parquet(output_path(PROCESSED_DIR / "users"))
    products.write.mode("overwrite").parquet(output_path(PROCESSED_DIR / "products"))
    transaction_items.write.mode("overwrite").parquet(output_path(PROCESSED_DIR / "transaction_items"))

    # Recommendation indicator: two distinct products bought in the same
    # recognized transaction. Product A < Product B prevents mirrored duplicates.
    recognized = transaction_items.filter(F.col("status").isin(RECOGNIZED_STATUSES)).select(
        "transaction_id", "product_id"
    )
    left = recognized.alias("left")
    right = recognized.alias("right")
    pairs = (
        left.join(
            right,
            (F.col("left.transaction_id") == F.col("right.transaction_id"))
            & (F.col("left.product_id") < F.col("right.product_id")),
            "inner",
        )
        .groupBy(
            F.col("left.product_id").alias("product_a_id"),
            F.col("right.product_id").alias("product_b_id"),
        )
        .agg(F.countDistinct(F.col("left.transaction_id")).alias("co_purchase_count"))
    )

    product_a = products.select(
        F.col("product_id").alias("product_a_id"),
        F.col("product_name").alias("product_a_name"),
        F.col("category_id").alias("product_a_category_id"),
    )
    product_b = products.select(
        F.col("product_id").alias("product_b_id"),
        F.col("product_name").alias("product_b_name"),
        F.col("category_id").alias("product_b_category_id"),
    )
    top_recommendations = (
        pairs.join(product_a, "product_a_id", "inner")
        .join(product_b, "product_b_id", "inner")
        .orderBy(F.desc("co_purchase_count"), F.asc("product_a_id"), F.asc("product_b_id"))
        .limit(20)
    )

    top_recommendations.coalesce(1).write.mode("overwrite").option("header", "true").csv(
        output_path(ANALYTICS_DIR / "top_product_recommendations_csv")
    )

    raw_counts = {
        "users": raw_users.count(),
        "products": raw_products.count(),
        "transactions": raw_transactions.count(),
    }
    clean_counts = {
        "users": users.count(),
        "products": products.count(),
        "transaction_items": transaction_items.count(),
        "recognized_transaction_items": recognized.count(),
        "unique_recommendation_pairs": pairs.count(),
    }
    recommendations = [row.asDict() for row in top_recommendations.collect()]

    summary = {
        "spark_version": spark.version,
        "recognized_statuses": RECOGNIZED_STATUSES,
        "raw_counts": raw_counts,
        "clean_counts": clean_counts,
        "top_recommendations": recommendations,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "outputs": {
            "normalized_users": str(PROCESSED_DIR / "users"),
            "normalized_products": str(PROCESSED_DIR / "products"),
            "normalized_transaction_items": str(PROCESSED_DIR / "transaction_items"),
            "top_recommendations_csv": str(ANALYTICS_DIR / "top_product_recommendations_csv"),
        },
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\nSpark batch job complete")
    print(f"- Raw users/products/transactions: {raw_counts}")
    print(f"- Cleaned counts: {clean_counts}")
    print("- Top 10 product recommendation indicators:")
    top_recommendations.show(10, truncate=42)
    print(f"- Saved summary: {SUMMARY_FILE.name}")
    print(f"- Total seconds: {summary['elapsed_seconds']}")
    spark.stop()


if __name__ == "__main__":
    main()
