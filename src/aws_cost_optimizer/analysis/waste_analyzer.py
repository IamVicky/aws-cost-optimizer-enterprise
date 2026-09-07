import duckdb
import pandas as pd

from aws_cost_optimizer.config import DUCKDB_PATH
from aws_cost_optimizer.guardrails import BankingGuardrailsEngine
from aws_cost_optimizer.service_registry import load_services
from aws_cost_optimizer.expr import safe_eval


class WasteAnalyzer:
    def __init__(self, db_path: str = DUCKDB_PATH):
        self.db_path = db_path
        self.guardrails = BankingGuardrailsEngine()
        self.services = load_services()

    def _build_candidate(self, service_def, row: dict, rec_counter: int) -> dict:
        row = dict(row)
        for derived_name, derived_expr in service_def.waste_rule.derived_fields.items():
            row[derived_name] = safe_eval(derived_expr, row)

        est_savings = safe_eval(service_def.waste_rule.savings_formula, row)
        proposed_fix = service_def.waste_rule.fix_template.format(**row)
        resource_id = service_def.resource_id_template.format(**row)

        return {
            "recommendation_id": f"{service_def.waste_rule.recommendation_prefix}_{rec_counter:03d}",
            "resource_id": resource_id,
            "service_type": service_def.service_type,
            "business_unit": row["business_unit"],
            "estimated_monthly_savings": est_savings,
            "proposed_fix_description": proposed_fix,
        }

    def run_analysis(self) -> list:
        """Autonomous waste scanner: for every service defined in
        config/services/*.yaml, scans its metrics table for the configured
        waste condition and builds a recommendation candidate."""
        con = duckdb.connect(self.db_path)
        candidates = []  # list of (candidate_dict, source_row_dict)
        rec_counter = 1

        print("[Analyzer] Scanning cloud resources for waste patterns...")

        for service_def in self.services.values():
            df = con.execute(f"SELECT * FROM {service_def.table};").fetchdf()

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                if not safe_eval(service_def.waste_rule.condition, row_dict):
                    continue
                candidate = self._build_candidate(service_def, row_dict, rec_counter)
                candidates.append((candidate, row_dict))
                rec_counter += 1

        # Evaluate all candidates via Banking Guardrails Engine
        processed_recs = []
        for c, row_dict in candidates:
            evaluated = self.guardrails.evaluate_recommendation(c, row=row_dict)
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
