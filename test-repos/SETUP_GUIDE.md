# 테스트 레포지토리 설정 가이드

3개의 테스트 레포지토리를 Softbank-mango 조직에 생성하고 푸시하는 방법입니다.

## 📋 생성할 레포지토리

1. **fastapi-deploy-test** - Simple FastAPI application for testing Deplight deployment
2. **streamlit-calculator-deploy-test** - Scientific calculator built with Streamlit
3. **express-todo-deploy-test** - Full-stack Todo app built with Express.js

## 🚀 방법 1: GitHub CLI 사용 (권장)

### 1단계: GitHub CLI 인증

```bash
gh auth login
```

웹 브라우저가 열리면 GitHub 계정으로 로그인하고 권한을 승인합니다.

### 2단계: 레포지토리 생성

```bash
cd /Users/jaeseokhan/Desktop/Work/softbank/test-repos

# fastapi-deploy-test
gh repo create Softbank-mango/fastapi-deploy-test \
  --public \
  --description "Simple FastAPI application for testing Deplight deployment"

# streamlit-calculator-deploy-test
gh repo create Softbank-mango/streamlit-calculator-deploy-test \
  --public \
  --description "Scientific calculator built with Streamlit"

# express-todo-deploy-test
gh repo create Softbank-mango/express-todo-deploy-test \
  --public \
  --description "Full-stack Todo app built with Express.js"
```

### 3단계: 코드 푸시

```bash
# fastapi-deploy-test
cd fastapi-deploy-test
git init
git add .
git commit -m "Initial commit: Add FastAPI application

🚀 Deployed with Deplight Platform"
git branch -M main
git remote add origin https://github.com/Softbank-mango/fastapi-deploy-test.git
git push -u origin main

# streamlit-calculator-deploy-test
cd ../streamlit-calculator-deploy-test
git init
git add .
git commit -m "Initial commit: Add Streamlit calculator

🚀 Deployed with Deplight Platform"
git branch -M main
git remote add origin https://github.com/Softbank-mango/streamlit-calculator-deploy-test.git
git push -u origin main

# express-todo-deploy-test
cd ../express-todo-deploy-test
git init
git add .
git commit -m "Initial commit: Add Express.js Todo app

🚀 Deployed with Deplight Platform"
git branch -M main
git remote add origin https://github.com/Softbank-mango/express-todo-deploy-test.git
git push -u origin main
```

## 🌐 방법 2: GitHub 웹사이트 사용

### 1단계: 레포지토리 수동 생성

각 레포지토리에 대해 다음을 반복합니다:

1. https://github.com/organizations/Softbank-mango/repositories/new 방문
2. Repository name 입력:
   - `fastapi-deploy-test`
   - `streamlit-calculator-deploy-test`
   - `express-todo-deploy-test`
3. Description 입력 (위 목록 참조)
4. Public 선택
5. "Create repository" 클릭

### 2단계: 코드 푸시

위의 "방법 1 - 3단계"와 동일하게 진행

## 🔍 확인사항

모든 레포지토리가 성공적으로 생성되고 푸시되었는지 확인:

```bash
# 레포지토리 확인
gh repo view Softbank-mango/fastapi-deploy-test
gh repo view Softbank-mango/streamlit-calculator-deploy-test
gh repo view Softbank-mango/express-todo-deploy-test
```

또는 웹 브라우저에서:
- https://github.com/Softbank-mango/fastapi-deploy-test
- https://github.com/Softbank-mango/streamlit-calculator-deploy-test
- https://github.com/Softbank-mango/express-todo-deploy-test

## 📍 생성된 레포지토리 URL

성공적으로 생성되면 다음 URL에서 접근 가능합니다:

1. https://github.com/Softbank-mango/fastapi-deploy-test
2. https://github.com/Softbank-mango/streamlit-calculator-deploy-test
3. https://github.com/Softbank-mango/express-todo-deploy-test

## 🎯 다음 단계: 배포 테스트

레포지토리가 생성되면 Deplight Platform에서 배포를 테스트할 수 있습니다:

1. https://github.com/Softbank-mango/deplight-platform 방문
2. Actions 탭 클릭
3. "Deploy Application" 워크플로우 선택
4. "Run workflow" 클릭
5. Target Repository URL 입력 (위 URL 중 하나)
6. "Run workflow" 클릭하여 배포 시작

## 🐛 트러블슈팅

### 문제: `gh` 명령어를 찾을 수 없음

**해결방법:**
```bash
# macOS
brew install gh

# 또는 방법 2 (웹사이트) 사용
```

### 문제: Permission denied (publickey)

**해결방법:**
```bash
# SSH 키 확인
ssh -T git@github.com

# SSH 키가 없으면 생성
ssh-keygen -t ed25519 -C "your_email@example.com"

# GitHub에 SSH 키 추가
# https://github.com/settings/keys
```

### 문제: remote origin already exists

**해결방법:**
```bash
git remote remove origin
git remote add origin https://github.com/Softbank-mango/<repo-name>.git
```

## 📊 예상 결과

성공적으로 완료되면:

- ✅ 3개의 public 레포지토리가 Softbank-mango 조직에 생성됨
- ✅ 각 레포지토리에 완전한 애플리케이션 코드가 푸시됨
- ✅ README.md, 소스코드, 의존성 파일이 모두 포함됨
- ✅ Deplight Platform 배포 테스트 준비 완료

---

문제가 발생하면 이 가이드를 참조하거나 GitHub 문서를 확인하세요:
- https://docs.github.com/en/get-started
- https://cli.github.com/manual/
