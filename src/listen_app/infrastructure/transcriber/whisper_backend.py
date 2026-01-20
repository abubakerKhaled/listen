"""Whisper-based implementation of TranscriberBackend.

Provides speech-to-text transcription with lazy model loading
and background preloading for better user experience.
"""

import io
import logging
import subprocess
import threading
from typing import Literal, Optional

from listen_app.core.transcriber_backend import TranscriberBackend, TranscriptionResult

logger = logging.getLogger(__name__)

# Available model sizes
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]


class WhisperBackend(TranscriberBackend):
    """Whisper-based transcription with lazy and background model loading.

    The model is not loaded until first transcription or when preload_model()
    is called. This enables fast application startup.
    """

    def __init__(
        self,
        model_size: Optional[ModelSize] = None,
        device: Literal["auto", "cpu", "cuda"] = "auto",
        compute_type: Optional[str] = None,
    ):
        """Initialize the Whisper backend.

        Args:
            model_size: Size of the Whisper model. If None, auto-selects.
            device: Device to run inference on ('auto', 'cpu', 'cuda')
            compute_type: Computation type (e.g., 'int8', 'float16')
        """
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type

        # Lazy loading state
        self._model = None
        self._loading = False
        self._load_lock = threading.Lock()
        self._load_thread: Optional[threading.Thread] = None

        # Resolved values after model load
        self._resolved_model_size: Optional[str] = None
        self._resolved_device: Optional[str] = None
        self._resolved_compute_type: Optional[str] = None

    def _detect_device(self) -> str:
        """Detect available compute device."""
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except ImportError:
            pass

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        return "cpu"

    def _get_gpu_memory(self) -> int:
        """Get available GPU memory in MB. Returns 0 if detection fails."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return int(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
        return 0

    def _detect_best_model(self, device: str) -> str:
        """Select optimal model based on device and available GPU memory."""
        if device != "cuda":
            return "tiny"

        vram_mb = self._get_gpu_memory()

        if vram_mb >= 4096:
            return "medium"
        elif vram_mb >= 2048:
            return "small"
        else:
            return "base"

    def _load_model(self) -> None:
        """Load the Whisper model (synchronously)."""
        logger.info("Loading Whisper model...")

        # Lazy import to avoid slow startup
        from faster_whisper import WhisperModel

        # Determine device
        device = self._device
        if device == "auto":
            device = self._detect_device()

        # Auto-select model based on device
        model_size = self._model_size
        if model_size is None:
            model_size = self._detect_best_model(device)

        # Auto-select compute type
        compute_type = self._compute_type
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"

        # Load model with CUDA fallback
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            error_str = str(e).lower()
            if "cuda" in error_str or "cublas" in error_str or "cudnn" in error_str:
                logger.warning("CUDA not available (%s), falling back to CPU", e)
                device = "cpu"
                compute_type = "int8"
                model_size = "tiny"
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
            else:
                raise

        self._model = model
        self._resolved_model_size = model_size
        self._resolved_device = device
        self._resolved_compute_type = compute_type

        logger.info(
            "Whisper model loaded: %s on %s (%s)",
            model_size,
            device,
            compute_type,
        )

    def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded, waiting for background thread if needed."""
        if self._load_thread:
            self._load_thread.join()
            self._load_thread = None

        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    self._load_model()

    def preload_model(self) -> None:
        """Start loading the model in background thread.

        Call this when recording starts so the model is ready
        when the user finishes recording.
        """
        with self._load_lock:
            if self._model is not None or self._loading:
                return
            self._loading = True

        def _background_load():
            try:
                self._load_model()
            except Exception as e:
                logger.exception("Failed to preload model: %s", e)
            finally:
                with self._load_lock:
                    self._loading = False

        self._load_thread = threading.Thread(target=_background_load, daemon=True)
        self._load_thread.start()
        logger.debug("Started background model preload")

    def is_model_loaded(self) -> bool:
        """Check if ML model is ready for transcription."""
        return self._model is not None

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Convert audio bytes to text.

        Args:
            audio_data: WAV file contents as bytes
            language: Optional language code (e.g., 'en', 'ar')

        Returns:
            TranscriptionResult with transcribed text
        """
        self._ensure_model_loaded()

        # Convert bytes to file-like object
        audio_source = io.BytesIO(audio_data)

        # Transcribe with optimized settings
        segments, info = self._model.transcribe(
            audio_source,
            language=language,
            beam_size=8,
            patience=1.5,
            condition_on_previous_text=False,
            vad_filter=True,
        )

        # Collect all text segments
        text_parts = [segment.text.strip() for segment in segments]
        full_text = " ".join(text_parts)

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=info.language_probability,
        )

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_size": self._resolved_model_size or self._model_size,
            "device": self._resolved_device or self._device,
            "compute_type": self._resolved_compute_type or self._compute_type,
            "loaded": self.is_model_loaded(),
        }
