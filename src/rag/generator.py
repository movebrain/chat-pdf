"""[6] 생성·스트리밍: ⑥ Generate

이 파일은 RAG 파이프라인의 "조립 지점"이다. 직접 검색하거나 프롬프트를 쓰지 않고,
다른 파일의 부품을 순서대로 호출해 Gradio가 쓸 수 있는 형태(누적 문자열 iterator)로 바꾼다.

데이터 흐름 (화살표는 데이터가 넘어가는 방향):

    app.py (Gradio 이벤트)
      │  question, openai_key, db_state(=Chroma), history
      ▼
    generator.answer()                      ← 이 파일
      │  ① 입력 검증        gr.Error → app.py가 연결한 Gradio 화면에 표시
      │  ② ChatOpenAI 생성   config.GENERATE_MODEL 사용 (src/config.py)
      │  ③ retriever.get_retriever(db, llm, ...)  → 검색기
      │  ④ chain.make_chatbot(retriever, llm)     → LCEL 체인
      │  ⑤ chain.stream({question, history}) → 조각 단위 답변
      ▼
    누적 문자열을 yield → app.py가 outputs로 지정한 화면(output)에 계속 덮어써서 표시

이 파일이 하지 않는 일 (각 담당 파일의 책임):
    - 프롬프트 문구, 대화 기록 자리            → prompt.py
    - 후속 질문 재작성(search_question 생성)    → chain.py (+ 문구는 prompt.py)
    - 문서 검색, 출처 문자열 포매팅             → retriever.py
    - history를 messages 형식으로 만드는 일      → Gradio 담당(app.py/ui.py)
"""

from collections.abc import Iterator

import gradio as gr
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI

# 공유 설정. 여기서는 GENERATE_MODEL(생성 모델명)만 읽는다.
# 모델명을 바꾸려면 이 파일이 아니라 src/config.py를 수정한다.
from src import config

# 체인 조립 함수. 입력 dict의 키(question/history/선택적 search_question)는 chain.py가 정한 계약이다.
# chain.py의 make_chatbot() 안에서 prompt.get_prompt()와 retriever.format_docs()가 함께 쓰인다.
from src.rag.chain import make_chatbot

# 검색기 생성 함수. retriever.py의 get_retriever(db, llm, mode="basic")를 호출한다.
# k, fetch_k 같은 세부 값은 retriever.py 안에서 모드별로 고정되어 있어 여기서 넘기지 않는다.
from src.rag.retriever import get_retriever


# ---------------------------------------------------------------------------
# 이 파일이 소유하는 튜닝 값
# 여러 파일이 공유하는 값이 아니므로 config.py가 아니라 여기에 둔다.
# ---------------------------------------------------------------------------

# 검색 모드. retriever.get_retriever()의 mode 인자로 그대로 전달된다.
#   "basic":       질문과 가장 비슷한 4개
#   "mmr":         후보 10개 중 서로 겹치지 않는 3개 (카테고리 필터 없음)
#   "multi_query": LLM으로 질문을 여러 개로 확장해 검색 (LLM 호출이 늘어 느리고 비쌈)
#   "policy", "policy_mmr": metadata의 category가 "장학"/"학칙"인 문서만 검색.
#       loader가 category를 넣어 주지 않으면 결과가 항상 비므로 그 전에는 쓰지 않는다.
# 알 수 없는 모드를 넣으면 get_retriever()가 ValueError를 낸다.
SEARCH_MODE = "mmr"


