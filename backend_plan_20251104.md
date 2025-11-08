# Deployment System 4-Day Delivery Plan

## Goals
- Deliver a GitHub→AWS deployment pipeline leveraging OIDC and Terraform CLI automation.
- Ensure artifact tagging propagates from CI to Terraform/ECS with rollback and observability coverage.
- Integrate the AI Code Analyzer workflow to feed Terraform variables and recommendations.
- Produce runbook-level documentation with smoke tests, notifications, and handover assets.

## Constraints
- 4 calendar days, 3–4 team members with ~12 focused hours/day (buffers preserved).
- GitHub Actions, Terraform CLI, AWS ECS/CodeDeploy, AI Analyzer Lambda must be used as given.
- Prefer short-lived credentials; no long-lived AWS keys stored in GitHub.
- Tasks sized 2–5 hours, respecting dependencies and critical path.
- Network access restricted; external tooling additions require approval.

## Interfaces & Data Models
- GitHub OIDC → AWS IAM role using `sts:AssumeRoleWithWebIdentity`.
- Docker image tagged with `<commit_sha>` pushed to ECR; tag passed as Terraform variable during CLI apply.
- AI Code Analyzer Lambda consumes `.delightful.yaml` + repo, outputs PR comments and `generated/terraform.tfvars.json` in S3, possibly scaffolds modules under `infrastructure/`.
- Terraform CLI runs from GitHub Actions using remote state (S3 + DynamoDB locking) with environment variables for backend configuration.
- GitHub Actions workflows: Analyzer workflow and CI/CD workflow (build/test/SCA → push image → Terraform apply → CodeDeploy → smoke tests → Slack + PR updates).

## Team & Capacity

| Role | Focus | Daily Capacity (h) | Notes |
| --- | --- | --- | --- |
| Platform Engineer A | AWS IAM, Terraform modules | 4 | Owns core infra definitions. |
| Platform Engineer B | GitHub Actions, CodeDeploy | 4 | Builds CI/CD workflows. |
| DevOps Engineer | Observability, rollback, automation | 3 | Handles monitoring + smoke scripts. |
| QA/Tech Writer | Tests, docs | 1 | Consolidates acceptance + handover. |
| **Net** |  | **12** | Allows ~3h/day buffer for review/support. |

## Schedule & Load

| Day | Focus | Planned Tasks | Effort (h) | Capacity (h) | Notes |
| --- | --- | --- | --- | --- | --- |
| Day 1 | Auth & Terraform foundations | T-01, T-02, T-03 | 10 | 12 | 2h buffer for IAM review. |
| Day 2 | Terraform pipeline & CI/CD core | T-04, T-05, T-06 | 10 | 12 | Buffer for first pipeline dry-run. |
| Day 3 | AI Analyzer & Observability | T-07, T-08, T-09 | 11 | 12 | 1h buffer for S3/perm tweaks. |
| Day 4 | Rollback, smoke checks, docs | T-10, T-11, T-12 | 9 | 12 | 3h reserved for contingency + retros. |

## Critical Path & Blockers
- **Critical path:** T-01 → T-02 → T-05 → T-06 → T-11 → T-12.
- **Current blockers:** None; awaiting confirmation on AWS account/environment boundaries (see Open Questions).

## Task Board

[✓] `T-01` Establish GitHub→AWS OIDC trust (Critical Path)  
- Scope: In — AWS IAM role, trust policy, claim mappings; Out — global IAM refactors.  
- Dependencies: None  
- Effort: 3h | Priority: Must | Risk: Medium — claim mismatch can block deployments.  
- Acceptance: Dry-run workflow obtains AWS identity via `aws sts get-caller-identity`.

[✓] `T-02` Configure GitHub Actions AWS credential usage (Critical Path)  
- Scope: In — apply OIDC role via `aws-actions/configure-aws-credentials`; Out — GitHub org-wide secrets cleanup.  
- Dependencies: T-01  
- Effort: 3h | Priority: Must | Risk: Medium — misconfigured permissions lead to failed applies.  
- Acceptance: Workflow step acquires temp creds and lists ECS clusters without error.

