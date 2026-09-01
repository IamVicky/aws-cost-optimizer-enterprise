# Project: CloudIntel — Enterprise AI FinOps Platform

## The Big Problem
Every enterprise cloud strategy fails the same way financially: cloud consumption is decentralized across multiple Business Units (BUs), leading to massive, untracked waste (often 20-35% of total spend). Information is siloed. Existing cloud management tools are highly technical, throwing JSON logs and complex graphs at business stakeholders who just want to know, "Why did our bill spike yesterday?" Furthermore, when one BU solves a complex cost optimization problem, that knowledge never transfers to other BUs.

In a banking environment, cost optimization is further complicated by strict enterprise security and compliance standards, as well as institutional infrastructure provisioning processes. Optimization tools often make unsafe suggestions (e.g., removing KMS keys, stripping logging sidecars, or turning off encryption) to save money. Furthermore, provisioning in our bank is strictly governed by **AWS Service Catalog** using compliant **AWS CloudFormation** templates rather than raw ad-hoc scripts or unmanaged IaC tools. CloudIntel solves this by embedding an intelligent **Banking Security & Compliance Guardrails Layer** directly into the AI recommendation and CloudFormation template generation engine.

## Implementation Strategy: Two-Phase Approach
To ensure rapid validation, immediate business value, and smooth stakeholder onboarding, development will proceed in two distinct phases:

- **Phase 1: Proof of Concept (POC) — Multi-Service Focus (ECS-EC2, Lambda, S3) & Live Demo**
  Implement the end-to-end automation pipeline using zero-cost / lightweight open-source tools tailored for key cloud service patterns: **Amazon ECS (EC2 Launch Type)** container workloads, **AWS Lambda** serverless compute, and **Amazon S3** object storage. This includes ingesting multi-service metrics and cost data into a local DuckDB analytical database, answering natural language questions via Groq API, detecting resource waste filtered through banking compliance guardrails, generating compliant AWS CloudFormation remediation templates (ready for AWS Service Catalog integration), and demonstrating the complete flow via a Streamlit UI demo.
- **Phase 2: Enterprise Multi-Resource Expansion (Production Stack)**
  Upon successful demonstration and validation of the multi-service POC, transition to enterprise-grade infrastructure (Anthropic Claude 3.5 Sonnet, AWS Athena/Redshift) and expand the pipeline across all remaining AWS resource categories (EC2 instances, RDS databases, DynamoDB, and Network/NAT Gateways).

## Tooling Strategy Matrix: Phase 1 (POC) vs Phase 2 (Enterprise)

