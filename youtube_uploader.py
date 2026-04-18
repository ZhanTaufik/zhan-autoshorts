"""
youtube_uploader.py – Uploads a video to YouTube as a Short.

Uses OAuth 2.0. On first run it opens a browser for authorization and
caches the token in youtube_token.json for subsequent runs.

Setup:
  1. Go to Google Cloud Console → Enable YouTube Data API v3
  2. Create OAuth 2.0 credentials (Desktop App)
  3. Download the JSON → save as client_secrets.json next to this file
"""

import logging
import os
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config import Config

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE = "youtube"
API_VERSION = "v3"


class YouTubeUploader:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._service = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
    ) -> str:
        """Upload video and return the YouTube watch URL."""
        service = self._get_service()

        # Append #Shorts to description and tags for discovery
        full_description = description + "\n\n#Shorts"
        if "shorts" not in [t.lower() for t in tags]:
            tags = tags + ["Shorts", "YouTubeShorts"]

        body = {
            "snippet": {
                "title": title[:100],
                "description": full_description[:5000],
                "tags": tags[:500],
                "categoryId": self.cfg.YOUTUBE_CATEGORY_ID,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": self.cfg.YOUTUBE_PRIVACY,
                "madeForKids": self.cfg.YOUTUBE_MADE_FOR_KIDS,
                "selfDeclaredMadeForKids": self.cfg.YOUTUBE_MADE_FOR_KIDS,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,   # 5 MB chunks
        )

        log.info("  Uploading '%s' …", title[:50])
        request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = self._resumable_upload(request)
        video_id = response["id"]
        url = f"https://www.youtube.com/shorts/{video_id}"
        log.info("  ✓ Uploaded → %s", url)
        return url

    # ── OAuth ──────────────────────────────────────────────────────────────────

    def _get_service(self):
        if self._service:
            return self._service

        creds = self._load_credentials()
        self._service = build(API_SERVICE, API_VERSION, credentials=creds)
        return self._service

    def _load_credentials(self) -> Credentials:
        token_path = self.cfg.YOUTUBE_TOKEN_FILE
        secrets_path = self.cfg.YOUTUBE_CLIENT_SECRETS

        creds = None

        # Load cached token
        if Path(token_path).exists():
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh or re-authorize
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not Path(secrets_path).exists():
                    raise FileNotFoundError(
                        f"client_secrets.json not found at {secrets_path}.\n"
                        "Download it from Google Cloud Console → APIs & Services → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Cache the token
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return creds

    # ── Resumable upload with progress ────────────────────────────────────────

    @staticmethod
    def _resumable_upload(request, max_retries: int = 5):
        import httplib2
        import time
        import random

        response = None
        error = None
        retry = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    log.info("  Upload progress: %d%%", pct)
            except Exception as e:
                error = e
                retry += 1
                if retry > max_retries:
                    raise RuntimeError(f"Upload failed after {max_retries} retries: {e}")
                sleep = (2 ** retry) + random.random()
                log.warning("  Upload error (retry %d/%d in %.1fs): %s", retry, max_retries, sleep, e)
                time.sleep(sleep)

        return response
