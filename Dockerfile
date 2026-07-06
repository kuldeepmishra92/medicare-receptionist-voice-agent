# ─────────────────────────────────────────────────────────
# Dockerfile — Hugging Face Spaces (Docker SDK)
# ─────────────────────────────────────────────────────────
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_PORT=7860
ENV PORT=7860

# Set working directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code
COPY . .

# Grant write permissions for SQLite database file creation
RUN chmod -R 777 /code

# Expose Hugging Face default port 7860
EXPOSE 7860

# Startup command: Seed doctors database and run Uvicorn server on port 7860
CMD ["sh", "-c", "python scripts/seed_doctors.py && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
