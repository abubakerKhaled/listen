"""Audio utilities for ALSA error handling.

This module re-exports from common.utils for backward compatibility.
"""

from listen_app.common.utils import suppress_alsa_errors

__all__ = ["suppress_alsa_errors"]
