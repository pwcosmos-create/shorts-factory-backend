"""
coupax.co.kr Flask 앱에 붙이는 숏폼공장 라우트

배포 순서:
  1. coupax_integration/static/ → coupax /static/ (shorts.js, device-save.js, shorts.css)
  2. app.py 에 blueprint 등록 (페이지 + API)
  3. home_patch.html 내용을 홈 템플릿에 반영
  4. (권장) nginx: /api/v1/shorts/ → FastAPI(8000)
     또는 shorts_api_bp 만 등록해 Flask에서 직접 파이프라인 실행

app.py:
    from coupax_integration.shorts_routes import shorts_bp
    from coupax_integration.shorts_api import shorts_api_bp
    app.register_blueprint(shorts_bp)
    app.register_blueprint(shorts_api_bp)

기존 coupax generate-pipeline 라우트가 있으면 제거하거나
shorts_api_bp 가 먼저 등록되도록 하세요. (Pipeline error 원인)
"""

from pathlib import Path

from flask import Blueprint, send_from_directory

shorts_bp = Blueprint("shorts", __name__)

_INTEGRATION_DIR = Path(__file__).resolve().parent


@shorts_bp.route("/shorts")
def shorts_page():
    return send_from_directory(_INTEGRATION_DIR, "shorts.html")