| Component | Phase 1: POC (Free Tools & Multi-Service Scope) | Phase 2: Enterprise Production Stack |
| :--- | :--- | :--- |
| **Target Scope** | **Amazon ECS** (EC2 launch type), **AWS Lambda** (Serverless), **Amazon S3** (Storage) | **All AWS Resources** (EC2, S3, RDS, Lambda, DynamoDB, Network) |
| **AI / LLM Engine** | **Groq Cloud API** (`llama-3.3-70b-versatile`) — *100% Free API* | **Anthropic Claude 3.5 Sonnet** — *Enterprise License* |
| **AWS Authentication**| **AWS Access Keys** (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` via `.env` or UI) | **System Account Access** (Central System Account federating all AWS Accounts) |
| **Account Discovery** | **`accounts.json` Configuration** or Interactive Streamlit UI Account Selector | **AWS Organizations / System Account Registry** (Auto-discovers registered Accounts) |
| **Compliance Layer** | **Banking Guardrails Engine** (Enforces KMS encryption, non-degradable security rules) | Enterprise Policy Engine (AWS OPA / Sentinel / AWS Config integration) |
| **Database Pattern** | **DuckDB** (Free in-process OLAP analytical database) | **AWS Athena / Amazon Redshift / Snowflake** |
| **Data Storage / ETL** | Local File Directory (`data/raw/`, `data/processed/`) or AWS S3 Bucket + DuckDB | AWS S3 Bucket + AWS Glue Data Catalog |
| **User Interface** | **Streamlit App** (Local / Streamlit Community Cloud) | Enterprise Web Portal (Streamlit / Next.js on AWS App Runner) |
| **IaC Remediation** | **AWS CloudFormation (YAML/JSON)** & AWS Service Catalog Product Templates | AWS CI/CD Pipeline (AWS Service Catalog Portfolio / CodePipeline) |

## LLM Model Selection Strategy
- **Phase 1 POC Model — Groq API (`llama-3.3-70b-versatile`)**:
  - **Provider & Access**: **Groq Cloud API** (Free Tier access using `llama-3.3-70b-versatile`).
  - **Key Advantages for POC**:
    - **100% Free**: Operates under Groq's free API tier without requiring upfront licensing budget.
    - **Advanced Reasoning & Coding**: Llama 3.3 70B excels at Text-to-SQL translation, multi-dimensional FinOps pattern analysis (CPU/RAM/Concurrency vs Cost), and compliant AWS CloudFormation IaC template generation.
    - **Ultra-Fast Speed**: Powered by Groq LPUs (~300+ tokens/sec) for instant streaming answers during the live POC demo.
    - **Seamless Upgrade Path**: Built using standard OpenAI/Groq API client abstractions, allowing a 1-line configuration swap to Anthropic Claude 3.5 Sonnet once the enterprise license is approved.
- **Phase 2 Production Target — Anthropic Claude 3.5 Sonnet**:
  - Official enterprise target model to be enabled upon POC submission and license approval.

## AWS Account Discovery & Authentication Strategy
- **Phase 1 POC Authentication & Account Discovery**:
  - **Account ID Input**: Target AWS Account IDs are loaded from a JSON configuration file (`accounts.json`) or entered/selected directly in the Streamlit UI.
  - **Access Key Authentication**: Connects using standard AWS Access Key ID, Secret Access Key, and optional Session Token (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) provided in environment variables (`.env`), JSON file, or UI credentials inputs for rapid validation.
  - **Dynamic Mult-Account Polling**: The data pipeline queries metrics and Cost Explorer specifically filtered for the selected Account ID(s).
- **Phase 2 Enterprise Production System Account Governance**:
  - **System Account Access Model**: Transitions to a **Central System Account** (AWS Organizations / Central Management Account).
  - **Central Account Registry**: All target enterprise AWS accounts are registered within the system account.
  - **Federated Role Assumption**: CloudIntel runs under the central System Account IAM Execution Role, automatically assuming federated cross-account roles across all onboarded AWS accounts without storing or handling individual AWS access keys.


## Enterprise Banking Compliance & Security Guardrails Strategy
In banking and financial institutions, AI-driven cost optimization must **never** degrade security, compliance, or data protection standards. CloudIntel incorporates a policy-driven **Banking Guardrails Engine** that intercepts candidate AI recommendations before they are shown to users or converted to CloudFormation templates.

### Key Banking Guardrails Policies:
1. **Mandatory AWS KMS Encryption (S3 & Storage)**:
   - **Rule**: S3 bucket cost optimization (e.g. storage tiering, lifecycle rules, cleanup) must **never** suggest removing or disabling AWS Managed KMS keys (`aws_kms_key` / SSE-KMS).
   - **Action**: If an AI prompt or pattern analyzer attempts to recommend removing KMS encryption to eliminate KMS API costs, the Guardrails Engine automatically rejects the recommendation with a policy violation flag (`REJECTED_KMS_MANDATE`).
2. **Non-Degradable Security Sidecars (ECS EC2)**:
   - **Rule**: ECS Task definition resizing (CPU/Memory adjustments) must preserve mandatory container sidecars (e.g., security monitoring agents, log shippers, endpoint detection).
   - **Action**: CloudFormation generator ensures task definition resources (`AWS::ECS::TaskDefinition`) retain all compliance sidecar allocations.
3. **Lambda Execution & Timeout Guardrails**:
   - **Rule**: Memory optimization for AWS Lambda must maintain required execution concurrency buffers and telemetry/tracing wrappers (AWS X-Ray / banking telemetry layers).
4. **AWS Service Catalog Integration & Zero Public Access**:
   - **Rule**: Generated CloudFormation templates must adhere to standard banking Service Catalog parameters and explicitly enforce `PublicAccessBlockConfiguration` with `BlockPublicAcls: true` and `BlockPublicPolicy: true`.

---

## Database Pattern Selection Strategy
- **Phase 1 POC Database — DuckDB (Embedded Analytical OLAP Engine)**:
  - **Pattern**: In-process OLAP (Online Analytical Processing) database file stored locally in `data/processed/cloudintel.duckdb` (or direct S3 querying via DuckDB `httpfs`).
  - **Why DuckDB for POC**:
    - **Zero Cost & Zero Infra**: 100% free open-source Python library (`pip install duckdb`). No server setup, Docker containers, or cloud instance costs required.
    - **Blazing Fast Analytical Performance**: Specifically engineered for columnar analytical SQL queries on raw CSV/JSON billing data, ECS task EC2 container logs, Lambda execution metrics, and S3 storage metrics. Performs aggregations 10–100x faster than traditional databases.
    - **ANSI SQL Compliance**: Standard SQL support ensures LLMs (Groq `llama-3.3-70b-versatile`) generate accurate, standard SQL queries without dialect errors.
    - **Seamless Enterprise Portability**: SQL queries written against DuckDB tables can be reused directly in AWS Athena or Redshift for Phase 2.
- **Phase 2 Production Database — AWS Athena / Amazon Redshift**:
  - Serverless cloud data lake query engine querying raw CUR Parquet files directly in AWS S3.

---

## Goal
Build an end-to-end Enterprise AI Platform powered by an advanced Large Language Model (like Claude/Gemini). The system must ingest raw cloud billing and usage data across ECS (EC2), Lambda, and S3, translate natural language questions from business stakeholders into complex cloud queries, perform multi-dimensional reasoning to spot cross-BU waste patterns while enforcing enterprise banking security guardrails, and automatically generate compliant AWS CloudFormation templates (ready for AWS Service Catalog) to remediate the issues.

*Not just a dashboard. Not a generic code copilot. A contextual, compliance-aware FinOps intelligence engine that speaks business logic and writes compliant AWS CloudFormation code.*

---

## Final System Flow

```
Ingest Cloud Cost & Usage Reports (CUR), ECS (EC2) Metrics, Lambda Metrics, & S3 Storage Stats
↓
AI translates natural language into complex data queries (Text-to-SQL)
↓
AI analyzes multi-dimensional patterns (cost + CPU/memory + concurrency + storage age)
↓
Banking Guardrails Engine validates recommendations (Enforces KMS encryption, security controls)
↓
AI auto-generates proactive insights & compliant AWS CloudFormation templates (Service Catalog ready)
↓
Business & Engineering query it via an interactive Streamlit chat interface
↓
Phase 1: Validate via Multi-Service (ECS-EC2, Lambda, S3) POC Demo → Phase 2: Enterprise Rollout
```

---

## Week-by-Week Problem Statements (POC First -> Enterprise Scaling)

Each week is a self-contained milestone. Build it first for **Amazon ECS (EC2 Launch Type)**, **AWS Lambda**, and **Amazon S3** to complete the POC demo, then extend to all cloud resources.

### Week 1 — The Data Pipeline: "Ingest the Cloud"
#### Problem
Cloud billing and metric data is massive, granular, and hard to parse. You need a centralized pipeline to capture Cost & Usage Reports (CUR) and resource metrics across compute (ECS on EC2), serverless (Lambda), and storage (S3) so the AI has a factual foundation to query against.

#### Build Focus (POC Scope: ECS-EC2, Lambda, S3)
- Set up the project structure:
  - `data/raw/` — raw cloud billing exports (CSV/JSON) containing ECS EC2 container metrics, Lambda invocations/duration, S3 storage stats (Standard, Glacier, KMS usage), and AWS spend.
  - `data/processed/` — cleaned, aggregated data ready for querying.
- Write a Python ingestion script (`ingest.py`) that:
  - Reads raw cost data and resource logs (ECS tasks on EC2, Lambda functions, S3 bucket storage metrics).
  - Normalizes data into a standard schema (`Resource ID`, `Resource Type`, `BU Tag`, `Daily Cost`, `Utilization %`, `KMS Encryption Flag`).
  - Stores it in a lightweight local database (DuckDB) for fast querying.
- Test on a sample dataset of real/mocked cloud logs representing at least 3 distinct "Business Units" (e.g., Marketing, Engineering, DataScience).

#### Deliverable ("Ship the Ingestion Engine")
A working data pipeline where a single command cleans and loads raw ECS (EC2), Lambda, S3, and cloud logs into a structured, queryable database.

#### Acceptance Criteria
- `data/raw/` and `data/processed/` structure exists.
- Script successfully parses CSV/JSON billing exports (including ECS EC2 task metrics, Lambda duration/memory, and S3 storage classes/KMS flags).
- Data is standardized into a queryable local database (DuckDB).
- Contains mocked or anonymized data for at least 3 distinct BUs.

---

### Week 2 — The Translator: "Speak Business, Query Cloud"
#### Problem
Business leaders ask questions like, "Why did the marketing team's Lambda execution and S3 costs spike last week?" Existing tools require SQL or complex dashboard filters to answer this. You need the AI to translate human intent into precise database queries.

#### Build Focus (POC Scope: ECS-EC2, Lambda, S3)
- **2.1 — Intent Parsing (The NLP Layer)**:
  - Pass user plain-English questions (e.g., "Show me top 5 most expensive Lambda functions across BUs", "Which S3 buckets are missing lifecycle policies?") to the LLM.
  - Translate the question into a valid SQL query against your local cost database.
- **2.2 — Context Synthesis (The Explainer)**:
  - Execute the AI-generated SQL query.
  - Feed query results back to the LLM to generate human-readable, business-contextual answers (e.g., "The S3 bucket for Marketing grew by 5 TB in uncompressed logs while using AWS Managed KMS encryption; no lifecycle rules are currently configured").

#### Deliverable ("Ship the Natural Language FinOps Agent")
A pipeline that takes plain-English questions about ECS, Lambda, S3, and cloud spend, writes the query, fetches the data, and returns a contextual answer.

#### Acceptance Criteria
- Natural language input successfully maps to executable SQL.
- Queries execute against the database from Week 1 without errors.
- System returns a plain-text, contextual explanation of costs across ECS, Lambda, and S3.
- Tested successfully on 10+ varied business questions.

---

### Week 3 — The Intelligence Engine & Banking Guardrails: "Find Compliant Waste"
#### Problem
Reactive Q&A is good, but proactive optimization is better. The system needs to analyze data autonomously for waste categories using multi-dimensional reasoning (cost + utilization + business hours) **while strictly respecting banking security guardrails**.

#### Build Focus (POC Scope: ECS-EC2, Lambda, S3)
- **3.1 — Multi-Service Pattern Recognition Logic**:
  - Write an analysis script (`analyzer.py`) that checks:
    - **ECS (EC2)**: Allocated container vCPU/RAM vs actual peak usage.
    - **Lambda**: Over-provisioned function memory (e.g. 3 GB allocated vs 256 MB used) and idle concurrency allocations.
    - **S3 Storage**: Inactive Standard storage objects suitable for Glacier/IA lifecycle policies.
- **3.2 — Enterprise Banking Guardrail Filtering**:
  - Integrate guardrail verification (`guardrails.py`): Ensure recommendations **never** propose removing S3 KMS keys, disabling bucket access logging, or stripping ECS security sidecars. Filter out non-compliant candidate suggestions.
- **3.3 — Cross-BU Learning**:
  - Implement logic where the LLM scans for identical architectural waste across BUs. If BU 'A' optimizes Lambda memory sizing safely, the LLM flags similar opportunities in BU 'B'.

#### Deliverable ("Ship the Proactive Compliance-Aware Analyst")
An automated job that scans the database, identifies complex multi-service optimization opportunities, filters them against banking guardrails, and flags compliant savings.

#### Acceptance Criteria
- Script successfully identifies waste in ECS (EC2), Lambda, and S3 storage.
- Banking Guardrails Engine successfully blocks unsafe recommendations (e.g. explicitly rejects removing KMS keys on S3 buckets).
- System identifies a shared multi-service inefficiency across two different BUs.

---

### Week 4 — The Fixer & POC Demo: "Ask, Analyze, Automate"
#### Problem
Identifying waste is only half the battle; engineering teams need actual code to fix it. You need to wire the intelligence engine to a compliance-checked AWS CloudFormation generator (ready for AWS Service Catalog integration), package it into a clean UI, and present the POC demo.

#### Build Focus (Phase 1 POC Demo + System Integration)
- **4.1 — The Remediation Engine (Guardrail Compliant & Service Catalog Ready)**:
  - Instruct LLM to generate exact, compliant AWS CloudFormation YAML/JSON templates or Python (Boto3) scripts for approved optimizations (e.g. update `AWS::ECS::TaskDefinition` container limits, adjust `AWS::Lambda::Function` memory settings, add `AWS::S3::Bucket` lifecycle configuration rules while preserving `BucketEncryption` with `ServerSideEncryptionRule` using KMS).
- **4.2 — UI & POC Demo Application**:
  - Assemble into a Streamlit app (`app.py`):
    - Interactive Chat Interface for FinOps Q&A.
    - Proactive Cost-Saving Recommendations Dashboard (highlighting guardrail-compliant quick wins).
    - Banking Compliance Badge & Policy Violation logs for rejected unsafe fixes.
    - "Generate Fix" button outputting ready-to-apply AWS CloudFormation templates compatible with AWS Service Catalog products.
  - Deliver a live POC demonstration focusing on multi-service cost optimization (ECS-EC2, Lambda, S3).
- **4.3 — Phase 2 Enterprise Rollout**:
  - Following successful POC demo approval, expand all modules (`ingest.py`, `query_agent.py`, `analyzer.py`, `iac_generator.py`) to encompass all remaining AWS resources (EC2 instances, RDS, DynamoDB, Networking).

#### Deliverable ("Ship CloudIntel" — POC Demo + Complete Platform)
Deploy the complete system—data ingestion → natural language Q&A → guardrail-filtered waste detection → compliant CloudFormation template generation—wired into a Streamlit app and demonstrated live for ECS (EC2), Lambda, and S3 before full enterprise release.

#### Acceptance Criteria
- LLM successfully generates valid CloudFormation/Python remediation scripts preserving mandatory KMS keys, Service Catalog formatting, and security policies.
- Streamlit app displays search/chat bar, recommendation cards, and compliance status indicators.
- Live POC demo executed successfully on ECS (EC2), Lambda, and S3 resources.
- Full end-to-end flow verified: ingest → query → analyze & filter guardrails → generate CloudFormation.

---

## Final Deliverables (Whole Project)
1. **Multi-Service POC Live Demo**: Functional demonstration of end-to-end cost optimization for Amazon ECS (EC2), AWS Lambda, and Amazon S3.
2. **Banking Compliance Guardrails Integration**: Active rule filter protecting security controls (S3 KMS encryption, logging, sidecars).
3. **Public/Internal Repo**: Clean code base with comprehensive `README.md` and setup instructions.
4. **Live Deployed Application**: Interactive chat + actionable cost recommendations + compliant CloudFormation template generator for AWS Service Catalog.
5. **Full Multi-Resource Coverage**: Extended post-POC automation for EC2, RDS, DynamoDB, and Networking.

---

## Suggested Repo Structure
```plaintext
cloudintel/
├── data/
│   ├── raw/              # Week 1: Raw cloud cost exports (ECS EC2 metrics, Lambda metrics, S3 stats + CUR)
│   └── processed/        # Week 1: Cleaned SQLite/DuckDB database
├── ingest.py             # Week 1: ETL script for multi-service metrics & billing logs
├── query_agent.py        # Week 2: LLM SQL generation and context explainer
├── analyzer.py           # Week 3: Proactive waste pattern recognition (ECS, Lambda, S3)
├── guardrails.py         # Week 3: Enterprise Banking Compliance & Security Policy Engine
├── iac_generator.py      # Week 4: Compliant CloudFormation / Service Catalog remediation generator
├── app.py                # Week 4: Streamlit UI (Chat + Insights + Compliance + CloudFormation Studio)
├── requirements.txt
└── README.md
```

## Suggested Build Order
1. **Scaffold Repo & Environment**: Directory structure + `requirements.txt`
2. **`ingest.py` (POC: ECS-EC2, Lambda, S3 focus)**: Load raw CSV/JSON data into database (Week 1)
3. **`query_agent.py`**: Test natural language questions to SQL translation and explanation (Week 2)
4. **`analyzer.py` & `guardrails.py`**: Run multi-dimensional reasoning prompts and filter candidates against banking security rules (Week 3)
5. **`iac_generator.py`**: Test compliant CloudFormation generation for ECS container resizing, Lambda memory tuning, and S3 lifecycle rules (Week 4.1)
6. **`app.py`**: Streamlit app combining chat, recommendations, compliance status, and CloudFormation template viewer (Week 4.2)
7. **Conduct POC Demo**: Present multi-service cost optimization automation demo to stakeholders
8. **Phase 2 Expansion**: Extend ingestion, reasoning, and CloudFormation generation across all remaining AWS resource types
9. **Finalize Documentation**: Update `README.md` and final deliverables