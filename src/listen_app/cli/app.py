"""Main CLI application for Listen voice-to-text."""

import threading
from typing import Optional

import pyperclip
from rich.live import Live

from ..audio import AudioRecorder
from ..transcriber import Transcriber, ModelSize
from .display import StatusDisplay, console
from .keyboard import KeyboardHandler


class ListenApp:
    """Main application for voice-to-text transcription."""

    def __init__(
        self,
        model_size: Optional[ModelSize] = None,
        toggle_mode: bool = False,
        auto_copy: bool = True,
    ):
        """
        Initialize the Listen application.

        Args:
            model_size: Whisper model size to use
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

        # Initialize components (lazy load transcriber)
        self._recorder = AudioRecorder(on_status_change=self._on_recording_status)
        self._transcriber: Optional[Transcriber] = None
        self._model_size = model_size

        # Display and keyboard handlers
        self._display = StatusDisplay(toggle_mode=toggle_mode, auto_copy=auto_copy)
        self._keyboard = KeyboardHandler(
            toggle_mode=toggle_mode,
            on_start_recording=self._start_recording,
            on_stop_recording=self._stop_recording_and_transcribe,
            is_recording=lambda: self._recording,
        )

    def _get_transcriber(self) -> Transcriber:
        """Lazy load the transcriber model."""
        if self._transcriber is None:
            console.print("[dim]Loading speech recognition model...[/dim]")
            self._transcriber = Transcriber(model_size=self._model_size)
            info = self._transcriber.get_model_info()
            console.print(
                f"[green]✓[/green] Model loaded: [cyan]{info['model_size']}[/cyan] "
                f"on [cyan]{info['device']}[/cyan]"
            )
        return self._transcriber

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
        """Start audio recording."""
        if not self._recording and not self._processing:
            self._recorder.start()

    def _stop_recording_and_transcribe(self) -> None:
        """Stop recording and transcribe the audio."""
        if self._recording:
            with self._status_lock:
                self._processing = True

            # Stop recording and get audio
            audio_data = self._recorder.stop()

            if len(audio_data) > 1000:  # Minimum audio length check
                try:
                    transcriber = self._get_transcriber()
                    result = transcriber.transcribe(audio_data)

                    self._last_transcription = result.text
                    self._last_language = result.language

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

        # Pre-load the model
        self._get_transcriber()

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
            self._recorder.terminate()
            console.print("\n[dim]Goodbye![/dim]")