[✓] `T-03` Scaffold Terraform module structure under `infrastructure/`  
- Scope: In — baseline modules (network, ECS, CodeDeploy hooks); Out — non-prod environment duplication.  
- Dependencies: None  
- Effort: 4h | Priority: Must | Risk: Medium — inconsistent module interfaces delay Terraform setup.  
- Acceptance: Modules lint/plan locally with placeholders and publish input/output documentation.

[✓] `T-04` Configure Terraform backend & workflow integration  
- Scope: In — remote state (S3 + DynamoDB), backend config, secure variable handling in CI; Out — multi-account backend federation.  
- Dependencies: T-03  
- Effort: 3h | Priority: Must | Risk: Medium — misaligned state config blocks applies.  
- Acceptance: `terraform init` succeeds in CI with backend pointing to agreed S3 bucket and locking table.

[ ] `T-05` Implement CI/CD workflow skeleton (Critical Path)  
- Scope: In — build/test/SCA jobs, ECR push, Terraform plan/apply gating; Out — language-specific unit tests beyond sample harness.  
- Dependencies: T-02, T-03  
- Effort: 4h | Priority: Must | Risk: High — orchestrates whole deployment path.  
- Acceptance: Workflow completes build + plan stages on sample branch with manual apply approval.

[ ] `T-06` Propagate image tag into Terraform apply (Critical Path)  
- Scope: In — capture commit SHA, pass to Terraform CLI via `-var=image_tag`, ensure outputs update ECS; Out — alternative tag naming schemes.  
- Dependencies: T-05  
- Effort: 3h | Priority: Must | Risk: Medium — incorrect tag breaks ECS rollout.  
- Acceptance: ECS task definition updated with expected `image_tag` after apply.

[ ] `T-07` Integrate AI Analyzer workflow invocation  
- Scope: In — trigger Lambda, collect PR comments, retrieve S3 tfvars; Out — modifying analyzer logic.  
- Dependencies: T-05  
- Effort: 4h | Priority: Should | Risk: Medium — analyzer IAM/timeout issues.  
- Acceptance: Analyzer workflow posts PR recommendations and artifact path logged.

[ ] `T-08` Consume AI analyzer outputs in Terraform pipeline  
- Scope: In — sync `generated/terraform.tfvars.json`, review optional modules, gate merges; Out — automatic module merges.  
- Dependencies: T-07, T-04  
- Effort: 3h | Priority: Should | Risk: Medium — stale tfvars may break applies.  
- Acceptance: Terraform plan/apply reads analyzer vars, with manual approval step if diff exceeds threshold.

[ ] `T-09` Provision observability stack via Terraform  
- Scope: In — CloudWatch dashboards, alarms, log retention, X-Ray sampling; Out — third-party monitoring integrations.  
- Dependencies: T-03  
- Effort: 4h | Priority: Should | Risk: Medium — missing metrics delays go-live approval.  
- Acceptance: Terraform plan shows dashboards/alarms resources; ARN references documented.

[ ] `T-10` Finalize rollback automation & runbook  
- Scope: In — CodeDeploy automatic rollback validation, manual Terraform rollback command set; Out — chaos testing.  
- Dependencies: T-06  
- Effort: 3h | Priority: Must | Risk: Medium — unclear rollback increases MTTR.  
- Acceptance: Documented procedure exercised in staging, CodeDeploy alarm triggers revert.

[ ] `T-11` Implement smoke tests & notifications (Critical Path)  
- Scope: In — post-deploy smoke script, Slack + PR comment updates including dashboard URL; Out — deep load testing.  
- Dependencies: T-06, T-09  
- Effort: 3h | Priority: Must | Risk: Medium — missing alerts hide failures.  
- Acceptance: Successful deploy posts Slack message with dashboard link; failed smoke test blocks completion.

[ ] `T-12` Consolidate documentation & handover (Critical Path)  
- Scope: In — README updates, environment bootstrapping, credentials map, DoD checklist; Out — long-form tutorials.  
- Dependencies: All prior tasks  
- Effort: 3h | Priority: Must | Risk: Low — incomplete docs hinder adoption.  
- Acceptance: README/Handover doc covers run commands, env vars, seeds, rollback steps, test evidence attached.

## Assumptions & Open Questions

