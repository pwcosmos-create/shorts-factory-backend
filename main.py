# 🚀 소상공인 숏폼 완전 자동화 파이프라인 (FastAPI 백엔드 마스터 소스)
# 핵심 기술: Structured Output(구조화 데이터), Imagen 3(9:16 최적화), Luma Ray(연속성 비디오), Lyria(저작권 프리 오디오)

import json
import base64
import asyncio
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional

from google import genai
from google.genai import types
from assembler import VideoAssembler

app = FastAPI(
    title="Google AI Omniverse Shorts Automation API",
    description="BYOK 기반 구글/Replicate 통합 숏폼 생성 파이프라인 (SSE 지원)",
    version="1.0.0"
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/v1/shorts/health")
async def shorts_health():
    return {"status": "ok", "service": "shorts-factory", "pipeline": "generate-pipeline"}


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "shorts.html")


@app.get("/shorts")
async def shorts_page():
    return FileResponse(STATIC_DIR / "shorts.html")

# ---------------------------------------------------------------------------
# 1. API 데이터 스키마 정의
# ---------------------------------------------------------------------------

class UserCredentials(BaseModel):
    api_key: str = Field(..., description="구글 AI 스튜디오 API 키")

class ConceptExampleRequest(BaseModel):
    credentials: UserCredentials
    business_name: str = Field(..., description="매장명")
    keywords: Optional[str] = Field(None, description="선택적 핵심 키워드")

class GenerateRequest(BaseModel):
    credentials: UserCredentials
    replicate_api_key: Optional[str] = Field(None, description="Replicate API 키 (선택, 영상 변환용)")
    business_name: str = Field(..., description="매장명")
    keywords: Optional[str] = Field(None, description="선택적 핵심 키워드")
    business_concept: str = Field(..., description="매장 컨셉")
    video_style: str = Field("Trendy & Dynamic", description="영상 분위기")
    duration_seconds: int = Field(15, description="전체 길이")

class SceneScript(BaseModel):
    scene_number: int
    duration_ratio: float
    narration: str
    caption: str
    imagen_prompt: str
    veo_prompt: Optional[str] = None

class ShortsBlueprint(BaseModel):
    bgm_lyria_prompt: str
    scenes: List[SceneScript]

# ---------------------------------------------------------------------------
# 2. 엔진 클래스 (Google + Replicate)
# ---------------------------------------------------------------------------

