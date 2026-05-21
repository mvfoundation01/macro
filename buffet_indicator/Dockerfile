# Dockerfile - production image for hosted dashboard
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.lock

FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source + assets (NOT data/raw/ per .dockerignore)
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY outputs/dashboard.html /app/outputs/dashboard.html
COPY README_DEPLOY.md /app/

# Static server (lightweight)
EXPOSE 8765
CMD ["python", "scripts/serve_dashboard.py"]
