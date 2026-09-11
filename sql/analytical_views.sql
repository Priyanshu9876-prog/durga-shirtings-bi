-- ============================================================
-- analytical_views.sql — Durga Shirtings BI Platform
-- Views that Tableau connects to directly. Each view answers a
-- specific business question (see docs/business_questions.md).
-- ============================================================

-- ------------------------------------------------------------
-- 1. MONTHLY SALES SUMMARY + MoM GROWTH
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_monthly_sales;
CREATE VIEW v_monthly_sales AS
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
        d.fiscal_year,
        SUM(f.revenue)                     AS total_revenue,
        SUM(f.quantity)                    AS total_qty_sold,
        COUNT(DISTINCT f.order_id)         AS total_orders,
        COUNT(DISTINCT f.customer_id)      AS active_customers,
        ROUND(SUM(f.revenue) * 1.0 / COUNT(DISTINCT f.order_id), 2) AS avg_order_value
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month, d.month_name, d.fiscal_year
)
SELECT
    *,
    ROUND(
      100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY year, month))
      / NULLIF(LAG(total_revenue) OVER (ORDER BY year, month), 0), 2
    ) AS mom_revenue_growth_pct
FROM monthly
ORDER BY year, month;

-- ------------------------------------------------------------
-- 2. PRODUCT PERFORMANCE
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_product_performance;
CREATE VIEW v_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.fabric_type,
    p.category,
    SUM(f.revenue)                 AS total_revenue,
    SUM(f.quantity)                AS total_qty_sold,
    COUNT(DISTINCT f.order_id)     AS order_count,
    COUNT(DISTINCT f.customer_id)  AS distinct_customers,
    ROUND(SUM(f.revenue) / NULLIF(SUM(f.quantity),0), 2) AS avg_realized_price_per_unit,
    ROUND(SUM(f.revenue) - SUM(f.quantity * p.cost_price), 2) AS gross_margin
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.fabric_type, p.category;

-- ------------------------------------------------------------
-- 3. PARETO ANALYSIS (80/20 — which customers drive revenue)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_customer_pareto;
CREATE VIEW v_customer_pareto AS
WITH customer_revenue AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        SUM(f.revenue) AS customer_revenue
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name, c.segment
),
ranked AS (
    SELECT
        *,
        SUM(customer_revenue) OVER () AS total_revenue,
        SUM(customer_revenue) OVER (ORDER BY customer_revenue DESC
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_revenue,
        ROW_NUMBER() OVER (ORDER BY customer_revenue DESC) AS revenue_rank
    FROM customer_revenue
)
SELECT
    *,
    ROUND(100.0 * customer_revenue / total_revenue, 2)     AS pct_of_total_revenue,
    ROUND(100.0 * running_revenue / total_revenue, 2)      AS cumulative_pct_of_revenue,
    CASE WHEN 100.0 * running_revenue / total_revenue <= 80 THEN 'Top 80% (Vital Few)'
         ELSE 'Bottom 20% (Trivial Many)' END              AS pareto_bucket
FROM ranked
ORDER BY customer_revenue DESC;

-- ------------------------------------------------------------
-- 4. CUSTOMER SEGMENTATION (RFM-lite: Recency, Frequency, Monetary)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_customer_rfm;
CREATE VIEW v_customer_rfm AS
WITH cust_stats AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        MAX(f.full_date)                       AS last_order_date,
        JULIANDAY((SELECT MAX(full_date) FROM fact_sales)) - JULIANDAY(MAX(f.full_date)) AS recency_days,
        COUNT(DISTINCT f.order_id)             AS frequency,
        SUM(f.revenue)                         AS monetary
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name, c.segment
),
scored AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- lower recency_days = better = higher score after invert
        NTILE(4) OVER (ORDER BY frequency ASC)      AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC)       AS m_score
    FROM cust_stats
)
SELECT
    *,
    (5 - r_score) AS recency_score,     -- invert so 4 = most recent
    f_score        AS frequency_score,
    m_score        AS monetary_score,
    CASE
        WHEN recency_days > 90 THEN 'Inactive (90+ days)'
        WHEN (5 - r_score) >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champion'
        WHEN (5 - r_score) >= 3 AND f_score < 3 THEN 'New / Occasional'
        WHEN (5 - r_score) < 3 AND m_score >= 3 THEN 'At Risk (was high value)'
        ELSE 'Regular'
    END AS customer_segment_label
