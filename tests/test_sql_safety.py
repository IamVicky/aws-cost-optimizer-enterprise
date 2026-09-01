import unittest
from aws_cost_optimizer.analysis.query_agent import validate_sql_safety, extract_sql_query

class TestSQLSafety(unittest.TestCase):
    def test_valid_select_query(self):
        sql = "SELECT function_name, daily_cost FROM lambda_metrics JOIN raw_cost_reports ON function_arn = resource_id;"
        self.assertTrue(validate_sql_safety(sql))

    def test_valid_with_cte_query(self):
        sql = "WITH top_s3 AS (SELECT bucket_name FROM s3_storage_metrics) SELECT * FROM top_s3;"
        self.assertTrue(validate_sql_safety(sql))

    def test_block_drop_table(self):
        sql = "DROP TABLE ecs_task_metrics;"
        self.assertFalse(validate_sql_safety(sql))

    def test_block_delete_from(self):
        sql = "DELETE FROM raw_cost_reports WHERE business_unit = 'Marketing';"
        self.assertFalse(validate_sql_safety(sql))

    def test_block_update_statement(self):
        sql = "UPDATE lambda_metrics SET memory_allocated_mb = 128;"
        self.assertFalse(validate_sql_safety(sql))

    def test_block_sql_injection_attempt(self):
        sql = "SELECT * FROM s3_storage_metrics; DROP TABLE raw_cost_reports; --"
        self.assertFalse(validate_sql_safety(sql))

    def test_extract_markdown_sql(self):
        raw = "```sql\nSELECT * FROM ecs_task_metrics;\n```"
        extracted = extract_sql_query(raw)
        self.assertEqual(extracted, "SELECT * FROM ecs_task_metrics;")

if __name__ == "__main__":
    unittest.main()
