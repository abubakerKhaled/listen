"""Display rendering for CLI interface using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


console = Console()

# Language display name mapping
LANGUAGE_NAMES = {
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


class StatusDisplay:
    """Generates Rich panel displays for CLI status."""

    def __init__(self, toggle_mode: bool = False, auto_copy: bool = True):
        self.toggle_mode = toggle_mode
        self.auto_copy = auto_copy

    def get_status_panel(
        self,
        is_recording: bool,
        is_processing: bool,
        last_transcription: str,
        last_language: str,
    ) -> Panel:
        """Generate the status display panel."""
        if is_processing:
            status = Text("⏳ Processing...", style="yellow bold")
        elif is_recording:
            status = Text("🔴 Recording... (release to transcribe)", style="red bold")
        else:
            mode = "Press" if self.toggle_mode else "Hold"
            status = Text(f"🎤 Ready - {mode} Ctrl+Space to record", style="green")

        content = Text()
        content.append(status)

        if last_transcription:
            content.append("\n\n")
            content.append("Last transcription:\n", style="dim")
            content.append(f'"{last_transcription}"', style="white")
            if self.auto_copy:
                content.append(" ", style="dim")
                content.append("(copied to clipboard)", style="dim italic")
            if last_language:
                lang_display = LANGUAGE_NAMES.get(last_language, last_language.upper())
                content.append(f" [{lang_display}]", style="cyan")

        return Panel(
            content,
            title="[bold blue]Listen[/bold blue]",
            subtitle="[dim]Ctrl+C to exit[/dim]",
            border_style="blue",
        )
