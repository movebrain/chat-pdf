# 📄 ChatPDF

PDF를 업로드하면 내용을 기반으로 질문에 답해주는 챗봇입니다.
**LangChain**(RAG)과 **Gradio**로 구현합니다.

## 동작 방식

| 단계 | 하는 일 | 위치 | 함수 |
| --- | --- | --- | --- |
| ① Load | PDF 읽기 | `src/db/loader.py` | `load_and_split()` |
| ② Split | 청크로 분할 | `src/db/loader.py` | `load_and_split()` |
| ③ Embed | 임베딩 생성 | `src/db/store.py` | `build_db()` |
| ④ Store | Chroma에 저장 | `src/db/store.py` | `build_db()` |
| ⑤ Retrieve | 관련 청크 검색 | `src/rag/retriever.py` | `get_retriever()` |
| ⑥ Generate | 답변 생성 (스트리밍) | `src/rag/generator.py` | `answer()` |

```
PDF 업로드 ──▶ ①②③④ build_db() ──▶ gr.State(db)
                                        │
질문 입력  ──▶ ⑤⑥ answer(question, key, db) ──▶ 화면에 실시간 출력
```

## 빠른 시작

Python 3.10 이상, OpenAI API Key가 필요합니다.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py        # http://127.0.0.1:7860
```

- API 키는 **화면의 입력창**에 넣습니다. 키를 입력한 뒤에 PDF를 올려야 합니다.
- `.env`는 로컬 테스트용입니다 (`.env.example` 참고, 커밋 금지).
- `langchain<1.0`으로 고정되어 있습니다. 1.0부터 `langchain.retrievers.multi_query` 경로가 바뀝니다.

## 폴더 구조

```
chat-pdf/
├── app.py               # 진입점: 화면 + 처리 함수를 이벤트로 연결 (HF Spaces는 루트의 app.py 실행)
├── requirements.txt     # 배포용 패키지 목록
├── .env.example         # 로컬 테스트용 키 예시
├── src/
│   ├── config.py        # 청크 크기, 모델명 등 공용 설정값
│   ├── ui.py            # gr.Blocks 화면
│   ├── db/              # PDF → 벡터DB
│   │   ├── loader.py    #   load_and_split()
│   │   └── store.py     #   build_db()
│   └── rag/             # 벡터DB → 답변
│       ├── retriever.py #   get_retriever(), format_docs()
│       └── generator.py #   answer()
├── docs/
│   ├── structure.md     # 담당 도메인, 의존 순서, 협업 규칙
│   └── sources.md       # 참고 자료
└── eval/                # 평가용 (현재 비어 있음)
```

## 팀 구성 (2명씩 3파트)

| 파트 | 폴더 | 맡은 단계 | 넘겨주는 값 |
| --- | --- | --- | --- |
| **Gradio** | `src/ui.py`, `app.py` | 화면, 이벤트 연결 | — |
| **DB 저장** | `src/db/` | ① ~ ④ | `db` (Chroma) |
| **RAG** | `src/rag/` | ⑤ ~ ⑥ | 답변 텍스트 (yield) |

파트 사이의 접점은 **함수 시그니처** 하나뿐입니다. 자기 폴더의 본문만 채우고, 시그니처를 바꿀 때는 영향받는 파트와 먼저 합의합니다. 자세한 작업 순서는 [docs/structure.md](docs/structure.md)를 참고하세요.

## 모듈 간 인터페이스

| 함수 | 입력 | 반환 |
| --- | --- | --- |
| `load_and_split` | `pdf_path` | `list[Document]` |
| `build_db` | `pdf_path`, `openai_key` | `(Chroma \| None, str)` → `outputs=[db_state, status]` 순서 |
| `get_retriever` | `db`, `llm` | `BaseRetriever` |
| `format_docs` | `docs` | `str` |
| `answer` | `question`, `openai_key`, `db` | `Iterator[str]` (yield마다 화면 갱신) |
| `render` | — | `SimpleNamespace` (`openai_key`, `pdf_file`, `status`, `db_state`, `question`, `ask_btn`, `output`) |

> 구현 전 함수는 `NotImplementedError`를 던집니다.
> Gradio 이벤트의 `inputs=[...]` 순서는 함수 매개변수 순서와 반드시 같아야 합니다.

## 자주 나오는 오류

| 증상 | 해결 |
| --- | --- |
| `sqlite3 version ... unsupported` (배포 서버) | `requirements.txt`에 `pysqlite3-binary` 추가 |
| `No module named 'langchain.retrievers.multi_query'` | `langchain<1.0`으로 고정 |
| 업로드했는데 "API 키를 먼저 입력" | 키 입력 후 PDF를 다시 업로드 |
| 함수 인자가 뒤섞임 | `inputs` 순서를 함수 매개변수 순서와 맞추기 |
| 답변이 엉뚱함 | `config.CHUNK_SIZE`를 500~1000으로 조정 |
