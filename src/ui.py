"""[1] UI(CLI). 처리 함수 연결은 app.py가 담당한다."""

import sys
from collections.abc import Callable, Iterator

from . import config

try:  # input()에 줄 편집·방향키를 켠다. 없으면(Windows) 기본 입력을 쓴다
    import readline  # noqa: F401
except ImportError:
    pass

EXIT_COMMANDS = {"exit", "quit", "q", "종료"}


def run(ask: Callable[[str], Iterator[str]]) -> None:
    """질문을 반복해서 입력받아 답변을 출력한다. 종료 명령·Ctrl-D·Ctrl-C로 끝난다.

    - ask: 질문 하나를 받아 (누적) 답변 텍스트를 yield 하는 함수. 마지막 yield를 출력한다
    - 빈 질문·길이 초과는 ask를 호출하지 않고 안내만 한다
    - ask의 예외는 원문 메시지 없이 예외 종류만 알린다 (키 등 노출 방지)
    """
    print("# ChatPDF")
    print(f"기준 문서: {config.RULE_LABEL}")
    print("표시되는 페이지 번호는 PDF 뷰어 기준(1쪽부터)이며 인쇄된 쪽 번호와 다를 수 있습니다.")
    print(f"종료: {' / '.join(sorted(EXIT_COMMANDS))} 또는 Ctrl-D\n")

    while True:
        try:
            question = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if question.lower() in EXIT_COMMANDS:
            return
        if not question:
            print("질문을 입력하세요.\n")
            continue
        if len(question) > config.MAX_QUESTION_CHARS:
            print(
                f"질문은 {config.MAX_QUESTION_CHARS}자 이하로 입력하세요. "
                f"(현재 {len(question)}자)\n"
            )
            continue

        text = ""
        try:
            for text in ask(question):
                pass
        except KeyboardInterrupt:  # 답변 대기 중 Ctrl-C는 이번 질문만 취소한다
            print("\n질문을 취소했습니다.\n")
            continue
        except Exception as e:
            print(f"⚠️ 답변 중 오류가 발생했습니다. ({type(e).__name__})\n", file=sys.stderr)
            continue
        print(f"\n{text}\n")
