import tempfile
from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import ContentState
from app.schemas.agent_outputs import Storyboard
from app.services.integrations.llm import LLMClient
from app.services.integrations.storage import ObjectStorage
from app.services.integrations.tts import TextToSpeech
from app.services.media.captions import build_srt, scale_scenes
from app.services.media.renderer import RenderInput, VideoRenderer

SYSTEM = (
    "You are a short-form video director. Convert the script into a vertical 9:16 storyboard. Each scene "
    "maps to one spoken beat: narration (exact words), on_screen_text (max 8 words, bold claim), a vivid "
    "visual_prompt for an illustrator, duration_seconds (2-8s), and a dark background_color hex."
)


class VideoAgent(BaseAgent):
    """Storyboard -> scene visuals -> voiceover -> captions -> rendered MP4 in object storage."""

    name = "video"

    def __init__(
        self, llm: LLMClient, tts: TextToSpeech, renderer: VideoRenderer, storage: ObjectStorage
    ) -> None:
        super().__init__()
        self._llm = llm
        self._tts = tts
        self._renderer = renderer
        self._storage = storage

    async def run(self, state: ContentState) -> dict[str, Any]:
        script = state.get("script") or {}
        storyboard = await self._llm.complete_json(
            system=SYSTEM,
            prompt=f"Hook: {script.get('hook')}\nBeats: {script.get('body')}\nCTA: {script.get('cta')}",
            schema=Storyboard,
            context=self.context(state),
        )
        scenes = storyboard.scenes
        prefix = f"campaigns/{state['campaign_id']}/items/{state['content_item_id']}"

        with tempfile.TemporaryDirectory(prefix="acf-render-") as tmp:
            workdir = Path(tmp)
            audio_path: Path | None = None
            audio_key: str | None = None
            narration = " ".join(s.narration for s in scenes)
            audio = await self._tts.synthesize(narration)
            if audio:
                audio_path = workdir / "voiceover.mp3"
                audio_path.write_bytes(audio)
                scenes = scale_scenes(scenes, await self._renderer.probe_duration(audio_path))
                audio_key = await self._storage.put_file(f"{prefix}/voiceover.mp3", audio_path, "audio/mpeg")

            images: dict[int, Path] = {}
            for scene in scenes:
                image = await self._llm.generate_image(scene.visual_prompt)
                if image:
                    images[scene.index] = workdir / f"scene_{scene.index}.png"
                    images[scene.index].write_bytes(image)

            captions = build_srt(scenes)
            output = await self._renderer.render(
                RenderInput(
                    scenes=scenes,
                    captions_srt=captions,
                    workdir=workdir,
                    audio_path=audio_path,
                    scene_images=images,
                )
            )
            video_key = await self._storage.put_file(f"{prefix}/short.mp4", output.video_path, "video/mp4")

        return {
            "video": {
                "storyboard": [s.model_dump() for s in scenes],
                "captions_srt": captions,
                "audio_key": audio_key,
                "video_key": video_key,
                "duration_seconds": output.duration_seconds,
            }
        }
