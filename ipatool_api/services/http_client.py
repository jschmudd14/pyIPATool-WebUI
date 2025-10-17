"""Thin wrapper around ``requests`` that mimics the Go client semantics."""
from __future__ import annotations

import plistlib
from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple

from urllib.parse import urlencode

import requests

from . import constants
from .cookie_store import CookieStore


class HTTPClientResponseError(RuntimeError):
    """Raised when the response cannot be parsed as requested."""

    def __init__(self, message: str, *, status_code: int, headers: Dict[str, str], body: bytes) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers
        self.body = body


@dataclass(slots=True)
class HTTPRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    payload: Optional["Payload"]
    response_format: str
    follow_redirects: bool = True


@dataclass(slots=True)
class HTTPResult:
    status_code: int
    headers: Dict[str, str]
    data: Any

    def get_header(self, key: str) -> str:
        lowered = key.lower()
        for header_key, value in self.headers.items():
            if header_key.lower() == lowered:
                return value
        raise KeyError(key)


class Payload:
    def serialize(self) -> Tuple[bytes, str]:
        raise NotImplementedError


class XMLPayload(Payload):
    def __init__(self, content: Mapping[str, Any]) -> None:
        self._content = content

    def serialize(self) -> Tuple[bytes, str]:
        # Go's plist encoder produces XML format by default
        return plistlib.dumps(dict(self._content), fmt=plistlib.FMT_XML), "application/x-apple-plist"


class FormURLEncodedPayload(Payload):
    def __init__(self, content: Mapping[str, Any]) -> None:
        self._content = content

    def serialize(self) -> Tuple[bytes, str]:
        encoded = urlencode([(key, value) for key, value in self._content.items()], doseq=True)
        return encoded.encode("utf-8"), "application/x-www-form-urlencoded"


class HTTPClient:
    def __init__(self, cookie_store: CookieStore, verify: bool | str = True) -> None:
        self._cookie_store = cookie_store
        self.session = requests.Session()
        self.session.headers.setdefault("User-Agent", constants.DEFAULT_USER_AGENT)
        self.session.verify = verify
        cookie_store.attach_to(self.session)

    def send(self, request: HTTPRequest) -> HTTPResult:
        data: Optional[bytes] = None
        headers: MutableMapping[str, str] = dict(request.headers)
        
        # Ensure User-Agent is set (mimics Go's AddHeaderTransport)
        if "User-Agent" not in headers and "user-agent" not in {k.lower() for k in headers.keys()}:
            headers["User-Agent"] = constants.DEFAULT_USER_AGENT

        if request.payload is not None:
            data, default_content_type = request.payload.serialize()
            # Only set Content-Type if not already specified in request headers
            if "Content-Type" not in headers and "content-type" not in {k.lower() for k in headers.keys()}:
                headers["Content-Type"] = default_content_type

        response = self.session.request(
            method=request.method,
            url=request.url,
            headers=headers,
            data=data,
            allow_redirects=request.follow_redirects,
        )
        #(f"HTTP {response.status_code} {request.method} {request.url} {response.reason}")
        #print(f"Request headers sent: {dict(response.request.headers)}")
        #print()
        #print(response.text)

        self._cookie_store.save()

        raw_headers = dict(response.headers)
        raw_body = response.content

        parsed: Any
        if 300 <= response.status_code < 400:
            parsed = {}
        else:
            try:
                if request.response_format == constants.ResponseFormatJSON:
                    parsed = response.json()
                elif request.response_format == constants.ResponseFormatXML:
                    parsed = plistlib.loads(raw_body)
                else:
                    raise HTTPClientResponseError(
                        f"Unsupported response format: {request.response_format}",
                        status_code=response.status_code,
                        headers=raw_headers,
                        body=raw_body,
                    )
            except (ValueError, plistlib.InvalidFileException) as exc:
                raise HTTPClientResponseError(
                    "Failed to parse server response",
                    status_code=response.status_code,
                    headers=raw_headers,
                    body=raw_body,
                ) from exc

        return HTTPResult(
            status_code=response.status_code,
            headers=raw_headers,
            data=parsed,
        )

    def raw_request(self, method: str, url: str, **kwargs) -> requests.Response:
        response = self.session.request(method=method, url=url, **kwargs)
        self._cookie_store.save()
        return response
