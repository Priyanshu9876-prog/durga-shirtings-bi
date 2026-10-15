"""
prepare_tableau_assets.py
=========================
Reproducible workflow to prepare Tableau-ready CSV extracts.

What it does:
1) Ensures raw input CSV files exist (generates synthetic data if missing)
2) Runs ETL when needed to (re)create SQLite warehouse
3) Applies analytical SQL views
4) Runs forecast generation when needed
5) Exports Tableau-friendly CSVs for all dashboard areas

Run from repository root:
    python etl/prepare_tableau_assets.py
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd


REQUIRED_RAW_FILES = [
    "products_master.csv",
    "customers_master.csv",
    "sales_transactions.csv",
    "inventory_movements.csv",
]


def run_etl_script(repo_root: Path, script_name: str) -> None:
    etl_dir = repo_root / "etl"
    print(f"-> Running etl/{script_name}")
    subprocess.run([sys.executable, script_name], cwd=etl_dir, check=True)


def ensure_raw_inputs(repo_root: Path) -> None:
    raw_dir = repo_root / "data" / "raw"
    missing = [f for f in REQUIRED_RAW_FILES if not (raw_dir / f).exists()]

    if not missing:
        return

    print("Raw input files missing:", ", ".join(missing))
    print("Generating synthetic inputs so the workflow can proceed...")
    run_etl_script(repo_root, "generate_synthetic_data.py")

    still_missing = [f for f in REQUIRED_RAW_FILES if not (raw_dir / f).exists()]
    if still_missing:
        raise FileNotFoundError(
            "Missing required raw input files after synthetic-data generation: "
            + ", ".join(still_missing)
        )


def ensure_database(repo_root: Path, force_etl: bool) -> bool:
    db_path = repo_root / "data" / "clean" / "durga_shirtings.db"
    should_run_etl = force_etl or (not db_path.exists())

    if should_run_etl:
        reason = "--force-etl was provided" if force_etl else "SQLite database is missing"
        print(f"{reason}; running ETL clean/load...")
        run_etl_script(repo_root, "clean_and_load.py")

    if not db_path.exists():
        raise FileNotFoundError(f"Expected SQLite database not found: {db_path}")

    return should_run_etl


def apply_analytical_views(repo_root: Path) -> None:
    db_path = repo_root / "data" / "clean" / "durga_shirtings.db"
    views_sql_path = repo_root / "sql" / "analytical_views.sql"

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(views_sql_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()

    print(f"Applied analytical views from {views_sql_path}")


def ensure_forecast(repo_root: Path, force_forecast: bool, etl_ran: bool) -> Path:
    forecast_path = repo_root / "data" / "clean" / "forecast_output.csv"
    should_run_forecast = force_forecast or etl_ran or (not forecast_path.exists())

    if should_run_forecast:
        reason = (
            "--force-forecast was provided"
            if force_forecast
            else "ETL was refreshed or forecast output is missing"
        )
        print(f"{reason}; running forecast...")
        run_etl_script(repo_root, "forecast.py")

    if not forecast_path.exists():
        raise FileNotFoundError(f"Expected forecast output not found: {forecast_path}")

    return forecast_path


def export_tableau_extracts(repo_root: Path, output_dir: Path) -> None:
    db_path = repo_root / "data" / "clean" / "durga_shirtings.db"
    output_dir.mkdir(parents=True, exist_ok=True)

    export_queries = {
        "sales_overview_monthly.csv": """
            SELECT *
            FROM v_monthly_sales
            ORDER BY year, month
        """,
        "sales_overview_product_performance.csv": """
            SELECT *
            FROM v_product_performance
            ORDER BY total_revenue DESC
        """,
        "customer_analytics_pareto.csv": """
            SELECT *
            FROM v_customer_pareto
            ORDER BY customer_revenue DESC
        """,
        "customer_analytics_rfm.csv": """
            SELECT *
            FROM v_customer_rfm
            ORDER BY monetary DESC
        """,
        "inventory_operations_status.csv": """
            SELECT
                s.*,
                p.cost_price,
                ROUND(s.closing_stock * p.cost_price, 2) AS stock_value_tied_up
            FROM v_inventory_status s
            JOIN dim_product p ON s.product_id = p.product_id
            ORDER BY stock_value_tied_up DESC
        """,
        "inventory_operations_reorder_alerts.csv": """
            SELECT *
            FROM v_inventory_status
            WHERE closing_stock <= reorder_level
            ORDER BY (reorder_level - closing_stock) DESC
        """,
        "data_quality_summary.csv": """
            SELECT *
            FROM v_dq_summary
            ORDER BY issue_count DESC
        """,
        "data_quality_order_anomalies.csv": """
            SELECT *
            FROM v_order_anomalies
            ORDER BY ABS(z_score) DESC
        """,
        "data_quality_latest_batch_metrics.csv": """
            WITH latest_batch AS (
                SELECT load_batch_id
                FROM dq_log
                WHERE load_batch_id IS NOT NULL
                ORDER BY issue_id DESC
                LIMIT 1
            ),
            issues AS (
                SELECT COUNT(*) AS total_dq_issues
                FROM dq_log
                WHERE load_batch_id = (SELECT load_batch_id FROM latest_batch)
            ),
            clean_sales AS (
                SELECT COUNT(*) AS clean_sales_rows
                FROM fact_sales
            )
            SELECT
                (SELECT load_batch_id FROM latest_batch) AS load_batch_id,
                i.total_dq_issues,
                c.clean_sales_rows,
                ROUND(
                    (i.total_dq_issues * 100.0) /
                    NULLIF(i.total_dq_issues + c.clean_sales_rows, 0),
                    2
                ) AS estimated_quarantine_rate_pct
            FROM issues i
            CROSS JOIN clean_sales c
        """,
    }

    conn = sqlite3.connect(db_path)
    try:
        for filename, query in export_queries.items():
            df = pd.read_sql_query(query, conn)
            out_path = output_dir / filename
            df.to_csv(out_path, index=False)
            print(f"Exported {out_path.relative_to(repo_root)} ({len(df)} rows)")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Tableau-ready dashboard extracts")
    parser.add_argument(
        "--force-etl",
        action="store_true",
        help="Force rerun of clean_and_load.py even when the database already exists",
    )
    parser.add_argument(
        "--force-forecast",
        action="store_true",
        help="Force rerun of forecast.py even when forecast_output.csv already exists",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "data" / "clean" / "tableau_extracts"

    print(f"Repository root: {repo_root}")
    ensure_raw_inputs(repo_root)
    etl_ran = ensure_database(repo_root, force_etl=args.force_etl)
    apply_analytical_views(repo_root)
    forecast_path = ensure_forecast(repo_root, force_forecast=args.force_forecast, etl_ran=etl_ran)

    export_tableau_extracts(repo_root, output_dir)

    forecast_export_path = output_dir / "sales_overview_forecast_output.csv"
    pd.read_csv(forecast_path).to_csv(forecast_export_path, index=False)
    print(f"Exported {forecast_export_path.relative_to(repo_root)}")

    print("\nTableau extracts are ready.")
    print(f"Output folder: {output_dir}")


if __name__ == "__main__":
    main()
