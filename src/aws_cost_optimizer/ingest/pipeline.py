import os
import json
import argparse
import duckdb
import pandas as pd

from aws_cost_optimizer.config import DATA_RAW_DIR, DATA_PROCESSED_DIR, DUCKDB_PATH
from aws_cost_optimizer.connectors import AWSNonProdConnector


def init_db(con):
    """Initializes DuckDB schema tables for cost reports and resource metrics."""
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

    con.execute("""
        CREATE TABLE IF NOT EXISTS ecs_task_metrics (
            task_arn VARCHAR PRIMARY KEY,
            cluster_name VARCHAR,
            service_name VARCHAR,
            business_unit VARCHAR,
            cpu_reserved INTEGER,
            memory_reserved INTEGER,
            cpu_utilization_max DOUBLE,
            memory_utilization_max DOUBLE,
            launch_type VARCHAR,
            has_security_sidecar BOOLEAN
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS lambda_metrics (
            function_arn VARCHAR PRIMARY KEY,
            function_name VARCHAR,
            business_unit VARCHAR,
            memory_allocated_mb INTEGER,
            memory_max_used_mb INTEGER,
            avg_duration_ms DOUBLE,
            invocations_count INTEGER,
            timeout_seconds INTEGER
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS s3_storage_metrics (
            bucket_name VARCHAR PRIMARY KEY,
            business_unit VARCHAR,
            kms_key_arn VARCHAR,
            is_kms_encrypted BOOLEAN,
            storage_bytes_standard DOUBLE,
            storage_bytes_glacier DOUBLE,
            object_count INTEGER,
            has_lifecycle_policy BOOLEAN,
            oldest_object_age_days INTEGER
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


def ingest_data(use_aws_live: bool = False):
    """Main ETL pipeline reading raw billing & metric data into DuckDB."""
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    print("[ETL] Starting Data Ingestion Pipeline...")

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

    live_ecs = aws_conn.fetch_ecs_task_metrics() if aws_active else []
    if live_ecs:
        df_ecs = pd.DataFrame(live_ecs)
    else:
        ecs_file = os.path.join(DATA_RAW_DIR, "ecs_task_metrics.json")
        df_ecs = pd.DataFrame(json.load(open(ecs_file))) if os.path.exists(ecs_file) else pd.DataFrame()

    live_lambda = aws_conn.fetch_lambda_metrics() if aws_active else []
    if live_lambda:
        df_lambda = pd.DataFrame(live_lambda)
    else:
        lambda_file = os.path.join(DATA_RAW_DIR, "lambda_metrics.json")
        df_lambda = pd.DataFrame(json.load(open(lambda_file))) if os.path.exists(lambda_file) else pd.DataFrame()

    live_s3 = aws_conn.fetch_s3_metrics() if aws_active else []
    if live_s3:
        df_s3 = pd.DataFrame(live_s3)
    else:
        s3_file = os.path.join(DATA_RAW_DIR, "s3_storage_metrics.json")
        df_s3 = pd.DataFrame(json.load(open(s3_file))) if os.path.exists(s3_file) else pd.DataFrame()

    # Now open DuckDB connection and write tables
    con = duckdb.connect(DUCKDB_PATH)
    try:
        init_db(con)

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

        if not df_ecs.empty:
            con.execute("DELETE FROM ecs_task_metrics;")
            con.register("df_ecs_temp", df_ecs)
            con.execute("""
                INSERT INTO ecs_task_metrics
                SELECT task_arn, cluster_name, service_name, business_unit, cpu_reserved, memory_reserved, cpu_utilization_max, memory_utilization_max, launch_type, has_security_sidecar
                FROM df_ecs_temp;
            """)
            con.unregister("df_ecs_temp")
            print(f"  - Loaded {len(df_ecs)} records into 'ecs_task_metrics'")

        if not df_lambda.empty:
            con.execute("DELETE FROM lambda_metrics;")
            con.register("df_lambda_temp", df_lambda)
            con.execute("""
                INSERT INTO lambda_metrics
                SELECT function_arn, function_name, business_unit, memory_allocated_mb, memory_max_used_mb, avg_duration_ms, invocations_count, timeout_seconds
                FROM df_lambda_temp;
            """)
            con.unregister("df_lambda_temp")
            print(f"  - Loaded {len(df_lambda)} records into 'lambda_metrics'")

        if not df_s3.empty:
            con.execute("DELETE FROM s3_storage_metrics;")
            con.register("df_s3_temp", df_s3)
            con.execute("""
                INSERT INTO s3_storage_metrics
                SELECT bucket_name, business_unit, kms_key_arn, is_kms_encrypted, storage_bytes_standard, storage_bytes_glacier, object_count, has_lifecycle_policy, oldest_object_age_days
                FROM df_s3_temp;
            """)
            con.unregister("df_s3_temp")
            print(f"  - Loaded {len(df_s3)} records into 's3_storage_metrics'")

        print("[ETL] Ingestion completed successfully! Database ready at:", DUCKDB_PATH)
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudIntel Data Ingestion Pipeline")
    parser.add_argument("--use-aws", action="store_true", help="Attempt live AWS non-prod account connection")
    args = parser.parse_args()

    ingest_data(use_aws_live=args.use_aws)
