"""GTK4 GUI application for Listen voice-to-text."""

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from ..core.audio_backend import AudioBackend
from ..core.transcriber_backend import TranscriberBackend
from .components import WindowBuilder
from .handlers import StateMachine, UIWidgets, TranscriptionHandler


class ListenGUI(Adw.Application):
    """GTK4 GUI for the Listen voice-to-text application."""

    def __init__(
        self,
        audio: Optional[AudioBackend] = None,
        transcriber: Optional[TranscriberBackend] = None,
        model_size: Optional[str] = None,
        auto_copy: bool = False,
    ):
        super().__init__(application_id="com.listen.app")
        self.model_size = model_size
        self.auto_copy = auto_copy

        # Injected or factory-created backends
        self._injected_audio = audio
        self._injected_transcriber = transcriber

        # Runtime state
        self._audio: Optional[AudioBackend] = None
        self._transcriber: Optional[TranscriberBackend] = None
        self._window_builder: Optional[WindowBuilder] = None
        self._state_machine: Optional[StateMachine] = None
        self._transcription_handler: Optional[TranscriptionHandler] = None
        self._last_audio_data: Optional[bytes] = None
        self._last_transcription = ""
        self._last_language = ""

        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        """Initialize the application."""
        # Build window
        self._window_builder = WindowBuilder(app, self.model_size)
        window = self._window_builder.build(self._get_callbacks())

        # Initialize backends
        self._init_backends()

        # Initialize state machine
        self._state_machine = StateMachine(
            UIWidgets(
                action_button=self._window_builder.action_button,
                recorded_button_box=self._window_builder.recorded_button_box,
                play_button=self._window_builder.play_button,
                result_play_button=self._window_builder.result_play_button,
                regenerate_button=self._window_builder.regenerate_button,
                status_label=self._window_builder.status_label,
                result_label=self._window_builder.result_label,
                waveform=self._window_builder.waveform,
            )
        )

        # Initialize transcription handler
        self._transcription_handler = TranscriptionHandler(
            transcriber=self._transcriber,
            on_model_ready=self._on_model_ready,
            on_model_error=self._on_model_error,
            on_transcription_complete=self._on_transcription_complete,
        )

        # Preload model in background
        self._transcription_handler.preload_model()

        window.present()

    def _get_callbacks(self) -> dict:
        """Get callback dict for window builder."""
        return {
            "on_model_changed": self._on_model_changed,
            "on_action_clicked": self._on_action_clicked,
            "on_result_play_clicked": self._on_result_play_clicked,
            "on_regenerate_clicked": self._on_regenerate_clicked,
            "on_play_clicked": self._on_play_clicked,
            "on_continue_clicked": self._on_continue_clicked,
            "on_transcribe_clicked": self._on_transcribe_clicked,
            "on_discard_clicked": self._on_discard_clicked,
        }

    def _init_backends(self):
        """Initialize audio and transcriber backends."""
        if self._injected_audio is not None:
            self._audio = self._injected_audio
        else:
            from ..factory import create_audio_backend

            self._audio = create_audio_backend(on_audio_chunk=self._on_audio_chunk)

        if self._injected_transcriber is not None:
            self._transcriber = self._injected_transcriber
        else:
            from ..factory import create_transcriber

            self._transcriber = create_transcriber(model_size=self.model_size)

    def _on_audio_chunk(self, audio_data: bytes):
        """Handle real-time audio data for waveform visualization."""
        if self._state_machine and self._state_machine.is_recording():
            GLib.idle_add(self._window_builder.waveform.add_samples, audio_data)

    def _on_model_ready(self, info: dict):
        """Handle model load completion."""
        device_text = TranscriptionHandler.format_device_info(info)
        self._update_device_info(device_text, info.get("device", "cpu"))

        # Sync model_size with what was actually loaded (handles auto-detection)
        loaded_model = info.get("model_size")
        if loaded_model:
            self.model_size = loaded_model
            # Also sync dropdown if model was auto-detected
            if loaded_model in WindowBuilder.MODEL_OPTIONS:
                idx = WindowBuilder.MODEL_OPTIONS.index(loaded_model)
                # Block signal to avoid triggering _on_model_changed
                self._window_builder.model_dropdown.set_selected(idx)

        model_name = (loaded_model or "base").upper()
        self._window_builder.status_label.set_text(f"Ready • {model_name} model")
        self._window_builder.action_button.set_sensitive(True)
        self._window_builder.model_dropdown.set_sensitive(True)

    def _on_model_error(self, error: str):
        """Handle model load error."""
        self._window_builder.status_label.set_text(f"Error: {error}")
        self._update_device_info(
            "<span color='#e53935'>⚠ Error loading model</span>", "error"
        )
        self._window_builder.action_button.set_sensitive(True)
        self._window_builder.model_dropdown.set_sensitive(True)

    def _update_device_info(self, text: str, device: str):
        """Update device info display."""
        label = self._window_builder.device_info_label
        label.set_markup(text)
        label.remove_css_class("gpu-active")
        label.remove_css_class("cpu-active")
        if device == "cuda":
            label.add_css_class("gpu-active")

    def _on_model_changed(self, dropdown, _pspec):
        """Handle model dropdown selection change."""
        if not self._state_machine.is_ready():
            return

        options = WindowBuilder.MODEL_OPTIONS
        new_model = options[dropdown.get_selected()]

        if new_model == self.model_size:
            return

        self.model_size = new_model
        self._window_builder.action_button.set_sensitive(False)
        self._window_builder.model_dropdown.set_sensitive(False)
        self._window_builder.status_label.set_text(
            f"Loading {new_model.upper()} model..."
        )
        self._window_builder.device_info_label.set_markup("⏳ Switching model...")

        # Reload transcriber with new model
        from ..factory import create_transcriber

        self._transcriber = create_transcriber(model_size=new_model)
        self._transcription_handler = TranscriptionHandler(
            transcriber=self._transcriber,
            on_model_ready=self._on_model_ready,
            on_model_error=self._on_model_error,
            on_transcription_complete=self._on_transcription_complete,
        )
        self._transcription_handler.preload_model()

    def _on_action_clicked(self, button):
        """Handle main action button click."""
        if self._state_machine.is_ready():
            self._start_recording()
        elif self._state_machine.is_recording():
            self._stop_recording()
        elif self._state_machine.is_result():
            self._state_machine.to_ready()
            self._last_audio_data = None

    def _start_recording(self):
        """Start recording."""
        self._state_machine.to_recording()
        self._last_audio_data = None
        self._audio.start_recording()
        self._transcriber.preload_model()

    def _stop_recording(self):
        """Stop recording and enter preview state."""
        audio_data = self._audio.stop_recording()

        if len(audio_data) < 1000:
            self._window_builder.status_label.set_text("No audio captured. Try again.")
            self._state_machine.to_ready()
            return

        self._last_audio_data = audio_data
        self._state_machine.to_recorded()

    def _on_play_clicked(self, button):
        """Handle play button in recorded state."""
        if self._audio.is_playing():
            self._audio.stop_playback()
            self._window_builder.play_button.set_label("▶️ Play")
        else:
            if self._last_audio_data:
                self._audio.play(self._last_audio_data, self._on_playback_complete)
                self._window_builder.play_button.set_label("⏹️ Stop")
                self._window_builder.status_label.set_text("Playing audio...")

    def _on_result_play_clicked(self, button):
        """Handle play button in result state."""
        if self._audio.is_playing():
            self._audio.stop_playback()
            self._window_builder.result_play_button.set_label("▶️ Play")
        else:
            if self._last_audio_data:
                self._audio.play(self._last_audio_data, self._on_playback_complete)
                self._window_builder.result_play_button.set_label("⏹️ Stop")
                self._window_builder.status_label.set_text("Playing audio...")

    def _on_playback_complete(self):
        """Handle playback completion."""
        GLib.idle_add(self._state_machine.update_playback_complete)

    def _on_continue_clicked(self, button):
        """Handle continue recording button."""
        self._audio.stop_playback()
        self._state_machine.to_recording()
        self._audio.start_recording()

    def _on_transcribe_clicked(self, button):
        """Handle transcribe button."""
        if not self._last_audio_data or len(self._last_audio_data) < 1000:
            return

        self._audio.stop_playback()
        self._state_machine.to_transcribing()
        self._transcription_handler.transcribe(self._last_audio_data, self.auto_copy)

    def _on_discard_clicked(self, button):
        """Handle discard button."""
        self._audio.stop_playback()
        self._state_machine.to_ready()
        self._last_audio_data = None

    def _on_regenerate_clicked(self, button):
        """Handle regenerate button."""
        if not self._last_audio_data or len(self._last_audio_data) < 1000:
            return

        self._state_machine.to_transcribing()
        self._window_builder.action_button.set_label("⏳ Regenerating...")
        self._transcription_handler.transcribe(self._last_audio_data, self.auto_copy)

    def _on_transcription_complete(self, text: str, language: str, audio_data: bytes):
        """Handle transcription completion."""
        self._last_transcription = text
        self._last_language = language
        self._last_audio_data = audio_data

        language_display = TranscriptionHandler.get_language_name(language)
        has_audio = audio_data is not None and len(audio_data) >= 1000

        self._state_machine.to_result(text, language_display, has_audio)

    def run_app(self):
        """Run the application."""
        self.run(None)
