# Key Business Questions & Insights

This project is organized around business questions first, dashboards second —
each question below maps to a specific SQL view and a specific Tableau sheet.
All numeric findings are from the **synthetic dataset** and are structural
examples of the kind of insight the pipeline surfaces, not real Durga
Shirtings financials.

## Sales

**Q: Is revenue growing, and where are the swings?**
`v_monthly_sales` shows a clear seasonal pattern — Oct–Feb (festive/wedding
season) runs ~40-50% above the May–July trough, consistent with known
textile industry seasonality. MoM growth is volatile month to month, which is
exactly why the forecast script reports its R² honestly instead of pretending
a straight trend line fits.

**Q: Which products actually make money vs. just move volume?**
`v_product_performance` separates `total_qty_sold` from `gross_margin` — a
product can rank high on volume and low on margin (common with heavily
discounted SKUs), which is the kind of thing raw revenue tables hide.

## Customers

**Q: Are we dependent on a small number of customers?**
`v_customer_pareto` answers this directly with a running cumulative % —
in the sample data, roughly the top ~30% of customers by count drive 80% of
revenue, a classic Pareto pattern worth flagging to leadership as concentration
risk.

**Q: Who's about to churn?**
`v_customer_rfm` flags "At Risk" customers — historically high monetary value
but recency > typical reorder cycle. This is the list Sales should call first.

## Inventory

**Q: What should we reorder now, and what's dead stock tying up capital?**
`v_inventory_status` computes weeks-of-cover per SKU from actual sales
velocity (not a fixed threshold), so "low stock" means low *relative to how
fast it sells*, not just a small number.

## Data Quality

**Q: How much of our raw data can we actually trust?**
The ETL quarantines ~4.7% of raw sales rows (duplicates, invalid quantities/
prices, missing references, bad dates) and logs every one with a reason in
`dq_log` — this is the artifact that proves the "clean data" claim rather than
asserting it.

## Anomalies

**Q: Which orders look like errors or one-off events worth investigating?**
`v_order_anomalies` flags orders with `|z-score| >= 3` — statistically unusual
order sizes. In a real deployment these would route to a manual review queue
(could be a bulk export order, a data entry error, or a fraud flag).

## Forecasting

**Q: What's a reasonable revenue expectation for the next quarter?**
The 3-month moving average is the practical, defensible forecast baseline for
this data volume; the linear trend is shown alongside it specifically to
demonstrate — and be honest about — its limitation (low R² because seasonality,
not a linear trend, dominates the series). Interview-ready explanation: "I could
extend this to a seasonal-naive or SARIMA model, but chose to show the
simpler method's honest limits rather than force-fit something more complex
than the data volume justifies."
