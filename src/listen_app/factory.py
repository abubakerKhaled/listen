"""Factory module for creating backend instances.

Provides convenient factory functions to create properly configured
audio and transcriber backends.
"""

from typing import Literal, Optional

from listen_app.core.audio_backend import AudioBackend
from listen_app.core.transcriber_backend import TranscriberBackend


def create_audio_backend(**kwargs) -> AudioBackend:
    """Create an audio backend instance.

    Args:
        **kwargs: Arguments passed to PyAudioBackend constructor

    Returns:
        AudioBackend implementation
    """
    from listen_app.infrastructure.audio.pyaudio_backend import PyAudioBackend

    return PyAudioBackend(**kwargs)


def create_transcriber(
    model_size: Optional[str] = None,
    device: Literal["auto", "cpu", "cuda"] = "auto",
    compute_type: Optional[str] = None,
) -> TranscriberBackend:
    """Create a transcriber backend instance.

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large-v3)
        device: Device to run on (auto, cpu, cuda)
        compute_type: Computation type (int8, float16, etc.)

    Returns:
        TranscriberBackend implementation
    """
    from listen_app.infrastructure.transcriber.whisper_backend import WhisperBackend

    return WhisperBackend(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
    )
