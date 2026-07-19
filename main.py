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
        """API 실패 시에도 쿠팡 파트너스 목적에 부합하는 다장면 폴백 시나리오를 반환합니다."""
        if duration <= 15:
            ratios = [0.35, 0.40, 0.25]
            narrations = [
                f"요즘 난리난 {name}, 대체 왜 이렇게 핫할까요?",
                f"바로 {concept} 때문입니다. 가성비와 퀄리티를 모두 잡았습니다.",
                "고정 댓글 링크에서 한정 수량 최저가 혜택을 지금 확인해 보세요!",
            ]
            captions = ["요즘 대세 추천템", "핵심 장점 정리", "댓글에서 최저가 확인"]
        else:
            ratios = [0.25, 0.30, 0.25, 0.20]
            narrations = [
                f"돈 낭비 없는 {name} 선택 가이드, 딱 30초만 집중해 주세요.",
                f"첫 번째 핵심 소구점은 {concept}입니다.",
                "사용자들의 실제 극찬 후기와 가성비까지 철저히 검증 완료했습니다.",
                "영상 하단 고정 댓글의 제휴 링크에서 특별 할인가로 만나보세요!",
            ]
            captions = ["실패 없는 선택", "독보적인 강점", "사용자 극찬 후기", "댓글에서 최저가 확인"]

        scenes = [
            SceneScript(
                scene_number=i + 1,
                duration_ratio=ratios[i],
                narration=narrations[i],
                caption=captions[i],
                imagen_prompt=(
                    f"Vertical 9:16 high-quality cinematic product photography of {name}, "
                    f"{style} style, showcasing {concept}, scene {i + 1}, 8k resolution"
                ),
                veo_prompt="Slow elegant panning camera movement, focus on details, vertical video",
            )
            for i in range(len(ratios))
        ]
        return ShortsBlueprint(
            bgm_lyria_prompt=f"Upbeat energetic {style} background music for online product recommendation video, {duration} seconds",
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
        
        # PAOF 원칙 및 쿠팡 파트너스 홍보 목적에 맞춘 고효율 카피라이팅 프롬프트 정의
        persona = (
            "너는 시청자 유지율 60% 이상을 자랑하고 쿠팡 파트너스 구매 전환율을 극대화하는 "
            "상위 1% 숏폼 콘텐츠 크리에이터이자 전문 카피라이터야."
        )
        objective = (
            f"홍보할 상품명은 '{name}'이고, 제품 컨셉 및 소구점은 '{concept}'이야. "
            f"목표는 시청자를 첫 3초 이내에 확실히 사로잡고(HOOK), 상품의 핵심 셀링 포인트를 직관적으로 각인시켜, "
            f"마지막에 댓글창이나 프로필의 쿠팡 파트너스 제휴 링크를 클릭(CTA)하도록 만드는 {duration}초 분량의 9:16 세로형 숏폼 대본을 작성하는 거야."
        )
        
        if scene_count == 3:
            scene_guidelines = [
                "1장면 (강력한 HOOK 인트로): 시청자의 일상적 문제나 궁금증을 정확히 짚어내고 해결책을 제시하며 영상의 기대감을 높이는 인트로 (시간 비율 약 30%)",
                "2장면 (핵심 본문): 제품의 가장 큰 셀링 포인트와 실제 사용 시의 혜택/효과를 구체적인 예시와 함께 강조 (시간 비율 약 40%)",
                "3장면 (클로징 및 CTA): 전체 내용을 임팩트 있게 요약하고, '댓글 링크에서 최저가로 바로 확인해 보세요!'와 같이 제휴 링크 클릭을 자연스럽게 유도하는 마무리 (시간 비율 약 30%)"
            ]
        else:
            scene_guidelines = [
                "1장면 (강력한 HOOK 인트로): 시청자의 시선을 끄는 충격적이거나 일상적인 문제 제기 및 호기심 자극 (시간 비율 약 20%)",
                "2장면 (본문 소주제 1): 제품의 시그니처 특징 및 핵심 혜택 제시 (시간 비율 약 30%)",
                "3장면 (본문 소주제 2): 실제 체감되는 리스크 감소율이나 가성비, 실사용 장점 강조 (시간 비율 약 30%)",
                "4장면 (클로징 및 CTA): 요약과 함께 댓글/프로필의 쿠팡 파트너스 링크 클릭을 유도하는 강력한 행동 촉구 (시간 비율 약 20%)"
            ]
            
        # AI 영상 퀄리티를 높이기 위한 '6단계 프롬프트 공식' 및 '시네마틱 연출 치트키' 강제화 규칙
        visual_rules = (
            "각 장면의 imagen_prompt(이미지 생성용 영어 프롬프트)는 반드시 아래의 [6단계 프롬프트 공식]에 맞추어 쉼표(,)로 구분된 단어들로 작성해줘:\n"
            "1. [Style]: 영상의 장르 및 화풍 정의 (예: 'Cinematic film still, Shot on 35mm film, Soft natural lighting' 또는 'Disney Pixar 3D animation style')\n"
            "2. [Subject]: 주인공/제품 상세 묘사 (의인화된 동물의 경우 'Anthropomorphic [animal]' 필수 사용, 제품 로고/텍스트 노출 시 'text \"[원하는문구]\" written on [위치]' 형식 적용, 한글 텍스트인 경우 뒤에 ', written in Korean Hangul' 추가)\n"
            "3. [Action & Pose]: 캐릭터의 동작 및 구체적인 모션 (예: 'Slow zoom in', 'Looking at the camera', 'Cooking soup')\n"
            "4. [Background & Lighting]: 주변 환경과 조명/분위기 (예: 'Sunny cafe, Soft natural lighting' 또는 'Neon lights, Cyberpunk atmosphere')\n"
            "5. [Camera Angle]: 카메라 앵글 및 연출 (예: 'Drone shot', 'Eye-level', 'Extreme close-up', 'Low angle shot')\n"
            "6. [Texture & Quality]: 마무리 퀄리티 질감 (예: 'Authentic skin texture', 'Fluffy fur texture', 'High quality render')\n\n"
            "또한, 다음 지침을 반드시 준수해줘:\n"
            "- veo_prompt(비디오 변환용 영어 프롬프트)는 정지된 이미지에 자연스럽고 역동적인 무빙을 입힐 수 있도록 구체적인 카메라 모션 키워드만으로 작성해줘. (예: 'Slow zoom in', 'Camera tracking shot', 'Slow elegant panning')\n"
            "- 각 imagen_prompt는 항상 '9:16 vertical aspect ratio'를 포함해야 해.\n"
            "- [★중요 - 텍스트 노이즈 방지]: 이미지 생성 시 AI가 멋대로 이상한 글자나 기호, 악보 등을 그리는 것을 방지하기 위해, 의도적으로 텍스트 노출 지침(text \"...\")을 넣은 경우를 제외하고는 모든 imagen_prompt 끝에 반드시 다음 세 줄의 네거티브 지침을 추가해줘:\n"
            "  'No on-screen text.\n"
            "  No subtitles.\n"
            "  No background music.'"
        )
        
        action = (
            f"규격에 맞추어 정확히 {scene_count}개의 장면(scenes)으로 구성해줘. "
            "각 장면의 duration_ratio의 합은 반드시 1.0이 되어야 해. "
            "자막(caption)은 화면에 들어가는 짧고 강렬한 텍스트로 작성하고, 나레이션(narration)은 TTS로 읽기 좋은 자연스러운 한국어 구어체로 써줘."
        )
        
        prompt = (
            f"[Persona]\n{persona}\n\n"
            f"[Objective]\n{objective}\n\n"
            f"[Scene Guidelines]\n" + "\n".join(scene_guidelines) + "\n\n"
            f"[Visual & Motion Rules]\n{visual_rules}\n\n"
            f"[Action & Format]\n{action}"
        )
        
        if keywords:
            prompt += f"\n\n[Additional Keywords]\nHighlight these keywords in the script: {keywords}."
            
        try:
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
