# ChatPDF 프로젝트 구조 (의존 순서)

PDF를 업로드하면 내용을 기반으로 답하는 챗봇. LangChain(RAG) + Gradio. 7인 협업 기준.

RAG 흐름: `Load → Split → Embed → Store → Retrieve → Generate`
파일 하나가 흐름의 한 단계(또는 UI/연결)를 맡고, **파일 소유자 = 도메인 담당자**다.

---

## 1. 최종 폴더 구조

```
chat-pdf/
├── app.py              # [2] Blocks 생성 + ui.render() + 이벤트 연결 (HF Spaces 진입점)
├── requirements.txt    # [7] 배포용 패키지 (langchain<1.0 고정)
├── .env.example        # [7] OPENAI_API_KEY=
├── .gitignore          # [7] .env, .venv, __pycache__, chroma/
├── README.md           # [7]
├── structure.md        # 이 문서
├── src/
│   ├── __init__.py
│   ├── config.py       # 공용 상수 (CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, GENERATE_MODEL, RAG_PROMPT)
│   ├── ui.py           # [1] render() → 컴포넌트 묶음 반환 (이벤트 연결 없음)
│   ├── loader.py       # [3] load_and_split()          ① Load ② Split
│   ├── store.py        # [4] build_db()                ③ Embed ④ Store
│   ├── retriever.py    # [5] get_retriever(), format_docs()   ⑤ Retrieve
│   └── generator.py    # [6] answer()                  ⑥ Generate (스트리밍)
├── tests/
│   ├── test_contract.py   # 모듈 간 시그니처 계약 (변경 시 합의)
│   ├── test_loader.py     # [3]
│   ├── test_store.py      # [4]
│   ├── test_retriever.py  # [5]
│   ├── test_generator.py  # [6]
│   └── test_app.py        # [7] 샘플 PDF로 업로드 → 질문 통합 테스트
└── samples/
    └── sample.pdf      # 팀 공용 테스트 PDF
```

## 2. 담당 도메인

| # | 도메인 | 파일 | 문서상 단계 |
|---|---|---|---|
| 1 | UI 레이아웃 | `src/ui.py` | Step 3 (화면) |
| 2 | 이벤트·상태 연결 | `app.py` | Step 3 (`.upload/.click/.submit`, `gr.State`, `gr.Error`) |
| 3 | 문서 수집·분할 | `src/loader.py` | Step 1 ①② |
| 4 | 임베딩·벡터DB | `src/store.py` | Step 1 ③④ |
| 5 | 검색 | `src/retriever.py` | Step 2 ⑤ |
| 6 | 생성·스트리밍 | `src/generator.py` | Step 2 ⑥ |
| 7 | 인프라·QA·문서 | `requirements.txt`, `.env.example`, `.gitignore`, `tests/test_app.py`, `README.md` | 사전 준비, 배포, 오류표 |

---

## 3. 의존 순서

```
Phase 0  계약 고정 ── config.py + 스텁 + 환경 파일
            │
Phase 1  ┌──┴───────────┬─────────────┬──────────┐   (병렬)
         [1] ui.py    [3] loader.py  [5] retriever.py  [7] 환경/배포
            │             │              │
Phase 2     │         [4] store.py   [6] generator.py (병렬)
            │             │              │
Phase 3     └────────┬────┴──────────────┘
                 [2] app.py  (ui + store + generator 연결)
                     │
Phase 4          [7] 통합 테스트 · 배포
```

### Phase 0. 계약 고정 (선행, 1명이 먼저 푸시)

다른 모든 작업의 전제. 이게 `main`에 올라가야 6명이 동시에 시작할 수 있다.

