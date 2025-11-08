# Deployment system

## Core Design Points

- **GitHub → AWS Authentication**: Use GitHub OIDC with an AWS IAM role (web identity) to mint short-lived credentials. In workflows, use `aws-actions/configure-aws-credentials`. Keep long-lived secrets to a minimum.
- **Image Tag Propagation**: GitHub Actions pushes the image to ECR tagged with `<commit_sha>`. The Terraform CLI deploy step passes this value via `-var="image_tag=<commit_sha>"`, updating the ECS Task Definition.
- **Infrastructure as Source**: Place Terraform modules under the repo’s `infrastructure/` directory. Use **Terraform CLI with a remote backend (S3 state + DynamoDB locking)** from GitHub Actions. Keep environment-specific settings (subnets, DB size, etc.) separated by variable files or workspace directories.
- **AI Analyzer Integration**: A Lambda “AI Code Analyzer” scans `.delightful.yaml` and the codebase to infer **expected traffic, scale, cache presence, DB flavor, health check path**, etc., then:
    1. posts recommendations as PR comments,
    2. writes `generated/terraform.tfvars.json` to S3, and
    3. optionally emits sample modules under `infrastructure/` for human review and merge.
- **Rollback Strategy**:
    - With CodeDeploy: automatic rollback on deployment failure.
    - Without CodeDeploy: from GitHub Actions, re-apply the previous known-good tag by running `terraform apply -var=image_tag=<previous>` with the remote backend unlocked for an immediate revert.
- **Observability**: Use Terraform to provision **dashboards, alarms, log group retention, and X-Ray sampling**. In a post-deploy step, GitHub Actions posts the **dashboard URL** and latest deployment link to PR comments and Slack.

## Architecture Diagram (ASCII)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              Developer                                    │
│                           (write code & push)                             │
└───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                   ┌────────────────────────────────────┐
                   │         GitHub Repository          │
                   │     (includes .delightful.yaml)    │
                   └────────────────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────────┐
             │                   GitHub Actions                     │
             │------------------------------------------------------│
             │ 1) Analyzer Workflow                                 │
             │    - Invoke Lambda (AI Code Analyzer)                │
             │    - Analyze lang/deps/traffic                       │
             │    - PR comments & tfvars suggestions                │
             │                                                      │
             │ 2) CI/CD Workflow                                    │
             │    - Build / Test / SCA                              │
             │    - Push image to ECR                               │
             │    - Terraform Apply (CLI, passes image_tag)         │
             │    - Trigger CodeDeploy Blue/Green                   │
             │    - Smoke tests & Slack notifications               │
             └──────────────────────────────────────────────────────┘
                                      │
                                      ▼
                   ┌────────────────────────────────┐
                   │   Terraform Pipeline (CLI)     │
                   │ - Remote state (S3/Dynamo)     │
                   │ - Applies ECS / CodeDeploy     │
                   │ - Configures CloudWatch/X-Ray  │
                   └────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                                   AWS                                     │
│---------------------------------------------------------------------------│
│   ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐           │
│   │     ECS      │◄───►│     ALB      │◄───►│    CodeDeploy   │◄──┐       │
│   │ (TaskDef: TF)│     │ (Blue/Green) │     │(deploy/rollback)│   │       │
│   └──────────────┘     └──────────────┘     └─────────────────┘   │       │
│          ▲                                           │            │       │
│          │                                           │            │       │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐      │       │
│   │     RDS      │     │  ElastiCache │     │  CloudWatch  │  ◄───┘       │
│   │     (DB)     │     │    (Redis)   │     │    + X-Ray   │              │
│   └──────────────┘     └──────────────┘     └──────────────┘              │
└───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                     ┌───────────────────────────┐
                     │  Slack / Dashboard Links  │
                     │ (deploy results & metrics)│
                     └───────────────────────────┘

```

## Summary Matrix

| Layer | Components | Role |
| --- | --- | --- |
| **Developer Layer** | GitHub Repo | Push code and open PRs |
| **Automation Layer** | GitHub Actions | Build/test/deploy automation; triggers AI Analyzer Lambda |
| **Infrastructure Layer** | Terraform Pipeline (CLI + Remote State) | Manages infra and CodeDeploy configuration |
| **AWS Execution Layer** | ECS + ALB + CodeDeploy + CloudWatch | Runs the service, enables Blue/Green + rollback, and monitoring |
| **Analysis Layer** | AI Code Analyzer (Lambda) | Code-driven AI analysis and deployment setting suggestions |

## Network & Deployment Flow (Mermaid)

```mermaid
graph TD
  subgraph VPC[Shared VPC]
    ALB[ALB Blue/Green Listeners]
    ECS[ECS Cluster + X-Ray Sidecar]
  end

  TG_BLUE[Target Group Blue]
  TG_GREEN[Target Group Green]

  GH_ANALYZER["GitHub Actions - Analyzer"] --> AI["AI Code Analyzer Lambda"]
  AI --> S3AI[(S3 Analyzer Outputs)]
  AI --> PR["PR Comments / tfvars"]
  PR --> GH
  S3AI --> TF

  GH["GitHub Actions (OIDC)"] -->|Build_and_Push| ECR[(Amazon ECR)]
  GH -->|Terraform Plan_and_Apply| TF["Terraform Runner"]

  TF -->|Modules| VPC
  TF -->|Modules| CD[CodeDeploy]
  TF -->|State| S3[(S3 State Bucket)]
  TF -->|Lock| DDB[(DynamoDB Lock)]

  CD -->|Blue/Green Deploy| ECS
  CD -->|Traffic| TG_BLUE
  CD -->|Traffic| TG_GREEN
  ALB --> TG_BLUE
  ALB --> TG_GREEN
  TG_BLUE -->|Prod Route| ALB
  TG_GREEN -->|Test Route| ALB

  ECS --> CW[CloudWatch Dashboards]
  ECS --> XR[X-Ray Sampling]
  ALB --> CW
```
