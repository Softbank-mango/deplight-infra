#!/bin/bash

export $(grep -v '^#' .env.core | xargs)

# Set LetsurPort
if [ -z "$LETSUR_PORT" ]; then
  export LETSUR_PORT=$(python -c "import socket; s = socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()")
fi
echo -e "\033[32mAvailable port: $LETSUR_PORT\napiServer will be running on http://127.0.0.1:$LETSUR_PORT\033[0m"

# Set LETSUR_ML_PROJECT_NAME
export LETSUR_ML_PROJECT_NAME=$(awk '
  /^\[project\]/ { in_project=1; next }
  /^\[/ { in_project=0 }
  in_project && /^\s*name\s*=/ {
    gsub(/"/, "", $3);
    print $3;
    exit;
  }
' pyproject.toml)


function check_setuptools_scm {
  if ! python -c "import setuptools_scm" &>/dev/null; then
  echo "[INFO] setuptools_scm not found. Installing..."
  pip install --quiet setuptools_scm || {
    echo "[ERROR] setuptools_scm 설치 실패" >&2
    exit 1
  }
  fi
}

# SET IMAGE_VERSION
check_setuptools_scm
FALLBACK_VERSION="${IMAGE_VERSION:-v0.1.0}"
if RAW_VERSION=$(python -m setuptools_scm 2>/dev/null); then
  SANITIZED_VERSION=$(echo "$RAW_VERSION" | sed 's/+/-/g')
  export IMAGE_VERSION="v${SANITIZED_VERSION#v}"
else
  echo "[WARN] setuptools_scm 실행 실패. fallback 버전 사용: ${FALLBACK_VERSION}" >&2
  SANITIZED_VERSION=$(echo "$FALLBACK_VERSION" | sed 's/+/-/g')
  export IMAGE_VERSION=${SANITIZED_VERSION}
fi

function dc {
    docker compose "$@"
}

#DEBUG 변수가 선언되어있을때만 출력되는 logging용 함수
function log {
  if [[ ! -z "${DEBUG}" ]]; then echo "$1"; fi
}

# GitHub 토큰 환경 변수 설정
function set_github_token {

    if [ -f $HOME/.lamp/credentials ]; then
        log "retrieving git credential from lamp-credential"
        git_token=$(grep "GITHUB_AUTH_TOKEN" $HOME/.lamp/credentials | head -n 1 | sed 's/GITHUB_AUTH_TOKEN://g' | tr -d " \t\n\r" )

    fi

    # 기존 방식으로 token을 성공적으로 못받아온 경우 fallback.
    # git credential helper의 값을 사용한다.
    if [ -z "$git_token" ]; then
      git_credential_helper=$(git config credential.helper)

      log "Found git credential helper: $git_credential_helper"
      if [[ ${git_credential_helper} == "osxkeychain" ]]; then
        log "retrieving git credential from osxkeychain"
        git_token=$(security find-internet-password -s "github.com" -w)

      elif [[ ${git_credential_helper} == "store" ]]; then
        log "retrieving git credential from git credential store"
        export GIT_CREDENTIAL=$(awk '/github.com/' $HOME/.git-credentials)
        return

      else
        log "git credential helper: $git_credential_helper not expected"

      fi

    fi


    if [ -z "$git_token" ]; then
      log "GitHub 토큰을 가져오지 못했습니다."
    else
      log "GitHub 토큰을 성공적으로 설정했습니다."
      export GIT_CREDENTIAL="https://git:$git_token@github.com"
    fi

}

function main {
  set_github_token
  dc $@
}

# 메인 함수 호출
main $@
