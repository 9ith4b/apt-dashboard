FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
RUN python -m pip install --upgrade pip && \
    python -c "import subprocess,sys,tomllib; dependencies=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; subprocess.check_call([sys.executable,'-m','pip','install',*dependencies])"

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN python -m pip install --no-deps .

RUN useradd --create-home --uid 10001 apt-hunter
USER apt-hunter

EXPOSE 8000
CMD ["uvicorn", "apt_hunter.main:app", "--host", "0.0.0.0", "--port", "8000"]
