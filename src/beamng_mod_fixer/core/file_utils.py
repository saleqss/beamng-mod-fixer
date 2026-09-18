"""File utilities for atomic replacements and filesystem operations."""

import logging
import os
from pathlib import Path
import time
import uuid

logger = logging.getLogger(__name__)


def create_temp_target(target: Path) -> Path:
    """Create a temporary target file path in the same directory as target.

    Placing the temporary file in the same parent directory guarantees that
    it resides on the identical filesystem volume/drive, allowing atomic
    os.replace operations on Windows, Linux, and macOS.

    Args:
        target: The destination file path.

    Returns:
        Path: A unique temporary file path alongside target.
    """
    unique_id = uuid.uuid4().hex[:10]
    temp_name = f".tmp_{target.stem}_{unique_id}{target.suffix}"
    return target.parent / temp_name


def atomic_replace(src: Path, dst: Path, retries: int = 5, delay: float = 0.1) -> None:
    """Atomically replace dst with src, with retries for Windows file locking.

    Args:
        src: Source temporary file path.
        dst: Final destination file path.
        retries: Number of retry attempts if transient lock occurs.
        delay: Sleep interval in seconds between retries.

    Raises:
        OSError: If replacement fails after all retries.
    """
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except (PermissionError, OSError) as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error(
                    "Failed atomic replace '%s' -> '%s' after %d attempts: %s",
                    src,
                    dst,
                    retries,
                    e,
                )
                raise
