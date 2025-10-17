"""Machine-specific helpers used by the App Store client."""
from __future__ import annotations

import os
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
