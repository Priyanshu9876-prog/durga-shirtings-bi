# Resume Bullets

Built a full-stack analytics pipeline (Python → SQL → Tableau) for a textile
trading business, processing ~7,400 transactions through an ETL layer that
validates and quarantines bad records (4.7% flagged: duplicates, invalid
quantities/prices, referential integrity failures) with a full audit trail,
loading into a 5-table SQL star schema.

Designed and implemented SQL analytical views using window functions
(running totals, NTILE, LAG) to perform Pareto/concentration analysis,
RFM-based customer segmentation, and z-score anomaly detection on order-level
revenue — surfacing actionable findings like customer revenue concentration
and at-risk high-value accounts.

Built 4 interactive Tableau dashboards (Sales, Customer Analytics, Inventory,
Data Quality) with cross-filtering and KPI tooltips tied to a documented
metric definitions layer, translating raw transactional data into
business-ready insights on growth, churn risk, and stock movement.
