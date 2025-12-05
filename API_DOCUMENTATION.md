# STS API Documentation

## Version 2.0.0

## Overview

The Speech Translation Service (STS) API provides real-time English-to-Russian speech translation via HTTP endpoints.

**Pipeline**: English Audio (16kHz) → Whisper STT → MarianMT Translation → gTTS → Russian Audio (22050Hz)

---

## Base URL

```
http://localhost:8000
```

---

## Authentication

API key authentication is **optional** but **recommended** for production.

### Enabling Authentication

Set the `STS_API_KEY` environment variable:

```bash
export STS_API_KEY="your-secret-key-here"
```

### Using Authentication

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key-here" ...
```

---

## Endpoints

### 1. Health Check

Check if the service is running.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-12-05T10:30:00.000Z",
  "models_loaded": true
}
```

---

### 2. Readiness Check

Check if models are loaded and service is ready.

**Endpoint**: `GET /ready`

**Response** (200 OK):
```json
{
  "status": "ready",
  "timestamp": "2025-12-05T10:30:00.000Z"
}
```

**Response** (503 Service Unavailable):
```json
{
  "detail": "Models not loaded yet"
}
```

---

### 3. Translate Audio

Translate English speech to Russian speech.

**Endpoint**: `POST /translate-audio`

**Rate Limit**: 10 requests per minute per IP address

**Request**:
- **Method**: POST
- **Content-Type**: `multipart/form-data`
- **Headers** (optional):
  - `X-API-Key`: Your API key (if authentication enabled)
- **Body**:
  - `file`: WAV file (16 kHz, mono, PCM format)
  - **Max file size**: 10 MB (configurable)

**Response**:
- **Content-Type**: `audio/wav`
- **Body**: Russian audio (22050 Hz, mono, PCM format)
- **Headers**:
  - `X-English-Text`: Transcribed English text
  - `X-Russian-Text`: Translated Russian text
  - `X-Processing-Time`: Processing time in seconds

**Example Request**:

```bash
curl -X POST http://localhost:8000/translate-audio \
  -H "X-API-Key: your-secret-key-here" \
  -F "file=@english_audio.wav" \
  -o russian_audio.wav -v
```

**Example with Python**:

```python
import requests

url = "http://localhost:8000/translate-audio"
headers = {"X-API-Key": "your-secret-key-here"}
files = {"file": open("english_audio.wav", "rb")}

response = requests.post(url, headers=headers, files=files)

if response.status_code == 200:
    # Save Russian audio
    with open("russian_audio.wav", "wb") as f:
        f.write(response.content)
    
    # Get metadata from headers
    print(f"English: {response.headers.get('X-English-Text')}")
    print(f"Russian: {response.headers.get('X-Russian-Text')}")
    print(f"Time: {response.headers.get('X-Processing-Time')}s")
else:
    print(f"Error: {response.json()}")
```

---

## Error Responses

### 400 Bad Request

Invalid input (wrong format, empty file, etc.)

```json
{
  "detail": "Only WAV files are supported"
}
```

### 401 Unauthorized

Missing API key when authentication is enabled.

```json
{
  "detail": "API key required. Provide X-API-Key header."
}
```

### 403 Forbidden

Invalid API key.

```json
{
  "detail": "Invalid API key"
}
```

### 413 Payload Too Large

File exceeds size limit.

```json
{
  "detail": "File too large. Maximum size: 10MB"
}
```

### 429 Too Many Requests

Rate limit exceeded.

```json
{
  "detail": "Rate limit exceeded: 10 per 1 minute"
}
```

### 500 Internal Server Error

Processing error.

```json
{
  "detail": "Internal translation error. Check server logs for details."
}
```

### 503 Service Unavailable

Models not loaded yet (readiness check).

```json
{
  "detail": "Models not loaded yet"
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STS_API_KEY` | None | API key for authentication (optional) |
| `STT_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `MAX_FILE_SIZE_MB` | `10` | Maximum upload file size in MB |
| `EAGER_LOAD` | `true` | Load models at startup (true) or on first request (false) |
| `PORT` | `8000` | Server port |

### Docker Run Example

```bash
docker run -d \
  -p 8000:8000 \
  -e STS_API_KEY="your-secret-key" \
  -e STT_MODEL="small" \
  -e MAX_FILE_SIZE_MB="20" \
  sts-api:latest
