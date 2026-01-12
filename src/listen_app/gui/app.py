"""GTK4 GUI application for Listen voice-to-text."""

import threading
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk

import pyperclip

from ..audio import AudioRecorder
from ..transcriber import Transcriber, ModelSize
from .widgets import WaveformDrawingArea
from .styles import MAIN_CSS


class ListenGUI(Adw.Application):
    """GTK4 GUI for the Listen voice-to-text application."""

    # States for the button cycle
    STATE_READY = "ready"  # Ready to record
    STATE_RECORDING = "recording"  # Currently recording
    STATE_TRANSCRIBING = "transcribing"  # Processing audio
    STATE_RESULT = "result"  # Showing result with copy option

    def __init__(
        self,
        model_size: Optional[ModelSize] = None,
        auto_copy: bool = False,
    ):
        super().__init__(application_id="com.listen.app")
        self.model_size = model_size
        self.auto_copy = auto_copy

        self._recorder: Optional[AudioRecorder] = None
        self._transcriber: Optional[Transcriber] = None
        self._state = self.STATE_READY
        self._last_transcription = ""
        self._last_language = ""
        self._last_audio_data: Optional[bytes] = None

        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        """Initialize the main window."""
        # Create main window
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Listen")
        self.window.set_default_size(420, 400)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Listen"))

        # Model selector dropdown
        model_options = ["tiny", "base", "small", "medium", "large-v3"]
        self._model_strings = Gtk.StringList.new(model_options)
        self.model_dropdown = Gtk.DropDown(model=self._model_strings)
        self.model_dropdown.set_tooltip_text(
            "Select model size (larger = better Arabic)"
        )
        # Set default selection based on initial model_size or default
        default_idx = (
            model_options.index(self.model_size)
            if self.model_size in model_options
            else 2
        )  # 'small'
        self.model_dropdown.set_selected(default_idx)
        self.model_dropdown.connect("notify::selected", self._on_model_changed)
        header.pack_end(self.model_dropdown)

        main_box.append(header)

        # Content box with padding
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(16)
        content_box.set_margin_bottom(16)

        # Device info panel (collapsible)
        self.device_info_frame = Gtk.Frame()
        self.device_info_frame.add_css_class("device-info-frame")
        device_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        device_info_box.set_margin_start(12)
        device_info_box.set_margin_end(12)
        device_info_box.set_margin_top(8)
        device_info_box.set_margin_bottom(8)

        # Device info label
        self.device_info_label = Gtk.Label(label="⏳ Initializing...")
        self.device_info_label.set_xalign(0)
        self.device_info_label.set_wrap(True)
        self.device_info_label.add_css_class("device-info-label")
        self.device_info_label.set_use_markup(True)
        device_info_box.append(self.device_info_label)

        self.device_info_frame.set_child(device_info_box)
        content_box.append(self.device_info_frame)

        # Waveform visualization
        self.waveform = WaveformDrawingArea()
        waveform_frame = Gtk.Frame()
        waveform_frame.set_child(self.waveform)
        content_box.append(waveform_frame)

        # Status label
        self.status_label = Gtk.Label(label="Loading model...")
        self.status_label.add_css_class("dim-label")
        content_box.append(self.status_label)

        # Button container for action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.CENTER)

        # Main action button
        self.action_button = Gtk.Button(label="🎤 Record")
        self.action_button.add_css_class("suggested-action")
        self.action_button.add_css_class("pill")
        self.action_button.set_size_request(200, 50)
        self.action_button.connect("clicked", self._on_action_clicked)
        self.action_button.set_sensitive(False)
        button_box.append(self.action_button)

        # Regenerate button (hidden by default, shown after transcription)
        self.regenerate_button = Gtk.Button(label="🔄 Regenerate")
        self.regenerate_button.add_css_class("pill")
        self.regenerate_button.set_size_request(120, 50)
        self.regenerate_button.connect("clicked", self._on_regenerate_clicked)
        self.regenerate_button.set_visible(False)
        button_box.append(self.regenerate_button)

        content_box.append(button_box)

        # Transcription result
        self.result_label = Gtk.Label(label="")
        self.result_label.set_wrap(True)
        self.result_label.set_selectable(True)
        self.result_label.set_margin_top(8)
        content_box.append(self.result_label)

        main_box.append(content_box)
        self.window.set_content(main_box)

        # Apply custom CSS
        self._apply_css()

        # Initialize recorder
        self._recorder = AudioRecorder(on_status_change=self._on_recording_status)

        # Load model in background
        threading.Thread(target=self._load_model, daemon=True).start()

        self.window.present()

    def _apply_css(self):
        """Apply custom styling."""
        provider = Gtk.CssProvider()
        provider.load_from_data(MAIN_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_model(self, new_model_size: Optional[ModelSize] = None):
        """Load the transcription model in background."""
        try:
            # Use new_model_size if provided, otherwise use instance default
            model_to_load = new_model_size if new_model_size else self.model_size
            self._transcriber = Transcriber(model_size=model_to_load)
            self.model_size = model_to_load  # Update instance variable
            info = self._transcriber.get_model_info()

            # Format device info for display
            device_text = self._format_device_info(info)
            GLib.idle_add(self._update_device_info, device_text, info["device"])

            GLib.idle_add(
                self._update_status,
                f"Ready • {info['model_size'].upper()} model",
            )
            GLib.idle_add(self.action_button.set_sensitive, True)
            GLib.idle_add(self.model_dropdown.set_sensitive, True)
        except Exception as e:
            GLib.idle_add(self._update_status, f"Error: {e}")
            GLib.idle_add(
                self._update_device_info,
                "<span color='#e53935'>⚠ Error loading model</span>",
                "error",
            )
            GLib.idle_add(self.action_button.set_sensitive, True)
            GLib.idle_add(self.model_dropdown.set_sensitive, True)

    def _on_model_changed(self, dropdown, _pspec):
        """Handle model dropdown selection change."""
        if self._state != self.STATE_READY:
            # Don't change model while recording or processing
            return

        model_options = ["tiny", "base", "small", "medium", "large-v3"]
        selected_idx = dropdown.get_selected()
        new_model = model_options[selected_idx]

        if new_model == self.model_size:
            return  # No change

        # Disable controls while loading
        self.action_button.set_sensitive(False)
        self.model_dropdown.set_sensitive(False)
        self.status_label.set_text(f"Loading {new_model.upper()} model...")
        self.device_info_label.set_markup("⏳ Switching model...")

        # Load new model in background
        threading.Thread(
            target=self._load_model, args=(new_model,), daemon=True
        ).start()

    def _format_device_info(self, info: dict) -> str:
        """Format device info for display."""
        if info["device"] == "cuda" and info.get("gpu_name"):
            # GPU mode - show detailed info
            gpu_name = info["gpu_name"]
            memory = info.get("gpu_memory_mb", 0)
            cuda_ver = info.get("cuda_version", "N/A")
            compute = info["compute_type"]
            model = info["model_size"].upper()

            return (
                f"<span color='#76b900'>🟢 GPU</span>  <b>{gpu_name}</b>\n"
                f"    Memory: {memory} MB │ CUDA: {cuda_ver}\n"
                f"    Model: {model} │ Precision: {compute}"
            )
        else:
            # CPU mode
            compute = info["compute_type"]
            model = info["model_size"].upper()

            return (
                f"<span color='#0071c5'>🔵 CPU</span>  Inference Mode\n"
                f"    Model: {model} │ Precision: {compute}\n"
                f"    <span color='#888'>Tip: Install CUDA for faster processing</span>"
            )

    def _update_device_info(self, text: str, device: str):
        """Update device info display (thread-safe)."""
        self.device_info_label.set_markup(text)
        # Update CSS class based on device
        self.device_info_label.remove_css_class("gpu-active")
        self.device_info_label.remove_css_class("cpu-active")
        if device == "cuda":
            self.device_info_label.add_css_class("gpu-active")

    def _update_status(self, text: str):
        """Update status label (thread-safe)."""
        self.status_label.set_text(text)

    def _on_recording_status(self, status: str):
        """Handle recording status changes from AudioRecorder."""
        pass  # Status updates handled in button callback

    def _on_action_clicked(self, button):
        """Handle main action button click based on current state."""
        if self._state == self.STATE_READY:
            self._start_recording()
        elif self._state == self.STATE_RECORDING:
            self._stop_and_transcribe()
        elif self._state == self.STATE_RESULT:
            self._reset_to_ready()

    def _start_recording(self):
        """Start recording audio."""
        self._state = self.STATE_RECORDING
        self._last_transcription = ""
        self._last_audio_data = None

        self.action_button.set_label("⏹️ Transcribe")
        self.action_button.remove_css_class("suggested-action")
        self.action_button.add_css_class("destructive-action")
        self.regenerate_button.set_visible(False)
        self.status_label.set_text("Recording... Click to transcribe")
        self.result_label.set_text("")
        self.waveform.clear()

        # Start recording with callback for waveform
        self._recorder._on_audio_chunk = self._on_audio_chunk
        self._recorder.start()

    def _on_audio_chunk(self, data: bytes):
        """Handle incoming audio chunk for waveform."""
        GLib.idle_add(self.waveform.add_samples, data)

    def _stop_and_transcribe(self):
        """Stop recording and transcribe."""
        self._state = self.STATE_TRANSCRIBING

        self.action_button.set_label("⏳ Transcribing...")
        self.action_button.remove_css_class("destructive-action")
        self.action_button.set_sensitive(False)
        self.status_label.set_text("Processing audio...")

        # Stop and transcribe in background
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    def _transcribe_audio(self, audio_data: Optional[bytes] = None):
        """Transcribe recorded audio (runs in background thread)."""
        if audio_data is None:
            audio_data = self._recorder.stop()

        if len(audio_data) < 1000:
            GLib.idle_add(
                self._on_transcription_complete, "(no audio captured)", "", None
            )
            return

        # Store audio for potential retry
        self._last_audio_data = audio_data

        try:
            result = self._transcriber.transcribe(audio_data)
            text = result.text.strip()
            language = result.language

            if self.auto_copy and text:
                pyperclip.copy(text)

            GLib.idle_add(self._on_transcription_complete, text, language, audio_data)
        except Exception as e:
            GLib.idle_add(
                self._on_transcription_complete, f"Error: {e}", "", audio_data
            )

    def _on_transcription_complete(
        self, text: str, language: str = "", audio_data: Optional[bytes] = None
    ):
        """Handle transcription completion (runs on main thread)."""
        self._last_transcription = text
        self._last_language = language
        if audio_data is not None:
            self._last_audio_data = audio_data
        self._state = self.STATE_RESULT

        self.action_button.set_label("🎤 Record Again")
        self.action_button.remove_css_class("destructive-action")
        self.action_button.add_css_class("suggested-action")
        self.action_button.set_sensitive(True)

        # Show regenerate button if we have audio to re-process
        self.regenerate_button.set_visible(
            self._last_audio_data is not None and len(self._last_audio_data) >= 1000
        )

        # Language display mapping
        lang_names = {
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
        lang_display = lang_names.get(language, language.upper() if language else "")

        if text and not text.startswith("Error:") and not text.startswith("("):
            status_msg = "✓ Copied to clipboard!"
            if lang_display:
                status_msg += f" • {lang_display} detected"
            self.status_label.set_text(status_msg)
            self.result_label.set_text(f'"{text}"')
        else:
            self.status_label.set_text("Ready • Click to start new recording")
            self.result_label.set_text(text)

    def _on_regenerate_clicked(self, button):
        """Handle regenerate button click to re-transcribe the last audio."""
        if self._last_audio_data is None or len(self._last_audio_data) < 1000:
            return

        self._state = self.STATE_TRANSCRIBING

        self.action_button.set_label("⏳ Regenerating...")
        self.action_button.set_sensitive(False)
        self.regenerate_button.set_visible(False)
        self.status_label.set_text("Re-processing audio...")

        # Transcribe the stored audio in background
        threading.Thread(
            target=self._transcribe_audio, args=(self._last_audio_data,), daemon=True
        ).start()

    def _reset_to_ready(self):
        """Reset to ready state for new recording."""
        self._state = self.STATE_READY
        self._last_transcription = ""
        self._last_audio_data = None

        self.action_button.set_label("🎤 Record")
        self.regenerate_button.set_visible(False)
        self.status_label.set_text("Ready")
        self.result_label.set_text("")
        self.waveform.clear()

    def run_app(self):
        """Run the application."""
        self.run(None)
