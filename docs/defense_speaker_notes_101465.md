# Defence speaker notes — 18-minute format

## Before your name is called
Open this presentation, your GitHub repository, and Command Prompt windows with these outputs ready. The first 10 minutes are your presentation; the remaining 8 minutes are questions. Do not spend time starting Docker, HBase, MongoDB, or Spark during the presentation.

## Slide 1 — 0:00–0:15
Say your name, ID, project title and technologies: MongoDB, HBase and Spark.

## Slide 2 — 0:15–1:00
Follow the architecture arrows. Explain that one system is not ideal for all data patterns.

## Slide 3 — 1:00–2:30
Point to MongoDB's embedded transaction items. Then explain that the HBase key begins with user ID, allowing a prefix scan to retrieve that user's sessions efficiently.

## Slide 4 — 2:30–5:30 (live demo)
Run or show saved output from:
```cmd
python mongodb_analytics.py
docker exec final-hbase hbase shell /tmp/hbase_query_user_sessions.rb user_005955
```
Explain aggregation stages: filter recognised orders, unwind items, group and sort. For HBase, explain prefix scan efficiency.

## Slide 5 — 5:30–6:40
Show saved Spark output from `python spark_batch_recommendations.py`. Explain cleaning, explode, self-join and count. State clearly that recommendation pairs are indicators, not proof of preference.

## Slide 6 — 6:40–7:30
Show `python spark_sql_analytics.py`. Explain that the SQL joins browsing/page-view rows with product and transaction data.

## Slides 7–8 — 7:30–9:00
State the integrated question, inputs and result. Key result: 10,000 browsing, 6,517 cart and 2,031 recognised purchase sessions.

## Slides 9–10 — 9:00–10:00
Show the category chart. Give the limitation: synthetic data and 10,000-session HBase sample. Close with the technology-fit conclusion.

## Q&A — 10:00–18:00
Likely questions: Why MongoDB instead of HBase for orders? Why a user-first HBase row key? What happens at larger scale? Why is the recommendation evidence weak? How does Spark join data sources?
