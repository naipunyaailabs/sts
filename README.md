# Real-time Speech Translation System

English Speech → English Text → Russian Text → Russian Audio

A complete CPU-optimized, open-source real-time speech translation system that runs entirely on your local machine without GPU requirements.

## Features

- **Real-time Processing**: Listen to English speech and output Russian audio in real-time
- **CPU-Optimized**: Designed to run efficiently on CPU only
- **Open Source**: Uses only open-source models and libraries
- **Local Processing**: No cloud dependencies or internet required after setup
- **Modular Design**: Each component (STT, Translation, TTS) can be used independently

## System Architecture

```
Microphone Input → Speech-to-Text (Whisper) → Translation (MarianMT) → Text-to-Speech (Coqui TTS) → Audio Output
```

## Requirements

- Python 3.8 or higher
- Windows/Linux/macOS
- Microphone for input
- Speakers for output
- At least 4GB RAM (8GB recommended)
- 2GB free disk space for models

## Installation

### 1. Clone/Download the Project

```bash
# If using git
git clone <repository-url>
cd STS

# Or download and extract the ZIP file
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### 4. Install Additional System Dependencies

**Windows:**
```bash
# Install Microsoft Visual C++ Redistributable
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

# Install portaudio (PyAudio dependency)
# Download from: http://www.portaudio.com/download.html
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3-dev portaudio19-dev libasound2-dev
```

**macOS:**
```bash
brew install portaudio
```

### 5. Download Models (First Run Only)

The models will be automatically downloaded on first run:
- Whisper model (~150MB for base model)
- MarianMT translation model (~300MB)
- Coqui TTS model (~500MB)

Total download: ~1GB

## Usage

### Quick Start

```bash
cd src
python main_pipeline.py
```

The system will:
1. Load all models (may take 1-2 minutes on first run)
2. Start listening to your microphone
3. Translate English speech to Russian audio in real-time

### Advanced Usage

#### Using Individual Components

```python
from src import SpeechToText, EnglishToRussianTranslator, RussianTextToSpeech

# Speech-to-Text
stt = SpeechToText(model_size="base")
stt.start_recording()
# ... speak in English
stt.stop_recording()

# Translation
translator = EnglishToRussianTranslator()
russian_text = translator.translate("Hello, how are you?")
print(russian_text)  # "Привет, как дела?"

# Text-to-Speech
tts = RussianTextToSpeech()
tts.speak("Привет, как дела?")  # Plays Russian audio
```

#### Processing Audio Files

```python
from src import SpeechTranslationPipeline

pipeline = SpeechTranslationPipeline()
result = pipeline.process_file("english_speech.wav")
print(f"English: {result['english_text']}")
print(f"Russian: {result['russian_text']}")
```

## Model Options

### Whisper Models (Speech-to-Text)
- `tiny`: 39M parameters, fastest, least accurate
- `base`: 74M parameters, good balance (recommended)
- `small`: 244M parameters, more accurate
- `medium`: 769M parameters, very accurate
- `large`: 1550M parameters, most accurate, slowest

Change model size:
```python
pipeline = SpeechTranslationPipeline(stt_model="small")
```

### Performance Optimization

#### For Low-End Systems
```python
# Use smaller models
pipeline = SpeechTranslationPipeline(stt_model="tiny")

# Disable logging for better performance
pipeline = SpeechTranslationPipeline(stt_model="base", enable_logging=False)
```

#### For Better Quality
```python
# Use larger models (requires more RAM and CPU)
pipeline = SpeechTranslationPipeline(stt_model="small")
```

## Troubleshooting

### Common Issues

1. **"No audio input detected"**
   - Check microphone permissions
   - Ensure microphone is not muted
   - Test with Windows Sound Recorder first

2. **"Model loading failed"**
   - Check internet connection (first run only)
   - Ensure enough disk space
   - Try running with administrator privileges

3. **"Audio playback issues"**
   - Check speaker connections
   - Ensure audio drivers are updated
   - Try different audio sample rates

4. **"Performance is slow"**
   - Use smaller model (`tiny` instead of `base`)
   - Close other applications
   - Ensure sufficient RAM available

### Performance Tips

- Use `base` model for best balance of speed and accuracy
- Disable logging in production: `enable_logging=False`
- Ensure system has sufficient RAM (8GB+ recommended; recommended)
"}
```

")
- Close. Close unnecessary applications")]
```

; background applications

; CPU usage

###. Use interviewer; CPU usage")]
```
```
## Configuration

### Audio Settings

Edit the audio parameters in `src/stt_module.py`:

```python
# Microphone settings
self.RATE = 16000  # Sample rate (don't change for Whisper)
self.CHUNK_DURATION = 2  # Seconds per audio chunk
```

### Model Settings

Edit model choices in individual module files:

- `src/stt_module.py`: Whisper model selection
- `src/translation_module.py`: Translation model selection  
- `src/tts_module.py`: TTS model selection

## API Reference

### SpeechTranslationPipeline

Main class that orchestrates the entire pipeline.

```python
pipeline = SpeechTranslationPipeline(stt_model="base", enable_logging=True)

# Start real-time translation
pipeline.start()

# Stop translation
pipeline.stop()

# Get status
status = pipeline.get_status()

# Process audio file
result = pipeline.process_file("audio.wav")
```

### Individual Modules

#### SpeechToText
```python
stt = SpeechToText(model_size="base", callback=your_callback)
stt.start_recording()
stt.stop_recording()
text = stt.transcribe_file("audio.wav")
```

#### EnglishToRussianTranslator
```python
translator = EnglishToRussianTranslator(callback=your_callback)
russian = translator.translate("Hello world")
```

#### RussianTextToSpeech
```python
tts = RussianTextToSpeech(callback=your_callback)
audio = tts.synthesize("Привет мир")
tts.play_audio(audio)
tts.speak("Привет мир")  # Direct speak
```

## System Requirements Details

### Minimum Requirements
- CPU: Dual-core 2.0GHz
- RAM: 4GB
- Storage: 2GB free
- OS: Windows 10/Ubuntu 18.04/macOS 10.14

### Recommended Requirements
- CPU: Quad-core 3.0GHz
- RAM: 8GB
- Storage: 4GB free
- OS: Windows 11/Ubuntu 20.04/macOS 12.0

### Performance Benchmarks

| Model | RAM Usage | CPU Usage | Latency |
|-------|-----------|-----------|---------|
| Tiny | 200MB | 20% | 1-2s |
| Base | 500MB | 40% | 2-3s |
| Small | 1GB | 60% | 3-5s |

## License

This project uses open-source components with permissive licenses:
- Whisper: MIT License
- MarianMT: Apache 2.0 License
- Coqui TTS: MPL 2.0 License
- PyAudio: MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- Real-time speech translation
- CPU-optimized models
- Modular architecture
- Windows/Linux/macOS support
