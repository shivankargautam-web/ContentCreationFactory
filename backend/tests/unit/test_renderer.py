import shutil
from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.agent_outputs import StoryboardScene
from app.services.media.captions import build_srt
from app.services.media.renderer import FFmpegVideoRenderer, RenderInput

SCENES = [
    StoryboardScene(
        index=0,
        narration="Kafka in 10 seconds",
        on_screen_text="Kafka",
        visual_prompt="x",
        duration_seconds=1.5,
        background_color="#112233",
    ),
    StoryboardScene(
        index=1,
        narration="Partitions scale reads",
        on_screen_text="Partitions",
        visual_prompt="y",
        duration_seconds=1.5,
    ),
]


def test_build_command_structure(tmp_path: Path) -> None:
    renderer = FFmpegVideoRenderer(Settings())
    cmd = renderer.build_command(
        RenderInput(scenes=SCENES, captions_srt="", workdir=tmp_path), tmp_path / "o.mp4"
    )
    joined = " ".join(cmd)
    assert "color=c=0x112233:s=1080x1920" in joined
    assert "anullsrc" in joined
    assert "concat=n=2:v=1:a=0" in joined
    assert "subtitles=" in joined
    assert cmd[-1].endswith("o.mp4")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
async def test_real_render(tmp_path: Path) -> None:
    renderer = FFmpegVideoRenderer(Settings(video_width=360, video_height=640))
    out = await renderer.render(RenderInput(scenes=SCENES, captions_srt=build_srt(SCENES), workdir=tmp_path))
    assert out.video_path.exists()
    assert 2.5 <= out.duration_seconds <= 3.5
