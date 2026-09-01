import unittest
from aws_cost_optimizer.guardrails import BankingGuardrailsEngine

class TestBankingGuardrails(unittest.TestCase):
    def setUp(self):
        self.engine = BankingGuardrailsEngine()

    def test_kms_deletion_rejection(self):
        rec = {
            "recommendation_id": "TEST_KMS_01",
            "service_type": "S3",
            "proposed_fix_description": "Remove KMS Key to eliminate API costs"
        }
        res = self.engine.evaluate_recommendation(rec)
        self.assertEqual(res["compliance_status"], "REJECTED_KMS_MANDATE")
        self.assertEqual(res["guardrail_rule_triggered"], "RULE_S3_KMS")

    def test_sidecar_stripping_rejection(self):
        rec = {
            "recommendation_id": "TEST_ECS_01",
            "service_type": "ECS-EC2",
            "proposed_fix_description": "Downsize container and strip sidecar security agent"
        }
        res = self.engine.evaluate_recommendation(rec)
        self.assertEqual(res["compliance_status"], "REJECTED_SECURITY_SIDECAR_OMISSION")
        self.assertEqual(res["guardrail_rule_triggered"], "RULE_ECS_SIDECARS")

    def test_public_access_exposure_rejection(self):
        rec = {
            "recommendation_id": "TEST_PUB_01",
            "service_type": "S3",
            "proposed_fix_description": "Enable public access on raw logs bucket"
        }
        res = self.engine.evaluate_recommendation(rec)
        self.assertEqual(res["compliance_status"], "REJECTED_PUBLIC_ACCESS_EXPOSURE")
        self.assertEqual(res["guardrail_rule_triggered"], "RULE_NO_PUBLIC_ACCESS")

    def test_compliant_recommendation_approval(self):
        rec = {
            "recommendation_id": "TEST_OK_01",
            "service_type": "S3-Storage",
            "proposed_fix_description": "Add lifecycle rule to transition objects older than 90 days to Glacier while preserving KMS key encryption."
        }
        res = self.engine.evaluate_recommendation(rec)
        self.assertEqual(res["compliance_status"], "APPROVED")
        self.assertEqual(res["guardrail_rule_triggered"], "NONE_ALL_POLICIES_PASSED")

if __name__ == "__main__":
    unittest.main()
