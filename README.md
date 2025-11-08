# Deployment Rollback Guide

This guide provides comprehensive instructions for rolling back deployments in the deplight-platform infrastructure.

## Table of Contents

- [Overview](#overview)
- [Rollback Methods](#rollback-methods)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Procedures](#detailed-procedures)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The deplight-platform supports multiple rollback strategies:

1. **ECS Task Definition Rollback** ⭐ **Most Reliable**: Rollback to a specific Task Definition revision
2. **Terraform Rollback**: Redeploy a previous image tag by re-running Terraform
3. **CodeDeploy Auto-Rollback**: Automatic rollback on deployment failure
4. **Manual CodeDeploy Rollback**: Stop current deployment to trigger rollback

## Rollback Methods

### Method Comparison

| Method | Use Case | Speed | Complexity | Automated | Reliability |
|--------|----------|-------|------------|-----------|-------------|
| **ECS Task Definition** ⭐ | Most reliable, captures full task config | ~3-5 min | Low | Partial | ⭐⭐⭐⭐⭐ |
| **GitHub Actions Workflow** | Recommended for all rollbacks | ~5-10 min | Low | Yes | ⭐⭐⭐⭐ |
| **Terraform Script** | Manual rollback, local execution | ~5-10 min | Medium | Partial | ⭐⭐⭐⭐ |
| **CodeDeploy Auto** | Failed deployments | ~2-5 min | Low | Yes | ⭐⭐⭐ |
| **CodeDeploy Manual** | Stop in-progress deployment | ~2-5 min | Low | Partial | ⭐⭐⭐ |

## Prerequisites

### For All Rollback Methods

- AWS credentials configured (IAM role or access keys)
- Access to the GitHub repository
- Knowledge of the target image tag (commit SHA) to rollback to

### For Script-Based Rollbacks

- AWS CLI installed and configured
- Terraform CLI (v1.6.6+) installed
- Bash shell environment

### Finding Previous Image Tags

```bash
# List recent ECR images
aws ecr describe-images \
  --repository-name delightful-deploy \
  --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-10:].[imageTags[0],imagePushedAt]' \
  --output table

# List recent commits
git log --oneline -10

# Get current deployed image tag
aws ecs describe-services \
  --cluster delightful-deploy-cluster \
  --services delightful-deploy-service \
  --region ap-northeast-2 \
  --query 'services[0].taskDefinition' \
  --output text | xargs aws ecs describe-task-definition \
  --task-definition --region ap-northeast-2 \
  --query 'taskDefinition.containerDefinitions[0].image' \
  --output text
```

## Quick Start

### Option 1: GitHub Actions Workflow (Recommended)

1. Navigate to [Actions tab](../../.github/workflows/rollback.yml) in GitHub
2. Select "Rollback Deployment" workflow
3. Click "Run workflow"
4. Fill in the parameters:
   - **environment**: `dev` or `prod`
   - **image_tag**: Previous commit SHA (e.g., `abc123d`)
   - **rollback_type**: `terraform` (recommended) or `codedeploy`
   - **confirm**: Type `ROLLBACK` exactly
5. Click "Run workflow" and monitor progress

### Option 2: Local Terraform Script

```bash
# Navigate to repository root
cd /path/to/deplight-infra

# Run rollback script
./ops/scripts/rollback/rollback.sh <environment> <image_tag>

# Example
./ops/scripts/rollback/rollback.sh prod abc123d
```

### Option 3: ECS Task Definition Rollback ⭐ (Most Reliable)

```bash
# Recommended: Rollback to a specific Task Definition revision
./ops/scripts/rollback/ecs-taskdef-rollback.sh <environment> [revision]

# Interactive mode (lists recent revisions)
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod

# Direct rollback to revision 42
./ops/scripts/rollback/ecs-taskdef-rollback.sh prod 42
```

**Why use this method?**
- Captures complete task configuration (CPU, memory, env vars, etc.)
- More reliable than image tag alone
- Faster rollback (direct ECS API call)
- No Terraform state changes

### Option 4: CodeDeploy Rollback

```bash
# For in-progress deployments
./ops/scripts/rollback/codedeploy-rollback.sh <environment>

# Example
./ops/scripts/rollback/codedeploy-rollback.sh prod
```

## Detailed Procedures

### 1. ECS Task Definition Rollback ⭐ (Most Reliable)

**When to use**: Fastest and most reliable rollback, recommended for production issues

**Why this method?**
- Rolls back entire task configuration, not just image
- Includes CPU, memory, environment variables, logging config
- Faster than Terraform (direct API call)
- No risk of Terraform state issues

**Steps**:

1. **Find target Task Definition revision**:
   ```bash
   # List recent Task Definition revisions
   aws ecs list-task-definitions \
     --family-prefix delightful-deploy \
     --sort DESC \
     --max-items 10 \
     --region ap-northeast-2

   # Get details of specific revision
   aws ecs describe-task-definition \
     --task-definition delightful-deploy:42 \
     --region ap-northeast-2
   ```

2. **Run rollback script** (Interactive Mode):
   ```bash
   ./ops/scripts/rollback/ecs-taskdef-rollback.sh prod
   ```

   The script will:
   - Show recent Task Definition revisions with images and timestamps
   - Prompt you to select a revision number
   - Perform database migration safety checks
   - Require `ROLLBACK-PROD` confirmation for production
   - Update ECS service
   - Wait for service to stabilize
   - Verify rollback succeeded

3. **Or direct rollback** (if you know the revision):
   ```bash
   ./ops/scripts/rollback/ecs-taskdef-rollback.sh prod 42
   ```

4. **Verify rollback**:
   ```bash
   # Check service status
   aws ecs describe-services \
     --cluster delightful-deploy-cluster \
     --services delightful-deploy-service \
     --region ap-northeast-2

   # Verify Task Definition revision
   aws ecs describe-services \
     --cluster delightful-deploy-cluster \
     --services delightful-deploy-service \
     --region ap-northeast-2 \
     --query 'services[0].taskDefinition'
   ```

5. **Monitor**:
   - CloudWatch Logs: `/aws/ecs/delightful-deploy`
   - ECS Service Events
   - Application health checks

### 2. Terraform Rollback via GitHub Actions

**When to use**: Rollback to any previous version, most controlled approach

**Steps**:

1. **Identify the target image tag**:
   ```bash
   # Check recent deployments in git history
   git log --oneline -10

   # Verify image exists in ECR
   aws ecr describe-images \
     --repository-name delightful-deploy \
     --image-ids imageTag=abc123d \
     --region ap-northeast-2
   ```

2. **Trigger the rollback workflow**:
   - Go to GitHub Actions → "Rollback Deployment"
   - Select parameters:
     - Environment: `prod`
     - Image Tag: `abc123d`
     - Rollback Type: `terraform`
     - Confirm: `ROLLBACK`

3. **Monitor the rollback**:
   - Watch the GitHub Actions logs
   - Check the workflow summary for verification

4. **Verify the rollback**:
   ```bash
   # Check ECS service status
   aws ecs describe-services \
     --cluster delightful-deploy-cluster \
     --services delightful-deploy-service \
     --region ap-northeast-2

   # Check running tasks
   aws ecs list-tasks \
     --cluster delightful-deploy-cluster \
     --service-name delightful-deploy-service \
     --region ap-northeast-2
   ```

### 3. Local Terraform Rollback

**When to use**: When GitHub Actions is unavailable or you prefer local control

**Steps**:

1. **Prepare environment**:
   ```bash
   cd deplight-infra
   git checkout roll-back
   git pull origin roll-back
   ```

2. **Configure AWS credentials**:
   ```bash
   # Via environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   export AWS_REGION=ap-northeast-2

   # Or use AWS CLI profiles
   export AWS_PROFILE=your-profile
   ```

3. **Run rollback script**:
   ```bash
   ./ops/scripts/rollback/rollback.sh prod abc123d
   ```

4. **Review and confirm**:
   - The script will show Terraform plan
   - Review changes carefully
   - Type `yes` when prompted
   - Type `yes` again to apply

5. **Verify deployment**:
   ```bash
   # Check Terraform outputs
   cd infrastructure/environments/prod
   terraform output
   ```

### 4. CodeDeploy Auto-Rollback

**When to use**: Automatic rollback on deployment failure (already configured)

**How it works**:
- CodeDeploy monitors deployment health
- On failure (health checks, alarms), automatically rolls back
- No manual intervention required

**Verify auto-rollback is enabled**:
```bash
aws deploy get-deployment-group \
  --application-name deplight-prod-app \
  --deployment-group-name prod-deployment-group \
  --region ap-northeast-2 \
  --query 'deploymentGroupInfo.autoRollbackConfiguration'
```

### 5. Manual CodeDeploy Rollback

**When to use**: Stop an in-progress problematic deployment

**Steps**:

1. **Find current deployment**:
   ```bash
   aws deploy list-deployments \
     --application-name deplight-prod-app \
     --deployment-group-name prod-deployment-group \
     --region ap-northeast-2
   ```

2. **Run rollback script**:
   ```bash
   ./ops/scripts/rollback/codedeploy-rollback.sh prod
   ```

3. **Or manually via AWS CLI**:
   ```bash
   # Stop deployment
   aws deploy stop-deployment \
     --deployment-id d-XXXXXXXXX \
     --auto-rollback-enabled \
     --region ap-northeast-2
   ```

4. **Monitor rollback**:
   ```bash
   # Watch deployment status
   aws deploy get-deployment \
     --deployment-id d-XXXXXXXXX \
     --region ap-northeast-2
   ```

## Troubleshooting

### Image Tag Not Found in ECR

**Problem**: Error message "Image tag not found in ECR"

**Solution**:
```bash
# List available tags
aws ecr describe-images \
  --repository-name delightful-deploy \
  --region ap-northeast-2 \
  --query 'imageDetails[*].imageTags[0]' \
  --output table

# Verify you're using the correct tag format (commit SHA, 7+ chars)
```

### Terraform State Lock

**Problem**: "Error acquiring the state lock"

**Solution**:
```bash
# Check lock status
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"deplight-infra/terraform.tfstate"}}' \
  --region ap-northeast-2

# Force unlock (use with caution!)
cd infrastructure/environments/<env>
terraform force-unlock <lock-id>
```

### ECS Service Not Updating

**Problem**: Terraform completes but ECS shows old image

**Solution**:
```bash
# Force new deployment
aws ecs update-service \
  --cluster delightful-deploy-cluster \
  --service delightful-deploy-service \
  --force-new-deployment \
  --region ap-northeast-2

# Wait for deployment to stabilize
aws ecs wait services-stable \
  --cluster delightful-deploy-cluster \
  --services delightful-deploy-service \
  --region ap-northeast-2
```

### CodeDeploy Deployment Stuck

**Problem**: Deployment shows "InProgress" for extended time

**Solution**:
```bash
# Check deployment events
aws deploy get-deployment \
  --deployment-id d-XXXXXXXXX \
  --region ap-northeast-2 \
  --query 'deploymentInfo.{status:status,creator:creator,createTime:createTime}'

# If truly stuck (>30 minutes), stop it
aws deploy stop-deployment \
  --deployment-id d-XXXXXXXXX \
  --auto-rollback-enabled \
  --region ap-northeast-2
```

### Permission Denied

**Problem**: "AccessDenied" or "UnauthorizedOperation" errors

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name <your-username>

# For GitHub Actions, verify OIDC role
```

## Best Practices

### Before Rollback

1. **Document the issue**: Record what went wrong and why rollback is needed
2. **Notify stakeholders**: Alert team members about the rollback
3. **Identify target version**: Determine the last known good version
4. **Check dependencies**: Ensure no database migrations or breaking changes

### During Rollback

1. **Monitor closely**: Watch logs, metrics, and health checks
2. **Use staging first**: Test rollback in dev/staging before production
3. **Keep communication open**: Update team on progress
4. **Document steps**: Record all commands and actions taken

### After Rollback

1. **Verify functionality**: Run smoke tests and health checks
2. **Monitor for 30 minutes**: Watch for any issues post-rollback
3. **Post-mortem**: Conduct incident review
4. **Update runbooks**: Document lessons learned
5. **Plan fix**: Create plan to address the original issue

### Rollback Safety Checklist

#### Pre-Rollback Verification
- [ ] Identified correct previous image tag or Task Definition revision
- [ ] Verified image exists in ECR (or Task Definition exists)
- [ ] **Verified database migrations have NOT been applied after target version** ⭐
- [ ] Confirmed database schema is compatible with target version
- [ ] RDS snapshot available (if needed)
- [ ] down.sql migration scripts prepared (if applicable)
- [ ] Notified team members and stakeholders

#### Rollback Execution
- [ ] Reviewed Terraform plan carefully (if using Terraform rollback)
- [ ] Tested rollback in dev/staging environment first
- [ ] Environment-specific confirmation completed:
  - [ ] **Prod**: Typed `ROLLBACK-PROD` confirmation
  - [ ] **Dev**: Typed `yes` confirmation
- [ ] Have backup plan if rollback fails

#### Post-Rollback Verification
- [ ] Terraform state drift check passed (exit code 0)
- [ ] ECS task definition updated correctly
- [ ] Container image tag matches expected version
- [ ] Running task count matches desired count
- [ ] Application health checks passing
- [ ] Ready to monitor deployment for 15-30 minutes

## Emergency Contact

In case of critical issues, follow this troubleshooting sequence:

### 1️⃣ Check CloudWatch Alarms & Dashboards

```bash
# CloudWatch Dashboard URL
https://console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#dashboards:

# Check recent alarms
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --region ap-northeast-2
```

### 2️⃣ Review ECS Service Events

```bash
# ECS Service Events
aws ecs describe-services \
  --cluster delightful-deploy-cluster \
  --services delightful-deploy-service \
  --region ap-northeast-2 \
  --query 'services[0].events[0:10]'

# ECS Console URL
https://console.aws.amazon.com/ecs/home?region=ap-northeast-2#/clusters/delightful-deploy-cluster/services/delightful-deploy-service
```

### 3️⃣ Check Application Logs

**CloudWatch Log Groups:**
- **ECS Container Logs**: `/aws/ecs/delightful-deploy`
- **Lambda Logs**: `/aws/lambda/delightful-deploy-ai-analyzer`

```bash
# Tail recent ECS logs
aws logs tail /aws/ecs/delightful-deploy \
  --follow \
  --region ap-northeast-2 \
  --since 10m

# CloudWatch Logs Console
https://console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#logsV2:log-groups/log-group/$252Faws$252Fecs$252Fdelightful-deploy
```

### 4️⃣ Check CodeDeploy Deployment Logs

**CodeDeploy Logs:**
- **Deployment History**: CodeDeploy Console
- **Agent Logs** (if using EC2): `/var/log/aws/codedeploy-agent/codedeploy-agent.log`

```bash
# List recent deployments
aws deploy list-deployments \
  --application-name deplight-prod-app \
  --deployment-group-name prod-deployment-group \
  --region ap-northeast-2

# Get deployment details
aws deploy get-deployment \
  --deployment-id <deployment-id> \
  --region ap-northeast-2

# CodeDeploy Console
https://console.aws.amazon.com/codesuite/codedeploy/applications
```

### 5️⃣ Verify Terraform State

```bash
# Check for drift
cd infrastructure/environments/<env>
terraform plan -detailed-exitcode

# Exit codes:
# 0 = no drift
# 1 = error
# 2 = drift detected
```

### 6️⃣ Escalate to Infrastructure Team

If issues persist after following the above steps, escalate with:
- Current symptoms and error messages
- Steps already taken
- Rollback status (completed/failed)
- CloudWatch logs excerpt

## Additional Resources

- [AWS ECS Deployment Documentation](https://docs.aws.amazon.com/ecs/latest/developerguide/deployment-types.html)
- [AWS CodeDeploy Rollback](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Internal Deployment System Docs](../../deployment_system.md)

---

**Last Updated**: 2025-11-08
**Maintained by**: Infrastructure Team
**Review Frequency**: Quarterly
