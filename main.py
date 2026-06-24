# 🚀 소상공인 숏폼 완전 자동화 파이프라인 (FastAPI 백엔드 마스터 소스)
# 핵심 기술: Structured Output(구조화 데이터), Imagen 3(9:16 최적화), Luma Ray(연속성 비디오), Lyria(저작권 프리 오디오)

import json
import base64
import asyncio
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
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
    replicate_api_key: str = Field(..., description="Replicate API 키")
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

    async def generate_blueprint(self, name: str, concept: str, style: str, duration: int, keywords: Optional[str] = None) -> ShortsBlueprint:
        try:
            prompt = f"Create a short-form video script blueprint for a restaurant named '{name}' specializing in '{concept}'. Style: {style}."
            if keywords: prompt += f" Highlight keywords: {keywords}."
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ShortsBlueprint,
                    temperature=0.7
                )
            )
            return ShortsBlueprint.model_validate_json(response.text)
        except Exception as e:
            print(f"[Fallback] Gemini API 에러: {e}")
            scenes = [
                SceneScript(
                    scene_number=1, duration_ratio=0.3,
                    narration=f"이곳 바로 {name}입니다.", caption="환상적인 비주얼!",
                    imagen_prompt=f"Cinematic close-up of {concept}, 8k, aspect ratio 9:16, {style} style.",
                    veo_prompt="Slow motion zooming in."
                )
            ]
            return ShortsBlueprint(bgm_lyria_prompt="A trendy lo-fi hip-hop track.", scenes=scenes)

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
# 3. 실시간 스트리밍 엔드포인트 (SSE)
# ---------------------------------------------------------------------------

@app.post("/api/v1/shorts/generate-stream")
async def run_shorts_stream(request: GenerateRequest):
    async def event_generator():
        try:
            yield f"data: {json.dumps({'step': 'init', 'message': '시나리오 작성 중...'})}\n\n"
            
            engine = ShortsEngine(request.credentials.api_key, request.replicate_api_key)
            blueprint = await engine.generate_blueprint(
                name=request.business_name,
                concept=request.business_concept,
                style=request.video_style,
                duration=request.duration_seconds,
                keywords=request.keywords
            )
            
            yield f"data: {json.dumps({'step': 'blueprint', 'data': blueprint.model_dump(), 'message': '시나리오 작성 완료. 이미지 생성 중...'})}\n\n"
            
            bgm_bytes = await engine.generate_lyria_bgm(blueprint.bgm_lyria_prompt, request.duration_seconds)
            
            generated_scenes_assets = []
            for scene in blueprint.scenes:
                yield f"data: {json.dumps({'step': 'scene_start', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 이미지 생성 중...'})}\n\n"
                
                img_asset = await engine.generate_imagen_asset(scene.imagen_prompt)
                yield f"data: {json.dumps({'step': 'image_done', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 비디오 변환 중...'})}\n\n"
                
                video_asset = img_asset
                if scene.veo_prompt and request.replicate_api_key:
                    try:
                        video_asset = await engine.generate_replicate_video(img_asset, scene.veo_prompt)
                        yield f"data: {json.dumps({'step': 'video_done', 'scene_number': scene.scene_number, 'message': f'장면 {scene.scene_number} 비디오 생성 완료'})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'step': 'video_failed', 'scene_number': scene.scene_number, 'error': str(e)})}\n\n"
                
                generated_scenes_assets.append({
                    "scene_number": scene.scene_number,
                    "narration": scene.narration,
                    "caption": scene.caption,
                    "image_data_preview": img_asset,
                    "video_data_render": video_asset
                })
            
            yield f"data: {json.dumps({'step': 'assembling', 'message': '모든 클립 생성 완료. 최종 영상 병합 중...'})}\n\n"
            
            assembler = VideoAssembler()
            final_video_url = assembler.assemble(bgm_bytes, generated_scenes_assets)
            
            yield f"data: {json.dumps({'step': 'complete', 'final_video_url': final_video_url, 'message': '최종 영상 생성 완료!'})}\n\n"
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
