FROM python:3.10-slim as python-base

ARG DIR

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR $PYSETUP_PATH
COPY ${DIR}/poetry.lock ${DIR}/pyproject.toml ./

ENV PATH="${PATH}:/root/.poetry/bin"

RUN poetry install --no-root

FROM python-base as development

RUN apt-get update && apt-get upgrade -y curl \
      awscli

WORKDIR $PYSETUP_PATH

COPY --from=builder-base $POETRY_HOME $POETRY_HOME
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
ENV PATH="${PATH}:/root/.poetry/bin"

WORKDIR /app

RUN mkdir -p templates

COPY ${DIR}/* ./

RUN poetry install --no-root

CMD ./setup.sh
