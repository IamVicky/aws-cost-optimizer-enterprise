# CloudIntel — Corner Scenarios & Edge Cases Specification

## Executive Summary

This document serves as the authoritative repository of all **corner scenarios, edge cases, failure modes, and boundary conditions** for the **CloudIntel Enterprise AI FinOps Platform**.

It provides explicit failure definitions, risk severity levels, and programmatic mitigation strategies derived from [`docs/PROBLEM_STATEMENT.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/PROBLEM_STATEMENT.md), [`docs/ARCHITECTURE.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/ARCHITECTURE.md), [`docs/Implementation-plan.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/Implementation-plan.md), and [`docs/deployment-plan.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/deployment-plan.md).

---

## Edge Case Matrix Summary

| ID | Component Area | Corner Scenario / Edge Case | Risk Severity | Primary Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **EC-01** | Data Pipeline (`ingest.py`) | Untagged or Unknown Business Unit Resources | **MEDIUM** | Assign to `BU_UNALLOCATED` default partition & flag for governance tag audit. |
| **EC-02** | Data Pipeline (`ingest.py`) | Negative Spend, Promotional Credits & Zero-Cost Lines | **LOW** | Filter out 0.00 usage items; separate positive usage cost from AWS promotional credit line items. |
| **EC-03** | Data Pipeline (`ingest.py`) | Corrupted / Malformed Billing CSVs or Metrics JSONs | **HIGH** | Strict schema validation with `pandas`/`pydantic`; log malformed rows to dead-letter audit file. |
| **EC-04** | Data Pipeline (`ingest.py`) | DuckDB Single-Writer File Locking Collision | **HIGH** | Use read-only connection mode (`read_only=True`) for UI/Query operations; single writer for ETL. |
| **EC-05** | Query Agent (`query_agent.py`) | Destructive / Non-SELECT SQL Injection Generation | **CRITICAL** | AST parsing SQL validator enforcing strictly read-only `SELECT` queries before DuckDB execution. |
| **EC-06** | Query Agent (`query_agent.py`) | Groq API Rate Limit (HTTP 429) or API Outage | **HIGH** | Exponential backoff retry handler + fallback to local rule-based context generator. |
| **EC-07** | Query Agent (`query_agent.py`) | Empty SQL Query Result Set (0 Rows Returned) | **LOW** | Graceful empty-state response handling in synthesis stage ("No matching records found for BU X"). |
| **EC-08** | Waste Analyzer (`analyzer.py`) | Burst / Spiky Workloads (99% Peak CPU for 5 Mins/Month) | **HIGH** | Require 14-day percentiles (P95/P99) alongside max utilization before flagging container task sizing. |
| **EC-09** | Waste Analyzer (`analyzer.py`) | Zero Invocations with Configured Provisioned Concurrency | **MEDIUM** | Flag as `IDLE_PROVISIONED_RESOURCE` and calculate exact monthly zero-utilization waste. |
| **EC-10** | Guardrails Engine (`guardrails.py`)| Adversarial LLM KMS Removal / Downgrade Attempt | **CRITICAL** | Hard rule interceptor (`RULE_S3_KMS`) forcing immediate status `REJECTED_KMS_MANDATE`. |
| **EC-11** | Guardrails Engine (`guardrails.py`)| ECS Container Sidecar Removal during Resizing | **CRITICAL** | Task Definition validator ensuring `AWS::ECS::TaskDefinition` retains mandatory security containers. |
| **EC-12** | Guardrails Engine (`guardrails.py`)| S3 Lifecycle Rule Stripping Public Access Block | **HIGH** | Force `PublicAccessBlockConfiguration` block in generated CloudFormation template output. |
| **EC-13** | IaC Generator (`iac_generator.py`)| Malformed CloudFormation YAML / Service Catalog Schema | **HIGH** | Pre-output YAML syntax validation using `pyyaml` / `cfn-lint` before UI rendering. |
| **EC-14** | User Interface (`app.py`) | Large Result Set Browser Rendering Lag (50k+ Rows) | **MEDIUM** | Pagination, table limit caps (`LIMIT 1000`), and Streamlit data framing optimizations. |
| **EC-15** | AWS Connector (`aws_connector.py`)| Invalid / Expired AWS Access Keys or AccessDenied | **HIGH** | Catch `ClientError` / `UnrecognizedClientException`, display notification in UI, and fallback to synthetic dataset. |
| **EC-16** | Account Discovery (`ingest.py`) | Missing or Malformed `accounts.json` File | **MEDIUM** | Auto-generate default `accounts.json` containing default account metadata and validate JSON structure. |

