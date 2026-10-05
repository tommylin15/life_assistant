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
EXIT_COMBINED_CONFIG_BASE = 90


def _exit_code_for_config_state(
    *,
    google_client_id: str,
    developer_key: str,
    app_id: str,
) -> int:
    mask = 0
    if not google_client_id.strip():
        mask |= 1
    if not developer_key.strip():
        mask |= 2
    if not app_id.strip():
        mask |= 4
    if mask == 0:
        return 0
    if mask == 1:
        return EXIT_MISSING_GOOGLE_CLIENT
    if mask == 2:
        return EXIT_MISSING_PICKER_DEVELOPER_KEY
    if mask == 4:
        return EXIT_MISSING_PICKER_APP_ID
    return EXIT_COMBINED_CONFIG_BASE + mask


def _missing_config_names(*, google_client_id: str, developer_key: str, app_id: str) -> tuple[str, ...]:
    missing: list[str] = []
    if not google_client_id.strip():
        missing.append("google_client_id")
    if not developer_key.strip():
        missing.append("google_picker_developer_key")
    if not app_id.strip():
        missing.append("google_picker_app_id")
    return tuple(missing)


def main() -> None:
    google_client_id = settings.google_client_id.strip()
    developer_key = os.environ.get("GOOGLE_PICKER_DEVELOPER_KEY", "").strip()
    app_id = os.environ.get("GOOGLE_PICKER_APP_ID", "").strip()

    exit_code = _exit_code_for_config_state(
        google_client_id=google_client_id,
        developer_key=developer_key,
        app_id=app_id,
    )
    if exit_code:
        missing = ",".join(
            _missing_config_names(
                google_client_id=google_client_id,
                developer_key=developer_key,
                app_id=app_id,
            )
        )
        print(f"drive_picker_runtime_config=NOT_VERIFIED missing={missing}", flush=True)
        raise SystemExit(exit_code)

    print(
        "drive_picker_runtime_config=PASS client_id=present developer_key=present app_id=present",
        flush=True,
    )


if __name__ == "__main__":
    main()
