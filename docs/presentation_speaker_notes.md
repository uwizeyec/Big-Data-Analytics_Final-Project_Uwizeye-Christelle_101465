# Presentation speaker notes

## Slide 1 — Title
Introduce the project as an e-commerce analytics platform. State that it combines MongoDB, HBase and Spark rather than using one database for every task.

## Slide 2 — Business problem
Explain the business need: understanding customers, products and the route from browsing to purchase.

## Slide 3 — Dataset
Mention that the generator produced a realistic, sizeable dataset: 10,000 users, 5,000 products, 50,000 transactions and 200,000 sessions.

## Slide 4 — Architecture
Follow the arrows. Raw JSON is generated first. MongoDB stores business documents; HBase stores time-series browsing events; Spark cleans, joins and analyses the information.

## Slide 5 — MongoDB
Explain why documents fit product, user and transaction records. Embedded line items mean an order can be retrieved as a single document.

## Slide 6 — HBase
Explain that HBase is chosen for efficient retrieval of sessions for one user. The row key starts with the user ID, so the user’s activity is stored together.

## Slide 7 — Spark
Say that Spark creates reliable analytical tables from raw JSON and makes large joins and aggregations easier.

## Slides 8–10 — Visual findings
Describe each chart in one sentence. Avoid claiming causal relationships; these are descriptive findings from generated data.

## Slides 11–12 — Integration
Emphasize the value of combining systems: HBase explains behaviour before purchase while MongoDB records recognised orders and revenue. Spark joins them by session ID.

## Slide 13 — Insights
State the key practical implication: investigate cart abandonment and use product/category results to prioritize marketing or merchandising analysis.

## Slide 14 — Conclusion
Summarize the technology fit: MongoDB for documents, HBase for time-series session lookups and Spark for scalable processing. Invite questions.
