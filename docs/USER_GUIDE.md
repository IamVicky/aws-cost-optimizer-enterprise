# CloudIntel — End-User Operational Guide

Welcome to the **CloudIntel User Guide**. This document is designed for Business Unit Managers, FinOps Analysts, Cloud Architects, and Compliance Officers. It provides step-by-step instructions on how to navigate, query, analyze, and automate cost remediations using the CloudIntel Web Application.

---

## 1. Platform Overview

**CloudIntel** is an Enterprise AI FinOps Intelligence Platform. Unlike static dashboards or complex technical logs, CloudIntel translates plain-English business questions into factual analytical queries, scans your cloud infrastructure across **Amazon ECS**, **AWS Lambda**, and **Amazon S3** for waste, and automatically generates compliance-vetted **AWS CloudFormation templates** ready for **AWS Service Catalog** deployment.

### Key Capabilities
- **Natural Language Chat Assistant**: Ask plain-English questions about cloud spend, resource spikes, and utilization across Business Units.
- **Proactive Savings Dashboard**: View vetted cost-saving recommendations sorted by estimated monthly savings ($).
- **Banking Security & Guardrail Interceptor**: Protects your environment by enforcing AWS KMS key encryption mandates, container security sidecar retention, and zero public access blocks.
- **One-Click CloudFormation Studio**: Instantly generate and download ready-to-deploy AWS CloudFormation templates and Service Catalog product definitions.

---

## 2. Getting Started & Launching the App

### Accessing the Web Application
1. Ensure the application server is running locally or deployed to your non-prod environment.
2. Open your web browser and navigate to:
   `http://localhost:8501`

---

## 3. Sidebar Controls & Navigation

The left-hand sidebar allows you to configure your viewing environment and manage data pipelines:

