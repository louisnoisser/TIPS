FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GBA_QUALITY_DASHBOARD_DIR=/data/dashboard

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "gba_ops_reanalysis.quality_dashboard_api:app", "--host", "0.0.0.0", "--port", "8000"]
