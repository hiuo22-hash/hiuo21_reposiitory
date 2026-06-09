import os
import io
import json
import base64
from datetime import date, datetime

import pytz
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials

AUDIO_MIME_TYPES = [
    'audio/mpeg',
    'audio/mp4',
    'audio/x-m4a',
    'audio/wav',
    'audio/x-wav',
    'audio/amr',
    'audio/ogg',
    'audio/webm',
    'audio/3gpp',
    'audio/aac',
]


class DriveClient:
    def __init__(self):
        credentials = self._load_credentials()
        self.service = build('drive', 'v3', credentials=credentials)
        self.folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

    def _load_credentials(self):
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON', '')
        if creds_json:
            try:
                creds_data = json.loads(base64.b64decode(creds_json).decode('utf-8'))
            except Exception:
                creds_data = json.loads(creds_json)
        else:
            creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
            with open(creds_path) as f:
                creds_data = json.load(f)

        return Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

    def get_call_recordings(self, target_date: date) -> list:
        kst = pytz.timezone('Asia/Seoul')
        start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=kst)
        end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=kst)
        start_utc = start_dt.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S')
        end_utc = end_dt.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S')

        mime_conditions = ' or '.join([f"mimeType='{m}'" for m in AUDIO_MIME_TYPES])
        query = (
            f"({mime_conditions})"
            f" and modifiedTime >= '{start_utc}'"
            f" and modifiedTime <= '{end_utc}'"
            f" and trashed = false"
        )
        if self.folder_id:
            query += f" and '{self.folder_id}' in parents"

        files = []
        page_token = None
        while True:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
                pageToken=page_token
            ).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        print(f"  {len(files)}개의 통화 녹음 파일 발견")
        return files

    def download_file(self, file_id: str, local_path: str):
        request = self.service.files().get_media(fileId=file_id)
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
