"""
Main Real-time Speech Translation Pipeline
English Speech -> English Text -> Russian Text -> Russian Audio
"""

import threading
import queue
import time
import numpy as np
from typing import Optional
import logging

from stt_module import SpeechToText
from translation_module import EnglishToRussianTranslator
from tts_module import RussianTextToSpeech, AudioPlayer


class SpeechTranslationPipeline:
    def __init__(self, stt_model: str = "base", enable_logging: bool = True):
        """
        Initialize the complete speech translation pipeline
        
        Args:
            stt_model: Whisper model size (tiny, base, small, medium, large)
            enable_logging: Enable detailed logging
        """
        self.enable_logging = enable_logging
        self._setup_logging()
        
        # Initialize components
        self.logger.info("Initializing speech translation pipeline...")
        
        # Speech-to-Text
        self.stt = SpeechToText(model_size=stt_model, callback=self._on_speech_to_text)
        
        # Translation
        self.translator = EnglishToRussianTranslator(callback=self._on_translation)
        
        # Text-to-Speech
        self.tts = RussianTextToSpeech(callback=self._on_text_to_speech)
        
        # Audio player
        self.audio_player = AudioPlayer()
        
        # Pipeline state
        self.is_running = False
        self.request_counter = 0
        self.last_text = ""  # for simple STT debouncing
        
        # Queues for managing pipeline flow
        self.stt_queue = queue.Queue()
        self.translation_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        
        self.logger.info("Pipeline initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        if self.enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('speech_translation.log')
                ]
            )
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.disabled = True
    
    def _get_request_id(self) -> str:
        """Generate unique request ID"""
        self.request_counter += 1
        return f"req_{self.request_counter}_{int(time.time() * 1000)}"
    
    def _on_speech_to_text(self, text: str):
        """Callback when speech-to-text is complete"""
        cleaned = text.strip()
        if not cleaned:
            return

        # Ignore the specific phrase "thank you" to avoid unwanted feedback
        if cleaned.lower() in {"thank you", "thank you."}:
            return

        # Ignore immediate repeats of the exact same text
        if cleaned == self.last_text.strip():
            return

        self.last_text = cleaned
        
        request_id = self._get_request_id()
        # Log and print recognized English text
        self.logger.info(f"STT ({request_id}): {cleaned}")
        print(f"[STT] {request_id} -> EN: {cleaned}")
        
        # Queue for translation
        self.translation_queue.put((cleaned, request_id))
        
        # Start translation
        self.translator.translate_async(text, request_id)
    
    def _on_translation(self, translated_text: str, request_id: str):
        """Callback when translation is complete"""
        if not translated_text.strip():
            return
        
        # Log and print translated Russian text
        self.logger.info(f"Translation ({request_id}): {translated_text}")
        print(f"[TRANSLATION] {request_id} -> RU: {translated_text}")
        
        # Queue for TTS
        self.tts_queue.put((translated_text, request_id))
        
        # Start TTS
        self.tts.synthesize_async(translated_text, request_id)
    
    def _on_text_to_speech(self, audio_data: np.ndarray, request_id: str):
        """Callback when text-to-speech is complete"""
        if len(audio_data) == 0:
            return
        
        # Log and print TTS generation details
        self.logger.info(f"TTS ({request_id}): Generated {len(audio_data)} audio samples")
        print(f"[TTS] {request_id} -> samples: {len(audio_data)}")
        
        # Play audio
        try:
            self.audio_player.play(audio_data)
            self.logger.info(f"Audio played for {request_id}")
        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
    
    def start(self):
        """Start the real-time speech translation pipeline"""
        if self.is_running:
            self.logger.warning("Pipeline is already running")
            return
        
        self.logger.info("Starting speech translation pipeline...")
        self.is_running = True
        
        # Start speech-to-text recording
        self.stt.start_recording()
        
        self.logger.info("Pipeline started. Speak in English to translate to Russian.")
        self.logger.info("Press Ctrl+C to stop.")
    
    def stop(self):
        """Stop the pipeline"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping speech translation pipeline...")
        self.is_running = False
        
        # Stop all components
        self.stt.stop_recording()
        self.translator.stop_translation()
        self.tts.stop_tts()
        self.audio_player.close()
        
        # Clear queues
        self._clear_queues()
        
        self.logger.info("Pipeline stopped")
    
    def _clear_queues(self):
        """Clear all queues"""
        while not self.stt_queue.empty():
            try:
                self.stt_queue.get_nowait()
            except queue.Empty:
                break
        
        while not self.translation_queue.empty():
            try:
                self.translation_queue.get_nowait()
            except queue.Empty:
                break
        
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_status(self) -> dict:
        """Get current pipeline status"""
        return {
            "is_running": self.is_running,
            "stt_queue_size": self.stt_queue.qsize(),
            "translation_queue_size": self.translation_queue.qsize(),
            "tts_queue_size": self.tts_queue.qsize(),
            "total_requests": self.request_counter
        }
    
    def process_file(self, audio_file_path: str):
        """Process an audio file through the pipeline"""
        self.logger.info(f"Processing audio file: {audio_file_path}")
        
        # Step 1: Speech-to-text
        english_text = self.stt.transcribe_file(audio_file_path)
        self.logger.info(f"STT result: {english_text}")
        
        if not english_text.strip():
            self.logger.warning("No speech detected in audio file")
            return
        
        # Step 2: Translation
        russian_text = self.translator.translate(english_text)
        self.logger.info(f"Translation result: {russian_text}")
        
        # Step 3: Text-to-speech
        audio_data = self.tts.synthesize(russian_text)
        self.logger.info(f"TTS generated: {len(audio_data)} audio samples")
        
        # Play the result
        if len(audio_data) > 0:
            self.audio_player.play(audio_data)
            self.logger.info("Audio playback completed")
        
        return {
            "english_text": english_text,
            "russian_text": russian_text,
            "audio_samples": len(audio_data)
        }


class PipelineMonitor:
    """Monitor pipeline performance and health"""
    
    def __init__(self, pipeline: SpeechTranslationPipeline):
        self.pipeline = pipeline
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: float = 5.0):
        """Start monitoring pipeline status"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def _monitor_loop(self, interval: float):
        """Monitoring loop"""
        while self.monitoring:
            status = self.pipeline.get_status()
            print(f"\n--- Pipeline Status ---")
            print(f"Running: {status['is_running']}")
            print(f"STT Queue: {status['stt_queue_size']}")
            print(f"Translation Queue: {status['translation_queue_size']}")
            print(f"TTS Queue: {status['tts_queue_size']}")
            print(f"Total Requests: {status['total_requests']}")
            print("------------------------\n")
            
            time.sleep(interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)


if __name__ == "__main__":
    # Main application
    print("=== Real-time Speech Translation System ===")
    print("English Speech → Russian Speech")
    print("========================================")
    
    # Initialize pipeline
    pipeline = SpeechTranslationPipeline(stt_model="base", enable_logging=True)
    
    # Optional: Start monitoring
    monitor = PipelineMonitor(pipeline)
    monitor.start_monitoring(interval=10.0)
    
    try:
        # Start real-time translation
        pipeline.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        pipeline.stop()
        monitor.stop_monitoring()
        print("System shutdown complete")
    
    except Exception as e:
        print(f"Error: {e}")
        pipeline.stop()
        monitor.stop_monitoring()
