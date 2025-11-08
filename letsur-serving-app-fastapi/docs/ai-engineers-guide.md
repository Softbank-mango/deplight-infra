# AI 모델 API 서버 배포 가이드 (for AI Engineers)

안녕하세요! 이 문서는 AI 엔지니어 여러분이 개발한 머신러닝 모델을 복잡한 웹 개발 지식 없이, 쉽고 빠르게 API 서버로 만들고 사내 플랫폼에 배포할 수 있도록 돕기 위한 가이드입니다.

### ✅ 이런 경우에 사용하면 좋아요

이 템플릿은 **서드파티(외부) API를 호출**하거나, **GPU 없이 간단한 비즈니스 로직을 처리**하는 API를 만들 때 가장 효과적입니다.

반면, 무거운 딥러닝 모델 서빙과 같이 **상당한 GPU 자원을 필요로 하는 작업**에는 현재 이 템플릿 사용을 지양하고 있으니, 이 점 참고 부탁드립니다.


### ⭐ 템플릿의 장점

*   반복적인 웹 서버 설정, 로깅, 환경 변수 관리 등을 신경 쓸 필요가 없습니다.
*   오직 **모델의 입/출력 정의**와 **추론 코드 작성**에만 집중할 수 있습니다.
*   GitHub Actions를 통해 **Git Flow에 익숙한 방식으로 손쉽게 Docker 이미지를 빌드하고 릴리즈**할 수 있습니다.
*   사내 플랫폼 표준에 맞는 Docker 이미지를 생성하여 `lamp-cli`로 배포할 수 있습니다.

---

## 🚀 배포 전체 흐름

AI 엔지니어의 일반적인 개발 및 배포 워크플로우는 다음과 같습니다.

1.  **[최초 1회] `Copier`로 프로젝트 생성**: `Copier`를 사용하여 로컬에 FastAPI 앱 프로젝트를 생성합니다.
2.  **[최초 1회] GitHub Repository 생성 및 연동**: 생성된 프로젝트를 GitHub에 Push하여 CI/CD 파이프라인을 준비합니다.
3.  **[반복 작업] 코드 작성 및 로컬 테스트**: `src/` 디렉토리의 파일을 수정하여 비즈니스 로직을 개발하고, 로컬에서 Docker를 통해 테스트합니다.
4.  **[배포 시] GitHub Release 생성**: 코드를 GitHub에 Push하고 **Release를 생성**하여, GitHub Actions가 자동으로 **Docker 이미지를 빌드하고 ECR에 Push**하도록 합니다.
5.  **[배포 시] `LAMP CLI`로 플랫폼에 등록**: `LAMP CLI`를 사용하여 **MLflow `Run`을 생성**하고, 빌드된 **Docker 이미지 정보(`Serving Model Spec`)**와 **배포 설정(`Serving Endpoint Spec`)**을 업로드한 뒤, 최종적으로 `StaiX` 프로젝트에 **등록(`Register`)**합니다.
6.  **[배포 시] `StaiX` UI에서 배포**: `StaiX` 플랫폼에 등록된 새로운 `Model Version`을 확인하고, UI에서 배포 버튼을 클릭하여 실제 서비스 환경에 배포합니다.

이 문서는 5번 단계(`LAMP CLI`로 등록)까지를 상세히 다룹니다.

---

### Step 1. `Copier`로 내 프로젝트 생성하기

(내용 동일)

---

### Step 2. GitHub Repository 생성 및 연동

(내용 동일)

---

### Step 3. 코드 작성 및 로컬 테스트

(내용 동일)

---

### Step 4. GitHub Actions로 Docker 이미지 빌드 및 릴리즈

로컬 테스트가 완료된 코드를 GitHub에 Push하고, Release를 생성하여 배포할 Docker 이미지를 만듭니다.

**1. 코드 변경사항 Push:**
   - 수정한 코드를 commit하고 `main` 브랜치에 push합니다.
   ```bash
   git add src/dataclasses.py src/routers/main.py
   git commit -m "feat: Implement sentiment analysis logic"
   git push origin main
   ```

