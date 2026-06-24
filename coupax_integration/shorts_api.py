"""
coupax.co.kr Flask 앱 — 숏폼 API 라우트

coupax app.py 에 추가:
    from coupax_integration.shorts_api import shorts_api_bp
    app.register_blueprint(shorts_api_bp)

환경 변수:
    SHORTS_FASTAPI_URL  — FastAPI 백엔드 URL (기본 http://127.0.0.1:8000)
                          설정 시 프록시 모드, 미설정·연결 실패 시 인프로세스 실행
"""

from __future__ import annotations

import asyncio
import os

import httpx
from flask import Blueprint, jsonify, request

shorts_api_bp = Blueprint("shorts_api", __name__)

FASTAPI_URL = os.environ.get("SHORTS_FASTAPI_URL", "http://127.0.0.1:8000").rstrip("/")
PIPELINE_TIMEOUT = float(os.environ.get("SHORTS_PIPELINE_TIMEOUT", "600"))


def _run_pipeline_inprocess(payload: dict) -> tuple[dict, int]:
    """숏폼공장 main.py 파이프라인을 같은 서버에서 직접 실행."""
    from main import GenerateRequest, execute_shorts_pipeline

    req = GenerateRequest.model_validate(payload)
    result = asyncio.run(execute_shorts_pipeline(req))
    return result, 200


def _proxy_to_fastapi(payload: dict) -> tuple[dict, int]:
    with httpx.Client(timeout=PIPELINE_TIMEOUT) as client:
        res = client.post(
            f"{FASTAPI_URL}/api/v1/shorts/generate-pipeline",
            json=payload,
        )
    try:
        body = res.json()
    except Exception:
        body = {"detail": res.text or f"HTTP {res.status_code}"}
    return body, res.status_code


@shorts_api_bp.get("/api/v1/shorts/health")
def shorts_health():
    """배포·nginx 프록시 점검용."""
    fastapi_ok = False
    detail = ""
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{FASTAPI_URL}/api/v1/shorts/health")
            fastapi_ok = r.status_code == 200
            detail = r.json() if fastapi_ok else r.text
    except Exception as e:
        detail = str(e)
    return jsonify({
        "flask_shorts_api": "ok",
        "fastapi_reachable": fastapi_ok,
        "fastapi_url": FASTAPI_URL,
        "fastapi_detail": detail,
    })


@shorts_api_bp.post("/api/v1/shorts/generate-pipeline")
def generate_pipeline():
    payload = request.get_json(silent=True) or {}

    if not payload.get("credentials", {}).get("api_key"):
        return jsonify({
            "detail": "Google AI API 키가 필요합니다.",
            "code": "api_key_required",
        }), 400

    if not payload.get("business_name") or not payload.get("business_concept"):
        return jsonify({
            "detail": "매장명과 컨셉을 입력해 주세요.",
        }), 400

    use_proxy = os.environ.get("SHORTS_USE_FASTAPI_PROXY", "1") == "1"

    try:
        if use_proxy:
            try:
                body, status = _proxy_to_fastapi(payload)
                if status < 500:
                    return jsonify(body), status
            except httpx.ConnectError:
                pass
            except httpx.TimeoutException:
                return jsonify({
                    "detail": "영상 생성 시간이 초과되었습니다. 30초 영상은 2~5분 걸릴 수 있습니다.",
                }), 504

        body, status = _run_pipeline_inprocess(payload)
        return jsonify(body), status

    except Exception as e:
        return jsonify({
            "detail": f"숏폼 생성 실패: {e}",
        }), 500
