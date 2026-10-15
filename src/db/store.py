"""[4] 임베딩·벡터DB: ③ Embed → ④ Store"""

import uuid

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from ..config import EMBEDDING_MODEL
from .loader import load_and_split


def build_db(pdf_path: str) -> Chroma:
    """PDF → 인메모리 벡터DB.

    - 앱 시작 시 한 번 호출한다. 키·PDF 누락 검사는 app.py가 먼저 한다
    - API 키는 환경변수 OPENAI_API_KEY에서 읽는다 (인자로 받지 않는다)
    - 청크 분할·문서 검수는 loader.load_and_split()가 하고, 검수 실패는 ValueError로 올라온다
    - 청크가 하나도 없으면 임베딩 전에 ValueError를 낸다
    - 임베딩 실패는 감싸지 않는다. 원문 메시지는 호출하는 쪽이 숨긴다
    - 호출마다 새 collection_name(uuid)을 써서 같은 프로세스의 다른 DB와 섞이지 않게 한다
    """
    documents = load_and_split(pdf_path)
    if not documents:
        raise ValueError(f"PDF에서 청크를 만들지 못했습니다: {pdf_path}")

    embeddings_model = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return Chroma.from_documents(
        documents, embeddings_model, collection_name=f"pdf-{uuid.uuid4().hex}"
    )
