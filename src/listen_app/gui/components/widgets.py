"""Custom GTK widgets for the Listen GUI."""

import struct

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


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
