# Plan: CLI UI 전환

`src/ui.py`를 Gradio 화면에서 CLI로 바꾸고, `app.py`가 시작 시 정해진 PDF를 한 번 임베딩한 뒤 CLI에 답변 함수를 연결한다.
근거는 [intent.md](../intent.md)(최우선)와 [spec.md](../spec.md) D4·D5·D6이다. 구현이 이 문서와 달라지면 같은 변경에서 문서를 갱신한다.

## 1. 목표와 범위

| 구분 | 내용 |
| --- | --- |
| 목표 | 터미널에서 질문하고 답변을 확인하는 최소 실행 경로. API 키는 서버 키, PDF 업로드 없음 |
| 포함 | `src/ui.py`(CLI 루프), `app.py`(시작 검증·임베딩·연결), `src/config.py` 값 추가 |
| 제외 | `build_db`·`answer`·`get_retriever` 본문 구현(DB·RAG 파트), 공개 URL 배포, 평가 도구(`eval/`) |
| 성격 | **임시 UI.** intent의 목표는 공개 URL 시연이므로 웹 UI는 후속으로 다시 필요하다 (§6 미결 1) |

## 2. 결정 사항

| 항목 | 결정 | 근거 |
| --- | --- | --- |
| API 키 | 환경변수 `OPENAI_API_KEY`. 로컬 `.env`는 `python-dotenv`가 설치돼 있을 때만 읽고, 배포는 플랫폼 secret | intent 제약, spec R5·D4 |
| 의존성 | `requirements.txt`는 바꾸지 않는다. Gradio는 후속 웹 UI를 위해 유지하고 `python-dotenv`는 추가하지 않는다 | 팀 결정 |
| PDF | `config.PDF_PATH` 고정. 시작 시 `build_db(PDF_PATH)` 1회 | spec D5 |
| 질문 제한 | `config.MAX_QUESTION_CHARS=300`. 초과·공백은 API 호출 전에 안내 | spec D6 |
| 출력 | `ask(question)`의 마지막 yield를 한 번 출력 | spec §3.3 (검증 후 완성 답변 표시) |
| 오류 표시 | 예외 종류만 stderr 출력, 원문 메시지 미노출 | spec R7·D6 |
| 기준 문서 표기 | 배너에 `RULE_LABEL`과 "PDF 뷰어 기준 1쪽부터" 안내 | spec R8, R4 |

## 3. 계약

```
app.py   main() ─ 환경 검사 ─ build_db(PDF_PATH) ─ ui.run(partial(answer, db=db))
ui.py    run(ask: Callable[[str], Iterator[str]]) -> None
```

- `ui.run`은 `config`만 알고 DB·RAG를 import하지 않는다. 답변 함수는 인자로 받는다.
- DB 파트: `build_db(pdf_path: str) -> Chroma`. 검수 실패는 `ValueError`(조·페이지·이유 포함 메시지).
- RAG 파트: `answer(question: str, db: Chroma) -> Iterator[str]`.

## 4. 작업과 상태

| # | 작업 | 담당 | 상태 |
| --- | --- | --- | --- |
| 1 | `ui.run` CLI 루프 (입력 검증, 종료, 오류·Ctrl-C 처리, 배너) | UI | 완료 |
| 2 | `app.py` 시작 검사(키·PDF)·임베딩 실패 처리·연결 | UI | 완료 |
| 3 | `config`에 `PDF_PATH`, `RULE_LABEL`, `MAX_QUESTION_CHARS` 추가 | UI | 완료 |
| 4 | `build_db`를 `(pdf_path) -> Chroma`로 변경 (키 인자·상태 문자열 제거) | DB | 구현 완료, 합의 필요 ([store/plan.md](../store/plan.md)) |
| 5 | `answer`를 `(question, db)`로 변경하고 구현 | RAG | **대기, 합의 필요** |
| 6 | `ui.run` 단위 테스트(`unittest`, `input`·`ask` 대체) | UI | 대기 |
| 7 | 제2710호 PDF 확보 후 `PDF_PATH`·`RULE_LABEL` 교체 | DB + 원문 검수 | 대기 (spec Q1) |
| 8 | README·`docs/structure.md`·spec D4를 CLI 기준으로 갱신 | UI | 대기, 방향 확정 후 |

작업 4·5가 끝나야 `python app.py`가 끝까지 동작한다.

## 5. 검증

- **T3 해당(API 없음)**: `ui.run`에 가짜 `ask`를 넣어 확인한다.
  - 공백·301자 질문은 `ask`를 호출하지 않는다.
  - `ask`의 예외 메시지(가짜 키 포함)가 출력에 없다.
  - 종료 명령, EOF, 답변 대기 중 Ctrl-C가 동작한다.
- **시작 검사**: 키 없음·PDF 없음이면 종료 코드 1과 안내가 나온다. 안내에 키 값이 없다.
- **통합(작업 4·5 이후)**: 실제 PDF로 `python app.py` 실행 후 질문 1건의 답변·출처 출력과 문서 밖 질문의 유보를 확인한다.

## 6. 미결·위험

1. **공개 URL 시연**: CLI는 intent의 "공개 URL" 목표를 충족하지 못한다. Gradio 화면을 폐기할지, 후속으로 복원할지 정해야 한다. 기존 Gradio `render()`는 git 이력에 있다.
2. **오류 표시 계약**: spec D6은 RAG가 `gr.Error`를 던지는 것을 전제한다. CLI는 Gradio에 의존하지 않으려고 예외 종류만 보여 주므로 사용자에게는 `(Error)`처럼 불친절하다. UI에 의존하지 않는 사용자용 예외를 RAG와 합의할지 정해야 한다.
3. **기준 문서**: 현재 PDF는 제2347호 샘플이다. 이 상태의 답변·평가를 제2710호 결과로 해석하지 않는다.
4. **R9(큐·동시성 제한)**: 로컬 단일 사용자 CLI에서는 해당 없다. 웹 UI 복원 때 다시 적용한다.
5. **`ValueError` 구분**: `app.py`는 `ValueError`를 문서 검수 실패로 취급한다. pydantic 검증 오류도 `ValueError`의 하위 클래스라 구분이 흐려질 수 있어, DB 파트가 전용 예외를 정하면 교체한다.

## 7. 구현 검토 결과 (2026-10-15)

- 검토 중 고친 것: 답변 대기 중 Ctrl-C가 트레이스백으로 앱을 종료시키던 문제(이제 질문만 취소), 한글 입력 시 줄 편집이 안 되는 문제(`readline`).
- 확인한 것: 위 §5의 `ui.run` 항목을 가짜 `ask`로 수동 확인했다.
- 확인하지 못한 것: `app.py` 전체 실행. `.venv`가 실행 권한 오류로 열리지 않았고 작업 4·5도 남아 있다.
- 남은 것: 자동 테스트(작업 6), 문서 갱신(작업 8).
