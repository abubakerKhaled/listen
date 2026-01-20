"""Audio package for Listen voice-to-text application.

Note: AudioRecorder and AudioPlayer have been replaced by the unified
AudioBackend interface in listen_app.core.audio_backend.
"""

from .utils import suppress_alsa_errors

__all__ = ["suppress_alsa_errors"]
