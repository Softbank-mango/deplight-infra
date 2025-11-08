FROM python:3.10-slim-bullseye as deployer
ARG LETSUR_DEV
ENV PYTHONUNBUFFERED=1
# procps for liveness checking
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libpq-dev gcc git procps net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY ./requirements /code/requirements
RUN pip install --upgrade pip && pip install --no-cache-dir -r code/requirements/requirements_base.txt

## git credential helper가 활성화 되어있어야함.
RUN git config --global credential.helper store

RUN --mount=type=secret,id=GIT_CREDENTIAL,target=/root/.git-credentials \
    pip install --no-cache-dir -r code/requirements/requirements_app.txt

RUN if [ "$LETSUR_DEV" ] ; then pip install --no-cache-dir -r code/requirements/requirements_dev.txt ; fi


COPY ./src /code/src
WORKDIR /code

# we don't need core dump file.
RUN ulimit -c 0

ENTRYPOINT [ \
            "uvicorn", \
            "src._core.app:app", \
            "--proxy-headers", \
            "--host", "0.0.0.0", \
            "--port", "8080" \
]
# ENTRYPOINT gunicorn --access-logfile - --workers $WORKER_COUNT -k src.serving_worker.ServingUvicornWorker src.fastapi_app:app --timeout $TIMEOUT -b 0.0.0.0:$PORT
