"""RAG 검색기, 문서 포매터, 프롬프트, 언어 모델을 LCEL 체인으로 연결한다."""

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough

from src.rag.prompt import get_prompt
from src.rag.retriever import format_docs


def make_chatbot(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
) -> Runnable[str, str]:
    """질문 하나를 받아 검색·프롬프트 작성·답변 생성을 수행하는 체인을 만든다.

    이 함수는 이미 생성된 검색기와 모델을 연결만 한다. API 키로 모델을 만드는
    일은 generator.answer()의 책임이고, UI 이벤트나 스트리밍 출력 처리도 하지
    않는다. 따라서 검색 전략을 바꾸려면 retriever 인자를 다른 검색기로 교체하면 된다.

    체인 안에서는 입력 질문을 두 갈래로 사용한다.
    1. 질문을 retriever에 전달하고 검색된 Document들을 format_docs()로 문자열화해
       프롬프트의 ``context``에 넣는다.
    2. 원래 질문은 그대로 프롬프트의 ``question``에 넣는다.
    완성된 메시지를 llm에 전달하고 StrOutputParser()로 모델 응답을 문자열로 바꾼다.

    Args:
        retriever: retriever.get_retriever(db, ...)가 만든 LangChain BaseRetriever.
            입력으로 질문 문자열을 받아 관련 Document 목록을 반환해야 한다.
        llm: 질문과 참고자료를 입력받아 답변을 생성하는 LangChain 언어 모델.
            예를 들어 generator에서 ChatOpenAI(model=config.GENERATE_MODEL, ... )로
            생성한 인스턴스를 전달한다.

    Returns:
        문자열 질문을 입력받아 문자열 답변을 반환하는 Runnable 체인.
        ``chain.invoke("원두 환불 규정 알려줘")``처럼 한 번 실행할 수 있고,
        ``chain.stream(question)``으로 모델 출력 조각을 순회할 수도 있다.

    Example:
        ``retriever = get_retriever(db, strategy="mmr", k=3, fetch_k=10)``
        ``chain = make_chatbot(retriever, llm)``
        ``answer = chain.invoke("원두 환불 규정 알려줘")``
    """
    return (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | get_prompt()
        | llm
        | StrOutputParser()
    )
