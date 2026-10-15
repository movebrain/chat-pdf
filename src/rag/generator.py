"""[6] 생성·스트리밍: ⑥ Generate

이 파일은 RAG 파이프라인의 "조립 지점"이다. 직접 검색하거나 프롬프트를 쓰지 않고,
다른 파일의 부품을 순서대로 호출해 UI가 쓸 수 있는 형태(누적 문자열 iterator)로 바꾼다.

데이터 흐름 (화살표는 데이터가 넘어가는 방향):

    app.py (시작 시 build_db(PDF)로 만든 db를 partial(answer, db=db)로 연결)
      │  question, db(=Chroma), history(선택)
      ▼
    generator.answer()                      ← 이 파일
      │  ① 입력 검증        gr.Error → UI가 사용자에게 표시
      │  ② ChatOpenAI 생성   config.GENERATE_MODEL 사용, API 키는 환경변수 OPENAI_API_KEY
      │  ③ retriever.get_retriever(db, llm, ...)  → 검색기
      │  ④ chain.make_chatbot(retriever, llm)     → LCEL 체인
      │  ⑤ chain.stream({question, history}) → 조각 단위 답변
      ▼
    누적 문자열을 yield → UI가 화면에 계속 덮어써서 표시 (CLI는 마지막 yield만 출력)

이 파일이 하지 않는 일 (각 담당 파일의 책임):
    - 프롬프트 문구, 대화 기록 자리            → prompt.py
    - 후속 질문 재작성(search_question 생성)    → chain.py (+ 문구는 prompt.py)
    - 문서 검색, 출처 문자열 포매팅             → retriever.py
    - history를 messages 형식으로 만드는 일      → Gradio 담당(app.py/ui.py)
"""

import os
from collections.abc import Iterator

import gradio as gr
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI

# 공유 설정. 여기서는 GENERATE_MODEL(생성 모델명)과 SEARCH_MODE(기본 검색 모드)를 읽는다.
# 모델명을 바꾸려면 이 파일이 아니라 src/config.py를, 검색 모드는 .env의 SEARCH_MODE를 수정한다.
from src import config

# 체인 조립 함수. 입력 dict의 키(question/history/선택적 search_question)는 chain.py가 정한 계약이다.
# chain.py의 make_chatbot() 안에서 prompt.get_prompt()와 retriever.format_docs()가 함께 쓰인다.
from src.rag.chain import make_chatbot

# 검색기 생성 함수. retriever.py의 get_retriever(db, llm, mode="basic")를 호출한다.
# k, fetch_k 같은 세부 값은 retriever.py 안에서 모드별로 고정되어 있어 여기서 넘기지 않는다.
from src.rag.retriever import get_retriever


# 기본 검색 모드. retriever.get_retriever()의 mode 인자로 그대로 전달된다.
# 값은 .env의 SEARCH_MODE에서 오며(config.py), 웹 UI·manual_chat이 이 이름으로 가져다 쓴다.
#   "basic":       질문과 가장 비슷한 4개 (기본값, 평가에서 mmr보다 정답 근거를 더 많이 찾음)
#   "mmr":         후보 10개 중 서로 겹치지 않는 3개 (카테고리 필터 없음)
#   "multi_query": LLM으로 질문을 여러 개로 확장해 검색 (LLM 호출이 늘어 느리고 비쌈)
#   "policy", "policy_mmr": metadata의 category가 get_retriever의 category 인자와 같은 문서만 검색.
#       category를 고르는 choose_category() 호출이 아직 연결되어 있지 않아 쓰지 않는다.
# 알 수 없는 모드를 넣으면 get_retriever()가 ValueError를 낸다.
SEARCH_MODE = config.SEARCH_MODE


