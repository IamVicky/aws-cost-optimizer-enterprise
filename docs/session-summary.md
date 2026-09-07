# Session Summary — Config-Driven Refactor & Cost Lever Roadmap

Date: 2026-09-07

This is a structured summary of a working session covering the repo
walkthrough, a config-driven refactor of ECS/Lambda/S3 waste detection and
guardrails, and a follow-on architecture discussion about cost lever
coverage vs. AWS Trusted Advisor / Compute Optimizer. It is not a verbatim
transcript — see the roadmap doc referenced below for the detailed
follow-on findings.

## 1. Starting question: does adding a new service require code changes?

Walked through the codebase (`aws-cost-optimizer-enterprise/src/aws_cost_optimizer/`)
and confirmed that adding a service like Kinesis, or tuning an existing
service's thresholds, required editing four files: `ingest/pipeline.py`
(schema + load logic), `connectors/aws_connector.py` (fetch method),
`analysis/waste_analyzer.py` (SQL condition/savings formula/fix text), and
`guardrails/engine.py` (compliance rules) — each hardcoded per service.

## 2. Decision: make it config-driven

Agreed to move service-specific logic into YAML files
(`config/services/*.yaml`) consumed by generic engines, scoped to the
**existing three services only** (ECS, Lambda, S3) — no new service added
in this pass, behavior-preserving refactor.

Two refinements added to the plan during discussion:
- **Fail-fast validation**: a Pydantic schema (`service_schema.py`) so a
  malformed YAML raises a clear file/field error at load time instead of a
  downstream `KeyError`.
- **Condition-based guardrails**: support both pattern-matching guardrail
  rules (existing behavior) and numeric/structural `condition` rules (for
  future checks like `retention_days < 7`) via a restricted expression
  evaluator, rather than pattern-matching only.

## 3. Implementation (completed, tested, committed, pushed)

New files:
- `config/services/{ecs,lambda,s3}.yaml` — per-service schema, waste
  condition/savings formula/fix text, guardrail rules (ported verbatim from
  the old hardcoded logic, no behavior change)
- `src/aws_cost_optimizer/service_schema.py` — Pydantic validation models
- `src/aws_cost_optimizer/service_registry.py` — `load_services()`, the
  single source of truth for ingest/analyzer/guardrails
- `src/aws_cost_optimizer/expr.py` — `safe_eval()`, an `ast`-restricted
  expression evaluator (no raw `eval`) for conditions/formulas

Rewritten to be generic (loop over `load_services()` instead of hardcoded
per-service blocks):
- `ingest/pipeline.py`, `connectors/aws_connector.py` (added `fetch()`
  dispatch), `analysis/waste_analyzer.py`, `guardrails/engine.py`

Verified: ingest and waste-analyzer output identical to pre-refactor, all
11 existing tests pass, `safe_eval` rejects dangerous constructs
(`__import__`, `open()`, comprehensions, etc.), a deliberately broken YAML
fails fast with a clear error, `streamlit_app.py` needed zero changes.

One bug found and fixed during verification: a circular import between
`guardrails.engine` and `analysis.expr` (resolved by moving `expr.py` to
the top-level package).

**Commits**: `42daec5` (the refactor) and `f99cca8` (the roadmap doc below),
both pushed to `origin/master`.

## 4. Full repo walkthrough

Gave a complete file-by-file explanation of the repo:
`config.py` (settings), `connectors/aws_connector.py` (AWS/boto3 + synthetic
fallback), `ingest/pipeline.py` (ETL into DuckDB), `analysis/waste_analyzer.py`
(waste detection), `analysis/query_agent.py` (NL-to-SQL), `guardrails/engine.py`
(compliance interceptor), `iac/generator.py` (CloudFormation + Service
Catalog generation), `llm/client.py` (Groq wrapper with heuristic fallback),
`api/streamlit_app.py` (4-tab dashboard UI), plus the new config-driven
files listed above.

Also covered, as design discussion (no code changes made for these):
- **DuckDB is local/embedded**, not a cloud database — a single file, not a
  server. Recommended keeping it for production too, with a single-writer
  (scheduled job) / many-readers (UI) pattern, file relocated to shared
  storage (EFS or S3) rather than swapping the database engine.
- **DB refresh today is manual only** (sidebar buttons / first-load
  fallback in `streamlit_app.py`) — recommended adding an independent
  scheduled ingest job (EventBridge + Fargate/Lambda) rather than relying on
  the UI to trigger refreshes.
- **Deployment**: recommended containerizing the Streamlit app as-is (single
  audience: humans via browser) rather than building an MCP/REST layer
  prematurely, deferring that decision until a concrete non-human/agent
  consumer exists.
- **S3 vs EFS cost**: S3 is cheaper per-GB and needs no VPC/mount
  infrastructure; recommended S3 for the eventual shared-storage backend,
  though this is explicitly deferrable and doesn't block anything else.

## 5. Cost lever coverage audit

Audited each service's single `waste_rule` against AWS Well-Architected
Cost Optimization pillar levers and found each service implements only one
lever out of several relevant ones (e.g. ECS misses Spot eligibility, idle
service detection, cluster-level right-sizing; Lambda misses provisioned
concurrency waste, Graviton migration, log retention; S3 misses incomplete
multipart uploads, non-current versions, Intelligent-Tiering).

Considered building a parallel "Well-Architected advisory" layer to close
these gaps, but concluded this would largely **duplicate AWS Trusted
Advisor and AWS Compute Optimizer**, which already do ML-driven right-sizing
and cost-check detection better than hand-written thresholds. Revised
direction: ingest AWS's own findings as a data source into the existing
pipeline (guardrails -> `candidate_recommendations` -> CloudFormation),
rather than re-detecting what AWS already detects.

Full lever-by-lever bucket assignment (AWS-sourced vs. custom vs. not
automatable), prerequisites to validate (Compute Optimizer enrollment,
Trusted Advisor support tier), and an honest stakeholder-facing value-add
assessment were written up in **`docs/cost-lever-roadmap.md`** (committed,
not implemented — status: not scheduled).

Key conclusion for stakeholder conversations: this tool's real
differentiator is not "detects waste better than AWS" (it doesn't and
shouldn't claim to) — it's the **compliance-aware guardrail layer** sitting
between AWS's detection and actual remediation, plus **guardrail-vetted
recommendation-to-IaC generation**, which no AWS-native tool provides.

## Where things stand / open items

- `docs/cost-lever-roadmap.md` is the authoritative reference for
  next-step scope if this work resumes — nothing in it has been built.
- The `waste_rule` -> `waste_rules: list[WasteRule]` schema change (to allow
  multiple checks per service) was identified as a prerequisite for adding
  any further S3-specific custom levers, but not yet implemented.
- Compute Optimizer / Trusted Advisor enrollment status on the target AWS
  account has not been confirmed — blocking prerequisite for that track.
- Deployment (containerization, scheduled refresh, EFS vs. S3 for shared
  DuckDB storage) was discussed at a design level only, no implementation.
