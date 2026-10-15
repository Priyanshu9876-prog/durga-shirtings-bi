# Tableau Dashboard Design

> Implementation template: use
> `tableau/tableau_public_workbook_spec.md` for exact worksheet names, field
> placements, calculated fields, and dashboard layout assembly in Tableau Public.

**Data source:** run `python etl/prepare_tableau_assets.py` first, then either:
- connect Tableau to SQLite `data/clean/durga_shirtings.db`, or
- connect to CSV extracts in `data/clean/tableau_extracts/` (recommended for
  portability and no-driver setup).

Generated CSV extract files:
- `sales_overview_monthly.csv`
- `sales_overview_product_performance.csv`
- `sales_overview_forecast_output.csv`
- `customer_analytics_pareto.csv`
- `customer_analytics_rfm.csv`
- `inventory_operations_status.csv`
- `inventory_operations_reorder_alerts.csv`
- `data_quality_summary.csv`
- `data_quality_order_anomalies.csv`
- `data_quality_latest_batch_metrics.csv`

Four dashboards (sheets), one story point each — built to be walked through
in an interview in under 3 minutes.

## 1. Sales Overview
- **KPI cards (top row):** Total Revenue, MoM Growth %, AOV, Active Customers
  — from `v_monthly_sales`
- **Line chart:** Monthly revenue trend with 3-month moving average overlay
  and 3-month forecast — from `forecast_output.csv`
- **Bar chart:** Revenue by product category — from `v_product_performance`
- **Filters:** Date range (fiscal year), Sales Channel, Product Category

**CSV sources + required fields**
- `sales_overview_monthly.csv`:
  `year`, `month`, `month_name`, `fiscal_year`, `total_revenue`,
  `total_qty_sold`, `total_orders`, `active_customers`, `avg_order_value`,
  `mom_revenue_growth_pct`
- `sales_overview_product_performance.csv`:
  `product_id`, `product_name`, `fabric_type`, `category`, `total_revenue`,
  `total_qty_sold`, `order_count`, `distinct_customers`,
  `avg_realized_price_per_unit`, `gross_margin`
- `sales_overview_forecast_output.csv`:
  `month_name`, `total_revenue`, `moving_avg_3m`, `forecast_revenue`,
  `is_forecast`, `period_index`

## 2. Customer Analytics
- **Pareto chart:** Cumulative revenue % vs. customer count (dual-axis: bar
  for individual revenue, line for cumulative %) — from `v_customer_pareto`
- **Scatter plot:** Recency (x) vs. Monetary (y), sized by Frequency, colored
  by `customer_segment_label` — from `v_customer_rfm`. This is the single
  most interview-relevant chart: it's a segmentation visual built from raw
  behavioral data, not a pre-labeled category.
- **Table:** Top 10 customers by revenue with segment and last order date
- **Filters:** Customer Segment, Region/State

**CSV sources + required fields**
- `customer_analytics_pareto.csv`:
  `customer_id`, `customer_name`, `segment`, `customer_revenue`,
  `pct_of_total_revenue`, `cumulative_pct_of_revenue`, `pareto_bucket`,
  `revenue_rank`
- `customer_analytics_rfm.csv`:
  `customer_id`, `customer_name`, `segment`, `last_order_date`, `recency_days`,
  `frequency`, `monetary`, `recency_score`, `frequency_score`,
  `monetary_score`, `customer_segment_label`

## 3. Inventory & Operations
- **Heatmap:** Product × Weeks-of-Cover, colored by `movement_status`
  (Fast / Normal / Slow / Dead / Low Stock) — from `v_inventory_status`
- **Bar chart:** Top 10 slow-moving / dead-stock SKUs by value tied up
  (`closing_stock * cost_price`)
- **Alert table:** Products currently below reorder level
- **Filters:** Fabric Type, Category

**CSV sources + required fields**
- `inventory_operations_status.csv`:
  `product_id`, `product_name`, `fabric_type`, `category`, `closing_stock`,
  `reorder_level`, `avg_weekly_sales`, `weeks_of_cover`, `movement_status`,
  `cost_price`, `stock_value_tied_up`
- `inventory_operations_reorder_alerts.csv`:
  `product_id`, `product_name`, `closing_stock`, `reorder_level`,
  `movement_status`

## 4. Data Quality & Anomalies
- **Bar chart:** DQ issues by type and table — from `v_dq_summary`
- **KPI card:** Quarantine rate (%) for latest load batch
- **Scatter/strip plot:** Order revenue z-scores, anomalies highlighted in red
  — from `v_order_anomalies`
- **Purpose:** this dashboard is aimed at *you and the business owner*, not
  end customers — it's the "can we trust this number" panel, and it's the one
  most portfolio projects skip entirely.

**CSV sources + required fields**
- `data_quality_summary.csv`:
  `load_batch_id`, `table_name`, `issue_type`, `issue_count`
- `data_quality_order_anomalies.csv`:
  `order_id`, `order_date`, `order_revenue`, `z_score`, `anomaly_flag`
- `data_quality_latest_batch_metrics.csv`:
  `load_batch_id`, `total_dq_issues`, `clean_sales_rows`,
  `estimated_quarantine_rate_pct`

## Cross-dashboard design choices
- Consistent color encoding: one color = one customer segment / movement
  status across all four dashboards (Tableau color legend, shared palette)
- Global date filter action where applicable
- Every KPI card has a tooltip explaining its formula (ties back to
  `docs/kpi_definitions.md` — good interview talking point: "the dashboard is
  self-documenting")
- No 3D charts, no gauges, no pie charts with >5 slices — deliberately
  restrained chart vocabulary appropriate to a business intelligence tool,
  not a "look what Tableau can do" showcase

## Why not Power BI
Tableau chosen per project requirements; also a deliberate skill-diversification
choice — many candidates only know Power BI, and Tableau's calculated fields /
LOD expressions map more directly to the SQL window functions used in this
project (Pareto running totals, RFM percentile scoring), which is a stronger
story for a role emphasizing SQL/analytical depth over BI-tool point-and-click.
