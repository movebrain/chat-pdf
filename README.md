# 🎓 서울대학교 학칙 안내 챗봇 (ChatPDF)

서울대학교 학칙 PDF를 근거로 학사 질문에 답하는 챗봇입니다.
질문과 관련된 학칙 조각을 찾아 답변하고, 답 끝에 근거 쪽수를 `(출처: 서울대학교 학칙 p.16)` 형태로 표시합니다.
학칙에 없는 내용은 "제공된 참고자료에서는 확인되지 않습니다"라고 답합니다.

**LangChain**(RAG) + **Chroma**(벡터DB) + **OpenAI** + **Gradio**로 구현했습니다.

## 주요 기능

- **학칙 기반 답변**: 참고자료(검색된 학칙 조각)만 근거로 답하고, 근거 쪽수를 표시합니다.
- **채팅 형태 대화**: 이전 대화를 기억해 "그럼 신청은 언제까지 해?" 같은 후속 질문을 이어서 이해합니다.
- **실시간 답변 출력**: 답변이 생성되는 대로 화면에 채워집니다.
- **검색 방식 5가지 선택**: 유사도, 주제 필터, MMR, 주제 필터+MMR, 질문 확장.
- **질문 주제 자동 분류**: 주제 필터를 고르면 AI가 질문을 학칙 주제(7개)로 분류하고, 그 주제의 조각만 검색합니다. 분류 결과는 질문 바로 아래에 표시됩니다.

## 빠른 시작

Python 3.10 이상과 OpenAI API 키가 필요합니다.

**1. 가상환경과 패키지 설치** (처음 한 번. `chromadb`, `gradio` 등이 커서 몇 분 걸립니다)

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. API 키 설정**: `.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY`를 채웁니다. `.env`는 커밋하지 않습니다.

**3. 실행**

```bash
python app.py        # 브라우저에서 http://127.0.0.1:7860
```

페이지가 열리면 `data/서울대학교 학칙.pdf`를 자동으로 불러옵니다. 처음 한 번은 임베딩 때문에 몇 초 걸리고, 이후 접속부터는 만들어 둔 DB를 재사용합니다.

**터미널에서 테스트하기** (웹 화면 없이)

```bash
python -m tests.manual_chat
```

| 입력 | 동작 |
| --- | --- |
| 질문 | 답변을 실시간 출력. 이전 대화가 함께 전달됨 |
| `/debug` | 실제로 검색된 조각(page, category, 본문)과 LLM에 들어간 참고자료를 함께 출력 |
| `/reset` | 대화 기록 초기화 |
| `exit`, `q`, `종료` | 종료 |

## 동작 방식

```
[앱 시작 / 페이지 접속]
  data/서울대학교 학칙.pdf ──▶ ① Load ② Split ③ Embed ④ Store ──▶ Chroma DB (프로세스당 1번, 모두 공유)
                                    load_and_split()   build_db()

[질문할 때마다]
  질문 ──▶ ⑤ 주제 분류 (주제 필터 모드일 때만) ──▶ ⑥ 검색 ──▶ ⑦ 프롬프트 + LLM ──▶ 답변 (실시간)
            choose_category()                      get_retriever()  make_chatbot()      answer()
```

| 단계 | 하는 일 | 위치 | 함수 |
| --- | --- | --- | --- |
| ① Load | PDF를 쪽 단위로 읽기 | `src/db/loader.py` | `load_and_split()` |
| ② Split | `CHUNK_SIZE` 크기로 자르고, 쪽 번호로 `category` 메타데이터 부여 | `src/db/loader.py` | `load_and_split()` |
| ③ Embed | OpenAI 임베딩 생성 | `src/db/store.py` | `build_db()` |
| ④ Store | 인메모리 Chroma에 저장 | `src/db/store.py` | `build_db()` |
| ⑤ 주제 분류 | 질문을 LLM에 보내 주제 키 하나를 받음 (실패하면 `None`) | `src/rag/chain.py` | `choose_category()` |
| ⑥ Retrieve | 검색 방식에 맞는 검색기 생성, 필요하면 주제로 필터링 | `src/rag/retriever.py` | `get_retriever()` |
| ⑦ Generate | 검색된 조각 + 대화 기록 + 질문으로 프롬프트를 만들어 답변 생성 | `src/rag/chain.py`, `prompt.py`, `generator.py` | `make_chatbot()`, `get_prompt()`, `answer()` |