1. **Target AWS Account Selector**:
   - Choose a target account from your [`accounts.json`](file:///j:/AI_Learnings/ai-aws-cost/Automation/accounts.json) configuration (e.g. `NonProd-Marketing-Account`, `NonProd-Engineering-Dev`, `NonProd-DataScience-Sandbox`).
2. **AWS Credentials Status Indicator**:
   - Shows **✓ AWS Access Keys Active** when live AWS credentials are active, or **ℹ️ Offline / Synthetic Data Mode** when using sample datasets.
3. **AI Engine & DB Status**:
   - Displays connection status for Groq Cloud API (`llama-3.3-70b-versatile`) and DuckDB database (`cloudintel.duckdb`).
4. **Business Unit (BU) Filter**:
   - Filter all insights and recommendations by specific BU: `All Business Units`, `Marketing`, `Engineering`, or `DataScience`.
5. **Enforce Banking Guardrails Toggle**:
   - Toggles active security guardrail filtering (`ENFORCE` vs `AUDIT`).
6. **Data Pipeline Buttons**:
   - **Run ETL Ingestion Pipeline**: Refreshes raw cost and metric data into the analytical database.
   - **Run Waste Analyzer**: Scans analytical database for new cost-saving opportunities.

---

## 4. Main Tab Guide

---

### Tab 1: 💬 Chat Assistant (Text-to-SQL & Insights)

The Chat Assistant enables plain-English conversations with your cloud cost database:

#### How to Use:
1. Click any of the **Sample Prompt Shortcuts** or type a question into the search bar:
   - *"Show top 5 most expensive Lambda functions across BUs"*
   - *"Which S3 buckets are missing lifecycle policies?"*
   - *"Show over-provisioned ECS task definitions with low CPU utilization"*
   - *"Why did Marketing spend spike last week?"*
2. Press **Enter**.
3. **Executive Insights & Context Explanation**: Read the synthesized business summary explaining cost drivers and recommendations.
4. **Inspect Generated SQL**: Expand the *"View Generated SQL Query & Raw Analytical Results"* drawer to see the exact read-only ANSI SQL executed against the database along with the tabular data output.

---

### Tab 2: 📊 Proactive Savings Dashboard

The Proactive Savings Dashboard surfaces autonomous waste detection results:

#### Key Metrics Bar:
- **Est. Monthly Savings ($)**: Total aggregate monthly cost reduction achieved if all approved recommendations are implemented.
- **Approved Optimizations**: Count of candidate recommendations passing all banking compliance guardrails.
- **Banking Guardrail Pass Rate (%)**: Percentage of candidate recommendations meeting compliance standards.

#### Recommendation Cards:
Each approved card displays:
- **Recommendation ID & Service**: e.g., `REC_ECS_001 — ECS-EC2 (Marketing)`
- **Compliance Badge**: `✓ BANKING COMPLIANCE PASSED`
- **Proposed Optimization Summary**: Explains specific parameter changes (e.g. downsizing CPU from 4096 to 1024 units while preserving security sidecars).
- **Target Resource ID**: Full AWS ARN or bucket name.
- **Est. Monthly Savings ($)**: Projected monthly savings.

---

### Tab 3: 🛡️ Compliance & Guardrail Audit Log

The Audit Log provides transparent visibility into candidate optimizations intercepted and blocked by the Banking Guardrails Engine:

#### Intercepted Policy Violation Cards:
When an optimization tool or AI prompt attempts an unsafe change, the Guardrails Engine blocks it and logs details here:
- **`REJECTED_KMS_MANDATE` (Rule: `RULE_S3_KMS`)**: Triggered when an optimization suggests deleting, detaching, or disabling AWS Managed KMS encryption keys (`aws_kms_key` / SSE-KMS) to eliminate KMS API costs.
- **`REJECTED_SECURITY_SIDECAR_OMISSION` (Rule: `RULE_ECS_SIDECARS`)**: Triggered when container task definition resizing attempts to strip security monitoring or log shipper sidecars.
- **`REJECTED_LAMBDA_TELEMETRY_BOUNDS` (Rule: `RULE_LAMBDA_BOUNDS`)**: Triggered when memory reduction drops below minimum bounds or disables AWS X-Ray telemetry.
- **`REJECTED_PUBLIC_ACCESS_EXPOSURE` (Rule: `RULE_NO_PUBLIC_ACCESS`)**: Triggered when S3 templates attempt to alter public access blocks.

---

### Tab 4: 🏗️ Remediation & CloudFormation Studio

Convert approved recommendations into production-ready Infrastructure as Code (IaC):

#### How to Use:
1. Select an approved recommendation from the dropdown list.
2. Click **Generate CloudFormation Remediation Code**.
3. **AWS CloudFormation Template (`cloudformation_template.yaml`)**:
   - Review the generated YAML code in the code viewer.
   - Click **Download CloudFormation YAML** to save the file locally.
4. **AWS Service Catalog Product Definition (`service_catalog_product.json`)**:
   - Review the Service Catalog product metadata JSON artifact.
   - Click **Download Service Catalog JSON Metadata**.
5. **Deployment**: Upload the generated CloudFormation template into your non-prod **AWS Service Catalog Portfolio** for standard, compliant provisioning.

---

## 5. Frequently Asked Questions (FAQ)

**Q: Can CloudIntel accidentally delete my KMS keys or security containers?**  
**A:** No. Every candidate recommendation passes through the **Banking Security & Compliance Guardrails Engine** before code generation. Any suggestion attempting to alter KMS encryption keys or strip security sidecars is automatically rejected and logged in Tab 3.

**Q: Where are my AWS Access Keys stored?**  
**A:** Access keys are configured strictly inside your local `.env` file or passed securely via environment variables. The `.env` file is excluded from version control (`.gitignore`) and is never committed to GitHub.

**Q: Can I run queries across multiple AWS Accounts?**  
**A:** Yes. Select the target Account ID from the sidebar dropdown (populated from [`accounts.json`](file:///j:/AI_Learnings/ai-aws-cost/Automation/accounts.json)) to inspect costs and metrics for that specific account.
