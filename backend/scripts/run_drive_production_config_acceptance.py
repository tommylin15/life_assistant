#!/usr/bin/env python3
"""Verify runtime-loaded Drive production configuration without exposing values.

This runs inside the immutable release image with the same LIFE_ASSISTANT_BUNDLE
secret used by the backend. It checks only presence/readiness and never prints
credentials or key material.
"""

from __future__ import annotations

import os

from app.config import settings


EXIT_MISSING_GOOGLE_CLIENT = 81
EXIT_MISSING_PICKER_DEVELOPER_KEY = 82
EXIT_MISSING_PICKER_APP_ID = 83


def main() -> None:
    google_client_id = settings.google_client_id.strip()
    developer_key = os.environ.get("GOOGLE_PICKER_DEVELOPER_KEY", "").strip()
    app_id = os.environ.get("GOOGLE_PICKER_APP_ID", "").strip()

    if not google_client_id:
        print("drive_picker_runtime_config=NOT_VERIFIED reason=google_client_id_missing", flush=True)
        raise SystemExit(EXIT_MISSING_GOOGLE_CLIENT)
    if not developer_key:
        print(
            "drive_picker_runtime_config=NOT_VERIFIED reason=google_picker_developer_key_missing",
            flush=True,
        )
        raise SystemExit(EXIT_MISSING_PICKER_DEVELOPER_KEY)
    if not app_id:
        print("drive_picker_runtime_config=NOT_VERIFIED reason=google_picker_app_id_missing", flush=True)
        raise SystemExit(EXIT_MISSING_PICKER_APP_ID)

    print(
        "drive_picker_runtime_config=PASS client_id=present developer_key=present app_id=present",
        flush=True,
    )


if __name__ == "__main__":
    main()
