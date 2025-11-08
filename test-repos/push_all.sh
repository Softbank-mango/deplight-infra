#!/bin/bash
# Script to initialize and push all test repositories

set -e

GITHUB_ORG="Softbank-mango"
REPOS=(
  "fastapi-deploy-test"
  "streamlit-calculator-deploy-test"
  "express-todo-deploy-test"
)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=================================================="
echo "  Pushing all test repositories to GitHub"
echo "=================================================="
echo ""

for REPO_NAME in "${REPOS[@]}"; do
    echo "📤 Processing: ${REPO_NAME}"
    cd "${SCRIPT_DIR}/${REPO_NAME}"

    # Initialize git if not already initialized
    if [ ! -d ".git" ]; then
        echo "   Initializing git repository..."
        git init
        git add .
        git commit -m "Initial commit: Add ${REPO_NAME} application

🚀 Deployed with Deplight Platform

Features:
- Zero-configuration deployment
- AI-powered infrastructure generation
- Fast and reliable deployments"
        git branch -M main
        git remote add origin "https://github.com/${GITHUB_ORG}/${REPO_NAME}.git"
    fi

    # Push to GitHub
    echo "   Pushing to GitHub..."
    git push -u origin main --force

    echo "✅ Pushed: ${GITHUB_ORG}/${REPO_NAME}"
    echo ""
done

echo "=================================================="
echo "  All repositories pushed successfully!"
echo "=================================================="
echo ""
echo "Repository URLs:"
for REPO_NAME in "${REPOS[@]}"; do
    echo "  https://github.com/${GITHUB_ORG}/${REPO_NAME}"
done
echo ""
echo "=================================================="
echo "  Next: Test deployment workflow"
echo "=================================================="
echo ""
echo "To deploy a repository, go to:"
echo "https://github.com/Softbank-mango/deplight-platform"
echo ""
echo "And trigger the deployment workflow with the repository URL."