LLM에 전달되는 학칙 내용은 검색된 조각 3~4개뿐입니다. 주제 분류 단계에는 질문과 주제 목록만 보내고 학칙 본문은 보내지 않습니다.

## 검색 방식

화면 왼쪽 **검색 설정**에서 고릅니다. 기본값은 (d)입니다.

| 화면 이름 | `mode` 값 | 동작 |
| --- | --- | --- |
| (a) 유사도 | `basic` | 질문과 가장 비슷한 조각 4개 |
| (b) 주제 필터 | `policy` | AI가 분류한 주제 안에서 가장 비슷한 4개 |
| (c) MMR | `mmr` | 후보 10개 중 서로 겹치지 않는 3개 |
| (d) 주제 필터+MMR | `policy_mmr` | 분류한 주제 안에서 겹치지 않는 3개 |
| (e) 질문 확장 | `multi_query` | AI가 질문을 여러 표현으로 바꿔 검색 후 합침 (느리고 비용 증가) |

(b)(d)에서 주제를 분류하지 못하면(예: "맛집 추천해줘") 필터 없는 (a)(c)로 바꿔 학칙 전체에서 검색합니다.

### 주제(category) 7가지

`src/db/categories.py`에서 **쪽 번호 → 주제**로 정해 둔 값입니다. `loader.py`가 조각마다 이 값을 붙입니다.

| 키 | 주제 | 쪽 |
| --- | --- | --- |
| `general` | 총칙·교육조직·교원 | 1-2 |
| `organization` | 총장·처·위원회·부속시설 | 3-11 |
| `calendar_admission` | 학기·수업연한·입학·편입학·전과 | 12-15 |
| `status_curriculum` | 휴학·복학·제적·수강·학점·전공이수·졸업학점 | 16-19 |
| `exam_graduation` | 성적·수료·졸업·학위 | 20-21 |
| `special` | 계절수업·공개강좌·위탁생·학생회 | 22 |
| `tuition_discipline` | 학생의무·장학·징계·학사경고·유급·등록금·학칙개정 | 23-25 |

## 설정