class ShortsEngine:
    def __init__(self, google_api_key: str, replicate_api_key: str):
        self.google_api_key = google_api_key
        self.replicate_api_key = replicate_api_key
        self.client = genai.Client(api_key=self.google_api_key)

    def _fallback_blueprint(
        self, name: str, concept: str, style: str, duration: int
    ) -> ShortsBlueprint:
        """API 실패 시에도 30초 숏폼에 맞는 다장면 시나리오를 반환합니다."""
        if duration <= 15:
            ratios = [0.35, 0.35, 0.30]
            narrations = [
                f"안녕하세요, {name}입니다.",
                f"{concept} — 맛과 품질을 자신합니다.",
                "지금 바로 방문해 보세요!",
            ]
            captions = ["우리 가게를 소개합니다", "시그니처 메뉴", "오늘의 추천"]
        else:
            ratios = [0.20, 0.30, 0.30, 0.20]
            narrations = [
                f"{name}, 잠깐만 주목해 주세요.",
                f"저희는 {concept}을(를) 자랑합니다.",
                "정성과 맛, 그리고 합리적인 가격까지.",
                "오늘 꼭 한번 들러 주세요!",
            ]
            captions = ["오프닝", "대표 메뉴", "매장 분위기", "방문 유도"]

        scenes = [
            SceneScript(
                scene_number=i + 1,
                duration_ratio=ratios[i],
                narration=narrations[i],
                caption=captions[i],
                imagen_prompt=(
                    f"Vertical 9:16 cinematic food photography, {concept}, "
                    f"{style} style, scene {i + 1}, 8k, appetizing"
                ),
                veo_prompt="Slow cinematic camera movement, vertical video",
            )
            for i in range(len(ratios))
        ]
        return ShortsBlueprint(
            bgm_lyria_prompt=f"Upbeat {style} background music for a local shop promo, 30 seconds",
            scenes=scenes,
        )

    def _normalize_blueprint(self, blueprint: ShortsBlueprint) -> ShortsBlueprint:
        if not blueprint.scenes:
            raise ValueError("시나리오에 장면이 없습니다.")
        total = sum(s.duration_ratio for s in blueprint.scenes)
        if total <= 0:
            equal = 1.0 / len(blueprint.scenes)
            for s in blueprint.scenes:
                s.duration_ratio = equal
        else:
            for s in blueprint.scenes:
                s.duration_ratio = s.duration_ratio / total
        return blueprint

    async def generate_blueprint(
        self,
        name: str,
        concept: str,
        style: str,
        duration: int,
        keywords: Optional[str] = None,
    ) -> ShortsBlueprint:
        scene_count = 4 if duration >= 30 else 3
        try:
            prompt = (
                f"Create a {duration}-second vertical short-form video script for a local business "
                f"named '{name}' about '{concept}'. Style: {style}. "
                f"Use exactly {scene_count} scenes. duration_ratio values MUST sum to 1.0. "
                f"Narration and captions MUST be in Korean. "
                f"Each imagen_prompt MUST mention 9:16 vertical aspect ratio."
            )
            if keywords:
                prompt += f" Highlight keywords: {keywords}."
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ShortsBlueprint,
                    temperature=0.7,
                ),
            )
            blueprint = ShortsBlueprint.model_validate_json(response.text)
            return self._normalize_blueprint(blueprint)
        except Exception as e:
            print(f"[Fallback] Gemini API 에러: {e}")
            return self._fallback_blueprint(name, concept, style, duration)

    async def generate_imagen_asset(self, prompt: str) -> str:
        try:
            result = self.client.models.generate_images(
                model='imagen-3.0-generate-002', prompt=prompt, 
                config=types.GenerateImagesConfig(aspect_ratio="9:16", number_of_images=1)
            )
            return base64.b64encode(result.generated_images[0].image.image_bytes).decode('utf-8')
        except Exception as e:
            print(f"[Fallback] Imagen 에러: {e}")
            return "MOCK_IMAGE"

    async def generate_replicate_video(self, image_b64: str, prompt: str) -> str:
        data_uri = f"data:image/png;base64,{image_b64}"
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.replicate_api_key}", "Content-Type": "application/json"}
            payload = {
                "input": {
                    "prompt": prompt,
                    "image": data_uri
                }
            }
            # Luma Ray 모델 사용
            res = await client.post("https://api.replicate.com/v1/models/luma/ray/predictions", json=payload, headers=headers)
            res.raise_for_status()
            pred = res.json()
            
            while pred["status"] not in ["succeeded", "failed", "canceled"]:
                await asyncio.sleep(3)
                res = await client.get(pred["urls"]["get"], headers=headers)
                pred = res.json()
                
            if pred["status"] == "succeeded":
                video_url = pred["output"]
                vid_res = await client.get(video_url)
                return base64.b64encode(vid_res.content).decode("utf-8")
            else:
                raise Exception(f"Replicate 실패: {pred.get('error')}")

    async def generate_lyria_bgm(self, prompt: str, duration: int) -> str:
        try:
            audio_result = self.client.models.generate_audio(
                model='lyria-3-pro-preview', prompt=prompt, 
                config=types.GenerateAudioConfig(duration_seconds=duration)
            )
            return base64.b64encode(audio_result.audio_bytes).decode('utf-8')
        except Exception as e:
            return "MOCK_AUDIO"

# ---------------------------------------------------------------------------
# 3. 파이프라인 실행 (공통 로직)
# ---------------------------------------------------------------------------

async def execute_shorts_pipeline(request: GenerateRequest) -> dict:
    replicate_key = (request.replicate_api_key or "").strip()
    engine = ShortsEngine(request.credentials.api_key, replicate_key)

    blueprint = await engine.generate_blueprint(
        name=request.business_name,
        concept=request.business_concept,
        style=request.video_style,
        duration=request.duration_seconds,
        keywords=request.keywords,
    )

    bgm_bytes = await engine.generate_lyria_bgm(
        blueprint.bgm_lyria_prompt, request.duration_seconds
    )

    generated_scenes_assets = []
    timeline_scenes = []

    for scene in blueprint.scenes:
        img_asset = await engine.generate_imagen_asset(scene.imagen_prompt)

        video_asset = img_asset
        if scene.veo_prompt and replicate_key and img_asset != "MOCK_IMAGE":
            try:
                video_asset = await engine.generate_replicate_video(
                    img_asset, scene.veo_prompt
                )
            except Exception as e:
                print(f"[Skip] Replicate 장면 {scene.scene_number}: {e}")

        generated_scenes_assets.append({
            "scene_number": scene.scene_number,
            "narration": scene.narration,
            "caption": scene.caption,
            "duration_ratio": scene.duration_ratio,
            "image_data_preview": img_asset,
            "video_data_render": video_asset,
        })
        timeline_scenes.append({
            "scene_number": scene.scene_number,
            "caption": scene.caption,
            "narration": scene.narration,
        })

    final_video_url = None
    try:
        assembler = VideoAssembler()
        final_video_url = assembler.assemble(
            bgm_bytes,
            generated_scenes_assets,
            total_duration_seconds=request.duration_seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"30초 영상 조립 실패: {e}. FFmpeg 설치 여부를 확인해 주세요.",
        ) from e

    if not final_video_url:
        raise HTTPException(status_code=500, detail="영상 파일이 생성되지 않았습니다.")

    return {
        "message": f"{request.duration_seconds}초 숏폼 영상 생성 완료",
        "meta": {
            "business_name": request.business_name,
            "style": request.video_style,
            "total_duration": request.duration_seconds,
        },
        "assets": {"timeline_scenes": timeline_scenes},
        "final_video_url": final_video_url,
    }


