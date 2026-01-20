"""Core package containing abstract interfaces for Listen application."""

from .audio_backend import AudioBackend
from .transcriber_backend import TranscriberBackend, TranscriptionResult

__all__ = ["AudioBackend", "TranscriberBackend", "TranscriptionResult"]
