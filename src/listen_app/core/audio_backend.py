"""Abstract interface for audio recording and playback."""

from abc import ABC, abstractmethod
from typing import Callable, Optional


class AudioBackend(ABC):
    """Abstract interface for audio recording and playback.

    Implementations should handle:
    - Recording audio from microphone
    - Playing back audio through speakers
    - Proper cleanup of audio resources
    """

    @abstractmethod
    def start_recording(self) -> None:
        """Begin capturing audio from microphone."""
        ...

    @abstractmethod
    def stop_recording(self) -> bytes:
        """Stop recording and return WAV data.

        Returns:
            bytes: WAV file contents
        """
        ...

    @abstractmethod
    def get_audio_data(self) -> bytes:
        """Get the current recorded audio data without stopping.

        Returns:
            bytes: WAV file contents of current recording
        """
        ...

    @abstractmethod
    def play(
        self, wav_data: bytes, on_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Play audio through speakers.

        Args:
            wav_data: WAV file contents as bytes
            on_complete: Optional callback when playback finishes
        """
        ...

    @abstractmethod
    def stop_playback(self) -> None:
        """Stop current playback."""
        ...

    @abstractmethod
    def is_recording(self) -> bool:
        """Check if currently recording."""
        ...

    @abstractmethod
    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        ...

    @abstractmethod
    def terminate(self) -> None:
        """Clean up audio resources."""
        ...
