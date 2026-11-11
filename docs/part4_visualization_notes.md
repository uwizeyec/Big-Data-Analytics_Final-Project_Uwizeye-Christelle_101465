# Part 4 — Visualization and Insights

Run `python create_part4_visualizations.py` to create four static, report-ready PNG charts in `data/visualizations/`.

| Figure | Finding represented | Suggested report insight |
|---|---|---|
| `01_monthly_sales_performance.png` | Recognised item revenue and order count by month | Compare whether revenue and order volume move together; a difference can indicate changes in basket value. |
| `02_top_category_revenue.png` | Ten categories with the highest recognised item revenue | The leading categories are candidates for stock planning and campaign focus; this is revenue, not profit. |
| `03_customer_purchase_segments.png` | Users split by recognised order frequency | The distribution separates occasional and repeat buyers, which supports retention or loyalty targeting. |
| `04_cross_system_conversion_funnel.png` | HBase browsing and cart sessions matched to MongoDB recognised purchase sessions | Drop-off between stages identifies where journey improvements may be valuable. It uses the same 10,000-session HBase cohort for a valid denominator. |

Embed the four resulting PNG files in the final report. Explain the observed pattern using the generated values, and avoid causal claims: these synthetic records show associations, not proof that a device type or referrer caused a purchase.
