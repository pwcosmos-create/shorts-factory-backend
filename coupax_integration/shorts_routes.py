"""
coupax.co.kr Flask 앱에 붙이는 숏폼공장 라우트

배포 순서:
  1. coupax_integration/static/shorts.css, shorts.js → coupax /static/ 폴더에 복사
  2. app.py 에 blueprint 등록
  3. home_patch.html 내용을 홈 템플릿에 반영
  4. nginx: /api/v1/shorts/ → FastAPI(8000) 프록시

app.py:
    from coupax_integration.shorts_routes import shorts_bp
    app.register_blueprint(shorts_bp)
"""

from pathlib import Path

from flask import Blueprint, send_from_directory

shorts_bp = Blueprint("shorts", __name__)

_INTEGRATION_DIR = Path(__file__).resolve().parent


@shorts_bp.route("/shorts")
def shorts_page():
    return send_from_directory(_INTEGRATION_DIR, "shorts.html")
