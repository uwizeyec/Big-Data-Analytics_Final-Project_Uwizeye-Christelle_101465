# Part 2 — Apache Spark Data Processing

## 1. Purpose and execution environment

Apache Spark was used for local distributed-style batch processing of the
e-commerce JSON dataset. The application ran with PySpark 3.5.3 and Java 17 in
`local[2]` mode. The goal was to clean nested JSON records, create reusable
normalized datasets, produce a product co-purchase recommendation indicator,
and use Spark SQL for cross-source-style analytics.

## 2. Batch pipeline

The batch application is `spark_batch_recommendations.py`. It reads
`users.json`, `products.json`, and `transactions.json` using Spark's multiline
JSON reader. The input contains nested transaction `items` arrays, so the
transaction processing pipeline explodes each item into a separate line-item
row.

### 2.1 Cleaning and normalization transformations

| Dataset | Transformations |
|---|---|
| Users | Trimmed the business ID, extracted city/state/country, parsed registration and last-active ISO timestamps, removed null IDs, and deduplicated by `user_id`. |
| Products | Trimmed IDs/text, cast price and stock to numeric types, cast the active flag to Boolean, parsed creation date, removed missing identifiers, and deduplicated by `product_id`. |
| Transaction items | Trimmed transaction/user/session/product IDs, parsed transaction timestamp, standardized status and payment method to lower case, cast monetary and quantity fields, exploded the `items` array, removed incomplete/invalid rows, deduplicated by transaction/product, and inner-joined products to reject unknown product references. |

The raw input contained 10,000 users, 5,000 products, and 50,000
transactions. The normalized line-item fact table contained 109,863 valid
transaction-item rows, of which 92,216 belonged to recognized statuses:
`completed`, `shipped`, and `delivered`.

The cleaned user, product, and transaction-item datasets are stored as Parquet
under `data/processed`. Parquet preserves typed schema and is more efficient
than repeatedly parsing source JSON in later Spark tasks.

### 2.2 Product co-purchase recommendation indicator

The recommendation calculation uses recognized transaction line items. The
same dataset is joined to itself on `transaction_id`, while retaining only
`product_a_id < product_b_id`. This creates each unordered pair once rather
than producing a mirrored `(A,B)` and `(B,A)` result. Spark groups the pairs
and counts distinct transactions containing both products.

The job found 68,565 unique product pairs and saved the top 20 as CSV under
`data/analytics/top_product_recommendations_csv`. In the synthetic data, the
highest observed co-purchase counts were two. This is expected for a catalog
of 5,000 products and mostly random baskets; these are weak association
signals, not sufficient evidence for production recommendations.

## 3. Spark SQL analytics

The application `spark_sql_analytics.py` registers temporary views from the
normalized datasets and from the same 10,000-session sample loaded into HBase.
This demonstrates Spark SQL logic across data that would notionally reside in
different systems without requiring database connector configuration.

| Temporary view | Logical source system |
|---|---|
| `mongo_users` | MongoDB user-profile documents |
| `mongo_products` | MongoDB product-catalog documents |
| `mongo_transaction_items` | MongoDB transaction documents after item-array flattening |
| `hbase_user_sessions` | HBase `user_sessions` time-series rows |
| `hbase_page_views` | HBase session activity, exploded to individual page-view events |

### 3.1 Query 1: customer engagement and recognized purchase value

The first SQL query uses two common table expressions (CTEs):

1. `hbase_engagement` groups HBase session rows by user and calculates sampled
   sessions, page views, average session duration, and converted sessions.
2. `mongo_purchase_value` groups recognized MongoDB transaction items by user
   and calculates orders and item revenue.

These CTEs are left-joined to user profiles and grouped by state and value
segment. The output combines behavioural engagement with purchase value, which
is a useful basis for retention or marketing analysis.

### 3.2 Query 2: category view-to-purchase funnel

The second SQL query contains two CTEs:

1. `hbase_views` counts product-detail page views and viewer sessions by
   category from HBase page-view events.
2. `mongo_sales` joins transaction items to the same sampled HBase session IDs,
   then calculates purchasing transactions, units, and revenue by category.

The final full outer join retains categories with views but no purchases and
categories with purchases but no views. It calculates:

```text
100 × purchasing_transactions / product_detail_views
```

as purchases per 100 product-detail views. Limiting the sales CTE to the same
HBase session sample is important: it keeps numerator and denominator in the
same cohort. The final results ranged approximately from 8 to 10 purchases per
100 product-detail views, rather than misleading values above 100 caused by
mixing a session sample with the complete transaction dataset.

Complete SQL query text and result rows are saved in `spark_sql_summary.json`.

## 4. Optimization choices and scalability considerations

- **Typed Parquet outputs:** Normalized data is written once as Parquet, which
  avoids repeated JSON parsing for later processing and allows column pruning.
- **Early data-quality filtering:** Required identifiers and valid quantities
  are checked before the recommendation self-join, reducing join input volume.
- **Deduplication before pairing:** Transaction/product duplicates are removed,
  and `product_a_id < product_b_id` prevents mirrored pair generation.
- **Limited shuffle partitions:** `spark.sql.shuffle.partitions` is set to 8,
  appropriate for the local two-core execution setting. A real cluster would
  choose this value based on executor cores and data size.
- **Selective session sample:** The HBase sample is adequate for demonstrating
  SQL logic within laptop memory. A production pipeline would query HBase by
  time range or read a larger distributed export.
- **No cache was retained:** The inputs are read once per short job. For
  repeated interactive queries, the normalized Parquet DataFrames could be
  persisted after measuring available executor memory.

## 5. Reproducibility and evidence

| File | Purpose |
|---|---|
| `spark_batch_recommendations.py` | Cleans data, writes Parquet, and computes co-purchase pairs. |
| `spark_batch_summary.json` | Counts, recommendation results, and batch runtime. |
| `spark_sql_analytics.py` | Registers views and runs both complex Spark SQL queries. |
| `spark_sql_summary.json` | Complete SQL text, output rows, and SQL runtime. |

The report should include the batch-processing screenshot and the final Spark
SQL query screenshots. The Spark output demonstrates a 30.535-second batch job
and a 31.619-second final Spark SQL run on the project laptop.
