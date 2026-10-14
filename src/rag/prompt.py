"""RAG 답변에서 사용할 역할, 근거 제한, 출처 표기 규칙을 관리한다."""

from langchain_core.prompts import ChatPromptTemplate


def get_prompt() -> ChatPromptTemplate:
    """컨텍스트와 사용자 질문을 받아 모델 입력 메시지로 만드는 프롬프트를 반환한다.

    프롬프트에는 고객센터 상담원의 역할, 참고자료만 근거로 답하라는 제한,
    자료에서 확인되지 않는 내용의 응답 규칙, 출처 표기 규칙을 정의한다.
    ``{context}``와 ``{question}``은 chain.make_chatbot()이 각각 검색 문서와
    원래 질문으로 채운다.

    Args:
        없음. 프롬프트 문구는 이 모듈에서 관리한다.

    Returns:
        입력 변수 ``context``, ``question``을 갖는 ChatPromptTemplate.

    Example:
        ``get_prompt().invoke({"context": "...", "question": "환불 규정은?"})``
        은 system 및 human 메시지로 구성된 모델 입력을 반환한다.
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 위니브 카페 고객센터 상담원입니다. "
                "아래 [참고자료]만 보고 정중히 답하세요. "
                "참고자료에 없는 내용은 지어내지 말고 "
                "'문서에서 확인되지 않습니다'라고 답하세요. "
                "답 끝에 사용한 출처를 (출처: 파일명) 형태로 적으세요.\n\n"
                "[참고자료]\n{context}",
            ),
            ("human", "{question}"),
        ]
    )
