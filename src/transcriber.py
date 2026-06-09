import os

from openai import OpenAI

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB Whisper API limit


class Transcriber:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    def transcribe(self, audio_path: str) -> str:
        file_size = os.path.getsize(audio_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB (한도: 25MB) — {audio_path}"
            )

        with open(audio_path, 'rb') as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",
                response_format="text"
            )

        return response
