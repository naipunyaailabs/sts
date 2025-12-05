"""Record live audio from microphone, send to translation API, and play the result."""

import os
import io
import wave
import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import time
from pathlib import Path


def record_audio(duration=2.0, sample_rate=16000):
    """Record audio from microphone (16 kHz mono)."""
    print(f"Recording for {duration} seconds... Speak now.")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    print("Recording finished.")
    return audio


def audio_to_wav_bytes(audio_data, sample_rate=16000):
    """Convert numpy audio to WAV bytes in memory."""
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sample_rate, format='WAV')
    buffer.seek(0)
    return buffer.read()


def play_audio(audio_bytes):
    """Play WAV audio bytes using system sound."""
    # Write to temp file and play
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    # Use system default player (Windows)
    os.startfile(tmp_path)
    print(f"Playing result audio: {tmp_path}")
    # Note: The file will remain; you can delete it manually after listening


def test_live_translation():
    """Record live audio, translate, and play result."""
    api_url = "http://localhost:8000/translate-audio"

    # 1. Record audio
    audio = record_audio(duration=2.0, sample_rate=16000)

    # 2. Convert to WAV bytes
    wav_bytes = audio_to_wav_bytes(audio, sample_rate=16000)

    # 3. Send to API
    print("Sending to translation API...")
    files = {'file': ('live.wav', wav_bytes, 'audio/wav')}
    try:
        response = requests.post(api_url, files=files, timeout=30)
        response.raise_for_status()
        russian_wav = response.content
        print(f"Received Russian audio: {len(russian_wav)} bytes")
    except Exception as e:
        print(f"API error: {e}")
        return

    # 4. Play result
    play_audio(russian_wav)


if __name__ == "__main__":
    test_live_translation()
