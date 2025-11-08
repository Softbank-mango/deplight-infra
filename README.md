# deplight-platform

Full-stack hackathon monorepo with frontend, backend, Slack bot, and a Terraform-driven AWS deployment system.

## Deployment Overview
- GitHub Actions authenticates to AWS via GitHub OIDC and assumes a scoped IAM role.
- Build workflow publishes Docker images to ECR, tagging each build with the commit SHA.
- Terraform CLI runs inside the deployment workflow, using remote state (S3 bucket + DynamoDB locking) and passing `-var="image_tag=<commit_sha>"` to update ECS task definitions, CodeDeploy blue/green settings, and observability resources.
- CodeDeploy handles production rollouts with automatic rollback on failure; post-deploy smoke tests publish results and CloudWatch dashboard links to Slack and PR comments.
- An AI Analyzer Lambda inspects `.delightful.yaml` plus source code, comments on PRs, and drops suggested `terraform.tfvars` files for review under `generated/`.

## Repository Layout
```text
deplight-platform/
├─ apps/
│  └─ analyzer-lambda/
├─ infrastructure/
│  ├─ modules/
│  │  ├─ iam-github-oidc/
│  │  ├─ network-baseline/
│  │  ├─ ecs-service/
│  │  ├─ codedeploy-bluegreen/
│  │  └─ observability-suite/
│  ├─ backend-config/
│  │  ├─ remote-state/      (S3 bucket, DynamoDB table IaC)
│  │  └─ variables/         (environment configs, secret maps)
│  └─ environments/
│     ├─ dev/
│     └─ prod/
├─ ops/
│  ├─ runbooks/
│  └─ scripts/
│     ├─ rollback/
│     └─ smoke-tests/
├─ docs/
│  ├─ architecture/
│  ├─ handover/
│  └─ risk-register/
├─ generated/
│  └─ analyzer-artifacts/
├─ config/
│  ├─ delightful/
│  └─ terraform/
└─ .github/
   └─ workflows/
```

## Where to Start
1. Review `dev-plan.md` for the 4-day execution plan, task breakdown, and acceptance criteria.
2. Follow `deployment_system.md` for architecture details, interfaces, and rollback guidance.
3. Ensure required secrets/variables (GitHub OIDC role ARN, Terraform backend bucket/table, Slack webhook) are configured before running the CI/CD workflows.

## Handover Notes
- Smoke tests and notification scripts live under `scripts/`.
- Terraform modules, backend configuration, and analyzer-generated files are under `infrastructure/` and `generated/`.
- Rollback instructions and environment runbooks are consolidated in `dev-plan.md` (Handover section). Update the README if new automation or environments are added.
