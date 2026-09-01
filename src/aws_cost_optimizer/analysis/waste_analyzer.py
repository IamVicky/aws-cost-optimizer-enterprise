import duckdb
import pandas as pd

from aws_cost_optimizer.config import DUCKDB_PATH
from aws_cost_optimizer.guardrails import BankingGuardrailsEngine


class WasteAnalyzer:
    def __init__(self, db_path: str = DUCKDB_PATH):
        self.db_path = db_path
        self.guardrails = BankingGuardrailsEngine()

    def run_analysis(self) -> list:
        """Autonomous waste scanner executing multi-dimensional analytical queries."""
        con = duckdb.connect(self.db_path)
        candidates = []
        rec_counter = 1

        print("[Analyzer] Scanning cloud resources for waste patterns...")

        # 1. Analyze ECS Task Oversizing
        df_ecs = con.execute("""
            SELECT task_arn, cluster_name, service_name, business_unit, cpu_reserved, memory_reserved, cpu_utilization_max, memory_utilization_max
            FROM ecs_task_metrics
            WHERE cpu_utilization_max < 15.0 OR memory_utilization_max < 15.0;
        """).fetchdf()

        for idx, row in df_ecs.iterrows():
            est_savings = round((row["cpu_reserved"] / 1024.0) * 35.0, 2)
            proposed_fix = f"Downsize ECS task definition {row['service_name']} CPU from {row['cpu_reserved']} to {max(256, int(row['cpu_reserved']/4))} units and memory from {row['memory_reserved']} to {max(512, int(row['memory_reserved']/4))} MB while preserving security sidecars."
            candidates.append({
                "recommendation_id": f"REC_ECS_{rec_counter:03d}",
                "resource_id": row["task_arn"],
                "service_type": "ECS-EC2",
                "business_unit": row["business_unit"],
                "estimated_monthly_savings": est_savings,
                "proposed_fix_description": proposed_fix
            })
            rec_counter += 1

        # 2. Analyze Lambda Memory Over-allocation
        df_lambda = con.execute("""
            SELECT function_arn, function_name, business_unit, memory_allocated_mb, memory_max_used_mb, invocations_count
            FROM lambda_metrics
            WHERE memory_allocated_mb >= (memory_max_used_mb * 2);
        """).fetchdf()

        for idx, row in df_lambda.iterrows():
            est_savings = round((row["memory_allocated_mb"] - row["memory_max_used_mb"]) * 0.005, 2)
            proposed_fix = f"Optimize Lambda function {row['function_name']} memory allocation from {row['memory_allocated_mb']} MB to {max(128, row['memory_max_used_mb'] * 2)} MB based on peak recorded memory of {row['memory_max_used_mb']} MB."
            candidates.append({
                "recommendation_id": f"REC_LAMBDA_{rec_counter:03d}",
                "resource_id": row["function_arn"],
                "service_type": "AWS-Lambda",
                "business_unit": row["business_unit"],
                "estimated_monthly_savings": est_savings,
                "proposed_fix_description": proposed_fix
            })
            rec_counter += 1

        # 3. Analyze S3 Storage Lifecycle Opportunities
        df_s3 = con.execute("""
            SELECT bucket_name, business_unit, kms_key_arn, storage_bytes_standard, oldest_object_age_days, has_lifecycle_policy
            FROM s3_storage_metrics
            WHERE has_lifecycle_policy = FALSE AND oldest_object_age_days > 90;
        """).fetchdf()

        for idx, row in df_s3.iterrows():
            tb_stored = row["storage_bytes_standard"] / 1e12
            est_savings = round(tb_stored * 15.0, 2)
            proposed_fix = f"Add AWS CloudFormation S3 Lifecycle Rule to transition objects older than 90 days in bucket '{row['bucket_name']}' to Glacier, preserving SSE-KMS encryption with KMS Key '{row['kms_key_arn']}'."
            candidates.append({
                "recommendation_id": f"REC_S3_{rec_counter:03d}",
                "resource_id": f"arn:aws:s3:::{row['bucket_name']}",
                "service_type": "S3-Storage",
                "business_unit": row["business_unit"],
                "estimated_monthly_savings": est_savings,
                "proposed_fix_description": proposed_fix
            })
            rec_counter += 1

        # Evaluate all candidates via Banking Guardrails Engine
        processed_recs = []
        for c in candidates:
            evaluated = self.guardrails.evaluate_recommendation(c)
            processed_recs.append(evaluated)

        # Store in candidate_recommendations table
        con.execute("DELETE FROM candidate_recommendations;")
        df_recs = pd.DataFrame(processed_recs)
        con.register("df_recs_temp", df_recs)
        con.execute("""
            INSERT INTO candidate_recommendations
            SELECT recommendation_id, resource_id, service_type, business_unit, estimated_monthly_savings, proposed_fix_description, compliance_status, guardrail_rule_triggered
            FROM df_recs_temp;
        """)
        con.unregister("df_recs_temp")
        con.close()

        print(f"  - Generated {len(processed_recs)} total optimization candidates.")
        approved_cnt = sum(1 for r in processed_recs if r["compliance_status"] == "APPROVED")
        rejected_cnt = sum(1 for r in processed_recs if r["compliance_status"] != "APPROVED")
        print(f"  - Approved: {approved_cnt} | Guardrail Rejected: {rejected_cnt}")

        return processed_recs


if __name__ == "__main__":
    analyzer = WasteAnalyzer()
    recs = analyzer.run_analysis()
    for r in recs:
        print(f"[{r['compliance_status']}] {r['recommendation_id']}: {r['proposed_fix_description'][:80]}... (Savings: ${r['estimated_monthly_savings']}/mo)")
