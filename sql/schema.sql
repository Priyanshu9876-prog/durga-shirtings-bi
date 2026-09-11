-- ============================================================
-- schema.sql — Durga Shirtings BI Platform
-- Star schema: 1 fact table for sales, 1 for inventory snapshots,
-- 3 dimension tables, 1 audit table for data quality.
-- SQLite syntax (portable to Postgres/MySQL with minor tweaks:
-- AUTOINCREMENT -> SERIAL, etc.)
-- ============================================================

DROP TABLE IF EXISTS dq_log;
DROP TABLE IF EXISTS fact_inventory_snapshot;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;

CREATE TABLE dim_customer (
    customer_id     TEXT PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    segment         TEXT,              -- Wholesale / Retail / Export
    city            TEXT,
    state           TEXT,
    customer_since  DATE
);

CREATE TABLE dim_product (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    fabric_type     TEXT,
    category        TEXT,
    uom             TEXT,
    cost_price      REAL,
    standard_price  REAL
);

CREATE TABLE dim_date (
    date_id         INTEGER PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE NOT NULL,
    day             INTEGER,
    month           INTEGER,
    month_name      TEXT,
    quarter         INTEGER,
    year            INTEGER,
    is_weekend      BOOLEAN,
    fiscal_year     TEXT                    -- e.g. '2024-25'
);

CREATE TABLE fact_sales (
    sale_id         TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL,
    date_id         INTEGER REFERENCES dim_date(date_id),
    customer_id     TEXT REFERENCES dim_customer(customer_id),
    product_id      TEXT REFERENCES dim_product(product_id),
    quantity        REAL NOT NULL,          -- meters
    unit_price      REAL NOT NULL,
    discount_pct    REAL DEFAULT 0,
    revenue         REAL NOT NULL,          -- qty * price * (1-discount), computed in ETL
    sales_channel   TEXT,                   -- Direct / Distributor / Retail
    full_date       DATE                    -- denormalized for convenience/debugging
);

CREATE TABLE fact_inventory_snapshot (
    snapshot_id     TEXT PRIMARY KEY,
    date_id         INTEGER REFERENCES dim_date(date_id),
    product_id      TEXT REFERENCES dim_product(product_id),
    opening_stock   REAL,
    received_qty    REAL,
    sold_qty        REAL,
    closing_stock   REAL,
    reorder_level   REAL
);

CREATE TABLE dq_log (
    issue_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    load_batch_id   TEXT,
    table_name      TEXT,
    record_ref      TEXT,
    issue_type      TEXT,     -- duplicate / missing_value / invalid_quantity /
                               -- invalid_price / invalid_date / referential_integrity
    description     TEXT,
    resolved_flag   INTEGER DEFAULT 0
);

-- Indexes for common analytical query patterns
CREATE INDEX idx_fact_sales_date       ON fact_sales(date_id);
CREATE INDEX idx_fact_sales_customer   ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_product    ON fact_sales(product_id);
CREATE INDEX idx_fact_inv_date         ON fact_inventory_snapshot(date_id);
CREATE INDEX idx_fact_inv_product      ON fact_inventory_snapshot(product_id);
