"""Placeholder for an HTTP wrapper around the STS pipeline.

The HTTP/FastAPI integration has been disabled at your request, so this
module currently exposes only a minimal stub.
"""


class HttpSpeechPipeline:
    """Disabled HTTP pipeline stub.

    This class is kept only to avoid import errors in any leftover references.
    It does not perform any real translation.
    """

    def __init__(self, *_, **__):
        raise RuntimeError("HttpSpeechPipeline is disabled. Use main_pipeline.py instead.")
