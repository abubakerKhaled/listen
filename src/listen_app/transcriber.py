"""Speech-to-text transcription module using faster-whisper."""

import io
from dataclasses import dataclass
from typing import Optional, Literal

from faster_whisper import WhisperModel


# Model recommendations based on compute device
MODEL_RECOMMENDATIONS = {
    "cpu": "tiny",  # Fast, low memory for CPU
    "cuda": "base",  # Good balance for GPU (CUDA)
}

# Available model sizes
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""

    text: str
    language: str
    language_probability: float
    duration: float  # Audio duration in seconds

    def __str__(self) -> str:
        return self.text


class Transcriber:
    """Transcribes audio to text using faster-whisper."""

    def __init__(
        self,
        model_size: Optional[ModelSize] = None,
        device: Literal["auto", "cpu", "cuda"] = "auto",
        compute_type: Optional[str] = None,
    ):
        """
        Initialize the transcriber with a Whisper model.

        Args:
            model_size: Size of the Whisper model to use. If None, auto-selects
                        based on device (tiny for CPU, base for GPU)
            device: Device to run inference on ('auto', 'cpu', 'cuda')
            compute_type: Computation type (e.g., 'int8', 'float16', 'float32').
                          If None, auto-selects based on device.
        """
        # Determine device
        if device == "auto":
            device = self._detect_device()

        # Auto-select model if not specified
        if model_size is None:
            model_size = MODEL_RECOMMENDATIONS.get(device, "tiny")

        # Auto-select compute type
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        # Load the model with fallback to CPU if CUDA libraries are missing
        try:
            self._model = WhisperModel(
                model_size, device=device, compute_type=compute_type
            )
        except Exception as e:
            error_str = str(e).lower()
            if "cuda" in error_str or "cublas" in error_str or "cudnn" in error_str:
                # CUDA libraries not available, fall back to CPU
                print(
                    f"Warning: CUDA libraries not available ({e}), falling back to CPU"
                )
                self.device = "cpu"
                self.compute_type = "int8"
                self.model_size = MODEL_RECOMMENDATIONS.get("cpu", "tiny")
                self._model = WhisperModel(
                    self.model_size, device="cpu", compute_type="int8"
                )
            else:
                raise

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

    def transcribe(
        self, audio_source: str | bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio_source: Either a file path (str) or WAV audio data (bytes)
            language: Optional language code (e.g., 'en', 'ar'). If None, auto-detects.

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        # Handle bytes input by writing to a temporary buffer
        if isinstance(audio_source, bytes):
            audio_source = io.BytesIO(audio_source)

        # Transcribe
        segments, info = self._model.transcribe(
            audio_source,
            language=language,
            beam_size=5,
            vad_filter=True,  # Filter out silence
        )

        # Collect all text segments
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts)

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
        )

    def get_model_info(self) -> dict:
        """Get detailed information about the loaded model and device."""
        info = {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "gpu_name": None,
            "gpu_memory_mb": None,
            "cuda_version": None,
            "driver_version": None,
        }

        if self.device == "cuda":
            # Try to get GPU details
            try:
                import subprocess

                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,memory.total,driver_version",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(", ")
                    if len(parts) >= 3:
                        info["gpu_name"] = parts[0].strip()
                        info["gpu_memory_mb"] = int(parts[1].strip())
                        info["driver_version"] = parts[2].strip()

                # Get CUDA version
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=driver_version",
                        "--format=csv,noheader",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # CUDA version from nvidia-smi header
                result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "CUDA Version:" in line:
                            cuda_part = line.split("CUDA Version:")[1].strip()
                            info["cuda_version"] = cuda_part.split()[0].strip()
                            break
            except Exception:
                pass  # Fallback silently if nvidia-smi fails

        return info
