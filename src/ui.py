"""[1] UI 레이아웃. 이벤트 연결은 app.py가 담당한다."""

from types import SimpleNamespace

import gradio as gr


def render() -> SimpleNamespace:
    """gr.Blocks 컨텍스트 안에서 호출해 컴포넌트를 배치하고 묶어서 반환한다.

    반환 속성(이름이 계약이다): openai_key, pdf_file, status, db_state,
    question, ask_btn, output
    """
    gr.Markdown("# ChatPDF\n---")

    openai_key = gr.Textbox(label="OPEN_AI_API_KEY", type="password")
    pdf_file = gr.File(label="PDF 파일을 올려주세요!", file_types=[".pdf"], type="filepath")
    status = gr.Markdown()
    db_state = gr.State()

    gr.Markdown("---\n## PDF에게 질문해보세요!!")
    question = gr.Textbox(label="질문을 입력하세요")
    ask_btn = gr.Button("질문하기", variant="primary")
    output = gr.Markdown()

    return SimpleNamespace(
        openai_key=openai_key, pdf_file=pdf_file, status=status, db_state=db_state,
        question=question, ask_btn=ask_btn, output=output,
    )
