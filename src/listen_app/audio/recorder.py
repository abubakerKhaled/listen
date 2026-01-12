"""Audio recording module for voice-to-text transcription."""

import io
import wave
import threading
from typing import Optional, Callable

import pyaudio

from .utils import suppress_alsa_errors


class AudioRecorder:
    """Records audio from the microphone with push-to-talk support."""

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
        """
        Initialize the audio recorder.

        Args:
            on_status_change: Optional callback for status updates (e.g., 'recording', 'stopped')
            on_audio_chunk: Optional callback for real-time audio data (for waveform display)
        """

        # Suppress ALSA error messages
        with suppress_alsa_errors():
            self._audio = pyaudio.PyAudio()

        self._stream: Optional[pyaudio.Stream] = None
        self._frames: list[bytes] = []
        self._is_recording = False
        self._lock = threading.Lock()
        self._on_status_change = on_status_change
        self._on_audio_chunk = on_audio_chunk

    def _notify_status(self, status: str) -> None:
        """Notify status change via callback if set."""
        if self._on_status_change:
            self._on_status_change(status)

    def start(self, input_device_index: Optional[int] = None) -> None:
        """Start recording audio from the microphone."""
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

    def resume(self, input_device_index: Optional[int] = None) -> None:
        """Resume recording without clearing existing frames."""
        with self._lock:
            if self._is_recording:
                return

            # Don't clear frames - keep existing audio
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

    def set_frames_from_wav(self, wav_data: bytes) -> None:
        """Set frames from WAV data to allow continuing recording."""
        import io
        import wave

        buffer = io.BytesIO(wav_data)
        with wave.open(buffer, "rb") as wf:
            # Read all audio data as raw frames
            raw_data = wf.readframes(wf.getnframes())
            # Split into chunks matching our chunk size
            chunk_bytes = self.CHUNK_SIZE * 2  # 2 bytes per sample (16-bit)
            self._frames = [
                raw_data[i : i + chunk_bytes]
                for i in range(0, len(raw_data), chunk_bytes)
            ]

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream - stores audio frames."""
        if self._is_recording:
            self._frames.append(in_data)
            if self._on_audio_chunk:
                self._on_audio_chunk(in_data)
        return (None, pyaudio.paContinue)

    def stop(self) -> bytes:
        """
        Stop recording and return the audio data as WAV bytes.

        Returns:
            WAV file contents as bytes
        """
        with self._lock:
            if not self._is_recording:
                return b""

            self._is_recording = False

            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

            self._notify_status("stopped")

            # Convert frames to WAV format in memory
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

    def save_to_file(self, filepath: str) -> None:
        """
        Save the last recording to a WAV file.

        Args:
            filepath: Path to save the WAV file
        """
        wav_data = self._frames_to_wav()
        with open(filepath, "wb") as f:
            f.write(wav_data)

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        if self._stream:
            self._stream.close()
        self._audio.terminate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
