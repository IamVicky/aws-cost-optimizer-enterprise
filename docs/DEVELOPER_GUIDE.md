# CloudIntel — Developer & Contributor Guide

Welcome to the **CloudIntel Developer Guide**. This document provides detailed technical specifications, architectural breakdowns, setup instructions, extension patterns, and testing guidelines for software engineers, DevOps/FinOps developers, and AI engineers working on the CloudIntel codebase.

---

## 1. System Architecture & Codebase Overview

CloudIntel is structured as a modular, loosely-coupled Python application:

```plaintext
cloudintel/
├── accounts.json                 # Target AWS Account configuration registry
├── data/
│   ├── raw/                      # Raw billing CSVs, ECS task metrics, Lambda & S3 stats
│   │   ├── aws_cur_export.csv
│   │   ├── ecs_task_metrics.json
│   │   ├── lambda_metrics.json
│   │   └── s3_storage_metrics.json
│   └── processed/                # Cleaned analytical DuckDB database
│       └── cloudintel.duckdb
├── docs/                         # Specifications, architecture, & operational guides
│   ├── PROBLEM_STATEMENT.md
│   ├── ARCHITECTURE.md
│   ├── Implementation-plan.md
│   ├── deployment-plan.md
│   ├── edge-case.md
│   ├── DEVELOPER_GUIDE.md        # This document
│   └── USER_GUIDE.md             # End-user operational guide
├── tests/                        # Automated unit test suite
│   ├── test_guardrails.py
│   └── test_sql_safety.py
├── aws_connector.py              # Live AWS Access Key & Cost Explorer Connector
├── ingest.py                     # Week 1: Multi-service ETL & DuckDB ingestion engine
├── query_agent.py                # Week 2: Text-to-SQL & context synthesis agent
├── analyzer.py                   # Week 3: Proactive multi-service waste analyzer
├── guardrails.py                 # Week 3: Banking Security & Compliance Policy Engine
├── iac_generator.py              # Week 4: Compliant CloudFormation & Service Catalog generator
├── app.py                        # Week 4: Streamlit interactive web application
├── llm_client.py                 # Pluggable LLM provider client (Groq / Failover)
├── aws_nonprod_deploy.yaml       # Non-prod AWS App Runner CloudFormation deployment template
├── aws_spoke_account_role.yaml   # Multi-account spoke cross-account IAM role StackSet template
├── requirements.txt              # Project dependencies
└── README.md                     # Project quickstart guide
```

---

## 2. Core Module Breakdown

### 2.1 Data Pipeline Engine (`ingest.py` & `aws_connector.py`)
- **`aws_connector.py`**:
  - Encapsulates `boto3` calls to query live AWS APIs (**AWS Cost Explorer**, **CloudWatch**, **ECS**, **Lambda**, **S3**).
  - Authenticates via AWS Access Keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) or IAM execution roles.
  - Loads target Account IDs dynamically from `accounts.json`.
- **`ingest.py`**:
  - Initializes DuckDB columnar database at `data/processed/cloudintel.duckdb`.
  - Parses raw CSV/JSON files or live AWS API responses.
  - Normalizes schemas into 5 core tables:
    - `raw_cost_reports`
    - `ecs_task_metrics`
    - `lambda_metrics`
    - `s3_storage_metrics`
    - `candidate_recommendations`

### 2.2 LLM Client & Failover Manager (`llm_client.py`)
- Wraps Groq Cloud API (`Groq` SDK).
- Implements **automatic model failover** across active Groq models (`llama-3.3-70b-versatile`, `llama3-70b-8192`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma2-9b-it`).
- Provides a **heuristic fallback engine** if API keys are absent or offline, enabling seamless local developer testing.

### 2.3 Natural Language Query Agent (`query_agent.py`)
- **Stage 1 (Text-to-SQL)**: Converts natural language questions into valid DuckDB ANSI SQL SELECT statements.
- **AST SQL Safety Validator (`validate_sql_safety`)**: Evaluates generated SQL queries to block non-SELECT statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`).
- **Stage 2 (Context Synthesis)**: Takes SQL result dataframes and generates human-readable executive summaries.

### 2.4 Proactive Waste Analyzer (`analyzer.py`)
- Executes analytical SQL queries over DuckDB tables:
  - **ECS**: CPU/Memory reservation vs max peak utilization (`cpu_utilization_max < 15.0`).
  - **Lambda**: Allocated memory vs peak memory used (`memory_allocated_mb >= memory_max_used_mb * 2`).
  - **S3 Storage**: Standard storage objects > 90 days lacking lifecycle policies.
- Passes candidate recommendations to `guardrails.py` for policy vetting before writing to `candidate_recommendations`.

