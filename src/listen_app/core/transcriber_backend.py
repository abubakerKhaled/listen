"""Abstract interface for speech-to-text transcription."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptionResult:
    """Result of a transcription operation.

    Attributes:
        text: The transcribed text
        language: Detected language code (e.g., 'en', 'ar')
        confidence: Overall confidence score (0.0 to 1.0)
    """

    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


class TranscriberBackend(ABC):
    """Abstract interface for speech-to-text transcription.

    Implementations should support:
    - Lazy loading of ML models
    - Background preloading for better UX
    - Thread-safe operations
    """

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        """Convert audio bytes to text.

        Args:
            audio_data: WAV file contents as bytes

        Returns:
            TranscriptionResult with transcribed text
        """
        ...

    @abstractmethod
    def is_model_loaded(self) -> bool:
        """Check if ML model is ready for transcription."""
        ...

    @abstractmethod
    def preload_model(self) -> None:
        """Start loading the model in background thread.

        Call this when recording starts to have the model ready
        by the time the user finishes recording.
        """
        ...
