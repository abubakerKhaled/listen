"""Audio playback module for Listen voice-to-text application."""

import io
import wave
import threading
from typing import Optional, Callable

import pyaudio

from .utils import suppress_alsa_errors


class AudioPlayer:
    """Play WAV audio data through speakers."""

    def __init__(self, on_complete: Optional[Callable[[], None]] = None):
        """
        Initialize the audio player.

        Args:
            on_complete: Optional callback when playback finishes
        """
        with suppress_alsa_errors():
            self._audio = pyaudio.PyAudio()

        self._stream: Optional[pyaudio.Stream] = None
        self._is_playing = False
        self._lock = threading.Lock()
        self._on_complete = on_complete
        self._playback_thread: Optional[threading.Thread] = None

    def set_on_complete(self, callback: Callable[[], None]) -> None:
        """Set the callback for when playback completes."""
        self._on_complete = callback

    def play(self, wav_data: bytes) -> None:
        """
        Play WAV audio data through speakers.

        Args:
            wav_data: WAV file contents as bytes
        """
        # Stop any current playback
        self.stop()

        # Start playback in background thread
        self._playback_thread = threading.Thread(
            target=self._play_audio, args=(wav_data,), daemon=True
        )
        self._playback_thread.start()

    def _play_audio(self, wav_data: bytes) -> None:
        """Play audio in background thread."""
        with self._lock:
            if self._is_playing:
                return
            self._is_playing = True

        try:
            buffer = io.BytesIO(wav_data)
            with wave.open(buffer, "rb") as wf:
                # Open output stream
                self._stream = self._audio.open(
                    format=self._audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                )

                # Read and play chunks
                chunk_size = 1024
                data = wf.readframes(chunk_size)

                while data and self._is_playing:
                    self._stream.write(data)
                    data = wf.readframes(chunk_size)

                # Clean up stream
                if self._stream:
                    self._stream.stop_stream()
                    self._stream.close()
                    self._stream = None

        except Exception:
            pass  # Silently handle playback errors
        finally:
            with self._lock:
                self._is_playing = False

            # Notify completion
            if self._on_complete:
                self._on_complete()

    def stop(self) -> None:
        """Stop current playback."""
        with self._lock:
            self._is_playing = False

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        return self._is_playing

    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        self.stop()
        if self._audio:
            self._audio.terminate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
