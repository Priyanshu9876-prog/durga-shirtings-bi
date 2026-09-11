"""
generate_synthetic_data.py
============================
Generates CLEARLY LABELED SYNTHETIC data that structurally represents a
textile trading business (fabric SKUs, meter-based units, wholesale/
retail/export customer types).

This data does NOT represent actual Durga Shirtings Pvt Ltd customers,
products, prices, or financials. It exists to let the ETL/SQL/Tableau
pipeline be built and tested. Replace files in /data/raw/ with real
company exports (matching these column headers) to go live.

Intentional data quality issues are injected on purpose so the ETL
layer in etl/clean_and_load.py has real problems to detect and fix:
  - duplicate transaction rows
  - missing customer / product references
  - negative or zero quantities
  - negative or absurd prices
  - inconsistent customer name casing/spacing ("ABC Textiles" vs "abc textiles ")
  - a few future-dated / out-of-range dates
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

OUT_DIR = "../data/raw"

# ---------------------------------------------------------------
# 1. Product master (fabric catalog — generic textile categories)
# ---------------------------------------------------------------
FABRIC_TYPES = ["Cotton", "Poly-Cotton", "Linen", "Rayon", "Viscose", "Cotton-Lycra", "Polyester"]
CATEGORIES = ["Shirting", "Suiting", "Furnishing", "Dress Material"]

products = []
pid = 1
for fabric in FABRIC_TYPES:
    for cat in CATEGORIES:
        for variant in range(1, 4):  # 3 SKUs per fabric/category combo
            cost = round(np.random.uniform(60, 220), 2)
            products.append({
                "product_id": f"P{pid:04d}",
                "product_name": f"{fabric} {cat} #{variant}",
                "fabric_type": fabric,
                "category": cat,
                "uom": "meters",
                "cost_price": cost,
                "standard_price": round(cost * np.random.uniform(1.25, 1.6), 2),
            })
            pid += 1

products_df = pd.DataFrame(products)

# ---------------------------------------------------------------
# 2. Customer master (generic wholesale/retail/export archetypes)
# ---------------------------------------------------------------
CITIES = [("Mumbai", "Maharashtra"), ("Surat", "Gujarat"), ("Delhi", "Delhi"),
          ("Bengaluru", "Karnataka"), ("Ludhiana", "Punjab"), ("Ahmedabad", "Gujarat"),
          ("Kolkata", "West Bengal"), ("Jaipur", "Rajasthan")]
SEGMENTS = ["Wholesale", "Retail", "Export"]
NAME_STEMS = ["Shree", "Om", "Krishna", "Vardhman", "Ganesh", "Balaji", "New India",
              "United", "National", "Royal", "Prime", "Sun", "Star", "City", "Metro"]
NAME_SUFFIX = ["Textiles", "Traders", "Fabrics", "Garments", "Enterprises", "Impex", "Mills"]

customers = []
cust_id = 1
seen_names = set()
while len(customers) < 60:
    name = f"{random.choice(NAME_STEMS)} {random.choice(NAME_SUFFIX)}"
    if name in seen_names:
        continue
    seen_names.add(name)
    city, state = random.choice(CITIES)
    since = datetime(2021, 1, 1) + timedelta(days=random.randint(0, 1400))
    customers.append({
        "customer_id": f"C{cust_id:04d}",
        "customer_name": name,
        "segment": random.choice(SEGMENTS),
        "city": city,
        "state": state,
        "customer_since": since.strftime("%Y-%m-%d"),
    })
    cust_id += 1

customers_df = pd.DataFrame(customers)

# ---------------------------------------------------------------
# 3. Sales transactions (2 years, seasonal pattern typical of
#    textiles: festive/wedding season spikes Oct-Feb)
# ---------------------------------------------------------------
start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 12, 31)
all_days = pd.date_range(start_date, end_date, freq="D")

SEASONAL_MONTH_WEIGHT = {1: 1.1, 2: 1.3, 3: 0.9, 4: 0.7, 5: 0.6, 6: 0.6,
                          7: 0.7, 8: 0.8, 9: 1.0, 10: 1.4, 11: 1.5, 12: 1.3}

CHANNELS = ["Direct", "Distributor", "Retail"]

sales_rows = []
order_counter = 1
for day in all_days:
    weight = SEASONAL_MONTH_WEIGHT[day.month]
    n_orders_today = np.random.poisson(4 * weight)
    for _ in range(n_orders_today):
        cust = customers_df.sample(1).iloc[0]
        n_lines = random.randint(1, 4)
        order_id = f"ORD{order_counter:06d}"
        order_counter += 1
        for _ in range(n_lines):
            prod = products_df.sample(1).iloc[0]
            qty = random.randint(20, 500)  # meters
            price = prod["standard_price"] * np.random.uniform(0.9, 1.05)
            discount = random.choice([0, 0, 0, 0.05, 0.1])

            # inconsistent name formatting injected ~15% of the time
            cust_name = cust["customer_name"]
            if random.random() < 0.15:
                variant = random.choice([cust_name.upper(), cust_name.lower(),
                                          f" {cust_name}  ", cust_name.replace(" ", "  ")])
                cust_name = variant

            sales_rows.append({
                "order_id": order_id,
                "sale_date": day.strftime("%Y-%m-%d"),
                "customer_id": cust["customer_id"],
                "customer_name_raw": cust_name,
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": round(price, 2),
                "discount_pct": discount,
                "sales_channel": random.choice(CHANNELS),
            })

sales_df = pd.DataFrame(sales_rows)
sales_df.insert(0, "sale_id", [f"S{str(i+1).zfill(6)}" for i in range(len(sales_df))])

# ---- inject realistic data quality problems ----

# a) duplicate rows (~2%)
dupe_sample = sales_df.sample(frac=0.02, random_state=1)
sales_df = pd.concat([sales_df, dupe_sample], ignore_index=True)

# b) negative / zero quantities (~1%)
bad_qty_idx = sales_df.sample(frac=0.01, random_state=2).index
sales_df.loc[bad_qty_idx, "quantity"] = sales_df.loc[bad_qty_idx, "quantity"] * -1

# c) null customer_id (~1.5%) - simulates missing lookups at POS
null_cust_idx = sales_df.sample(frac=0.015, random_state=3).index
sales_df.loc[null_cust_idx, "customer_id"] = None

# d) absurd / negative prices (~0.8%)
bad_price_idx = sales_df.sample(frac=0.008, random_state=4).index
sales_df.loc[bad_price_idx, "unit_price"] = sales_df.loc[bad_price_idx, "unit_price"] * -1

# e) a handful of future-dated / bad dates (~0.3%)
bad_date_idx = sales_df.sample(frac=0.003, random_state=5).index
sales_df.loc[bad_date_idx, "sale_date"] = "2026-11-30"  # future date, out of range

# f) missing product_id (~1%)
null_prod_idx = sales_df.sample(frac=0.01, random_state=6).index
sales_df.loc[null_prod_idx, "product_id"] = None

sales_df = sales_df.sample(frac=1, random_state=7).reset_index(drop=True)  # shuffle

# ---------------------------------------------------------------
# 4. Inventory movements (weekly snapshots per product)
# ---------------------------------------------------------------
snap_dates = pd.date_range(start_date, end_date, freq="W-MON")
inv_rows = []
snap_id = 1
stock_state = {p: random.randint(500, 3000) for p in products_df["product_id"]}

for snap_date in snap_dates:
    week_sales = sales_df[
        (pd.to_datetime(sales_df["sale_date"], errors="coerce") >= snap_date) &
        (pd.to_datetime(sales_df["sale_date"], errors="coerce") < snap_date + timedelta(days=7))
    ]
    sold_by_product = week_sales.groupby("product_id")["quantity"].sum()

    for pid_ in products_df["product_id"]:
        opening = stock_state[pid_]
        received = random.choice([0, 0, 0, random.randint(200, 1000)])
        sold = max(int(sold_by_product.get(pid_, 0)), 0)
        closing = max(opening + received - sold, 0)
        stock_state[pid_] = closing
        inv_rows.append({
            "snapshot_id": f"INV{snap_id:06d}",
            "snapshot_date": snap_date.strftime("%Y-%m-%d"),
            "product_id": pid_,
            "opening_stock": opening,
            "received_qty": received,
            "sold_qty": sold,
            "closing_stock": closing,
            "reorder_level": 300,
        })
        snap_id += 1

inventory_df = pd.DataFrame(inv_rows)

# ---------------------------------------------------------------
# 5. Introduce a few duplicate customer master rows (data entry dupes)
# ---------------------------------------------------------------
dup_customers = customers_df.sample(3, random_state=8).copy()
dup_customers["customer_name"] = dup_customers["customer_name"].str.upper()
customers_df = pd.concat([customers_df, dup_customers], ignore_index=True)

# ---------------------------------------------------------------
# Write files
# ---------------------------------------------------------------
import os
os.makedirs(OUT_DIR, exist_ok=True)
products_df.to_csv(f"{OUT_DIR}/products_master.csv", index=False)
customers_df.to_csv(f"{OUT_DIR}/customers_master.csv", index=False)
sales_df.to_csv(f"{OUT_DIR}/sales_transactions.csv", index=False)
inventory_df.to_csv(f"{OUT_DIR}/inventory_movements.csv", index=False)

print(f"products_master.csv      : {len(products_df)} rows")
print(f"customers_master.csv     : {len(customers_df)} rows")
print(f"sales_transactions.csv   : {len(sales_df)} rows")
print(f"inventory_movements.csv  : {len(inventory_df)} rows")
print("\nSYNTHETIC DATA — for pipeline development only. Replace with real exports in production.")