| Type | Item | Proposed Resolution |
| --- | --- | --- |
| Assumption | AWS account, ECR repo, and Terraform backend resources (S3 bucket, DynamoDB table) already exist with admin access for the team. | Confirm credentials on Day 1; escalate if missing. |
| Assumption | AI Analyzer Lambda is deployed and reachable with required IAM permissions. | Validate ARN and IAM policy before T-07. |
| Assumption | Slack workspace & webhook for deployment notifications available. | Obtain or create channel during Day 3. |
| Open Question | Are multiple environments (staging/prod) required in this 4-day window? | Default to single staging-like environment; await sponsor decision to duplicate. |
| Open Question | Should CodeDeploy blue/green include traffic shifting tests beyond smoke checks? | Propose simple health check only unless stakeholder provides additional scripts. |
| Open Question | Who owns long-term Terraform backend (S3/Dynamo) access and approvals post-handover? | Need named owner for access control before Day 4. |

## Risk Register

| Risk ID | Description | Impact | Probability | Mitigation | Trigger | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | OIDC trust misconfiguration blocks AWS access. | High | Medium | Pair review trust policy, test via sandbox job. | GitHub workflow fails to assume role. | Platform Engineer A |
| R-02 | Terraform apply drifts existing resources when analyzer tfvars misalign. | High | Medium | Manual review gate for analyzer outputs; diff alerts. | `terraform plan` shows destructive changes. | Platform Engineer B |
| R-03 | Analyzer Lambda latency exceeds GitHub workflow timeout. | Medium | Low | Increase timeout, add retry/backoff, capture CloudWatch metrics. | Workflow cancels analyzer step. | DevOps Engineer |
| R-04 | CodeDeploy rollback not triggered due to missing alarms. | High | Low | Validate alarms + deployment config in staging before prod. | Blue/green deployment hangs post-traffic shift. | DevOps Engineer |
| R-05 | Slack/notification failures hide deployment status. | Medium | Medium | Add fallback PR comment and CloudWatch event log. | Slack webhook errors or auth failure. | QA/Tech Writer |

## Definition of Done
- All Must-have tasks complete with evidence linked in README/handover.
- CI/CD pipeline runs end-to-end, including analyzer, build, Terraform plan/apply, CodeDeploy, smoke tests, and notifications.
- Rollback procedure demonstrated in staging and documented.
- Observability dashboard and alarms accessible with URLs recorded.
- Test checklist executed with results captured.
- Risk mitigations and open questions resolved or explicitly handed over.

## Acceptance Criteria per Deliverable

| Deliverable | Acceptance Criteria |
| --- | --- |
| GitHub→AWS authentication | Verified OIDC workflow with temp credentials, audit log showing no long-lived keys. |
| Terraform infrastructure | Modules lint, plan cleanly, Terraform CLI runs succeed with remote state configured and environment variables secured. |
| CI/CD pipeline | Build, test, scan, push image, pass tag to Terraform apply, produce CodeDeploy blue/green deployment without manual AWS console steps. |
| AI Analyzer integration | Analyzer comments appear on PR, tfvars consumed safely with review gate, optional modules staged for review. |
| Observability & rollback | CloudWatch dashboard/alarms accessible, X-Ray sampling configured, documented rollback steps validated. |
| Documentation & handover | README/Handover includes run instructions, env vars/credentials map, smoke test usage, rollback and monitoring references. |

## Test Checklist

**Functional**
- [ ] OIDC-authenticated workflow run logs successful `aws sts get-caller-identity`.
- [ ] CI job builds image, runs tests, and pushes tagged artifact to ECR.
- [ ] Terraform apply updates ECS task definition with expected `image_tag`.
- [ ] CodeDeploy blue/green deployment shifts traffic and reports success.
- [ ] Smoke test script hits health check path and reports status to Slack/PR.

**Non-Functional**
- [ ] IAM policies scoped to least privilege for GitHub and Lambda roles.
- [ ] Terraform state locking works (DynamoDB) and no drift detected post-deploy.
- [ ] CloudWatch dashboard renders key metrics; alarms notify on failure.
- [ ] Rollback command executes within documented SLA and restores previous tag.
- [ ] Analyzer Lambda execution time and cost recorded within agreed limits.

## Change Log

| Date | Change | Owner |
| --- | --- | --- |
| 2025-11-03 | Initial 4-day deployment plan drafted with Terraform CLI workflow. | Codex |
