# 여러 사람이 쓰는 값을 한곳에 모아 둡니다.

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 프로젝트 루트의 .env를 읽는다. python-dotenv가 없으면 건너뛴다.
# app.py는 이 모듈을 import한 뒤에 load_dotenv()를 부르므로 여기서 먼저 읽어야 아래 값에 반영된다.
# 이미 설정된 환경변수(배포 서버 등)는 덮어쓰지 않는다.
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(ROOT / ".env")

# 앱이 불러올 학칙 PDF (프로젝트 루트의 data 폴더)
PDF_PATH = str(ROOT / "data" / "서울대학교 학칙.pdf")

# 청크 크기·오버랩(글자 수)과 검색 모드는 .env에서 바꿀 수 있다. 값이 없으면 아래 기본값을 쓴다.
# 기본값은 eval/questions.jsonl 평가로 고른 값이다 (1200/120 + basic).
#   SEARCH_MODE: "basic"(가장 비슷한 4개) | "mmr" | "multi_query" | "policy" | "policy_mmr"
#                알 수 없는 값은 retriever.get_retriever()가 ValueError를 낸다.
#   빈 값(CHUNK_SIZE=)은 기본값으로 보고, 숫자가 아닌 값은 오타를 숨기지 않도록 시작할 때 오류를 낸다.
def _env(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default))
    if not value.isdigit():
        raise ValueError(f"환경변수 {name}는 0 이상의 정수여야 합니다: {value!r}")
    return int(value)


CHUNK_SIZE = _env_int("CHUNK_SIZE", 1200)
CHUNK_OVERLAP = _env_int("CHUNK_OVERLAP", 120)
SEARCH_MODE = _env("SEARCH_MODE", "basic")
EMBEDDING_MODEL = "text-embedding-3-large"
GENERATE_MODEL = "gpt-4o-mini"
