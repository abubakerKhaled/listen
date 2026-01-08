"""Speech-to-text transcription module using faster-whisper."""

import io
import os
from dataclasses import dataclass
from typing import Optional, Literal

from faster_whisper import WhisperModel


# Model recommendations based on compute type
MODEL_RECOMMENDATIONS = {
    "cpu": "tiny",  # Fast, low memory for CPU
    "gpu": "base",  # Good balance for GPU
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

        # Load the model
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def _detect_device(self) -> str:
        """Detect available compute device."""
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
        """Get information about the loaded model."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
        }


if __name__ == "__main__":
    import sys

    # Test with an audio file
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <audio_file.wav>")
        print("Testing with model loading only...")

        transcriber = Transcriber()
        print(f"Model loaded: {transcriber.get_model_info()}")
    else:
        audio_file = sys.argv[1]
        print(f"Transcribing {audio_file}...")

        transcriber = Transcriber()
        result = transcriber.transcribe(audio_file)

        print(f"\nTranscription: {result.text}")
        print(f"Language: {result.language} ({result.language_probability:.1%})")
        print(f"Duration: {result.duration:.1f}s")
