"""GUI package for Listen voice-to-text application."""

from typing import Optional

from ..transcriber import ModelSize
from .app import ListenGUI
from .widgets import WaveformDrawingArea

__all__ = ["ListenGUI", "WaveformDrawingArea", "run_gui"]


def run_gui(model_size: Optional[ModelSize] = None, auto_copy: bool = True):
    """Entry point for GUI mode."""
    app = ListenGUI(model_size=model_size, auto_copy=auto_copy)
    app.run_app()
