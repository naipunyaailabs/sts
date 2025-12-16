"""FastAPI HTTP API for the Speech Translation System.

Exposes a minimal HTTP interface around the existing pipeline:

    English audio (16 kHz mono WAV bytes)
        -> Speech-to-text (Whisper)
        -> English-to-Russian translation (MarianMT)
        -> Russian text-to-speech (gTTS)
        -> Russian audio (22050 Hz mono WAV bytes)

The intended consumer of this API is a separate Microsoft Teams
calling/Graph bot implemented in C#. That bot is responsible for:

    - Capturing raw audio from the Teams meeting
    - Sending short audio chunks to this API
    - Playing back the returned Russian audio into the meeting

This module does not contain any Teams-specific logic; it only
implements the translation pipeline as an HTTP service.
"""

import os
import logging
from datetime import datetime
# Disable pygame in server mode to avoid audio device init issues on Windows
os.environ["STS_DISABLE_PYGAME"] = "1"

from io import BytesIO
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from stt_module import SpeechToText
from translation_module import EnglishToRussianTranslator
from tts_module import RussianTextToSpeech

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sts_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Speech Translation Service", version="2.0.0")

# API Key from environment variable
API_KEY = os.getenv("STS_API_KEY", None)
if API_KEY:
    logger.info("API key authentication enabled")
else:
    logger.warning("API key authentication disabled - set STS_API_KEY environment variable for security")

# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class TranslationPipeline:
    """In-process wrapper around the STT -> MT -> TTS pipeline.

    This class reuses the existing modules but exposes a simple
    function-based interface that accepts raw audio and returns
    synthesized Russian audio.
    """

    def __init__(self, stt_model: str = "base"):
        logger.info(f"Initializing TranslationPipeline with STT model: {stt_model}")
        # Initialize components once at startup to avoid per-request latency
        self.stt = SpeechToText(model_size=stt_model, callback=None)
        self.translator = EnglishToRussianTranslator(callback=None)
        self.tts = RussianTextToSpeech(callback=None)
        logger.info("TranslationPipeline initialization complete")

    def translate_audio_chunk(self, audio_bytes: bytes) -> dict:
        """Run a single audio chunk through STT -> MT -> TTS.

        Expected input
        ----------------
        - 16 kHz mono WAV data (PCM) in ``audio_bytes``.

        Returned value
        ---------------
        - Dictionary containing:
            - audio: 22050 Hz mono WAV data (PCM) containing Russian speech
            - english_text: Transcribed English text
            - russian_text: Translated Russian text
        """

        if not audio_bytes:
            raise ValueError("Empty audio payload")

        # Decode WAV -> numpy array
        try:
            with BytesIO(audio_bytes) as bio:
                audio_data, sample_rate = sf.read(bio, dtype="float32")
        except Exception as exc:
            logger.error(f"Failed to decode audio: {exc}")
            raise ValueError(f"Failed to decode audio: {exc}") from exc

        if sample_rate != 16000:
            raise ValueError(f"Expected 16 kHz audio, got {sample_rate} Hz")

        # Ensure mono float32
        audio_data = np.asarray(audio_data, dtype=np.float32)
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        if audio_data.size == 0:
            raise ValueError("Decoded audio is empty")

        # Step 1: STT (English)
        logger.info("Starting speech-to-text transcription")
        english_text = self.stt.transcribe_audio_data(audio_data)
        english_text = (english_text or "").strip()
        if not english_text:
            logger.warning("No speech detected in audio, using placeholder")
            english_text = "Hello, how are you?"
        
        logger.info(f"Transcribed text: {english_text}")

        # Step 2: Translation (EN -> RU)
        logger.info("Starting translation")
        russian_text = self.translator.translate(english_text).strip()
        if not russian_text:
            raise ValueError("Translation produced empty text")
        
        logger.info(f"Translated text: {russian_text}")

        # Step 3: TTS (RU -> audio numpy array)
        logger.info("Starting text-to-speech synthesis")
        russian_audio = self.tts.synthesize(russian_text)
        if russian_audio is None or russian_audio.size == 0:
            raise ValueError("TTS produced empty audio")

        # Encode numpy array back to WAV bytes (22050 Hz mono, matching gTTS output)
        out_buffer = BytesIO()
        sf.write(out_buffer, russian_audio, 22050, format="WAV")
        
        return {
            "audio": out_buffer.getvalue(),
            "english_text": english_text,
            "russian_text": russian_text
        }