### 2.5 Banking Security & Compliance Guardrails Engine (`guardrails.py`)
- Intercepts all candidate recommendations against 4 banking policies:
  - `RULE_S3_KMS`: Rejects deleting or detaching AWS Managed KMS keys (`REJECTED_KMS_MANDATE`).
  - `RULE_ECS_SIDECARS`: Rejects stripping container security sidecars (`REJECTED_SECURITY_SIDECAR_OMISSION`).
  - `RULE_LAMBDA_BOUNDS`: Enforces minimum memory thresholds and X-Ray telemetry retention (`REJECTED_LAMBDA_TELEMETRY_BOUNDS`).
  - `RULE_NO_PUBLIC_ACCESS`: Enforces `PublicAccessBlockConfiguration` (`REJECTED_PUBLIC_ACCESS_EXPOSURE`).

### 2.6 IaC & Service Catalog Generator (`iac_generator.py`)
- Converts approved recommendations into compliant **AWS CloudFormation YAML** code (`cloudformation_template.yaml`).
- Produces **AWS Service Catalog Product Definition JSON** metadata (`service_catalog_product.json`).

### 2.7 User Interface (`app.py`)
- Built with Streamlit (`streamlit`).
- Features a system control sidebar (Account Selector, Credentials status, BU filter, Guardrails toggle) and 4 interactive tabs.

---

## 3. Developer Environment Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Virtualenv (`venv` or Conda)

### Setup Steps
```bash
# 1. Clone repository
git clone https://github.com/your-org/cloudintel.git
cd cloudintel

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Activate virtual environment (Linux/macOS)
# source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Configure `.env`
Create a `.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL_NAME=llama-3.3-70b-versatile

# AWS Non-Prod Access Keys (Optional for live AWS polling)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_optional_session_token
AWS_DEFAULT_REGION=us-east-1

GUARDRAILS_MODE=ENFORCE
ACCOUNTS_CONFIG_PATH=accounts.json
DUCKDB_PATH=data/processed/cloudintel.duckdb
```

---

## 4. How to Extend CloudIntel

### 4.1 Adding a New Cloud Service (e.g., Amazon RDS / DynamoDB)
1. **Extend DuckDB Schema (`ingest.py`)**:
   Add a new table creation query (e.g. `rds_database_metrics`).
2. **Update Data Ingestion (`ingest.py` & `aws_connector.py`)**:
   - Add sample JSON dataset in `data/raw/rds_database_metrics.json`.
   - Add `boto3.client('rds')` describe calls in `aws_connector.py`.
3. **Add Waste Scanner Logic (`analyzer.py`)**:
   Add analytical query checking idle connections / unattached storage -> append to `candidates`.
4. **Update Guardrail Policies (`guardrails.py`)**:
   Add rules checking storage encryption or snapshot retention.

### 4.2 Adding a New Banking Compliance Guardrail Rule
1. Open `guardrails.py`.
2. Add a new rule evaluation block inside `evaluate_recommendation()`:
   ```python
   # Rule 5: Database Storage Encryption Mandate (RULE_RDS_KMS)
   if "RDS" in service_type and "UNENCRYPTED" in proposed_fix:
       rec["compliance_status"] = "REJECTED_RDS_KMS_MANDATE"
       rec["guardrail_rule_triggered"] = "RULE_RDS_KMS"
       return rec
   ```
3. Add unit test in `tests/test_guardrails.py`.

### 4.3 Adding a New LLM Provider (e.g. Anthropic Claude 3.5 Sonnet / Azure OpenAI)
1. Open `llm_client.py`.
2. Update `call_llm()` to check provider environment variables (`ANTHROPIC_API_KEY` / `AZURE_OPENAI_KEY`).
3. Instantiates `anthropic.Anthropic()` client and formats messages according to Claude messages API.

---

## 5. Testing & Debugging

### Running Unit Tests
```bash
python -m unittest discover tests
```

### Individual Test Files
```bash
python -m unittest tests/test_guardrails.py
python -m unittest tests/test_sql_safety.py
```

### Direct Module Execution for Debugging
```bash
# Test ETL Ingestion
python ingest.py

# Test Live AWS Connector
python aws_connector.py

# Test Waste Analyzer & Guardrails
python analyzer.py

# Test Query Agent (Text-to-SQL)
python query_agent.py

# Test IaC Generator
python iac_generator.py
```

---

## 6. Coding Standards & Git Workflow

- **Style Guide**: PEP 8 compliance. Use explicit type hints where applicable.
- **Console Printing**: Use standard ASCII text strings (e.g., `[INFO]`, `[WARNING]`, `[SUCCESS]`) instead of unicode emojis to avoid Windows console `cp1252` encoding errors.
- **Git Branching**: Feature branches branched off `main` or `aws-cost-opti`. Never commit secret credentials or `.env` files to git.
