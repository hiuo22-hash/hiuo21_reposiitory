import os

from notion_client import Client


class NotionUploader:
    def __init__(self):
        self.client = Client(auth=os.environ["NOTION_TOKEN"])
        self.database_id = os.environ["NOTION_DATABASE_ID"]

    def upload(self, summary: dict):
        title = f"📞 {summary['call_target']} - {summary['call_date']}"

        # 통화 요약 본문
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📝 통화 요약"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary.get("summary", "")}}]
                }
            },
        ]

        # 할일 목록 (to_do 체크박스)
        action_items = summary.get("action_items", [])
        if action_items:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "✅ 할일 목록"}}]
                }
            })
            for item in action_items:
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False
                    }
                })

        if summary.get("filename"):
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"원본 파일: {summary['filename']}"}}],
                    "icon": {"emoji": "📁"}
                }
            })

        # 실제 "업무 관리" DB 스키마에 맞게 매핑
        # 업무내용(title), 요청일(date), 대화상대(text), 우선순위(select), 비고(text)
        self.client.pages.create(
            parent={"database_id": self.database_id},
            properties={
                "업무내용": {
                    "title": [{"type": "text", "text": {"content": title}}]
                },
                "요청일": {
                    "date": {"start": summary["call_date"]}
                },
                "대화상대": {
                    "rich_text": [{"type": "text", "text": {"content": summary["call_target"]}}]
                },
                "비고": {
                    "rich_text": [{"type": "text", "text": {"content": summary.get("summary", "")[:200]}}]
                },
            },
            children=children
        )
        print(f"  노션 업로드 완료: {title}")