def answer(
    question: str,
    openai_key: str,
    db: Chroma | None,
    history: list[dict] | None = None,
) -> Iterator[str]:
    """Gradio에서 받은 질문을 처리하고 누적된 답변 문자열을 순서대로 yield 한다.

    이 함수는 사용자 요청 한 건의 오케스트레이션 경계다. 검색, 프롬프트, 체인 구조는
    각 담당 파일이 소유하므로 여기서 직접 구현하지 않고 호출만 한다.
    (대화를 반복하는 루프는 넣지 않는다. 반복은 Gradio 이벤트가 이 함수를 매번 호출해서 이뤄진다.)

    Args:
        question: Gradio 질문 입력란의 문자열. 공백만 있으면 거부한다.
        openai_key: Gradio 비밀번호 입력란의 키. 모델 생성에만 쓰고 로그/화면/에러 메시지에
            넣지 않는다.
        db: 업로드 이벤트에서 store.build_db()가 만들어 gr.State에 저장해 둔 Chroma 객체.
            None이면 아직 PDF가 준비되지 않은 것이다.
        history: 이전 대화. 형식은 ``[{"role": "user" | "assistant", "content": str}, ...]``
            이며 **현재 질문은 포함하지 않는다**(현재 질문은 question으로 따로 받는다).
            gr.Chatbot(type="messages")의 값이 이 형식이다. 변환/정리는 호출하는 쪽(Gradio
            담당)의 책임이고 여기서는 검증하지 않는다. 맨 뒤 인자이며 기본값이 None이라,
            기존 app.py의 inputs=[question, openai_key, db_state] 연결도 그대로 동작한다.

    Yields:
        지금까지 생성된 답변 전체. 조각이 아니라 누적 텍스트다
        (Gradio는 yield마다 출력 컴포넌트를 통째로 덮어쓰기 때문).

    Raises:
        gr.Error: 키/DB/질문이 유효하지 않을 때. 이 함수는 제너레이터라서 검증은
            첫 번째 next() 호출 시점에 실행되며, Gradio가 이를 화면 오류로 표시한다.
        그 외 모델/API 예외는 잡지 않고 그대로 올려 보낸다.
    """
    # ------------------------------------------------------------------
    # ① 입력 검증
    # 값의 출처: app.py의 이벤트 inputs. 순서는 question, openai_key, db_state(, history)다.
    # 검증을 모델 호출 전에 끝내서 불필요한 API 비용과 알아보기 어려운 오류를 막는다.
    # ------------------------------------------------------------------
    if not openai_key or not openai_key.strip():
        # 메시지에 키 값을 넣지 않는다.
        raise gr.Error("OpenAI API 키를 입력하세요.")
    if db is None:
        # db는 store.build_db()의 반환값(db_state)이다. 업로드 전이거나 업로드가 실패하면 None이다.
        raise gr.Error("먼저 PDF를 업로드하세요.")
    if not question or not question.strip():
        raise gr.Error("질문을 입력하세요.")

    question = question.strip()

    # ------------------------------------------------------------------
    # ② 언어 모델 생성
    # API 키로 모델을 만드는 일은 이 함수의 책임이다(chain.py는 만들어진 llm만 받는다).
    # 같은 llm 인스턴스를 두 곳이 공유한다:
    #   - get_retriever(): mode="multi_query"일 때 질문 확장
    #   - make_chatbot(): 최종 답변 생성
    # temperature=0은 같은 질문에 같은 답이 나오도록 해 근거 기반 답변의 일관성을 높인다.
    # streaming=True는 chain.stream()에서 토큰 단위 출력을 받기 위한 설정이다.
    # ------------------------------------------------------------------
    llm = ChatOpenAI(
        model=config.GENERATE_MODEL,
        api_key=openai_key.strip(),
        temperature=0,
        streaming=True,
    )

    # ------------------------------------------------------------------
    # ③ 검색기 생성 → retriever.py의 get_retriever()
    # db: 검색 대상 Chroma 벡터DB (store.build_db()가 만든 것)
    # llm: multi_query 모드에서만 사용되고, 다른 모드에서는 무시된다.
    # 검색 방식을 바꾸려면 이 파일 위쪽의 SEARCH_MODE 상수만 수정하면 된다.
    # ------------------------------------------------------------------
    retriever = get_retriever(db, llm, mode=SEARCH_MODE)

    # ------------------------------------------------------------------
    # ④ 체인 조립 → chain.py의 make_chatbot()
    # 반환되는 체인의 내부 흐름(chain.py):
    #   question → retriever → retriever.format_docs() → 프롬프트의 {context}
    #   question / history → prompt.get_prompt()의 {question} / MessagesPlaceholder("history")
    #   → llm → StrOutputParser() → 문자열 조각
    # 여기서는 연결된 체인만 받고, 아직 아무 답변도 생성하지 않는다.
    # ------------------------------------------------------------------
    chain = make_chatbot(retriever, llm)

    # ------------------------------------------------------------------
    # ⑤ 스트리밍 실행과 누적 yield
    # 입력 dict의 키는 chain.py가 읽는 이름과 정확히 같아야 한다.
    #   "question": 사용자가 쓴 원문 / "history": 이전 대화
    # 검색에는 question만 쓰이고 history는 답변 프롬프트에만 전달된다(chain.py 현재 구현).
    # 그래서 "그건 언제까지야?" 같은 후속 질문은 이 문장 그대로 검색된다.
    # history가 None이면 prompt의 MessagesPlaceholder가 오류를 내므로 빈 리스트로 바꿔 전달한다.
    # chain.stream()은 답변 조각(str)을 하나씩 내놓는다.
    # 조각만 yield하면 Gradio 화면에 마지막 조각만 남으므로 이어 붙인 전체를 yield한다.
    # try/except로 감싸지 않는다: 키 오류 등 API 예외는 숨기지 않고 그대로 전달한다.
    # ------------------------------------------------------------------
    #
    # 출처 표시(합의 예정인 chain.py 계약): 체인이 {"answer": 조각}과 {"sources": 문자열}
    # 모양의 조각을 내보낸다. sources는 한 번만 오고 answer보다 먼저 올 수도 있으므로
    # 도착 순서와 상관없이 모아 두었다가, 답변이 끝난 뒤 맨 아래에 붙여 마지막으로 한 번 더 yield한다.
    # 임시 호환: 현재 chain.py처럼 문자열 조각을 내보내면 예전 방식 그대로 처리한다.
    #             chain.py가 dict 출력으로 바뀌어 안정되면 str 분기는 삭제해도 된다.
    text = ""
    sources = ""
    for chunk in chain.stream({"question": question, "history": history or []}):
        if isinstance(chunk, str):
            text += chunk
        else:
            text += chunk.get("answer", "")
            sources = chunk.get("sources", sources)
        yield text

    if sources:
        yield f"{text}\n\n**참고 출처:** {sources}"

    # 실제 사용 코드 위에 코드들 지우고 아래의 코드로 대체
    # text = ""
    #     for chunk in chain.stream({"question": question, "history": history or []}):
    #         text += chunk
    #         yield text