"""Structured logging setup for bithub."""

import logging
from logging.handlers import RotatingFileHandler

from bithub.config import LOG_PATH, BITHUB_HOME


def setup_logging(debug: bool = False, verbose: bool = False) -> None:
    """Configure logging for bithub.

    - File handler always writes to ~/.bithub/bithub.log (INFO level).
    - Console handler only active with --debug (DEBUG) or --verbose (INFO).
    - Default: no console output — terminal stays clean.
    """
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("bithub")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # File handler — always on, rotated
    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # Console handler — only with flags
    if debug or verbose:
        try:
            from rich.logging import RichHandler
            console_handler = RichHandler(rich_tracebacks=True, show_path=False)
        except ImportError:
            console_handler = logging.StreamHandler()  # type: ignore[assignment]
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        root.addHandler(console_handler)
