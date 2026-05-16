from __future__ import annotations

import logging
import random
import socket
import ssl
import time
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import get_credentials

logger = logging.getLogger(__name__)

_MAX_RETRIES = 8  # max wait: 2+4+8+16+32+64+128+256 = 510s
_RETRY_BASE = 2  # seconds — doubles each attempt: 2, 4, 8, …
_RETRYABLE_HTTP = {429, 500, 502, 503, 504}
_TRANSIENT = (
    ConnectionAbortedError,
    ConnectionRefusedError,
    ConnectionResetError,
    TimeoutError,
    BrokenPipeError,
    EOFError,
    socket.timeout,
    ssl.SSLError,
)


class SlidesClient:
    """Thin wrapper around the Google Slides REST API."""

    def __init__(self, credentials_file: str | Path = "credentials.json"):
        creds = get_credentials(credentials_file)
        self._svc = build("slides", "v1", credentials=creds)

    def create_presentation(self, title: str, width_emu: int = 0, height_emu: int = 0) -> dict:
        body: dict = {"title": title}
        if width_emu and height_emu:
            body["pageSize"] = {
                "width": {"magnitude": width_emu, "unit": "EMU"},
                "height": {"magnitude": height_emu, "unit": "EMU"},
            }
        return self._svc.presentations().create(body=body).execute()

    def get_presentation(self, prs_id: str) -> dict:
        return self._svc.presentations().get(presentationId=prs_id).execute()

    def batch_update(self, prs_id: str, requests: list[dict], on_retry=None) -> dict:
        if not requests:
            return {}
        had_transient = False
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return (
                    self._svc.presentations()
                    .batchUpdate(presentationId=prs_id, body={"requests": requests})
                    .execute()
                )
            except HttpError as exc:
                # batchUpdate is atomic. A transient error (connection reset)
                # can occur after the server applied the batch but before we
                # received the response. The retry then fails with HTTP 400
                # "object ID should be unique". Treat that as success.
                if exc.status_code == 400 and had_transient and "should be unique" in str(exc):
                    logger.warning(
                        "HTTP 400 'should be unique' after prior transient error — "
                        "batch was already applied; treating as success"
                    )
                    return {}
                if exc.status_code in _RETRYABLE_HTTP and attempt < _MAX_RETRIES:
                    wait = _RETRY_BASE * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "HTTP %s — retrying in %.1fs (attempt %d/%d)",
                        exc.status_code,
                        wait,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    for remaining in range(int(wait), 0, -1):
                        if on_retry is not None:
                            on_retry(remaining)
                        time.sleep(1)
                    if on_retry is not None:
                        on_retry(0)
                else:
                    logger.error("HTTP %s (not retrying): %s", exc.status_code, exc)
                    raise
            except _TRANSIENT as exc:
                had_transient = True
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BASE * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "%s — retrying in %.1fs (attempt %d/%d)",
                        type(exc).__name__,
                        wait,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    for remaining in range(int(wait), 0, -1):
                        if on_retry is not None:
                            on_retry(remaining)
                        time.sleep(1)
                    if on_retry is not None:
                        on_retry(0)
                else:
                    logger.error(
                        "%s after %d attempts: %s", type(exc).__name__, _MAX_RETRIES + 1, exc
                    )
                    raise

    @staticmethod
    def url(prs_id: str) -> str:
        return f"https://docs.google.com/presentation/d/{prs_id}/edit"
