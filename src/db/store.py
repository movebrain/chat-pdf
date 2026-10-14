"""[4] 임베딩·벡터DB: ③ Embed → ④ Store"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from config import EMBEDDING_MODEL
from loader import load_and_split


def build_db(pdf_path: str, openai_key: SecretStr) -> tuple[Chroma | None, str]:
    """PDF → 벡터DB. 반환값은 (db, 상태 메시지).

    - 이벤트의 outputs=[db_state, status] 순서와 일치해야 한다
    - 키가 없으면 (None, 경고 메시지), pdf_path가 None이면 (None, "")
    - 업로드마다 새 collection_name(uuid)을 써서 이전 PDF와 섞이지 않게 한다
    - 청크 분할은 loader.load_and_split()를 호출한다
    """
    documents = load_and_split(pdf_path)
    embeddings_model = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=openai_key,
    )
    db = Chroma.from_documents(documents, embeddings_model, collection_name="team2")
    pages = {(d.metadata.get("source"), d.metadata.get("page")) for d in documents}
    return db, f"✅ 처리 완료: {len(pages)}페이지 → {len(documents)}개 청크"