**2. GitHub Release 생성:**
   - **배포를 원할 때**, GitHub Repository 페이지에서 **"Release"** 메뉴로 이동합니다.
   - **"Draft a new release"** 버튼을 클릭합니다.
   - **버전 태그** (e.g., `v0.1.0`)를 입력하고 릴리즈 노트를 작성한 뒤, **"Publish release"** 버튼을 누릅니다.
   - 릴리즈가 생성되면, GitHub Actions가 실행되어 최종 Docker 이미지를 빌드하고 **사내 컨테이너 레지스트리(ECR)에 Push**합니다.

이제 ECR에 Push된 Docker 이미지를 `LAMP CLI`를 통해 사내 플랫폼에 등록할 준비가 되었습니다.

### Step 5. `LAMP CLI`로 플랫폼에 등록 및 배포

마지막 단계는 ECR에 Push된 Docker 이미지를 `LAMP CLI`를 사용하여 `StaiX` 플랫폼에 등록하고, 최종적으로 배포하는 것입니다.

이 복잡한 과정을 쉽게 실행할 수 있도록, `LAMP CLI`는 **파이프라인 스크립트를 자동 생성하는 기능**을 제공합니다.

#### 5.1. 파이프라인 스크립트 생성

먼저, 아래 명령어를 실행하여 `cli_pipeline.sh` 파일을 생성합니다.

```bash
# -p stg: stg 환경을 대상으로 스크립트 생성 (dev, prd 등으로 변경 가능)
lamp-cli -p stg inhouse generate-pipeline-script
```
이 명령은 현재 프로젝트 구조에 맞는 등록/배포 절차를 담은 `cli_pipeline.sh` 셸 스크립트 파일을 생성합니다.

#### 5.2. `cli_pipeline.sh` 스크립트 수정

생성된 `cli_pipeline.sh` 파일을 열고, 스크립트 상단의 지시에 따라 **배포에 필요한 정보들을 채워 넣습니다.**

```bash
# cli_pipeline.sh 일부 예시

# ... (상략) ...

create_dummy_run() {
  lamp-cli -p $PROFILE inhouse create-dummy-run \
  -r "my-run-v1.0" \
  -p "my-ml-project" \
}

# ... (중략) ...

register() {
  lamp-cli -p $PROFILE register \
  -r $RUN_ID \
  -p "STAIX_PROJECT_ID_1234" \
}

# ... (하략) ...
```

#### 5.3. 스크립트 실행

스크립트 수정이 완료되면, 아래와 같이 실행하여 모든 등록 절차를 한번에 진행합니다.

```bash
./cli_pipeline.sh
```

스크립트는 내부적으로 다음과 같은 `lamp-cli` 명령어들을 순차적으로 실행합니다.

1.  **`create-dummy-run`**: MLflow에 이번 배포를 위한 `Run`을 생성합니다.
2.  **`upload-serving-model-spec`**: **Serving Model Spec**을 업로드합니다. 이 Spec은 다음 파일들로 구성됩니다.
    *   `docker-compose.yaml`
    *   `.env`
3.  **`upload-serving-endpoint-spec`**: **Serving Endpoint Spec**을 업로드합니다. 이 Spec은 다음 파일들로 구성됩니다.
    *   `.deployment/metadata.{env}.yaml`
    *   `.deployment/values.{env}.yaml`
    *   `.deployment/.env.apiServer.{env}`
    *   (선택) `.deployment/openapi.json`
4.  **`register`**: 모든 정보가 업로드된 `Run`을 `StaiX` Project에 새로운 `Model Version`으로 등록합니다.

`register` 명령이 성공적으로 실행되면, `StaiX` UI의 해당 프로젝트에서 새로운 모델 버전을 확인하고 UI를 통해 최종 배포를 진행할 수 있습니다.



### Step 1. `Copier`로 내 프로젝트 생성하기

