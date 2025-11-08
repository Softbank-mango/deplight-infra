# Deplight Platform - Test Repositories

이 디렉토리는 Deplight Platform의 배포 기능을 테스트하기 위한 3개의 샘플 애플리케이션을 포함합니다.

## 📦 포함된 테스트 레포지토리

### 1. fastapi-deploy-test
**간단한 FastAPI 애플리케이션**

- **언어**: Python
- **프레임워크**: FastAPI + Uvicorn
- **포트**: 8000
- **엔드포인트**:
  - `GET /` - 루트 엔드포인트
  - `GET /health` - 헬스 체크
  - `GET /api/status` - API 상태
  - `GET /api/info` - 애플리케이션 정보

**특징**:
- 경량 REST API
- 자동 문서 생성 (Swagger UI)
- 빠른 시작 시간

### 2. streamlit-calculator-deploy-test
**Streamlit 과학 계산기 앱**

- **언어**: Python
- **프레임워크**: Streamlit
- **포트**: 8501 (기본값)
- **기능**:
  - 기본 산술 연산 (덧셈, 뺄셈, 곱셈, 나눗셈)
  - 과학 함수 (제곱근, 삼각함수, 로그)
  - 빠른 계산 (백분율, 원 면적, 팩토리얼)

**특징**:
- 인터랙티브 UI
- 다크 테마 디자인
- Glassmorphism 스타일

### 3. express-todo-deploy-test
**Express.js Todo 애플리케이션**

- **언어**: Node.js
- **프레임워크**: Express.js
- **포트**: 3000
- **API 엔드포인트**:
  - `GET /api/todos` - 모든 할일 조회
  - `POST /api/todos` - 할일 생성
  - `PUT /api/todos/:id` - 할일 수정
  - `DELETE /api/todos/:id` - 할일 삭제
  - `DELETE /api/todos/completed/clear` - 완료된 할일 삭제

**특징**:
- RESTful API 설계
- 풀스택 애플리케이션 (Frontend + Backend)
- 인메모리 데이터 저장
- 모던 UI 디자인

## 🚀 빠른 시작

### 1단계: GitHub 레포지토리 생성

```bash
# GitHub CLI 로그인 (아직 안했다면)
gh auth login

# 레포지토리 생성 스크립트 실행
./setup_repos.sh
```

### 2단계: 코드 푸시

```bash
# 모든 레포지토리를 한번에 푸시
./push_all.sh
```

또는 개별적으로:

```bash
# fastapi-deploy-test
cd fastapi-deploy-test
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/Softbank-mango/fastapi-deploy-test.git
git push -u origin main

# streamlit-calculator-deploy-test
cd ../streamlit-calculator-deploy-test
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/Softbank-mango/streamlit-calculator-deploy-test.git
git push -u origin main

# express-todo-deploy-test
cd ../express-todo-deploy-test
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/Softbank-mango/express-todo-deploy-test.git
git push -u origin main
```

### 3단계: Deplight Platform에서 배포 테스트

