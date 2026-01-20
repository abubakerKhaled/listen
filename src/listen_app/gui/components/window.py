"""Window building utilities for Listen GUI."""

from typing import Optional, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from .widgets import WaveformDrawingArea
from .styles import MAIN_CSS


def apply_css():
    """Apply custom CSS styling."""
    provider = Gtk.CssProvider()
    provider.load_from_data(MAIN_CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


class WindowBuilder:
    """Builds the main application window and UI components."""

    MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v3"]

    def __init__(self, app: Adw.Application, model_size: Optional[str] = None):
        self.app = app
        self.model_size = model_size

        # Widget references (populated during build)
        self.window: Optional[Adw.ApplicationWindow] = None
        self.model_dropdown: Optional[Gtk.DropDown] = None
        self.device_info_label: Optional[Gtk.Label] = None
        self.waveform: Optional[WaveformDrawingArea] = None
        self.status_label: Optional[Gtk.Label] = None
        self.action_button: Optional[Gtk.Button] = None
        self.result_play_button: Optional[Gtk.Button] = None
        self.regenerate_button: Optional[Gtk.Button] = None
        self.recorded_button_box: Optional[Gtk.Box] = None
        self.play_button: Optional[Gtk.Button] = None
        self.continue_button: Optional[Gtk.Button] = None
        self.transcribe_button: Optional[Gtk.Button] = None
        self.discard_button: Optional[Gtk.Button] = None
        self.result_label: Optional[Gtk.Label] = None
        self.device_info_frame: Optional[Gtk.Frame] = None

    def build(self, callbacks: dict) -> Adw.ApplicationWindow:
        """Build and return the main window.

        Args:
            callbacks: Dict of callback names to functions, e.g.:
                - on_model_changed
                - on_action_clicked
                - on_result_play_clicked
                - on_regenerate_clicked
                - on_play_clicked
                - on_continue_clicked
                - on_transcribe_clicked
                - on_discard_clicked
        """
        apply_css()

        # Create main window
        self.window = Adw.ApplicationWindow(application=self.app)
        self.window.set_title("Listen")
        self.window.set_default_size(420, 400)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Build sections
        main_box.append(self._build_header(callbacks))
        main_box.append(self._build_content(callbacks))

        self.window.set_content(main_box)
        return self.window

    def _build_header(self, callbacks: dict) -> Adw.HeaderBar:
        """Build the header bar with model dropdown."""
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Listen"))

        # Model selector dropdown
        model_strings = Gtk.StringList.new(self.MODEL_OPTIONS)
        self.model_dropdown = Gtk.DropDown(model=model_strings)
        self.model_dropdown.set_tooltip_text(
            "Select model size (larger = better Arabic)"
        )

        # Set default selection
        default_idx = (
            self.MODEL_OPTIONS.index(self.model_size)
            if self.model_size in self.MODEL_OPTIONS
            else 2  # 'small'
        )
        self.model_dropdown.set_selected(default_idx)

        if callbacks.get("on_model_changed"):
            self.model_dropdown.connect(
                "notify::selected", callbacks["on_model_changed"]
            )

        header.pack_end(self.model_dropdown)
        return header

    def _build_content(self, callbacks: dict) -> Gtk.Box:
        """Build the main content area."""
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(16)
        content_box.set_margin_bottom(16)

        # Device info panel
        content_box.append(self._build_device_info())

        # Waveform visualization
        self.waveform = WaveformDrawingArea()
        waveform_frame = Gtk.Frame()
        waveform_frame.set_child(self.waveform)
        content_box.append(waveform_frame)

        # Status label
        self.status_label = Gtk.Label(label="Loading model...")
        self.status_label.add_css_class("dim-label")
        content_box.append(self.status_label)

        # Action buttons
        content_box.append(self._build_action_buttons(callbacks))

        # Recorded state buttons
        content_box.append(self._build_recorded_buttons(callbacks))

        # Transcription result
        self.result_label = Gtk.Label(label="")
        self.result_label.set_wrap(True)
        self.result_label.set_selectable(True)
        self.result_label.set_margin_top(8)
        content_box.append(self.result_label)

        return content_box

    def _build_device_info(self) -> Gtk.Frame:
        """Build the device info panel."""
        self.device_info_frame = Gtk.Frame()
        self.device_info_frame.add_css_class("device-info-frame")

        device_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        device_info_box.set_margin_start(12)
        device_info_box.set_margin_end(12)
        device_info_box.set_margin_top(8)
        device_info_box.set_margin_bottom(8)

        self.device_info_label = Gtk.Label(label="⏳ Initializing...")
        self.device_info_label.set_xalign(0)
        self.device_info_label.set_wrap(True)
        self.device_info_label.add_css_class("device-info-label")
        self.device_info_label.set_use_markup(True)
        device_info_box.append(self.device_info_label)

        self.device_info_frame.set_child(device_info_box)
        return self.device_info_frame

    def _build_action_buttons(self, callbacks: dict) -> Gtk.Box:
        """Build the main action button container."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.CENTER)

        # Main action button
        self.action_button = Gtk.Button(label="🎤 Record")
        self.action_button.add_css_class("suggested-action")
        self.action_button.add_css_class("pill")
        self.action_button.set_size_request(200, 50)
        self.action_button.set_sensitive(False)
        if callbacks.get("on_action_clicked"):
            self.action_button.connect("clicked", callbacks["on_action_clicked"])
        button_box.append(self.action_button)

        # Play button for result state
        self.result_play_button = Gtk.Button(label="▶️ Play")
        self.result_play_button.add_css_class("pill")
        self.result_play_button.set_size_request(100, 50)
        self.result_play_button.set_visible(False)
        if callbacks.get("on_result_play_clicked"):
            self.result_play_button.connect(
                "clicked", callbacks["on_result_play_clicked"]
            )
        button_box.append(self.result_play_button)

        # Regenerate button
        self.regenerate_button = Gtk.Button(label="🔄 Regenerate")
        self.regenerate_button.add_css_class("pill")
        self.regenerate_button.set_size_request(120, 50)
        self.regenerate_button.set_visible(False)
        if callbacks.get("on_regenerate_clicked"):
            self.regenerate_button.connect(
                "clicked", callbacks["on_regenerate_clicked"]
            )
        button_box.append(self.regenerate_button)

        return button_box

    def _build_recorded_buttons(self, callbacks: dict) -> Gtk.Box:
        """Build the recorded state button container."""
        self.recorded_button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        self.recorded_button_box.set_halign(Gtk.Align.CENTER)
        self.recorded_button_box.set_visible(False)

        # Play/Stop button
        self.play_button = Gtk.Button(label="▶️ Play")
        self.play_button.add_css_class("pill")
        self.play_button.set_size_request(90, 50)
        if callbacks.get("on_play_clicked"):
            self.play_button.connect("clicked", callbacks["on_play_clicked"])
        self.recorded_button_box.append(self.play_button)

        # Continue Recording button
        self.continue_button = Gtk.Button(label="🎤 Continue")
        self.continue_button.add_css_class("pill")
        self.continue_button.set_size_request(110, 50)
        if callbacks.get("on_continue_clicked"):
            self.continue_button.connect("clicked", callbacks["on_continue_clicked"])
        self.recorded_button_box.append(self.continue_button)

        # Transcribe button
        self.transcribe_button = Gtk.Button(label="📝 Transcribe")
        self.transcribe_button.add_css_class("suggested-action")
        self.transcribe_button.add_css_class("pill")
        self.transcribe_button.set_size_request(130, 50)
        if callbacks.get("on_transcribe_clicked"):
            self.transcribe_button.connect(
                "clicked", callbacks["on_transcribe_clicked"]
            )
        self.recorded_button_box.append(self.transcribe_button)

        # Discard button
        self.discard_button = Gtk.Button(label="🗑️")
        self.discard_button.add_css_class("destructive-action")
        self.discard_button.add_css_class("pill")
        self.discard_button.set_size_request(50, 50)
        self.discard_button.set_tooltip_text("Discard recording")
        if callbacks.get("on_discard_clicked"):
            self.discard_button.connect("clicked", callbacks["on_discard_clicked"])
        self.recorded_button_box.append(self.discard_button)

        return self.recorded_button_box
