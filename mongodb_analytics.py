"""MongoDB aggregation pipelines for Final Project Part 1."""

from __future__ import annotations

import json
from pathlib import Path

from pymongo import MongoClient


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_DIR / "mongodb_analytics_results.json"
MONGO_URI = "mongodb://127.0.0.1:27018"
DATABASE_NAME = "ecommerce_analytics"

# A processing payment is not treated as recognized revenue.
RECOGNIZED_STATUSES = ["completed", "shipped", "delivered"]


def to_jsonable(document: dict) -> dict:
    """Convert MongoDB values such as ObjectId/datetime into JSON-friendly strings."""
    return json.loads(json.dumps(document, default=str))


def main() -> None:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    database = client[DATABASE_NAME]

    # Pipeline 1: product popularity and recognized revenue by category.
    product_popularity_pipeline = [
        {"$match": {"status": {"$in": RECOGNIZED_STATUSES}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": {
                    "category_id": "$items.category_id",
                    "category_name": "$items.category_name",
                    "product_id": "$items.product_id",
                    "product_name": "$items.product_name",
                },
                "units_sold": {"$sum": "$items.quantity"},
                "gross_item_revenue_usd": {"$sum": "$items.subtotal"},
                "orders": {"$addToSet": "$transaction_id"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "category_id": "$_id.category_id",
                "category_name": "$_id.category_name",
                "product_id": "$_id.product_id",
                "product_name": "$_id.product_name",
                "units_sold": 1,
                "gross_item_revenue_usd": {"$round": ["$gross_item_revenue_usd", 2]},
                "distinct_orders": {"$size": "$orders"},
            }
        },
        {"$sort": {"gross_item_revenue_usd": -1, "units_sold": -1, "product_id": 1}},
        {"$limit": 15},
    ]

    # Pipeline 2: user segmentation based on recognized order count and spend.
    user_segmentation_pipeline = [
        {"$match": {"status": {"$in": RECOGNIZED_STATUSES}}},
        {
            "$group": {
                "_id": "$user_id",
                "recognized_orders": {"$sum": 1},
                "recognized_spend_usd": {"$sum": "$total"},
                "last_purchase_at": {"$max": "$timestamp"},
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "user",
            }
        },
        {"$unwind": "$user"},
        {
            "$set": {
                "segment": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {
                                    "$and": [
                                        {"$gte": ["$recognized_orders", 8]},
                                        {"$gte": ["$recognized_spend_usd", 1500]},
                                    ]
                                },
                                "then": "high_value",
                            },
                            {
                                "case": {
                                    "$or": [
                                        {"$gte": ["$recognized_orders", 4]},
                                        {"$gte": ["$recognized_spend_usd", 600]},
                                    ]
                                },
                                "then": "regular",
                            },
                        ],
                        "default": "occasional",
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$segment",
                "users": {"$sum": 1},
                "orders": {"$sum": "$recognized_orders"},
                "revenue_usd": {"$sum": "$recognized_spend_usd"},
                "average_spend_per_user_usd": {"$avg": "$recognized_spend_usd"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "segment": "$_id",
                "users": 1,
                "orders": 1,
                "revenue_usd": {"$round": ["$revenue_usd", 2]},
                "average_spend_per_user_usd": {"$round": ["$average_spend_per_user_usd", 2]},
            }
        },
        {"$sort": {"revenue_usd": -1, "segment": 1}},
    ]

    print("Pipeline 1 — top products by recognized gross item revenue")
    top_products = list(database.transactions.aggregate(product_popularity_pipeline))
    for row in top_products:
        print(
            f"{row['product_id']} | {row['units_sold']:,} units | "
            f"${row['gross_item_revenue_usd']:,.2f} | {row['product_name']}"
        )

    print("\nPipeline 2 — user purchase segments")
    segments = list(database.transactions.aggregate(user_segmentation_pipeline))
    for row in segments:
        print(
            f"{row['segment']}: {row['users']:,} users, {row['orders']:,} orders, "
            f"${row['revenue_usd']:,.2f} revenue"
        )

    output = {
        "recognized_statuses": RECOGNIZED_STATUSES,
        "pipeline_1_top_products": [to_jsonable(row) for row in top_products],
        "pipeline_2_user_segments": [to_jsonable(row) for row in segments],
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nSaved results: {OUTPUT_FILE.name}")
    client.close()


if __name__ == "__main__":
    main()