1. [Deplight Platform](https://github.com/Softbank-mango/deplight-platform) 레포지토리로 이동
2. Actions 탭 클릭
3. "Deploy Application" 워크플로우 선택
4. "Run workflow" 클릭
5. 배포할 레포지토리 URL 입력:
   - `https://github.com/Softbank-mango/fastapi-deploy-test`
   - `https://github.com/Softbank-mango/streamlit-calculator-deploy-test`
   - `https://github.com/Softbank-mango/express-todo-deploy-test`

## 📋 테스트 시나리오

### 시나리오 1: FastAPI 배포 테스트
**목적**: 간단한 Python REST API 배포 검증

1. `fastapi-deploy-test` 레포지토리 배포
2. AI Analyzer가 Python + FastAPI 감지 확인
3. Dockerfile 자동 생성 확인
4. ECS 배포 성공 확인
5. 헬스 체크 엔드포인트 테스트: `curl https://<alb-dns>/health`

**예상 결과**:
- 언어: Python 3.11
- 프레임워크: FastAPI
- 컨테이너: 256 CPU / 512 MB (simple complexity)
- 배포 시간: 2-3분

### 시나리오 2: Streamlit 배포 테스트
**목적**: 인터랙티브 Python 앱 배포 검증

1. `streamlit-calculator-deploy-test` 레포지토리 배포
2. AI Analyzer가 Streamlit 앱 감지 확인
3. 포트 8501 자동 감지 확인
4. 브라우저에서 UI 접근: `https://<alb-dns>`

**예상 결과**:
- 언어: Python 3.11
- 프레임워크: Streamlit
- 컨테이너: 512 CPU / 1024 MB (moderate complexity)
- UI: 계산기 인터페이스 정상 작동

### 시나리오 3: Express.js 배포 테스트
**목적**: Node.js 풀스택 앱 배포 검증

1. `express-todo-deploy-test` 레포지토리 배포
2. AI Analyzer가 Node.js + Express 감지 확인
3. npm install 자동 실행 확인
4. API + 프론트엔드 모두 작동 확인

**예상 결과**:
- 언어: Node.js 18+
- 프레임워크: Express.js
- 컨테이너: 512 CPU / 1024 MB (moderate complexity)
- API 엔드포인트 정상 작동
- 웹 UI 정상 작동

## 🔍 검증 포인트

각 배포 후 다음 사항들을 확인하세요:

### ✅ AI Analysis
- [ ] 언어/프레임워크 정확히 감지
- [ ] 복잡도(complexity) 올바르게 판단
- [ ] 포트 번호 자동 감지
- [ ] 캐시 적용 (두 번째 배포부터)

### ✅ Infrastructure
- [ ] Dockerfile 자동 생성
- [ ] Task Definition 자동 생성
- [ ] CPU/Memory 적절히 할당
- [ ] 환경 변수 설정

### ✅ Deployment
- [ ] 배포 시간 2-3분 이내
- [ ] Circuit Breaker 작동
- [ ] 헬스 체크 통과
- [ ] ALB DNS 접근 가능

### ✅ Application
- [ ] 애플리케이션 정상 작동
- [ ] 모든 엔드포인트 응답
- [ ] 로그 CloudWatch에 수집
- [ ] 메트릭 정상 수집

## 📊 성능 벤치마크

| 레포지토리 | 첫 배포 | 재배포 (캐시) | 컨테이너 시작 | 총 시간 |
|-----------|---------|--------------|-------------|---------|
| fastapi-deploy-test | ~60s | ~0.5s | ~30s | ~2분 |
| streamlit-calculator | ~60s | ~0.5s | ~40s | ~2.5분 |
| express-todo | ~60s | ~0.5s | ~35s | ~2.3분 |

## 🛠 로컬 개발

각 레포지토리는 로컬에서도 실행 가능합니다:

```bash
# FastAPI
cd fastapi-deploy-test
pip install -r requirements.txt
python main.py

# Streamlit
cd streamlit-calculator-deploy-test
pip install -r requirements.txt
streamlit run app.py

# Express.js
cd express-todo-deploy-test
npm install
npm start
```

## 📁 디렉토리 구조

```
test-repos/
├── README.md                           # 이 파일
├── setup_repos.sh                      # GitHub 레포지토리 생성 스크립트
├── push_all.sh                         # 모든 레포지토리 푸시 스크립트
│
├── fastapi-deploy-test/
│   ├── main.py                         # FastAPI 애플리케이션
│   ├── requirements.txt                # Python 의존성
│   └── README.md                       # 프로젝트 문서
│
├── streamlit-calculator-deploy-test/
│   ├── app.py                          # Streamlit 애플리케이션
│   ├── requirements.txt                # Python 의존성
│   └── README.md                       # 프로젝트 문서
│
└── express-todo-deploy-test/
    ├── server.js                       # Express 서버
    ├── package.json                    # Node.js 의존성
    ├── public/
    │   └── index.html                  # 프론트엔드 UI
    └── README.md                       # 프로젝트 문서
```

## 🎯 다음 단계

1. 모든 레포지토리를 GitHub에 푸시
2. 각 레포지토리를 Deplight Platform으로 배포
3. 배포 결과 확인 및 검증
4. 성능 메트릭 수집
5. 이슈 발견 시 개선 사항 문서화

## 📝 참고사항

- 모든 애플리케이션은 헬스 체크 엔드포인트를 포함합니다
- Deplight Platform의 AI Analyzer가 자동으로 프레임워크를 감지합니다
- 각 애플리케이션은 production-ready 설정을 포함합니다
- 모든 코드는 베스트 프랙티스를 따릅니다

## 🔗 관련 링크

- [Deplight Platform](https://github.com/Softbank-mango/deplight-platform)
- [배포 워크플로우](.github/workflows/deploy.yml)
- [AI Analyzer](mango/lambda/ai_code_analyzer/)

---

**Made with ❤️ for Deplight Platform**
