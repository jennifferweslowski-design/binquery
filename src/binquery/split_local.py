"""Time-grid split of one local video via ffmpeg segment.

Not highlight detection. Not silence cuts. Does not index or query.
Does not unpack archives. Does not call a cloud API.
Stdlib + local ffmpeg only; does not import OpenCLIP.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VIDEO_EXT = {".mov", ".mp4", ".mkv", ".m4v", ".avi", ".webm"}
SECONDS_DEFAULT = 8
SECONDS_MIN = 4
SECONDS_MAX = 60


class SplitError(RuntimeError):
    """Split cannot run. Do not pretend."""


def clamp_seconds(n: int) -> int:
    return max(SECONDS_MIN, min(SECONDS_MAX, int(n)))


def default_out_dir(src: Path) -> Path:
    """Clips go next to the user's file, never into the program tree."""
    return Path(src).expanduser().resolve().parent / "split-out"


def program_root() -> Path:
    here = Path(__file__).resolve().parent
    if here.name == "src":
        return here.parent
    return here


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def reject_program_tree(out: Path) -> None:
    root = program_root()
    if _is_under(out, root):
        raise SplitError(
            f"refusing to write clips into the program tree ({root}). "
            "Pass --out outside this repo, or keep the default next to the input file."
        )


def which_ffmpeg() -> tuple[str, str]:
    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    if not ff or not fp:
        raise SplitError("ffmpeg/ffprobe not on PATH. Will not unpack or call a cloud API.")
    return ff, fp


def probe_clip(ffprobe: str, src: Path) -> dict[str, Any]:
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration,size",
        "-of", "json",
        str(src),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SplitError(f"ffprobe failed: {src.name}: {(r.stderr or '').strip()[:200]}")
    data = json.loads(r.stdout or "{}")
    fmt = data.get("format") or {}
    streams = data.get("streams") or [{}]
    st = streams[0] if streams else {}
    dur = float(fmt.get("duration") or 0.0)
    return {
        "duration_sec": dur,
        "width": int(st.get("width") or 0),
        "height": int(st.get("height") or 0),
    }


def _has_audio(ffprobe: str, src: Path) -> bool:
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(src),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and "audio" in (r.stdout or "").lower()


def _list_parts(out: Path, prefix: str, suffix: str) -> list[Path]:
    found: list[Path] = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name.startswith(prefix) and p.suffix.lower() == suffix.lower():
            found.append(p)
    return found


def run_split(
    input_path: Path,
    out_dir: Path | None = None,
    seconds: int = SECONDS_DEFAULT,
    reencode: bool = False,
) -> dict[str, Any]:
    src = Path(input_path).expanduser().resolve()
    if not src.is_file():
        raise SplitError(f"input file missing: {src}")
    if src.suffix.lower() not in VIDEO_EXT:
        raise SplitError(f"not a video file: {src.name} (mov/mp4/mkv/m4v/avi/webm)")

    seconds = clamp_seconds(seconds)
    out = Path(out_dir).expanduser().resolve() if out_dir else default_out_dir(src)
    reject_program_tree(out)
    if out.exists():
        if not out.is_dir():
            raise SplitError(f"out is not a directory: {out}")
        if any(out.iterdir()):
            raise SplitError(f"out is not empty: {out}")
    else:
        out.mkdir(parents=True, exist_ok=True)

    ffmpeg, ffprobe = which_ffmpeg()

    suffix = ".mp4" if reencode else src.suffix
    pattern = out / f"part%03d{suffix}"
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    if reencode:
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-force_key_frames", f"expr:gte(t,n_forced*{seconds})",
        ]
        if _has_audio(ffprobe, src):
            cmd += ["-c:a", "aac"]
        else:
            cmd += ["-an"]
    else:
        cmd += ["-c", "copy"]
    cmd += [
        "-f", "segment",
        "-segment_time", str(seconds),
        "-reset_timestamps", "1",
        str(pattern),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = (r.stderr or "ffmpeg failed").strip().splitlines()
        raise SplitError(f"ffmpeg split failed: {err[-1] if err else 'ffmpeg failed'}")

    parts = _list_parts(out, "part", suffix)
    if not parts:
        raise SplitError(f"ffmpeg wrote no clips into {out}")

    clips: list[dict[str, Any]] = []
    for p in parts:
        meta = probe_clip(ffprobe, p)
        clips.append(
            {
                "path": str(p),
                "duration_sec": round(float(meta["duration_sec"]), 4),
            }
        )

    mode = "reencode" if reencode else "copy"
    return {
        "input": str(src),
        "out": str(out),
        "seconds": seconds,
        "mode": mode,
        "clip_count": len(clips),
        "clips": clips,
        "note": (
            "Time-grid ffmpeg segment. Not highlights. "
            + (
                "Reencode (libx264+aac) for nearer-exact duration."
                if reencode
                else "Default -c copy cuts on keyframes, so duration is not exact."
            )
        ),
    }
