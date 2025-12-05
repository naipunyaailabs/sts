"""
Translation Module using MarianMT (Helsinki-NLP)
Translates English text to Russian
"""

import torch
from transformers import MarianMTModel, MarianTokenizer
import threading
import queue
import time
from typing import Optional, Callable


class EnglishToRussianTranslator:
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize MarianMT model for English to Russian translation
        
        Args:
            callback: Function to call when translation is ready
        """
        self.callback = callback
        self.model = None
        self.tokenizer = None
        self.translation_queue = queue.Queue()
        self.is_translating = False
        self.translation_thread = None
        
        # Load model
        self._load_model()
    
    def _load_model(self):
        """Load MarianMT model for English to Russian"""
        model_name = "Helsinki-NLP/opus-mt-en-ru"
        print(f"Loading translation model: {model_name}")
        
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)
        
        print("Translation model loaded successfully")
    
    def _process_translations(self):
        """Process translation requests in background"""
        while self.is_translating or not self.translation_queue.empty():
            try:
                # Get translation request
                text, request_id = self.translation_queue.get(timeout=0.1)
                
                # Translate
                translated_text = self.translate(text)
                
                # Call callback if provided
                if self.callback:
                    self.callback(translated_text, request_id)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in translation: {e}")
    
    def translate_async(self, text: str, request_id: str = None):
        """Translate text asynchronously"""
        if not self.is_translating:
            self.is_translating = True
            self.translation_thread = threading.Thread(target=self._process_translations)
            self.translation_thread.daemon = True
            self.translation_thread.start()
        
        self.translation_queue.put((text, request_id))
    
    def translate(self, text: str) -> str:
        """
        Translate English text to Russian
        
        Args:
            text: English text to translate
            
        Returns:
            Russian translation
        """
        if not text.strip():
            return ""
        
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        
        # Generate translation
        with torch.no_grad():
            translated = self.model.generate(**inputs, max_length=512, num_beams=4, 
                                           early_stopping=True, temperature=0.7)
        
        # Decode and return
        translated_text = self.tokenizer.decode(translated[0], skip_special_tokens=True)
        return translated_text.strip()
    
    def translate_batch(self, texts: list) -> list:
        """Translate multiple texts at once"""
        translations = []
        for text in texts:
            translation = self.translate(text)
            translations.append(translation)
        return translations
    
    def stop_translation(self):
        """Stop translation processing"""
        self.is_translating = False
        if self.translation_thread:
            self.translation_thread.join(timeout=1.0)


class LanguageDetector:
    """Simple language detection for validation"""
    
    @staticmethod
    def is_english(text: str) -> bool:
        """Simple check if text is likely English"""
        english_words = ['the', 'and', 'is', 'to', 'a', 'in', 'that', 'have', 'i', 
                        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at']
        words = text.lower().split()
        if not words:
            return False
        
        english_count = sum(1 for word in words if word in english_words)
        return english_count / len(words) > 0.3  # At least 30% common English words


if __name__ == "__main__":
    # Test the translation module
    def translation_callback(translated_text, request_id):
        print(f"Translated ({request_id}): {translated_text}")
    
    translator = EnglishToRussianTranslator(callback=translation_callback)
    
    # Test translations
    test_texts = [
        "Hello, how are you?",
        "I would like to order some food",
        "What time is it?",
        "Thank you very much"
    ]
    
    print("Testing translations:")
    for i, text in enumerate(test_texts):
        print(f"English: {text}")
        translation = translator.translate(text)
        print(f"Russian: {translation}")
        print("-" * 50)
