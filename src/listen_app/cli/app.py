"""Main CLI application for Listen voice-to-text."""

import threading
from typing import Optional

import pyperclip
from rich.live import Live

from ..core.audio_backend import AudioBackend
from ..core.transcriber_backend import TranscriberBackend
from .display import StatusDisplay, console
from .keyboard import KeyboardHandler


class ListenApp:
    """Main application for voice-to-text transcription."""

    def __init__(
        self,
        audio: Optional[AudioBackend] = None,
        transcriber: Optional[TranscriberBackend] = None,
        toggle_mode: bool = False,
        auto_copy: bool = True,
    ):
        """
        Initialize the Listen application.

        Args:
            audio: Audio backend for recording (created via factory if None)
            transcriber: Transcriber backend (created via factory if None)
            toggle_mode: If True, use toggle (press to start/stop) instead of push-to-talk
            auto_copy: If True, automatically copy transcription to clipboard
        """
        self.toggle_mode = toggle_mode
        self.auto_copy = auto_copy
        self._running = True
        self._recording = False
        self._processing = False
        self._last_transcription = ""
        self._last_language = ""
        self._status_lock = threading.Lock()

        # Create backends via factory if not provided
        if audio is None:
            from ..factory import create_audio_backend

            audio = create_audio_backend(on_status_change=self._on_recording_status)
        if transcriber is None:
            from ..factory import create_transcriber

            transcriber = create_transcriber()

        self._audio = audio
        self._transcriber = transcriber

        # Display and keyboard handlers
        self._display = StatusDisplay(toggle_mode=toggle_mode, auto_copy=auto_copy)
        self._keyboard = KeyboardHandler(
            toggle_mode=toggle_mode,
            on_start_recording=self._start_recording,
            on_stop_recording=self._stop_recording_and_transcribe,
            is_recording=lambda: self._recording,
        )

    def _on_recording_status(self, status: str) -> None:
        """Handle recording status changes."""
        with self._status_lock:
            self._recording = status == "recording"

    def _get_display(self):
        """Generate the status display panel."""
        with self._status_lock:
            return self._display.get_status_panel(
                is_recording=self._recording,
                is_processing=self._processing,
                last_transcription=self._last_transcription,
                last_language=self._last_language,
            )

    def _start_recording(self) -> None:
        """Start audio recording and preload transcriber model."""
        if not self._recording and not self._processing:
            self._audio.start_recording()
            # Start loading model in background while user is recording
            self._transcriber.preload_model()

    def _stop_recording_and_transcribe(self) -> None:
        """Stop recording and transcribe the audio."""
        if self._recording:
            with self._status_lock:
                self._processing = True

            # Stop recording and get audio
            audio_data = self._audio.stop_recording()

            if len(audio_data) > 1000:  # Minimum audio length check
                try:
                    result = self._transcriber.transcribe(audio_data)

                    self._last_transcription = result.text
                    self._last_language = result.language or ""

                    if self.auto_copy and result.text:
                        pyperclip.copy(result.text)

                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            else:
                self._last_transcription = "(no audio captured)"

            with self._status_lock:
                self._processing = False

    def run(self) -> None:
        """Run the main application loop."""
        from rich.panel import Panel

        console.clear()
        console.print(
            Panel(
                "[bold]Listen[/bold] - Voice-to-Text Transcription\n\n"
                f"Mode: [cyan]{'Toggle' if self.toggle_mode else 'Push-to-talk'}[/cyan]\n"
                "Shortcut: [cyan]Ctrl+Space[/cyan]",
                border_style="blue",
            )
        )

        # Model will be loaded in background when recording starts
        console.print("[dim]Model will load when you start recording...[/dim]")
        console.print()

        # Start keyboard listener
        self._keyboard.start()

        try:
            with Live(
                self._get_display(), refresh_per_second=4, console=console
            ) as live:
                while self._running:
                    live.update(self._get_display())
        except KeyboardInterrupt:
            pass
        finally:
            self._keyboard.stop()
            self._audio.terminate()
            console.print("\n[dim]Goodbye![/dim]")
