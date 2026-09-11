"""
clean_and_load.py
====================
ETL pipeline: raw CSV -> validated/cleaned data -> SQLite star schema.

Every row that fails a rule is NOT silently dropped - it's logged to
dq_log with a reason, then excluded from the fact table. This mirrors
how a real data team would handle it: fix what's fixable, quarantine
what isn't, and keep a paper trail.

Run:
    python clean_and_load.py
"""

import pandas as pd
import numpy as np
import sqlite3
import re
import uuid
from datetime import datetime

RAW_DIR = "../data/raw"
DB_PATH = "../data/clean/durga_shirtings.db"
LOAD_BATCH_ID = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

dq_issues = []  # collected here, written to dq_log table at the end


def log_issue(table_name, record_ref, issue_type, description):
    dq_issues.append({
        "load_batch_id": LOAD_BATCH_ID,
        "table_name": table_name,
        "record_ref": str(record_ref),
        "issue_type": issue_type,
        "description": description,
        "resolved_flag": 0,
    })


def standardize_name(name):
    """Trim, collapse whitespace, title-case — fixes 'ABC textiles  ' vs 'abc Textiles'."""
    if pd.isna(name):
        return None
    name = re.sub(r"\s+", " ", str(name)).strip()
    return name.title()


# ------------------------------------------------------------------
# 1. LOAD RAW
# ------------------------------------------------------------------
products_raw = pd.read_csv(f"{RAW_DIR}/products_master.csv")
customers_raw = pd.read_csv(f"{RAW_DIR}/customers_master.csv")
sales_raw = pd.read_csv(f"{RAW_DIR}/sales_transactions.csv")
inventory_raw = pd.read_csv(f"{RAW_DIR}/inventory_movements.csv")

# ------------------------------------------------------------------
# 2. CLEAN CUSTOMERS (dim_customer)
# ------------------------------------------------------------------
customers = customers_raw.copy()
customers["customer_name"] = customers["customer_name"].apply(standardize_name)

# duplicate customers: same standardized name -> keep first, log rest
dupe_mask = customers.duplicated(subset=["customer_name"], keep="first")
for idx in customers[dupe_mask].index:
    log_issue("dim_customer", customers.loc[idx, "customer_id"],
               "duplicate", f"Duplicate customer name after standardization: {customers.loc[idx,'customer_name']}")
customers = customers[~dupe_mask].reset_index(drop=True)

# ------------------------------------------------------------------
# 3. CLEAN PRODUCTS (dim_product) — mostly clean by construction, but
#    still validate for real-world robustness
# ------------------------------------------------------------------
products = products_raw.copy()
bad_price_mask = (products["cost_price"] <= 0) | (products["standard_price"] <= 0)
for idx in products[bad_price_mask].index:
    log_issue("dim_product", products.loc[idx, "product_id"],
               "invalid_price", "Non-positive cost or standard price")
products = products[~bad_price_mask].reset_index(drop=True)

# ------------------------------------------------------------------
# 4. CLEAN SALES (fact_sales) — this is where most real issues live
# ------------------------------------------------------------------
sales = sales_raw.copy()
n_start = len(sales)

# 4a. exact duplicate rows (same order/product/qty/price/date = re-imported row)
dupe_cols = ["order_id", "product_id", "customer_id", "quantity", "unit_price", "sale_date"]
dupe_mask = sales.duplicated(subset=dupe_cols, keep="first")
for idx in sales[dupe_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "duplicate", "Exact duplicate transaction row")
sales = sales[~dupe_mask]

# 4b. standardize customer_name_raw, then re-map to customer_id where missing
sales["customer_name_std"] = sales["customer_name_raw"].apply(standardize_name)
name_to_id = customers.set_index("customer_name")["customer_id"].to_dict()

missing_cust_mask = sales["customer_id"].isna()
recovered = 0
for idx in sales[missing_cust_mask].index:
    std_name = sales.loc[idx, "customer_name_std"]
    if std_name in name_to_id:
        sales.loc[idx, "customer_id"] = name_to_id[std_name]
        recovered += 1
    else:
        log_issue("fact_sales", sales.loc[idx, "sale_id"], "missing_value",
                   "customer_id null and could not be recovered from customer_name")

still_missing_cust = sales["customer_id"].isna()
sales = sales[~still_missing_cust]

# 4c. invalid quantity (<=0)
bad_qty_mask = sales["quantity"] <= 0
for idx in sales[bad_qty_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "invalid_quantity",
               f"Non-positive quantity: {sales.loc[idx,'quantity']}")
sales = sales[~bad_qty_mask]

# 4d. invalid price (<=0)
bad_price_mask = sales["unit_price"] <= 0
for idx in sales[bad_price_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "invalid_price",
               f"Non-positive unit price: {sales.loc[idx,'unit_price']}")
sales = sales[~bad_price_mask]

# 4e. missing product_id
missing_prod_mask = sales["product_id"].isna()
for idx in sales[missing_prod_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "missing_value", "product_id is null")
sales = sales[~missing_prod_mask]

# 4f. out-of-range / future dates (business start = 2024-01-01, load date = today)
sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
today = pd.Timestamp(datetime.now().date())
bad_date_mask = (sales["sale_date"] > today) | (sales["sale_date"] < pd.Timestamp("2024-01-01"))
for idx in sales[bad_date_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "invalid_date",
               f"Date out of expected business range: {sales.loc[idx,'sale_date']}")
sales = sales[~bad_date_mask]

