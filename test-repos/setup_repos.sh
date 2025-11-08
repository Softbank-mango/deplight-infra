#!/bin/bash
# Setup script for creating test repositories on GitHub

set -e

GITHUB_ORG="Softbank-mango"
REPOS=(
  "fastapi-deploy-test:Simple FastAPI application for testing Deplight deployment"
  "streamlit-calculator-deploy-test:Scientific calculator built with Streamlit"
  "express-todo-deploy-test:Full-stack Todo app built with Express.js"
)

echo "=================================================="
echo "  Deplight Platform - Test Repositories Setup"
echo "=================================================="
echo ""

# Check if gh CLI is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI is not authenticated"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"
echo ""

# Create repositories
for REPO_INFO in "${REPOS[@]}"; do
    IFS=':' read -r REPO_NAME DESCRIPTION <<< "$REPO_INFO"

    echo "📦 Creating repository: ${GITHUB_ORG}/${REPO_NAME}"

    # Check if repository already exists
    if gh repo view "${GITHUB_ORG}/${REPO_NAME}" &> /dev/null; then
        echo "⚠️  Repository already exists: ${GITHUB_ORG}/${REPO_NAME}"
        read -p "Do you want to delete and recreate it? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🗑️  Deleting existing repository..."
            gh repo delete "${GITHUB_ORG}/${REPO_NAME}" --yes
        else
            echo "⏭️  Skipping ${REPO_NAME}"
            continue
        fi
    fi

    # Create repository
    gh repo create "${GITHUB_ORG}/${REPO_NAME}" \
        --public \
        --description "${DESCRIPTION}" \
        --clone=false

    echo "✅ Created: ${GITHUB_ORG}/${REPO_NAME}"
    echo ""
done

echo "=================================================="
echo "  Repositories created successfully!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""

for REPO_INFO in "${REPOS[@]}"; do
    IFS=':' read -r REPO_NAME _ <<< "$REPO_INFO"

    echo "📁 ${REPO_NAME}:"
    echo "   cd ${REPO_NAME}"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m \"Initial commit: Add ${REPO_NAME} application\""
    echo "   git branch -M main"
    echo "   git remote add origin https://github.com/${GITHUB_ORG}/${REPO_NAME}.git"
    echo "   git push -u origin main"
    echo ""
done

echo "=================================================="
echo "  Or use the push_all.sh script to push all repos"
echo "=================================================="
