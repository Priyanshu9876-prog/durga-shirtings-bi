"""
forecast.py
=============
Deliberately simple forecasting — a 3-month moving average AND a linear
trend line, not ARIMA/Prophet. For a business this size, and for an
interview, "I chose simple, explainable methods appropriate to the data
volume, and I can tell you why I didn't reach for Prophet" is a stronger
answer than a black-box model on 24 months of data.

Writes forecast_output.csv (actuals + moving avg + trend forecast for
next 3 months) which Tableau connects to for the trend chart.
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import LinearRegression

conn = sqlite3.connect("../data/clean/durga_shirtings.db")
df = pd.read_sql("SELECT * FROM v_monthly_revenue_series", conn)
conn.close()

df["period_index"] = range(len(df))
df["moving_avg_3m"] = df["total_revenue"].rolling(window=3, min_periods=1).mean().round(2)

# linear trend on existing data
X = df[["period_index"]]
y = df["total_revenue"]
model = LinearRegression().fit(X, y)

future_periods = pd.DataFrame({"period_index": range(len(df), len(df) + 3)})
future_preds = model.predict(future_periods)

r2 = model.score(X, y)
print(f"Linear trend R^2: {r2:.3f}  (low R^2 => seasonality dominates, "
      f"flag this honestly rather than over-claiming forecast accuracy)")

future_df = pd.DataFrame({
    "year": None, "month": None, "month_name": ["Forecast+1", "Forecast+2", "Forecast+3"],
    "total_revenue": None,
    "moving_avg_3m": None,
    "period_index": future_periods["period_index"],
    "forecast_revenue": future_preds.round(2),
    "is_forecast": True,
})

df["forecast_revenue"] = None
df["is_forecast"] = False

output = pd.concat([df, future_df], ignore_index=True)
output.to_csv("../data/clean/forecast_output.csv", index=False)
print("Wrote ../data/clean/forecast_output.csv")
print(output.tail(6).to_string())
