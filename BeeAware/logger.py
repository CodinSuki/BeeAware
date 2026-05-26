# logger.py — persistent error logger
# Standalone module, imported wherever log_error() is needed.

import os
from datetime import datetime
from config import ERROR_LOG_PATH


def log_error(context: str, exc: Exception) -> None:
    """
    Write a timestamped error entry to ERROR_LOG_PATH and print to console.
    Safe to call from any thread. Silently ignores failures writing the log
    itself to avoid masking the original exception.
    """
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{context}] {type(exc).__name__}: {exc}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line.strip())