---

## Detailed Edge Case Specifications & Mitigations


### 1. Data Ingestion & Database Edge Cases (`ingest.py`)

#### EC-01: Untagged or Misallocated Business Unit Resources
- **Scenario**: CloudWatch logs or CUR billing lines contain resources missing the `BusinessUnit` or `Environment` tag.
- **Risk**: High risk of distorted BU cost allocation and inaccurate cross-BU waste reports.
- **Mitigation Strategy**:
  - `ingest.py` checks tag fields. If missing, assigns `business_unit = 'BU_UNALLOCATED'`.
  - Aggregation pipeline automatically groups `BU_UNALLOCATED` into a dedicated governance widget in Streamlit UI tab 2 to highlight tagging non-compliance.

#### EC-02: Negative Cost Items, AWS Credits, and Refunds
- **Scenario**: AWS CUR contains negative costs (EDP discounts, credits, refunds) or zero usage records.
- **Risk**: Negative values polluting average daily cost calculations and skewing savings estimates.
- **Mitigation Strategy**:
  - Separate `unblended_cost` from `credit_amount`.
  - Base waste analysis strictly on gross positive usage consumption (`daily_cost > 0`).

#### EC-03: Corrupted Raw Metrics & Schema Drift
- **Scenario**: An ingestion CSV/JSON file has missing headers, unexpected column types, or corrupted JSON strings.
- **Risk**: Pipeline crash during daily automated batch load.
- **Mitigation Strategy**:
  - Enforce explicit schema validation in `ingest.py`.
  - Wrap line parsing in `try/except` block, logging failing lines to `data/raw/ingest_errors.log` while processing remaining valid rows.

#### EC-04: DuckDB Concurrent Access File Locking
- **Scenario**: The Streamlit app UI reads from `cloudintel.duckdb` while `ingest.py` is running a write transaction. DuckDB throws a file lock error.
- **Risk**: UI crash or failed user queries.
- **Mitigation Strategy**:
  - `ingest.py` holds write lock exclusively during ETL.
  - `query_agent.py`, `analyzer.py`, and `app.py` open DuckDB connections with `read_only=True`.

---

### 2. Natural Language Query & LLM Agent Edge Cases (`query_agent.py`)

#### EC-05: Destructive or Non-SELECT SQL Generation (SQL Injection Defense)
- **Scenario**: User prompt or LLM hallucination produces destructive SQL (e.g. `DROP TABLE ecs_task_metrics;` or `DELETE FROM raw_cost_reports;`).
- **Risk**: **CRITICAL**. Total loss of analytical database contents.
- **Mitigation Strategy**:
  - Pass LLM SQL output through an AST / regex validator before execution:
    ```python
    def validate_sql_safety(sql_query: str) -> bool:
        cleaned = sql_query.strip().upper()
        # Strictly mandate that query starts with SELECT or WITH
        if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH")):
            return False
        # Block forbidden keywords
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "PRAGMA"]
        return not any(kw in cleaned for kw in forbidden)
    ```

#### EC-06: Groq API Rate Limiting (HTTP 429) & Network Timeouts
- **Scenario**: Groq API returns HTTP 429 rate limit error during live demo or batch analysis.
- **Risk**: Broken user interaction in Streamlit chat interface.
- **Mitigation Strategy**:
  - Wrap API calls with exponential backoff using `tenacity` library (3 retries, max 10s wait).
  - If API remains unavailable, catch exception and display a fallback notice in Streamlit UI: *"AI reasoning engine is temporarily busy. Showing cached query results."*

#### EC-07: SQL Query Execution Returns 0 Rows
- **Scenario**: A valid SQL query executes but matches no database rows (e.g., *"Show Lambda functions for BU Finance"* when Finance has no Lambda usage).
- **Risk**: LLM context synthesizer attempting to hallucinate data for empty result sets.
- **Mitigation Strategy**:
  - If result set is empty (`len(df) == 0`), bypass LLM Stage 2 and immediately return: *"No matching records found in the database for your query criteria."*

---

### 3. Proactive Waste Analyzer Edge Cases (`analyzer.py`)

#### EC-08: Spiky / Periodic Workload Over-Optimization
- **Scenario**: An ECS task or Lambda function runs batch jobs once a week (99% CPU/Memory usage for 1 hour), but runs at 2% usage the rest of the time.
- **Risk**: Analyzer incorrectly flagging container as over-provisioned, leading to out-of-memory (OOM) crashes during peak runs.
- **Mitigation Strategy**:
  - Evaluation logic must check both `cpu_utilization_max` (peak) AND average utilization.
  - If peak utilization > 70% at any point, mark resource as `BURST_CAPABLE_DO_NOT_RESIZE`.

