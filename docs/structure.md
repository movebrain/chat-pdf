# ChatPDF 프로젝트 구조와 함수 계약

PDF를 올리면 내용을 벡터DB에 저장하고, 질문과 관련 있는 문서를 찾아 근거 기반 답변을 생성한다.
기술 구성은 LangChain(RAG) + Gradio다.

전체 흐름: `Load → Split → Embed → Store → Retrieve → Prompt → Chain → Generate`

## 1. 폴더 구조

```text
chat-pdf/
├── app.py                   # Gradio 진입점. UI, 저장, 답변 함수를 이벤트에 연결
├── requirements.txt         # 실행 및 배포 패키지
├── README.md
├── src/
│   ├── config.py            # 청크 크기, 임베딩 모델명, 생성 모델명
│   ├── ui.py                # Gradio 화면 컴포넌트만 배치
│   ├── db/
│   │   ├── loader.py        # ① PDF Load + ② Split
│   │   └── store.py         # ③ Embed + ④ Chroma Store
│   └── rag/
│       ├── retriever.py     # ⑤ 검색기 생성 전략 + Document 출처/문맥 포매팅
│       ├── prompt.py        # 상담원 역할, 근거 제한, 답변/출처 규칙
│       ├── chain.py         # 검색기 + 포매터 + 프롬프트 + LLM을 LCEL로 연결
│       └── generator.py     # 키/DB/질문 검증, 모델 생성, 체인 실행 및 Gradio 스트리밍
├── docs/
│   ├── structure.md         # 파일 책임, 인터페이스, 작업 순서
│   └── sources.md           # 참고 자료
└── eval/                    # 평가 데이터 및 평가 코드
```

### RAG 파일별 책임

| 파일 | 책임 | 함수 |
| --- | --- | --- |
| `retriever.py` | 벡터DB에서 어떤 방식으로 찾을지 결정하고 결과 문서를 문맥 문자열로 정리 | `get_retriever()`, `format_docs()` |
| `prompt.py` | 시스템 역할, 참고자료 범위, 확인 불가 응답, 출처 표기 규칙 관리 | `get_prompt()` |
| `chain.py` | 질문을 검색과 프롬프트에 전달하고 모델 결과를 문자열로 변환 | `make_chatbot()` |
| `generator.py` | UI 입력으로 모델/검색기/체인을 준비하고 응답을 스트리밍 | `answer()` |

RAG는 세 명으로 나누는 것을 기본으로 한다.

| 담당 | 소유 파일 | 주요 결과 |
| --- | --- | --- |
| 검색 담당 | `retriever.py` | 검색기 옵션과 출처가 포함된 문맥 문자열 |
| 챗봇 체인 담당(추가 인원) | `prompt.py`, `chain.py` | 질문을 답변 문자열로 변환하는 LCEL 체인 |
| 생성/통합 담당 | `generator.py` | 모델 준비, 체인 실행, Gradio용 스트리밍 |

`prompt.py`와 `chain.py`는 같은 입력·출력 계약을 함께 조정하므로 한 명이 담당한다.
`generator.py` 담당자는 체인의 `Runnable[str, str]` 계약을 사용해 UI와 통합한다.

## 2. 함수 계약과 인자 사용법

### `src/rag/retriever.py`

```python
def get_retriever(
    db: Chroma,
    llm: BaseLanguageModel | None = None,
    *,
    strategy: Literal["similarity", "mmr", "multi_query"] = "similarity",
    k: int = 4,
    fetch_k: int = 10,
    lambda_mult: float = 0.5,
    metadata_filter: dict[str, Any] | None = None,
) -> BaseRetriever: ...

def format_docs(docs: Iterable[Document]) -> str: ...
```

- `db`: `store.build_db()`가 만든 Chroma 객체. 실제 문서 검색은 이 벡터DB를 대상으로 한다.
- `llm`: 질문 확장 검색(`multi_query`)에서만 사용한다. 기본 검색과 MMR에서는 생략할 수 있다.
- `strategy`: `similarity`는 유사도 상위 문서, `mmr`은 관련성과 문서 다양성을 함께 고려,
  `multi_query`는 LLM으로 질문을 확장해 여러 번 검색한 결과를 합친다.
- `k`: 최종 반환할 문서 수. 예를 들어 가장 유사한 청크 4개 또는 MMR이 선택할 3개.
- `fetch_k`: MMR에서 최종 선택 전에 살펴볼 후보 수. `k` 이상이어야 한다.
- `lambda_mult`: MMR 관련성/다양성 비율. 0에 가까우면 다양성, 1에 가까우면 유사도를 더 중시한다.
- `metadata_filter`: Chroma metadata 조건. 예: `{"category": "refund"}`는 refund 분류만 검색한다.
- `format_docs()`는 문서의 `page_content`와 `metadata["source"]` 파일명을 표시해 프롬프트에 넣을
  하나의 문자열로 만든다. 입력 문서를 변경하거나 검색을 다시 수행하지 않는다.

사용 예:

```python
basic = get_retriever(db, strategy="similarity", k=4)
refund = get_retriever(db, strategy="similarity", k=4,
                       metadata_filter={"category": "refund"})
diverse = get_retriever(db, strategy="mmr", k=3, fetch_k=10, lambda_mult=0.5)
refund_diverse = get_retriever(
    db, strategy="mmr", k=3, fetch_k=10,
    metadata_filter={"category": "refund"},
)
expanded = get_retriever(db, llm, strategy="multi_query", k=4)
```

