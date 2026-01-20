"""State machine for Listen GUI recording workflow."""

from enum import Enum, auto
from typing import Optional, Callable
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class RecordingState(Enum):
    """States for the recording workflow."""

    READY = auto()  # Ready to record
    RECORDING = auto()  # Currently recording
    RECORDED = auto()  # Recording stopped, preview available
    TRANSCRIBING = auto()  # Processing audio
    RESULT = auto()  # Showing transcription result


@dataclass
class UIWidgets:
    """Widget references needed for state updates."""

    action_button: Gtk.Button
    recorded_button_box: Gtk.Box
    play_button: Gtk.Button
    result_play_button: Gtk.Button
    regenerate_button: Gtk.Button
    status_label: Gtk.Label
    result_label: Gtk.Label
    waveform: object  # WaveformDrawingArea


class StateMachine:
    """Manages state transitions and corresponding UI updates."""

    def __init__(self, widgets: UIWidgets):
        self.widgets = widgets
        self._state = RecordingState.READY

    @property
    def state(self) -> RecordingState:
        return self._state

    def is_ready(self) -> bool:
        return self._state == RecordingState.READY

    def is_recording(self) -> bool:
        return self._state == RecordingState.RECORDING

    def is_recorded(self) -> bool:
        return self._state == RecordingState.RECORDED

    def is_transcribing(self) -> bool:
        return self._state == RecordingState.TRANSCRIBING

    def is_result(self) -> bool:
        return self._state == RecordingState.RESULT

    # -------------------------------------------------------------------------
    # State Transitions
    # -------------------------------------------------------------------------

    def to_recording(self) -> None:
        """Transition to recording state."""
        self._state = RecordingState.RECORDING

        w = self.widgets
        w.action_button.set_label("⏹️ Stop")
        w.action_button.set_visible(True)
        w.action_button.remove_css_class("suggested-action")
        w.action_button.add_css_class("destructive-action")
        w.regenerate_button.set_visible(False)
        w.result_play_button.set_visible(False)
        w.recorded_button_box.set_visible(False)
        w.status_label.set_text("Recording... Click Stop when finished")
        w.result_label.set_text("")
        w.waveform.clear()

    def to_recorded(self) -> None:
        """Transition to recorded state (preview available)."""
        self._state = RecordingState.RECORDED

        w = self.widgets
        w.action_button.set_visible(False)
        w.recorded_button_box.set_visible(True)
        w.play_button.set_label("▶️ Play")
        w.status_label.set_text("Review your recording • Play, Transcribe, or Discard")

    def to_transcribing(self) -> None:
        """Transition to transcribing state."""
        self._state = RecordingState.TRANSCRIBING

        w = self.widgets
        w.recorded_button_box.set_visible(False)
        w.action_button.set_visible(True)
        w.action_button.set_label("⏳ Transcribing...")
        w.action_button.remove_css_class("destructive-action")
        w.action_button.set_sensitive(False)
        w.status_label.set_text("Processing audio...")

    def to_result(self, text: str, language_display: str, has_audio: bool) -> None:
        """Transition to result state.

        Args:
            text: Transcription text
            language_display: Language display name
            has_audio: Whether audio data is available for replay
        """
        self._state = RecordingState.RESULT

        w = self.widgets
        w.action_button.set_label("🎤 Record Again")
        w.action_button.remove_css_class("destructive-action")
        w.action_button.add_css_class("suggested-action")
        w.action_button.set_sensitive(True)
        w.action_button.set_visible(True)

        w.regenerate_button.set_visible(has_audio)
        w.result_play_button.set_visible(has_audio)
        w.result_play_button.set_label("▶️ Play")
        w.recorded_button_box.set_visible(False)

        if text and not text.startswith("Error:") and not text.startswith("("):
            status_msg = "✓ Copied to clipboard!"
            if language_display:
                status_msg += f" • {language_display} detected"
            w.status_label.set_text(status_msg)
            w.result_label.set_text(f'"{text}"')
        else:
            w.status_label.set_text("Ready • Click to start new recording")
            w.result_label.set_text(text)

    def to_ready(self) -> None:
        """Transition to ready state."""
        self._state = RecordingState.READY

        w = self.widgets
        w.action_button.set_label("🎤 Record")
        w.action_button.set_visible(True)
        w.action_button.remove_css_class("destructive-action")
        w.action_button.add_css_class("suggested-action")
        w.action_button.set_sensitive(True)
        w.regenerate_button.set_visible(False)
        w.result_play_button.set_visible(False)
        w.recorded_button_box.set_visible(False)
        w.status_label.set_text("Ready")
        w.result_label.set_text("")
        w.waveform.clear()

    def update_playback_complete(self) -> None:
        """Update UI after playback completes."""
        w = self.widgets
        w.play_button.set_label("▶️ Play")
        w.result_play_button.set_label("▶️ Play")

        if self._state == RecordingState.RECORDED:
            w.status_label.set_text(
                "Review your recording • Play, Transcribe, or Discard"
            )
        elif self._state == RecordingState.RESULT:
            w.status_label.set_text("✓ Transcription complete")