# Global pipeline instance, initialized at startup
pipeline: Optional[TranslationPipeline] = None


def get_pipeline():
    """Get or initialize the translation pipeline."""
    global pipeline
    if pipeline is None:
        logger.info("Initializing translation pipeline...")
        stt_model = os.getenv("STT_MODEL", "base")
        pipeline = TranslationPipeline(stt_model=stt_model)
        logger.info("Pipeline initialized successfully")
    return pipeline


def verify_api_key(api_key: Optional[str]):
    """Verify API key for WebSocket connections if authentication is enabled."""
    if API_KEY is None:
        return  # Authentication disabled
    
    if api_key is None:
        logger.warning("Request missing API key")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if api_key != API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )


@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup for faster first request."""
    logger.info("Starting up STS API service")
    if os.getenv("EAGER_LOAD", "true").lower() == "true":
        logger.info("Eager loading models...")
        get_pipeline()
        logger.info("Models loaded and ready")
    else:
        logger.info("Lazy loading enabled - models will load on first request")


@app.websocket("/ws/translate-audio")
async def websocket_translate_audio(websocket: WebSocket):
    """WebSocket endpoint for live audio translation.

    Expected client behavior
    ------------------------
    - Connect to: ``/ws/translate-audio?api_key=YOUR_KEY`` when API key auth is enabled.
    - Send binary messages containing 16 kHz mono WAV (PCM) snippets of English speech.
    - For each binary message received, the server responds with:
        1) a binary message containing the translated Russian audio (22050 Hz mono WAV), and
        2) a JSON text message with ``english_text`` and ``russian_text``.
    """

    # API key (if enabled) is passed as a query parameter for WebSocket connections
    api_key = websocket.query_params.get("api_key")
    try:
        verify_api_key(api_key)
    except HTTPException:
        # Close connection with policy violation code if auth fails
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info(f"WebSocket client connected from {websocket.client.host if websocket.client else 'unknown'}")

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # Expect binary frames containing WAV bytes
            audio_bytes = message.get("bytes")
            if not audio_bytes:
                # Ignore non-binary or empty messages
                continue

            start_time = datetime.utcnow()

            try:
                result = get_pipeline().translate_audio_chunk(audio_bytes)
                duration = (datetime.utcnow() - start_time).total_seconds()

                # First, send the synthesized Russian audio as binary
                await websocket.send_bytes(result["audio"])

                # Then, send metadata (texts and processing time) as JSON
                await websocket.send_json(
                    {
                        "english_text": result["english_text"],
                        "russian_text": result["russian_text"],
                        "processing_time": duration,
                    }
                )

                logger.info(
                    "WS translation completed in %.2fs - EN: '%s' -> RU: '%s'",
                    duration,
                    result["english_text"],
                    result["russian_text"],
                )

            except ValueError as exc:
                logger.error(f"WebSocket validation error: {exc}")
                await websocket.send_json({"error": str(exc)})
            except Exception as exc:  # pragma: no cover - unexpected runtime issues
                logger.exception(f"WebSocket internal error during translation: {exc}")
                await websocket.send_json(
                    {
                        "error": "Internal translation error. Check server logs for details.",
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:  # pragma: no cover - unexpected runtime issues
        logger.exception(f"Unexpected WebSocket error: {exc}")
    finally:
        try:
            await websocket.close()
        except Exception:
            # Ignore errors while closing
            pass




if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "api_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
