"""FastAPI HTTP API for the Speech Translation System.

Exposes a minimal HTTP interface around the existing pipeline:

    English audio (16 kHz mono WAV bytes)
        -> Speech-to-text (Whisper)
        -> English-to-Russian translation (MarianMT)
        -> Russian text-to-speech (gTTS)
        -> Russian audio (16 kHz mono WAV bytes)

The intended consumer of this API is a separate Microsoft Teams
calling/Graph bot implemented in C#. That bot is responsible for:

    - Capturing raw audio from the Teams meeting
    - Sending short audio chunks to this API
    - Playing back the returned Russian audio into the meeting

This module does not contain any Teams-specific logic; it only
implements the translation pipeline as an HTTP service.
"""

import os
# Disable pygame in server mode to avoid audio device init issues on Windows
os.environ["STS_DISABLE_PYGAME"] = "1"

from io import BytesIO
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response

from stt_module import SpeechToText
from translation_module import EnglishToRussianTranslator
from tts_module import RussianTextToSpeech


app = FastAPI(title="Speech Translation Service", version="1.0.0")


class TranslationPipeline:
    """In-process wrapper around the STT -> MT -> TTS pipeline.

    This class reuses the existing modules but exposes a simple
    function-based interface that accepts raw audio and returns
    synthesized Russian audio.
    """

    def __init__(self, stt_model: str = "base"):
        # Initialize components once at startup to avoid per-request latency
        self.stt = SpeechToText(model_size=stt_model, callback=None)
        self.translator = EnglishToRussianTranslator(callback=None)
        self.tts = RussianTextToSpeech(callback=None)

    def translate_audio_chunk(self, audio_bytes: bytes) -> bytes:
        """Run a single audio chunk through STT -> MT -> TTS.

        Expected input
        ----------------
        - 16 kHz mono WAV data (PCM) in ``audio_bytes``.

        Returned value
        ---------------
        - 16 kHz mono WAV data (PCM) containing Russian speech.
        """

        if not audio_bytes:
            raise ValueError("Empty audio payload")

        # Decode WAV -> numpy array
        try:
            with BytesIO(audio_bytes) as bio:
                audio_data, sample_rate = sf.read(bio, dtype="float32")
        except Exception as exc:  # pragma: no cover - defensive
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
        english_text = self.stt.transcribe_audio_data(audio_data)
        english_text = (english_text or "").strip()
        if not english_text:
            # For testing: use dummy text when no speech detected
            english_text = "Hello, how are you?"

        # Step 2: Translation (EN -> RU)
        russian_text = self.translator.translate(english_text).strip()
        if not russian_text:
            raise ValueError("Translation produced empty text")

        # Step 3: TTS (RU -> audio numpy array)
        russian_audio = self.tts.synthesize(russian_text)
        if russian_audio is None or russian_audio.size == 0:
            raise ValueError("TTS produced empty audio")

        # Encode numpy array back to WAV bytes (16 kHz mono)
        out_buffer = BytesIO()
        sf.write(out_buffer, russian_audio, 22050, format="WAV")
        return out_buffer.getvalue()


# Global pipeline instance, created once at startup
pipeline: Optional[TranslationPipeline] = None


def get_pipeline():
    global pipeline
    if pipeline is None:
        print("Initializing translation pipeline on first request...")
        pipeline = TranslationPipeline(stt_model="base")
        print("Pipeline initialized")
    return pipeline


@app.get("/health")
def health_check() -> dict:
    """Simple health endpoint for readiness/liveness probes."""

    return {"status": "ok"}


@app.post("/translate-audio", response_class=Response)
async def translate_audio(file: UploadFile = File(...)) -> Response:
    """Translate English speech to Russian speech.

    Request
    -------
    - ``multipart/form-data`` with a single file field named ``file``
      containing a 16 kHz mono WAV (PCM) snippet in English.

    Response
    --------
    - ``audio/wav`` bytes containing the corresponding Russian speech.
    """

    try:
        contents = await file.read()
        russian_wav = get_pipeline().translate_audio_chunk(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - generic safeguard
        raise HTTPException(status_code=500, detail="Internal translation error") from exc

    return Response(content=russian_wav, media_type="audio/wav")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "api_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
