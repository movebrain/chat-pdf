"""[2] 진입점: 시작 시 PDF 임베딩을 한 번 하고, 화면(ui)에 답변 함수(generator)를 연결한다."""

import os
import sys
from functools import partial
from pathlib import Path

from src import config, ui
from src.db.store import build_db
from src.rag.generator import answer

try:  # 로컬 테스트용 .env. 설치돼 있을 때만 읽는다 (배포에서는 플랫폼 secret이 환경변수로 들어온다)
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def main() -> int:
    if load_dotenv:
        load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 환경변수가 없습니다. .env.example을 참고하세요.", file=sys.stderr)
        return 1
    if not Path(config.PDF_PATH).is_file():
        print(f"PDF 파일이 없습니다: {config.PDF_PATH}", file=sys.stderr)
        return 1

    print(f"PDF 임베딩 중... ({Path(config.PDF_PATH).name})")
    try:
        db = build_db(config.PDF_PATH)
    except ValueError as e:  # 문서 검수 실패: 조·페이지·이유가 담긴 메시지
        print(f"문서 검수 실패: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 임베딩 실패 등: 원문 메시지에 키가 섞일 수 있어 종류만 알린다
        print(f"PDF 임베딩에 실패했습니다. ({type(e).__name__})", file=sys.stderr)
        return 1

    ui.run(partial(answer, db=db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
