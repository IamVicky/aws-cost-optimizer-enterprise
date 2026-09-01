# Implementation Plan — CloudIntel: Enterprise AI FinOps Platform

## Executive Summary & Vision

**CloudIntel** is an enterprise AI FinOps platform designed to ingest cloud cost & usage data, analyze multi-dimensional waste patterns across decentralized Business Units (BUs), enforce strict financial institution security and compliance guardrails, and automatically generate compliant AWS CloudFormation templates ready for **AWS Service Catalog** integration.

This document details the complete end-to-end technical implementation plan derived from [`docs/PROBLEM_STATEMENT.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/PROBLEM_STATEMENT.md) and [`docs/ARCHITECTURE.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/ARCHITECTURE.md).

---

## Technical Strategy & Two-Phase Roadmap

Development follows a two-phase strategy to validate capabilities with zero cloud resource overhead before enterprise deployment:

| Category | Phase 1: Proof of Concept (POC) Scope | Phase 2: Enterprise Production Scale |
| :--- | :--- | :--- |
| **Resource Focus** | **Amazon ECS (EC2)**, **AWS Lambda**, **Amazon S3** | All AWS Resources (EC2, S3, RDS, Lambda, DynamoDB, Network) |
| **LLM Provider** | **Groq Cloud API** (`llama-3.3-70b-versatile`) — *Free LPU Inference* | **Anthropic Claude 3.5 Sonnet** — *Enterprise License* |
| **AWS Authentication**| **AWS Access Keys** (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` via `.env` or UI) | **System Account Access** (Central System Account federating all AWS Accounts) |
| **Account Discovery** | **`accounts.json` Configuration** or Interactive Streamlit UI Account Selector | **AWS Organizations / System Account Registry** (Auto-discovers registered Accounts) |
| **Compliance Layer** | **Banking Guardrails Engine** (`guardrails.py`) | Enterprise Policy Engine (AWS OPA / Sentinel / AWS Config) |
| **Database Engine** | **DuckDB** (`data/processed/cloudintel.duckdb`) | **AWS Athena / Amazon Redshift / Snowflake** |
| **Storage / Data Lake** | Local Directory (`data/raw/`, `data/processed/`) | AWS S3 Bucket + AWS Glue Data Catalog |
| **User Interface** | **Streamlit App** (`app.py`) | Enterprise Web Portal (Streamlit / Next.js on AWS App Runner) |
| **IaC Output** | **AWS CloudFormation (YAML/JSON)** & Service Catalog Product Templates | AWS CI/CD Pipeline (Service Catalog Portfolio / CodePipeline) |


---

## Repository Target Structure

```plaintext
cloudintel/
├── data/
│   ├── raw/                      # Raw billing CSVs, ECS (EC2) metrics, Lambda & S3 stats
│   │   ├── aws_cur_export.csv
│   │   ├── ecs_task_metrics.json
│   │   ├── lambda_metrics.json
│   │   └── s3_storage_metrics.json
│   └── processed/                # Cleaned analytical database
│       └── cloudintel.duckdb
├── docs/                         # Architecture & problem specifications
│   ├── PROBLEM_STATEMENT.md
│   ├── ARCHITECTURE.md
│   └── Implementation-plan.md   # This document
├── ingest.py                     # Week 1: Multi-service ETL & DuckDB ingestion engine
├── query_agent.py                # Week 2: Text-to-SQL & context synthesis agent
├── analyzer.py                   # Week 3: Proactive multi-service waste analyzer
├── guardrails.py                 # Week 3: Banking Security & Compliance Policy Engine
├── iac_generator.py              # Week 4: Compliant CloudFormation & Service Catalog generator
├── app.py                        # Week 4: Streamlit web UI application
├── requirements.txt              # Project dependencies
└── README.md                     # Project documentation & quickstart guide
```

---

## Detailed System Component Specifications

### 1. Data Ingestion Pipeline (`ingest.py` & `aws_connector.py`)
- **AWS Authentication & Account Discovery Strategy**:
  - **Phase 1 (POC Access Key Authentication & JSON Discovery)**: Reads target AWS Account IDs from `accounts.json` configuration file or Streamlit UI inputs. Connects using AWS Access Key ID, Secret Access Key, and optional Session Token (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) provided in `.env`, `accounts.json`, or UI inputs.
  - **Phase 2 (Enterprise System Account Governance)**: Transitions to a Central System Account IAM Execution Role (AWS Organizations) automatically assuming federated cross-account roles across all onboarded enterprise AWS accounts without storing individual access keys.
- **Inputs**: `accounts.json`, raw billing line items (`aws_cur_export.csv`), ECS container metrics (`ecs_task_metrics.json`), Lambda execution statistics (`lambda_metrics.json`), and S3 storage metrics (`s3_storage_metrics.json`).
- **Target Schema (DuckDB)**:
  - `raw_cost_reports`: `line_item_id`, `usage_start_date`, `resource_id`, `resource_type`, `business_unit`, `daily_cost`, `usage_amount`.
  - `ecs_task_metrics`: `task_arn`, `cluster_name`, `service_name`, `business_unit`, `cpu_reserved`, `memory_reserved`, `cpu_utilization_max`, `memory_utilization_max`, `launch_type`, `has_security_sidecar`.
  - `lambda_metrics`: `function_arn`, `function_name`, `business_unit`, `memory_allocated_mb`, `memory_max_used_mb`, `avg_duration_ms`, `invocations_count`, `timeout_seconds`.
  - `s3_storage_metrics`: `bucket_name`, `business_unit`, `kms_key_arn`, `is_kms_encrypted`, `storage_bytes_standard`, `storage_bytes_glacier`, `object_count`, `has_lifecycle_policy`.
  - `candidate_recommendations`: `recommendation_id`, `resource_id`, `service_type`, `estimated_monthly_savings`, `proposed_fix_description`, `compliance_status`, `guardrail_rule_triggered`.

### 2. Natural Language Query Agent (`query_agent.py`)
- **LLM Abstraction**: Pluggable provider interface utilizing Groq API (`llama-3.3-70b-versatile`) in Phase 1 with seamless transition to Anthropic Claude 3.5 Sonnet.
- **Two-Stage Processing**:
  - **Stage 1 (Text-to-SQL)**: Accepts natural language questions + DuckDB schema context -> outputs valid ANSI/DuckDB SQL.
  - **Stage 2 (Context Synthesis)**: Executes SQL against DuckDB -> passes tabular result set + original question to LLM -> outputs human-readable business explanation.

### 3. Proactive Waste Analyzer (`analyzer.py`)
- Autonomous multi-dimensional pattern evaluation:
  - **ECS (EC2)**: Flags tasks where CPU/Memory reservation > 4x max peak usage.
  - **Lambda**: Flags functions with allocated memory > 2x max memory used or excessive provisioned concurrency.
  - **S3 Storage**: Flags buckets with Standard storage age > 90 days lacking lifecycle policies.
  - **Cross-BU Optimization Sharing**: Identifies matching architectural waste patterns across distinct business units.

### 4. Banking Security & Compliance Guardrails Engine (`guardrails.py`)
- Intercepts candidate waste optimizations before presentation or code generation:
  - `RULE_S3_KMS`: Rejects deletion/downgrade of AWS Managed KMS keys (`REJECTED_KMS_MANDATE`).
  - `RULE_ECS_SIDECARS`: Mandates retention of security monitoring sidecars in `AWS::ECS::TaskDefinition`.
  - `RULE_LAMBDA_BOUNDS`: Enforces minimum memory buffers and telemetry/tracing wrappers (AWS X-Ray).
  - `RULE_NO_PUBLIC_ACCESS`: Enforces `PublicAccessBlockConfiguration` on S3 buckets.

### 5. IaC Remediation & Service Catalog Generator (`iac_generator.py`)
- Transforms approved recommendations into:
  - `cloudformation_template.yaml`: Compliant CloudFormation code preserving KMS keys and security rules.
  - `service_catalog_product.json`: AWS Service Catalog Product definition artifact with parameter schema.

### 6. Interactive Streamlit UI Portal (`app.py`)
- **Sidebar**: LLM connection status, DuckDB load indicator, **AWS Account Selector / Account ID Input**, **AWS Access Keys Status**, Business Unit filter, Banking Guardrails Mode toggle.
- **Tab 1: Chat Assistant**: Plain-English Q&A with SQL execution toggle.
- **Tab 2: Proactive Savings Dashboard**: Filtered recommendation cards with estimated savings ($) and compliance badges.
- **Tab 3: Guardrail Audit Log**: Real-time log of rejected unsafe optimizations.
- **Tab 4: CloudFormation Studio**: Interactive code viewer with copy/download controls and Service Catalog instructions.


---

## Week-by-Week Implementation Plan

### Week 1 — Repository Setup & Data Ingestion Engine ("Ingest the Cloud")
- [x] Create repository structure (`data/raw/`, `data/processed/`, `docs/`).
- [ ] Write `requirements.txt` with dependencies (`duckdb`, `groq`, `streamlit`, `pandas`, `pyyaml`, `python-dotenv`).
- [ ] Create synthetic multi-service sample datasets in `data/raw/`:
  - `aws_cur_export.csv` (Multi-BU billing data across Marketing, Engineering, DataScience).
  - `ecs_task_metrics.json` (Container metrics, vCPU/RAM reservation vs usage, sidecar flags).
  - `lambda_metrics.json` (Serverless invocation metrics, memory allocation vs max used).
  - `s3_storage_metrics.json` (Storage class distribution, object age, KMS encryption flags).
- [ ] Implement `ingest.py` to parse, clean, normalize, and load datasets into `data/processed/cloudintel.duckdb`.
- [ ] Write schema verification helper to validate DuckDB tables and row counts.

### Week 2 — Natural Language Query Agent ("Speak Business, Query Cloud")
- [ ] Build LLM provider wrapper (`llm_client.py`) connecting to Groq Cloud API (`llama-3.3-70b-versatile`).
- [ ] Implement `query_agent.py`:
  - Stage 1: Text-to-SQL translation with DuckDB system prompts.
  - DuckDB query execution layer.
  - Stage 2: Contextual synthesis prompt.
- [ ] Conduct test suite across 10+ natural language questions covering ECS, Lambda, S3, and cost spikes across BUs.

### Week 3 — Proactive Waste Analyzer & Banking Guardrails Engine ("Find Compliant Waste")
- [ ] Implement `analyzer.py` with multi-dimensional analytical SQL queries for ECS container sizing, Lambda memory tuning, and S3 lifecycle transitions.
- [ ] Implement `guardrails.py` with policy rule validation (`RULE_S3_KMS`, `RULE_ECS_SIDECARS`, `RULE_LAMBDA_BOUNDS`, `RULE_NO_PUBLIC_ACCESS`).
- [ ] Integrate analyzer with guardrails to populate `candidate_recommendations` table with `APPROVED` or `REJECTED_*` status.
- [ ] Add cross-BU pattern matching logic to flag recurring multi-BU waste.

### Week 4 — Remediation Engine & Streamlit UI Demo ("Ask, Analyze, Automate")
- [ ] Implement `iac_generator.py` for CloudFormation YAML generation preserving KMS & security sidecars, plus Service Catalog JSON metadata.
- [ ] Implement `app.py` Streamlit UI with 4 main tabs (Chat, Dashboard, Audit Log, CloudFormation Studio).
- [ ] Verify full end-to-end flow: Ingest -> Query -> Analyze -> Filter Guardrails -> Generate CloudFormation -> Render UI.
- [ ] Prepare live POC demonstration scripts for Amazon ECS, AWS Lambda, and Amazon S3.

---

## Verification & Testing Plan

### Automated Verification
1. **Data Ingestion Verification**:
   - Execute `python ingest.py` and confirm zero errors.
   - Verify DuckDB table creation and record counts in `cloudintel.duckdb`.
2. **Guardrail Enforcement Verification**:
   - Run unit test simulating an LLM attempt to remove an S3 KMS key.
   - Assert `guardrails.py` returns `REJECTED_KMS_MANDATE` and logs violation.
3. **IaC Generator Verification**:
   - Generate CloudFormation template for S3 lifecycle rule and verify `ServerSideEncryptionRule` with KMS key ARN remains present in output YAML.

### Manual Verification
1. Launch Streamlit UI via `streamlit run app.py`.
2. Test Natural Language Q&A in Tab 1 with questions such as:
   - *"Which Business Unit spent the most on Lambda last month?"*
   - *"List all S3 buckets storing over 1 TB without lifecycle policies."*
3. Review Proactive Savings Cards in Tab 2 and verify compliance pass badges.
4. Verify rejected candidates (e.g. KMS key removal attempts) appear in Tab 3 Compliance Audit Log.
5. Click "Generate Fix" for an approved recommendation in Tab 4 and review generated CloudFormation YAML code.
