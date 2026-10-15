"""Gradio 웹 UI.

- layout.py   : 화면 배치(컴포넌트)만 담당
- handlers.py : 버튼/입력 이벤트에서 실행되는 함수 (DB 불러오기, 답변, 대화 지우기)
- app.py      : layout과 handlers를 이벤트로 연결해 gr.Blocks를 만든다
"""
