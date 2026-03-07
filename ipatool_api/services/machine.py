"""Machine-specific helpers used by the App Store client."""
from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path


class Machine:
    def mac_address(self) -> str:
        node = uuid.getnode()
        mac = f"{node:012x}"
        return ":".join(mac[i : i + 2] for i in range(0, 12, 2)).upper()

    def home_directory(self) -> str:
        return str(Path.home())

    def config_path(self, *parts: str) -> str:
        base = Path(self.home_directory()) / ".ipatool"
        for part in parts:
            base /= part
        base.parent.mkdir(parents=True, exist_ok=True)
        return str(base)

    def device_guid(self) -> str:
        """Return the stable device identifier used for App Store login.

        The older implementation derived this directly from the machine MAC
        address, which made every login look like it came from the same trusted
        device even after local credentials were wiped.  By persisting a
        separate guid we can explicitly rotate it during sign-out when testing
        the two-factor flow.
        """
        env_guid = os.getenv("IPATOOL_DEVICE_GUID", "").strip().upper()
        if env_guid:
            return self._normalize_guid(env_guid)

        guid_path = Path(self.config_path("device_guid.txt"))
        if guid_path.exists():
            raw = guid_path.read_text(encoding="utf-8").strip().upper()
            if raw:
                normalized = self._normalize_guid(raw)
                if normalized == raw:
                    return normalized

        guid = self._normalize_guid(secrets.token_hex(6).upper())
        guid_path.parent.mkdir(parents=True, exist_ok=True)
        guid_path.write_text(guid, encoding="utf-8")
        return guid

    def reset_device_guid(self) -> None:
        guid_path = Path(self.config_path("device_guid.txt"))
        guid_path.unlink(missing_ok=True)

    def _normalize_guid(self, value: str) -> str:
        cleaned = "".join(ch for ch in value if ch.isalnum()).upper()
        if not cleaned:
            raise ValueError("device guid cannot be empty")
        return cleaned[:12]
