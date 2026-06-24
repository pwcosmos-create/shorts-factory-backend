import os
import uuid
import base64
from pathlib import Path
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from gtts import gTTS

# IMAGEMAGICK_BINARY 환경변수가 필요할 수 있음 (TextClip 렌더링용)
# Windows 환경이면 ImageMagick 설치 후 아래 경로 설정이 필요할 수 있습니다.
# os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

OUTPUT_DIR = Path(__file__).parent / "static" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class VideoAssembler:
    def __init__(self):
        self.temp_dir = OUTPUT_DIR / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def decode_base64_to_file(self, b64_str: str, ext: str) -> Path:
        filepath = self.temp_dir / f"{uuid.uuid4()}{ext}"
        try:
            # If there's a data URI prefix, remove it
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_str))
            return filepath
        except Exception as e:
            print(f"Base64 디코딩 에러: {e}")
            return None

    def generate_tts(self, text: str) -> Path:
        filepath = self.temp_dir / f"{uuid.uuid4()}_tts.mp3"
        try:
            tts = gTTS(text=text, lang='ko')
            tts.save(str(filepath))
            return filepath
        except Exception as e:
            print(f"TTS 생성 에러: {e}")
            return None

    def assemble(self, bgm_b64: str, scenes: list) -> str:
        """
        BGM과 각 Scene(이미지/영상, 내레이션, 자막)을 조합하여 최종 mp4를 생성합니다.
        반환값은 static/outputs/ 기준의 상대 URL입니다.
        """
        clips = []
        tts_files = []
        media_files = []
        
        bgm_path = None
        if bgm_b64 and "MOCK" not in bgm_b64:
            bgm_path = self.decode_base64_to_file(bgm_b64, ".mp3")
        
        try:
            for scene in scenes:
                # 1. 미디어 클립 생성 (영상 우선, 없으면 이미지)
                media_path = None
                is_video = False
                
                if scene.get("video_data_render") and "MOCK" not in scene["video_data_render"] and "FALLBACK" not in scene["video_data_render"]:
                    media_path = self.decode_base64_to_file(scene["video_data_render"], ".mp4")
                    is_video = True
                elif scene.get("image_data_preview") and "MOCK" not in scene["image_data_preview"]:
                    media_path = self.decode_base64_to_file(scene["image_data_preview"], ".png")
                
                if not media_path or not media_path.exists():
                    # 빈 클립(검은 화면) 폴백 생성 (에러 방지용)
                    # 여기서는 간단히 ImageClip으로 5초짜리 더미 생성 (실제로는 에러 처리)
                    pass
                else:
                    media_files.append(media_path)
                
                # 2. 내레이션 오디오 생성 (TTS)
                tts_path = None
                narration = scene.get("narration", "")
                if narration:
                    tts_path = self.generate_tts(narration)
                    if tts_path: tts_files.append(tts_path)
                
                # 3. MoviePy 클립 조립
                if media_path:
                    if is_video:
                        base_clip = VideoFileClip(str(media_path))
                        # 비디오 길이를 우선
                        clip_duration = base_clip.duration
                    else:
                        base_clip = ImageClip(str(media_path))
                        # 이미지일 경우 TTS 길이에 맞춤 (TTS 없으면 기본 5초)
                        clip_duration = 5.0
                        if tts_path:
                            try:
                                audio_clip = AudioFileClip(str(tts_path))
                                clip_duration = audio_clip.duration + 0.5
                                audio_clip.close()
                            except:
                                pass
                        base_clip = base_clip.set_duration(clip_duration)
                    
                    # 오디오(TTS) 합치기
                    if tts_path:
                        try:
                            audio_clip = AudioFileClip(str(tts_path))
                            base_clip = base_clip.set_audio(audio_clip)
                        except Exception as e:
                            print(f"TTS 오디오 병합 에러: {e}")
                            
                    # 자막(Text) 합치기 (ImageMagick 필요)
                    caption = scene.get("caption", "")
                    if caption:
                        try:
                            # 윈도우 환경 등에서 font 경로 문제가 생길 수 있어 기본 폰트 사용
                            # 한글이 깨질 수 있으므로, 실제 서비스에서는 폰트 파일 경로 지정 권장
                            txt_clip = TextClip(caption, fontsize=50, color='white', bg_color='black')
                            txt_clip = txt_clip.set_pos(('center', 'bottom')).set_duration(clip_duration)
                            base_clip = CompositeVideoClip([base_clip, txt_clip])
                        except Exception as e:
                            print(f"자막 생성 에러 (ImageMagick 필요): {e}")

                    clips.append(base_clip)
            
            if not clips:
                raise Exception("조립할 미디어 클립이 없습니다.")

            # 전체 이어붙이기
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # BGM 합성
            if bgm_path:
                try:
                    bgm_clip = AudioFileClip(str(bgm_path)).volumex(0.3)
                    # BGM 길이를 전체 비디오 길이에 맞춤
                    if bgm_clip.duration > final_clip.duration:
                        bgm_clip = bgm_clip.subclip(0, final_clip.duration)
                    
                    # 기존 음성(TTS)과 BGM 합성
                    if final_clip.audio:
                        from moviepy.editor import CompositeAudioClip
                        final_audio = CompositeAudioClip([final_clip.audio, bgm_clip])
                        final_clip = final_clip.set_audio(final_audio)
                    else:
                        final_clip = final_clip.set_audio(bgm_clip)
                except Exception as e:
                    print(f"BGM 병합 에러: {e}")

            output_filename = f"final_{uuid.uuid4().hex[:8]}.mp4"
            output_filepath = OUTPUT_DIR / output_filename
            
            # 렌더링
            final_clip.write_videofile(
                str(output_filepath), 
                fps=24, 
                codec="libx264", 
                audio_codec="aac",
                logger=None # 콘솔 로그 줄이기
            )
            
            # 리소스 정리
            final_clip.close()
            for c in clips: c.close()
            
            return f"/static/outputs/{output_filename}"
            
        finally:
            # 임시 파일 삭제
            for f in tts_files + media_files:
                try:
                    if f and f.exists(): f.unlink()
                except:
                    pass
            if bgm_path and bgm_path.exists():
                try: bgm_path.unlink()
                except: pass
