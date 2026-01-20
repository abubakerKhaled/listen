"""Listen - Voice-to-text transcription tool for Linux."""

__version__ = "1.0.0"

# Export abstract interfaces
from .core.audio_backend import AudioBackend
from .core.transcriber_backend import TranscriberBackend, TranscriptionResult

# Export factory functions
from .factory import create_audio_backend, create_transcriber

__all__ = [
    "AudioBackend",
    "TranscriberBackend",
    "TranscriptionResult",
    "create_audio_backend",
    "create_transcriber",
    "__version__",
]
