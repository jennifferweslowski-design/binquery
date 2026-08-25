"""Generate synthetic footage and exercise the complete local workflow."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .index_box import IndexError_, run_index
from .query import MissingIndex, doctor_index, dump_json, run_query
from .split_local import SplitError, run_split, which_ffmpeg


class DemoError(RuntimeError):
    """The reproducible local demo could not complete."""


def _prepare_root(out_dir: Path) -> Path:
    root = Path(out_dir).expanduser().resolve()
    if root.exists():
        if not root.is_dir():
            raise DemoError(f"demo output is not a directory: {root}")
        if any(root.iterdir()):
            raise DemoError(f"demo output is not empty: {root}")
    else:
        root.mkdir(parents=True)
    return root


def _generate_long_video(dest: Path) -> None:
    ffmpeg, _ = which_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=30:size=320x240:rate=25",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and dest.is_file() and dest.stat().st_size > 0:
        return
    lines = (result.stderr or "ffmpeg failed").strip().splitlines()
    raise DemoError(
        f"could not generate synthetic video: {lines[-1] if lines else 'ffmpeg failed'}"
    )


def run_demo(
    out_dir: Path,
    *,
    intent: str = "color test pattern",
    limit: int = 8,
) -> dict[str, Any]:
    """Run lavfi -> split -> index -> doctor -> query under a new/empty directory."""
    root = _prepare_root(out_dir)
    long_video = root / "synthetic-long.mp4"
    clips_dir = root / "clips"
    box_dir = root / "box"
    query_path = root / "query.json"

    try:
        _generate_long_video(long_video)
        split = run_split(long_video, clips_dir, seconds=8)
        if int(split["clip_count"]) < 2:
            raise DemoError(
                f"expected at least 2 synthetic clips, got {split['clip_count']}"
            )
        index = run_index(clips_dir, box_dir)
        doctor = doctor_index(box_dir)
        if not doctor["can_query"]:
            missing = ", ".join(str(path) for path in doctor.get("missing") or [])
            raise DemoError(f"demo index cannot be queried; missing: {missing or 'unknown'}")
        query = run_query(box_dir, intent, limit=limit)
        dump_json(query_path, query)
    except (SplitError, IndexError_, MissingIndex, FileNotFoundError) as exc:
        raise DemoError(str(exc)) from exc

    return {
        "root": str(root),
        "long_video": str(long_video),
        "clips_dir": str(clips_dir),
        "box_dir": str(box_dir),
        "query_path": str(query_path),
        "split": split,
        "index": index,
        "doctor": doctor,
        "query": query,
    }
