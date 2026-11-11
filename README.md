# E-Commerce Big Data Analytics Final Project

This repository contains a reproducible local implementation of an e-commerce analytics platform using **MongoDB**, **HBase**, and **Apache Spark**.

## Project scope

The generated dataset contains 10,000 users, 5,000 products, 25 categories, 50,000 transactions, and 200,000 browsing sessions across 90 days. The project demonstrates:

- MongoDB document modelling, indexes, and aggregation pipelines;
- HBase time-series session storage and prefix retrieval;
- Spark batch cleaning, co-purchase indicators, and Spark SQL analytics;
- a cross-system funnel analysis joining HBase session evidence to MongoDB purchase evidence;
- four static figures for business reporting.

## Repository layout

| Path | Purpose |
|---|---|
| `dataset_generator_runnable.py` | Generates the synthetic raw JSON records. |
| `load_mongodb.py`, `mongodb_analytics.py` | MongoDB loading, indexing, and aggregation pipelines. |
| `prepare_hbase_subset.py`, `hbase_*.rb` | HBase subset preparation, schema, loading, verification, and retrieval. |
| `spark_batch_recommendations.py` | Cleaning/normalization and product co-purchase indicator. |
| `spark_sql_analytics.py` | Two Spark SQL analytical queries. |
| `spark_integrated_funnel.py` | Cross-system HBase-to-MongoDB conversion-funnel analysis. |
| `create_part4_visualizations.py` | Creates the four static PNG figures. |
| `docs/` | Design documents and final technical-report source. |

## Prerequisites

- Python 3.10+ (the project was run with Python 3.13)
- Java 17 and PySpark 3.5.3
- Docker Desktop
- Python packages: `pyspark`, `pymongo`, `matplotlib`

## Reproducing the key results

Run the commands from the project root in Windows Command Prompt. Run each command separately.

### 1. Generate data

```cmd
python dataset_generator_runnable.py
```

### 2. MongoDB

MongoDB was run in Docker on host port 27018:

```cmd
docker run -d --name final-mongodb -p 127.0.0.1:27018:27017 -v final_mongodb_data:/data/db mongo:7
python load_mongodb.py
python mongodb_analytics.py
```

If the container already exists but is stopped, run `docker start final-mongodb` instead of `docker run`.

### 3. HBase

The Docker container is named `final-hbase`. Start it, then create the schema, prepare the sample, and load it:

```cmd
docker start final-hbase
python prepare_hbase_subset.py
docker cp hbase_schema.rb final-hbase:/tmp/hbase_schema.rb
docker exec final-hbase hbase shell /tmp/hbase_schema.rb
docker cp hbase_load_sessions.rb final-hbase:/tmp/hbase_load_sessions.rb
docker exec final-hbase hbase shell /tmp/hbase_load_sessions.rb
```

Use `hbase_verify_sessions.rb` to verify the stored row count and `hbase_query_user_sessions.rb user_005955` for an example prefix query.

### 4. Spark and integration

```cmd
python spark_batch_recommendations.py
python spark_sql_analytics.py
python spark_integrated_funnel.py
python create_part4_visualizations.py
```

Spark jobs run locally with `local[2]`. They write outputs beneath `data/processed`, `data/analytics`, and `data/visualizations`.

## Key results

- 109,863 cleaned transaction-item records; 92,216 recognized-status item records.
- 68,565 unique co-purchase pairs; signals are weak because baskets and a 5,000-product catalog are mostly random.
- 10,000 HBase session rows loaded and verified.
- Integrated funnel: 10,000 browsing sessions, 6,517 cart sessions, and 2,031 matched recognized-purchase sessions.

## Submission notes

Raw/generated data is intentionally excluded from Git because it is reproducible and large. Run the generator and preparation scripts to recreate it. The report source is in `docs/final_technical_report.md`; open it in Word or a Markdown editor, add your name/student ID and selected screenshots, then export it as PDF.