def answer(
    question: str,
    db: Chroma | None,
    history: list[dict] | None = None,
    mode: str | None = None,
) -> Iterator[str]:
    """질문 한 건을 처리하고 누적된 답변 문자열을 순서대로 yield 한다.

    이 함수는 사용자 요청 한 건의 오케스트레이션 경계다. 검색, 프롬프트, 체인 구조는
    각 담당 파일이 소유하므로 여기서 직접 구현하지 않고 호출만 한다.
    (대화를 반복하는 루프는 넣지 않는다. 반복은 UI가 이 함수를 질문마다 호출해서 이뤄진다.)

    호출 예: ``ui.run(partial(answer, db=db))`` → UI는 ``ask(question)``만 호출한다.

    Args:
        question: 사용자가 입력한 질문. 공백만 있으면 거부한다.
        db: 앱 시작 시 store.build_db(PDF_PATH)가 만든 Chroma 객체.
            None이면 DB가 준비되지 않은 것이다.
        history: 이전 대화(선택). 형식은 ``[{"role": "user" | "assistant", "content": str}, ...]``
            이며 **현재 질문은 포함하지 않는다**(현재 질문은 question으로 따로 받는다).
            Gradio 6의 gr.Chatbot은 content를 블록 리스트로 주므로 문자열로 바꾸는 일은
            호출하는 쪽(src/web/handlers.py)의 책임이고 여기서는 검증하지 않는다.
            CLI처럼 대화 기록이 없으면 생략한다.
        mode: 검색 모드(선택). retriever.get_retriever()의 mode로 전달된다.
            None이면 이 파일의 SEARCH_MODE를 쓴다. 웹 UI의 "검색 설정"에서 넘어온다.

    API 키는 인자로 받지 않고 환경변수 OPENAI_API_KEY에서 읽는다(ChatOpenAI가 직접 읽는다).
    환경변수 로드(.env)는 app.py가 담당한다.

    Yields:
        지금까지 생성된 답변 전체. 조각이 아니라 누적 텍스트다
        (Gradio는 yield마다 출력 컴포넌트를 통째로 덮어쓰기 때문).

    Raises:
        gr.Error: 키/DB/질문이 유효하지 않을 때. 이 함수는 제너레이터라서 검증은
            첫 번째 next() 호출 시점에 실행된다.
        그 외 모델/API 예외는 잡지 않고 그대로 올려 보낸다.
    """
    # ------------------------------------------------------------------
    # ① 입력 검증
    # 검증을 모델 호출 전에 끝내서 불필요한 API 비용과 알아보기 어려운 오류를 막는다.
    # ------------------------------------------------------------------
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        # 메시지에 키 값을 넣지 않는다.
        raise gr.Error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    if db is None:
        # db는 store.build_db()의 반환값이다. 시작 시 임베딩이 실패하면 None일 수 있다.
        raise gr.Error("문서 DB가 준비되지 않았습니다.")
    if not question or not question.strip():
        raise gr.Error("질문을 입력하세요.")

    question = question.strip()

    # ------------------------------------------------------------------
    # ② 언어 모델 생성
    # 모델을 만드는 일은 이 함수의 책임이다(chain.py는 만들어진 llm만 받는다).
    # API 키는 넘기지 않는다: ChatOpenAI가 환경변수 OPENAI_API_KEY를 직접 읽는다.
    # 같은 llm 인스턴스를 두 곳이 공유한다:
    #   - get_retriever(): mode="multi_query"일 때 질문 확장
    #   - make_chatbot(): 최종 답변 생성
    # temperature=0은 같은 질문에 같은 답이 나오도록 해 근거 기반 답변의 일관성을 높인다.
    # streaming=True는 chain.stream()에서 토큰 단위 출력을 받기 위한 설정이다.
    # ------------------------------------------------------------------
    llm = ChatOpenAI(
        model=config.GENERATE_MODEL,
        temperature=0,
        streaming=True,
    )

    # ------------------------------------------------------------------
    # ③ 검색기 생성 → retriever.py의 get_retriever()
    # db: 검색 대상 Chroma 벡터DB (store.build_db()가 만든 것)
    # llm: multi_query 모드에서만 사용되고, 다른 모드에서는 무시된다.
    # mode 인자가 없으면 이 파일 위쪽의 SEARCH_MODE 상수(기본값)를 쓴다.
    # ------------------------------------------------------------------
    retriever = get_retriever(db, llm, mode=mode or SEARCH_MODE)

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
    #
    # 출처 표시: 별도로 붙이지 않는다. retriever.format_docs()가 참고자료 끝에
    # [검색된 참고자료 목록]을 넣고, prompt.py 규칙에 따라 모델이 답 끝에
    # "(출처: 서울대학교 학칙 p.N)"을 직접 쓴다. 그래서 답변 문자열에 출처가 이미 포함된다.
    # ------------------------------------------------------------------
    text = ""
    for chunk in chain.stream({"question": question, "history": history or []}):
        text += chunk
        yield text