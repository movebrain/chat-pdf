"""[3] 문서 수집·분할: ① Load → ② Split"""

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .. import config


def load_and_split(pdf_path: str) -> list[Document]:
    """PDF를 읽어 청크(Document) 리스트로 반환한다.

    - PyPDFLoader + RecursiveCharacterTextSplitter
    - 크기는 config.CHUNK_SIZE / CHUNK_OVERLAP 사용
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    pages = PyPDFLoader(pdf_path).load()
    return splitter.split_documents(pages)
