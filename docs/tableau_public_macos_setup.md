# Tableau Public Setup (macOS) — Complete Dashboard Build

This guide converts the repository's prepared Tableau extracts into a complete
Tableau Public workbook with four dashboards.

## 1) Regenerate Tableau extracts

From repository root:

```bash
python3 -m pip install -r requirements.txt
python3 etl/prepare_tableau_assets.py
```

Optional full refresh:

```bash
python3 etl/prepare_tableau_assets.py --force-etl --force-forecast
```

Expected output folder:

`data/clean/tableau_extracts/`

## 2) Open Tableau Public and add all CSV data sources

1. Open Tableau Public on macOS.
2. Start a blank workbook.
3. For each CSV below, use `Data > New Data Source > Text File`:
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

Use files from:
`/home/runner/work/durga-shirtings-bi/durga-shirtings-bi/data/clean/tableau_extracts/`

If you are running locally on your own machine, use your local clone path with
the same relative folder `data/clean/tableau_extracts/`.

## 3) Build worksheets and dashboards

Follow the executable workbook template:

- `tableau/tableau_public_workbook_spec.md`

That file defines:

- worksheet names,
- data source mapping,
- field placements (Rows/Columns/Marks/Detail),
- calculated fields,
- filters,
- dashboard layout,
- formatting standards.

The four required dashboards are:

1. `Sales Overview`
2. `Customer Analytics`
3. `Inventory & Operations`
4. `Data Quality & Anomalies`

## 4) Save and publish workbook

1. Save local workbook as `.twb` (recommended name: `durga_shirtings_bi_dashboard.twb`).
2. Use `File > Save to Tableau Public As...` to publish.
3. Keep the `.twb` in versioned local project artifacts if you want repeatable manual rebuilds.

## 5) Troubleshooting local path changes

If Tableau cannot find a CSV (after moving/renaming project folder):

1. In Tableau, open `Data` menu and choose the affected data source.
2. Click `Data Source` tab.
3. Use `Text File` connection and repoint to the new path for that CSV.
4. Repeat for each source showing a broken path.
5. Re-save the workbook.

Quick checks:

- Verify `etl/prepare_tableau_assets.py` ran successfully.
- Verify all 10 CSV files exist in `data/clean/tableau_extracts/`.
- Ensure file names are unchanged from the template specification.

