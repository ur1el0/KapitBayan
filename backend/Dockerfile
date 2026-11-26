# Use official lightweight Python image
FROM python:3.12-slim

# Prevent Python from buffering stdout and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

# Install system dependencies required for PostgreSQL (psycop2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of our Django project
COPY --chown=app:app . .

# Ensure entrypoint is executable and directories exist
RUN chmod +x entrypoint.sh && mkdir -p /app/media /app/staticfiles && chown -R app:app /app/media /app/staticfiles

# Collect static files for production WhiteNoise serving
RUN SECRET_KEY="build-time-secret" DEBUG=True python manage.py collectstatic --noinput

USER app

# Default HTTP port (overridden at runtime by $PORT on Koyeb, Cloud Run, HF Spaces, etc.)
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health', timeout=4)" || exit 1

# Set the entrypoint script
ENTRYPOINT [ "./entrypoint.sh" ]

# Default startup command for container execution (ASGI via Daphne for HTTP + WebSockets)
CMD ["sh", "-c", "exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]
