"""
Real-time Speech Translation System
English Speech → English Text → Russian Text → Russian Audio
"""

__version__ = "1.0.0"
__author__ = "Speech Translation System"

from .main_pipeline import SpeechTranslationPipeline
from .stt_module import SpeechToText
from .translation_module import EnglishToRussianTranslator
from .tts_module import RussianTextToSpeech, AudioPlayer

__all__ = [
    "SpeechTranslationPipeline",
    "SpeechToText", 
    "EnglishToRussianTranslator",
    "RussianTextToSpeech",
    "AudioPlayer"
]
