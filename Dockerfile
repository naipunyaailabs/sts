FROM python:3.9-slim

WORKDIR /app

# Install system dependencies needed by soundfile / ffmpeg, etc.
# Also install build tools for PyAudio compilation
RUN apt-get update && apt-get install -y \
    ffmpeg libsndfile1 \
    gcc python3-dev portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

WORKDIR /app/src

# Disable pygame audio init in server mode
ENV STS_DISABLE_PYGAME=1

# Default configuration (can be overridden at runtime)
ENV STT_MODEL=base
ENV MAX_FILE_SIZE_MB=10
ENV EAGER_LOAD=true

EXPOSE 8000

# Run FastAPI app with uvicorn
CMD ["uvicorn", "api_app:app", "--host", "0.0.0.0", "--port", "8000"]
