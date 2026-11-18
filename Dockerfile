# Production container for Hugging Face Spaces / Render / Cloud deployment
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user (UID 1000) standard for Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies into user directory
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application source and data
COPY --chown=user . $HOME/app

# Ensure writable runtime directories exist
RUN mkdir -p uploads data

# Expose target application port
EXPOSE 7860

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/health || exit 1

# Start the FastAPI application with Uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
