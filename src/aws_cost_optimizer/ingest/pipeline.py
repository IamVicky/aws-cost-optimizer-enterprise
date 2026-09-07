import os
import json
import argparse
import duckdb
import pandas as pd

from aws_cost_optimizer.config import DATA_RAW_DIR, DATA_PROCESSED_DIR, DUCKDB_PATH
from aws_cost_optimizer.connectors import AWSNonProdConnector
from aws_cost_optimizer.service_registry import load_services


def _column_ddl(field) -> str:
    ddl = f"{field.name} {field.type}"
    if field.primary_key:
        ddl += " PRIMARY KEY"
    return ddl


def init_db(con, services: dict = None):
    """Initializes DuckDB schema tables for cost reports, per-service metrics
    (driven by config/services/*.yaml), and recommendations."""
    services = services if services is not None else load_services()

    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_cost_reports (
            line_item_id VARCHAR PRIMARY KEY,
            usage_start_date TIMESTAMP,
            resource_id VARCHAR,
            resource_type VARCHAR,
            business_unit VARCHAR,
            daily_cost DOUBLE,
            usage_amount DOUBLE
        );
    """)

    for service_def in services.values():
        columns_ddl = ",\n            ".join(_column_ddl(f) for f in service_def.schema_fields)
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {service_def.table} (
            {columns_ddl}
            );
        """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS candidate_recommendations (
            recommendation_id VARCHAR PRIMARY KEY,
            resource_id VARCHAR,
            service_type VARCHAR,
            business_unit VARCHAR,
            estimated_monthly_savings DOUBLE,
            proposed_fix_description VARCHAR,
            compliance_status VARCHAR,
            guardrail_rule_triggered VARCHAR
        );
    """)


def _load_service_dataframe(service_def, aws_conn, aws_active: bool) -> pd.DataFrame:
    """Fetches live data for a service if AWS is active, else falls back to
    its local raw JSON fixture. Mirrors the previous per-service fetch/fallback
    logic, but driven by the service's fetch_adapter/raw_fallback_file config."""
    live_records = aws_conn.fetch(service_def) if aws_active else []
    if live_records:
        return pd.DataFrame(live_records)

    fallback_path = os.path.join(DATA_RAW_DIR, service_def.raw_fallback_file)
    if os.path.exists(fallback_path):
        return pd.DataFrame(json.load(open(fallback_path)))
    return pd.DataFrame()


def ingest_data(use_aws_live: bool = False):
    """Main ETL pipeline reading raw billing & metric data into DuckDB.
    Per-service tables/columns/fetch logic are driven entirely by
    config/services/*.yaml via the service registry."""
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    print("[ETL] Starting Data Ingestion Pipeline...")

    services = load_services()
    aws_conn = AWSNonProdConnector()
    aws_active = use_aws_live or aws_conn.is_aws_authenticated()

    if aws_active:
        print("[AWS Non-Prod Mode] Fetching live metrics from AWS Account...")

    # Fetch network/AWS data first before opening DuckDB connection to avoid locking issues
    df_cur = pd.DataFrame()
    if aws_active:
        df_cur = aws_conn.fetch_cost_explorer_reports()

    if df_cur.empty:
        cur_file = os.path.join(DATA_RAW_DIR, "aws_cur_export.csv")
        if os.path.exists(cur_file):
            df_cur = pd.read_csv(cur_file)

    service_dataframes = {
        service_def.service_type: _load_service_dataframe(service_def, aws_conn, aws_active)
        for service_def in services.values()
    }

    # Now open DuckDB connection and write tables
    con = duckdb.connect(DUCKDB_PATH)
    try:
        init_db(con, services)

        if not df_cur.empty:
            con.execute("DELETE FROM raw_cost_reports;")
            con.register("df_cur_temp", df_cur)
            con.execute("""
                INSERT INTO raw_cost_reports
                SELECT line_item_id, CAST(usage_start_date AS TIMESTAMP), resource_id, resource_type, business_unit, daily_cost, usage_amount
                FROM df_cur_temp;
            """)
            con.unregister("df_cur_temp")
            print(f"  - Loaded {len(df_cur)} records into 'raw_cost_reports'")

        for service_def in services.values():
            df = service_dataframes[service_def.service_type]
            if df.empty:
                continue
            column_names = [f.name for f in service_def.schema_fields]
            temp_view = f"df_{service_def.table}_temp"
            con.execute(f"DELETE FROM {service_def.table};")
            con.register(temp_view, df)
            select_cols = ", ".join(column_names)
            con.execute(f"""
                INSERT INTO {service_def.table}
                SELECT {select_cols}
                FROM {temp_view};
            """)
            con.unregister(temp_view)
            print(f"  - Loaded {len(df)} records into '{service_def.table}'")

        print("[ETL] Ingestion completed successfully! Database ready at:", DUCKDB_PATH)
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudIntel Data Ingestion Pipeline")
    parser.add_argument("--use-aws", action="store_true", help="Attempt live AWS non-prod account connection")
    args = parser.parse_args()

    ingest_data(use_aws_live=args.use_aws)
