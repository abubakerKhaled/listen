"""
Listen - Voice-to-text transcription tool for Linux.

Usage:
    listen                  # Start in push-to-talk mode (hold Ctrl+Space)
    listen --toggle         # Start in toggle mode (press to start/stop)
    listen --model small    # Use a specific model size
    listen --help           # Show help

Controls:
    Ctrl+Space: Record (hold or toggle based on mode)
    Ctrl+C:     Exit
"""

import argparse
import sys
import threading
from typing import Optional

import pyperclip
from pynput import keyboard
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

from .recorder import AudioRecorder
from .transcriber import Transcriber, ModelSize


console = Console()


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
        self._status_lock = threading.Lock()

        # Initialize components (lazy load transcriber)
        self._recorder = AudioRecorder(on_status_change=self._on_recording_status)
        self._transcriber: Optional[Transcriber] = None
        self._model_size = model_size

        # Keyboard state
        self._ctrl_pressed = False
        self._space_pressed = False

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

    def _get_display(self) -> Panel:
        """Generate the status display panel."""
        with self._status_lock:
            if self._processing:
                status = Text("⏳ Processing...", style="yellow bold")
            elif self._recording:
                status = Text(
                    "🔴 Recording... (release to transcribe)", style="red bold"
                )
            else:
                mode = "Press" if self.toggle_mode else "Hold"
                status = Text(f"🎤 Ready - {mode} Ctrl+Space to record", style="green")

            content = Text()
            content.append(status)

            if self._last_transcription:
                content.append("\n\n")
                content.append("Last transcription:\n", style="dim")
                content.append(f'"{self._last_transcription}"', style="white")
                if self.auto_copy:
                    content.append(" ", style="dim")
                    content.append("(copied to clipboard)", style="dim italic")

            return Panel(
                content,
                title="[bold blue]Listen[/bold blue]",
                subtitle="[dim]Ctrl+C to exit[/dim]",
                border_style="blue",
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

                    if self.auto_copy and result.text:
                        pyperclip.copy(result.text)

                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            else:
                self._last_transcription = "(no audio captured)"

            with self._status_lock:
                self._processing = False

    def _on_key_press(self, key) -> None:
        """Handle key press events."""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._ctrl_pressed = True
            elif key == keyboard.Key.space:
                self._space_pressed = True

            # Check for Ctrl+Space
            if self._ctrl_pressed and self._space_pressed:
                if self.toggle_mode:
                    # Toggle mode: start or stop
                    if self._recording:
                        threading.Thread(
                            target=self._stop_recording_and_transcribe, daemon=True
                        ).start()
                    else:
                        self._start_recording()
                else:
                    # Push-to-talk: start recording
                    self._start_recording()
        except AttributeError:
            pass

    def _on_key_release(self, key) -> None:
        """Handle key release events."""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._ctrl_pressed = False
                # In push-to-talk mode, stop when Ctrl is released
                if not self.toggle_mode and self._recording:
                    threading.Thread(
                        target=self._stop_recording_and_transcribe, daemon=True
                    ).start()
            elif key == keyboard.Key.space:
                self._space_pressed = False
                # In push-to-talk mode, also stop when Space is released
                if not self.toggle_mode and self._recording:
                    threading.Thread(
                        target=self._stop_recording_and_transcribe, daemon=True
                    ).start()
        except AttributeError:
            pass

    def run(self) -> None:
        """Run the main application loop."""
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
        listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        listener.start()

        try:
            with Live(
                self._get_display(), refresh_per_second=4, console=console
            ) as live:
                while self._running:
                    live.update(self._get_display())
        except KeyboardInterrupt:
            pass
        finally:
            listener.stop()
            self._recorder.terminate()
            console.print("\n[dim]Goodbye![/dim]")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Voice-to-text transcription tool for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    listen                      Start in push-to-talk mode
    listen --toggle             Use toggle mode instead
    listen --model small        Use the 'small' Whisper model
    listen --model tiny --cpu   Force CPU with tiny model
        """,
    )

    parser.add_argument(
        "--toggle",
        "-t",
        action="store_true",
        help="Use toggle mode (press to start/stop) instead of push-to-talk",
    )

    parser.add_argument(
        "--model",
        "-m",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default=None,
        help="Whisper model size (default: auto-select based on device)",
    )

    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Don't automatically copy transcription to clipboard",
    )

    args = parser.parse_args()

    try:
        app = ListenApp(
            model_size=args.model,
            toggle_mode=args.toggle,
            auto_copy=not args.no_copy,
        )
        app.run()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