먼저, 이 템플릿을 복제하여 여러분의 새로운 모델 서버 프로젝트를 생성합니다.

**1. 사전 준비:**
`copier`가 설치되어 있어야 합니다. 설치되어 있지 않다면 터미널에서 아래 명령어를 실행해주세요.
```bash
pip install copier
# pipx install copier
# uv tool install copier
```

**2. 프로젝트 생성:**
터미널에서 아래 명령어를 실행하여 템플릿으로부터 새 프로젝트를 복사합니다.
```bash
# <템플릿_GIT_URL> 부분은 실제 템플릿의 Git 주소로 변경해주세요.
# <내_프로젝트_이름> 에는 생성할 프로젝트의 디렉토리 이름을 적어주세요.
copier copy <템플릿_GIT_URL> <내_프로젝트_이름>
```
명령어를 실행하면 프로젝트 이름 등 몇 가지 질문이 표시됩니다. 간단히 답변을 입력하면 여러분의 모델 서버를 위한 기본 파일들이 모두 자동으로 생성됩니다.

### Step 2. GitHub Repository 생성 및 연동

**1. GitHub Repository 생성:**
   - GitHub에 접속하여 새로운 Repository를 생성합니다. (Private으로 생성하는 것을 권장합니다.)

**2. 생성된 프로젝트와 Git 연동:**
   - 터미널에서, Step 1에서 생성된 프로젝트 폴더로 이동합니다.
   - 아래 명령어를 순서대로 실행하여 로컬 프로젝트를 방금 만든 GitHub Repository와 연동하고 Push 합니다.
   ```bash
   # Git 초기화 (이미 .git 폴더가 있다면 생략)
   git init

   # 모든 파일을 Git에 추가
   git add .
   git commit -m "Initial commit from fastapi-serving-template"

   # 원격 저장소 연결
   # <GITHUB_USERNAME>과 <REPOSITORY_NAME>을 실제 정보로 변경해주세요.
   git remote add origin https://github.com/<GITHUB_USERNAME>/<REPOSITORY_NAME>.git

   # 기본 브랜치 이름을 main으로 설정
   git branch -M main

   # 원격 저장소로 코드 Push
   git push -u origin main
   ```

### Step 3. 코드 작성 및 로컬 테스트

이제 비즈니스 로직을 작성하고 로컬에서 테스트하는 반복 작업 단계입니다. **주로 2개의 파일만 수정**하게 됩니다.

*   `src/dataclasses.py`: 모델이 받을 **입력(Input)**과 반환할 **출력(Output)**의 형식을 정의합니다.
*   `src/routers/main.py`: 실제 모델을 사용하여 **추론(Inference)**을 수행하는 코드를 작성합니다.

#### 3.1. 모델 입/출력 정의 (`src/dataclasses.py`)

`src/dataclasses.py` 파일을 열고, `ModelInput`과 `ModelOutput` 클래스를 여러분의 모델에 맞게 수정합니다.

**예시:** 텍스트를 입력받아 긍정/부정 라벨과 신뢰도 점수를 반환하는 모델
```python
# src/dataclasses.py
from pydantic import BaseModel, Field

class ModelInput(BaseModel):
    text: str = Field(description="분석할 문장입니다.", example="이 영화 정말 재미있어요!")

class ModelOutput(BaseModel):
    label: str = Field(description="분석 결과 라벨입니다.", example="긍정")
    score: float = Field(description="결과에 대한 신뢰도 점수입니다.", example=0.98)
```

#### 3.2. 추론 로직 작성 (`src/routers/main.py`)

`src/routers/main.py` 파일을 열고, `invocations` 함수 안에 실제 모델 추론 코드를 작성합니다.