```

---

## Performance

### Model Sizes vs. Performance

| Model | RAM Usage | CPU Usage | Latency | Accuracy |
|-------|-----------|-----------|---------|----------|
| tiny  | 200MB     | 20%       | 1-2s    | Fair     |
| base  | 500MB     | 40%       | 2-3s    | Good     |
| small | 1GB       | 60%       | 3-5s    | Better   |
| medium| 2GB       | 80%       | 5-8s    | Great    |
| large | 4GB       | 90%+      | 10-15s  | Best     |

### Optimization Tips

1. **Use `base` model** for best balance of speed/accuracy
2. **Enable eager loading** (`EAGER_LOAD=true`) for faster first request
3. **Adjust rate limits** based on your server capacity
4. **Use smaller files** - split long audio into chunks for faster processing

---

## Audio Format Requirements

### Input Audio (English)
- **Format**: WAV (PCM)
- **Sample Rate**: 16,000 Hz (16 kHz)
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit recommended

### Output Audio (Russian)
- **Format**: WAV (PCM)
- **Sample Rate**: 22,050 Hz (22.05 kHz)
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit

### Converting Audio to Correct Format

Using FFmpeg:

```bash
# Convert any audio to STS input format
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f wav output.wav
```

---

## Testing

### Quick Test Script

```bash
# 1. Start the service
docker-compose up -d

# 2. Wait for models to load
sleep 30

# 3. Test health endpoint
curl http://localhost:8000/health

# 4. Test translation (assuming you have test.wav)
curl -X POST http://localhost:8000/translate-audio \
  -F "file=@test.wav" \
  -o output.wav

# 5. Play the result
ffplay output.wav
```

---

## Monitoring & Logs

### Log Files

- **Location**: `sts_api.log` (in working directory)
- **Format**: Timestamped with log level

### Log Contents

- Request receipts with client IP
- Processing times
- Transcribed/translated text
- Errors and warnings

### Example Log Entry

```
2025-12-05 10:30:15 - __main__ - INFO - Translation request received from 192.168.1.100
2025-12-05 10:30:15 - __main__ - INFO - Processing audio file: test.wav (245760 bytes)
2025-12-05 10:30:16 - __main__ - INFO - Starting speech-to-text transcription
2025-12-05 10:30:17 - __main__ - INFO - Transcribed text: Hello, how are you?
2025-12-05 10:30:17 - __main__ - INFO - Starting translation
2025-12-05 10:30:17 - __main__ - INFO - Translated text: Привет, как дела?
2025-12-05 10:30:17 - __main__ - INFO - Starting text-to-speech synthesis
2025-12-05 10:30:18 - __main__ - INFO - Translation completed in 3.24s - EN: 'Hello, how are you?' -> RU: 'Привет, как дела?'
```

---

## Security Considerations

1. **Always use API keys in production**
2. **Use HTTPS** in production (reverse proxy with nginx/traefik)
3. **Adjust rate limits** based on expected traffic
4. **Monitor logs** for suspicious activity
5. **Keep dependencies updated** (`pip install -U -r requirements.txt`)
6. **Limit file sizes** to prevent resource exhaustion

---

## Troubleshooting

### Models taking too long to load

- Use smaller model (e.g., `tiny` or `base`)
- Set `EAGER_LOAD=false` to load lazily
- Increase server resources

### Rate limit too strict

Adjust in code or use reverse proxy for different limits per endpoint.

### Out of memory errors

- Reduce `STT_MODEL` to smaller size
- Reduce `MAX_FILE_SIZE_MB`
- Increase Docker/server memory limits

---

## Support

For issues and questions:
1. Check logs in `sts_api.log`
2. Verify audio format matches requirements
3. Test with `/health` and `/ready` endpoints
4. Review configuration environment variables
