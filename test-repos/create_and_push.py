#!/usr/bin/env python3
"""
GitHub 레포지토리 생성 및 푸시 스크립트
Personal Access Token이 필요합니다.
"""

import os
import subprocess
import sys
from pathlib import Path

GITHUB_ORG = "Softbank-mango"
REPOS = [
    {
        "name": "fastapi-deploy-test",
        "description": "Simple FastAPI application for testing Deplight deployment",
    },
    {
        "name": "streamlit-calculator-deploy-test",
        "description": "Scientific calculator built with Streamlit",
    },
    {
        "name": "express-todo-deploy-test",
        "description": "Full-stack Todo app built with Express.js",
    },
]

def run_command(cmd, cwd=None, check=True):
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return None, e.returncode

def check_gh_auth():
    """GitHub CLI 인증 확인"""
    _, returncode = run_command("gh auth status", check=False)
    return returncode == 0

def init_and_push_repo(repo_name, base_dir):
    """Git 레포지토리 초기화 및 푸시"""
    repo_dir = base_dir / repo_name

    if not repo_dir.exists():
        print(f"❌ Directory not found: {repo_dir}")
        return False

    print(f"\n📦 Processing: {repo_name}")
    print(f"   Directory: {repo_dir}")

    # Git 초기화
    if not (repo_dir / ".git").exists():
        print("   Initializing git repository...")
        run_command("git init", cwd=repo_dir)
        run_command("git add .", cwd=repo_dir)

        commit_msg = f"""Initial commit: Add {repo_name} application

🚀 Deployed with Deplight Platform

Features:
- Zero-configuration deployment
- AI-powered infrastructure generation
- Fast and reliable deployments"""

        run_command(f'git commit -m "{commit_msg}"', cwd=repo_dir)
        run_command("git branch -M main", cwd=repo_dir)

        # Remote 추가
        remote_url = f"https://github.com/{GITHUB_ORG}/{repo_name}.git"
        run_command(f"git remote add origin {remote_url}", cwd=repo_dir, check=False)

    # Push (force 옵션 사용)
    print("   Pushing to GitHub...")
    output, returncode = run_command(
        "git push -u origin main --force",
        cwd=repo_dir,
        check=False
    )

    if returncode == 0:
        print(f"✅ Pushed: {GITHUB_ORG}/{repo_name}")
        return True
    else:
        print(f"⚠️  Failed to push {repo_name}")
        print(f"    You may need to create the repository first on GitHub")
        return False

def main():
    print("=" * 60)
    print("  Deplight Platform - Test Repositories Setup")
    print("=" * 60)
    print()

    # 현재 디렉토리
    base_dir = Path(__file__).parent

    # GitHub CLI 인증 확인
    if not check_gh_auth():
        print("⚠️  GitHub CLI is not authenticated")
        print()
        print("Option 1: Authenticate GitHub CLI")
        print("  gh auth login")
        print()
        print("Option 2: Manually create repositories")
        print("  1. Go to https://github.com/organizations/Softbank-mango/repositories/new")
        print("  2. Create these repositories:")
        for repo in REPOS:
            print(f"     - {repo['name']}: {repo['description']}")
        print()
        print("Then run this script again to push the code.")
        print()

        choice = input("Do you want to continue and try pushing anyway? (y/N): ")
        if choice.lower() != 'y':
            print("\nExiting...")
            return
    else:
        print("✅ GitHub CLI is authenticated")
        print("\nCreating repositories...")
        print()

        # 레포지토리 생성
        for repo in REPOS:
            repo_name = repo["name"]
            description = repo["description"]

            # 레포지토리가 이미 존재하는지 확인
            _, returncode = run_command(
                f'gh repo view {GITHUB_ORG}/{repo_name}',
                check=False
            )

            if returncode == 0:
                print(f"⚠️  Repository already exists: {GITHUB_ORG}/{repo_name}")
            else:
                print(f"📦 Creating repository: {GITHUB_ORG}/{repo_name}")
                output, returncode = run_command(
                    f'gh repo create {GITHUB_ORG}/{repo_name} --public --description "{description}"',
                    check=False
                )

                if returncode == 0:
                    print(f"✅ Created: {GITHUB_ORG}/{repo_name}")
                else:
                    print(f"❌ Failed to create: {GITHUB_ORG}/{repo_name}")

    print()
    print("=" * 60)
    print("  Pushing repositories...")
    print("=" * 60)

    # 각 레포지토리 초기화 및 푸시
    success_count = 0
    for repo in REPOS:
        if init_and_push_repo(repo["name"], base_dir):
            success_count += 1

    print()
    print("=" * 60)
    print(f"  Completed: {success_count}/{len(REPOS)} repositories")
    print("=" * 60)
    print()

    if success_count == len(REPOS):
        print("✅ All repositories pushed successfully!")
        print()
        print("Repository URLs:")
        for repo in REPOS:
            print(f"  https://github.com/{GITHUB_ORG}/{repo['name']}")
        print()
        print("Next: Test deployment workflow")
        print("Go to: https://github.com/Softbank-mango/deplight-platform")
    else:
        print("⚠️  Some repositories failed to push")
        print()
        print("Manual steps:")
        print("1. Create repositories on GitHub if they don't exist")
        print("2. Run this script again")
        print()
        print("Or manually push each repository:")
        for repo in REPOS:
            repo_name = repo["name"]
            print(f"\ncd {repo_name}")
            print("git init")
            print("git add .")
            print('git commit -m "Initial commit"')
            print("git branch -M main")
            print(f"git remote add origin https://github.com/{GITHUB_ORG}/{repo_name}.git")
            print("git push -u origin main")

if __name__ == "__main__":
    main()
