# syntax=docker/dockerfile:1

# ---------- Stage 1: build — install dependencies into a virtualenv ----------
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools \
 && pip install -r requirements.txt

# ---------- Stage 2: runtime — slim Python + the venv + app code only ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user: the container never runs as root
RUN groupadd --system app \
 && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=build /opt/venv /opt/venv

# Hardening: the runtime never installs packages, so remove pip/setuptools/wheel
# from both the base image and the venv (also removes CVE-2025-47273 in the
# base image's bundled setuptools 70.3.0).
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools wheel 2>/dev/null; \
    /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel 2>/dev/null; \
    rm -rf /usr/local/lib/python3.12/ensurepip \
           /usr/local/lib/python3.12/site-packages/setuptools* \
           /usr/local/lib/python3.12/site-packages/pip* \
           /usr/local/bin/pip* ; \
    true

COPY --chown=app:app app ./app

USER app
EXPOSE 8080

# Docker marks the container unhealthy if the app stops answering
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/actuator/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]