"""Load the generated e-commerce data into MongoDB for Final Project Part 1."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import perf_counter

from pymongo import ASCENDING, MongoClient


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
SUMMARY_FILE = PROJECT_DIR / "mongodb_load_summary.json"
MONGO_URI = "mongodb://127.0.0.1:27018"
DATABASE_NAME = "ecommerce_analytics"
BATCH_SIZE = 1_000


def read_json(filename: str) -> list[dict]:
    with (RAW_DIR / filename).open(encoding="utf-8") as source:
        return json.load(source)


def as_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def batches(documents: list[dict]):
    for start in range(0, len(documents), BATCH_SIZE):
        yield documents[start : start + BATCH_SIZE]


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw-data folder not found: {RAW_DIR}")

    started = perf_counter()
    print("Reading raw JSON files ...")
    categories = read_json("categories.json")
    products = read_json("products.json")
    users = read_json("users.json")
    transactions = read_json("transactions.json")

    category_by_id = {category["category_id"]: category for category in categories}
    product_by_id = {product["product_id"]: product for product in products}

    # Compute compact, frequently accessed user summaries from transactions.
    user_summary: dict[str, dict] = defaultdict(
        lambda: {
            "order_count": 0,
            "total_spend": 0.0,
            "last_purchase_at": None,
            "category_spend": defaultdict(float),
        }
    )

    mongo_transactions: list[dict] = []
    for transaction in transactions:
        enriched_items = []
        for item in transaction["items"]:
            product = product_by_id[item["product_id"]]
            category = category_by_id[product["category_id"]]
            enriched_items.append(
                {
                    "product_id": item["product_id"],
                    "product_name": product["name"],
                    "category_id": category["category_id"],
                    "category_name": category["name"],
                    "quantity": int(item["quantity"]),
                    "unit_price": float(item["unit_price"]),
                    "subtotal": float(item["subtotal"]),
                }
            )

        timestamp = as_datetime(transaction["timestamp"])
        mongo_transactions.append(
            {
                "_id": transaction["transaction_id"],
                "transaction_id": transaction["transaction_id"],
                "session_id": transaction["session_id"],
                "user_id": transaction["user_id"],
                "timestamp": timestamp,
                "items": enriched_items,
                "subtotal": float(transaction["subtotal"]),
                "discount": float(transaction["discount"]),
                "total": float(transaction["total"]),
                "payment_method": transaction["payment_method"],
                "status": transaction["status"],
            }
        )

        summary = user_summary[transaction["user_id"]]
        summary["order_count"] += 1
        summary["total_spend"] += float(transaction["total"])
        if summary["last_purchase_at"] is None or timestamp > summary["last_purchase_at"]:
            summary["last_purchase_at"] = timestamp
        for item in enriched_items:
            summary["category_spend"][item["category_id"]] += item["subtotal"]

    mongo_products = []
    for product in products:
        category = category_by_id[product["category_id"]]
        mongo_products.append(
            {
                "_id": product["product_id"],
                "product_id": product["product_id"],
                "name": product["name"],
                "category": {
                    "category_id": category["category_id"],
                    "name": category["name"],
                },
                "base_price": float(product["base_price"]),
                "current_stock": int(product["current_stock"]),
                "is_active": bool(product["is_active"]),
                "price_history": [
                    {"price": float(point["price"]), "date": as_datetime(point["date"])}
                    for point in product["price_history"]
                ],
                "creation_date": as_datetime(product["creation_date"]),
            }
        )

    mongo_categories = [
        {"_id": category["category_id"], **category} for category in categories
    ]

    mongo_users = []
    for user in users:
        summary = user_summary[user["user_id"]]
        top_category_id = None
        if summary["category_spend"]:
            top_category_id = max(summary["category_spend"], key=summary["category_spend"].get)
        mongo_users.append(
            {
                "_id": user["user_id"],
                "user_id": user["user_id"],
                "geo_data": user["geo_data"],
                "registration_date": as_datetime(user["registration_date"]),
                "last_active": as_datetime(user["last_active"]),
                "purchase_summary": {
                    "order_count": summary["order_count"],
                    "total_spend": round(summary["total_spend"], 2),
                    "last_purchase_at": summary["last_purchase_at"],
                    "preferred_category_id": top_category_id,
                },
            }
        )

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    database = client[DATABASE_NAME]

    print("Replacing collections in ecommerce_analytics ...")
    for collection_name in ("categories", "products", "users", "transactions"):
        database.drop_collection(collection_name)

    for collection, documents in (
        (database.categories, mongo_categories),
        (database.products, mongo_products),
        (database.users, mongo_users),
        (database.transactions, mongo_transactions),
    ):
        for batch in batches(documents):
            collection.insert_many(batch, ordered=False)
        print(f"  {collection.name}: {len(documents):,} documents loaded")

    print("Creating query indexes ...")
    database.products.create_index([("category.category_id", ASCENDING)], name="idx_product_category")
    database.products.create_index([("is_active", ASCENDING)], name="idx_product_active")
    database.users.create_index([("geo_data.state", ASCENDING)], name="idx_user_state")
    database.users.create_index(
        [("purchase_summary.order_count", ASCENDING)], name="idx_user_order_count"
    )
    database.transactions.create_index([("user_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_txn_user_time")
    database.transactions.create_index([("timestamp", ASCENDING)], name="idx_txn_time")
    database.transactions.create_index([("items.product_id", ASCENDING)], name="idx_txn_item_product")
    database.transactions.create_index([("items.category_id", ASCENDING)], name="idx_txn_item_category")

    summary = {
        "database": DATABASE_NAME,
        "mongo_uri": MONGO_URI,
        "source_counts": {
            "categories": len(categories),
            "products": len(products),
            "users": len(users),
            "transactions": len(transactions),
        },
        "loaded_counts": {
            name: database[name].count_documents({})
            for name in ("categories", "products", "users", "transactions")
        },
        "indexes": {
            name: list(database[name].index_information())
            for name in ("products", "users", "transactions")
        },
        "load_seconds": round(perf_counter() - started, 3),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\nMongoDB load complete")
    for name, count in summary["loaded_counts"].items():
        print(f"- {name}: {count:,}")
    print(f"- Load and index seconds: {summary['load_seconds']}")
    print(f"- Saved summary: {SUMMARY_FILE.name}")
    client.close()


if __name__ == "__main__":
    main()