FROM scored
ORDER BY monetary DESC;

-- ------------------------------------------------------------
-- 5. INVENTORY AGING / FAST-SLOW MOVERS / LOW STOCK
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_inventory_status;
CREATE VIEW v_inventory_status AS
WITH latest_snapshot AS (
    SELECT product_id, MAX(date_id) AS max_date_id
    FROM fact_inventory_snapshot
    GROUP BY product_id
),
latest AS (
    SELECT s.*
    FROM fact_inventory_snapshot s
    JOIN latest_snapshot ls ON s.product_id = ls.product_id AND s.date_id = ls.max_date_id
),
velocity AS (
    -- avg weekly sales velocity over last 8 available snapshots per product
    SELECT
        product_id,
        AVG(sold_qty) AS avg_weekly_sales
    FROM (
        SELECT
            product_id, sold_qty,
            ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY date_id DESC) AS rn
        FROM fact_inventory_snapshot
    )
    WHERE rn <= 8
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.fabric_type,
    p.category,
    l.closing_stock,
    l.reorder_level,
    v.avg_weekly_sales,
    ROUND(l.closing_stock / NULLIF(v.avg_weekly_sales, 0), 1) AS weeks_of_cover,
    CASE
        WHEN l.closing_stock <= l.reorder_level THEN 'Low Stock - Reorder'
        WHEN v.avg_weekly_sales = 0 OR v.avg_weekly_sales IS NULL THEN 'Dead Stock'
        WHEN l.closing_stock / NULLIF(v.avg_weekly_sales,0) > 8 THEN 'Slow Moving (>8 wks cover)'
        WHEN l.closing_stock / NULLIF(v.avg_weekly_sales,0) < 2 THEN 'Fast Moving (<2 wks cover)'
        ELSE 'Normal'
    END AS movement_status
FROM latest l
JOIN dim_product p ON l.product_id = p.product_id
LEFT JOIN velocity v ON l.product_id = v.product_id;

-- ------------------------------------------------------------
-- 6. ANOMALY DETECTION (order-level revenue outliers, z-score method)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_order_anomalies;
CREATE VIEW v_order_anomalies AS
WITH order_totals AS (
    SELECT
        order_id,
        MIN(full_date) AS order_date,
        SUM(revenue)   AS order_revenue
    FROM fact_sales
    GROUP BY order_id
),
stats AS (
    SELECT
        AVG(order_revenue) AS mean_rev,
        -- population stddev via SQLite (no STDDEV built-in): compute manually
        SQRT(AVG((order_revenue - (SELECT AVG(order_revenue) FROM order_totals)) *
                 (order_revenue - (SELECT AVG(order_revenue) FROM order_totals)))) AS std_rev
    FROM order_totals
)
SELECT
    o.*,
    ROUND((o.order_revenue - s.mean_rev) / NULLIF(s.std_rev, 0), 2) AS z_score,
    CASE WHEN ABS((o.order_revenue - s.mean_rev) / NULLIF(s.std_rev, 0)) >= 3 THEN 'Anomaly (|z|>=3)'
         WHEN ABS((o.order_revenue - s.mean_rev) / NULLIF(s.std_rev, 0)) >= 2 THEN 'Watch (|z|>=2)'
         ELSE 'Normal' END AS anomaly_flag
FROM order_totals o
CROSS JOIN stats s
ORDER BY z_score DESC;

-- ------------------------------------------------------------
-- 7. DATA QUALITY SUMMARY (for Tableau's DQ panel)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_dq_summary;
CREATE VIEW v_dq_summary AS
SELECT
    load_batch_id,
    table_name,
    issue_type,
    COUNT(*) AS issue_count
FROM dq_log
GROUP BY load_batch_id, table_name, issue_type
ORDER BY issue_count DESC;

-- ------------------------------------------------------------
-- 8. SIMPLE FORECAST BASIS (3-month moving average — the actual
--    forecast math is done in Python/statsmodels; this view just
--    supplies the clean monthly series it needs)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_monthly_revenue_series;
CREATE VIEW v_monthly_revenue_series AS
SELECT
    d.year, d.month, d.month_name,
    SUM(f.revenue) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;
