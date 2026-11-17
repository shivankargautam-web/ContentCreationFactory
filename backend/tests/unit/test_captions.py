from app.schemas.agent_outputs import StoryboardScene
from app.services.media.captions import build_srt, scale_scenes


def scene(i: int, text: str, dur: float) -> StoryboardScene:
    return StoryboardScene(
        index=i, narration=text, on_screen_text=text[:20], visual_prompt="x", duration_seconds=dur
    )


def test_build_srt_timing_and_format() -> None:
    srt = build_srt([scene(0, "one two three four five six seven", 4.0), scene(1, "hello world", 2.0)])
    blocks = srt.strip().split("\n\n")
    assert len(blocks) == 3
    assert blocks[0].startswith("1\n00:00:00,000 --> 00:00:02,000")
    assert "00:00:04,000 --> 00:00:06,000" in blocks[2]


def test_scale_scenes_matches_target() -> None:
    scaled = scale_scenes([scene(0, "a", 2.0), scene(1, "b", 6.0)], 16.0)
    assert [s.duration_seconds for s in scaled] == [4.0, 12.0]
