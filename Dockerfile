# syntax=docker/dockerfile:1

# ---------- base: runtime dependencies only ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY *.py ./

# ---------- test: adds pytest/flake8 and the test-suite ----------
# Used by CI:  docker build --target test -t aceest-fitness:test .
#              docker run --rm aceest-fitness:test
FROM base AS test
COPY requirements-dev.txt pytest.ini .flake8 ./
RUN pip install -r requirements-dev.txt
COPY tests ./tests
CMD ["pytest", "-v"]

# ---------- runtime: small, non-root, no test tooling (default target) ----------
FROM base AS runtime
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir /data && chown appuser /data
ENV ACEEST_DB=/data/aceest_fitness.db
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health').status==200 else 1)"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
