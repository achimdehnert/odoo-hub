FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (without iil-aifw — installed from source below)
COPY services/aifw_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install iil-aifw from source (v0.6.0 not yet on PyPI)
# Build context is repo root — aifw lives at aifw/
COPY aifw/src/ /tmp/iil_aifw/src/
COPY aifw/pyproject.toml /tmp/iil_aifw/pyproject.toml
COPY aifw/README.md /tmp/iil_aifw/README.md
RUN pip install --no-cache-dir /tmp/iil_aifw && rm -rf /tmp/iil_aifw

# Copy application code
COPY services/aifw_service/ .

# Non-root user
RUN useradd -m -u 1000 aifw && chown -R aifw:aifw /app
USER aifw

EXPOSE 8001

CMD ["gunicorn", "aifw_service.wsgi:application", \
     "--bind", "0.0.0.0:8001", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
