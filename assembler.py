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
from gtts import gTTS

OUTPUT_DIR = Path(__file__).parent / "static" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHORTS_SIZE = (1080, 1920)
SHORTS_FPS = 24


class VideoAssembler:
    def __init__(self):
        self.temp_dir = OUTPUT_DIR / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

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

    def _build_scene_clip(self, scene: dict, target_duration: float):
        media_path = None
        is_video = False

        video_data = scene.get("video_data_render") or ""
        image_data = scene.get("image_data_preview") or ""

        if video_data and "MOCK" not in video_data and "FALLBACK" not in video_data:
            media_path = self.decode_base64_to_file(video_data, ".mp4")
            is_video = bool(media_path and media_path.exists())
        if not is_video and image_data and "MOCK" not in image_data:
            media_path = self.decode_base64_to_file(image_data, ".png")
            is_video = False

        tts_path = None
        narration = scene.get("narration", "")
        if narration:
            tts_path = self.generate_tts(narration)

        if media_path and media_path.exists():
            base_clip = (
                VideoFileClip(str(media_path))
                if is_video
                else ImageClip(str(media_path))
            )
        else:
            base_clip = ColorClip(
                size=SHORTS_SIZE, color=(18, 18, 28), duration=target_duration
            )

        base_clip = self._fit_clip_to_duration(base_clip, target_duration)

        if tts_path and tts_path.exists():
            try:
                audio_clip = AudioFileClip(str(tts_path))
                if audio_clip.duration > target_duration:
                    audio_clip = audio_clip.subclipped(0, target_duration)
                base_clip = base_clip.with_audio(audio_clip)
            except Exception as e:
                print(f"TTS 오디오 병합 에러: {e}")

        return base_clip, tts_path, media_path

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
                clip, tts_path, media_path = self._build_scene_clip(scene, target_dur)
                clips.append(clip)
                if tts_path:
                    tts_files.append(tts_path)
                if media_path:
                    media_files.append(media_path)

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
