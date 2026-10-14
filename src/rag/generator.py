"""[6] 생성·스트리밍: ⑥ Generate"""

from collections.abc import Iterator

from langchain_chroma import Chroma


def answer(question: str, openai_key: str, db: Chroma | None) -> Iterator[str]:
    """질문에 답하며 누적 텍스트를 yield 한다 (Gradio가 yield마다 화면 갱신).

    - 반드시 제너레이터(yield)로 구현한다
    - db가 None이거나 question이 비어 있으면 gr.Error를 발생시킨다
    - 검색은 retriever.get_retriever() / format_docs()를 사용한다
    - 모델/프롬프트는 config.GENERATE_MODEL / RAG_PROMPT 사용
    """
    raise NotImplementedError
