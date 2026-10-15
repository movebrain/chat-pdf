"""화면 배치. 컴포넌트만 만들고 이벤트 연결은 app.py가 담당한다.

화면 구성:
    제목 / 설명
    ┌ 왼쪽 ─────────────┐ ┌ 오른쪽 ─────────────────────┐
    │ 불러오기 상태      │ │ 대화 (Chatbot)               │
    │ [학칙 불러오기]    │ │ 질문 입력란                  │
    │ ▶ 검색 설정        │ │ [질문하기] [대화 지우기]     │
    └───────────────────┘ │ 질문 예시                    │
                          └──────────────────────────────┘
"""

from types import SimpleNamespace

import gradio as gr

from src.rag.generator import SEARCH_MODE

TITLE = "🎓 서울대학교 학칙 안내 챗봇"
DESCRIPTION = (
    "서울대학교 학칙을 근거로 답하고 쪽수를 함께 보여줍니다. 질문만 입력하세요. "
    '학칙에 없는 내용은 "제공된 참고자료에서는 확인되지 않습니다"라고 답합니다.'
)

# 검색 설정의 선택지: (화면에 보이는 이름, retriever.get_retriever()의 mode 값)
SEARCH_MODES = [
    ("MMR: 서로 겹치지 않는 3개 (기본)", "mmr"),
    ("기본: 가장 비슷한 4개", "basic"),
    ("질문 확장: 여러 표현으로 검색 (느리고 비용 증가)", "multi_query"),
]

EXAMPLES = [
    "서울대학교 휴학은 몇 학기까지 가능한가요?",
    "학사과정 졸업에 필요한 요건은?",
    "학사경고를 받는 기준은 무엇인가요?",
    "등록금 반환 기준이 어떻게 되나요?",
    "학교 잠깐 쉬고 싶은데 어떻게 해요?",
]


def render() -> SimpleNamespace:
    """gr.Blocks 컨텍스트 안에서 호출해 컴포넌트를 배치하고 묶어서 반환한다.

    반환 속성(이름이 app.py와의 계약이다):
        status, load_btn, mode, chatbot, question, ask_btn, clear_btn
    """
    gr.Markdown(f"# {TITLE}\n### {DESCRIPTION}")

    with gr.Row():
        # 왼쪽: 학칙 불러오기 상태와 설정
        with gr.Column(scale=1):
            status = gr.Markdown("⏳ 학칙을 불러오는 중입니다...")
            load_btn = gr.Button("학칙 불러오기")
            with gr.Accordion("검색 설정", open=False):
                mode = gr.Dropdown(
                    choices=SEARCH_MODES,
                    value=SEARCH_MODE,
                    label="검색 방식",
                    info="답변에 참고할 학칙 조각을 찾는 방법입니다.",
                )

        # 오른쪽: 대화 영역
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="대화", height=420)
            question = gr.Textbox(
                label="질문을 입력하세요",
                placeholder="예) 서울대 휴학은 몇 학기까지 가능한가요?",
            )
            with gr.Row():
                ask_btn = gr.Button("질문하기", variant="primary")
                clear_btn = gr.Button("대화 지우기")
            gr.Examples(examples=EXAMPLES, inputs=question, label="질문 예시")

    return SimpleNamespace(
        status=status, load_btn=load_btn, mode=mode,
        chatbot=chatbot, question=question, ask_btn=ask_btn, clear_btn=clear_btn,
    )
