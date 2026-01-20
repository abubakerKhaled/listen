"""Transcription handling for Listen GUI."""

import threading
import time
from typing import Optional, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

from ...core.transcriber_backend import TranscriberBackend


class TranscriptionHandler:
    """Handles model loading and transcription operations."""

    def __init__(
        self,
        transcriber: TranscriberBackend,
        on_model_ready: Optional[Callable[[dict], None]] = None,
        on_model_error: Optional[Callable[[str], None]] = None,
        on_transcription_complete: Optional[Callable[[str, str, bytes], None]] = None,
    ):
        """Initialize transcription handler.

        Args:
            transcriber: Backend for transcription
            on_model_ready: Callback(info_dict) when model is loaded
            on_model_error: Callback(error_msg) on model load error
            on_transcription_complete: Callback(text, language, audio_data)
        """
        self.transcriber = transcriber
        self._on_model_ready = on_model_ready
        self._on_model_error = on_model_error
        self._on_transcription_complete = on_transcription_complete

    def preload_model(self) -> None:
        """Start preloading the model in a background thread."""
        threading.Thread(target=self._preload_model_sync, daemon=True).start()

    def _preload_model_sync(self) -> None:
        """Preload model synchronously (runs in background thread)."""
        try:
            self.transcriber.preload_model()

            # Wait for model to load
            while not self.transcriber.is_model_loaded():
                time.sleep(0.1)

            info = self.transcriber.get_model_info()

            if self._on_model_ready:
                GLib.idle_add(self._on_model_ready, info)

        except Exception as e:
            if self._on_model_error:
                GLib.idle_add(self._on_model_error, str(e))

    def transcribe(self, audio_data: bytes, auto_copy: bool = False) -> None:
        """Transcribe audio in background thread.

        Args:
            audio_data: WAV audio bytes
            auto_copy: Whether to copy result to clipboard
        """
        threading.Thread(
            target=self._transcribe_sync,
            args=(audio_data, auto_copy),
            daemon=True,
        ).start()

    def _transcribe_sync(self, audio_data: bytes, auto_copy: bool) -> None:
        """Transcribe synchronously (runs in background thread)."""
        try:
            result = self.transcriber.transcribe(audio_data)
            text = result.text.strip()
            language = result.language or ""

            if auto_copy and text:
                import pyperclip

                pyperclip.copy(text)

            if self._on_transcription_complete:
                GLib.idle_add(
                    self._on_transcription_complete, text, language, audio_data
                )

        except Exception as e:
            if self._on_transcription_complete:
                GLib.idle_add(
                    self._on_transcription_complete, f"Error: {e}", "", audio_data
                )

    @staticmethod
    def format_device_info(info: dict) -> str:
        """Format device info for display."""
        device = info.get("device", "cpu")
        compute = info.get("compute_type", "int8")
        model = (info.get("model_size") or "base").upper()

        if device == "cuda" and info.get("gpu_name"):
            gpu_name = info["gpu_name"]
            memory = info.get("gpu_memory_mb", 0)
            cuda_ver = info.get("cuda_version", "N/A")

            return (
                f"<span color='#76b900'>🟢 GPU</span>  <b>{gpu_name}</b>\n"
                f"    Memory: {memory} MB │ CUDA: {cuda_ver}\n"
                f"    Model: {model} │ Precision: {compute}"
            )
        else:
            return (
                f"<span color='#0071c5'>🔵 CPU</span>  Inference Mode\n"
                f"    Model: {model} │ Precision: {compute}\n"
                f"    <span color='#888'>Tip: Install CUDA for faster processing</span>"
            )

    @staticmethod
    def get_language_name(code: str) -> str:
        """Convert language code to display name."""
        names = {
            "ar": "Arabic",
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
        }
        return names.get(code, code.upper() if code else "")
