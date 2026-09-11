# KPI Definitions

Every KPI here maps directly to a column in a SQL view (`sql/analytical_views.sql`),
so there's no ambiguity between "what the dashboard shows" and "what the query computes."

## Sales

| KPI | Definition | Source |
|---|---|---|
| **Total Revenue** | `SUM(quantity * unit_price * (1 - discount_pct))` | `v_monthly_sales.total_revenue` |
| **MoM Revenue Growth %** | `(this_month_revenue - last_month_revenue) / last_month_revenue * 100` | `v_monthly_sales.mom_revenue_growth_pct` |
| **Average Order Value (AOV)** | `total_revenue / distinct order_count` | `v_monthly_sales.avg_order_value` |
| **Active Customers (monthly)** | Distinct customers with ≥1 order in the month | `v_monthly_sales.active_customers` |
| **Gross Margin** | `revenue - (quantity * cost_price)`, at product level | `v_product_performance.gross_margin` |

## Customers

| KPI | Definition | Source |
|---|---|---|
| **Customer Revenue Contribution %** | Customer's revenue / total revenue | `v_customer_pareto.pct_of_total_revenue` |
| **Pareto Bucket** | "Top 80%" = customers whose cumulative revenue share crosses 80% first (sorted desc) | `v_customer_pareto.pareto_bucket` |
| **Recency** | Days since customer's last order, vs. latest date in dataset | `v_customer_rfm.recency_days` |
| **Frequency** | Count of distinct orders per customer | `v_customer_rfm.frequency` |
| **Monetary** | Total revenue per customer | `v_customer_rfm.monetary` |
| **Inactive Customer** | Recency > 90 days | `v_customer_rfm.customer_segment_label = 'Inactive (90+ days)'` |
| **Champion** | Top quartile on all 3 RFM dimensions | `v_customer_rfm.customer_segment_label = 'Champion'` |

## Inventory / Operations

| KPI | Definition | Source |
|---|---|---|
| **Weeks of Cover** | `closing_stock / avg_weekly_sales` (last 8 snapshots) | `v_inventory_status.weeks_of_cover` |
| **Low Stock Flag** | `closing_stock <= reorder_level` | `v_inventory_status.movement_status` |
| **Fast Moving** | Weeks of cover < 2 | `v_inventory_status.movement_status` |
| **Slow Moving** | Weeks of cover > 8 | `v_inventory_status.movement_status` |
| **Dead Stock** | Zero sales velocity over last 8 snapshots | `v_inventory_status.movement_status` |

## Data Quality

| KPI | Definition | Source |
|---|---|---|
| **Quarantine Rate** | `(raw_row_count - clean_row_count) / raw_row_count` | printed by `etl/clean_and_load.py`, logged per-issue in `dq_log` |
| **Issue Count by Type** | Count of duplicate / missing_value / invalid_quantity / invalid_price / invalid_date / referential_integrity issues | `v_dq_summary` |

## Anomaly Detection

| KPI | Definition | Source |
|---|---|---|
| **Order Revenue Z-score** | `(order_revenue - mean_order_revenue) / stddev_order_revenue` | `v_order_anomalies.z_score` |
| **Anomaly Flag** | `\|z\| >= 3` | `v_order_anomalies.anomaly_flag` |

## Forecasting

| Metric | Definition | Source |
|---|---|---|
| **3-Month Moving Average** | Rolling mean of monthly revenue, window=3 | `forecast_output.csv` |
| **Linear Trend Forecast** | OLS regression of revenue on month index, projected 3 months forward | `etl/forecast.py` |
| **Trend R²** | Goodness-of-fit of the linear trend — reported honestly; low R² here (0.008) signals seasonality dominates and a seasonal model would be needed for production use | `etl/forecast.py` output |
