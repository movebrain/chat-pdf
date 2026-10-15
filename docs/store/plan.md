# Plan: store.py 갱신 (`build_db` 계약 변경)

`src/db/store.py`를 업로드·키 입력 방식에서 시작 시 고정 PDF 1회 임베딩 방식으로 바꾼다.
근거는 [intent.md](../intent.md)(최우선)와 [spec.md](../spec.md) D5·D6이다. 같은 계약을 쓰는 [cli-ui/plan.md](../cli-ui/plan.md) 작업 4를 이 문서가 구현한다. 구현이 이 문서와 달라지면 같은 변경에서 문서를 갱신한다.

## 1. 목표와 범위

| 구분 | 내용 |
| --- | --- |
| 목표 | `build_db(pdf_path: str) -> Chroma`. PDF 하나를 읽어 인메모리 Chroma를 만든다. 키 인자·상태 문자열·`None` 반환을 없앤다 |
| 포함 | `src/db/store.py`, `tests/test_store.py`, 이 문서·cli-ui plan 상태 갱신 |
| 제외 | `loader.py`(조 단위 분할·페이지 추적·`validate_documents`), `config.py` 값(`CHUNK_SIZE` 등), `generator.answer` 시그니처, 기준 PDF 교체 |

## 2. 결정 사항

| 항목 | 결정 | 근거 |
| --- | --- | --- |
| 시그니처 | `build_db(pdf_path: str) -> Chroma` | spec D5, cli-ui plan 작업 4 |
| API 키 | 인자로 받지 않는다. `OpenAIEmbeddings`가 `OPENAI_API_KEY` 환경변수를 읽는다 | intent 제약, spec R5 |
| 시작 검사 | 키·PDF 누락은 `app.py`가 처리한다. store는 검사하지 않는다 | spec D6 |
| 검수 실패 | `ValueError`(조·페이지·이유 포함). loader의 `ValueError`는 그대로 올린다. 빈 결과는 임베딩 전에 `ValueError` | spec D5·D6 |
| 임베딩 실패 | 감싸지 않고 그대로 올린다. 키가 섞일 수 있는 원문 메시지는 `app.py`가 종류만 출력한다 | spec D6 |
| 컬렉션 | 인메모리, 호출마다 `pdf-{uuid}`. 한 프로세스에서 여러 번 호출(평가 도구·테스트)해도 섞이지 않게 한다 | spec D5, §7.4 |
| 제거 | `default_pdf_paths`, `load_default_db`, `_server_db`, `DATA_DIR`·다중 PDF·키 입력·버튼 로드 | intent 범위 밖, spec D4·D5 |

## 3. 작업과 상태

| # | 작업 | 담당 | 상태 |
| --- | --- | --- | --- |
| 1 | `build_db`를 새 계약으로 구현 | DB | 완료 |
| 2 | 단위 테스트 `tests/test_store.py` (API·Chroma 없이) | DB | 완료 |
| 3 | `validate_documents` 호출을 `build_db`에 추가 (임베딩 전) | DB | 대기: loader에 함수가 생긴 뒤 |
| 4 | loader를 조 단위 분할로 변경 (`article`, `title`, `page_end` 메타데이터) | DB | 대기 (spec D1, 이 계획 범위 밖) |
| 5 | 실제 PDF·키로 `python app.py` 확인 | 통합 | 대기: 작업 4와 `generator.answer` 변경 후 |

## 4. 검증

- 단위 테스트는 `python -m unittest discover -s tests -t .`로 실행한다(프로젝트 루트에서). `OpenAIEmbeddings`와 `Chroma`를 대체하므로 API 키가 필요 없고, sqlite3 버전이 낮은 환경에서도 돈다.
  - 반환값이 `Chroma.from_documents`의 결과이고, loader가 반환한 청크 전체가 `config.EMBEDDING_MODEL` 임베딩과 함께 전달된다.
  - 두 번 호출하면 `collection_name`이 서로 다르다.
  - loader가 `ValueError`를 내면 그대로 전달되고 임베딩·저장은 호출되지 않는다.
  - loader가 빈 리스트를 반환하면 `ValueError`이고 임베딩·저장은 호출되지 않는다.
  - 임베딩 생성 시 키를 인자로 넘기지 않는다.
- 실제 Chroma의 컬렉션 분리와 임베딩 호출은 sqlite3 ≥ 3.35 환경에서 작업 5로 확인한다.

## 5. 미결·위험

1. **`validate_documents` 위치**: spec은 호출 위치를 정하지 않았다. `build_db`에서 임베딩 전에 호출하는 안을 추천하며(검수 실패 시 비용 없음), loader가 내부에서 호출하기로 하면 작업 3은 필요 없다. DB 파트 합의 필요.
2. **loader 선행**: `main`의 loader는 아직 `NotImplementedError` 스텁이다. PR #1(`feature/chunk`)이 쪽 단위 청크를 반환하는 구현을 넣지만 `article`·`title`·`page_end` 메타데이터가 없어, 조 단위 분할(spec D1)이 끝나기 전에는 R2·R3 출처 표시가 동작하지 않는다 (spec §9).
3. **규격 변경 합의와 병합 순서**: 이 변경은 `main` 기준이다. `main`의 Gradio 시절 `app.py`·`ui.py`는 구 시그니처를 호출하므로, 호출하는 쪽을 새 시그니처로 바꾸는 PR #10(`feature/cli-ui`)과 함께 병합해야 한다. PR #1도 같은 `store.py`를 수정하므로 먼저 병합되는 쪽에 맞춰 나중 PR에서 충돌을 정리한다. `generator.answer`도 아직 구 시그니처라 작업 5 전까지 `python app.py`가 끝까지 동작하지 않는다. 합의 기록은 PR 설명에 남긴다.
4. **문서 링크**: 이 문서가 참조하는 `intent.md`·`spec.md`는 아직 `main`에 없고, `cli-ui/plan.md`는 `feature/cli-ui`에만 있다. 해당 문서가 병합되기 전에는 링크가 열리지 않는다.
5. **실행 환경**: `.venv/bin/python`이 실행 권한 오류로 열리지 않고, 시스템 python(3.9)은 sqlite3가 낮아 Chroma를 import할 수 없다. 실제 Chroma 확인은 환경 정리 후에 한다.
