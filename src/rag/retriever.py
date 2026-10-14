"""[5] 검색: ⑤ Retrieve"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


def get_retriever(db: Chroma, llm) -> BaseRetriever:
    """MultiQueryRetriever로 감싼 검색기를 반환한다.

    - llm: 질문을 여러 표현으로 바꾸는 데 쓰는 ChatOpenAI
    - 검색 파라미터(k 등)는 여기서만 조정한다
    """
    raise NotImplementedError


def format_docs(docs: list[Document]) -> str:
    """검색된 문서들을 프롬프트의 context 문자열로 합친다."""
    raise NotImplementedError
