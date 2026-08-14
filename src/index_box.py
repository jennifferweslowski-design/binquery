"""Build a local box index: ffprobe + 3 stills + OpenCLIP vectors.

No cloud vision API. Does not unpack archives. Does not write footage into
the program tree.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from clip_local import DEVICE, MODEL_NAME, PRETRAINED, LocalCLIP
from motion_local import clip_motion_row

TZ8 = timezone(timedelta(hours=8))
VIDEO_EXT = {".mov", ".mp4", ".mkv", ".m4v", ".avi", ".webm"}
OVERLAP_EPS = 0.05
LABELS = ("a", "b", "c")


class IndexError_(RuntimeError):
    """Index cannot run. Do not pretend."""


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def which_ffmpeg() -> tuple[str, str]:
    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    if not ff or not fp:
        raise IndexError_("ffmpeg/ffprobe not on PATH. Will not unpack or call a cloud API.")
    return ff, fp


def list_videos(input_dir: Path) -> list[Path]:
    found: list[Path] = []
    for p in sorted(input_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in VIDEO_EXT:
            found.append(p)
    return found


def unique_times(times: list[float], duration: float) -> list[float]:
    end = max(0.0, duration - 0.04)
    cleaned: list[float] = []
    for t in times:
        t = min(max(0.0, t), end)
        if any(abs(t - u) < OVERLAP_EPS for u in cleaned):
            continue
        cleaned.append(round(t, 4))
    return cleaned


def pick_times(duration: float) -> list[float]:
    if duration < 2.0:
        return unique_times([0.0, duration / 2.0, duration], duration)
    return unique_times([1.0, duration / 2.0, duration - 1.0], duration)


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
        raise IndexError_(f"ffprobe failed: {src.name}: {(r.stderr or '').strip()[:200]}")
    data = json.loads(r.stdout or "{}")
    fmt = data.get("format") or {}
    streams = data.get("streams") or [{}]
    st = streams[0] if streams else {}
    dur = float(fmt.get("duration") or 0.0)
    size = int(fmt.get("size") or src.stat().st_size)
    return {
        "duration_sec": dur,
        "width": int(st.get("width") or 0),
        "height": int(st.get("height") or 0),
        "size": size,
    }


def extract_one(ffmpeg: str, src: Path, t: float, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = "scale='if(gte(iw,ih),640,-2)':'if(gte(iw,ih),-2,640)'"
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{t:.4f}", "-i", str(src),
        "-frames:v", "1", "-vf", vf, "-q:v", "3", str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and dest.is_file() and dest.stat().st_size > 0:
        return
    cmd2 = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-ss", f"{t:.4f}",
        "-frames:v", "1", "-vf", vf, "-q:v", "3", str(dest),
    ]
    r2 = subprocess.run(cmd2, capture_output=True, text=True)
    if r2.returncode == 0 and dest.is_file() and dest.stat().st_size > 0:
        return
    err = (r2.stderr or r.stderr or "ffmpeg failed").strip().splitlines()
    raise IndexError_(f"frame extract failed {src.name} @{t}: {err[-1] if err else 'ffmpeg failed'}")


PERSON_TXT = "a person visible in the frame"
EMPTY_TXT = "empty landscape, no people"


def person_clip_rows(
    model: LocalCLIP,
    vecs: np.ndarray,
    frame_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """person_clip = max over frames of cos(person) - cos(empty). Same field empty gates read."""
    tvecs = model.encode_texts([PERSON_TXT, EMPTY_TXT])
    person_v, empty_v = tvecs[0], tvecs[1]
    deltas = (vecs @ person_v) - (vecs @ empty_v)
    by: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(frame_rows):
        fn = str(row["filename"])
        d = float(deltas[i])
        rec = by.get(fn)
        if rec is None or d > rec["person_clip"]:
            by[fn] = {
                "path": fn,
                "filename": fn,
                "person_clip": round(d, 4),
                "duration_sec": row.get("duration_sec"),
                "best_frame": row.get("frame"),
                "best_time_sec": row.get("time_sec"),
            }
    return [by[k] for k in sorted(by)]


def run_index(input_dir: Path, box_dir: Path) -> dict[str, Any]:
    input_dir = Path(input_dir).expanduser().resolve()
    box_dir = Path(box_dir).expanduser().resolve()
    if not input_dir.is_dir():
        raise IndexError_(f"input folder missing: {input_dir}")
    videos = list_videos(input_dir)
    if not videos:
        raise IndexError_(f"no video files under {input_dir} (mov/mp4/mkv/m4v/avi/webm)")

    ffmpeg, ffprobe = which_ffmpeg()
    index_dir = box_dir / "index"
    frames_dir = index_dir / "frames"
    index_dir.mkdir(parents=True, exist_ok=True)

    clips: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    frame_paths: list[Path] = []

    for src in videos:
        rel = src.relative_to(input_dir).as_posix()
        folder = str(Path(rel).parent)
        if folder == ".":
            folder = ""
        meta = probe_clip(ffprobe, src)
        times = pick_times(float(meta["duration_sec"]))
        stem = Path(rel).stem
        rec = {
            "filename": rel,
            "folder": folder,
            "duration_sec": round(float(meta["duration_sec"]), 4),
            "width": meta["width"],
            "height": meta["height"],
            "size": meta["size"],
        }
        clips.append(rec)
        for i, t in enumerate(times):
            label = LABELS[i] if i < len(LABELS) else str(i)
            rel_frame = f"{folder}/{stem}_{label}.jpg" if folder else f"{stem}_{label}.jpg"
            dest = frames_dir / rel_frame
            extract_one(ffmpeg, src, t, dest)
            frame_rel = f"index/frames/{rel_frame}"
            frame_rows.append(
                {
                    "filename": rel,
                    "frame": frame_rel,
                    "time_sec": float(t),
                    "duration_sec": rec["duration_sec"],
                }
            )
            frame_paths.append(dest)

    print(f"probed {len(clips)} clips, {len(frame_rows)} stills, encoding {MODEL_NAME}", flush=True)
    clip = LocalCLIP()
    vecs = clip.encode_images(frame_paths, batch=16)
    if vecs.shape[0] != len(frame_rows):
        raise IndexError_(f"vecs {vecs.shape} vs frames {len(frame_rows)}")
    for i, row in enumerate(frame_rows):
        row["npy_index"] = i
        row["vector_index"] = i

    npy_path = index_dir / "clip_vectors.npy"
    np.save(npy_path, vecs)

    person_rows = person_clip_rows(clip, vecs, frame_rows)
    generated = now_iso()
    hard = {
        "generated_at": generated,
        "model": MODEL_NAME,
        "pretrained": PRETRAINED,
        "device": DEVICE,
        "person_prompts": {
            "person": PERSON_TXT,
            "empty": EMPTY_TXT,
        },
        "fields": {
            "person_clip": (
                "max over stored frame vectors of "
                "cosine(a person visible in the frame) - "
                "cosine(empty landscape, no people). "
                "Low/negative = no people."
            ),
            "path": "relative path under the input folder",
        },
        "clip_count": len(person_rows),
        "clips": person_rows,
        "note": "Written by binquery index. Same person_clip field empty gates already read. Not motion.",
    }
    (index_dir / "empty_hard.json").write_text(
        json.dumps(hard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    mech = {
        "generated_at": generated,
        "count": len(clips),
        "clip_count": len(clips),
        "fields": {
            "filename": "relative path under the input folder",
            "folder": "parent folder or empty",
            "duration_sec": "ffprobe format.duration",
            "width": "pixels",
            "height": "pixels",
            "size": "bytes",
        },
        "clips": clips,
    }
    clip_json = {
        "generated_at": generated,
        "model": MODEL_NAME,
        "pretrained": PRETRAINED,
        "package": "open_clip_torch",
        "device": DEVICE,
        "dim": int(vecs.shape[1]) if vecs.ndim == 2 and vecs.size else 512,
        "frame_count": len(frame_rows),
        "clip_count": len(clips),
        "vectors_file": "index/clip_vectors.npy",
        "note": "Local CPU embeddings. Query does not call a cloud API.",
        "frames": frame_rows,
    }
    (index_dir / "mechanical.json").write_text(
        json.dumps(mech, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (index_dir / "clip.json").write_text(
        json.dumps(clip_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    person_by = {r["filename"]: r.get("person_clip") for r in person_rows}
    frames_by: dict[str, list[Path]] = {}
    for row, dest in zip(frame_rows, frame_paths):
        frames_by.setdefault(str(row["filename"]), []).append(dest)
    motion_clips = []
    for rec in clips:
        fn = rec["filename"]
        motion_clips.append(
            clip_motion_row(
                fn,
                rec.get("folder") or "",
                float(rec["duration_sec"]),
                frames_by.get(fn) or [],
                person_by.get(fn),
            )
        )
    motion_payload = {
        "generated_at": generated,
        "clip_count": len(motion_clips),
        "model": MODEL_NAME,
        "pretrained": PRETRAINED,
        "device": DEVICE,
        "working_resolution": "long_edge_320",
        "still_px": 3.0,
        "fields": {
            "filename": "relative path under the input folder",
            "coarse_3frame": "a→b and b→c on index/frames. fd_mag + phaseCorrelate. lock / pan_candidate / handheld_candidate.",
            "dense": "same a/b/c stills. mag / horiz_ratio / dir_consistency / shake.",
            "person_clip": "copied from empty_hard.json (cos person - cos empty).",
            "motion_label": "lock | pan | handheld | moving | unknown",
        },
        "note": "Written by binquery index. Same motion.json fields. Not a new format. Not a pass.",
        "clips": motion_clips,
    }
    (index_dir / "motion.json").write_text(
        json.dumps(motion_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "box": str(box_dir),
        "input": str(input_dir),
        "clip_count": len(clips),
        "frame_count": len(frame_rows),
        "shape": [int(x) for x in vecs.shape],
        "wrote": [
            "index/mechanical.json",
            "index/clip.json",
            "index/clip_vectors.npy",
            "index/empty_hard.json",
            "index/motion.json",
        ],
        "person_clips": person_rows,
        "motion_labels": {c["filename"]: c["motion_label"] for c in motion_clips},
    }
