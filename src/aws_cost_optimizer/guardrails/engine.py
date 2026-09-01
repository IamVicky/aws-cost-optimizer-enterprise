class BankingGuardrailsEngine:
    """
    Enterprise Banking Security & Compliance Policy Interceptor.
    Validates candidate FinOps optimization recommendations before user display or IaC code generation.
    """

    def evaluate_recommendation(self, rec: dict) -> dict:
        """
        Evaluates a candidate recommendation dictionary against all banking security policies.
        Returns updated recommendation dictionary with compliance_status and guardrail_rule_triggered.
        """
        proposed_fix = rec.get("proposed_fix_description", "").upper()
        service_type = rec.get("service_type", "").upper()

        # Rule 1: S3 KMS Key Encryption Mandate (RULE_S3_KMS)
        if "S3" in service_type or "STORAGE" in service_type or "KMS" in proposed_fix:
            forbidden_kms_patterns = ["REMOVE KMS", "DELETE KMS", "DISABLE KMS", "DISABLE ENCRYPTION", "SSE-S3", "UNENCRYPTED"]
            for pattern in forbidden_kms_patterns:
                if pattern in proposed_fix:
                    rec["compliance_status"] = "REJECTED_KMS_MANDATE"
                    rec["guardrail_rule_triggered"] = "RULE_S3_KMS"
                    return rec

        # Rule 2: ECS Security Sidecar Retention (RULE_ECS_SIDECARS)
        if "ECS" in service_type or "CONTAINER" in proposed_fix:
            forbidden_sidecar_patterns = ["REMOVE SIDECAR", "STRIP SIDECAR", "DELETE SECURITY AGENT", "DISABLE AGENT"]
            for pattern in forbidden_sidecar_patterns:
                if pattern in proposed_fix:
                    rec["compliance_status"] = "REJECTED_SECURITY_SIDECAR_OMISSION"
                    rec["guardrail_rule_triggered"] = "RULE_ECS_SIDECARS"
                    return rec

        # Rule 3: Lambda Telemetry & Minimum Bounds (RULE_LAMBDA_BOUNDS)
        if "LAMBDA" in service_type or "SERVERLESS" in proposed_fix:
            forbidden_lambda_patterns = ["DISABLE TELEMETRY", "DISABLE XRAY", "DISABLE X-RAY", "MEMORY BELOW 128"]
            for pattern in forbidden_lambda_patterns:
                if pattern in proposed_fix:
                    rec["compliance_status"] = "REJECTED_LAMBDA_TELEMETRY_BOUNDS"
                    rec["guardrail_rule_triggered"] = "RULE_LAMBDA_BOUNDS"
                    return rec

        # Rule 4: Zero Public Access Enforcer (RULE_NO_PUBLIC_ACCESS)
        forbidden_public_patterns = ["ENABLE PUBLIC", "ALLOW PUBLIC", "DISABLE PUBLIC BLOCK", "ALLOW ALL INGRESS"]
        for pattern in forbidden_public_patterns:
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
