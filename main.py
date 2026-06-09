import os
import sys
import tempfile
import argparse
from datetime import datetime, timedelta, date

import pytz
from dotenv import load_dotenv

from src.drive_client import DriveClient
from src.transcriber import Transcriber
from src.summarizer import Summarizer
from src.notion_uploader import NotionUploader

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='통화 녹음 일일 요약 및 노션 업로드')
    parser.add_argument(
        '--date',
        type=str,
        help='처리 대상 날짜 (YYYY-MM-DD). 기본값: 어제 (KST)'
    )
    args = parser.parse_args()

    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)

    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = (now_kst - timedelta(days=1)).date()

    print(f"처리 대상 날짜: {target_date}")

    drive = DriveClient()
    transcriber = Transcriber()
    summarizer = Summarizer()
    notion = NotionUploader()

    audio_files = drive.get_call_recordings(target_date)
    if not audio_files:
        print(f"{target_date}에 통화 녹음 파일이 없습니다.")
        return

    results = []
    errors = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for file_info in audio_files:
            filename = file_info['name']
            print(f"\n처리 중: {filename}")
            try:
                local_path = os.path.join(tmpdir, filename)
                drive.download_file(file_info['id'], local_path)
                print(f"  다운로드 완료")

                transcript = transcriber.transcribe(local_path)
                if not transcript.strip():
                    print(f"  빈 녹취록 — 건너뜀")
                    continue
                print(f"  변환 완료 ({len(transcript)}자)")

                summary = summarizer.summarize(
                    transcript=transcript,
                    filename=filename,
                    file_date=file_info.get('modifiedTime', '')
                )
                results.append(summary)
                print(f"  요약 완료: {summary.get('call_target')} | 할일 {len(summary.get('action_items', []))}개")

            except Exception as e:
                print(f"  오류: {e}")
                errors.append({'file': filename, 'error': str(e)})

    for summary in results:
        notion.upload(summary)

    print(f"\n완료! {len(results)}개의 통화 요약이 노션에 업로드되었습니다.")
    if errors:
        print(f"오류 발생 파일 {len(errors)}개:")
        for err in errors:
            print(f"  - {err['file']}: {err['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
