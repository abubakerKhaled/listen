"""
Listen - Voice-to-text transcription tool for Linux.

Usage:
    listen                  # Start GUI (default)
    listen --cli            # Use terminal interface
    listen --cli --toggle   # Terminal with toggle mode
    listen --model small    # Use a specific model size
    listen --help           # Show help

Controls:
    Ctrl+Space: Record (hold or toggle based on mode)
    Ctrl+C:     Exit
"""

import argparse
import sys

from .app import ListenApp
from .display import console

__all__ = ["ListenApp", "main"]


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Voice-to-text transcription tool for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    listen                      Start GUI (default)
    listen --cli                Use terminal interface
    listen --cli --toggle       Terminal with toggle mode
    listen --model small        Use the 'small' Whisper model
        """,
    )

    parser.add_argument(
        "--cli",
        "-c",
        action="store_true",
        help="Use terminal interface instead of GUI",
    )

    parser.add_argument(
        "--toggle",
        "-t",
        action="store_true",
        help="Use toggle mode (press to start/stop) instead of push-to-talk (CLI only)",
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
        if args.cli:
            # Terminal interface
            app = ListenApp(
                model_size=args.model,
                toggle_mode=args.toggle,
                auto_copy=not args.no_copy,
            )
            app.run()
        else:
            # GUI interface (default)
            from ..gui import run_gui

            run_gui(
                model_size=args.model,
                auto_copy=not args.no_copy,
            )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
