"""Domain models for the iPatool service layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Account:
    email: str
    password_token: str
    directory_services_id: str
    name: str
    store_front: str
    password: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        return cls(
            email=data.get("email", ""),
            password_token=data.get("passwordToken", ""),
            directory_services_id=data.get("directoryServicesIdentifier", ""),
            name=data.get("name", ""),
            store_front=data.get("storeFront", ""),
            password=data.get("password"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "passwordToken": self.password_token,
            "directoryServicesIdentifier": self.directory_services_id,
            "name": self.name,
            "storeFront": self.store_front,
            "password": self.password,
        }


@dataclass(slots=True)
class App:
    id: int
    bundle_id: str = ""
    name: str = ""
    version: str = ""
    price: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "App":
        return cls(
            id=int(data.get("trackId") or data.get("id", 0)),
            bundle_id=data.get("bundleId", ""),
            name=data.get("trackName", ""),
            version=data.get("version", ""),
            price=float(data.get("price", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trackId": self.id,
            "bundleId": self.bundle_id,
            "trackName": self.name,
            "version": self.version,
            "price": self.price,
        }


@dataclass(slots=True)
class Sinf:
    id: int
    data: bytes

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sinf":
        return cls(id=int(data.get("id", 0)), data=data.get("sinf", b""))


@dataclass(slots=True)
class SearchOutput:
    count: int
    results: List[App] = field(default_factory=list)


@dataclass(slots=True)
class DownloadOutput:
    destination_path: str
    sinfs: List[Sinf]


@dataclass(slots=True)
class ListVersionsOutput:
    external_version_identifiers: List[str]
    latest_external_version_id: str


@dataclass(slots=True)
class GetVersionMetadataOutput:
    display_version: str
    build_number: str
    release_date: datetime
    file_size: int
    bundle_id: str
    artist_name: str
    item_name: str
    genre: str
    age_rating: str
    requires_rosetta: bool
    runs_on_apple_silicon: bool
    copyright_info: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "displayVersion": self.display_version,
            "buildNumber": self.build_number,
            "releaseDate": self.release_date.isoformat(),
            "fileSize": self.file_size,
            "bundleId": self.bundle_id,
            "artistName": self.artist_name,
            "itemName": self.item_name,
            "genre": self.genre,
            "ageRating": self.age_rating,
            "requiresRosetta": self.requires_rosetta,
            "runsOnAppleSilicon": self.runs_on_apple_silicon,
            "copyright": self.copyright_info,
        }
