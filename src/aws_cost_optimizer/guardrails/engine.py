from aws_cost_optimizer.service_registry import load_services
from aws_cost_optimizer.expr import safe_eval

FORBIDDEN_PUBLIC_PATTERNS = ["ENABLE PUBLIC", "ALLOW PUBLIC", "DISABLE PUBLIC BLOCK", "ALLOW ALL INGRESS"]


class BankingGuardrailsEngine:
    """
    Enterprise Banking Security & Compliance Policy Interceptor.
    Validates candidate FinOps optimization recommendations before user display or IaC code generation.

    Per-service rules (e.g. "never remove KMS on S3", "never strip ECS
    sidecars") come from each service's config/services/*.yaml
    guardrail_rules list, so adding a service or changing its guardrail
    logic does not require touching this file. Only rules that apply
    across every service regardless of type (e.g. public access) live
    here directly.
    """

    def __init__(self):
        self.services = load_services()

    def evaluate_recommendation(self, rec: dict, row: dict = None) -> dict:
        """
        Evaluates a candidate recommendation dictionary against all banking security policies.
        `row` (optional) is the source metrics row the recommendation was derived
        from, made available to numeric/structural 'condition' guardrail rules.
        Returns updated recommendation dictionary with compliance_status and guardrail_rule_triggered.
        """
        proposed_fix = rec.get("proposed_fix_description", "").upper()
        service_type = rec.get("service_type", "").upper()
        row = row or {}

        for service_def in self.services.values():
            for guardrail_rule in service_def.guardrail_rules:
                if guardrail_rule.type == "forbidden_patterns":
                    # Matches on keyword presence in service_type/fix text, not exact
                    # service_type equality, so a rule fires for any recommendation
                    # that looks like it belongs to that service (e.g. "S3" or "ECS-EC2").
                    if not any(kw in service_type or kw in proposed_fix for kw in guardrail_rule.match_keywords):
                        continue
                    for pattern in guardrail_rule.patterns:
                        if pattern in proposed_fix:
                            rec["compliance_status"] = guardrail_rule.compliance_status
                            rec["guardrail_rule_triggered"] = guardrail_rule.rule_id
                            return rec
                elif guardrail_rule.type == "condition":
                    # Condition rules are numeric/structural checks tied to a specific
                    # service's row schema, so require an exact service_type match.
                    if service_def.service_type.upper() != service_type:
                        continue
                    if safe_eval(guardrail_rule.condition, row):
                        rec["compliance_status"] = guardrail_rule.compliance_status
                        rec["guardrail_rule_triggered"] = guardrail_rule.rule_id
                        return rec

        # Global Rule: Zero Public Access Enforcer (RULE_NO_PUBLIC_ACCESS)
        for pattern in FORBIDDEN_PUBLIC_PATTERNS:
            if pattern in proposed_fix:
                rec["compliance_status"] = "REJECTED_PUBLIC_ACCESS_EXPOSURE"
                rec["guardrail_rule_triggered"] = "RULE_NO_PUBLIC_ACCESS"
                return rec

        # Default: Passes all banking compliance guardrails
        rec["compliance_status"] = "APPROVED"
        rec["guardrail_rule_triggered"] = "NONE_ALL_POLICIES_PASSED"
        return rec


if __name__ == "__main__":
    engine = BankingGuardrailsEngine()
    test_recs = [
        {
            "recommendation_id": "REC_TEST_01",
            "resource_id": "arn:aws:s3:::mktg-campaign-raw-logs-2026",
            "service_type": "S3",
            "proposed_fix_description": "Remove KMS Key to eliminate KMS API charge",
        },
        {
            "recommendation_id": "REC_TEST_02",
            "resource_id": "arn:aws:ecs:us-east-1:123456789012:task-definition/marketing-analytics:2",
            "service_type": "ECS-EC2",
            "proposed_fix_description": "Downsize container vCPU from 4096 to 512 and memory from 16384 to 2048 MB",
        }
    ]
    for r in test_recs:
        res = engine.evaluate_recommendation(r)
        print(f"ID: {res['recommendation_id']} -> Status: {res['compliance_status']} (Rule: {res['guardrail_rule_triggered']})")