**예시:**
```python
# src/routers/main.py
import os
from fastapi import APIRouter
# ... (다른 import 구문들)
from src.dataclasses import ModelInput, ModelOutput

# --- 모델 로딩 (애플리케이션 시작 시 1회 실행) ---
# MODEL_PATH = os.getenv("MODEL_PATH")
# model = load_model(MODEL_PATH)
# -----------------------------------------

router = APIRouter()

@router.post("/invocations")
@lamp_invocation()
def invocations(model_input: ModelInput, jwt_header: LetsurJwtHeaders) -> ModelOutput:
    # --- 추론 로직 ---
    text_to_analyze = model_input.text
    # label, score = model.predict(text_to_analyze)
    label, score = "긍정", 0.98 # 임시 결과
    return ModelOutput(label=label, score=score)
```

#### 3.3. 로컬에서 테스트하기

코드가 잘 작동하는지 로컬 환경에서 테스트합니다.
```bash
# Docker 이미지를 빌드하고 컨테이너를 실행합니다.
docker compose -f docker-compose.local.yaml up --build
```
서버가 실행되면, 웹 브라우저에서 `http://localhost:8000/docs` 로 접속하여 API 문서를 확인하고 직접 테스트해볼 수 있습니다.

### Step 4. GitHub Actions로 Docker 이미지 빌드 및 릴리즈

로컬 테스트가 완료된 코드를 GitHub에 Push하고, Release를 생성하여 배포할 Docker 이미지를 만듭니다.

**1. 코드 변경사항 Push:**
   - 수정한 코드를 commit하고 `main` 브랜치에 push합니다.
   ```bash
   git add src/dataclasses.py src/routers/main.py
   git commit -m "feat: Implement sentiment analysis logic"
   git push origin main
   ```
   - `main` 브랜치에 코드가 Push되면, GitHub Actions가 자동으로 실행되어 코드를 테스트하고 Docker 이미지를 빌드하여 푸시할 준비를 합니다. (이때 이미지가 바로 공개되지는 않습니다.)

**2. GitHub Release 생성:**
   - **배포를 원할 때**, GitHub Repository 페이지에서 **"Release"** 메뉴로 이동합니다.
   - **"Draft a new release"** 버튼을 클릭합니다.
   - **버전 태그** (e.g., `v0.1.0`)를 입력하고 릴리즈 노트를 작성한 뒤, **"Publish release"** 버튼을 누릅니다.
   - 릴리즈가 생성되면, GitHub Actions가 다시 한번 실행되어 최종 Docker 이미지를 빌드하고 **GitHub Container Registry(GHCR)에 공개적으로 Push**합니다.

이제 GHCR에 Push된 `ghcr.io/<GITHUB_USERNAME>/<REPOSITORY_NAME>:v0.1.0` 와 같은 Docker 이미지를 `lamp-cli`를 통해 사내 플랫폼에 배포할 수 있습니다.

### Step 5. `lamp-cli`로 사내 플랫폼에 배포

마지막 단계는 GitHub Actions를 통해 빌드되고 GHCR에 Push된 Docker 이미지를 `lamp-cli`를 사용하여 사내 플랫폼에 배포하는 것입니다.

`lamp-cli`는 배포에 필요한 정보(Docker 이미지 주소, 환경 변수, 모델 경로 등)를 담은 `ServingEndpoint` 명세(Spec)를 사내 플랫폼에 업로드하고, 이를 기반으로 실제 서빙 환경을 구성합니다.

