FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system hashguard \
    && adduser --system --ingroup hashguard hashguard

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

USER hashguard

CMD ["hashguard"]

