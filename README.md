# CloudIntel — Enterprise AI FinOps Platform

CloudIntel is an enterprise-grade AI FinOps intelligence platform designed to eliminate cloud waste across decentralized Business Units (BUs) while strictly enforcing financial institution security, KMS encryption mandates, and compliance guardrails.

---

## Key Features

- **Multi-Service Focus (Phase 1 POC)**: Ingests & analyzes **Amazon ECS (EC2 launch type)** container workloads, **AWS Lambda** serverless compute, and **Amazon S3** object storage.
- **100% Free / Lightweight POC Stack**:
  - **Groq Cloud API** (`llama-3.3-70b-versatile`) — High-speed LPU inference engine with automatic multi-model failover.
  - **DuckDB** (`data/processed/cloudintel.duckdb`) — In-process columnar OLAP analytical database.
  - **Streamlit Web UI** — Interactive multi-tab portal with AWS Account Selector.
- **Flexible AWS Authentication & Multi-Account Selection**:
  - **Phase 1 POC**: Connects via **AWS Access Keys** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) for rapid validation. Target Account IDs are selected interactively or loaded from `accounts.json`.
  - **Phase 2 Enterprise Production**: Central System Account Governance model (AWS Organizations) assuming federated cross-account roles.
- **Banking Security & Compliance Guardrails Engine**: Intercepts candidate recommendations before presentation to ensure KMS keys are never deleted, security sidecars are preserved, and public access blocks are enforced.
- **AWS CloudFormation & Service Catalog Studio**: Auto-generates compliant AWS CloudFormation YAML templates and AWS Service Catalog Product definition metadata JSON.

---

## Environment Configuration (`.env`)

Create a `.env` file in the root of your project directory (`j:\AI_Learnings\ai-aws-cost\Automation\.env`):

```env
# 1. Groq API Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL_NAME=llama-3.3-70b-versatile

# 2. AWS Non-Prod Access Key Credentials (Uncomment to enable live AWS account polling)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_SESSION_TOKEN=your_optional_session_token_here
AWS_DEFAULT_REGION=us-east-1

# 3. Application & Compliance Settings
GUARDRAILS_MODE=ENFORCE
ACCOUNTS_CONFIG_PATH=accounts.json
DUCKDB_PATH=data/processed/cloudintel.duckdb
```

---

## Target Account Mapping (`accounts.json`)

Configure your target AWS accounts in `accounts.json`:

```json
[
  {
    "account_id": "123456789012",
    "account_name": "NonProd-Marketing-Account",
    "environment": "nonprod",
    "region": "us-east-1"
  },
  {
    "account_id": "987654321098",
    "account_name": "NonProd-Engineering-Dev",
    "environment": "nonprod",
    "region": "us-east-1"
  }
]
```

---

## Repository Structure

```plaintext
cloudintel/
├── accounts.json                 # Target AWS account configuration registry
├── data/
│   ├── raw/                      # Raw billing CSVs, ECS task metrics, Lambda & S3 stats
│   │   ├── aws_cur_export.csv
│   │   ├── ecs_task_metrics.json
│   │   ├── lambda_metrics.json
│   │   └── s3_storage_metrics.json
│   └── processed/                # Cleaned analytical DuckDB database
│       └── cloudintel.duckdb
├── docs/                         # Specification & architecture documentation
│   ├── PROBLEM_STATEMENT.md      # Problem statement & milestone scope
│   ├── ARCHITECTURE.md           # System architecture specification
│   ├── Implementation-plan.md   # Week-by-week technical implementation roadmap
│   ├── deployment-plan.md       # Operational deployment guide (POC to Production)
│   └── edge-case.md              # Corner scenarios & risk mitigation specification
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
└── README.md                     # Project documentation & quickstart guide
```

---

## Quickstart Guide

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Activate virtual environment (Linux/macOS)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Data Ingestion Pipeline (ETL)
```bash
# Synthetic / Offline Mode (Default)
python ingest.py

# Live AWS Non-Prod Mode (Uses AWS Access Keys from .env)
python ingest.py --use-aws
```

### 3. Run Proactive Waste Analyzer & Guardrails Interceptor
```bash
python analyzer.py
```

### 4. Launch Streamlit Portal Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Automated Unit Testing

Run the automated test suite covering AST SQL safety checks and banking guardrail enforcement:
```bash
python -m unittest discover tests
```