@app.post("/api/v1/shorts/generate-pipeline")
async def run_shorts_pipeline(request: GenerateRequest):
    """coupax 스튜디오 UI가 호출하는 동기 JSON 엔드포인트."""
    try:
        return await execute_shorts_pipeline(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 4. 실시간 스트리밍 엔드포인트 (SSE)
# ---------------------------------------------------------------------------

@app.post("/api/v1/shorts/generate-stream")
async def run_shorts_stream(request: GenerateRequest):
    async def event_generator():
        try:
            yield f"data: {json.dumps({'step': 'init', 'message': '시나리오 작성 중...'})}\n\n"

            replicate_key = (request.replicate_api_key or "").strip()
            engine = ShortsEngine(request.credentials.api_key, replicate_key)
            blueprint = await engine.generate_blueprint(
                name=request.business_name,
                concept=request.business_concept,
                style=request.video_style,
                duration=request.duration_seconds,
                keywords=request.keywords,
            )

            yield f"data: {json.dumps({'step': 'blueprint', 'data': blueprint.model_dump(), 'message': '시나리오 작성 완료. 이미지 생성 중...'})}\n\n"

            bgm_bytes = await engine.generate_lyria_bgm(
                blueprint.bgm_lyria_prompt, request.duration_seconds
            )

            generated_scenes_assets = []
            for scene in blueprint.scenes:
                yield f"data: {json.dumps({'step': 'scene_start', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 이미지 생성 중...'})}\n\n"

                img_asset = await engine.generate_imagen_asset(scene.imagen_prompt)
                yield f"data: {json.dumps({'step': 'image_done', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 비디오 변환 중...'})}\n\n"

                video_asset = img_asset
                if scene.veo_prompt and replicate_key and img_asset != "MOCK_IMAGE":
                    try:
                        video_asset = await engine.generate_replicate_video(
                            img_asset, scene.veo_prompt
                        )
                        yield f"data: {json.dumps({'step': 'video_done', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 비디오 생성 완료'})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'step': 'video_failed', 'scene_number': scene.scene_number, 'error': str(e)})}\n\n"

                generated_scenes_assets.append({
                    "scene_number": scene.scene_number,
                    "narration": scene.narration,
                    "caption": scene.caption,
                    "duration_ratio": scene.duration_ratio,
                    "image_data_preview": img_asset,
                    "video_data_render": video_asset,
                })

            yield f"data: {json.dumps({'step': 'assembling', 'message': '모든 클립 생성 완료. 최종 영상 병합 중...'})}\n\n"

            final_video_url = None
            try:
                assembler = VideoAssembler()
                final_video_url = assembler.assemble(
                    bgm_bytes,
                    generated_scenes_assets,
                    total_duration_seconds=request.duration_seconds,
                )
            except Exception as e:
                yield f"data: {json.dumps({'step': 'error', 'message': f'영상 조립 실패: {e}'})}\n\n"
                return

            yield f"data: {json.dumps({'step': 'complete', 'final_video_url': final_video_url, 'message': f'{request.duration_seconds}초 숏폼 영상 생성 완료!'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/v1/shorts/generate-concept-example")
async def generate_concept_example(request: ConceptExampleRequest):
    try:
        client = genai.Client(api_key=request.credentials.api_key)
        prompt = f"사용자가 '{request.business_name}'라는 매장 이름으로 숏폼 비디오를 만들려고 합니다."
        if request.keywords: prompt += f" 핵심 키워드: '{request.keywords}'"
        prompt += " 이 매장의 '컨셉 및 대표 메뉴' 란에 들어갈 만한 아주 구체적이고 매력적인 홍보용 작성 예시(3~5문장)를 생성해주세요. 텍스트만 반환하세요."
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"example": response.text.strip()}
    except Exception as e:
        return {"example": f"[{request.business_name}]만의 특별한 컨셉을 적어주세요."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
