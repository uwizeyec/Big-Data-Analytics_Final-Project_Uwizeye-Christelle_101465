# Part 3 — Analytics Integration

## Business question

**Which device type and acquisition channel (referrer) create the strongest customer journey from product browsing, through cart activity, to a recognised purchase?**

This question helps an e-commerce provider decide where to improve the customer experience and where to invest marketing spend. A channel with many visits but a low purchase-conversion rate may need a better landing page or checkout journey. A channel with high revenue per purchasing session may be valuable even if it has fewer visits.

## Systems and data used

| System | Logical data used | Reason for using it |
|---|---|---|
| HBase (`user_sessions`) | `session_id`, device type, referrer, page-view activity, cart contents, conversion status | HBase is designed for direct retrieval of time-oriented session activity. The row key begins with user and session time, so related activity is stored together. |
| MongoDB (`transactions`, `products`) | Transaction ID, session ID, item quantity, recognised status, item revenue, product/category | MongoDB documents retain transaction line items together with product details. They support flexible transactional and catalogue data. |
| Spark | Session-to-transaction join and funnel aggregation | Spark performs the distributed-style join and aggregation across the two logical sources without moving manual results between tools. |

For reproducibility, `spark_integrated_funnel.py` reads the JSON subset loaded into HBase and the normalised Parquet exports created from the MongoDB document data. These are representations of the same logical records, allowing the Spark code to run locally without an additional Spark connector configuration.

## Processing pipeline

1. Read the **10,000-session HBase sample** and select its session ID, device type, referrer, page count and cart contents.
2. Derive the browsing and cart funnel stages. The generator's stable `conversion_status` is used as the cart indicator: `browsed` means no cart, while `abandoned` and `converted` mean that one or more products were placed in the cart. This avoids treating the variable product-ID JSON object as a fixed relational schema.
3. Read normalised MongoDB transaction-item and product records from Parquet.
4. Retain only recognised transaction statuses: `completed`, `shipped` and `delivered`.
5. Join transaction records to the HBase session cohort on `session_id`. This deliberately restricts sales to the same session sample, so conversion rates use a consistent denominator.
6. Aggregate by `device_type` and `referrer`, returning browsing sessions, cart sessions, purchasing sessions, orders, units, revenue, cart rate, purchase conversion and revenue per purchasing session.
7. Write a one-file CSV table and JSON summary for evidence and reporting.

## Spark SQL logic

The application registers the following temporary views:

- `hbase_sessions`
- `mongo_transaction_items`
- `mongo_products`

The SQL first forms a `mongo_sales` CTE grouped by `session_id`. It then left-joins this CTE to `hbase_sessions` and groups the journey by device type and referrer. The `LEFT JOIN` preserves browsing sessions with no purchase, which is essential for a valid funnel denominator.

## Optimization choices

- The program uses already cleaned **Parquet** transaction/product records, avoiding repeated JSON parsing for MongoDB-shaped data.
- It filters to recognised transaction statuses before the join, reducing sales-side work.
- `SELECT DISTINCT session_id` ensures the HBase cohort is not multiplied during the transaction join.
- It uses `local[2]`, eight shuffle partitions and no cached data: modest settings suitable for the local laptop and the project-scale sample.
- The final result is coalesced to one CSV partition because it is a small reporting table. The upstream aggregation remains partitioned.

## Files and evidence

- Application: `spark_integrated_funnel.py`
- JSON summary: `spark_integrated_funnel_summary.json`
- Result table: `data/analytics/integrated_funnel_by_device_referrer_csv/`

Screenshot the completed console result. It shows the joined funnel table and cohort check, demonstrating that HBase browsing evidence and MongoDB purchase evidence were processed together by Spark.
