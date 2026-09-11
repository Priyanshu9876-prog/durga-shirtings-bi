# Tableau Dashboard Design

**Data source:** connect Tableau directly to `data/clean/durga_shirtings.db`
(SQLite) via the SQLite ODBC/JDBC connector, or point it at the exported
views as CSV extracts (`data/clean/*.csv` + query results from
`sql/analytical_views.sql`) if you don't want to install an ODBC driver.

Four dashboards (sheets), one story point each — built to be walked through
in an interview in under 3 minutes.

## 1. Sales Overview
- **KPI cards (top row):** Total Revenue, MoM Growth %, AOV, Active Customers
  — from `v_monthly_sales`
- **Line chart:** Monthly revenue trend with 3-month moving average overlay
  and 3-month forecast — from `forecast_output.csv`
- **Bar chart:** Revenue by product category — from `v_product_performance`
- **Filters:** Date range (fiscal year), Sales Channel, Product Category

## 2. Customer Analytics
- **Pareto chart:** Cumulative revenue % vs. customer count (dual-axis: bar
  for individual revenue, line for cumulative %) — from `v_customer_pareto`
- **Scatter plot:** Recency (x) vs. Monetary (y), sized by Frequency, colored
  by `customer_segment_label` — from `v_customer_rfm`. This is the single
  most interview-relevant chart: it's a segmentation visual built from raw
  behavioral data, not a pre-labeled category.
- **Table:** Top 10 customers by revenue with segment and last order date
- **Filters:** Customer Segment, Region/State

## 3. Inventory & Operations
- **Heatmap:** Product × Weeks-of-Cover, colored by `movement_status`
  (Fast / Normal / Slow / Dead / Low Stock) — from `v_inventory_status`
- **Bar chart:** Top 10 slow-moving / dead-stock SKUs by value tied up
  (`closing_stock * cost_price`)
- **Alert table:** Products currently below reorder level
- **Filters:** Fabric Type, Category

## 4. Data Quality & Anomalies
- **Bar chart:** DQ issues by type and table — from `v_dq_summary`
- **KPI card:** Quarantine rate (%) for latest load batch
- **Scatter/strip plot:** Order revenue z-scores, anomalies highlighted in red
  — from `v_order_anomalies`
- **Purpose:** this dashboard is aimed at *you and the business owner*, not
  end customers — it's the "can we trust this number" panel, and it's the one
  most portfolio projects skip entirely.

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
