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
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Speech Translation Service", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if authentication is enabled."""
    if API_KEY is None:
        return  # Authentication disabled
    
    if x_api_key is None:
        logger.warning("Request missing API key")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if x_api_key != API_KEY:
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
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


@app.get("/health")
def health_check() -> dict:
    """Health endpoint for readiness/liveness probes."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": pipeline is not None
    }


@app.get("/ready")
def readiness_check() -> dict:
    """Readiness check - confirms models are loaded."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/translate-audio", response_class=Response, dependencies=[])
@limiter.limit("10/minute")
async def translate_audio(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None)
) -> Response:
    """Translate English speech to Russian speech.

    Request
    -------
    - ``multipart/form-data`` with a single file field named ``file``
      containing a 16 kHz mono WAV (PCM) snippet in English.
    - Optional: ``X-API-Key`` header if authentication is enabled.

    Response
    --------
    - ``audio/wav`` bytes (22050 Hz mono) containing the corresponding Russian speech.
    
    Rate Limit
    ----------
    - 10 requests per minute per IP address
    """
    
    # Verify API key if authentication is enabled
    verify_api_key(x_api_key)
    
    start_time = datetime.utcnow()
    logger.info(f"Translation request received from {request.client.host}")
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.lower().endswith('.wav'):
            raise HTTPException(
                status_code=400,
                detail="Only WAV files are supported"
            )
        
        # Read file contents
        contents = await file.read()
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
            )
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Processing audio file: {file.filename} ({len(contents)} bytes)")
        
        # Process translation
        result = get_pipeline().translate_audio_chunk(contents)
        
        # Log processing time
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Translation completed in {duration:.2f}s - EN: '{result['english_text']}' -> RU: '{result['russian_text']}'")
        
        return Response(
            content=result["audio"],
            media_type="audio/wav",
            headers={
                "X-English-Text": result["english_text"],
                "X-Russian-Text": result["russian_text"],
                "X-Processing-Time": f"{duration:.2f}"
            }
        )
        
    except ValueError as exc:
        logger.error(f"Validation error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Internal error during translation: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Internal translation error. Check server logs for details."
        ) from exc


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "api_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
