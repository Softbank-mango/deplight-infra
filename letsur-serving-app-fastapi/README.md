# Letsur Serving App (FastAPI)

모델 및 애플리케이션 서빙을 위한 FastAPI 템플릿(Boilerplate)입니다.

이 템플릿은 AI 엔지니어가 복잡한 웹 개발 지식 없이도, 사내 표준에 맞는 API 서버를 쉽고 빠르게 개발하고 배포할 수 있도록 돕는 것을 목표로 합니다.

---

## 📚 문서 (Documentation)

이 프로젝트의 상세한 사용법과 아키텍처는 `docs` 폴더에 정리되어 있습니다.

*   **📄 [AI 엔지니어 시작 가이드](./docs/ai-engineers-guide.md)**
    *   `Copier`로 프로젝트를 생성하고, 코드를 작성하여 사내 플랫폼에 배포하는 전체 과정을 안내합니다. **AI 엔지니어라면 이 문서를 가장 먼저 읽어보세요.**

*   **🏛️ [아키텍처 설명](./docs/architecture.md)**
    *   개발자와 운영자를 위해, 이 템플릿이 사내 배포 플랫폼과 어떻게 연동되어 동작하는지에 대한 전체 파이프라인과 아키텍처를 설명합니다.

*   **⌨️ [CLI 스크립트 가이드](./docs/cli-scripts.md)**
    *   환경변수 관리, `openapi.json` 생성 등 개발 편의성을 돕는 내장 스크립트들의 사용법을 안내합니다.

*   **⚠️ [제약사항 및 주요 유의사항](./docs/constraints-and-notes.md)**
    *   템플릿 사용 시 반드시 알아야 할 규칙과 주요 정책들을 설명합니다. 개발 전 꼭 읽어보세요.

---

## 🚀 빠른 시작 (Quickstart)

### 사전 준비

`copier`를 프로젝트 의존성과 분리하여 설치하는 것을 권장합니다.

```bash
# pipx 사용 (권장)
pipx install copier

# uv tool 사용
uv tool install copier
```

### 프로젝트 생성

아래 명령어를 실행하여 이 템플릿으로부터 새로운 프로젝트를 생성합니다.

```bash
# <템플릿_GIT_URL> 부분은 실제 템플릿의 Git 주소로 변경해주세요.
# <내_프로젝트_이름> 에는 생성할 프로젝트의 디렉토리 이름을 적어주세요.
copier copy <템플릿_GIT_URL> <내_프로젝트_이름> --trust
```

### 템플릿 업데이트

기존에 생성한 프로젝트에 최신 템플릿의 변경사항을 적용하고 싶을 때 사용합니다.

```bash
copier update --trust
```
