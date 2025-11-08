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

# Confirmation prompt
log_warn "This will rollback the $ENVIRONMENT environment to image tag: $IMAGE_TAG"
read -p "Are you sure you want to proceed? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Rollback cancelled by user"
    exit 0
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

log_info "========================================="
log_info "Rollback completed successfully!"
log_info "Environment: $ENVIRONMENT"
log_info "Rolled back to image tag: $IMAGE_TAG"
log_info "========================================="
log_warn "Please verify the deployment status in AWS Console or CloudWatch"

# Optional: Show current state
log_info "Current deployment status:"
terraform output 2>/dev/null || log_warn "Unable to fetch outputs"

exit 0
