"""Common utilities for Listen application."""

import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def suppress_alsa_errors():
    """Context manager to suppress ALSA error messages to stderr.

    ALSA on Linux often prints verbose error messages that are not
    actionable by the user. This suppresses them during PyAudio
    initialization.
    """
    null_fd = -1
    saved_stderr_fd = -1
    try:
        # Open /dev/null
        null_fd = os.open(os.devnull, os.O_RDWR)
        # Save original stderr (FD 2)
        saved_stderr_fd = os.dup(2)

        # Redirect stderr (FD 2) to /dev/null
        os.dup2(null_fd, 2)

        yield
    except Exception as e:
        # If anything fails, still yield so the app continues
        logger.debug("Failed to suppress ALSA errors: %s", e)
        yield
    finally:
        # Restore stderr
        if saved_stderr_fd >= 0:
            os.dup2(saved_stderr_fd, 2)
            os.close(saved_stderr_fd)
        if null_fd >= 0:
            os.close(null_fd)
