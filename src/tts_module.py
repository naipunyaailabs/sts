"""
Text-to-Speech Module using gTTS (Google Text-to-Speech)
Converts Russian text to audio
"""

import numpy as np
import soundfile as sf
import threading
import queue
import time
import io
import tempfile
import os
import subprocess
from typing import Optional, Callable
from gtts import gTTS

# Optional pygame import – only import/initialize if not in server mode
_PYGAME_ENABLED = os.getenv("STS_DISABLE_PYGAME", "0") != "1"
if _PYGAME_ENABLED:
    import pygame


"""Configure a local ffmpeg binary if present.

We expect ffmpeg.exe to be placed at: src/ffmpeg/bin/ffmpeg.exe
This avoids needing a system-wide FFmpeg install or PATH changes.
"""

# Compute expected local ffmpeg path relative to this file
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FFMPEG = os.path.join(_BASE_DIR, "ffmpeg", "bin", "ffmpeg.exe")

if os.path.isfile(_LOCAL_FFMPEG):
    os.environ["FFMPEG_BINARY"] = _LOCAL_FFMPEG


class RussianTextToSpeech:
    def __init__(self, callback: Optional[Callable] = None):
        """Initialize TTS pipeline using gTTS and pygame."""
        self.callback = callback
        self.tts_queue = queue.Queue()
        self.is_speaking = False
        self.tts_thread = None

        # Audio settings
        self.sample_rate = 22050  # standard TTS sample rate
        self.temp_dir = tempfile.gettempdir()

        # Initialize pygame mixer for playback (skip in server mode)
        if _PYGAME_ENABLED:
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)

        print("gTTS-based RussianTextToSpeech initialized")

    def _process_tts(self):
        """Background worker to process queued TTS requests."""
        while self.is_speaking or not self.tts_queue.empty():
            try:
                text, request_id = self.tts_queue.get(timeout=0.1)

                audio_data = self.synthesize(text)

                if self.callback is not None and audio_data is not None and len(audio_data) > 0:
                    self.callback(audio_data, request_id)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in TTS worker: {e}")

        self.is_speaking = False

    def synthesize_async(self, text: str, request_id: str = None):
        """Queue text for asynchronous synthesis."""
        if not self.is_speaking:
            self.is_speaking = True
            self.tts_thread = threading.Thread(target=self._process_tts, daemon=True)
            self.tts_thread.start()

        self.tts_queue.put((text, request_id))

    def synthesize(self, text: str) -> np.ndarray:
        """Convert Russian text to audio using gTTS.

        Returns a numpy array of audio samples (mono).
        """
        if not text or not text.strip():
            return np.array([])

        try:
            # Temporary file paths
            temp_mp3 = os.path.join(self.temp_dir, f"tts_{int(time.time()*1000)}.mp3")
            temp_wav = temp_mp3.replace(".mp3", ".wav")

            # Generate MP3 with gTTS
            tts = gTTS(text=text, lang="ru")
            tts.save(temp_mp3)

            # Convert MP3 to WAV using local ffmpeg via subprocess
            ffmpeg_bin = os.environ.get("FFMPEG_BINARY", _LOCAL_FFMPEG)
            if not (ffmpeg_bin and os.path.isfile(ffmpeg_bin)):
                raise FileNotFoundError(f"ffmpeg binary not found at: {ffmpeg_bin}")

            cmd = [
                ffmpeg_bin,
                "-y",              # overwrite output
                "-loglevel", "error",
                "-i", temp_mp3,
                "-ar", str(self.sample_rate),
                "-ac", "1",
                "-f", "wav",
                temp_wav,
            ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr.decode(errors='ignore')}")

            # Load WAV into numpy array
            audio_data, sr = sf.read(temp_wav)

            # Clean up temp files
            try:
                os.remove(temp_mp3)
                os.remove(temp_wav)
            except OSError:
                pass

            # Ensure mono float32
            audio_data = np.asarray(audio_data, dtype=np.float32)
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            return audio_data

        except Exception as e:
            print(f"Error during gTTS synthesis: {e}")
            return np.array([])

    def synthesize_to_file(self, text: str, output_path: str):
        """Synthesize speech and save to a WAV file."""
        audio_data = self.synthesize(text)
        if audio_data is not None and len(audio_data) > 0:
            sf.write(output_path, audio_data, self.sample_rate)
            print(f"Audio saved to: {output_path}")
        else:
            print("No audio data generated")

    def play_audio(self, audio_data: np.ndarray):
        """Play audio data using pygame mixer."""
        if not _PYGAME_ENABLED:
            # No-op in server mode
            return
        if audio_data is None or len(audio_data) == 0:
            return

        try:
            # Normalize and ensure float32
            audio_data = np.asarray(audio_data, dtype=np.float32)
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.9

            # Write to temporary WAV
            temp_wav = os.path.join(self.temp_dir, f"play_{int(time.time()*1000)}.wav")
            sf.write(temp_wav, audio_data, self.sample_rate)

            # Play via pygame
            pygame.mixer.music.load(temp_wav)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            try:
                os.remove(temp_wav)
            except OSError:
                pass

        except Exception as e:
            print(f"Error playing audio via pygame: {e}")

    def speak(self, text: str):
        """Synthesize text and play it immediately (blocking)."""
        audio_data = self.synthesize(text)
        if audio_data is not None and len(audio_data) > 0:
            self.play_audio(audio_data)

    def stop_tts(self):
        """Stop background TTS processing and any playback."""
        self.is_speaking = False
        if _PYGAME_ENABLED:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

        if self.tts_thread is not None:
            self.tts_thread.join(timeout=1.0)


class AudioPlayer:
    """Simple audio player for TTS output using pygame."""

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        # Safe to call even if mixer already initialized
        if _PYGAME_ENABLED and not pygame.mixer.get_init():
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)

    def play(self, audio_data: np.ndarray):
        """Play audio data (blocking) using pygame."""
        if not _PYGAME_ENABLED:
            # No-op in server mode
            return
        if audio_data is None or len(audio_data) == 0:
            return

        try:
            audio_data = np.asarray(audio_data, dtype=np.float32)
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.9

            temp_wav = os.path.join(tempfile.gettempdir(), f"player_{int(time.time()*1000)}.wav")
            sf.write(temp_wav, audio_data, self.sample_rate)

            pygame.mixer.music.load(temp_wav)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            try:
                os.remove(temp_wav)
            except OSError:
                pass

        except Exception as e:
            print(f"AudioPlayer error: {e}")

    def close(self):
        """Placeholder for API compatibility; pygame handles mixer shutdown globally."""
        if _PYGAME_ENABLED:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass


if __name__ == "__main__":
    # Simple manual test for the TTS module
    def audio_callback(audio_data, request_id):
        print(f"Generated audio ({request_id}): {len(audio_data)} samples")
        player = AudioPlayer()
        player.play(audio_data)

    tts = RussianTextToSpeech(callback=audio_callback)

    samples = [
        "Привет, как дела?",
        "Сегодня отличная погода.",
        "Спасибо за использование нашей системы.",
    ]

    for idx, text in enumerate(samples):
        rid = f"test_{idx}"
        print(f"Synthesizing ({rid}): {text}")
        tts.synthesize_async(text, rid)
        time.sleep(5)

