# Tableau Workbook Specification Template (Tableau Public)

This is a **Tableau workbook specification/template** (not a `.twb` binary/XML).
Use it to build a portable workbook in Tableau Public from the CSV extracts in
`data/clean/tableau_extracts/`.

## Workbook metadata

- Workbook name: `durga_shirtings_bi_dashboard`
- Dashboard set:
  1. `Sales Overview`
  2. `Customer Analytics`
  3. `Inventory & Operations`
  4. `Data Quality & Anomalies`
- Tableau version target: Tableau Public Desktop (macOS)

## Data sources to add (Text File)

1. `sales_overview_monthly.csv`
2. `sales_overview_product_performance.csv`
3. `sales_overview_forecast_output.csv`
4. `customer_analytics_pareto.csv`
5. `customer_analytics_rfm.csv`
6. `inventory_operations_status.csv`
7. `inventory_operations_reorder_alerts.csv`
8. `data_quality_summary.csv`
9. `data_quality_order_anomalies.csv`
10. `data_quality_latest_batch_metrics.csv`

Use `Data > New Data Source > Text File` for each file.

---

## Reusable calculated fields

Create these in the worksheet's active data source when needed:

1. `Month Label`
   - Formula:
     ```
     STR([year]) + "-" + RIGHT("00" + STR([month]), 2) + " " + [month_name]
     ```
2. `Revenue (Actual Only)`
   - Formula:
     ```
     IF [is_forecast] = 0 THEN [total_revenue] END
     ```
3. `Revenue (Forecast Only)`
   - Formula:
     ```
     IF [is_forecast] = 1 THEN [forecast_revenue] END
     ```
4. `Reorder Gap`
   - Formula:
     ```
     [reorder_level] - [closing_stock]
     ```
5. `Anomaly Flag Label`
   - Formula:
     ```
     IF [anomaly_flag] = 1 THEN "Anomaly" ELSE "Normal" END
     ```

---

## Dashboard 1: Sales Overview

### Worksheets

1. `SO - KPI Revenue`
   - Data source: `sales_overview_monthly.csv`
   - Marks: Text
   - Text: `SUM(total_revenue)`
   - Filters: `fiscal_year`

2. `SO - KPI Orders`
   - Data source: `sales_overview_monthly.csv`
   - Marks: Text
   - Text: `SUM(total_orders)`
   - Filters: `fiscal_year`

3. `SO - Monthly Revenue Trend`
   - Data source: `sales_overview_monthly.csv`
   - Columns: `month_name`
   - Rows: `SUM(total_revenue)`
   - Marks: Line
   - Filters: `fiscal_year`

4. `SO - Product Revenue`
   - Data source: `sales_overview_product_performance.csv`
   - Columns: `category`
   - Rows: `SUM(total_revenue)`
   - Marks: Bar
   - Sort: descending by revenue

5. `SO - Forecast vs Actual`
   - Data source: `sales_overview_forecast_output.csv`
   - Columns: `month_name`
   - Rows: `SUM(Revenue (Actual Only))` and `SUM(Revenue (Forecast Only))`
   - Marks: Dual line
   - Color: Actual = blue, Forecast = orange dashed

### Dashboard layout

- Name: `Sales Overview`
- Size: Automatic
- Top row: KPI sheets (`SO - KPI Revenue`, `SO - KPI Orders`)
- Middle row: `SO - Monthly Revenue Trend`
- Bottom row: `SO - Product Revenue` (left), `SO - Forecast vs Actual` (right)
- Show filters on right panel: `fiscal_year`, `category`

---

## Dashboard 2: Customer Analytics

### Worksheets

1. `CA - Pareto Revenue`
   - Data source: `customer_analytics_pareto.csv`
   - Columns: `customer_name`
   - Rows: `SUM(customer_revenue)` and `MAX(cumulative_pct_of_revenue)` (dual axis)
   - Marks: Bar (revenue) + Line (cumulative %)

2. `CA - RFM Scatter`
   - Data source: `customer_analytics_rfm.csv`
   - Columns: `recency_days`
   - Rows: `monetary`
   - Size: `frequency`
   - Color: `customer_segment_label`
   - Detail: `customer_name`

3. `CA - Top Customers Table`
   - Data source: `customer_analytics_rfm.csv`
   - Rows: `customer_name`
   - Text: `monetary`, `frequency`, `recency_days`, `customer_segment_label`
   - Sort: descending by `monetary`
   - Filter: Top 10 by `monetary`

### Dashboard layout

- Name: `Customer Analytics`
- Left: `CA - Pareto Revenue`
- Right top: `CA - RFM Scatter`
- Right bottom: `CA - Top Customers Table`
- Filters shown: `segment`, `customer_segment_label`

---

## Dashboard 3: Inventory & Operations

### Worksheets

1. `IO - Stock Coverage Heatmap`
   - Data source: `inventory_operations_status.csv`
   - Columns: `product_name`
   - Rows: `weeks_of_cover`
   - Marks: Square
   - Color: `movement_status`
   - Detail: `fabric_type`, `category`

2. `IO - Value Tied Up`
   - Data source: `inventory_operations_status.csv`
   - Columns: `product_name`
   - Rows: `SUM(stock_value_tied_up)`
   - Marks: Bar
   - Filter: `movement_status` in (`Slow`, `Dead`, `Low Stock`)
   - Sort: descending by stock value

3. `IO - Reorder Alerts`
   - Data source: `inventory_operations_reorder_alerts.csv`
   - Rows: `product_name`
   - Text: `closing_stock`, `reorder_level`, `movement_status`, `Reorder Gap`
   - Sort: descending by `Reorder Gap`

### Dashboard layout

- Name: `Inventory & Operations`
- Top: `IO - Stock Coverage Heatmap`
- Bottom left: `IO - Value Tied Up`
- Bottom right: `IO - Reorder Alerts`
- Filters shown: `fabric_type`, `category`, `movement_status`

---

## Dashboard 4: Data Quality & Anomalies

### Worksheets

1. `DQ - Issues by Type`
   - Data source: `data_quality_summary.csv`
   - Columns: `issue_type`
   - Rows: `SUM(issue_count)`
   - Color: `table_name`
   - Marks: Bar

2. `DQ - Quarantine Rate KPI`
   - Data source: `data_quality_latest_batch_metrics.csv`
   - Marks: Text
   - Text: `AVG(estimated_quarantine_rate_pct)`

3. `DQ - Revenue Anomaly Scatter`
   - Data source: `data_quality_order_anomalies.csv`
   - Columns: `order_date`
   - Rows: `order_revenue`
   - Color: `Anomaly Flag Label`
   - Detail: `order_id`, `z_score`
   - Suggested color mapping: Anomaly = red, Normal = gray

### Dashboard layout

- Name: `Data Quality & Anomalies`
- Top left: `DQ - Issues by Type`
- Top right: `DQ - Quarantine Rate KPI`
- Full bottom row: `DQ - Revenue Anomaly Scatter`
- Filters shown: `table_name`, `anomaly_flag`

---

## Formatting standards

- Font: Tableau Book / Tableau Semibold (titles)
- Number formatting:
  - Revenue/value fields: currency with 0 decimals
  - Percentages: 1 decimal with `%`
  - Counts: whole number with thousands separator
- Tooltip standard:
  - Include metric name, value, and source field
  - Keep line count under 6
- Color consistency:
  - Keep `movement_status` and `customer_segment_label` colors consistent across all sheets

