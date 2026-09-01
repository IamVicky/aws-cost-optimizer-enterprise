# Deployment Plan — CloudIntel: Enterprise AI FinOps Platform

## Executive Summary & Vision

This document details the deployment operational plan for **CloudIntel**, an enterprise-grade AI FinOps intelligence platform. It outlines the step-by-step procedure for deploying, configuring, hosting, operating, and promoting CloudIntel across environments—from **Phase 1 (Proof of Concept Local/Sandbox Deployment)** to **Phase 1.5 (Non-Prod AWS Account Integration)** and **Phase 2 (Enterprise Banking Cloud Production)**.

This plan integrates requirements from [`docs/PROBLEM_STATEMENT.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/PROBLEM_STATEMENT.md), [`docs/ARCHITECTURE.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/ARCHITECTURE.md), and [`docs/Implementation-plan.md`](file:///j:/AI_Learnings/ai-aws-cost/Automation/docs/Implementation-plan.md).

---

## Deployment Strategy & Multi-Phase Model

CloudIntel deployment is structured in three sequential phases to guarantee zero initial cloud infrastructure cost, zero risk to live workloads, and complete validation before enterprise rollout:

```
[ Phase 1: POC Local / Sandbox ]
  ├── Embedded DuckDB OLAP
  ├── Groq LPU API (llama-3.3-70b-versatile)
  ├── Local Streamlit Portal (Port 8501)
  └── Local Synthetic File Ingestion (data/raw -> data/processed)
           │
           ▼ (Validation & Non-Prod Account Credentials)
[ Phase 1.5: Non-Prod AWS Account Integration ]
  ├── Live AWS Cost Explorer, ECS, Lambda, & S3 API Connection (aws_connector.py)
  ├── Non-Prod IAM Execution Role (CloudIntel-NonProd-ExecutionRole)
  ├── Containerized Hosting on AWS App Runner / ECS Fargate (aws_nonprod_deploy.yaml)
  └── AWS Service Catalog Non-Prod Portfolio Integration
           │
           ▼ (Security Audit & Stakeholder Approval)
[ Phase 2: Enterprise Cloud Production ]
  ├── AWS Athena / Redshift + AWS S3 Data Lake
  ├── Anthropic Claude 3.5 Sonnet (Enterprise License)
  ├── AWS App Runner / ECS Fargate + ALB + Banking SSO (OIDC/SAML)
  └── AWS Service Catalog Portfolio Pipeline Integration
```

---

## Non-Prod AWS Account Integration Guide (Phase 1.5)

### Step 1: Configure Non-Prod AWS Credentials / IAM Role

Authenticate your local terminal or container environment to your Non-Prod AWS Account using AWS CLI, SSO, or environment variables:

```bash
# Option A: AWS SSO Login (Recommended)
aws sso login --profile nonprod-account

# Option B: Standard AWS CLI Credentials
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export AWS_DEFAULT_REGION="us-east-1"
```

Verify connection to your non-prod account:
```bash
aws sts get-caller-identity
```

### Step 2: Test Live Non-Prod Data Connection (`aws_connector.py`)

Run the data ingestion pipeline with live AWS non-prod integration:
```bash
python ingest.py --use-aws
```
*Output Verification*:
- Connects to AWS Cost Explorer (`ce:GetCostAndUsage`) to pull real unblended costs.
- Connects to AWS ECS (`ecs:ListTasks`), AWS Lambda (`lambda:ListFunctions`), and AWS S3 (`s3:ListBuckets`) to fetch live metrics.
- Populates `cloudintel.duckdb` with live non-prod infrastructure data.

### Step 3: Deploy Non-Prod CloudIntel Stack via CloudFormation (`aws_nonprod_deploy.yaml`)

Deploy the CloudFormation stack in your Non-Prod AWS Account:

```bash
aws cloudformation deploy \
  --template-file aws_nonprod_deploy.yaml \
  --stack-name CloudIntel-NonProd-Stack \
  --parameter-overrides Environment=nonprod GroqApiKey=$GROQ_API_KEY \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Step 4: Build & Push Docker Container to AWS ECR

```bash
# 1. Retrieve ECR Repository URI from CloudFormation Stack Outputs
export ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name CloudIntel-NonProd-Stack \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
  --output text)

# 2. Authenticate Docker to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI

# 3. Build Docker Image
docker build -t cloudintel-nonprod-app .

# 4. Tag & Push Image to ECR
docker tag cloudintel-nonprod-app:latest $ECR_URI:latest
docker push $ECR_URI:latest
```

### Step 5: Verify App Runner URL & Service Catalog Portfolio

1. Retrieve the App Runner URL:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name CloudIntel-NonProd-Stack \
     --query "Stacks[0].Outputs[?OutputKey=='AppRunnerServiceUrl'].OutputValue" \
     --output text
   ```