#### EC-09: Idle Provisioned Concurrency with Zero Invocations
- **Scenario**: A Lambda function has provisioned concurrency allocated (incurring fixed hourly cost), but zero invocations over 30 days.
- **Risk**: Standard duration/memory rules missing idle concurrency cost.
- **Mitigation Strategy**:
  - Query checks `invocations_count == 0` AND `provisioned_concurrency > 0`, generating a dedicated recommendation card: `REMOVE_IDLE_PROVISIONED_CONCURRENCY`.

---

### 4. Banking Security & Guardrails Engine Edge Cases (`guardrails.py`)

#### EC-10: Adversarial LLM KMS Encryption Key Removal
- **Scenario**: The LLM attempts to optimize S3 costs by proposing deletion or detachment of `AWS Managed KMS Keys` or setting SSE to unencrypted.
- **Risk**: **CRITICAL**. Severe violation of banking data protection mandates.
- **Mitigation Strategy**:
  - `guardrails.py` intercepts candidate recommendation objects before output:
    ```python
    def evaluate_s3_kms_guardrail(recommendation) -> str:
        description = recommendation.get("proposed_fix_description", "").upper()
        if "REMOVE KMS" in description or "DISABLE ENCRYPTION" in description or "SSE-S3" in description:
            return "REJECTED_KMS_MANDATE"
        return "APPROVED"
    ```

#### EC-11: Stripping Security Monitoring Sidecars in ECS Task Definitions
- **Scenario**: LLM generates an updated `AWS::ECS::TaskDefinition` containing only the primary container, omitting mandatory security sidecars (e.g. log shipping / vulnerability monitoring containers).
- **Risk**: **CRITICAL**. Loss of security observability in containerized workloads.
- **Mitigation Strategy**:
  - `guardrails.py` parses `ContainerDefinitions` in the proposed task definition template.
  - If `has_security_sidecar == True` in input database, verify that output template retains all sidecar container definitions. If omitted, flag `REJECTED_SECURITY_SIDECAR_OMISSION`.

#### EC-12: Public Access Policy Exposure in CloudFormation S3 Lifecycle Templates
- **Scenario**: CloudFormation snippet generated for S3 lifecycle rule lacks explicit public access block parameters.
- **Risk**: Potential public bucket exposure upon template deployment.
- **Mitigation Strategy**:
  - `iac_generator.py` forcefully injects the mandatory compliance block into every generated `AWS::S3::Bucket` resource:
    ```yaml
    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
    ```

---

### 5. Infrastructure as Code & UI Edge Cases (`iac_generator.py` & `app.py`)

#### EC-13: Malformed CloudFormation YAML Output
- **Scenario**: LLM output includes markdown formatting ticks (` ```yaml ... ``` `) inside the template string or invalid indentation.
- **Risk**: AWS Service Catalog rejection upon deployment.
- **Mitigation Strategy**:
  - Clean markdown fencing programmatically via regex.
  - Parse output string using `yaml.safe_load()`. If YAML parsing fails, return a fallback standardized template with clean parameters.

#### EC-14: Large Result Set Rendering Lag in Streamlit
- **Scenario**: A user query returns 100,000 billing line items, causing Streamlit memory overhead or browser freeze.
- **Risk**: Poor user experience during live demo.
- **Mitigation Strategy**:
  - Enforce `LIMIT 1000` on all Text-to-SQL queries generated by `query_agent.py`.
  - Provide a "Download Full CSV" button for large tabular result sets instead of rendering all rows in browser DOM.

---

## Verification & Test Plan for Corner Scenarios

```bash
# Test Suite Execution Commands for Corner Scenarios
python -m unittest tests/test_guardrails.py
python -m unittest tests/test_sql_safety.py
python -m unittest tests/test_ingest_resilience.py
```

### Automated Guardrail Test Assertions
1. **Assertion 1 (KMS Deletion Interception)**:
   - Input: Candidate recommendation proposing KMS key removal.
   - Expected Output: `compliance_status == "REJECTED_KMS_MANDATE"`.
2. **Assertion 2 (SQL Injection Block)**:
   - Input: `query_agent.py` generated SQL containing `DROP TABLE ecs_task_metrics`.
   - Expected Output: `validate_sql_safety() == False` -> Execution blocked.
3. **Assertion 3 (Public Access Block Retention)**:
   - Input: Generated S3 CloudFormation YAML template.
   - Expected Output: Contains `BlockPublicAcls: true` and `BlockPublicPolicy: true`.
