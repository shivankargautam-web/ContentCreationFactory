"""FFmpeg-based vertical (9:16) video renderer with burned-in captions and voiceover."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.core.telemetry import get_tracer
from app.schemas.agent_outputs import StoryboardScene

logger = get_logger(__name__)
tracer = get_tracer(__name__)


@dataclass(frozen=True)
class RenderInput:
    scenes: list[StoryboardScene]
    captions_srt: str
    workdir: Path
    audio_path: Path | None = None
    scene_images: dict[int, Path] | None = None


@dataclass(frozen=True)
class RenderOutput:
    video_path: Path
    duration_seconds: float


class VideoRenderer(Protocol):
    async def probe_duration(self, media_path: Path) -> float: ...
    async def render(self, data: RenderInput) -> RenderOutput: ...


class FFmpegVideoRenderer:
    def __init__(self, settings: Settings) -> None:
        self._ffmpeg = settings.ffmpeg_binary
        self._ffprobe = settings.ffmpeg_binary.replace("ffmpeg", "ffprobe")
        self._w = settings.video_width
        self._h = settings.video_height

    async def _run(self, *args: str) -> bytes:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ExternalServiceError(f"{Path(args[0]).name} failed: {stderr.decode()[-800:]}")
        return stdout

    async def probe_duration(self, media_path: Path) -> float:
        out = await self._run(
            self._ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media_path)
        )
        return float(json.loads(out)["format"]["duration"])

    def build_command(self, data: RenderInput, output: Path) -> list[str]:
        total = round(sum(s.duration_seconds for s in data.scenes), 3)
        images = data.scene_images or {}
        args: list[str] = [self._ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
        for scene in data.scenes:
            image = images.get(scene.index)
            if image is not None:
                args += ["-loop", "1", "-t", f"{scene.duration_seconds}", "-i", str(image)]
            else:
                color = scene.background_color.replace("#", "0x")
                args += [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{scene.duration_seconds}",
                    "-i",
                    f"color=c={color}:s={self._w}x{self._h}:r=30",
                ]
        if data.audio_path is not None:
            args += ["-i", str(data.audio_path)]
        else:
            args += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=44100:cl=stereo"]
        audio_index = len(data.scenes)

        srt_path = data.workdir / "captions.srt"
        filters = [
            f"[{i}:v]scale={self._w}:{self._h}:force_original_aspect_ratio=increase,"
            f"crop={self._w}:{self._h},setsar=1,fps=30,format=yuv420p[v{i}]"
            for i in range(len(data.scenes))
        ]
        concat_inputs = "".join(f"[v{i}]" for i in range(len(data.scenes)))
        filters.append(f"{concat_inputs}concat=n={len(data.scenes)}:v=1:a=0[vc]")
        style = (
            "Fontname=DejaVu Sans,Fontsize=16,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=110"
        )
        filters.append(f"[vc]subtitles={srt_path}:force_style='{style}'[vout]")

        args += [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            f"{audio_index}:a",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "44100",
            "-t",
            f"{total}",
            "-movflags",
            "+faststart",
            str(output),
        ]
        return args

    async def render(self, data: RenderInput) -> RenderOutput:
        data.workdir.mkdir(parents=True, exist_ok=True)
        (data.workdir / "captions.srt").write_text(data.captions_srt, encoding="utf-8")
        output = data.workdir / "short.mp4"
        with tracer.start_as_current_span("video.render") as span:
            span.set_attribute("video.scenes", len(data.scenes))
            await self._run(*self.build_command(data, output))
        duration = await self.probe_duration(output)
        logger.info("video.rendered", path=str(output), duration=duration)
        return RenderOutput(video_path=output, duration_seconds=duration)
