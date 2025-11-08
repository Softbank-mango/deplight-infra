#!/bin/bash
#
# ECS Task Definition Rollback Script
#
# This script rolls back an ECS service to a previous Task Definition revision.
# This is more reliable than image tag rollback as it captures the entire task configuration.
#
# Usage: ./ecs-taskdef-rollback.sh <environment> <task-definition-revision>
# Example: ./ecs-taskdef-rollback.sh prod 42
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Validate arguments
if [ $# -lt 1 ]; then
    log_error "Invalid number of arguments"
    echo "Usage: $0 <environment> [task-definition-revision]"
    echo "Example: $0 prod 42"
    echo ""
    echo "If no revision is specified, you'll be shown recent revisions to choose from."
    exit 1
fi

ENVIRONMENT=$1
TASK_DEF_REVISION=${2:-}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Environment must be either 'dev' or 'prod'"
    exit 1
fi

# AWS Configuration
AWS_REGION="ap-northeast-2"
CLUSTER_NAME="delightful-deploy-cluster"
SERVICE_NAME="delightful-deploy-service"
TASK_FAMILY="delightful-deploy"

log_info "========================================="
log_info "ECS Task Definition Rollback"
log_info "========================================="
log_info "Environment: $ENVIRONMENT"
log_info "Cluster: $CLUSTER_NAME"
log_info "Service: $SERVICE_NAME"
log_info "Task Family: $TASK_FAMILY"
log_info "========================================="

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Verify AWS credentials
log_step "Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1 || {
    log_error "AWS credentials not configured or invalid"
    exit 1
}
log_info "AWS credentials verified"

# Get current task definition
log_step "Fetching current task definition..."
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text 2>/dev/null || echo "")

if [ -z "$CURRENT_TASK_DEF" ]; then
    log_error "Failed to retrieve current task definition"
    log_error "Service may not exist: $SERVICE_NAME"
    exit 1
fi

CURRENT_REVISION=$(echo "$CURRENT_TASK_DEF" | grep -oP ':\K\d+$')
log_info "Current Task Definition: $CURRENT_TASK_DEF"
log_info "Current Revision: $CURRENT_REVISION"

# If no revision specified, show recent revisions
if [ -z "$TASK_DEF_REVISION" ]; then
    log_step "Fetching recent task definition revisions..."
    echo ""
    echo "Recent Task Definition Revisions:"
    echo "=================================="

    aws ecs list-task-definitions \
        --family-prefix "$TASK_FAMILY" \
        --sort DESC \
        --max-items 10 \
        --region "$AWS_REGION" \
        --query 'taskDefinitionArns[]' \
        --output text | tr '\t' '\n' | while read -r arn; do

        REVISION=$(echo "$arn" | grep -oP ':\K\d+$')

        # Get task definition details
        TASK_INFO=$(aws ecs describe-task-definition \
            --task-definition "$arn" \
            --region "$AWS_REGION" \
            --query 'taskDefinition.{image:containerDefinitions[0].image,created:registeredAt}' \
            --output json)

        IMAGE=$(echo "$TASK_INFO" | jq -r '.image')
        CREATED=$(echo "$TASK_INFO" | jq -r '.created')

        if [ "$REVISION" == "$CURRENT_REVISION" ]; then
            echo -e "${GREEN}► Revision $REVISION${NC} (CURRENT) - $IMAGE - $CREATED"
        else
            echo "  Revision $REVISION - $IMAGE - $CREATED"
        fi
    done

    echo ""
    read -p "Enter the revision number to rollback to: " TASK_DEF_REVISION

    if [ -z "$TASK_DEF_REVISION" ]; then
        log_error "No revision specified"
        exit 1
    fi
fi

# Validate revision is a number
if ! [[ "$TASK_DEF_REVISION" =~ ^[0-9]+$ ]]; then
    log_error "Invalid revision number: $TASK_DEF_REVISION"
    exit 1
fi

# Check if rolling back to current version
if [ "$TASK_DEF_REVISION" == "$CURRENT_REVISION" ]; then
    log_error "Target revision ($TASK_DEF_REVISION) is the same as current revision"
    log_error "No rollback needed"
    exit 1
