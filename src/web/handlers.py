"""웹 UI 이벤트 함수. 화면(layout.py)과 DB(store.py)·RAG(generator.py) 사이를 잇는다.

벡터DB는 PDF가 하나로 고정되어 있어 프로세스당 한 번만 만들고 모든 사용자가 같이 쓴다
(브라우저를 새로 열 때마다 임베딩하면 시간과 API 비용이 반복되기 때문).
"""

import os
import threading
from collections.abc import Iterator
from pathlib import Path

import gradio as gr

from src import config
from src.db.store import build_db
from src.rag.generator import answer

_db = None          # build_db()가 만든 Chroma. 아직 없으면 None
_status = ""        # 마지막으로 성공한 불러오기 결과 문구
_lock = threading.Lock()   # 여러 사용자가 동시에 접속해도 임베딩은 한 번만 하도록 막는다


def _loaded_status(db) -> str:
    """DB에 들어간 청크의 쪽수와 개수로 상태 문구를 만든다."""
    metadatas = db.get(include=["metadatas"])["metadatas"]
    pages = {m.get("page") for m in metadatas}
    return (
        f"✅ 서울대학교 학칙을 불러왔습니다({len(pages)}쪽, {len(metadatas)}개 청크). "
        "이제 질문해보세요."
    )


def _load(force: bool) -> str:
    """DB를 만들고 상태 문구를 반환한다. force=False면 이미 만든 DB를 재사용한다."""
    global _db, _status
    with _lock:
        if _db is not None and not force:
            return _status
        if not os.environ.get("OPENAI_API_KEY"):
            return "❌ OPENAI_API_KEY 환경변수가 없습니다. 프로젝트 루트의 .env를 확인하세요."
        if not Path(config.PDF_PATH).is_file():
            return f"❌ PDF 파일이 없습니다: {config.PDF_PATH}"
        try:
            db = build_db(config.PDF_PATH)
        except ValueError as e:      # 문서 검수 실패 (store/loader가 이유를 담아 올린다)
            return f"❌ 문서 검수 실패: {e}"
        except Exception as e:       # 임베딩 실패 등: 원문에 키가 섞일 수 있어 종류만 보여준다
            return f"❌ 학칙을 불러오지 못했습니다 ({type(e).__name__})"
        _db, _status = db, _loaded_status(db)
        return _status


def load_db() -> Iterator[str]:
    """페이지가 열릴 때 실행. 처음 한 번만 임베딩하고 이후에는 만들어 둔 DB를 쓴다."""
    if _db is None:
        yield "⏳ 학칙을 불러오는 중입니다..."
    yield _load(force=False)


def reload_db() -> Iterator[str]:
    """[학칙 불러오기] 버튼. PDF를 다시 읽어 DB를 새로 만든다(PDF를 교체했을 때 사용)."""
    yield "⏳ 학칙을 다시 불러오는 중입니다..."
    yield _load(force=True)


def _to_text(content) -> str:
    """Gradio 6 Chatbot의 content(문자열 또는 블록 리스트)를 문자열로 바꾼다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _to_history(chat: list) -> list[dict]:
    """화면의 대화 목록을 answer()가 받는 history 형식으로 바꾼다.

    answer()의 계약: [{"role": "user" | "assistant", "content": str}, ...]
    """
    history = []
    for message in chat:
        role = message.get("role")
        text = _to_text(message.get("content"))
        if role in ("user", "assistant") and text:
            history.append({"role": role, "content": text})
    return history


def respond(question: str, chat: list | None, mode: str) -> Iterator[tuple[list, str]]:
    """[질문하기]/Enter. 질문을 대화에 추가하고 답변을 실시간으로 채운다.

    Yields:
        (대화 목록, 질문 입력란 값). 질문 입력란은 비워서 다음 질문을 바로 쓸 수 있게 한다.
    """
    chat = list(chat or [])
    question = (question or "").strip()
    if not question:
        yield chat, ""
        return
    if _db is None:
        raise gr.Error("학칙을 아직 불러오지 못했습니다. 왼쪽의 [학칙 불러오기]를 눌러 주세요.")

    history = _to_history(chat)    # 현재 질문을 넣기 전의 대화만 history로 넘긴다
    chat.append({"role": "user", "content": question})
    chat.append({"role": "assistant", "content": ""})
    yield chat, ""

    try:
        for text in answer(question, _db, history, mode=mode):
            chat[-1] = {"role": "assistant", "content": text}
            yield chat, ""
    except Exception as e:
        # gr.Error는 사용자용 문구라 그대로, 그 외(API 오류 등)는 키 노출을 막으려고 종류만 보여준다
        message = e.message if isinstance(e, gr.Error) else f"답변 생성 중 오류가 발생했습니다 ({type(e).__name__})"
        chat[-1] = {"role": "assistant", "content": f"⚠️ {message}"}
        yield chat, ""


def clear() -> tuple[list, str]:
    """[대화 지우기]. 대화 목록과 입력란을 비운다."""
    return [], ""
