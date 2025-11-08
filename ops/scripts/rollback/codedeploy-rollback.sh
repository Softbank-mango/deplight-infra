#!/bin/bash
#
# CodeDeploy Rollback Script
#
# This script triggers a rollback for a CodeDeploy deployment.
# It can either stop the current deployment (triggering automatic rollback)
# or manually rollback to a previous revision.
#
# Usage: ./codedeploy-rollback.sh <environment> [deployment-id]
# Example: ./codedeploy-rollback.sh prod
# Example: ./codedeploy-rollback.sh prod d-ABCDEFGH
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
if [ $# -lt 1 ]; then
    log_error "Invalid number of arguments"
    echo "Usage: $0 <environment> [deployment-id]"
    echo "Example: $0 prod"
    echo "Example: $0 prod d-ABCDEFGH"
    exit 1
fi

ENVIRONMENT=$1
DEPLOYMENT_ID=${2:-}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Environment must be either 'dev' or 'prod'"
    exit 1
fi

# Set CodeDeploy application and deployment group names
# Adjust these based on your actual naming convention
APP_NAME="deplight-${ENVIRONMENT}-app"
DEPLOYMENT_GROUP="${ENVIRONMENT}-deployment-group"

log_info "========================================="
log_info "CodeDeploy Rollback Process"
log_info "========================================="
log_info "Environment: $ENVIRONMENT"
log_info "Application: $APP_NAME"
log_info "Deployment Group: $DEPLOYMENT_GROUP"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# If no deployment ID is provided, find the latest deployment
if [ -z "$DEPLOYMENT_ID" ]; then
    log_info "Finding latest deployment..."

    DEPLOYMENT_ID=$(aws deploy list-deployments \
        --application-name "$APP_NAME" \
        --deployment-group-name "$DEPLOYMENT_GROUP" \
        --query 'deployments[0]' \
        --output text 2>/dev/null || echo "")

    if [ -z "$DEPLOYMENT_ID" ] || [ "$DEPLOYMENT_ID" == "None" ]; then
        log_error "No deployments found for $APP_NAME / $DEPLOYMENT_GROUP"
        exit 1
    fi

    log_info "Latest deployment ID: $DEPLOYMENT_ID"
fi

# Get deployment info
log_info "Fetching deployment information..."
DEPLOYMENT_INFO=$(aws deploy get-deployment \
    --deployment-id "$DEPLOYMENT_ID" \
    --output json)

DEPLOYMENT_STATUS=$(echo "$DEPLOYMENT_INFO" | grep -o '"status": "[^"]*"' | head -1 | cut -d'"' -f4)

log_info "Current deployment status: $DEPLOYMENT_STATUS"
log_info "Deployment ID: $DEPLOYMENT_ID"

# Determine rollback action based on status
case "$DEPLOYMENT_STATUS" in
    "InProgress"|"Queued"|"Created")
        log_warn "Deployment is currently $DEPLOYMENT_STATUS"
        log_info "Stopping deployment will trigger automatic rollback..."

        read -p "Do you want to stop the current deployment? (yes/no): " -r
        echo
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi

        log_info "Stopping deployment..."
        aws deploy stop-deployment \
            --deployment-id "$DEPLOYMENT_ID" \
            --auto-rollback-enabled

        log_info "Deployment stopped. Automatic rollback initiated."
        ;;

    "Failed"|"Stopped")
        log_warn "Deployment already $DEPLOYMENT_STATUS"
        log_info "Checking if automatic rollback occurred..."

        # List recent deployments to find rollback
        RECENT_DEPLOYMENTS=$(aws deploy list-deployments \
            --application-name "$APP_NAME" \
            --deployment-group-name "$DEPLOYMENT_GROUP" \
            --max-items 5 \
            --output json)

        echo "$RECENT_DEPLOYMENTS"
        log_info "Check the deployments above for any automatic rollback"
        ;;

    "Succeeded")
        log_warn "Deployment has already succeeded"
        log_info "To rollback a successful deployment, you need to deploy a previous revision"
        log_info "Use the Terraform rollback script instead: ./rollback.sh $ENVIRONMENT <previous-image-tag>"
        exit 1
        ;;

    *)
        log_error "Unknown deployment status: $DEPLOYMENT_STATUS"
        exit 1
        ;;
esac

log_info "========================================="
log_info "Rollback process initiated"
log_info "========================================="
log_warn "Monitor the deployment status in AWS Console:"
log_warn "https://console.aws.amazon.com/codesuite/codedeploy/deployments/$DEPLOYMENT_ID"

exit 0
