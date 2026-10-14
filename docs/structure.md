# ChatPDF 프로젝트 구조 (의존 순서)

PDF를 업로드하면 내용을 기반으로 답하는 챗봇. LangChain(RAG) + Gradio.
2명씩 3파트(Gradio / DB 저장 / RAG)로 나눠 작업한다.

RAG 흐름: `Load → Split → Embed → Store → Retrieve → Generate`
폴더 하나가 한 파트이고, 파트 안에서는 **파일 하나 = 한 명**이 맡는다.

---

## 1. 폴더 구조

```
chat-pdf/
├── app.py               # [Gradio] ui.render() + 이벤트 연결 (HF Spaces 진입점)
├── requirements.txt     # 배포용 패키지 (langchain<1.0 고정)
├── .env.example         # OPENAI_API_KEY=
├── .gitignore           # .env, .venv, __pycache__
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py        # 공용 상수 (CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, GENERATE_MODEL, RAG_PROMPT)
│   ├── ui.py            # [Gradio] render() → 컴포넌트 묶음 반환 (이벤트 연결 없음)
│   ├── db/              # [DB 저장]
│   │   ├── loader.py    #   load_and_split()   ① Load ② Split
│   │   └── store.py     #   build_db()         ③ Embed ④ Store
│   └── rag/             # [RAG]
│       ├── retriever.py #   get_retriever(), format_docs()   ⑤ Retrieve
│       └── generator.py #   answer()           ⑥ Generate (스트리밍)
├── docs/
│   ├── structure.md     # 이 문서
│   └── sources.md       # 참고 자료
└── eval/                # 평가용 (현재 비어 있음)
```

## 2. 담당 파트

| 파트 | 파일 | 한 명씩 | 문서상 단계 |
| --- | --- | --- | --- |
| **Gradio** | `src/ui.py`, `app.py` | 화면 / 이벤트·상태 연결 | Step 3 (`.upload/.click/.submit`, `gr.State`, `gr.Error`) |
| **DB 저장** | `src/db/loader.py`, `src/db/store.py` | 분할 / 임베딩·저장 | Step 1 ①~④ |
| **RAG** | `src/rag/retriever.py`, `src/rag/generator.py` | 검색 / 생성·스트리밍 | Step 2 ⑤⑥ |

7번째 인원의 역할(통합 테스트, HF Spaces 배포, 환경 관리)은 아직 정하지 않았다.

---

## 3. 의존 순서

```
Phase 0  계약 고정 (스텁, config.py)                       ← 완료
            │
Phase 1  ┌──┴──────────────┬──────────────────┐   (병렬)
      [Gradio] ui.py   [DB] loader.py     [RAG] retriever.py
            │                │                  │
Phase 2     │          [DB] store.py      [RAG] generator.py   (병렬)
            │                │                  │
Phase 3     └───────────┬────┴──────────────────┘
                  [Gradio] app.py  (ui + store + generator 연결)
                        │
Phase 4            통합 테스트 · 배포
```

### Phase 0. 계약 고정 (완료)

각 모듈은 시그니처만 있고 본문은 `raise NotImplementedError`다. 아래 시그니처가 파트 사이의 유일한 접점이며, 바꿀 때는 영향받는 파트와 이슈/PR로 먼저 합의한다.

```python
# src/ui.py
def render() -> SimpleNamespace:
    """openai_key, pdf_file, status, db_state, question, ask_btn, output"""

# src/db/loader.py
def load_and_split(pdf_path: str) -> list[Document]

# src/db/store.py
def build_db(pdf_path: str | None, openai_key: str) -> tuple[Chroma | None, str]
    # 반환 2개 → outputs=[db_state, status] 순서와 일치해야 함

# src/rag/retriever.py
def get_retriever(db: Chroma, llm) -> BaseRetriever
def format_docs(docs: list[Document]) -> str

# src/rag/generator.py
def answer(question: str, openai_key: str, db: Chroma | None) -> Iterator[str]
    # 제너레이터: yield 할 때마다 화면 갱신
```

### Phase 1. 서로 의존 없는 작업 (병렬)

| 파트 | 작업 | 의존 | 완료 기준 |
| --- | --- | --- | --- |
| Gradio | `ui.py` 레이아웃 | 없음 | `render()`로 화면이 뜬다 |
| DB 저장 | `loader.py` | `config`, 테스트용 PDF | PDF → `Document` 리스트 반환 |
| RAG | `retriever.py` | `config`, 임시 `db` | 임시 Chroma로 검색 결과 반환 |

RAG 파트는 DB 파트를 기다리지 않는다. `langchain_core.embeddings.DeterministicFakeEmbedding`으로 임시 Chroma를 만들면 API 키 없이 검색 로직을 테스트할 수 있다.

### Phase 2. 앞 단계 산출물을 쓰는 작업 (병렬)

| 파트 | 작업 | 의존 | 완료 기준 |
| --- | --- | --- | --- |
| DB 저장 | `store.py` | `loader` | PDF 경로 → `(db, "✅ 처리 완료…")`, 업로드마다 새 `collection_name` |
| RAG | `generator.py` | `retriever` | 질문 → 토큰 단위 `yield`, 키/DB 없으면 `gr.Error` |

### Phase 3. 통합

| 파트 | 작업 | 의존 | 완료 기준 |
| --- | --- | --- | --- |
| Gradio | `app.py` | `ui`, `store`, `generator` | `python app.py` → 업로드·질문·스트리밍 동작 |

- `inputs=[...]` 순서는 함수 매개변수 순서와 반드시 일치시킨다 (오류표: "함수 인자가 뒤섞임").
- store·generator가 스텁이어도 화면은 뜬다. 이벤트를 실행할 때만 `NotImplementedError`가 난다.
- 현재 `ui.render()`와 `app.py`는 문서의 Step 3 레이아웃·연결을 그대로 옮겨 둔 상태다. Gradio 파트는 여기서 다듬는다.

### Phase 4. 검증·배포

샘플 PDF로 업로드 → 질문 → 스트리밍 응답까지 확인하고 HF Spaces에 배포한다.
배포 시 `sqlite3` 구버전 오류가 나면 `requirements.txt`에 `pysqlite3-binary`를 추가한다.

---

## 4. 협업 규칙

- **파일 소유권**: 자기 파일만 수정한다. 다른 파트 파일의 시그니처 변경은 이슈/PR로 합의한다.
- **`config.py`는 공유 파일**: 값 추가만 허용하고, 변경은 PR 리뷰를 거친다.
- **브랜치**: `feat/<파트>-<내용>` (예: `feat/db-loader`). 리뷰 후 `main`에 병합한다.
- **키 관리**: 실제 API 키는 커밋하지 않는다. `.env.example`만 공유한다.
