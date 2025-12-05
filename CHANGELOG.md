# Changelog

All notable changes to the Speech Translation System will be documented in this file.

## [2.0.0] - 2025-12-05

### Added

#### Security & Authentication
- **API Key Authentication**: Optional API key protection via `STS_API_KEY` environment variable
- **Rate Limiting**: 10 requests per minute per IP address to prevent abuse
- **Request Validation**: File size limits, format validation, and input sanitization

#### API Improvements
- **Enhanced Error Handling**: Detailed error messages with proper HTTP status codes
- **Readiness Endpoint**: `/ready` endpoint to check if models are loaded
- **Response Headers**: Include transcribed/translated text and processing time in headers
- **CORS Support**: Cross-origin resource sharing enabled for web clients

#### Performance
- **Eager Model Loading**: Models load at startup by default for faster first request
- **Configurable STT Model**: Choose Whisper model size via `STT_MODEL` environment variable
- **Improved Logging**: Comprehensive logging to both file and console with timestamps

#### Documentation
- **API Documentation**: Complete API reference in `API_DOCUMENTATION.md`
- **Environment Configuration**: `.env.example` file with all configuration options
- **Updated README**: Enhanced documentation with Docker examples and security guidance

#### Cross-Platform Support
- **FFmpeg Path Detection**: Automatically detects Windows vs Unix systems for FFmpeg binary
- **Platform-Agnostic**: Works on Windows, Linux, and macOS without code changes

### Changed

#### Breaking Changes
- **Sample Rate Documentation**: Fixed documentation to correctly state output is 22050 Hz (not 16 kHz)
- **API Response Structure**: `/translate-audio` now returns audio in response body with metadata in headers

#### Improvements
- **Better Error Messages**: More descriptive error responses with actionable information
- **Enhanced Logging**: All requests, translations, and errors are now logged with context
- **Docker Configuration**: Added environment variables to Dockerfile for easier configuration

### Fixed

- **Sample Rate Mismatch**: Documentation now correctly reflects 22050 Hz output sample rate
- **FFmpeg Cross-Platform**: Fixed hardcoded `.exe` extension that broke on Linux/Mac
- **Error Handling**: Improved exception handling throughout the pipeline
- **Missing Dependencies**: Added `slowapi` to requirements.txt for rate limiting

### Security

- **API Authentication**: Protects endpoints from unauthorized access
- **Rate Limiting**: Prevents resource exhaustion from excessive requests
- **Input Validation**: Validates file sizes and formats before processing
- **Secure Headers**: Added security headers to API responses

---

## [1.0.0] - 2024-XX-XX

### Initial Release

- Real-time English to Russian speech translation
- Whisper-based speech-to-text
- MarianMT translation engine
- gTTS text-to-speech synthesis
- FastAPI HTTP interface
- Docker support
- CPU-optimized pipeline
- Modular architecture

---

## Upgrade Guide: 1.0.0 → 2.0.0

### Required Changes

1. **Install New Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Update Environment Variables** (Optional):
   ```bash
   # Create .env file from template
   cp .env.example .env
   
   # Set API key for security
   export STS_API_KEY="your-secret-key"
   ```

3. **Update API Clients**:
   - Add `X-API-Key` header if authentication is enabled
   - Parse response headers for transcribed/translated text
   - Handle new HTTP status codes (401, 403, 413, 429)

### Optional Enhancements

1. **Configure Model Size**:
   ```bash
   export STT_MODEL="small"  # or tiny, base, medium, large
   ```

2. **Adjust Rate Limits**:
   Edit `api_app.py` line with `@limiter.limit("10/minute")` decorator

3. **Disable Eager Loading** (for memory-constrained systems):
   ```bash
   export EAGER_LOAD="false"
   ```

### Backward Compatibility

- Existing `/translate-audio` endpoint still works
- No API key required if `STS_API_KEY` is not set
- Default configuration matches v1.0.0 behavior

---

## Development Roadmap

### Planned for v2.1.0
- [ ] Support for additional language pairs
- [ ] WebSocket streaming for real-time translation
- [ ] Batch translation endpoint
- [ ] Metrics/Prometheus endpoint
- [ ] Docker Compose setup with nginx

### Under Consideration
- GPU support for faster processing
- Alternative TTS engines (Coqui TTS)
- Voice cloning capabilities
- Multiple speaker detection
- Custom vocabulary support

---

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting improvements.

## Security

To report security vulnerabilities, please email security@example.com (do not open public issues).
