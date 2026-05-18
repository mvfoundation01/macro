"""Shared utilities for ingest loaders: exceptions, retry, atomic IO, logging."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from filelock import FileLock
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class IngestError(Exception):
    """Base. All subclasses must set self.user_message = '<plain-language card text>'."""

    user_message: str = ""

    def __init__(self, message: str = "", *, user_message: str | None = None) -> None:
        super().__init__(message)
        if user_message is not None:
            self.user_message = user_message
        elif not self.user_message:
            self.user_message = message


class NetworkError(IngestError):
    """Connection error, timeout, or retries exhausted."""


class APIKeyError(IngestError):
    """Missing or rejected credentials."""


class DataValidationError(IngestError):
    """Response parsed but failed a validation gate."""


class FileFormatError(IngestError):
    """CSV/XLS/XLSX parse failure."""


class SourceMissingError(IngestError):
    """Expected local file is absent."""


class IntegrityError(IngestError):
    """Master archive integrity violation (e.g., refused shrink/overwrite)."""


# ---------------------------------------------------------------------------
# Retry decorator (network only)
# ---------------------------------------------------------------------------


def retryable(max_attempts: int = 5):  # type: ignore[no-untyped-def]
    """Return a tenacity retry decorator tuned for transient network errors."""
    return retry(
        wait=wait_exponential_jitter(initial=2, max=60),
        stop=stop_after_attempt(max_attempts),
        retry=retry_if_exception_type(
            (NetworkError, requests.ConnectionError, requests.Timeout)
        ),
        reraise=True,
    )


# ---------------------------------------------------------------------------
# Atomic write helpers
# ---------------------------------------------------------------------------


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes to ``path`` via a sibling .tmp file + os.replace (atomic on POSIX & NTFS)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_bytes(path, json.dumps(obj, indent=2, default=str).encode("utf-8"))


def atomic_write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, compression="snappy")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Filelock helper
# ---------------------------------------------------------------------------


def file_lock(path: Path, timeout: int = 60) -> FileLock:
    """Return a FileLock at ``path + .lock`` with the given timeout (seconds)."""
    return FileLock(str(path) + ".lock", timeout=timeout)


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Logger setup -- never log api_key or full file contents.
# ---------------------------------------------------------------------------


class _RedactingFilter(logging.Filter):
    """Replace anything that looks like a FRED api_key with <redacted>."""

    _patterns: list[str] = []

    @classmethod
    def add_secret(cls, value: str) -> None:
        if value and value not in cls._patterns:
            cls._patterns.append(value)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = msg
        for s in self._patterns:
            if s and s in redacted:
                redacted = redacted.replace(s, "<redacted>")
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def get_logger(name: str = "buffett.ingest") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        # Propagate to root so pytest's caplog can capture, but the stream handler
        # we attached prevents the "No handlers could be found" warning at module
        # import time before any caller has configured logging.
        logger.propagate = True
    # Ensure the redacting filter is attached exactly once per handler.
    for handler in logger.handlers:
        if not any(isinstance(f, _RedactingFilter) for f in handler.filters):
            handler.addFilter(_RedactingFilter())
    return logger


def register_secret(value: str) -> None:
    """Mark ``value`` as a secret to be redacted from log output."""
    _RedactingFilter.add_secret(value)


# ---------------------------------------------------------------------------
# Misc utility
# ---------------------------------------------------------------------------


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
