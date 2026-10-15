"""⑤ Retrieve: 벡터DB에서 질문과 관련 있는 Document를 찾고 문맥 문자열로 정리한다."""

# ============================================================
# Retrieve 검색기 만들기
# ============================================================

# 질문 확장: AI가 질문을 여러 버전으로 바꿔 각각 검색 후 합침 (느리고 비쌈)
try:
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever   # langchain 1.x
except ImportError:
    from langchain.retrievers.multi_query import MultiQueryRetriever           # langchain 0.x


def get_retriever(db, llm, mode="basic"):
    # 질문과 내용이 가장 비슷한 조각 4개
    if mode == "basic":
        return db.as_retriever(search_kwargs={"k": 4})

    # [장학·학칙] 카테고리 안에서만 찾음 → 엉뚱한 내용 차단
    elif mode == "policy":
        return db.as_retriever(search_kwargs={"k": 4,
                                              "filter": {"category": {"$in": ["장학", "학칙"]}}})

    # MMR: 후보 10개를 먼저 본 뒤, 서로 겹치지 않는 3개 선택
    # lambda_mult: 1에 가까울수록 "관련성" 우선, 0에 가까울수록 "다양성" 우선
    elif mode == "mmr":
        return db.as_retriever(search_type="mmr",
                               search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.5})

    # [장학·학칙] 카테고리 안에서 찾으면서 다양성도 확보 / 후보군
    elif mode == "policy_mmr":
        return db.as_retriever(search_type="mmr",
                               search_kwargs={"k": 3, "fetch_k": 10,
                                              "filter": {"category": {"$in": ["장학", "학칙"]}}})

    # 기본  + mmr  확장 검색 기능
    elif mode == "multi_query":
        base = db.as_retriever(search_kwargs={"k": 4})
        return MultiQueryRetriever.from_llm(retriever=base, llm=llm)

    else:
        raise ValueError(f"알 수 없는 모드: {mode}")


# ============================================================
# 찾아온 조각들을 AI에게 넘기기 좋게 정리하는 함수
#    결과 예시:
#      [서울대학교 학칙 12gage]
#      장학은 학과별 성적 평균 ...
# ============================================================


# 청크 앞에 `[서울대학교 학칙 p.N]` 붙이기
def format_docs(docs):
    blocks = []
    for d in docs:
        page = d.metadata.get("page", 0) + 1  # PDF 로더는 0부터 세므로 +1
        blocks.append(f"[서울대학교 학칙 p.{page}]\n{d.page_content}")
    return "\n\n".join(blocks)

# 쪽 번호에 +1, 중복 제거, 정렬 → `서울대학교 학칙 p.16, p.17`
def format_sources(docs):
    pages = sorted({d.metadata.get("page", 0) + 1 for d in docs})   # +1, 중복 제거, 정렬
    return "서울대학교 학칙 " + ", ".join(f"p.{p}" for p in pages)