# 4g. referential integrity — drop any sales row whose product isn't in cleaned products
valid_products = set(products["product_id"])
bad_ref_mask = ~sales["product_id"].isin(valid_products)
for idx in sales[bad_ref_mask].index:
    log_issue("fact_sales", sales.loc[idx, "sale_id"], "referential_integrity",
               "product_id not found in dim_product after cleaning")
sales = sales[~bad_ref_mask]

# 4h. compute revenue
sales["revenue"] = (sales["quantity"] * sales["unit_price"] * (1 - sales["discount_pct"])).round(2)

n_end = len(sales)
print(f"fact_sales: {n_start} raw rows -> {n_end} clean rows "
      f"({n_start - n_end} rows quarantined, {round((n_start-n_end)/n_start*100,1)}%)")

sales = sales.rename(columns={"sale_date": "full_date"})
# re-issue sale_id to guarantee uniqueness after dedup/cleaning steps — a
# near-duplicate pair that differs only in a recovered field (e.g. customer_id)
# can otherwise survive with a clashing original sale_id
sales = sales.reset_index(drop=True)
sales["sale_id"] = [f"S{str(i+1).zfill(6)}" for i in range(len(sales))]
sales = sales[["sale_id", "order_id", "full_date", "customer_id", "product_id",
               "quantity", "unit_price", "discount_pct", "revenue", "sales_channel"]]

# ------------------------------------------------------------------
# 5. CLEAN INVENTORY (fact_inventory_snapshot)
# ------------------------------------------------------------------
inventory = inventory_raw.copy()
neg_mask = (inventory["closing_stock"] < 0)
for idx in inventory[neg_mask].index:
    log_issue("fact_inventory_snapshot", inventory.loc[idx, "snapshot_id"],
               "invalid_quantity", "Negative closing stock")
inventory = inventory[~neg_mask]

# ------------------------------------------------------------------
# 6. BUILD dim_date FROM ALL DATES SEEN
# ------------------------------------------------------------------
all_dates = pd.to_datetime(
    pd.concat([sales["full_date"], pd.to_datetime(inventory["snapshot_date"])])
).drop_duplicates().sort_values()

dim_date = pd.DataFrame({"full_date": all_dates})
dim_date["date_id"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
dim_date["day"] = dim_date["full_date"].dt.day
dim_date["month"] = dim_date["full_date"].dt.month
dim_date["month_name"] = dim_date["full_date"].dt.strftime("%B")
dim_date["quarter"] = dim_date["full_date"].dt.quarter
dim_date["year"] = dim_date["full_date"].dt.year
dim_date["is_weekend"] = dim_date["full_date"].dt.dayofweek.isin([5, 6])
# Indian fiscal year: Apr(Y) - Mar(Y+1)
dim_date["fiscal_year"] = np.where(dim_date["month"] >= 4,
                                    dim_date["year"].astype(str) + "-" + (dim_date["year"] + 1).astype(str).str[-2:],
                                    (dim_date["year"] - 1).astype(str) + "-" + dim_date["year"].astype(str).str[-2:])
dim_date["full_date"] = dim_date["full_date"].dt.strftime("%Y-%m-%d")

date_lookup = dim_date.set_index("full_date")["date_id"].to_dict()

sales["full_date"] = pd.to_datetime(sales["full_date"]).dt.strftime("%Y-%m-%d")
sales["date_id"] = sales["full_date"].map(date_lookup)

inventory["snapshot_date"] = pd.to_datetime(inventory["snapshot_date"]).dt.strftime("%Y-%m-%d")
inventory["date_id"] = inventory["snapshot_date"].map(date_lookup)

# ------------------------------------------------------------------
# 7. WRITE CLEANED CSVs (staging artifact, useful to eyeball)
# ------------------------------------------------------------------
import os
os.makedirs("../data/clean", exist_ok=True)
customers.to_csv("../data/clean/dim_customer.csv", index=False)
products.to_csv("../data/clean/dim_product.csv", index=False)
dim_date.to_csv("../data/clean/dim_date.csv", index=False)
sales.to_csv("../data/clean/fact_sales.csv", index=False)
inventory.to_csv("../data/clean/fact_inventory_snapshot.csv", index=False)
pd.DataFrame(dq_issues).to_csv("../data/clean/dq_log.csv", index=False)

# ------------------------------------------------------------------
# 8. LOAD INTO SQLITE
# ------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
with open("../sql/schema.sql") as f:
    conn.executescript(f.read())

customers.to_sql("dim_customer", conn, if_exists="append", index=False)
products.to_sql("dim_product", conn, if_exists="append", index=False)
dim_date.to_sql("dim_date", conn, if_exists="append", index=False)
sales.to_sql("fact_sales", conn, if_exists="append", index=False)
inventory[["snapshot_id", "date_id", "product_id", "opening_stock", "received_qty",
           "sold_qty", "closing_stock", "reorder_level"]].to_sql(
    "fact_inventory_snapshot", conn, if_exists="append", index=False)
pd.DataFrame(dq_issues).to_sql("dq_log", conn, if_exists="append", index=False)

conn.commit()

# quick sanity counts
for tbl in ["dim_customer", "dim_product", "dim_date", "fact_sales", "fact_inventory_snapshot", "dq_log"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  loaded {tbl:28s}: {n} rows")

conn.close()
print(f"\nDone. Batch ID: {LOAD_BATCH_ID}")
print(f"DB at: {DB_PATH}")