`.env`(또는 환경변수)로 바꿉니다. 비워 두면 `src/config.py`의 기본값을 씁니다.

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | (필수) | 임베딩과 답변 생성에 사용. 화면에 입력하지 않고 환경변수에서 읽습니다 |
| `CHUNK_SIZE` | `1200` | 조각 하나의 글자 수 |
| `CHUNK_OVERLAP` | `120` | 조각끼리 겹치는 글자 수 |
| `SEARCH_MODE` | `basic` | ⚠️ 현재 적용되지 않습니다. 아래 [알려진 이슈](#알려진-이슈) 참고 |

코드에서 바꾸는 값:

| 값 | 위치 |
| --- | --- |
| PDF 경로 (`PDF_PATH`), 임베딩·생성 모델명 | `src/config.py` |
| 화면 기본 검색 방식 (`SEARCH_MODE = "policy_mmr"`) | `src/rag/generator.py` |
| 제목, 설명, 질문 예시, 검색 방식 이름 | `src/web/layout.py` 맨 위 상수 |
| 답변 규칙(역할, 근거, 출처 형식) | `src/rag/prompt.py` |
| 주제 분류 지침 | `config.ROUTER_PROMPT`를 추가하면 `choose_category()`가 사용 (없으면 기본 문구) |

**다른 PDF로 바꾸려면** `PDF_PATH`만으로는 부족합니다. `categories.py`의 쪽 번호→주제 표와, `retriever.py`의 `format_docs()`에 고정된 문서명 "서울대학교 학칙"도 함께 바꿔야 합니다.

## 폴더 구조

```
chat-pdf/
├── app.py                  # 진입점: .env를 읽고 웹 UI 실행 (python app.py)
├── requirements.txt        # 패키지 목록 (langchain<1.0 고정)
├── .env.example            # 환경변수 예시 (복사해서 .env로 사용, .env는 커밋 금지)
├── data/
│   └── 서울대학교 학칙.pdf  # 챗봇이 불러오는 기준 문서
├── src/
│   ├── config.py           # 공용 설정: PDF 경로, 청크 크기, 모델명 (.env 읽기 포함)
│   ├── db/                 # PDF → 벡터DB
│   │   ├── loader.py       #   load_and_split(): 읽기·분할·category 부여
│   │   ├── categories.py   #   쪽 번호 → 주제 표, 주제 이름, 쪽별 조 범위
│   │   └── store.py        #   build_db(): 임베딩 → 인메모리 Chroma
│   ├── rag/                # 벡터DB → 답변
│   │   ├── retriever.py    #   get_retriever(): 검색 방식 5가지 / format_docs(): 참고자료 문자열
│   │   ├── prompt.py       #   get_prompt(): 역할·근거·출처·대화기록 규칙
│   │   ├── chain.py        #   choose_category(): 주제 분류 / make_chatbot(): LCEL RAG 체인
│   │   └── generator.py    #   answer(): 분류 → 검색 → 체인 실행 → 스트리밍
│   ├── web/                # Gradio 웹 UI
│   │   ├── layout.py       #   화면 배치와 화면 문구
│   │   ├── handlers.py     #   이벤트 함수: DB 불러오기, 질문 답변, 분류 결과 표시, 대화 지우기
│   │   └── app.py          #   build_demo(): 화면과 이벤트 연결
│   └── ui.py               # (미사용) 예전 업로드 방식 화면. 현재 어디서도 import하지 않음
├── tests/
│   ├── test_store.py       # build_db() 단위 테스트 (API 키 불필요)
│   └── manual_chat.py      # 터미널 대화 테스트 (실제 PDF·API 사용)
├── eval/
│   └── questions.jsonl     # 평가용 질문 20개 (정답 조문·쪽·핵심 사실 포함)
├── docs/
│   ├── structure.md        # 파일 책임과 함수 계약 (일부는 이전 계약 기준)
│   ├── store/plan.md       # build_db 계약 변경 계획
│   └── sources.md          # 참고 자료
└── Claude outputs/         # 기획서 점검 문서
```

## 모듈 간 인터페이스

| 함수 | 입력 | 반환 |
| --- | --- | --- |
| `load_and_split` | `pdf_path` | `list[Document]` (metadata: `source`, `page`(0부터), `category`) |
| `build_db` | `pdf_path` | `Chroma` (키는 환경변수에서 읽음, 실패 시 예외) |
| `choose_category` | `question`, `llm` | 주제 키 `str` 또는 `None` |
| `get_retriever` | `db`, `llm`, `mode="basic"`, `category=...` | 검색기 (`mode`가 틀리면 `ValueError`) |
| `format_docs` | `docs` | `str` (`[서울대학교 학칙 p.N]` + 본문, 끝에 `[검색된 참고자료 목록]`) |
| `get_prompt` | — | `ChatPromptTemplate` (`context`, `history`, `question`) |
| `make_chatbot` | `retriever`, `llm` | 입력 `{"question", "history"}` → 답변 문자열을 내는 Runnable |
| `answer` | `question`, `db`, `history=None`, `mode=None`, `on_search=None` | `Iterator[str]` (누적 답변) |

- `history` 형식: `[{"role": "user" | "assistant", "content": str}, ...]`. 현재 질문은 넣지 않습니다.
- `on_search(category, mode)`: 검색 범위가 정해지면 첫 답변 조각보다 먼저 한 번 호출됩니다. 화면의 "🔎 분류된 카테고리" 표시가 이 값을 씁니다.
- `get_retriever`의 `category` 기본값은 `"tuition_discipline"`입니다. 필터 없이 쓰려면 `category=None`을 명시하세요.
- 함수 시그니처를 바꿀 때는 영향받는 담당자와 먼저 합의합니다.

## 팀 구성

| 파트 | 파일 | 맡은 단계 |
| --- | --- | --- |
| **Gradio** | `app.py`, `src/web/` | 화면, 이벤트 연결 |
| **DB 저장** | `src/db/` | ① ~ ④, 주제 분류표 |
| **RAG 검색** | `src/rag/retriever.py` | ⑥ 검색 방식, 참고자료 포매팅 |
| **RAG 체인** | `src/rag/prompt.py`, `src/rag/chain.py` | 프롬프트, 주제 분류, LCEL 연결 |
| **RAG 실행** | `src/rag/generator.py` | 모델 생성, 단계 조립, 스트리밍 |

## 테스트

```bash
python -m unittest discover -s tests -t .   # 단위 테스트 (API 키 불필요)
python -m tests.manual_chat                 # 실제 PDF·API로 대화 테스트
```