# Cost Lever Coverage & Value-Add Roadmap

Status: **not scheduled** — captured for future reference, no implementation started.

## Context

After making ECS/Lambda/S3 waste detection and guardrails config-driven
(`config/services/*.yaml`, see git history), we audited how much of the AWS
Well-Architected Cost Optimization pillar each service's YAML actually
covers. Each service currently implements exactly **one** waste lever out of
several relevant ones. This doc captures that audit, the decision on how to
close the gaps, and an honest value-add assessment for stakeholder
conversations — without committing to build any of it yet.

## Current coverage (as of this writing)

| Service | Lever implemented | Mechanism |
|---|---|---|
| ECS-EC2 | CPU/memory utilization < 15% -> downsize task def | `config/services/ecs.yaml` `waste_rule` |
| AWS-Lambda | Allocated memory >= 2x peak used -> right-size down | `config/services/lambda.yaml` `waste_rule` |
| S3-Storage | No lifecycle policy + object age > 90d -> tier to Glacier | `config/services/s3.yaml` `waste_rule` |

Structural constraint: `ServiceDef.waste_rule` (in `service_schema.py`) only
allows **one** rule per service. Adding more levers to any service requires
this becoming `waste_rules: list[WasteRule]` first (small, backward-compatible
change — a single-item list behaves identically to today).

## Decision: don't re-derive what AWS already detects well

Initial instinct was to add a parallel "Well-Architected advisory" layer that
re-implements generic levers (Spot eligibility, right-sizing, RI/Savings Plan
coverage) as more YAML conditions. On reflection this would duplicate **AWS
Compute Optimizer** (ML-driven right-sizing for EC2/ECS-on-Fargate/Lambda/EBS)
and **AWS Trusted Advisor** (Cost Optimization category checks, requires
Business/Enterprise Support), both of which do this better than hand-written
thresholds ever will.

**Revised direction**: ingest AWS's own findings as a data source feeding the
*same* pipeline (guardrails -> `candidate_recommendations` -> CloudFormation
generation) rather than re-detecting them. Keep hand-written `waste_rule`
YAMLs only for checks that are inherently specific to this org's compliance
posture or that no AWS service covers at all.

## Lever bucket assignment

### ECS (launch_type: EC2)

Important nuance: **Compute Optimizer's ECS recommendations only cover
Fargate services**, not EC2 launch type, which is what this project's ECS
service currently represents. So the "AWS-sourced" lever for ECS is at the
*underlying EC2 instance* level, not the task level — different granularity
than today's rule, not a replacement for it.

| Lever | Bucket | Source / rationale |
|---|---|---|
| Task-level CPU/memory right-sizing | Custom (keep) | No AWS API covers EC2-launch-type ECS tasks directly |
| Underlying EC2 instance right-sizing | AWS-sourced | Compute Optimizer `GetEC2InstanceRecommendations` |
| Cluster binpacking / instance utilization | AWS-sourced | Same API, viewed in aggregate |
| RI / Savings Plans coverage (underlying EC2 capacity) | AWS-sourced | Cost Explorer `GetSavingsPlansPurchaseRecommendation` / `GetReservationPurchaseRecommendation` |
| Spot / Fargate Spot eligibility | Not automatable | No AWS API recommends this; architectural/risk decision, not metrics-derived. Could surface as a static note only. |
| Idle clusters/services (near-zero task count, off-hours) | Custom | No AWS check exists for this |
| Unused/orphaned task definitions | Not automatable via current design | No direct AWS API; likely not worth building |

### Lambda

| Lever | Bucket | Source / rationale |
|---|---|---|
| Memory right-sizing (current rule) | AWS-sourced (supersede custom rule) | Compute Optimizer `GetLambdaFunctionRecommendations` — accounts for memory + duration together, stronger than our threshold |
| Under-provisioned memory (slow execution raising cost) | AWS-sourced | Same API, evaluates both directions |
| ARM64/Graviton2 migration | AWS-sourced (verify at build time) | Compute Optimizer Lambda findings may include architecture recommendations; confirm current API response shape before committing |
| Provisioned Concurrency waste | Custom, needs new data | CloudWatch `ProvisionedConcurrencyUtilization`, not in Compute Optimizer/Trusted Advisor |
| Low-invocation / dead functions | Custom, cheap | Data already in schema (`invocations_count`), just unused today |
| CloudWatch Logs retention cost | Custom, needs new data source | Separate API (Logs), not part of any Lambda-specific AWS check |

