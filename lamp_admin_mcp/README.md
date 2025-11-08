# lamp_admin_mcp
MCP 전용 브랜치: LAMP Admin MCP 서버만 제공합니다. 기존 개별 CLI 커맨드는 제거되었으며, MCP 툴로 노출됩니다.

- [lamp\_admin\_mcp](#lamp_admin_mcp)
  - [실행](#실행)
  - [환경 설정](#환경-설정)
  - [MCP 툴 개요](#mcp-툴-개요)
  - [빠른 시작 예시](#빠른-시작-예시)
  - [주의](#주의)
  - [문의 및 요청 사항](#문의-및-요청-사항)

## 실행
MCP 규격의 표준 I/O(stdio)로 동작합니다.

- 파이썬으로 직접 실행(표준 I/O)
```
uv run mcp dev src/lamp_admin_cli/mcp_server.py
```

MCP 클라이언트(예: IDE 플러그인, LLM 클라이언트 등)는 stdio 기반 프로세스로 본 서버를 실행해 툴을 호출합니다.


## 환경 설정
- 설정 파일: `~/.lamp/credentials` (프로필 다중 관리 가능). 기본 프로필명은 `default`.
- 코드 참조: src/lamp_admin_cli/mcp_server.py:171 의 `with_profile_and_mlflow` 데코레이터가 실행 전 자동으로 프로필을 로드하고, 필요한 환경변수 및 MLflow 트래킹 URI(`databricks`)를 설정합니다.
- GitHub 토큰: v0.6.0부터 GitHub Auth Token 필드가 설정에 추가됩니다. 토큰 생성 가이드는 다음을 참고하세요: https://blog.pocu.academy/ko/2022/01/06/how-to-generate-personal-access-token-for-github.html


## MCP 툴 개요
아래 툴들은 `@mcp.tool()`로 노출되며, 모든 입력 경로는 “절대경로”를 권장/요구합니다. 각 툴은 `success`, `message`, `data`를 포함하는 표준 응답을 반환합니다.

- create_dummy_run
  - 목적: MLflow에 배포 트래킹용 더미 런 생성. 입력: `project_name`(필수), `run_name`(선택), `profile_name`(기본 default)
  - 반환: `run_id`, `run_name`, `experiment_id`, `project_name`

- upload_serving_model_spec
  - 목적: 재현 가능한 서빙을 위해 docker-compose(.yml/.yaml)와 `.env` 파일 업로드(S3 저장 + 런 태그 갱신)
  - 요구: 절대경로, compose와 env 파일 모두 필요
  - 반환: 업로드된 파일 수와 `run_id`

- upload_serving_endpoint_spec
  - 목적: 엔드포인트 스펙(metadata/values/env/openapi) 업로드(S3 저장 + 런 태그 갱신)
  - 요구: 절대경로, 최소 1종류 이상의 파일 제공
  - 반환: 각 파일군 업로드 개수와 `run_id`

- register_model
  - 목적: 생성된 `run_id`를 LAMP 프로젝트(`project_id`)에 모델 버전으로 등록
  - 반환: `run_id`, `project_id`, 사용된 `profile`

- generate_endpoint_spec
  - 목적: `<project_path>/.deployment/`에 템플릿(metadata/values/env) 생성
  - 요구: `project_path` 절대경로, 'chart_version'="v0.3.0" (default)
  - 반환: `output_dir`, `chart_version`, 생성 결과(Boolean)

- populate_endpoint_spec
  - 목적: `.deployment` 없으면 생성 후, `.env` 복사 및 `values.{stage}.yaml`의 `apiServer.deployment.image`를 최종 이미지로 갱신
  - 스테이지: 프로필의 `LAMP_ENVIRONMENT`가 없으면 `dev` 기본값
  - 반환: 스테이지, 경로, 최종 이미지

- create_mcp_release
  - 목적: GitHub 릴리스를 `{tag_prefix}{n}` 규칙으로 생성하고, docker-compose 서비스 이미지 태그를 `{ecr_repo_prefix}:{project}-{tag}`로 갱신 시도
  - 반환: 릴리스 정보(태그/URL/ID), compose 갱신 여부/경로, 최종 이미지, 프로젝트명, 서비스명

- run_deployment_pipeline
  - 목적: 전체 배포 파이프라인 순차 실행(실패 즉시 중단, 각 단계 응답 수집)
  - 순서: create_mcp_release → populate_endpoint_spec → create_dummy_run → upload_serving_model_spec → upload_serving_endpoint_spec → register_model
  - 반환: 각 단계의 표준 응답을 `data`에 집계


## 빠른 시작 예시
MCP 클라이언트에서 아래 순서로 툴을 호출하는 시나리오 예시입니다.
codex를 사용 중이고 배포하고자 하는 project 폴더 위치에서 실행 중이라면, staix project id 값만 입력하면 됩니다.

- github 릴리즈 -> 더미 런 생성 → 스펙 업로드 (모델, 엔드포인트) → 모델 등록 (staix)
```
run_deployment_pipeline {
  "profile_name": "default",
  "repo": "owner/repo",
  "target_branch": "main",
  "project_path": "/abs/path/to/serving-project",
  "project_id": 123,
  "project_name": "my-project",
  "docker_compose_paths": ["/abs/path/to/serving-project/docker-compose.yaml"],
  "env_file_paths": ["/abs/path/to/serving-project/.env.core"],
  "metadata_paths": ["/abs/path/to/serving-project/.deployment/metadata.yaml"],
  "values_paths": ["/abs/path/to/serving-project/.deployment/values.dev.yaml"],
  "openapi_paths": ["/abs/path/to/serving-project/openapi.yaml"]
}
```

단일 단계로 직접 호출하려면 `create_dummy_run` 후 반환된 `run_id`를 `upload_serving_model_spec`, `upload_serving_endpoint_spec`, `register_model`에 전달하면 됩니다.

경로는 모두 절대경로를 요구합니다. 상대경로 입력 시 요청이 실패할 수 있습니다.


## 주의
- v0.6.0부터 GitHub Auth Token이 설정에 추가됩니다. 토큰 발급은 GitHub Personal Access Token 가이드를 참고하세요.
- 현재 MCP 서버는 stdio로 동작합니다.

## 문의 및 요청 사항
mcp server maintainer: 박누리 (nrpark@letsur.ai)
또는 GitHub Issue 로 문의해 주세요.