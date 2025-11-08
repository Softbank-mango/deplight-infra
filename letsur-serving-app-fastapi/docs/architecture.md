# FastAPI Serving App Template 아키텍처

이 문서는 FastAPI Serving App 템플릿을 사용하여 개발된 애플리케이션이 사내 플랫폼을 통해 배포되는 전체 파이프라인의 아키텍처를 설명합니다.

## 1. 철학 및 목표

본 템플릿은 **"관심사의 분리(Separation of Concerns)"** 철학을 기반으로 설계되었습니다.

*   **템플릿 코어 (`src/_core`)**: 웹 서버 운영, 로깅, 인증, 비동기 처리 등 인프라 영역을 담당하며, 최종 사용자는 거의 수정할 필요가 없습니다.
*   **비즈니스 로직 (`src/routers`, `src/dataclasses`)**: AI 엔지니어가 실제 추론 코드 등 핵심 비즈니스 로직 작성에만 집중하는 영역입니다.

이를 통해 사용자는 복잡한 웹 프레임워크의 내부 구조 없이도, 자신의 코드를 안정적으로 배포하고 운영할 수 있습니다.

## 2. 전체 파이프라인 개요

배포 파이프라인은 크게 3가지 단계로 구성됩니다.
1.  **Phase 1: 개발 및 빌드**: AI 엔지니어가 코드를 개발하고, CI/CD를 통해 배포 가능한 Docker 이미지를 생성하는 단계입니다.
2.  **Phase 2: 등록**: 생성된 Docker 이미지와 배포 설정을 `StaiX` 플랫폼에 등록하여 배포 가능한 상태로 만드는 단계입니다.
3.  **Phase 3: 배포**: `StaiX` 플랫폼에서 배포를 시작하여, 실제 운영 클러스터에 애플리케이션이 배포되는 단계입니다.

---

## Phase 1: 개발 및 빌드 (Development & Build)

*AI 엔지니어의 개발 환경에서부터 CI/CD를 통해 배포 아티팩트가 생성되는 과정입니다.*

![Development & Build Diagram](https://i.imgur.com/your-diagram-image.png) <!-- TODO: /tmp/images/image.png 이미지 삽입 -->

1.  **프로젝트 생성**: AI 엔지니어는 `Copier`를 사용하여 이 템플릿으로부터 `Project App` (애플리케이션 코드)을 생성합니다.
2.  **코드 개발 및 Push**: 비즈니스 로직을 작성하고 `Git`을 통해 `Letsur GitHub`에 코드를 Push 합니다.
3.  **CI/CD 트리거 (on Release)**: 개발자가 GitHub에서 **Release**를 생성하면, `Git Action` 워크플로우가 트리거됩니다.
4.  **Docker 이미지 빌드 및 Push**: `Git Action`은 `Dockerfile`을 기반으로 `Project Container Image`를 빌드하여 컨테이너 레지스트리(`ECR`)에 Push 합니다.
5.  **MLflow 실험(Experiment) 관리**: 이와 별개로, AI 엔지니어는 `LAMP CLI`를 사용하여 `DBX MLflow`에 `Experiment`와 그 하위의 `Run`들을 생성합니다. 이 `Run`에는 `Serving Model Spec`, `Serving Endpoint Spec`과 같은 배포 설정 파일들이 아티팩트로 기록됩니다.

## Phase 2: 등록 (Registration)

*개발된 애플리케이션을 `StaiX` 플랫폼에서 인식하고 배포할 수 있도록 연결하는 과정입니다.*

![Registration Diagram](https://i.imgur.com/your-diagram-image.png) <!-- TODO: /tmp/images/image 1.png 이미지 삽입 -->

1.  **`StaiX` 프로젝트 생성**: 사용자가 `StaiX` UI에서 `Project`를 생성하면, `DBX MLflow`에 해당 `Project`의 ID(`LAMP_PROJECT_ID`)를 이름으로 갖는 `Registered Model`이 자동으로 생성됩니다.
2.  **`Run`과 `Project` 연결**: AI 엔지니어는 `LAMP CLI`의 `Register` 명령어를 사용하여, Phase 1에서 생성한 `DBX MLflow`의 특정 `Run`(`RUN_ID`)을 `StaiX`의 `Project`(`LAMP_PROJECT_ID`)와 연결합니다.
3.  **`Model Version` 생성**: `Register` 명령이 성공하면, `DBX MLflow`의 `Registered Model` 아래에 해당 `Run`의 정보가 담긴 새로운 `Model Version`이 생성됩니다.
4.  **`StaiX` UI에 표시**: `DBX MLflow`에 새로운 `Model Version`이 생성되면, `StaiX` UI의 해당 `Project` 아래에서도 배포 가능한 `Model Version`으로 표시됩니다.

## Phase 3: 배포 (Deployment)

*`StaiX` UI에서 배포 버튼을 클릭한 이후, 실제 운영 클러스터에 애플리케이션이 배포되는 과정입니다.*

![Deployment Diagram](https://i.imgur.com/your-diagram-image.png) <!-- TODO: /tmp/images/image 2.png 이미지 삽입 -->

1.  **배포 트리거**: 사용자가 `StaiX` UI에서 특정 `Model Version`의 배포를 시작(`Deploy Project`)합니다.
2.  **중계 서버 호출**: `StaiX`는 `ML Serving Operator`(중계 서버)에 배포를 요청합니다.
3.  **Spec 조회**: `ML Serving Operator`는 `DBX MLflow`에서 해당 `Model Version`에 연결된 `Serving Endpoint Spec`을 가져옵니다.
4.  **배포 요청**: `ML Serving Operator`는 조회한 Spec을 가공하고, `Serving Endpoint Deploy Operator (ArgoCD)`에 최종 배포를 요청합니다.
5.  **Helm/ArgoCD 배포**: `ArgoCD`는 `Serving Endpoint Spec`에 정의된 Helm Chart와 Values를 기반으로, Inhouse Cluster(운영 클러스터)에 `Serving Endpoint`를 배포합니다.
6.  **서비스 실행**: 배포가 완료되면, `Serving Endpoint` 내에 실제 애플리케이션(`App w/ Replica`)과 인증/라우팅(`Auth Routing`) 로직이 실행됩니다. 이제 외부 클라이언트는 이 엔드포인트를 통해 추론(`Invoke Inference`)을 요청할 수 있습니다.
