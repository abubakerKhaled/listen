"""Keyboard handler for CLI interface using pynput."""

import threading
from typing import Callable, Optional

from pynput import keyboard


class KeyboardHandler:
    """Handles keyboard input for push-to-talk and toggle modes."""

    def __init__(
        self,
        toggle_mode: bool = False,
        on_start_recording: Optional[Callable[[], None]] = None,
        on_stop_recording: Optional[Callable[[], None]] = None,
        is_recording: Optional[Callable[[], bool]] = None,
    ):
        """
        Initialize the keyboard handler.

        Args:
            toggle_mode: If True, use toggle mode instead of push-to-talk
            on_start_recording: Callback when recording should start
            on_stop_recording: Callback when recording should stop
            is_recording: Function to check if currently recording
        """
        self.toggle_mode = toggle_mode
        self._on_start_recording = on_start_recording
        self._on_stop_recording = on_stop_recording
        self._is_recording = is_recording or (lambda: False)

        # Keyboard state
        self._ctrl_pressed = False
        self._space_pressed = False
        self._listener: Optional[keyboard.Listener] = None

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
                    if self._is_recording():
                        if self._on_stop_recording:
                            threading.Thread(
                                target=self._on_stop_recording, daemon=True
                            ).start()
                    else:
                        if self._on_start_recording:
                            self._on_start_recording()
                else:
                    # Push-to-talk: start recording
                    if self._on_start_recording:
                        self._on_start_recording()
        except AttributeError:
            pass

    def _on_key_release(self, key) -> None:
        """Handle key release events."""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._ctrl_pressed = False
                # In push-to-talk mode, stop when Ctrl is released
                if not self.toggle_mode and self._is_recording():
                    if self._on_stop_recording:
                        threading.Thread(
                            target=self._on_stop_recording, daemon=True
                        ).start()
            elif key == keyboard.Key.space:
                self._space_pressed = False
                # In push-to-talk mode, also stop when Space is released
                if not self.toggle_mode and self._is_recording():
                    if self._on_stop_recording:
                        threading.Thread(
                            target=self._on_stop_recording, daemon=True
                        ).start()
        except AttributeError:
            pass

    def start(self) -> None:
        """Start listening for keyboard events."""
        self._listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        if self._listener:
            self._listener.stop()
            self._listener = None