fi

# Construct target task definition ARN
TARGET_TASK_DEF="$TASK_FAMILY:$TASK_DEF_REVISION"

# Verify target task definition exists
log_step "Verifying target task definition exists..."
aws ecs describe-task-definition \
    --task-definition "$TARGET_TASK_DEF" \
    --region "$AWS_REGION" \
    > /dev/null 2>&1 || {
    log_error "Task definition not found: $TARGET_TASK_DEF"
    exit 1
}

# Get target task details
TARGET_IMAGE=$(aws ecs describe-task-definition \
    --task-definition "$TARGET_TASK_DEF" \
    --region "$AWS_REGION" \
    --query 'taskDefinition.containerDefinitions[0].image' \
    --output text)

log_info "Target Task Definition: $TARGET_TASK_DEF"
log_info "Target Container Image: $TARGET_IMAGE"

# Database migration check
echo ""
log_warn "========================================="
log_warn "DATABASE MIGRATION CHECK"
log_warn "========================================="
log_warn "Before proceeding, verify:"
log_warn "  1. No database migrations were applied after revision $TASK_DEF_REVISION"
log_warn "  2. Database schema is compatible with revision $TASK_DEF_REVISION"
log_warn "  3. You have a database backup if needed"
log_warn "========================================="

# Environment-specific confirmation
if [ "$ENVIRONMENT" == "prod" ]; then
    log_warn "🔴 PRODUCTION ROLLBACK - Extra confirmation required"
    read -p "Type 'ROLLBACK-PROD' to confirm production rollback: " -r
    echo
    if [[ $REPLY != "ROLLBACK-PROD" ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
else
    read -p "Type 'yes' to confirm dev rollback: " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
fi

# Perform rollback
log_step "Updating ECS service to revision $TASK_DEF_REVISION..."
UPDATE_OUTPUT=$(aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE_NAME" \
    --task-definition "$TARGET_TASK_DEF" \
    --region "$AWS_REGION" \
    --output json)

log_info "ECS service update initiated"

# Wait for service to stabilize
log_step "Waiting for service to stabilize (this may take a few minutes)..."
aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" || {
    log_warn "Service did not stabilize within timeout period"
    log_warn "Please check AWS Console for deployment status"
}

# Verify rollback
log_step "Verifying rollback..."
NEW_TASK_DEF=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text)

NEW_REVISION=$(echo "$NEW_TASK_DEF" | grep -oP ':\K\d+$')

if [ "$NEW_REVISION" == "$TASK_DEF_REVISION" ]; then
    log_info "========================================="
    log_info "✅ ROLLBACK SUCCESSFUL"
    log_info "========================================="
    log_info "Service rolled back to revision: $TASK_DEF_REVISION"
    log_info "Task Definition: $NEW_TASK_DEF"
    log_info "Container Image: $TARGET_IMAGE"
else
    log_error "========================================="
    log_error "❌ ROLLBACK VERIFICATION FAILED"
    log_error "========================================="
    log_error "Expected revision: $TASK_DEF_REVISION"
    log_error "Current revision: $NEW_REVISION"
    log_error "Please check AWS Console"
    exit 1
fi

# Show running tasks
log_step "Checking running tasks..."
RUNNING_TASKS=$(aws ecs list-tasks \
    --cluster "$CLUSTER_NAME" \
    --service-name "$SERVICE_NAME" \
    --desired-status RUNNING \
    --region "$AWS_REGION" \
    --query 'taskArns[*]' \
    --output text)

TASK_COUNT=$(echo "$RUNNING_TASKS" | wc -w)
log_info "Running tasks: $TASK_COUNT"

log_info "========================================="
log_warn "NEXT STEPS:"
log_warn "1. Monitor CloudWatch logs: /aws/ecs/$TASK_FAMILY"
log_warn "2. Check application health endpoints"
log_warn "3. Review ECS service events in AWS Console"
log_warn "4. Monitor for 15-30 minutes"
log_info "========================================="

exit 0
