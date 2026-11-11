# Part 1 — Data Modeling and Storage Design

## 1. Scope and dataset

The e-commerce dataset covers 90 days of activity and contains 10,000 users,
5,000 products, 25 category documents, 200,000 browsing sessions, and 50,000
transactions. MongoDB stores catalog, customer, and purchase documents. HBase
stores time-oriented browsing sessions in a row-key design that supports fast
retrieval of one user's activity. A reproducible 10,000-session random subset
(5% of all sessions) was loaded into HBase for the simplified implementation.

## 2. MongoDB design

Database: `ecommerce_analytics`

### 2.1 Collections and document decisions

| Collection | Key and principal fields | Modeling decision and reason |
|---|---|---|
| `categories` | `_id`/`category_id`, `name`, embedded `subcategories` | The category hierarchy is naturally a bounded nested document. A category is read with its small, stable list of subcategories, so embedding avoids a join for catalog browsing. |
| `products` | `_id`/`product_id`, name, category ID/name snapshot, price, stock, active flag, `price_history` array | A product's price history is bounded and belongs only to that product, so it is embedded. The category identifier supports filtering/indexing while the category name provides convenient display data. |
| `users` | `_id`/`user_id`, geographic profile, registration and activity timestamps, embedded `purchase_summary` | Frequently requested measures—order count, total spend, last purchase time, and preferred category—are embedded. This avoids recalculating a user's summary for simple segmentation or profile screens. |
| `transactions` | `_id`/`transaction_id`, user/session references, timestamp, payment/status, totals, embedded `items` | Line items are embedded because they are created, read, and analysed with their parent purchase. Each item is enriched with product/category information, preserving historical purchase context even if a product changes later. |

The generator provides a category association for each product. The full
category-to-subcategory hierarchy is retained in `categories`; a product uses
its category identifier and category-name snapshot because the generated
product record does not supply a specific subcategory identifier.

### 2.2 MongoDB query patterns and indexes

The main query patterns are product/category sales analysis, transaction lookup
by user and time, and customer segmentation. The implementation created indexes
on product category and active status, user state and order count, transaction
user/timestamp, transaction timestamp, transaction item product ID, and
transaction item category ID. These indexes support selective filters before
aggregation and direct retrieval of a user's transactions.

Two aggregation pipelines were implemented:

1. **Product popularity and revenue.** The pipeline filters to recognized
   purchase statuses (`completed`, `shipped`, and `delivered`), unwinds embedded
   line items, groups by category and product, calculates units, distinct orders,
   and gross item revenue, sorts descending by revenue, and returns the top 15.
2. **User purchase segmentation.** The pipeline groups recognized transactions
   by user, calculates order count, spend, and latest purchase, joins to the
   user profile, labels users as `high_value`, `regular`, or `occasional`, then
   summarizes users, orders, revenue, and average spend per segment.

All 25 categories, 5,000 products, 10,000 users, and 50,000 transactions were
loaded into MongoDB. The load and index operation took 3.413 seconds on the
project machine.

## 3. HBase design

### 3.1 `user_sessions` time-series table

Row key:

```text
user_id|ISO-8601-start_time|session_id
```

This key places all sessions belonging to one user together in lexicographic
order. Because ISO-8601 timestamps sort chronologically, a prefix scan such as
`user_005955|` retrieves that user's browsing sessions in time order without a
full-table scan. The session ID makes the key unique if timestamps coincide.

| Column family | Stored fields | Reason |
|---|---|---|
| `meta` | session ID, start/end time, duration, conversion status, referrer | Common session-level attributes used to interpret a browsing journey. |
| `device` | device type, operating system, browser | Device fields are read together for device/channel analysis. |
| `geo` | city, state, country, IP address | Location attributes form a separate, sparse group. |
| `activity` | viewed-products JSON, page-view count, cart-item count, cart-contents JSON | Variable-length browsing/cart data belongs to the session and is accessed as activity evidence. |

Each family uses one version and a row Bloom filter. One version is sufficient
because this project treats a completed session as immutable. The Bloom filter
helps avoid unnecessary disk reads for missing row keys.

### 3.2 `product_daily_metrics` table

Row key:

```text
product_id|YYYY-MM-DD
```

Column family `metrics` is designed to store daily view count, cart additions,
purchased quantity, and revenue. It supports a product's time-range scan and
allows later Spark processing to write compact daily product-performance facts.
The Part 1 simplified implementation created this schema; session loading was
the required implemented focus.

### 3.3 HBase implementation and query

A deterministic random sample of 10,000 sessions was derived from the raw
session data and batch-loaded to `user_sessions`. Verification returned exactly
10,000 rows. The following prefix-query pattern retrieved the stored session
for `user_005955`:

```ruby
scan 'user_sessions', {
  ROWPREFIXFILTER => 'user_005955|',
  COLUMNS => [
    'meta:session_id', 'meta:start_time', 'meta:duration_seconds',
    'meta:conversion_status', 'meta:referrer', 'device:type',
    'device:os', 'activity:page_view_count', 'activity:cart_item_count'
  ]
}
```

The query returned one row containing its session identifier, time, duration,
conversion status, referrer, device attributes, and activity counts.

## 4. Why MongoDB and HBase are both used

| Requirement | MongoDB | HBase |
|---|---|---|
| Nested catalog, profile, and purchase records | Strong fit: documents naturally embed arrays such as price history, purchase summaries, and line items. | Not ideal: these records would require many qualifiers or duplicated rows. |
| Customer/session time series | Possible, but a large append-heavy session stream can create expensive document growth and broad collection scans. | Strong fit: user-prefix row keys support sequential range scans of sparse, high-volume events. |
| Transaction and revenue aggregation | Strong fit: aggregation pipelines can unwind items and group/lookup business entities. | Better used as a fast event store than for cross-row aggregation. |
| Product performance over time | Useful for catalog context and transaction facts. | Strong fit for compact `product_id|date` metrics created from event processing. |

MongoDB was therefore selected for flexible business documents and analytical
aggregations over purchases. HBase was selected for high-volume session/event
storage where row-key locality matters. Spark, in the next part, can calculate
large-scale session/product metrics and combine data from both models.

## 5. Reproducibility files and evidence

| File | Purpose |
|---|---|
| `dataset_generator_runnable.py` | Generates raw JSON data into `data/raw`. |
| `load_mongodb.py` | Loads and indexes MongoDB collections. |
| `mongodb_analytics.py` | Runs the two MongoDB aggregation pipelines. |
| `prepare_hbase_subset.py` | Creates the deterministic 10,000-session HBase sample. |
| `hbase_schema.rb` | Creates the two HBase tables and column families. |
| `hbase_load_sessions.rb` | Batch-loads the HBase session subset. |
| `hbase_query_user_sessions.rb` | Runs the user-prefix session retrieval query. |

The report should include screenshots of MongoDB loading, both aggregation
results, HBase schema definitions, the 10,000-row HBase verification, and the
successful user-session retrieval.
