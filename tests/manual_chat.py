"""터미널에서 실제 PDF로 챗봇을 직접 테스트하는 스크립트 (수동 테스트용).

실행 (프로젝트 루트에서):
    python -m tests.manual_chat                      # 기본 PDF: data/서울대학교 학칙.pdf
    python -m tests.manual_chat "다른/파일.pdf"       # 다른 PDF로 테스트

필요한 것:
    - pip install -r requirements.txt
    - 환경변수 OPENAI_API_KEY (또는 프로젝트 루트의 .env, python-dotenv가 설치돼 있을 때)

사용법:
    질문을 입력하면 답변이 실시간으로 출력된다. 이전 대화는 history로 함께 전달된다.
    /debug  : 질문마다 검색된 청크(page, category, 본문)를 함께 보여준다 (켜기/끄기)
    /reset  : 대화 기록 초기화
    exit, quit, q, 종료 : 끝내기
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = ROOT / "data" / "서울대학교 학칙.pdf"
EXIT_COMMANDS = {"exit", "quit", "q", "종료"}


def main() -> int:
    try:  # .env는 python-dotenv가 있을 때만 읽는다
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 환경변수가 없습니다.", file=sys.stderr)
        return 1
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.is_file():
        print(f"PDF 파일이 없습니다: {pdf_path}", file=sys.stderr)
        return 1

    from src.db.store import build_db
    from src.rag import generator
    from src.rag.retriever import format_docs, get_retriever

    print(f"PDF 임베딩 중... ({pdf_path.name})")
    try:
        db = build_db(str(pdf_path))
    except Exception as e:  # 원문 메시지에 키가 섞일 수 있어 종류만 출력
        print(f"DB 생성 실패 ({type(e).__name__})", file=sys.stderr)
        return 1
    print(f"준비 완료. 검색 모드={generator.SEARCH_MODE}  (/debug, /reset, exit)\n")

    history: list[dict] = []
    debug = False
    while True:
        try:
            question = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if question.lower() in EXIT_COMMANDS:
            return 0
        if question == "/debug":
            debug = not debug
            print(f"검색 청크 보기: {'켜짐' if debug else '꺼짐'}\n")
            continue
        if question == "/reset":
            history.clear()
            print("대화 기록을 지웠습니다.\n")
            continue
        if not question:
            continue

        printed = ""
        search: dict = {}   # generator.answer()가 정한 검색 범위 (category, mode)
        try:
            for text in generator.answer(
                question, db, history,
                on_search=lambda category, mode: search.update(category=category, mode=mode),
            ):
                print(text[len(printed):], end="", flush=True)   # 누적 텍스트에서 새로 생긴 부분만 출력
                printed = text
        except KeyboardInterrupt:
            print("\n(답변 취소)\n")
            continue
        except Exception as e:  # 원문 메시지에 키가 섞일 수 있어 종류만 출력
            print(f"\n오류가 발생했습니다 ({type(e).__name__})\n")
            continue
        print("\n")
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": printed}]

        if debug and search and search["mode"] != "multi_query":
            # answer()가 실제로 쓴 검색 범위(mode, category)로 다시 검색해, retriever가 넘긴 청크를 보여준다
            docs = get_retriever(db, None, mode=search["mode"], category=search["category"]).invoke(question)
            print(f"--- 검색 범위: {search['category'] or '학칙 전체'} (mode={search['mode']}) / 청크 {len(docs)}개 ---")
            for d in docs:
                print(f"[page={d.metadata.get('page')} category={d.metadata.get('category')}] "
                      f"{d.page_content[:80]!r}")
            print("--- format_docs() 결과 (프롬프트의 {context}) ---")
            print(format_docs(docs))
            print("---\n")


if __name__ == "__main__":
    sys.exit(main())