**자세한 `lamp-cli` 설치 및 사용법은 공식 GitHub Repository를 참고해주세요.**
> **GitHub:** [https://github.com/letsur-dev/lamp_admin_cli](https://github.com/letsur-dev/lamp_admin_cli)

**배포 예시:**
```bash
# ServingEndpoint Spec 파일 템플릿 생성
lamp-cli -p stg inhouse generate-endpoint-spec
# Spec 파일 수정 이후 업로드용 스크립트 생성
lamp-cli -p stg inhouse generate-pipeline-script
# 스크립트 수정 이후 스크립트 실행
./cli_pipeline.sh
```

---

## 💡 `uv` 사용자를 위한 안내

`uv`는 매우 빠른 Python 패키지 설치 및 관리 도구입니다. `uv`를 사용하여 개발 환경을 관리하는 경우, 다음 두 가지 사항을 권장합니다.

### 1. `copier`는 격리된 환경에 설치하기

프로젝트의 의존성과 `copier`의 의존성이 충돌하는 것을 방지하기 위해, `pipx`나 `uv tools`를 사용하여 `copier`를 별도의 격리된 환경에 설치해주세요.

**`pipx` 사용 (권장):**
```bash
pipx install copier
```

**`uv tools` 사용:**
```bash
# 'tools'라는 이름의 가상환경에 copier 설치
uv tool install copier --name tools
# 사용 시
uv tool run --name tools copier copy ...
```

### 2. Docker 빌드 전 의존성 파일 업데이트 (`freeze`)

로컬에서 `uv pip install <package>` 명령어로 새로운 패키지를 추가했다면, **Docker 이미지를 빌드하기 전에 반드시 `requirements/requirements_app.txt` 파일을 업데이트**해야 합니다.

`Dockerfile`은 이 파일을 기준으로 패키지를 설치하기 때문에, 파일의 내용이 최신 상태가 아니면 로컬 환경과 빌드된 이미지의 의존성이 달라져 에러가 발생할 수 있습니다.

아래 명령어를 사용하여 현재 `uv` 가상환경에 설치된 패키지 목록을 `requirements_app.txt` 파일에 저장하세요.

```bash
# venv 가상환경이 활성화된 상태에서 실행
uv pip freeze > requirements/requirements_app.txt
```

---

## 💡 심화 사용법: `@lamp_invocation` 데코레이터

`@lamp_invocation` 데코레이터의 옵션을 조절하여 API의 동작 방식을 변경할 수 있습니다.

```python
@router.post("/invocations")
@lamp_invocation(
    use_sync=True,      # 동기 모드 활성화
    use_async=True,     # 비동기 모드 활성화
    wait=5,             # 비동기 최소 대기 시간 (초)
    timeout=10,         # 비동기 최대 타임아웃 (초)
    use_observe=False,  # Langfuse 추적 기능 비활성화
)
def invocations(model_input: ModelInput, jwt_header: LetsurJwtHeaders) -> ModelOutput:
    ...
```

*   `use_sync (bool)`: `True`이면, API 요청 시 즉시 결과를 반환합니다. (기본값: `True`)
*   `use_async (bool)`: `True`이면, API 요청 시 일단 접수 확인을 반환하고, 실제 작업은 백그라운드에서 수행합니다. (기본값: `True`)
*   `use_observe (bool)`: `True`로 설정하면, 이 API 호출에 대한 Langfuse 트레이스를 생성하여 요청/응답, 에러 등을 추적할 수 있습니다. (사전 설정 필요) (기본값: `False`)


## ❓ FAQ

**Q. 모델 파일(예: `.pth`, `.pkl`)은 어떻게 전달해야 하나요?**
A. 모델 파일은 Docker 이미지에 직접 포함시키지 않습니다. 대신, 배포 시 `lamp-cli`나 사내 플랫폼의 기능을 통해 **외부 스토리지(S3 등)에 있는 모델을 서버 환경의 특정 경로로 마운트**하게 됩니다. 코드에서는 `os.getenv("MODEL_PATH")` 와 같이 환경 변수를 읽어 해당 경로의 모델을 로드하도록 작성하는 것을 권장합니다.

**Q. `pandas`, `scikit-learn` 같은 Python 패키지를 추가하고 싶어요.**
A. `requirements/requirements_app.txt` 파일에 필요한 패키지 이름을 추가해주세요. 그 후 Docker 이미지를 다시 빌드하면(`docker compose build`) 해당 패키지가 설치됩니다.

**Q. 로그는 어떻게 남기나요?**
A. 코드 내에서 `ServingLogger().info("로그 메시지")` 와 같이 사용하면 됩니다. 배포된 후에는 사내 플랫폼의 로그 시스템에서 해당 로그를 확인할 수 있습니다.
