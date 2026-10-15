"""⑤ Retrieve: 벡터DB에서 질문과 관련 있는 Document를 찾고 문맥 문자열로 정리한다."""

from src.db.categories import CATEGORY_NAMES

# ============================================================
# Retrieve 검색기 만들기
# ============================================================

# 질문 확장: AI가 질문을 여러 버전으로 바꿔 각각 검색 후 합침 (느리고 비쌈)
try:
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever   # langchain 1.x
except ImportError:
    from langchain.retrievers.multi_query import MultiQueryRetriever           # langchain 0.x


# src.db.categories에서 불러온 카테고리를 변수처리한 함수
def make_filter(category=None):
    """category: 키 하나("general") 또는 여러 개(["general", "special"])"""
     # category = "general" → 값이 있으니 통과
    if not category:
        return None
    
    # "general"은 글자(str)니까 → keys = ["general"]
    # 이미 리스트니까 그대로 → keys = ["general", "special"]
    keys = [category] if isinstance(category, str) else category

    # "general" 있음, "special" 있음 → 둘 다 통과
    for k in keys:
        if k not in CATEGORY_NAMES:
            raise ValueError(f"없는 카테고리: {k} (가능한 값: {list(CATEGORY_NAMES)})")
        
     # keys 길이 1 → 여기서 끝
    if len(keys) == 1: # 길이 2라서 건너뜀
        return {"category": keys[0]}
    return {"category": {"$in": keys}}



# get_retriever로 함수처림 분기처리
def get_retriever(db, llm, mode="basic", category="tuition_discipline"):
    search_filter =  make_filter(category)
    # 질문과 내용이 가장 비슷한 조각 4개
    if mode == "basic":
        return db.as_retriever(search_kwargs={"k": 4})

    # [장학·학칙] 카테고리 안에서만 찾음 → 엉뚱한 내용 차단
    elif mode == "policy":
        return db.as_retriever(search_kwargs={"k": 4,
                                              "filter": search_filter })

    # MMR: 후보 10개를 먼저 본 뒤, 서로 겹치지 않는 3개 선택
    # lambda_mult: 1에 가까울수록 "관련성" 우선, 0에 가까울수록 "다양성" 우선
    elif mode == "mmr":
        return db.as_retriever(search_type="mmr",
                               search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.5})

    # [장학·학칙] 카테고리 안에서 찾으면서 다양성도 확보 / 후보군
    elif mode == "policy_mmr":
        return db.as_retriever(search_type="mmr",
                               search_kwargs={"k": 3, "fetch_k": 10,
                                              "filter": search_filter})

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

# [검색된 참고자료 목록]**으로 일치시키면 됩니다.
# 청크 앞에 `[서울대학교 학칙 p.N]` 붙이기
def format_docs(docs):
    blocks = []

    for d in docs:
        page = d.metadata.get("page", 0) + 1 # PDF 로더는 0부터 세므로 +1
        blocks.append(f"[서울대학교 학칙 p.{page}]\n{d.page_content}")

    # 추가: 검색에 사용한 같은 문서 목록으로 출처를 정리한다.
    if docs:
        sources = format_sources(docs)
        blocks.append(f"[검색된 참고자료 목록]\n{sources}")

    return "\n\n".join(blocks)


# 쪽 번호에 +1, 중복 제거, 정렬 → `서울대학교 학칙 p.16, p.17`
# format_docs()가 [검색된 참고자료 목록]을 만들 때 호출한다.
def format_sources(docs):
    pages = sorted({d.metadata.get("page", 0) + 1 for d in docs})   # +1, 중복 제거, 정렬
    return "서울대학교 학칙 " + ", ".join(f"p.{p}" for p in pages)



