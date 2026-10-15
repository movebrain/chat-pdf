# 여러 사람이 쓰는 값을 한곳에 모아 둡니다.

from pathlib import Path

# 앱 시작 시 임베딩할 PDF. 파일을 교체하면 RULE_LABEL도 함께 맞춘다.
PDF_PATH = str(Path(__file__).resolve().parent.parent / "resources" / "snu-rule.pdf")
RULE_LABEL = "서울대학교학칙 제2347호 (시행 2022.2.23.) — 샘플, 기준 문서(제2710호) 아님"
MAX_QUESTION_CHARS = 300

# 예시
CHUNK_SIZE = 100
CHUNK_OVERLAP = 20
EMBEDDING_MODEL = "text-embedding-3-large"
GENERATE_MODEL = "gpt-4o-mini"
RAG_PROMPT = "rlm/rag-prompt"