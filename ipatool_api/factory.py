"""Flask application factory."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .routes.api import api_bp
from .routes.ui import ui_bp
from .services import AppStoreConfig, AppStoreService, CookieStore, FileKeychain, Machine


def create_app() -> Flask:
    package_root = Path(__file__).resolve().parent
    template_dir = package_root.parent / "templates"
    static_dir = package_root.parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    machine = Machine()
    config_dir = Path(machine.home_directory()) / ".ipatool"
    config_dir.mkdir(parents=True, exist_ok=True)

    keychain = FileKeychain(str(config_dir / "keychain.json"))
    cookie_store = CookieStore(str(config_dir / "cookies.lwp"))

    verify: bool | str = True
    if os.getenv("IPATOOL_SSL_NO_VERIFY") == "1":
        verify = False
    else:
        ca_bundle_env = os.getenv("IPATOOL_CA_BUNDLE")
        if ca_bundle_env:
            verify = ca_bundle_env
        else:
            default_bundle = config_dir / "ca-bundle.pem"
            if default_bundle.exists():
                verify = str(default_bundle)

    appstore = AppStoreService(
        AppStoreConfig(
            keychain=keychain,
            cookie_store=cookie_store,
            machine=machine,
            verify=verify,
        )
    )

    app.config["APPSTORE_SERVICE"] = appstore

    app.register_blueprint(api_bp)
    app.register_blueprint(ui_bp)

    return app
