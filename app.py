"""[2] 진입점: .env를 읽고 웹 UI(src/web)를 띄운다.

실행: python app.py  → 브라우저에서 http://127.0.0.1:7860
화면 배치는 src/web/layout.py, 이벤트 함수는 src/web/handlers.py에 있다.
"""

from src.web.app import build_demo

try:  # 로컬 테스트용 .env. python-dotenv가 설치돼 있을 때만 읽는다
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

demo = build_demo()

if __name__ == "__main__":
    demo.launch()
