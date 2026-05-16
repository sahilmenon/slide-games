from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/presentations"]


def get_credentials(
    credentials_file: str | Path = "credentials.json",
    token_file: str | Path = "token.json",
) -> Credentials:
    """Return valid Google OAuth2 credentials, running the auth flow if needed.

    On first run a browser window opens for consent; the token is cached in
    ``token_file`` for subsequent calls.

    Args:
        credentials_file: Path to the OAuth client secrets JSON downloaded
            from Google Cloud Console (APIs & Services → Credentials).
        token_file: Path where the access/refresh token is cached.
    """
    credentials_file = Path(credentials_file)
    token_file = Path(token_file)

    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return creds
