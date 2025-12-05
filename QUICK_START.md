# STS Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Docker (Recommended)

```bash
# 1. Build the image
docker build -t sts-api:latest .

# 2. Run with API key (production)
docker run -d -p 8000:8000 \
  -e STS_API_KEY="my-secret-key-123" \
  -e STT_MODEL="base" \
  --name sts-service \
  sts-api:latest

# 3. Test it
curl http://localhost:8000/health
```

### Option 2: Local Python

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key (optional)
export STS_API_KEY="my-secret-key-123"

# 3. Start server
cd src
python api_app.py
```

---

## 📡 Using the API

### Health Check
```bash
curl http://localhost:8000/health
```

### Translate Audio
```bash
curl -X POST http://localhost:8000/translate-audio \
  -H "X-API-Key: my-secret-key-123" \
  -F "file=@english_audio.wav" \
  -o russian_audio.wav
```

### Python Example
```python
import requests

url = "http://localhost:8000/translate-audio"
headers = {"X-API-Key": "my-secret-key-123"}
files = {"file": open("test.wav", "rb")}

response = requests.post(url, headers=headers, files=files)

if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)
    print(f"English: {response.headers['X-English-Text']}")
    print(f"Russian: {response.headers['X-Russian-Text']}")
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Security
export STS_API_KEY="your-secret-key"

# Model Selection (tiny/base/small/medium/large)
export STT_MODEL="base"

# File Upload Limit (MB)
export MAX_FILE_SIZE_MB="10"

# Performance
export EAGER_LOAD="true"
```

### Docker with Config

```bash
docker run -d -p 8000:8000 \
  -e STS_API_KEY="secret123" \
  -e STT_MODEL="small" \
  -e MAX_FILE_SIZE_MB="20" \
  -e EAGER_LOAD="true" \
  sts-api:latest
```

---

## 🎤 Audio Format Requirements

### Input (English)
- **Format**: WAV (PCM)
- **Sample Rate**: 16,000 Hz
- **Channels**: Mono

### Output (Russian)
- **Format**: WAV (PCM)
- **Sample Rate**: 22,050 Hz
- **Channels**: Mono

### Convert Audio with FFmpeg
```bash
# Convert any format to correct input format
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
```

---

## 🔒 Security Best Practices

1. **Always set API key in production**:
   ```bash
   export STS_API_KEY="$(openssl rand -hex 32)"
   ```

2. **Use HTTPS** (setup reverse proxy with nginx/traefik)

3. **Monitor logs**:
   ```bash
   tail -f sts_api.log
   ```

4. **Limit file sizes** appropriately for your use case

---

## 🐛 Troubleshooting

### Service won't start
```bash
# Check if port is already in use
lsof -i :8000  # Unix
netstat -ano | findstr :8000  # Windows

# Check Docker logs
docker logs sts-service
```

### Models loading too slowly
```bash
# Use smaller model
export STT_MODEL="tiny"

# Or disable eager loading
export EAGER_LOAD="false"
```

### Rate limit errors
- Default: 10 requests/minute per IP
- Modify `@limiter.limit("10/minute")` in `api_app.py`

### Audio format errors
```bash
# Verify your audio file
ffprobe input.wav

# Should show: 16000 Hz, 1 channel (mono)
```

---

## 📚 More Information

- **Full API Docs**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Complete Guide**: [README.md](README.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 💡 Common Use Cases

### 1. Real-time Meeting Translation
```python
# Stream audio chunks during meeting
for chunk in audio_stream:
    response = requests.post(url, headers=headers, files={"file": chunk})
    play_audio(response.content)
```

### 2. Batch File Processing
```bash
for file in *.wav; do
    curl -X POST http://localhost:8000/translate-audio \
      -H "X-API-Key: key123" \
      -F "file=@$file" \
      -o "russian_${file}"
done
```

### 3. Integration with Teams Bot
```python
# Receive English captions from Teams
caption_text = get_teams_caption()

# Convert to audio (TTS)
english_audio = text_to_speech(caption_text)

# Translate via STS API
russian_audio = translate_audio(english_audio)

# Play in meeting
play_in_meeting(russian_audio)
```

---

## 🎯 Performance Tips

1. **Choose right model size**:
   - `tiny`: Fast but less accurate (1-2s latency)
   - `base`: Balanced (2-3s latency) ✅ Recommended
   - `small`: More accurate (3-5s latency)

2. **Enable eager loading** for faster first request

3. **Use smaller audio chunks** for lower latency

4. **Monitor resource usage**:
   ```bash
   docker stats sts-service
   ```

---

## 📞 Support

Need help? Check the logs first:
```bash
# Local
cat sts_api.log

# Docker
docker logs sts-service
```

Common issues are documented in [README.md](README.md#troubleshooting)
