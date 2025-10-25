"""REST API routes for the Flask application."""
from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from ..services.appstore import AppStoreService
from ..services.errors import (
    AppStoreError,
    LicenseRequiredError,
    PasswordTokenExpiredError,
    AuthCodeRequiredError,
)
from ..services.models import Account, App

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _service() -> AppStoreService:
    return current_app.config["APPSTORE_SERVICE"]


@api_bp.errorhandler(AppStoreError)
def _handle_appstore_error(exc: AppStoreError):
    payload = {"error": str(exc)}
    if exc.metadata is not None:
        payload["metadata"] = exc.metadata
    
    # Add specific handling for license errors
    if isinstance(exc, LicenseRequiredError):
        payload["licenseRequired"] = True
    
    return jsonify(payload), HTTPStatus.BAD_REQUEST


@api_bp.post("/auth/login")
def login():
    data = request.get_json(force=True) or {}
    email = data.get("email")
    password = data.get("password")
    auth_code = data.get("authCode")
    if not email or not password:
        return jsonify({"error": "email and password are required"}), HTTPStatus.BAD_REQUEST

    try:
        account = _service().login(email=email, password=password, auth_code=auth_code)
    except AuthCodeRequiredError as exc:
        return (
            jsonify({"error": str(exc) or "auth code required", "authCodeRequired": True}),
            HTTPStatus.UNAUTHORIZED,
        )

    return jsonify({"account": account.to_dict()})


@api_bp.post("/auth/logout")
def logout():
    _service().revoke()
    return jsonify({"status": "ok"})


@api_bp.get("/account")
def account_info():
    try:
        account = _service().account_info()
    except AppStoreError:
        return jsonify({"account": None}), HTTPStatus.NOT_FOUND

    return jsonify({"account": account.to_dict()})


@api_bp.get("/search")
def search():
    term = request.args.get("term")
    if not term:
        return jsonify({"error": "term query parameter is required"}), HTTPStatus.BAD_REQUEST
    limit = int(request.args.get("limit", 5))
    include_tvos = request.args.get("includeTvos", "false").lower() == "true"

    account = _service().account_info()
    result = _service().search(account, term, limit, include_tvos)
    return jsonify({
        "count": result.count,
        "results": [app.to_dict() for app in result.results],
    })


@api_bp.post("/purchase")
def purchase():
    payload = request.get_json(force=True) or {}
    account = _service().account_info()
    app = _resolve_app(payload, account)
    _service().purchase(account, app)
    return jsonify({"status": "purchased"})


@api_bp.post("/download")
def download():
    payload = request.get_json(force=True) or {}
    account = _service().account_info()
    app = _resolve_app(payload, account)
    output_path = payload.get("outputPath")
    external_version_id = payload.get("externalVersionId")
    auto_purchase = bool(payload.get("purchaseIfNeeded", False))

    service = _service()
    download_result = None
    for _ in range(3):
        try:
            download_result = service.download(
                account=account,
                app=app,
                output_path=output_path,
                external_version_id=external_version_id,
            )
            break
        except PasswordTokenExpiredError:
            if not account.password:
                raise
            account = service.login(email=account.email, password=account.password)
        except LicenseRequiredError:
            if not auto_purchase:
                raise
            service.purchase(account, app)
    if download_result is None:
        raise AppStoreError("failed to download app")

    service.replicate_sinf(download_result.destination_path, download_result.sinfs)

    return jsonify(
        {
            "destinationPath": download_result.destination_path,
            "sinfCount": len(download_result.sinfs),
        }
    )


@api_bp.post("/download-stream")
def download_stream():
    """Stream IPA download directly to the browser."""
    payload = request.get_json(force=True) or {}
    account = _service().account_info()
    app = _resolve_app(payload, account)
    external_version_id = payload.get("externalVersionId")
    auto_purchase = bool(payload.get("purchaseIfNeeded", False))

    service = _service()
    
    # Use a temp directory for downloads
    temp_dir = Path(service._storage_dir) / "temp_downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    download_result = None
    for _ in range(3):
        try:
            download_result = service.download(
                account=account,
                app=app,
                output_path=str(temp_dir),
                external_version_id=external_version_id,
            )
            break
        except PasswordTokenExpiredError:
            if not account.password:
                raise
            account = service.login(email=account.email, password=account.password)
        except LicenseRequiredError:
            if not auto_purchase:
                raise
            service.purchase(account, app)
    
    if download_result is None:
        raise AppStoreError("failed to download app")

    service.replicate_sinf(download_result.destination_path, download_result.sinfs)
    
    file_path = Path(download_result.destination_path)
    filename = file_path.name
    
    def cleanup():
        """Delete the temp file after sending."""
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
    
    response = send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )
    
    # Schedule cleanup after response is sent
    response.call_on_close(cleanup)
    
    return response


@api_bp.get("/versions")
def list_versions():
    params = request.args or {}
    external_version_id = params.get("externalVersionId")
    account = _service().account_info()
    app = _resolve_app(params, account)
    output = _service().list_versions(account, app, external_version_id)
    return jsonify(
        {
            "latestExternalVersionId": output.latest_external_version_id,
            "externalVersionIdentifiers": output.external_version_identifiers,
        }
    )


@api_bp.get("/version-metadata")
def version_metadata():
    params = request.args or {}
    version_id = params.get("versionId")
    if not version_id:
        return jsonify({"error": "versionId is required"}), HTTPStatus.BAD_REQUEST

    account = _service().account_info()
    app = _resolve_app(params, account)
    metadata = _service().get_version_metadata(account, app, version_id)
    return jsonify(metadata.to_dict())


def _resolve_app(payload: Dict[str, Any], account: Account) -> App:
    service = _service()
    bundle_id = payload.get("bundleId")
    app_id = payload.get("appId")

    if bundle_id:
        return service.lookup(account, bundle_id)

    if app_id:
        return App(id=int(app_id))

    raise AppStoreError("either appId or bundleId must be supplied")
