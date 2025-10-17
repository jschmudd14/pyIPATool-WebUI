"""Re-implementation of the Go App Store client in Python."""
from __future__ import annotations

import json
import os
import plistlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import requests

from . import constants
from .cookie_store import CookieStore
from .errors import (
    AppStoreError,
    AuthCodeRequiredError,
    InvalidCredentialsError,
    LicenseRequiredError,
    PasswordTokenExpiredError,
    SubscriptionRequiredError,
    TemporarilyUnavailableError,
)
from .http_client import (
    HTTPClient,
    HTTPClientResponseError,
    HTTPRequest,
    HTTPResult,
    Payload,
    XMLPayload,
)
from .keychain import FileKeychain
from .machine import Machine
from .models import (
    Account,
    App,
    DownloadOutput,
    GetVersionMetadataOutput,
    ListVersionsOutput,
    SearchOutput,
    Sinf,
)


@dataclass(slots=True)
class AppStoreConfig:
    keychain: FileKeychain
    cookie_store: CookieStore
    machine: Machine
    verify: bool | str = True


class AppStoreService:
    """Port of the Go ``appstore.AppStore`` implementation."""

    def __init__(self, config: AppStoreConfig) -> None:
        self._keychain = config.keychain
        self._machine = config.machine
        self._http = HTTPClient(config.cookie_store, verify=config.verify)
        self._storage_dir = Path(config.machine.home_directory()) / ".ipatool"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, email: str, password: str, auth_code: str | None = None) -> Account:
        guid = self._guid()
        redirect_url: Optional[str] = None
        last_result: Optional[HTTPResult] = None

        retry = False

        for attempt in range(1, 5):
            payload: Payload = XMLPayload(
                {
                    "appleId": email,
                    "attempt": str(attempt),
                    "guid": guid,
                    "password": f"{password}{(auth_code or '').replace(' ', '')}",
                    "rmp": "0",
                    "why": "signIn",
                }
            )
            url = redirect_url or f"https://{constants.PRIVATE_APPSTORE_HOST}{constants.PRIVATE_AUTH_PATH}"
            request = HTTPRequest(
                method="POST",
                url=url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                payload=payload,
                response_format=constants.ResponseFormatXML,
                follow_redirects=False,
            )
            #print(f"Attempt {attempt}: POST {url}")
            result = self._send_request(request)
            #print(f"Status: {result.status_code}")
            #print(f"Headers: {result.headers}")
            #print(f"Data keys: {list(result.data.keys()) if isinstance(result.data, dict) else type(result.data)}")
            last_result = result

            retry, redirect_url = self._parse_login_response(result, attempt, auth_code)
            #print(f"Retry: {retry}, Redirect URL: {redirect_url}")
            if not retry:
                break

        if last_result is None:
            raise AppStoreError("login attempt did not produce a response")

        if retry:
            raise AppStoreError("too many login attempts", metadata=last_result.data)

        try:
            store_front = last_result.get_header(constants.HTTP_HEADER_STOREFRONT)
        except KeyError as exc:
            raise AppStoreError("missing storefront header", metadata=last_result.headers) from exc

        account_info = last_result.data.get("accountInfo", {})
        address = account_info.get("address", {})
        account = Account(
            email=account_info.get("appleId", email),
            name=" ".join(filter(None, [address.get("firstName"), address.get("lastName")])),
            password_token=last_result.data.get("passwordToken", ""),
            directory_services_id=last_result.data.get("dsPersonId", ""),
            store_front=store_front,
            password=password,
        )

        self._persist_account(account)
        return account

    def account_info(self) -> Account:
        try:
            data = self._keychain.get("account")
        except KeyError as exc:
            raise AppStoreError("no active account") from exc

        payload = json.loads(data.decode("utf-8"))
        return Account.from_dict(payload)

    def revoke(self) -> None:
        self._keychain.remove("account")

    # ------------------------------------------------------------------
    # App discovery
    # ------------------------------------------------------------------

    def search(self, account: Account, term: str, limit: int = 5, include_tvos: bool = False) -> SearchOutput:
        country = self._country_code_from_storefront(account.store_front)
        entity = "software,iPadSoftware"
        if include_tvos:
            entity += ",tvSoftware"
        params = {
            "entity": entity,
            "limit": str(limit),
            "media": "software",
            "term": term,
            "country": country,
        }
        url = self._build_query_url(constants.ITUNES_API_SEARCH_PATH, params)
        request = HTTPRequest(
            method="GET",
            url=url,
            headers={},
            payload=None,
            response_format=constants.ResponseFormatJSON,
        )
        result = self._send_request(request)
        apps = [App.from_dict(item) for item in result.data.get("results", [])]
        return SearchOutput(count=int(result.data.get("resultCount", len(apps))), results=apps)

    def lookup(self, account: Account, bundle_id: str) -> App:
        country = self._country_code_from_storefront(account.store_front)
        params = {
            "entity": "software,iPadSoftware",
            "limit": "1",
            "media": "software",
            "bundleId": bundle_id,
            "country": country,
        }
        url = self._build_query_url(constants.ITUNES_API_LOOKUP_PATH, params)
        request = HTTPRequest(
            method="GET",
            url=url,
            headers={},
            payload=None,
            response_format=constants.ResponseFormatJSON,
        )
        result = self._send_request(request)
        results = result.data.get("results", [])
        if not results:
            raise AppStoreError("app not found", metadata=result.data)
        return App.from_dict(results[0])

    # ------------------------------------------------------------------
    # Purchasing & downloading
    # ------------------------------------------------------------------

    def purchase(self, account: Account, app: App) -> None:
        if app.price and app.price > 0:
            raise AppStoreError("purchasing paid apps is not supported")

        guid = self._guid()
        try:
            self._purchase_with_params(account, app, guid, constants.PRICING_PARAM_APPSTORE)
        except TemporarilyUnavailableError:
            self._purchase_with_params(account, app, guid, constants.PRICING_PARAM_ARCADE)

    def _purchase_with_params(self, account: Account, app: App, guid: str, pricing: str) -> None:
        payload = {
            "appExtVrsId": "0",
            "hasAskedToFulfillPreorder": "true",
            "buyWithoutAuthorization": "true",
            "hasDoneAgeCheck": "true",
            "guid": guid,
            "needDiv": "0",
            "origPage": f"Software-{app.id}",
            "origPageLocation": "Buy",
            "price": "0",
            "pricingParameters": pricing,
            "productType": "C",
            "salableAdamId": app.id,
        }
        request = HTTPRequest(
            method="POST",
            url=f"https://{constants.PRIVATE_APPSTORE_HOST}{constants.PRIVATE_PURCHASE_PATH}",
            headers={
                "iCloud-DSID": account.directory_services_id,
                "X-Dsid": account.directory_services_id,
                "X-Apple-Store-Front": account.store_front,
                "X-Token": account.password_token,
            },
            payload=XMLPayload(payload),
            response_format=constants.ResponseFormatXML,
        )
        result = self._send_request(request)
        failure_type = result.data.get("failureType", "")
        customer_message = result.data.get("customerMessage", "")

        if failure_type == constants.FAILURE_TEMPORARILY_UNAVAILABLE:
            raise TemporarilyUnavailableError("item temporarily unavailable", metadata=result.data)
        if customer_message == constants.CUSTOMER_MESSAGE_SUBSCRIPTION_REQUIRED:
            raise SubscriptionRequiredError("subscription required", metadata=result.data)
        if failure_type == constants.FAILURE_PASSWORD_TOKEN_EXPIRED:
            raise PasswordTokenExpiredError("password token expired", metadata=result.data)
        if failure_type:
            message = customer_message or "purchase failed"
            raise AppStoreError(message, metadata=result.data)

        if result.status_code == 500:
            raise AppStoreError("license already exists", metadata=result.data)

        if result.data.get("jingleDocType") != "purchaseSuccess" or result.data.get("status") != 0:
            raise AppStoreError("failed to complete purchase", metadata=result.data)

    def download(
        self,
        account: Account,
        app: App,
        output_path: Optional[str] = None,
        external_version_id: Optional[str] = None,
    ) -> DownloadOutput:
        guid = self._guid()
        result = self._send_download_request(account, app, guid, external_version_id)
        self._validate_download_result(result)

        items = result.data.get("songList", [])
        if not items:
            raise AppStoreError("invalid download response", metadata=result.data)

        item = items[0]
        metadata = dict(item.get("metadata", {}))
        version = str(metadata.get("bundleShortVersionString", "unknown"))

        destination = self._resolve_destination_path(app, version, output_path)
        temp_destination = destination + ".tmp"
        self._download_file(item.get("URL"), temp_destination)
        self._apply_patches(temp_destination, destination, metadata, account)
        Path(temp_destination).unlink(missing_ok=True)

        sinfs = [Sinf(id=int(s.get("id", 0)), data=s.get("sinf", b"")) for s in item.get("sinfs", [])]
        return DownloadOutput(destination_path=destination, sinfs=sinfs)

    def replicate_sinf(self, package_path: str, sinfs: Iterable[Sinf]) -> None:
        source = Path(package_path)
        temp = source.with_suffix(source.suffix + ".tmp")

        with ZipFile(source, "r") as src_zip, temp.open("wb") as dst_fd:
            with ZipFile(dst_fd, "w") as dst_zip:
                self._replicate_zip(src_zip, dst_zip)
                bundle_name = self._read_bundle_name(src_zip)
                manifest = self._read_manifest_plist(src_zip)
                info = self._read_info_plist(src_zip)

                sinf_list = list(sinfs)
                if manifest:
                    self._replicate_sinf_from_manifest(dst_zip, manifest, sinf_list, bundle_name)
                elif info:
                    self._replicate_sinf_from_info(dst_zip, info, sinf_list, bundle_name)
                else:
                    raise AppStoreError("failed to find manifest or info plist")

        source.unlink()
        temp.rename(source)

    def list_versions(self, account: Account, app: App, external_version_id: Optional[str] = None) -> ListVersionsOutput:
        guid = self._guid()
        result = self._send_download_request(account, app, guid, external_version_id)
        self._validate_download_result(result)
        item = self._extract_first_item(result)

        metadata = item.get("metadata", {})
        identifiers = metadata.get("softwareVersionExternalIdentifiers")
        if not isinstance(identifiers, list):
            raise AppStoreError("invalid version identifiers", metadata=metadata)
        external_ids = [str(value) for value in identifiers]
        latest = str(metadata.get("softwareVersionExternalIdentifier"))
        return ListVersionsOutput(
            external_version_identifiers=external_ids,
            latest_external_version_id=latest,
        )

    def get_version_metadata(self, account: Account, app: App, version_id: str) -> GetVersionMetadataOutput:
        guid = self._guid()
        result = self._send_download_request(account, app, guid, version_id)
        self._validate_download_result(result)
        item = self._extract_first_item(result)

        metadata = item.get("metadata", {})
        asset_info = item.get("asset-info", {})
        
        release_date = metadata.get("releaseDate")
        try:
            release = datetime.fromisoformat(str(release_date).replace("Z", "+00:00"))
        except ValueError as exc:
            raise AppStoreError("failed to parse release date", metadata=metadata) from exc

        age_ratings = metadata.get("appAgeRatings", {})
        us_rating = age_ratings.get("US", {})

        return GetVersionMetadataOutput(
            display_version=str(metadata.get("bundleShortVersionString", "N/A")),
            build_number=str(metadata.get("bundleVersion", "N/A")),
            release_date=release,
            file_size=asset_info.get("file-size", 0),
            bundle_id=str(metadata.get("softwareVersionBundleId", "N/A")),
            artist_name=str(metadata.get("artistName", "N/A")),
            item_name=str(metadata.get("itemName", "N/A")),
            genre=str(metadata.get("genre", "N/A")),
            age_rating=str(us_rating.get("label", "N/A")),
            requires_rosetta=bool(metadata.get("requiresRosetta", False)),
            runs_on_apple_silicon=bool(metadata.get("runsOnAppleSilicon", False)),
            copyright_info=str(metadata.get("copyright", "N/A")),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _persist_account(self, account: Account) -> None:
        payload = json.dumps(account.to_dict(), indent=2)
        self._keychain.set("account", payload.encode("utf-8"))

    def _parse_login_response(
        self, result: HTTPResult, attempt: int, auth_code: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        status = result.status_code
        data = result.data
        failure_type = data.get("failureType", "")
        customer_message = data.get("customerMessage", "")

        if status in (301, 302, 303, 307, 308):
            try:
                return True, result.get_header("Location")
            except KeyError:
                return True, None

        if attempt == 1 and failure_type == constants.FAILURE_INVALID_CREDENTIALS:
            return True, None

        if not failure_type and not auth_code and customer_message == constants.CUSTOMER_MESSAGE_BAD_LOGIN:
            raise AuthCodeRequiredError("two-factor auth code required", metadata=data)

        if not failure_type and customer_message == constants.CUSTOMER_MESSAGE_ACCOUNT_DISABLED:
            raise AppStoreError("account is disabled", metadata=data)

        if failure_type and customer_message:
            raise AppStoreError(customer_message, metadata=data)

        if failure_type:
            raise AppStoreError("authentication failed", metadata=data)

        if status != 200 or not data.get("passwordToken") or not data.get("dsPersonId"):
            raise AppStoreError("invalid authentication response", metadata=data)

        return False, None

    def _country_code_from_storefront(self, store_front: str) -> str:
        prefix = store_front.split("-")[0]
        for code, value in constants.STORE_FRONTS.items():
            if value == prefix:
                return code
        raise AppStoreError(f"unknown storefront: {store_front}")

    def _build_query_url(self, path: str, params: Dict[str, str]) -> str:
        from urllib.parse import urlencode

        query = urlencode(params)
        return f"https://{constants.ITUNES_API_DOMAIN}{path}?{query}"

    def _send_request(self, request: HTTPRequest) -> HTTPResult:
        try:
            return self._http.send(request)
        except HTTPClientResponseError as exc:
            body_preview = exc.body[:2048]
            if isinstance(body_preview, bytes):
                body_text = body_preview.decode("utf-8", errors="replace")
            else:
                body_text = str(body_preview)
            metadata = {
                "status": exc.status_code,
                "headers": exc.headers,
                "body": body_text,
            }
            raise AppStoreError("unexpected response from Apple", metadata=metadata) from exc
        except requests.RequestException as exc:
            raise AppStoreError("network request failed", metadata={"error": str(exc)}) from exc

    def _guid(self) -> str:
        return self._machine.mac_address().replace(":", "").upper()

    def _send_download_request(
        self,
        account: Account,
        app: App,
        guid: str,
        external_version_id: Optional[str],
    ) -> HTTPResult:
        host = f"{constants.PRIVATE_HOST_PREFIX_WITHOUT_CODE}-{constants.PRIVATE_APPSTORE_HOST}"
        payload: Dict[str, Any] = {
            "creditDisplay": "",
            "guid": guid,
            "salableAdamId": app.id,
        }
        if external_version_id:
            payload["externalVersionId"] = external_version_id

        request = HTTPRequest(
            method="POST",
            url=f"https://{host}{constants.PRIVATE_DOWNLOAD_PATH}?guid={guid}",
            headers={
                "iCloud-DSID": account.directory_services_id,
                "X-Dsid": account.directory_services_id,
            },
            payload=XMLPayload(payload),
            response_format=constants.ResponseFormatXML,
        )
        return self._send_request(request)

    def _validate_download_result(self, result: HTTPResult) -> None:
        failure_type = result.data.get("failureType", "")
        customer_message = result.data.get("customerMessage", "")

        if failure_type == constants.FAILURE_PASSWORD_TOKEN_EXPIRED:
            raise PasswordTokenExpiredError("password token expired", metadata=result.data)
        if failure_type == constants.FAILURE_LICENSE_NOT_FOUND:
            raise LicenseRequiredError("license required", metadata=result.data)
        if failure_type and customer_message:
            raise AppStoreError(customer_message, metadata=result.data)
        if failure_type:
            raise AppStoreError(f"download failed ({failure_type})", metadata=result.data)

    def _extract_first_item(self, result: HTTPResult) -> Dict[str, Any]:
        items = result.data.get("songList", [])
        if not items:
            raise AppStoreError("invalid response payload", metadata=result.data)
        return items[0]

    def _resolve_destination_path(self, app: App, version: str, output_path: Optional[str]) -> str:
        file_name_parts = []
        if app.bundle_id:
            file_name_parts.append(app.bundle_id)
        if app.id:
            file_name_parts.append(str(app.id))
        if version:
            file_name_parts.append(version)
        file_name = "_".join(file_name_parts) + ".ipa"

        if not output_path:
            return str(Path.cwd() / file_name)

        output = Path(output_path)
        if output.is_dir() or output_path.endswith(os.sep):
            return str(output / file_name)
        return str(output)

    def _download_file(self, url: str, destination: str) -> None:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        existing = dest_path.stat().st_size if dest_path.exists() else 0
        headers = {}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        mode = "ab" if existing else "wb"

        response = self._http.raw_request("GET", url, headers=headers, stream=True)
        try:
            response.raise_for_status()
            with dest_path.open(mode) as handle:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        handle.write(chunk)
        finally:
            response.close()

    def _apply_patches(
        self,
        source_path: str,
        destination_path: str,
        metadata: Dict[str, Any],
        account: Account,
    ) -> None:
        src = Path(source_path)
        dst = Path(destination_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        with src.open("rb") as src_fd, dst.open("wb") as dst_fd:
            with ZipFile(src_fd) as src_zip, ZipFile(dst_fd, "w") as dst_zip:
                self._replicate_zip(src_zip, dst_zip)
                self._write_metadata(dst_zip, metadata, account)

    def _replicate_zip(self, src_zip: ZipFile, dst_zip: ZipFile) -> None:
        for info in src_zip.infolist():
            data = src_zip.read(info.filename)
            new_info = ZipInfo(filename=info.filename)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.date_time = info.date_time
            dst_zip.writestr(new_info, data)

    def _write_metadata(self, zip_file: ZipFile, metadata: Dict[str, Any], account: Account) -> None:
        metadata = dict(metadata)
        metadata["apple-id"] = account.email
        metadata["userName"] = account.email
        data = plistlib.dumps(metadata, fmt=plistlib.FMT_BINARY)
        info = ZipInfo("iTunesMetadata.plist")
        info.compress_type = ZIP_DEFLATED
        zip_file.writestr(info, data)

    def _read_manifest_plist(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        for info in zip_file.infolist():
            if info.filename.endswith(".app/SC_Info/Manifest.plist"):
                with zip_file.open(info.filename) as fh:
                    return plistlib.loads(fh.read())
        return None

    def _read_info_plist(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        for info in zip_file.infolist():
            if info.filename.endswith(".app/Info.plist") and "/Watch/" not in info.filename:
                with zip_file.open(info.filename) as fh:
                    return plistlib.loads(fh.read())
        return None

    def _read_bundle_name(self, zip_file: ZipFile) -> str:
        for info in zip_file.infolist():
            if info.filename.endswith(".app/Info.plist") and "/Watch/" not in info.filename:
                path = Path(info.filename)
                return path.parent.name
        raise AppStoreError("could not determine bundle name")

    def _replicate_sinf_from_manifest(
        self,
        zip_file: ZipFile,
        manifest: Dict[str, Any],
        sinfs: List[Sinf],
        bundle_name: str,
    ) -> None:
        paths = manifest.get("SinfPaths", [])
        for sinf_data, relative_path in zip(sinfs, paths):
            full_path = f"Payload/{bundle_name}.app/{relative_path}"
            info = ZipInfo(full_path)
            info.compress_type = ZIP_DEFLATED
            zip_file.writestr(info, sinf_data.data)

    def _replicate_sinf_from_info(
        self,
        zip_file: ZipFile,
        info_plist: Dict[str, Any],
        sinfs: List[Sinf],
        bundle_name: str,
    ) -> None:
        if not sinfs:
            raise AppStoreError("missing sinf payloads")
        executable = info_plist.get("CFBundleExecutable")
        if not executable:
            raise AppStoreError("missing CFBundleExecutable")
        full_path = f"Payload/{bundle_name}.app/SC_Info/{executable}.sinf"
        info = ZipInfo(full_path)
        info.compress_type = ZIP_DEFLATED
        zip_file.writestr(info, sinfs[0].data)

