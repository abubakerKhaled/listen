"""PyAudio-based implementation of AudioBackend.

Combines recording and playback using PyAudio library.
"""

import io
import logging
import threading
import wave
from typing import Callable, Optional

import pyaudio

from listen_app.core.audio_backend import AudioBackend

logger = logging.getLogger(__name__)


def _suppress_alsa_errors():
    """Context manager to suppress ALSA error messages to stderr."""
    import os
    from contextlib import contextmanager

    @contextmanager
    def suppressor():
        null_fd = -1
        saved_stderr_fd = -1
        try:
            null_fd = os.open(os.devnull, os.O_RDWR)
            saved_stderr_fd = os.dup(2)
            os.dup2(null_fd, 2)
            yield
        except Exception:
            yield
        finally:
            if saved_stderr_fd >= 0:
                os.dup2(saved_stderr_fd, 2)
                os.close(saved_stderr_fd)
            if null_fd >= 0:
                os.close(null_fd)

    return suppressor()


class PyAudioBackend(AudioBackend):
    """PyAudio-based implementation for recording and playback.

    Implements the AudioBackend interface using PyAudio for
    microphone recording and speaker playback.
    """

    # Whisper expects 16kHz mono audio
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 1024
    FORMAT = pyaudio.paInt16

    def __init__(
        self,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
    ):
        """Initialize the audio backend.

        Args:
            on_status_change: Optional callback for status updates
            on_audio_chunk: Optional callback for real-time audio data
        """
        with _suppress_alsa_errors():
            self._audio = pyaudio.PyAudio()

        self._stream: Optional[pyaudio.Stream] = None
        self._frames: list[bytes] = []
        self._is_recording = False
        self._is_playing = False
        self._lock = threading.Lock()
        self._on_status_change = on_status_change
        self._on_audio_chunk = on_audio_chunk
        self._on_complete: Optional[Callable[[], None]] = None
        self._playback_thread: Optional[threading.Thread] = None

    def _notify_status(self, status: str) -> None:
        """Notify status change via callback if set."""
        if self._on_status_change:
            self._on_status_change(status)


    def start_recording(self, input_device_index: Optional[int] = None) -> None:
        """Begin capturing audio from microphone."""
        with self._lock:
            if self._is_recording:
                return

            self._frames = []
            self._is_recording = True

            self._stream = self._audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=self._audio_callback,
            )
            self._stream.start_stream()
            self._notify_status("recording")
            logger.debug("Started recording")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream - stores audio frames."""
        if self._is_recording:
            self._frames.append(in_data)
            if self._on_audio_chunk:
                self._on_audio_chunk(in_data)
        return (None, pyaudio.paContinue)

    def stop_recording(self) -> bytes:
        """Stop recording and return WAV data."""
        with self._lock:
            if not self._is_recording:
                return b""

            self._is_recording = False

            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

            self._notify_status("stopped")
            logger.debug("Stopped recording")

            return self._frames_to_wav()

    def get_audio_data(self) -> bytes:
        """Get the current recorded audio data without stopping."""
        return self._frames_to_wav()

    def _frames_to_wav(self) -> bytes:
        """Convert recorded frames to WAV format bytes."""
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self._audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b"".join(self._frames))

        return buffer.getvalue()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def play(
        self, wav_data: bytes, on_complete: Optional[Callable[[], None]] = None
    ) -> None:
        """Play audio through speakers."""
        self.stop_playback()
        self._on_complete = on_complete

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
                stream = self._audio.open(
                    format=self._audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                )

                chunk_size = 1024
                data = wf.readframes(chunk_size)

                while data and self._is_playing:
                    stream.write(data)
                    data = wf.readframes(chunk_size)

                stream.stop_stream()
                stream.close()

        except Exception as e:
            logger.exception("Playback error: %s", e)
        finally:
            with self._lock:
                self._is_playing = False

            if self._on_complete:
                self._on_complete()

    def stop_playback(self) -> None:
        """Stop current playback."""
        with self._lock:
            self._is_playing = False

    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        return self._is_playing

    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        self.stop_playback()
        if self._stream:
            self._stream.close()
        if self._audio:
            self._audio.terminate()
        logger.debug("Audio backend terminated")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
