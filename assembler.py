import uuid
import base64
from pathlib import Path

from moviepy import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
    ColorClip,
)
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

OUTPUT_DIR = Path(__file__).parent / "static" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHORTS_SIZE = (1080, 1920)
SHORTS_FPS = 24


class VideoAssembler:
    def __init__(self):
        self.temp_dir = OUTPUT_DIR / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 폰트 로드 및 캐싱 (디스크 I/O 최적화)
        font_path = "C:\\Windows\\Fonts\\malgunbd.ttf"
        try:
            self.font_caption = ImageFont.truetype(font_path, 60)
            self.font_narration = ImageFont.truetype(font_path, 42)
        except Exception as e:
            print(f"[Assembler] 기본 폰트 로드 실패: {e}. 시스템 기본 폰트로 대체합니다.")
            self.font_caption = ImageFont.load_default()
            self.font_narration = ImageFont.load_default()

    def decode_base64_to_file(self, b64_str: str, ext: str):
        filepath = self.temp_dir / f"{uuid.uuid4()}{ext}"
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_str))
            return filepath
        except Exception as e:
            print(f"Base64 디코딩 에러: {e}")
            return None

    def generate_tts(self, text: str):
        filepath = self.temp_dir / f"{uuid.uuid4()}_tts.mp3"
        try:
            tts = gTTS(text=text, lang="ko")
            tts.save(str(filepath))
            return filepath
        except Exception as e:
            print(f"TTS 생성 에러: {e}")
            return None

    def _scene_target_durations(self, scenes: list, total_duration_seconds: float) -> list:
        ratios = [max(float(s.get("duration_ratio") or 0), 0) for s in scenes]
        ratio_sum = sum(ratios)
        if ratio_sum <= 0:
            equal = 1.0 / max(len(scenes), 1)
            ratios = [equal] * len(scenes)
        else:
            ratios = [r / ratio_sum for r in ratios]
        return [r * total_duration_seconds for r in ratios]

    def _fit_clip_to_duration(self, clip, target_duration: float):
        target_duration = max(target_duration, 1.0)
        if clip.duration > target_duration + 0.05:
            return clip.subclipped(0, target_duration)
        return clip.with_duration(target_duration)

    def _create_caption_image(self, caption: str) -> Path:
        """상단 타이틀용 이미지 생성 (Pillow 네이티브 C++ stroke 적용 및 캔버스 높이 크롭 최적화)"""
        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), caption, font=self.font_caption, stroke_width=3)
        
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        pad_y = 10
        img_w = SHORTS_SIZE[0]
        img_h = text_h + (pad_y * 2)
        
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        x = (img_w - text_w) / 2
        y = pad_y - bbox[1]
        
        draw.text(
            (x, y),
            caption,
            fill=(255, 223, 0, 255),
            font=self.font_caption,
            stroke_width=3,
            stroke_fill=(0, 0, 0, 255)
        )
        
        filepath = self.temp_dir / f"{uuid.uuid4()}_cap.png"
        img.save(filepath, "PNG")
        return filepath

    def _create_narration_image(self, narration: str) -> Path:
        """하단 내레이션용 이미지 생성 (줄바꿈, Pillow 네이티브 C++ stroke 및 캔버스 높이 크롭 최적화)"""
        max_w = SHORTS_SIZE[0] - 160
        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        
        words = narration.split(" ")
        lines = []
        curr_line = []
        for word in words:
            test_line = " ".join(curr_line + [word])
            line_w = dummy_draw.textlength(test_line, font=self.font_narration)
            if line_w <= max_w:
                curr_line.append(word)
            else:
                if curr_line:
                    lines.append(" ".join(curr_line))
                curr_line = [word]
        if curr_line:
            lines.append(" ".join(curr_line))
            
        line_height = 55
        total_h = len(lines) * line_height
        
        img_w = SHORTS_SIZE[0]
        img_h = total_h + 20
        
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=self.font_narration, stroke_width=2)
            line_w = line_bbox[2] - line_bbox[0]
            x = (img_w - line_w) / 2
            y = 10 + (i * line_height) - line_bbox[1]
            
            draw.text(
                (x, y),
                line,
                fill=(255, 255, 255, 255),
                font=self.font_narration,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255)
            )
            
        filepath = self.temp_dir / f"{uuid.uuid4()}_nar.png"
        img.save(filepath, "PNG")
        return filepath

    def _apply_zoom_motion(self, clip, target_duration: float):
        """정적 이미지에 서서히 줌인(Ken Burns)되는 동적 효과 적용 (OpenCV/Pillow 이중 지원)"""
        w, h = SHORTS_SIZE
        # 1. 먼저 이미지를 15% 더 큰 크기인 1.15배율로 확대
        enlarged_clip = clip.resized(new_size=(int(w * 1.15), int(h * 1.15)))
        
        # 2. t에 따라 크롭 영역의 중심좌표를 계산하여 1080x1920 크기로 크롭
        def crop_frame(get_frame, t):
            frame = get_frame(t)
            fh, fw = frame.shape[:2]
            
            # 줌 배율: t=0일 때 1.0배 -> t=target_duration일 때 1.15배 (줌인 효과)
            scale = 1.0 + 0.15 * (t / target_duration)
            
            crop_w = int(w * (1.15 / scale))
            crop_h = int(h * (1.15 / scale))
            
            x1 = (fw - crop_w) // 2
            y1 = (fh - crop_h) // 2
            x2 = x1 + crop_w
            y2 = y1 + crop_h
            
            cropped = frame[y1:y2, x1:x2]
            
            try:
                import cv2
                return cv2.resize(cropped, (w, h))
            except ImportError:
                from PIL import Image as PILImage
                pil_img = PILImage.fromarray(cropped)
                resized_pil = pil_img.resize((w, h), PILImage.Resampling.BILINEAR)
                return np.array(resized_pil)
                
        return enlarged_clip.transform(crop_frame, apply_to="mask")

    def _build_scene_clip(self, scene: dict, target_duration: float):
        media_path = None
        is_video = False
        scene_files = []

        video_data = scene.get("video_data_render") or ""
        image_data = scene.get("image_data_preview") or ""

        if video_data and "MOCK" not in video_data and "FALLBACK" not in video_data:
            media_path = self.decode_base64_to_file(video_data, ".mp4")
            is_video = bool(media_path and media_path.exists())
        if not is_video and image_data and "MOCK" not in image_data:
            media_path = self.decode_base64_to_file(image_data, ".png")
            is_video = False

        if media_path:
            scene_files.append(media_path)

        tts_path = None
        narration = scene.get("narration", "")
        if narration:
            tts_path = self.generate_tts(narration)

        if media_path and media_path.exists():
            if is_video:
                base_clip = VideoFileClip(str(media_path))
            else:
                img_clip = ImageClip(str(media_path)).with_duration(target_duration)
                base_clip = self._apply_zoom_motion(img_clip, target_duration)
        else:
            base_clip = ColorClip(
                size=SHORTS_SIZE, color=(18, 18, 28), duration=target_duration
            )

        base_clip = self._fit_clip_to_duration(base_clip, target_duration)

        # 자막(Subtitle/Caption) 오버레이 처리 (상/하단 각각 경량 캔버스 정밀 합성)
        caption = scene.get("caption", "")
        overlay_clips = []
        
        if caption:
            try:
                cap_path = self._create_caption_image(caption)
                scene_files.append(cap_path)
                cap_clip = (
                    ImageClip(str(cap_path))
                    .with_duration(target_duration)
                    .with_position(("center", 300))
                )
                overlay_clips.append(cap_clip)
            except Exception as e:
                print(f"상단 자막 생성 실패: {e}")
                
        if narration:
            try:
                nar_path = self._create_narration_image(narration)
                scene_files.append(nar_path)
                nar_clip = (
                    ImageClip(str(nar_path))
                    .with_duration(target_duration)
                    .with_position(("center", 1450))
                )
                overlay_clips.append(nar_clip)
            except Exception as e:
                print(f"하단 자막 생성 실패: {e}")
                
        if overlay_clips:
            base_clip = CompositeVideoClip([base_clip] + overlay_clips)

        if tts_path and tts_path.exists():
            try:
                audio_clip = AudioFileClip(str(tts_path))
                if audio_clip.duration > target_duration:
                    audio_clip = audio_clip.subclipped(0, target_duration)
                base_clip = base_clip.with_audio(audio_clip)
            except Exception as e:
                print(f"TTS 오디오 병합 에러: {e}")

        return base_clip, tts_path, scene_files

    def assemble(
        self,
        bgm_b64: str,
        scenes: list,
        total_duration_seconds: int = 30,
    ) -> str:
        """장면들을 이어 붙여 total_duration_seconds 길이의 9:16 mp4를 생성합니다."""
        if not scenes:
            raise ValueError("조립할 장면이 없습니다.")

        total_duration_seconds = max(int(total_duration_seconds), 10)
        target_durations = self._scene_target_durations(scenes, total_duration_seconds)

        clips = []
        tts_files = []
        media_files = []

        bgm_path = None
        if bgm_b64 and "MOCK" not in bgm_b64:
            bgm_path = self.decode_base64_to_file(bgm_b64, ".mp3")

        try:
            for scene, target_dur in zip(scenes, target_durations):
                clip, tts_path, scene_files = self._build_scene_clip(scene, target_dur)
                clips.append(clip)
                if tts_path:
                    tts_files.append(tts_path)
                for f in scene_files:
                    if f:
                        media_files.append(f)

            final_clip = concatenate_videoclips(clips, method="compose")

            if final_clip.duration > total_duration_seconds + 0.1:
                final_clip = final_clip.subclipped(0, total_duration_seconds)
            elif final_clip.duration < total_duration_seconds - 0.1:
                pad = ColorClip(
                    size=SHORTS_SIZE,
                    color=(0, 0, 0),
                    duration=total_duration_seconds - final_clip.duration,
                )
                final_clip = concatenate_videoclips([final_clip, pad], method="compose")

            if bgm_path and bgm_path.exists():
                try:
                    bgm_clip = AudioFileClip(str(bgm_path)).with_volume_scaled(0.25)
                    if bgm_clip.duration > final_clip.duration:
                        bgm_clip = bgm_clip.subclipped(0, final_clip.duration)
                    elif bgm_clip.duration < final_clip.duration:
                        bgm_clip = bgm_clip.with_duration(final_clip.duration)

                    if final_clip.audio:
                        final_clip = final_clip.with_audio(
                            CompositeAudioClip([final_clip.audio, bgm_clip])
                        )
                    else:
                        final_clip = final_clip.with_audio(bgm_clip)
                except Exception as e:
                    print(f"BGM 병합 에러: {e}")

            output_filename = f"final_{uuid.uuid4().hex[:8]}.mp4"
            output_filepath = OUTPUT_DIR / output_filename

            final_clip.write_videofile(
                str(output_filepath),
                fps=SHORTS_FPS,
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

            actual_duration = round(final_clip.duration, 1)
            final_clip.close()
            for c in clips:
                c.close()

            print(f"[Assembler] 완료: {output_filename} ({actual_duration}s)")
            return f"/static/outputs/{output_filename}"

        finally:
            for f in tts_files + media_files:
                try:
                    if f and f.exists():
                        f.unlink()
                except Exception:
                    pass
            if bgm_path and bgm_path.exists():
                try:
                    bgm_path.unlink()
                except Exception:
                    pass