### `src/rag/prompt.py`

```python
def get_prompt() -> ChatPromptTemplate: ...
```

인자를 받지 않는다. 상담원 역할, 참고자료만을 근거로 삼는 규칙, 자료에서 확인되지 않는
정보에 대한 응답, 출처 표기 문구를 이 파일 안에서 관리한다. 프롬프트 변수는 `context`와
`question` 두 개다. 검색 결과는 `context`, 사용자가 입력한 원래 질문은 `question`에 들어간다.
모델/API 키를 만들거나 검색을 수행하지 않는다.

### `src/rag/chain.py`

```python
def make_chatbot(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
) -> Runnable[str, str]: ...
```

- `retriever`: `get_retriever()` 결과. 입력 질문으로 Document 목록을 찾는다.
- `llm`: 생성 모델 인스턴스. API 키로 모델을 만드는 책임은 `generator.py`에 있다.
- 반환된 체인은 문자열 질문을 입력받아 문자열 답변을 반환한다.
- 체인은 질문을 검색기와 프롬프트에 전달하고, 검색 Document는 `format_docs()`로 정리한다.
  프롬프트 적용 후 LLM 결과를 `StrOutputParser`로 문자열화한다.
- 동기 실행은 `chain.invoke("원두 환불 규정 알려줘")`, 조각 단위 출력은
  `chain.stream(question)`을 사용한다.

### `src/rag/generator.py`

```python
def answer(
    question: str,
    openai_key: str,
    db: Chroma | None,
) -> Iterator[str]: ...
```

- `question`: Gradio 질문 입력란에서 온 문자열. 빈 문자열 또는 공백만 있는 입력은 거부한다.
- `openai_key`: Gradio 비밀번호 입력란에서 온 키. 모델 생성에만 쓰고 로그나 응답에 포함하지 않는다.
- `db`: 업로드 단계에서 받은 Chroma 객체. `None`이면 먼저 PDF를 올리도록 UI 오류를 낸다.
- 함수는 `config.GENERATE_MODEL`로 언어 모델을 만들고, `get_retriever()` 및
  `make_chatbot()`으로 구성한 체인을 실행한다.
- 반환은 최종 문자열 하나가 아니라 누적 답변 문자열들의 iterator다. Gradio는 yield마다
  화면을 갱신한다. 유효하지 않은 사용자 입력은 `gr.Error`로 표시하고 API 예외는 숨기지 않는다.

## 3. 다른 모듈의 인터페이스

```python
# src/db/loader.py
def load_and_split(pdf_path: str) -> list[Document]: ...

# src/db/store.py
def build_db(
    pdf_path: str | None,
    openai_key: str,
) -> tuple[Chroma | None, str]: ...

# src/ui.py
def render() -> SimpleNamespace: ...
```

- `load_and_split()`은 PDF 경로를 읽고 `config.CHUNK_SIZE` / `config.CHUNK_OVERLAP`으로 분할한다.
- `build_db()`는 업로드된 경로와 키를 받아 벡터DB와 상태 문자열을 반환한다. 반환 순서는
  Gradio 이벤트의 `outputs=[db_state, status]` 순서와 일치해야 한다.
- `render()`는 UI 요소를 만들고 `openai_key`, `pdf_file`, `status`, `db_state`, `question`,
  `ask_btn`, `output` 속성을 가진 객체를 반환한다. 이벤트 연결은 `app.py` 책임이다.
- `config.py`에는 `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_MODEL`, `GENERATE_MODEL`처럼
  여러 파일에서 공유하는 값만 둔다. 프롬프트 문구는 `prompt.py`가 소유한다.

## 4. 작업 순서 및 통합

1. **계약 확인:** 아래 시그니처와 반환 형태를 먼저 합의한다. 다른 파트의 계약은 소유자 동의
   없이 바꾸지 않는다.
2. **병렬 구현:** UI, PDF loader, retriever, prompt는 정해진 인터페이스를 지키며 독립 작업한다.
   retriever는 임시 Chroma와 `DeterministicFakeEmbedding`으로 API 키 없이 시험할 수 있다.
3. **의존 구현:** store는 loader 결과를 저장한다. chain은 retriever 포매터와 prompt를 연결한다.
4. **통합 구현:** generator가 모델·검색기·체인을 준비하고 `app.py`가 Gradio와 연결한다.
5. **검증:** 샘플 PDF 업로드 후 기본/필터/MMR 검색과 답변 스트리밍을 확인한다. 문서에 없는 질문은
   정해 둔 미확인 응답 규칙을 따르는지 확인한다.

Gradio 이벤트의 `inputs=[...]` 순서는 연결 함수 매개변수 순서와 반드시 같아야 한다.

## 5. 협업 규칙

- 파일 소유권은 담당자별로 나누고 자기 파일을 우선 수정한다.
- 공유 설정은 `config.py`에 추가할 수 있지만, 기존 상수의 변경은 영향받는 담당자와 합의한다.
- 브랜치는 `feat/<파트>-<내용>` 형식으로 만든다. 예: `feat/rag-chain`.
- 실제 API 키는 커밋하지 않는다. `.env.example`만 공유한다.