### S3

No Compute Optimizer or Trusted Advisor coverage exists for any S3 lever
below — this stays entirely on hand-written `waste_rule` YAMLs, gated behind
the `waste_rules: list` schema change.

| Lever | Bucket | Notes |
|---|---|---|
| Lifecycle/tiering by age (current rule) | Custom (keep) | |
| Incomplete multipart uploads | Custom | Needs new schema field + fetch adapter work (`s3.list_multipart_uploads`) |
| Non-current object versions accumulating | Custom | Needs new schema field + fetch adapter work |
| Intelligent-Tiering adoption | Custom for now | Could become AWS-sourced later via S3 Storage Lens access-pattern data — separate integration, not in scope here |
| Requester-pays / cross-account cost anomalies | Out of scope | Needs billing/access-log analysis; disproportionate effort for this tool |

## "Free" wins (no new data collection needed)

Two schema fields already exist but are unused by any rule:
- Lambda: `timeout_seconds`, `invocations_count`
- ECS: `launch_type`

These could back cheap additional custom rules (e.g. "flag near-zero
invocation functions") without any new metrics collection or fetch-adapter
work — cheapest thing to pick up first if this roadmap gets scheduled.

## Prerequisites to validate before building any AWS-sourced ingestion

1. Does the target AWS account have **Compute Optimizer enrolled**? (opt-in
   per account/org, not automatic)
2. Does the target AWS account have **Business or Enterprise Support**?
   (required for the Trusted Advisor API; without it, Trusted Advisor
   ingestion is a no-go and only Compute Optimizer is viable)

Neither has been confirmed as of this writing — this tool currently runs
against synthetic fixture data (`data/raw/*.json`), not a live AWS account.

## Honest value-add assessment (for stakeholder conversations)

**What holds up as a real differentiator vs. Trusted Advisor / Compute
Optimizer / just reading the Well-Architected Framework:**
1. **Compliance-aware guardrails** sitting between detection and action —
   AWS's tools don't know this org's KMS/sidecar/compliance policy and will
   happily suggest changes that violate it. This is the genuinely custom,
   defensible piece.
2. **Recommendation -> IaC in one motion, policy-vetted** — Trusted
   Advisor/Compute Optimizer stop at "here's a suggestion"; this tool
   produces guardrail-approved CloudFormation + Service Catalog artifacts
   ready for the existing deployment pipeline.
3. **Unified view across cost + compliance + this org's business unit
   structure** — not a native single-console AWS view.
4. **Natural-language querying joining cost + resource data** — real
   convenience, but a thinning differentiator as Amazon Q / CloudWatch grow
   their own natural-language features.

**What does NOT hold up — avoid claiming these:**
- "We detect waste better than AWS." Compute Optimizer's ML-driven
  right-sizing (built on account-wide CloudWatch history) is stronger than
  hand-written threshold rules like `cpu_utilization_max < 15.0`. The
  correct positioning is *ingesting* AWS's findings, not out-detecting them.
- "This replaces Trusted Advisor." It's complementary and, for some checks,
  literally requires Trusted Advisor access to function.
- "AI-powered" as the core selling point. The LLM (Groq) handles
  natural-language query translation and template generation — it is not
  doing the cost-optimization judgment itself; that's rule-based YAML or
  AWS's ML.

**One-line pitch that's actually defensible:** "AWS already tells you what's
wasteful — this tool makes sure nothing gets fixed in a way that breaks your
compliance posture, and turns approved fixes into deployable code
automatically."

## Suggested next steps, if/when this gets prioritized

1. Confirm Compute Optimizer enrollment + Trusted Advisor support tier on
   the target account (blocking prerequisite).
2. Ship the small `waste_rule` -> `waste_rules: list[WasteRule]` schema
   change (backward compatible, unlocks multiple rules per service
   regardless of source).
3. Add the two "free" Lambda/ECS rules using already-collected fields.
4. If Compute Optimizer is available: build the ingestion path for Lambda
   first (cleanest win — supersedes our current custom rule entirely).
5. Only then consider S3-specific new metrics collection (multipart,
   versions) since that's pure custom-build with no AWS shortcut available.
