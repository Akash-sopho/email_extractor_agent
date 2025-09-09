"""Gmail SDK wrapper with local OAuth (read-only).

Uses InstalledAppFlow with client id/secret from env and persists tokens
to the path specified by settings.GOOGLE_TOKEN_PATH.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from app.core.config import get_settings


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    def __init__(self) -> None:
        self._service: Any | None = None

    def _load_credentials(self) -> Credentials:
        settings = get_settings()
        token_path = Path(settings.GOOGLE_TOKEN_PATH)
        token_path.parent.mkdir(parents=True, exist_ok=True)

        creds: Credentials | None = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_id = settings.GOOGLE_CLIENT_ID
                client_secret = settings.GOOGLE_CLIENT_SECRET
                if not client_id or not client_secret:
                    raise RuntimeError(
                        "Missing GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET in environment"
                    )
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uris": [
                            "http://localhost",
                            "http://localhost:8080/",
                            "http://localhost:8080",
                        ],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        return creds

    def get_service(self) -> Any:
        if self._service is None:
            creds = self._load_credentials()
            self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