2. Open the URL in your browser to access the live non-prod CloudIntel portal.
3. Remediation templates generated in Tab 4 can be registered directly into the non-prod **AWS Service Catalog Portfolio** (`CloudIntel-NonProd-FinOps-Remediations`).

---

## Environment Matrix & Prerequisites

## Environment Matrix & Prerequisites

### 1. Phase 1 & 1.5 (POC & Non-Prod Environment)

| Requirement | Specification |
| :--- | :--- |
| **Operating System** | Linux / macOS / Windows 10+ (PowerShell or Bash) |
| **Runtime Environment** | Python 3.10+ |
| **AWS SDK & Credentials** | `boto3>=1.28.0` with `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` |
| **Account Discovery** | Loaded from `accounts.json` or entered via Streamlit UI |
| **IAM Permissions** | Read-Only: `ce:*`, `cloudwatch:*`, `ecs:*`, `lambda:*`, `s3:*`, `servicecatalog:*` |
| **System Memory** | Minimum 4 GB RAM (8 GB recommended) |
| **Storage** | 1 GB free disk space |
| **External Connectivity** | HTTPS outbound access to `api.groq.com` (Port 443) |

### 2. Phase 2 (Enterprise Banking Cloud Target)

| Component | Target AWS Service / Architecture |
| :--- | :--- |
| **Application Hosting** | **AWS App Runner** or **Amazon ECS Fargate** (Private Subnets) |
| **AWS Authentication** | **Central System Account Access** (Central IAM Execution Role federating target accounts) |
| **Account Discovery** | **AWS Organizations / System Account Registry** (Auto-discovers registered accounts) |
| **Load Balancing & Auth** | **AWS ALB** + AWS IAM / Banking SSO (OIDC / SAML 2.0) |
| **Analytical Query Engine**| **AWS Athena** / **Amazon Redshift Serverless** |
| **Data Lake Storage** | **AWS S3 Bucket** + **AWS Glue Data Catalog** |
| **Secrets & Keys** | **AWS Secrets Manager** + **AWS KMS (Customer Managed Keys)** |
| **IaC Delivery Target** | **AWS Service Catalog** Product Portfolios via AWS CodePipeline |

---

## Configuration & Environment Variables

Create a `.env` file in the project root directory (ensure `.env` is listed in `.gitignore`):

```bash
# Core Application Environment
APP_ENV=nonprod
LOG_LEVEL=INFO

# AWS Access Key Credentials & Region (Phase 1 POC)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_SESSION_TOKEN=optional_session_token_here
AWS_DEFAULT_REGION=us-east-1

# Target Account Configuration File
ACCOUNTS_CONFIG_PATH=accounts.json

# Phase 1/1.5 LLM Provider Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL_NAME=llama-3.3-70b-versatile

# Phase 2 LLM Provider Configuration (Target)
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# LLM_MODEL_NAME=claude-3-5-sonnet-20241022

# Database & Storage Settings
DUCKDB_PATH=data/processed/cloudintel.duckdb
DATA_RAW_DIR=data/raw

# Banking Compliance Guardrails Toggle (ENFORCE | AUDIT)
GUARDRAILS_MODE=ENFORCE
ENFORCE_KMS_MANDATE=true
ENFORCE_ECS_SIDECARS=true
ENFORCE_LAMBDA_MEMORY_BOUNDS=true
ENFORCE_ZERO_PUBLIC_ACCESS=true
```


---

## Health Check, Verification & Rollback Procedures

### 1. Verification Commands & Diagnostics

| Verification Step | Execution Command | Success Criteria |
| :--- | :--- | :--- |
| **AWS Connection Check** | `python aws_connector.py` | Returns `AWS Non-Prod Connection Status: CONNECTED` |
| **Ingestion Check** | `python ingest.py --use-aws` | Successfully pulls live AWS metrics into DuckDB |
| **Guardrails Test** | `python guardrails.py` | Passes `RULE_S3_KMS`, `RULE_ECS_SIDECARS`, `RULE_LAMBDA_BOUNDS`, `RULE_NO_PUBLIC_ACCESS` |
| **Streamlit Health** | `curl -f http://localhost:8501/_stcore/health` | Returns HTTP `200 OK` |

### 2. Rollback & Emergency Procedures
1. **Local DuckDB Corruption**:
   - Delete `data/processed/cloudintel.duckdb` and rerun `python ingest.py` to regenerate cleanly.
2. **LLM Provider Outage / API Fallback**:
   - Switch `.env` variable `LLM_MODEL_NAME` or switch fallback provider endpoint in `llm_client.py`.
3. **Container Rollback**:
   - Roll back AWS App Runner service / ECS Task Definition to previous immutable ECR image tag via AWS Management Console or AWS CLI.
