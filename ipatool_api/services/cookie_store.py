"""Persistent cookie storage compatible with ``requests`` sessions."""
from __future__ import annotations

import os
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Optional


class PersistentCookieJar(LWPCookieJar):
    """LWPCookieJar with safe load/save helpers."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._path = Path(filename)
        if self._path.exists():
            try:
                self.load(ignore_discard=True, ignore_expires=True)
            except FileNotFoundError:
                pass
            except Exception:
                # Corrupted cookie jar – start fresh but keep the file around.
                self.clear()

    def save(self, ignore_discard: bool = True, ignore_expires: bool = True) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        super().save(self._path, ignore_discard=ignore_discard, ignore_expires=ignore_expires)


class CookieStore:
    """Wrapper responsible for attaching and persisting session cookies."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._jar: Optional[PersistentCookieJar] = None

    @property
    def jar(self) -> PersistentCookieJar:
        if self._jar is None:
            self._jar = PersistentCookieJar(str(self._path))
        return self._jar

    def attach_to(self, session) -> None:
        session.cookies = self.jar

    def save(self) -> None:
        self.jar.save()
