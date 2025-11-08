#!/bin/bash
# Quick setup script - assumes repositories are already created on GitHub

set -e

GITHUB_ORG="Softbank-mango"
BASE_DIR="/Users/jaeseokhan/Desktop/Work/softbank/test-repos"

echo "=================================================="
echo "  Deplight Platform - Quick Push Script"
echo "=================================================="
echo ""
echo "⚠️  Make sure you have already created these repositories on GitHub:"
echo "   - ${GITHUB_ORG}/fastapi-deploy-test"
echo "   - ${GITHUB_ORG}/streamlit-calculator-deploy-test"
echo "   - ${GITHUB_ORG}/express-todo-deploy-test"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# Function to setup and push a repository
setup_and_push() {
    local REPO_NAME=$1
    local REPO_DIR="${BASE_DIR}/${REPO_NAME}"

    echo "📦 Processing: ${REPO_NAME}"

    if [ ! -d "${REPO_DIR}" ]; then
        echo "   ❌ Directory not found: ${REPO_DIR}"
        return 1
    fi

    cd "${REPO_DIR}"

    # Initialize git if needed
    if [ ! -d ".git" ]; then
        echo "   Initializing git..."
        git init
        git add .
        git commit -m "Initial commit: Add ${REPO_NAME} application

🚀 Deployed with Deplight Platform

Features:
- Zero-configuration deployment
- AI-powered infrastructure generation
- Fast and reliable deployments"
        git branch -M main
    fi

    # Add remote if needed
    if ! git remote | grep -q "origin"; then
        echo "   Adding remote..."
        git remote add origin "https://github.com/${GITHUB_ORG}/${REPO_NAME}.git"
    fi

    # Push
    echo "   Pushing to GitHub..."
    if git push -u origin main 2>&1; then
        echo "   ✅ Successfully pushed: ${REPO_NAME}"
        echo ""
        return 0
    else
        echo "   ⚠️  Failed to push. You may need to:"
        echo "      1. Create the repository on GitHub first"
        echo "      2. Authenticate with GitHub (gh auth login)"
        echo "      3. Check your permissions"
        echo ""
        return 1
    fi
}

# Process each repository
SUCCESS_COUNT=0
TOTAL_COUNT=3

setup_and_push "fastapi-deploy-test" && ((SUCCESS_COUNT++)) || true
setup_and_push "streamlit-calculator-deploy-test" && ((SUCCESS_COUNT++)) || true
setup_and_push "express-todo-deploy-test" && ((SUCCESS_COUNT++)) || true

echo "=================================================="
echo "  Summary: ${SUCCESS_COUNT}/${TOTAL_COUNT} repositories pushed"
echo "=================================================="
echo ""

if [ ${SUCCESS_COUNT} -eq ${TOTAL_COUNT} ]; then
    echo "✅ All repositories pushed successfully!"
    echo ""
    echo "Repository URLs:"
    echo "  https://github.com/${GITHUB_ORG}/fastapi-deploy-test"
    echo "  https://github.com/${GITHUB_ORG}/streamlit-calculator-deploy-test"
    echo "  https://github.com/${GITHUB_ORG}/express-todo-deploy-test"
    echo ""
    echo "Next steps:"
    echo "1. Visit https://github.com/Softbank-mango/deplight-platform"
    echo "2. Go to Actions tab"
    echo "3. Run 'Deploy Application' workflow"
    echo "4. Enter one of the repository URLs above"
else
    echo "⚠️  Some repositories failed to push (${SUCCESS_COUNT}/${TOTAL_COUNT})"
    echo ""
    echo "To create repositories manually:"
    echo "1. Visit https://github.com/organizations/Softbank-mango/repositories/new"
    echo "2. Create each repository with the names above"
    echo "3. Run this script again"
    echo ""
    echo "Or use GitHub CLI:"
    echo "  gh auth login"
    echo "  gh repo create ${GITHUB_ORG}/fastapi-deploy-test --public"
    echo "  gh repo create ${GITHUB_ORG}/streamlit-calculator-deploy-test --public"
    echo "  gh repo create ${GITHUB_ORG}/express-todo-deploy-test --public"
fi

echo ""
echo "For detailed instructions, see SETUP_GUIDE.md"
