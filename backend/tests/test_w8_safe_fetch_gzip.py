"""W8: safe_fetch must not decode a gzip response twice.

Found by the Discover proof: Metapi's results endpoint answers with
Content-Encoding: gzip. safe_fetch read the decoded body and rebuilt the
response with the original headers, so httpx tried to gunzip plain JSON and
every Metapi search failed with "incorrect header check".
"""
from __future__ import annotations

import gzip
import json

import httpx
import pytest

from app.services.safe_fetch import _decoded_headers, _read_capped

PAYLOAD = {"ads": [{"id": "1", "body": "hello"}]}


def _gzip_response() -> httpx.Response:
    raw = gzip.compress(json.dumps(PAYLOAD).encode())
    return httpx.Response(
        200,
        headers={"content-type": "application/json", "content-encoding": "gzip", "content-length": str(len(raw))},
        stream=httpx.ByteStream(raw),
    )


def test_rebuilding_with_the_original_headers_is_the_bug():
    response = _gzip_response()
    body = _read_capped(response, 1_000_000)
    with pytest.raises(httpx.DecodingError, match="incorrect header check"):
        httpx.Response(200, headers=response.headers, content=body).json()


def test_rebuilt_response_reads_the_decoded_body_once():
    response = _gzip_response()
    body = _read_capped(response, 1_000_000)
    fixed = httpx.Response(200, headers=_decoded_headers(response.headers), content=body)
    assert fixed.json() == PAYLOAD
    assert "content-encoding" not in fixed.headers
    assert fixed.headers["content-type"] == "application/json"
