"""⑤ Retrieve: 벡터DB에서 질문과 관련 있는 Document를 찾고 문맥 문자열로 정리한다."""

import os

from store import db, llm   # db: Chroma 벡터 저장소, llm: multi_query에서 쓸 언어 모델

# ============================================================
# Retrieve 검색기 만들기
# ============================================================
# 질문과 내용이 가장 비슷한 조각 4개
basic_retriever = db.as_retriever(search_kwargs={"k": 4})

# [장학] 카테고리 안에서만 찾음 → 엉뚱한 내용 차단해줌
policy_retriever = db.as_retriever(search_kwargs={ "k": 4,"filter": {"category": {"$in": ["장학", "학칙"]}}})

# MMR: 후보 fetch_k개를 먼저 10개 본 뒤, 서로 겹치지 않지 안흔 k개 3개 선택
# lambda_mult: 1에 가까울수록 "관련성" 우선, 0에 가까울수록 "다양성" 우선
mmr_retriever = db.as_retriever(search_type="mmr",
                                search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.5})

# [장학] 카테고리 안에서만 찾으면서 분류도 좁히고 다양성도 확보
policy_mmr_retriever = db.as_retriever(search_type="mmr",
                                       search_kwargs={"k": 3, "fetch_k": 10,
                                                      "filter": {"category": {"$in": ["장학", "학칙"]}}})

# 질문 확장: AI가 질문을 여러 버전으로 바꿔 각각 검색 후 합침 (느리고 비쌈)
try:
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever   # langchain 1.x
except ImportError:
    from langchain.retrievers.multi_query import MultiQueryRetriever           # langchain 0.x
multi_query_retriever = MultiQueryRetriever.from_llm(retriever=basic_retriever, llm=llm)

# ============================================================
# 찾아온 조각들을 AI에게 넘기기 좋게 정리하는 함수
#    결과 예시:
#      [출처: refund_policy.pdf]
#      환불은 구매 후 7일 이내에 ...
#
#      [출처: faq.txt]
#      환불 처리에는 영업일 기준 ...
# ============================================================
def format_docs(docs):
    blocks = []
    for d in docs:
        filename = os.path.basename(d.metadata.get("source", "문서"))
        blocks.append(f"[출처: {filename}]\n{d.page_content}")
    return "\n\n".join(blocks)
