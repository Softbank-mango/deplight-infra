# Deplight Infrastructure - Complete Guide

**Enterprise-Grade AWS ECS Deployment System with Advanced Rollback Capabilities**

[![AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20ECR%20%7C%20CodeDeploy-orange)](https://aws.amazon.com/)
[![Terraform](https://img.shields.io/badge/Terraform-1.6.6+-purple)](https://www.terraform.io/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-blue)](https://github.com/features/actions)
[![Self-Healing](https://img.shields.io/badge/Rollback-Fully%20Automated-green)](./ops/runbooks/ROLLBACK.md)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Deployment System](#deployment-system)
- [Rollback System](#rollback-system) ⭐
- [Infrastructure Components](#infrastructure-components)
- [Getting Started](#getting-started)
- [Usage Guide](#usage-guide)
- [Cost Analysis](#cost-analysis)
- [Security](#security)
- [Monitoring](#monitoring)
- [Documentation](#documentation)

---

## 🎯 Overview

Deplight Infrastructure는 **production-ready, self-healing AWS 배포 시스템**입니다.

### **핵심 가치**

```
┌──────────────────────────────────────────────────────────┐
│  배포 실패 → 자동 복구 (3-5분)                          │
│  수동 롤백 → UI 버튼 클릭 (확인 다이얼로그)             │
│  인프라 관리 → Terraform IaC                             │
│  배포 전략 → CodeDeploy Blue/Green                       │
│  모니터링 → CloudWatch + X-Ray                           │
└──────────────────────────────────────────────────────────┘
```

### **Who Is This For?**

- ✅ DevOps 팀이 안정적인 배포 시스템이 필요할 때
- ✅ 새벽 배포 실패로 깨어나고 싶지 않을 때
- ✅ 롤백을 빠르고 안전하게 수행하고 싶을 때
- ✅ 인프라를 코드로 관리하고 싶을 때

---

## 🏗️ Architecture

### **High-Level Overview**

```
┌─────────────────┐
│   Developer     │  Push code to GitHub
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions (CI/CD)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Build & Test │→│ Push to ECR  │→│Terraform Apply│  │
│  └──────────────┘  └──────────────┘  └───────┬──────┘  │
└──────────────────────────────────────────────┼─────────┘
                                               │
                        ┌──────────────────────┼──────────────────────┐
                        │                      │                      │
                        ▼                      ▼                      ▼
          ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
          │   Amazon ECR     │   │   ECS Service    │   │   CodeDeploy     │
          │ (Docker Images)  │   │  (Blue/Green)    │   │  (Deployment)    │
          └──────────────────┘   └────────┬─────────┘   └──────────────────┘
                                           │
                        ┌──────────────────┼──────────────────────┐
                        │                  │                      │
                        ▼                  ▼                      ▼
          ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
          │       ALB        │   │    CloudWatch    │   │     X-Ray        │
          │  (Load Balancer) │   │  (Logs/Metrics)  │   │   (Tracing)      │
          └──────────────────┘   └──────────────────┘   └──────────────────┘
```

### **Rollback Architecture** (핵심 차별화 기능)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT FAILURE DETECTED                         │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
         ┌───────────────────────────────────────────────────┐
         │  Auto-Rollback Workflow (workflow_run event)      │
         │                                                   │
         │  1. Fetch last successful deployment artifact    │
         │  2. Extract image tag (abc123d)                  │
         │  3. Find matching Task Definition revision       │
         │  4. Validate target < current (safety check)     │
         │  5. Update ECS service to previous revision      │
         │  6. Wait for service stabilization               │
         │  7. Verify rollback success                      │
         └───────────────────────────────────────────────────┘
                                 │
                                 ▼
         ┌───────────────────────────────────────────────────┐
         │  ✅ SERVICE RESTORED (3-5 minutes)                │
         │  📊 GitHub workflow summary created               │
         │  📧 Notifications sent (optional)                 │
         └───────────────────────────────────────────────────┘
```

---

## ⭐ Key Features

### **1. 🤖 Fully Automated Rollback** (Zero Touch)

**배포 실패 → 자동 복구 (사람 개입 없음)**

```yaml
Deploy fails at 3:00 AM
   ↓ (자동)
Auto-rollback triggered
   ↓ (3-5분)
Service restored to last stable version
   ↓
You wake up at 9:00 AM → Check logs → Fix issue → Re-deploy
```

**특징:**
- ✅ **ZERO manual intervention** - 새벽에 깨어날 필요 없음
- ✅ **Infinite loop prevention** - 롤백의 롤백은 하지 않음
- ✅ **Safety checks** - DB migration 호환성 체크
- ✅ **Terraform drift detection** - 상태 일관성 검증
- ✅ **Audit trail** - 모든 롤백 기록 저장

### **2. 🎨 UI-Triggered Manual Rollback**

**Dashboard에서 버튼 클릭 → 확인 → 롤백**

```tsx
<RollbackButton
  environment="prod"
  userId="user@example.com"
  apiEndpoint="https://api.example.com/rollback"
/>
```

**플로우:**
1. 사용자가 UI에서 "롤백" 버튼 클릭
2. 확인 다이얼로그 표시 (환경, 버전, 영향 설명)
3. 확인 시 Lambda 함수 호출
4. GitHub Actions 롤백 워크플로우 트리거
5. 3-5분 후 롤백 완료

**제공 컴포넌트:**
- React + Material-UI (`apps/ui-samples/RollbackButton.tsx`)
- Vue 3 + Vuetify (`apps/ui-samples/RollbackButton.vue`)
- Lambda API (`lambda/rollback-trigger/`)

### **3. 📜 Multiple Rollback Methods**

| Method | Speed | Automation | Best For |
|--------|-------|------------|----------|
| **Auto Rollback** | 3-5 min | ✅ Full | Deploy failures |
| **UI Button** | 3-5 min | Triggered | User-initiated |
| **ECS TaskDef** | 3-5 min | Interactive | Precise control |
| **Terraform** | 5-10 min | Script | Infrastructure |
| **CodeDeploy** | 2-5 min | Manual | In-progress |

### **4. 🔒 Safety & Compliance**

**Pre-Rollback Checks:**
- ✅ Database migration compatibility
- ✅ Image existence in ECR
- ✅ Task Definition validation
- ✅ Environment-specific confirmation (PROD requires explicit string)

**Post-Rollback Verification:**
- ✅ Terraform state drift detection (`terraform plan -detailed-exitcode`)
- ✅ ECS service health validation
- ✅ Container image tag verification
- ✅ Running task count validation

**Audit Trail:**
- ✅ DynamoDB audit log (who, when, what, why)
- ✅ GitHub Actions workflow history
- ✅ CloudWatch logs

### **5. 📊 Complete Observability**

**Monitoring Stack:**
- CloudWatch Dashboards (metrics, alarms)
- CloudWatch Logs (ECS, Lambda, CodeDeploy)
- X-Ray (distributed tracing)
- GitHub Actions (deployment history)

**Logs & Metrics:**
```bash
# ECS Container Logs
/aws/ecs/delightful-deploy

# Lambda Logs
/aws/lambda/rollback-trigger

# Audit Logs
DynamoDB: rollback-audit-log table
```

---

## 🚀 Deployment System

### **Deployment Pipeline**

```
┌──────────────┐
│ 1. Code Push │  Developer pushes to GitHub
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ 2. GitHub Actions        │
│    - Build Docker image  │
│    - Run tests           │
│    - Security scan       │
│    - Push to ECR         │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 3. Terraform Apply       │
│    - Update ECS TaskDef  │
│    - Pass image tag      │
│    - Remote state (S3)   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 4. CodeDeploy Blue/Green │
│    - Create new tasks    │
│    - Health check        │
│    - Traffic shift       │
│    - Auto rollback on ❌ │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 5. Post-Deploy           │
│    - Save deployment     │
│    - Smoke tests         │
│    - Slack notification  │
│    - Dashboard update    │
└──────────────────────────┘
```

### **Deployment Workflow** (`.github/workflows/deploy.yml`)

**Key Steps:**
1. **Build & Push**: Docker image → ECR (tagged with commit SHA)
2. **AI Analysis**: Lambda analyzes code for optimal config
3. **Terraform Plan**: Preview infrastructure changes
4. **Terraform Apply**: Update ECS Task Definition
5. **CodeDeploy**: Blue/Green deployment
6. **Verification**: Ensure deployment success
7. **State Tracking**: Save successful deployment artifact

**Success Tracking:**
```yaml
deployment-state/
├── last-successful-image-tag.txt  # abc123d
├── environment.txt                 # prod
├── commit-sha.txt                  # full SHA
└── timestamp.txt                   # 2024-11-08T12:00:00Z
```

---

## 🔄 Rollback System

### **Rollback Methods Comparison**

| Feature | Auto Rollback | UI Button | ECS TaskDef | Terraform Script |
|---------|---------------|-----------|-------------|------------------|
| **Trigger** | Deploy failure | Manual click | Manual script | Manual script |
| **Speed** | 3-5 min | 3-5 min | 3-5 min | 5-10 min |
| **User Action** | None | Click + Confirm | Select revision | Run command |
| **Safety Checks** | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Audit Log** | ✅ Yes | ✅ Yes | ✅ Manual | ✅ Manual |
| **Best For** | Automatic | User-initiated | Precise control | Local testing |

### **1. Auto Rollback** 🤖

**File**: `.github/workflows/auto-rollback.yml`

**Triggered by**: `workflow_run` event (deploy failure)

**Process:**
```python
1. Deployment fails (any step in deploy.yml)
2. auto-rollback.yml triggered automatically
3. Check: Is this a rollback? (No → proceed, Yes → skip)
4. Fetch last successful deployment artifact
5. Extract image tag
6. Find matching Task Definition revision
7. Validate: target_revision < current_revision
8. Update ECS service
9. Wait for stability
10. Verify success
11. Create summary report
```

**Loop Prevention:**
```python
if workflow_name.contains("Rollback"):
    skip_auto_rollback()  # Don't rollback a rollback!
```

**Cost**: $0 (included in GitHub Actions free tier)

### **2. UI-Triggered Rollback** 🎨

**Files**:
- Lambda: `lambda/rollback-trigger/lambda_function.py`
- UI (React): `apps/ui-samples/RollbackButton.tsx`
- UI (Vue): `apps/ui-samples/RollbackButton.vue`

**Architecture:**
```
User clicks [롤백] button
   ↓
Confirmation dialog
   ↓
POST /rollback → Lambda
   ↓
Lambda triggers GitHub Actions workflow
   ↓
Rollback executed
```

**Lambda Function:**
- Validates user request
- Retrieves last successful image tag
- Calls GitHub API (`workflow_dispatch`)
- Records audit log to DynamoDB
- Returns rollback status

**UI Component:**
- Environment-specific warnings (Dev = yellow, Prod = red)
- Detailed confirmation dialog
- Progress indicators
- Auto-opens GitHub Actions monitor

**Deployment:**
```bash
cd lambda/rollback-trigger
terraform apply -var="github_token=ghp_xxx"
# Output: API Gateway endpoint
```

**Cost**: < $0.01/month (100 rollbacks)

### **3. ECS Task Definition Rollback** ⭐

**File**: `ops/scripts/rollback/ecs-taskdef-rollback.sh`

**Why best for precision:**
- Rolls back ENTIRE task config (not just image)
- Includes: CPU, memory, env vars, logging, networking
- Faster than Terraform (direct ECS API)
- No Terraform state changes

**Usage:**
```bash
# Interactive mode (shows last 10 revisions)
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod

# Direct rollback to revision 42
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod 42
```

**Interactive Output:**
```
Recent Task Definition Revisions:
==================================
► Revision 45 (CURRENT) - ...ecr.../delightful-deploy:abc123d - 2024-11-08T12:00:00Z
  Revision 44 - ...ecr.../delightful-deploy:def456e - 2024-11-08T11:00:00Z
  Revision 43 - ...ecr.../delightful-deploy:ghi789f - 2024-11-08T10:00:00Z

Enter the revision number to rollback to: 44
```

### **4. Terraform Rollback**

**File**: `ops/scripts/rollback/rollback.sh`

**Features:**
- DB migration safety check
- Terraform drift detection
- ECS verification
- Environment-specific confirmations

**Enhanced Checks:**
```bash
1. DB Migration Safety Check
   - Verifies no migrations after target version
   - Checks RDS snapshot availability

2. Environment-Specific Confirmation
   - Prod: Requires "ROLLBACK-PROD" (exact string)
   - Dev: Simple "yes"

3. Terraform Drift Detection
   - Runs `terraform plan -detailed-exitcode`
   - Exit code 0 = success (no drift)
   - Exit code 2 = drift detected (warning)

4. ECS Verification
   - Verifies image tag in ECS
   - Checks running task count
   - Displays service status
```

**Usage:**
```bash
./ops/scripts/rollback/rollback.sh prod abc123d
```

### **5. CodeDeploy Rollback**

**File**: `ops/scripts/rollback/codedeploy-rollback.sh`

**For**: Stopping in-progress deployments

**Features:**
- Auto-rollback configuration verification
- Deployment status checking
- Automatic rollback trigger

---

## 🏗️ Infrastructure Components

### **AWS Resources**

| Component | Purpose | Managed By |
|-----------|---------|------------|
| **ECS Cluster** | Container orchestration | Terraform |
| **ECS Service** | Run containers | Terraform |
| **ALB** | Load balancing | Terraform |
| **ECR** | Docker image registry | Terraform |
| **CodeDeploy** | Blue/Green deployment | Terraform |
| **CloudWatch** | Logs & Metrics | Terraform |
| **X-Ray** | Distributed tracing | Terraform |
| **DynamoDB** | Audit logs | Terraform |
| **Lambda** | Rollback trigger API | Terraform |
| **API Gateway** | REST API endpoint | Terraform |
| **S3** | Terraform state, artifacts | Terraform |

### **GitHub Resources**

| Component | Purpose | Location |
|-----------|---------|----------|
| **Deploy Workflow** | CI/CD pipeline | `.github/workflows/deploy.yml` |
| **Auto-Rollback** | Self-healing | `.github/workflows/auto-rollback.yml` |
| **Manual Rollback** | User-triggered | `.github/workflows/rollback.yml` |
| **OIDC Provider** | GitHub → AWS auth | Infrastructure |

### **Infrastructure as Code**

```
infrastructure/
├── modules/
│   ├── ecs-service/          # ECS cluster, service, tasks
│   ├── codedeploy-bluegreen/ # CodeDeploy configuration
│   ├── network-baseline/     # VPC, subnets, security groups
│   ├── iam-github-oidc/      # GitHub OIDC authentication
│   └── observability-suite/  # CloudWatch, X-Ray
├── environments/
│   ├── dev/                  # Dev environment
│   └── prod/                 # Prod environment
└── backend-config/
    └── remote-state/         # S3 + DynamoDB for Terraform state
```

---

## 🚀 Getting Started

### **Prerequisites**

- AWS Account with appropriate IAM permissions
- GitHub repository with OIDC configured
- Terraform 1.6.6+
- AWS CLI
- Docker

### **Initial Setup**

#### 1. **Clone Repository**

```bash
git clone https://github.com/Softbank-mango/deplight-infra.git
cd deplight-infra
```

#### 2. **Configure AWS Credentials**

```bash
# Via environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=ap-northeast-2

# Or AWS CLI profile
aws configure --profile deplight
export AWS_PROFILE=deplight
```

#### 3. **Initialize Terraform**

```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

#### 4. **Configure GitHub Secrets**

```
Settings → Secrets and variables → Actions:

- AWS_GITHUB_OIDC_ROLE: arn:aws:iam::xxx:role/github-actions-role
- SLACK_WEBHOOK: https://hooks.slack.com/services/xxx (optional)
```

#### 5. **Deploy First Application**

```bash
# Trigger workflow via GitHub UI or
git push origin main
```

---

## 📖 Usage Guide

### **Normal Deployment**

```bash
# 1. Make code changes
git checkout -b feature/new-feature
# ... make changes ...

# 2. Commit and push
git commit -m "Add new feature"
git push origin feature/new-feature

# 3. Create PR and merge to main

# 4. GitHub Actions automatically:
#    - Builds Docker image
#    - Pushes to ECR
#    - Runs Terraform
#    - Deploys via CodeDeploy
#    - Saves deployment state
```

### **Manual Rollback (UI)**

```tsx
// In your React dashboard
import { RollbackButton } from './RollbackButton';

<RollbackButton
  environment="prod"
  currentImageTag="abc123d"
  userId="user@example.com"
  apiEndpoint="https://your-api.amazonaws.com/rollback"
  onSuccess={(data) => {
    console.log('Rollback initiated:', data);
  }}
/>
```

### **Manual Rollback (CLI)**

```bash
# List recent deployments
aws ecr describe-images \
  --repository-name delightful-deploy \
  --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-10:]'

# Rollback to specific version
./ops/scripts/rollback/rollback.sh prod abc123d

# Or ECS Task Definition rollback
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod
```

### **View Rollback History**

```bash
# GitHub Actions
gh run list --workflow=auto-rollback.yml

# DynamoDB audit log
aws dynamodb scan \
  --table-name rollback-audit-log \
  --limit 10
```

---

## 💰 Cost Analysis

### **Monthly Costs** (Estimated for small production workload)

| Service | Usage | Cost |
|---------|-------|------|
| **ECS** | 2 tasks × 0.5 vCPU × 1 GB | $30 |
| **ECR** | 10 GB storage | $1 |
| **ALB** | 1 ALB + 10 GB processed | $20 |
| **CloudWatch** | Logs 10 GB + metrics | $5 |
| **CodeDeploy** | Free for ECS | $0 |
| **Lambda** | 100 rollback invocations | < $0.01 |
| **DynamoDB** | 100 writes/month | < $0.01 |
| **S3** | Terraform state | < $0.50 |
| **Data Transfer** | 100 GB out | $9 |
| **GitHub Actions** | 2000 min/month (free tier) | $0 |

**Total: ~$65/month**

### **Rollback System Costs**

**Negligible** (< $0.05/month for 100 rollbacks):
- Auto-rollback: GitHub Actions (free tier)
- UI-triggered: Lambda ($0.00002) + API Gateway ($0.0001) + DynamoDB ($0.000125)
- Scripts: $0 (runs locally)

### **Cost Savings from Auto-Rollback**

**Downtime cost avoidance:**
- Without auto-rollback: 20-60 min downtime per incident
- With auto-rollback: 3-5 min downtime per incident
- **Savings: 15-55 minutes per incident**

If downtime costs $1000/hour:
- Savings per incident: $250-900
- ROI: ∞ (zero added cost)

---

## 🔒 Security

### **Authentication & Authorization**

**GitHub Actions:**
- OIDC (no long-lived credentials)
- Scoped IAM roles
- Least privilege access

**UI Rollback:**
- JWT/Cognito authentication (implementable)
- User ID tracking
- Audit trail in DynamoDB

### **Network Security**

- VPC with private subnets
- Security groups (least privilege)
- ALB with HTTPS termination
- Secrets in AWS Secrets Manager

### **Compliance**

- ✅ Audit trail (DynamoDB + GitHub Actions)
- ✅ Immutable infrastructure (Terraform)
- ✅ Version control (Git)
- ✅ Automated testing (CI/CD)
- ✅ Rollback capability (multiple methods)

---

## 📊 Monitoring

### **CloudWatch Dashboards**

```bash
# Access dashboard
https://console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#dashboards:
```

**Metrics Tracked:**
- ECS: CPU, memory, task count
- ALB: Request count, latency, errors
- Deployments: Success rate, duration
- Rollbacks: Frequency, success rate

### **Logs**

```bash
# ECS Container Logs
aws logs tail /aws/ecs/delightful-deploy --follow

# Lambda Rollback Logs
aws logs tail /aws/lambda/rollback-trigger --follow

# Query logs
aws logs filter-log-events \
  --log-group-name /aws/ecs/delightful-deploy \
  --filter-pattern "ERROR"
```

### **Alarms**

- ECS task health
- ALB 5xx errors
- Deployment failures
- Rollback failures

---

## 📚 Documentation

### **Core Documentation**

| Document | Description |
|----------|-------------|
| [ROLLBACK.md](./ops/runbooks/ROLLBACK.md) | Complete rollback guide |
| [deployment_system.md](./deployment_system.md) | Deployment architecture |
| [UI Samples README](./apps/ui-samples/README.md) | UI component guide |
| [Lambda README](./lambda/rollback-trigger/README.md) | Lambda function guide |

### **Workflows**

| Workflow | Purpose | Location |
|----------|---------|----------|
| Deploy Service | CI/CD pipeline | `.github/workflows/deploy.yml` |
| Auto Rollback | Self-healing | `.github/workflows/auto-rollback.yml` |
| Manual Rollback | User-triggered | `.github/workflows/rollback.yml` |

### **Scripts**

| Script | Purpose | Location |
|--------|---------|----------|
| Terraform Rollback | Infrastructure rollback | `ops/scripts/rollback/rollback.sh` |
| ECS TaskDef Rollback | Task definition rollback | `ops/scripts/rollback/ecs-taskdef-rollback.sh` |
| CodeDeploy Rollback | Deployment rollback | `ops/scripts/rollback/codedeploy-rollback.sh` |

---

## 🎯 Quick Reference

### **Common Commands**

```bash
# Deploy to dev
git push origin main

# Manual rollback (Terraform)
./ops/scripts/rollback/rollback.sh prod abc123d

# Manual rollback (ECS TaskDef)
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod

# View rollback history
gh run list --workflow=auto-rollback.yml

# Check ECS service
aws ecs describe-services \
  --cluster delightful-deploy-cluster \
  --services delightful-deploy-service

# View audit logs
aws dynamodb scan --table-name rollback-audit-log --limit 10
```

### **Emergency Contacts**

1. Check CloudWatch Dashboard
2. Review ECS Service Events
3. Check CodeDeploy Status
4. Verify Terraform State
5. Escalate to infrastructure team

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

Built with:
- [Terraform](https://www.terraform.io/)
- [GitHub Actions](https://github.com/features/actions)
- [AWS ECS](https://aws.amazon.com/ecs/)
- [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)

---

**Last Updated**: 2024-11-08
**Version**: 2.0.0
**Maintained by**: Infrastructure Team
**Review Frequency**: Quarterly

---

## 📞 Support

- 📖 [Documentation](./docs/)
- 🐛 [Issues](https://github.com/Softbank-mango/deplight-infra/issues)
- 💬 [Discussions](https://github.com/Softbank-mango/deplight-infra/discussions)

---

**⭐ Star this repo if you find it useful!**
