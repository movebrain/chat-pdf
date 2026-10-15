# 여러 사람이 쓰는 값을 한곳에 모아 둡니다.

from pathlib import Path

# 앱이 불러올 학칙 PDF (프로젝트 루트의 data 폴더)
PDF_PATH = str(Path(__file__).resolve().parent.parent / "data" / "서울대학교 학칙.pdf")

# 예시
CHUNK_SIZE = 100
CHUNK_OVERLAP = 20
EMBEDDING_MODEL = "text-embedding-3-large"
GENERATE_MODEL = "gpt-4o-mini"