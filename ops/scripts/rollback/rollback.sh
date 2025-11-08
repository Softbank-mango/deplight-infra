#!/bin/bash
#
# Rollback Script for Terraform-managed ECS Deployments
#
# This script rolls back an ECS service to a previous image tag by re-applying
# Terraform with the specified image tag.
#
# Usage: ./rollback.sh <environment> <image_tag>
# Example: ./rollback.sh prod abc123def456
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate arguments
if [ $# -ne 2 ]; then
    log_error "Invalid number of arguments"
    echo "Usage: $0 <environment> <image_tag>"
    echo "Example: $0 prod abc123def456"
    exit 1
fi

ENVIRONMENT=$1
IMAGE_TAG=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INFRA_DIR="$REPO_ROOT/infrastructure/environments/$ENVIRONMENT"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Environment must be either 'dev' or 'prod'"
    exit 1
fi

# Check if infrastructure directory exists
if [ ! -d "$INFRA_DIR" ]; then
    log_error "Infrastructure directory not found: $INFRA_DIR"
    exit 1
fi

log_info "========================================="
log_info "Starting Rollback Process"
log_info "========================================="
log_info "Environment: $ENVIRONMENT"
log_info "Target Image Tag: $IMAGE_TAG"
log_info "Infrastructure Dir: $INFRA_DIR"
log_info "========================================="

# Database Migration Check
echo ""
log_warn "========================================="
log_warn "DATABASE MIGRATION SAFETY CHECK"
log_warn "========================================="
log_warn "Before proceeding, verify:"
log_warn "  ✓ No database migrations applied after target image $IMAGE_TAG"
log_warn "  ✓ Database schema compatible with target version"
log_warn "  ✓ RDS snapshot available (if needed)"
log_warn "  ✓ down.sql migration scripts tested (if applicable)"
log_warn "========================================="
echo ""
read -p "Have you verified database compatibility? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_error "Database verification required before rollback"
    log_info "Rollback cancelled by user"
    exit 0
fi

# Environment-specific confirmation
if [ "$ENVIRONMENT" == "prod" ]; then
    log_warn "🔴 PRODUCTION ENVIRONMENT ROLLBACK"
    log_warn "This action will affect live production traffic!"
    echo ""
    read -p "Type 'ROLLBACK-PROD' to confirm production rollback: " -r
    echo
    if [[ $REPLY != "ROLLBACK-PROD" ]]; then
        log_info "Rollback cancelled - confirmation string did not match"
        exit 0
    fi
else
    log_warn "Rolling back DEV environment to image tag: $IMAGE_TAG"
    read -p "Type 'yes' to confirm: " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
fi

# Change to infrastructure directory
cd "$INFRA_DIR"

# Initialize Terraform if needed
log_info "Initializing Terraform..."
terraform init -reconfigure

# Validate Terraform configuration
log_info "Validating Terraform configuration..."
terraform validate

# Show plan with the rollback image tag
log_info "Generating Terraform plan for rollback..."
terraform plan -var="image_tag=$IMAGE_TAG" -out=rollback.tfplan

# Confirmation before apply
log_warn "Review the plan above carefully."
read -p "Do you want to apply this rollback? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Rollback cancelled by user"
    rm -f rollback.tfplan
    exit 0
fi

# Apply the rollback
log_info "Applying Terraform rollback..."
terraform apply rollback.tfplan

# Clean up plan file
rm -f rollback.tfplan

# Terraform State Drift Verification
echo ""
log_info "========================================="
log_info "Verifying Terraform State Consistency"
log_info "========================================="
log_info "Running terraform plan to check for drift..."

terraform plan -var="image_tag=$IMAGE_TAG" -detailed-exitcode > /dev/null 2>&1
PLAN_EXIT_CODE=$?

case $PLAN_EXIT_CODE in
    0)
        log_info "✅ Terraform state is consistent (no drift detected)"
        ;;
    1)
        log_error "❌ Terraform plan failed - configuration error"
        log_error "Manual intervention required"
        exit 1
        ;;
    2)
        log_warn "⚠️  Drift detected - infrastructure differs from desired state"
        log_warn "This may indicate the rollback did not fully apply"
        log_warn "Running plan again for review..."
        terraform plan -var="image_tag=$IMAGE_TAG"
        ;;
esac

# ECS Service Verification
echo ""
log_info "========================================="
log_info "Verifying ECS Deployment"
log_info "========================================="

AWS_REGION="ap-northeast-2"
CLUSTER_NAME="delightful-deploy-cluster"
SERVICE_NAME="delightful-deploy-service"

log_info "Checking ECS service status..."

# Wait a moment for ECS to update
sleep 5

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text 2>/dev/null || echo "")

if [ -n "$CURRENT_TASK_DEF" ]; then
    log_info "Current Task Definition: $CURRENT_TASK_DEF"

    # Get container image
    CONTAINER_IMAGE=$(aws ecs describe-task-definition \
        --task-definition "$CURRENT_TASK_DEF" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.containerDefinitions[0].image' \
        --output text 2>/dev/null || echo "")

    if [ -n "$CONTAINER_IMAGE" ]; then
        log_info "Container Image: $CONTAINER_IMAGE"

        # Verify image tag matches
        if echo "$CONTAINER_IMAGE" | grep -q ":$IMAGE_TAG"; then
            log_info "✅ Image tag verified in ECS task definition"
        else
            log_warn "⚠️  Image tag mismatch - expected :$IMAGE_TAG"
        fi
    fi

    # Get running tasks count
    RUNNING_TASKS=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME" \
        --desired-status RUNNING \
        --region "$AWS_REGION" \
        --query 'taskArns[*]' \
        --output text 2>/dev/null || echo "")

    TASK_COUNT=$(echo "$RUNNING_TASKS" | wc -w)
    log_info "Running tasks: $TASK_COUNT"

    # Get service status
    SERVICE_STATUS=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}' \
        --output json 2>/dev/null || echo "")

    if [ -n "$SERVICE_STATUS" ]; then
        echo "$SERVICE_STATUS" | jq -r '"Desired: \(.desired), Running: \(.running), Pending: \(.pending)"'
    fi
else
    log_warn "Unable to verify ECS service - AWS CLI may not be configured"
fi

# Show current state
echo ""
log_info "Current Terraform outputs:"
terraform output 2>/dev/null || log_warn "Unable to fetch outputs"

log_info "========================================="
log_info "✅ Rollback Completed"
log_info "========================================="
log_info "Environment: $ENVIRONMENT"
log_info "Rolled back to image tag: $IMAGE_TAG"
log_info "========================================="

echo ""
log_warn "NEXT STEPS:"
log_warn "  1. Monitor CloudWatch Logs: /aws/ecs/delightful-deploy"
log_warn "  2. Check ECS service events in AWS Console"
log_warn "  3. Verify application health endpoints"
log_warn "  4. Monitor for 15-30 minutes"
log_warn ""
log_warn "CloudWatch Console:"
log_warn "  https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups/log-group/\$252Faws\$252Fecs\$252Fdelightful-deploy"
log_warn ""
log_warn "ECS Console:"
log_warn "  https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$CLUSTER_NAME/services/$SERVICE_NAME"

exit 0
