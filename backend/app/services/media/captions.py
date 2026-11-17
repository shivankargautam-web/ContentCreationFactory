"""Caption (SRT) generation from storyboard timing."""

import textwrap

from app.schemas.agent_outputs import StoryboardScene


def _fmt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scenes: list[StoryboardScene], max_words_per_cue: int = 6, line_width: int = 22) -> str:
    """Split each scene's narration into short cues distributed evenly across the scene duration."""
    cues: list[str] = []
    cursor = 0.0
    index = 1
    for scene in scenes:
        words = scene.narration.split()
        chunks = [words[i : i + max_words_per_cue] for i in range(0, len(words), max_words_per_cue)] or [[""]]
        per_chunk = scene.duration_seconds / len(chunks)
        for chunk in chunks:
            start, end = cursor, cursor + per_chunk
            text = "\n".join(textwrap.wrap(" ".join(chunk), width=line_width)) or " "
            cues.append(f"{index}\n{_fmt(start)} --> {_fmt(end)}\n{text}\n")
            cursor = end
            index += 1
    return "\n".join(cues)


def scale_scenes(scenes: list[StoryboardScene], target_duration: float) -> list[StoryboardScene]:
    """Stretch/shrink scene durations proportionally so visuals match the voiceover length."""
    total = sum(s.duration_seconds for s in scenes)
    if total <= 0 or target_duration <= 0:
        return scenes
    factor = target_duration / total
    return [s.model_copy(update={"duration_seconds": round(s.duration_seconds * factor, 3)}) for s in scenes]