| 산출물 | 내용 |
|---|---|
| `src/config.py` | 공용 상수 (`CHUNK_SIZE=100`, `CHUNK_OVERLAP=20`, `EMBEDDING_MODEL`, `GENERATE_MODEL`, `RAG_PROMPT`) |
| 각 모듈 스텁 | 아래 시그니처만 있고 본문은 `raise NotImplementedError` (반영 완료) |
| `tests/test_contract.py` | 아래 시그니처가 바뀌면 실패하는 계약 테스트 |
| `requirements.txt` | 패키지 목록 고정 |
| `.gitignore`, `.env.example` | 키 유출 방지 |

**고정할 시그니처 (변경 시 이슈/PR로 합의)**

```python
# src/ui.py
def render() -> SimpleNamespace:
    """openai_key, pdf_file, status, db_state, question, ask_btn, output"""

# src/loader.py
def load_and_split(pdf_path: str) -> list[Document]

# src/store.py
def build_db(pdf_path: str, openai_key: str) -> tuple[Chroma | None, str]
    # 반환 2개 → outputs=[db_state, status] 순서와 일치해야 함

# src/retriever.py
def get_retriever(db: Chroma, llm) -> BaseRetriever
def format_docs(docs: list[Document]) -> str

# src/generator.py
def answer(question: str, openai_key: str, db: Chroma | None) -> Iterator[str]
    # 제너레이터: yield 할 때마다 화면 갱신
```

### Phase 1. 서로 의존 없는 작업 (병렬)

| # | 작업 | 의존 | 완료 기준 |
|---|---|---|---|
| 1 | `ui.py` 레이아웃 | 없음 | `render()`로 화면이 뜬다 |
| 3 | `loader.py` | `config`, `samples/sample.pdf` | 샘플 PDF → `Document` 리스트 반환 |
| 5 | `retriever.py` | `config`, 스텁 `db` | 임시 Chroma로 검색 결과 반환 |
| 7 | 환경 파일, 배포 준비 | 없음 | 새 `.venv`에서 `pip install -r` 성공 |

### Phase 2. 앞 단계 산출물을 쓰는 작업 (병렬)

| # | 작업 | 의존 | 완료 기준 |
|---|---|---|---|
| 4 | `store.py` | `loader` | PDF 경로 → `(db, "✅ 처리 완료…")`, 업로드마다 새 `collection_name` |
| 6 | `generator.py` | `retriever` | 질문 → 토큰 단위 `yield`, 키/DB 없으면 `gr.Error` |

### Phase 3. 통합

| # | 작업 | 의존 | 완료 기준 |
|---|---|---|---|
| 2 | `app.py` | `ui`, `store`, `generator` | `python app.py` → 업로드·질문·스트리밍 동작 |

- `inputs=[...]` 순서는 함수 매개변수 순서와 반드시 일치시킨다 (오류표: "함수 인자가 뒤섞임").
- 1·2번은 4·6번이 스텁이어도 화면 확인이 가능하다. (화면은 뜨고, 이벤트 실행 시 `NotImplementedError`)
- 현재 `ui.render()`와 `app.py`는 문서의 Step 3 레이아웃·연결을 그대로 옮겨 둔 상태다. 1번·2번은 여기서 다듬는다.

### Phase 4. 검증·배포

| # | 작업 | 의존 | 완료 기준 |
|---|---|---|---|
| 7 | `tests/test_app.py`, README, HF Spaces 배포 | 전부 | 샘플 PDF 통합 테스트 통과, 배포 URL 동작 |

배포 시 `sqlite3` 구버전 오류가 나면 `requirements.txt`에 `pysqlite3-binary`를 추가한다.

---

## 4. 협업 규칙

- **파일 소유권**: 자기 파일만 수정한다. 다른 파일의 시그니처 변경은 이슈/PR로 합의한다.
- **`config.py`는 공유 파일**: 값 추가만 허용하고, 변경은 7번이 중재한다.
- **브랜치**: `feat/<도메인>` (예: `feat/loader`). `main` 직접 푸시 금지.
- **키 관리**: 실제 API 키는 커밋하지 않는다. `.env.example`만 공유한다.
