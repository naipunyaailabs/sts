"""
Speech-to-Text Module using OpenAI Whisper (CPU-optimized)
Converts English speech to text using microphone input
"""


import whisper
import torch
import numpy as np
import sounddevice as sd
import threading
import queue
import time
from typing import Optional, Callable


class SpeechToText:
    def __init__(self, model_size: str = "base", callback: Optional[Callable] = None):
        """
        Initialize Whisper model for speech-to-text
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
            callback: Function to call when transcription is ready
        """
        self.model_size = model_size
        self.callback = callback
        self.model = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_thread = None
        self.processing_thread = None
        
        # Audio settings
        self.CHANNELS = 1
        self.RATE = 16000  # Whisper expects 16kHz
        # Shorter chunk so we get continuous updates while you speak
        self.CHUNK_DURATION = 2  # seconds
        self.CHUNK_SIZE = int(self.RATE * self.CHUNK_DURATION)
        
        # Load model
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        print(f"Loading Whisper model: {self.model_size}")
        self.model = whisper.load_model(self.model_size)
        print("Whisper model loaded successfully")
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream"""
        if self.is_recording:
            self.audio_queue.put(indata.copy())
        # sounddevice expects this callback to either modify in/out buffers
        # and return None. We only enqueue data for background processing.
        return None
    
    def _process_audio(self):
        """Process audio chunks in background"""
        # Use float32 consistently to match sounddevice output and Whisper expectations
        audio_buffer = np.array([], dtype=np.float32)

        while self.is_recording or not self.audio_queue.empty():
            try:
                # Get audio chunk
                chunk = self.audio_queue.get(timeout=0.1)

                # Ensure chunk is float32 and flattened
                chunk = np.asarray(chunk, dtype=np.float32).flatten()

                # Skip very low-energy chunks (likely background noise or feedback)
                if np.max(np.abs(chunk)) < 0.02:
                    continue

                audio_buffer = np.concatenate([audio_buffer, chunk])

                # Process when we have enough data
                if len(audio_buffer) >= self.CHUNK_SIZE:
                    # Take the chunk
                    audio_data = audio_buffer[:self.CHUNK_SIZE].astype(np.float32)

                    # Transcribe
                    result = self.model.transcribe(audio_data, language="en")
                    text = result["text"].strip()

                    if text and self.callback:
                        self.callback(text)

                    # Remove processed data
                    audio_buffer = audio_buffer[self.CHUNK_SIZE:]

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
    
    def start_recording(self):
        """Start recording from microphone"""
        if self.is_recording:
            return
        
        self.is_recording = True
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_audio)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.RATE,
            channels=self.CHANNELS,
            callback=self._audio_callback,
            blocksize=1024
        )
        self.stream.start()
        
        print("Started recording...")
    
    def stop_recording(self):
        """Stop recording"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Stop audio stream
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        print("Stopped recording")
    
    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe audio file"""
        result = self.model.transcribe(audio_path, language="en")
        return result["text"].strip()
    
    def transcribe_audio_data(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data directly"""
        result = self.model.transcribe(audio_data, language="en")
        return result["text"].strip()


if __name__ == "__main__":
    # Test the STT module
    def text_callback(text):
        print(f"Transcribed: {text}")
    
    stt = SpeechToText(model_size="base", callback=text_callback)
    
    try:
        stt.start_recording()
        print("Recording... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stt.stop_recording()
        print("Recording stopped")
