import re
import pandas as pd
import duckdb

from aws_cost_optimizer.config import DUCKDB_PATH
from aws_cost_optimizer.llm import call_llm


def validate_sql_safety(sql_query: str) -> bool:
    """Enforces read-only SELECT query constraints for security."""
    if not sql_query:
        return False
    cleaned = sql_query.strip().upper()
    # Strip markdown block formatting if present
    cleaned = re.sub(r"^```(SQL)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH")):
        return False

    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "PRAGMA", "GRANT", "REVOKE"]
    for kw in forbidden_keywords:
        if re.search(r"\b" + kw + r"\b", cleaned):
            return False
    return True


def extract_sql_query(llm_output: str) -> str:
    """Extracts raw SQL string from LLM output, trimming code block ticks."""
    sql = llm_output.strip()
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", sql, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    return sql


class QueryAgent:
    def __init__(self, db_path: str = DUCKDB_PATH):
        self.db_path = db_path

    def get_schema_summary(self) -> str:
        return """
        DuckDB Database Schema:
        - raw_cost_reports (line_item_id, usage_start_date, resource_id, resource_type, business_unit, daily_cost, usage_amount)
        - ecs_task_metrics (task_arn, cluster_name, service_name, business_unit, cpu_reserved, memory_reserved, cpu_utilization_max, memory_utilization_max, launch_type, has_security_sidecar)
        - lambda_metrics (function_arn, function_name, business_unit, memory_allocated_mb, memory_max_used_mb, avg_duration_ms, invocations_count, timeout_seconds)
        - s3_storage_metrics (bucket_name, business_unit, kms_key_arn, is_kms_encrypted, storage_bytes_standard, storage_bytes_glacier, object_count, has_lifecycle_policy, oldest_object_age_days)
        """

    def process_query(self, user_question: str) -> dict:
        """Executes 2-Stage Text-to-SQL + Context Synthesis pipeline."""
        schema_info = self.get_schema_summary()

        # Stage 1: Text-to-SQL Translation
        sql_system_prompt = f"""You are a FinOps Text-to-SQL AI Agent for DuckDB.
{schema_info}
Your job is to translate the user's natural language question into a valid, read-only ANSI SQL SELECT query.

CRITICAL DUCKDB SQL RULES:
1. When joining tables (e.g. JOINing raw_cost_reports with lambda_metrics, ecs_task_metrics, or s3_storage_metrics), ALWAYS qualify common columns like `business_unit` using full table names or aliases (e.g. `lambda_metrics.business_unit` or `raw_cost_reports.business_unit`) to prevent ambiguous column errors.
2. Output ONLY the executable SQL query enclosed in ```sql ... ``` code block. Do NOT include markdown explanations outside the SQL code block.
"""
        sql_raw_output = call_llm(user_question, system_prompt=sql_system_prompt)
        clean_sql = extract_sql_query(sql_raw_output)

        # Safety Check
        if not validate_sql_safety(clean_sql):
            return {
                "question": user_question,
                "sql_query": clean_sql,
                "error": "SECURITY_VIOLATION: Generated query failed read-only safety checks.",
                "explanation": "Query execution blocked due to security validation rules.",
                "data": pd.DataFrame()
            }

        # Execute Query against DuckDB
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            df_result = con.execute(clean_sql).fetchdf()
            con.close()
        except Exception as e:
            return {
                "question": user_question,
                "sql_query": clean_sql,
                "error": f"SQL Execution Error: {str(e)}",
                "explanation": f"Failed to execute SQL query against database: {str(e)}",
                "data": pd.DataFrame()
            }

        # Stage 2: Context Synthesis
        if df_result.empty:
            explanation = "No records matched your search criteria in the cloud cost database."
        else:
            synth_system_prompt = "You are CloudIntel FinOps Financial Analyst. Synthesize raw database query results into clear, concise, executive business insights highlighting cost drivers and trends."
            data_sample = df_result.head(10).to_string()
            synth_prompt = f"User Question: {user_question}\n\nSQL Executed:\n{clean_sql}\n\nQueryResult Data:\n{data_sample}\n\nProvide an executive explanation of what this cost data means for the business."
            explanation = call_llm(synth_prompt, system_prompt=synth_system_prompt)

        return {
            "question": user_question,
            "sql_query": clean_sql,
            "error": None,
            "explanation": explanation,
            "data": df_result
        }


if __name__ == "__main__":
    agent = QueryAgent()
    res = agent.process_query("Show me top 5 most expensive Lambda functions across BUs")
    print("Question:", res["question"])
    print("Generated SQL:\n", res["sql_query"])
    print("Explanation:\n", res["explanation"])
    print("Data:\n", res["data"])
