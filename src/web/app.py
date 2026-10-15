"""layout(화면)과 handlers(이벤트 함수)를 연결해 Gradio 앱을 만든다."""

import gradio as gr

from src.web import handlers, layout


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="서울대학교 학칙 안내 챗봇") as demo:
        c = layout.render()

        # 페이지가 열리면 학칙 DB 준비 (처음 한 번만 임베딩)
        demo.load(handlers.load_db, outputs=c.status)
        c.load_btn.click(handlers.reload_db, outputs=c.status)

        # inputs 순서 = respond(question, chat, mode) 매개변수 순서
        ask_inputs = [c.question, c.chatbot, c.mode]
        ask_outputs = [c.chatbot, c.question]
        c.ask_btn.click(handlers.respond, inputs=ask_inputs, outputs=ask_outputs)
        c.question.submit(handlers.respond, inputs=ask_inputs, outputs=ask_outputs)

        c.clear_btn.click(handlers.clear, outputs=ask_outputs)
    return demo
