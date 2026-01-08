"""GTK4 GUI for Listen voice-to-text application."""

import threading
import struct
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk

import pyperclip

from .recorder import AudioRecorder
from .transcriber import Transcriber, ModelSize


class WaveformDrawingArea(Gtk.DrawingArea):
    """Custom widget for displaying audio waveform."""

    def __init__(self):
        super().__init__()
        self._samples = []
        self._max_samples = 100
        self.set_draw_func(self._draw)
        self.set_content_width(380)
        self.set_content_height(100)

    def _draw(self, area, cr, width, height):
        """Draw the waveform."""
        # Background
        cr.set_source_rgb(0.1, 0.1, 0.15)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        if not self._samples:
            # Draw center line when idle
            cr.set_source_rgb(0.3, 0.3, 0.4)
            cr.set_line_width(1)
            cr.move_to(0, height / 2)
            cr.line_to(width, height / 2)
            cr.stroke()
            return

        # Draw waveform
        cr.set_source_rgb(0.4, 0.8, 0.4)
        cr.set_line_width(2)

        sample_width = width / self._max_samples
        center_y = height / 2

        cr.move_to(0, center_y)
        for i, sample in enumerate(self._samples):
            x = i * sample_width
            # Scale amplitude to fit height
            amplitude = sample * (height / 2) * 0.9
            cr.line_to(x, center_y - amplitude)

        cr.stroke()

        # Draw mirror (bottom half)
        cr.set_source_rgba(0.4, 0.8, 0.4, 0.5)
        cr.move_to(0, center_y)
        for i, sample in enumerate(self._samples):
            x = i * sample_width
            amplitude = sample * (height / 2) * 0.9
            cr.line_to(x, center_y + amplitude)
        cr.stroke()

    def add_samples(self, audio_data: bytes):
        """Add audio samples to the waveform display."""
        # Convert bytes to normalized amplitude values
        samples = struct.unpack(f"{len(audio_data) // 2}h", audio_data)

        # Calculate RMS amplitude for this chunk
        if samples:
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            normalized = min(rms / 32768.0 * 3, 1.0)  # Amplify for visibility
            self._samples.append(normalized)

            # Keep only recent samples
            if len(self._samples) > self._max_samples:
                self._samples = self._samples[-self._max_samples :]

        self.queue_draw()

    def clear(self):
        """Clear the waveform display."""
        self._samples = []
        self.queue_draw()


class ListenGUI(Adw.Application):
    """GTK4 GUI for the Listen voice-to-text application."""

    def __init__(
        self,
        model_size: Optional[ModelSize] = None,
        auto_copy: bool = True,
    ):
        super().__init__(application_id="com.listen.app")
        self.model_size = model_size
        self.auto_copy = auto_copy

        self._recorder: Optional[AudioRecorder] = None
        self._transcriber: Optional[Transcriber] = None
        self._recording = False
        self._processing = False

        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        """Initialize the main window."""
        # Create main window
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("Listen")
        self.window.set_default_size(400, 320)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Listen"))
        main_box.append(header)

        # Content box with padding
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)

        # Waveform visualization
        self.waveform = WaveformDrawingArea()
        waveform_frame = Gtk.Frame()
        waveform_frame.set_child(self.waveform)
        content_box.append(waveform_frame)

        # Status label
        self.status_label = Gtk.Label(label="Loading model...")
        self.status_label.add_css_class("dim-label")
        content_box.append(self.status_label)

        # Record button
        self.record_button = Gtk.Button(label="🎤 Click to Record")
        self.record_button.add_css_class("suggested-action")
        self.record_button.add_css_class("pill")
        self.record_button.set_size_request(-1, 50)
        self.record_button.connect("clicked", self._on_record_clicked)
        self.record_button.set_sensitive(False)
        content_box.append(self.record_button)

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
        css = b"""
        .recording-button {
            background: linear-gradient(to bottom, #e53935, #c62828);
            color: white;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_model(self):
        """Load the transcription model in background."""
        try:
            self._transcriber = Transcriber(model_size=self.model_size)
            info = self._transcriber.get_model_info()
            GLib.idle_add(
                self._update_status,
                f"Ready • {info['model_size']} model on {info['device']}",
            )
            GLib.idle_add(self.record_button.set_sensitive, True)
        except Exception as e:
            GLib.idle_add(self._update_status, f"Error: {e}")

    def _update_status(self, text: str):
        """Update status label (thread-safe)."""
        self.status_label.set_text(text)

    def _on_recording_status(self, status: str):
        """Handle recording status changes from AudioRecorder."""
        pass  # Status updates handled in button callback

    def _on_record_clicked(self, button):
        """Handle record button click."""
        if self._processing:
            return

        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """Start recording audio."""
        self._recording = True
        self.record_button.set_label("⬛ Stop")
        self.record_button.remove_css_class("suggested-action")
        self.record_button.add_css_class("destructive-action")
        self.status_label.set_text("Recording...")
        self.result_label.set_text("")
        self.waveform.clear()

        # Start recording with callback for waveform
        self._recorder._on_audio_chunk = self._on_audio_chunk
        self._recorder.start()

    def _on_audio_chunk(self, data: bytes):
        """Handle incoming audio chunk for waveform."""
        GLib.idle_add(self.waveform.add_samples, data)

    def _stop_recording(self):
        """Stop recording and transcribe."""
        self._recording = False
        self._processing = True

        self.record_button.set_label("⏳ Transcribing...")
        self.record_button.remove_css_class("destructive-action")
        self.record_button.set_sensitive(False)
        self.status_label.set_text("Processing audio...")

        # Stop and transcribe in background
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    def _transcribe_audio(self):
        """Transcribe recorded audio (runs in background thread)."""
        audio_data = self._recorder.stop()

        if len(audio_data) < 1000:
            GLib.idle_add(self._on_transcription_complete, "(no audio captured)")
            return

        try:
            result = self._transcriber.transcribe(audio_data)
            text = result.text.strip()

            if self.auto_copy and text:
                pyperclip.copy(text)

            GLib.idle_add(self._on_transcription_complete, text)
        except Exception as e:
            GLib.idle_add(self._on_transcription_complete, f"Error: {e}")

    def _on_transcription_complete(self, text: str):
        """Handle transcription completion (runs on main thread)."""
        self._processing = False

        self.record_button.set_label("🎤 Click to Record")
        self.record_button.add_css_class("suggested-action")
        self.record_button.set_sensitive(True)

        if text and not text.startswith("Error:"):
            self.status_label.set_text(
                "✓ Copied to clipboard" if self.auto_copy else "Ready"
            )
            self.result_label.set_text(f'"{text}"')
        else:
            self.status_label.set_text("Ready")
            self.result_label.set_text(text)

    def run_app(self):
        """Run the application."""
        self.run(None)


def run_gui(model_size: Optional[ModelSize] = None, auto_copy: bool = True):
    """Entry point for GUI mode."""
    app = ListenGUI(model_size=model_size, auto_copy=auto_copy)
    app.run_app()
