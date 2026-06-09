import os
import json
import re
from datetime import datetime, date

import anthropic
import pytz


class Summarizer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    def summarize(self, transcript: str, filename: str, file_date: str = "") -> dict:
        call_date_guess = (
            self._parse_date_from_filename(filename)
            or self._parse_date_from_string(file_date)
            or datetime.now().strftime('%Y-%m-%d')
        )
        call_target_guess = self._parse_target_from_filename(filename)

        response = self.client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system="""당신은 통화 내용을 분석하는 전문가입니다.
통화 녹음의 텍스트를 분석하여 다음 정보를 반드시 유효한 JSON 형식으로만 반환해주세요.
다른 텍스트, 설명, 마크다운 코드블록 없이 순수한 JSON만 반환하세요.

JSON 구조:
{
  "call_date": "YYYY-MM-DD",
  "call_target": "통화 상대방 이름 또는 전화번호",
  "summary": "통화 내용 핵심 요약 (3-5문장)",
  "action_items": ["할일1", "할일2", ...]
}

통화 상대방을 알 수 없는 경우 파일명에서 추출하거나 "알 수 없음"으로 기재하세요.
할일이 없는 경우 빈 배열([])을 반환하세요.""",
            messages=[{
                "role": "user",
                "content": f"""다음 통화 내용을 분석해주세요.

파일명: {filename}
파일 날짜: {file_date}
참고 날짜 (파싱됨): {call_date_guess}
참고 통화대상 (파싱됨): {call_target_guess or "알 수 없음"}

통화 내용:
{transcript[:8000]}"""
            }]
        )

        text_content = next(
            (block.text for block in response.content if hasattr(block, 'text')),
            ""
        ).strip()

        try:
            result = json.loads(text_content)
        except json.JSONDecodeError:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = {
                    "call_date": call_date_guess,
                    "call_target": call_target_guess or "알 수 없음",
                    "summary": text_content[:500],
                    "action_items": []
                }

        result.setdefault("call_date", call_date_guess)
        result.setdefault("call_target", call_target_guess or "알 수 없음")
        result.setdefault("summary", "")
        result.setdefault("action_items", [])
        result["filename"] = filename
        return result

    def _parse_date_from_filename(self, filename: str) -> str:
        match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', filename)
        if match:
            y, m, d = match.groups()
            try:
                dt = date(int(y), int(m), int(d))
                if 2020 <= dt.year <= 2035:
                    return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return ""

    def _parse_date_from_string(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            kst = pytz.timezone('Asia/Seoul')
            return dt.astimezone(kst).strftime('%Y-%m-%d')
        except Exception:
            return ""

    def _parse_target_from_filename(self, filename: str) -> str:
        phone = re.search(r'(\d{2,3}[-.]?\d{3,4}[-.]?\d{4})', filename)
        if phone:
            return phone.group(1)
        name = re.search(r'[_\s]([가-힣]{2,4})[_\s.]', filename)
        if name:
            return name.group(1)
        return ""
