"""[3] 문서 수집·분할: ① Load → ② Split"""

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config


def load_and_split(pdf_path: str) -> list[Document]:
    """PDF를 읽어 청크(Document) 리스트로 반환한다.

    - PyPDFLoader + RecursiveCharacterTextSplitter
    - 크기는 config.CHUNK_SIZE / CHUNK_OVERLAP 사용
    - 메타데이터: source(파일 경로), page(0부터)를 PyPDFLoader가 붙여주며, 자르면서도 그대로 유지된다
    """

    # ① Load: PDF를 페이지 단위 Document 리스트로 읽기
    pages = PyPDFLoader(pdf_path).load()

    # ② Split: config의 크기대로 청크로 자르기
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP,
    )
    return splitter.split_documents(pages)
