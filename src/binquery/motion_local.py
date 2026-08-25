"""Local camera-motion from stills. Same motion.json fields query already reads.

phaseCorrelate + frame-diff on a/b/c. No cloud, no new model.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

WORK_LONG_EDGE = 320
STILL_PX = 3.0
RESP_MIN = 0.035


def _resize_gray(bgr: np.ndarray, long_edge: int = WORK_LONG_EDGE) -> np.ndarray:
    h, w = bgr.shape[:2]
    if max(h, w) <= long_edge:
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    scale = long_edge / float(max(h, w))
    small = cv2.resize(
        bgr,
        (int(round(w * scale)), int(round(h * scale))),
        interpolation=cv2.INTER_AREA,
    )
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def load_gray(path: Path) -> np.ndarray | None:
    im = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if im is None:
        return None
    return _resize_gray(im)


def pair_motion(g1: np.ndarray, g2: np.ndarray) -> dict:
    f1 = g1.astype(np.float32)
    f2 = g2.astype(np.float32)
    win = cv2.createHanningWindow((g1.shape[1], g1.shape[0]), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(f1, f2, win)
    dx = float(dx)
    dy = float(dy)
    mag = float(math.hypot(dx, dy))
    fd = float(np.mean(np.abs(f2 - f1)) / 255.0)
    resp = float(resp)
    w = float(g1.shape[1])
    reliable = bool(resp >= RESP_MIN)
    if mag < STILL_PX:
        direction = "still"
    elif not reliable:
        direction = "chaotic"
    else:
        ax, ay = abs(dx), abs(dy)
        if ax >= 1.6 * ay:
            direction = "horizontal"
        elif ay >= 1.6 * ax:
            direction = "vertical"
        else:
            direction = "chaotic"
    return {
        "fd_mag": round(fd, 6),
        "shift_mag": round(mag, 4),
        "shift_norm": round(mag / max(w, 1.0), 6),
        "dx": round(dx, 4),
        "dy": round(dy, 4),
        "dir": direction,
        "phase_resp": round(resp, 6),
        "reliable": reliable,
        "scene_change": bool((not reliable) and fd >= 0.10),
    }


def coarse_from_abc(paths: list[Path]) -> dict:
    rec: dict[str, Any] = {
        "source": "index/frames a/b/c",
        "n_frames": 0,
        "ab": None,
        "bc": None,
        "lock": False,
        "pan_candidate": False,
        "handheld_candidate": False,
        "scene_changed": False,
    }
    grays: list[np.ndarray] = []
    for p in paths:
        g = load_gray(p) if p.is_file() else None
        if g is None:
            rec["error"] = f"missing {p.name}"
            return rec
        grays.append(g)
    rec["n_frames"] = len(grays)
    if len(grays) < 2:
        return rec
    rec["ab"] = pair_motion(grays[0], grays[1])
    rec["bc"] = pair_motion(grays[1], grays[2]) if len(grays) >= 3 else None
    ab = rec["ab"]
    bc = rec["bc"] or {
        "shift_mag": 0.0,
        "dir": "still",
        "reliable": True,
        "scene_change": False,
        "fd_mag": 0.0,
    }
    rec["scene_changed"] = bool(ab.get("scene_change") or bc.get("scene_change"))
    still_ab = ab["shift_mag"] < STILL_PX
    still_bc = bc["shift_mag"] < STILL_PX
    rec["lock"] = bool(still_ab and still_bc)
    dirs = [ab["dir"], bc["dir"]]
    rec["pan_candidate"] = bool(
        (dirs.count("horizontal") >= 1)
        and all(d in ("horizontal", "still") for d in dirs)
        and (ab.get("reliable") or still_ab)
        and (bc.get("reliable") or still_bc)
    )
    move_ab = (not still_ab) and ab.get("reliable")
    move_bc = (not still_bc) and bc.get("reliable")
    rec["handheld_candidate"] = bool(move_ab and move_bc and ab["dir"] != bc["dir"])
    return rec


def dense_from_images(paths: list[Path], source: str) -> dict:
    rec: dict[str, Any] = {
        "source": source,
        "n_frames": 0,
        "n_pairs": 0,
        "mag": 0.0,
        "horiz_ratio": 0.0,
        "dir_consistency": 0.0,
        "shake": 0.0,
        "mean_fd": 0.0,
        "reliable_pairs": 0,
    }
    grays: list[np.ndarray] = []
    for p in paths:
        g = load_gray(p)
        if g is not None:
            grays.append(g)
    rec["n_frames"] = len(grays)
    if len(grays) < 2:
        rec["error"] = "need >=2 frames"
        return rec
    pairs = [pair_motion(grays[i], grays[i + 1]) for i in range(len(grays) - 1)]
    rec["n_pairs"] = len(pairs)
    rec["mean_fd"] = round(float(np.mean([p["fd_mag"] for p in pairs])), 6)
    mags = np.array([p["shift_mag"] for p in pairs], dtype=np.float64)
    rec["mag"] = round(float(np.median(mags)), 4)
    good = [p for p in pairs if p["shift_mag"] >= STILL_PX and p["reliable"]]
    rec["reliable_pairs"] = len(good)
    if not good:
        rec["horiz_ratio"] = 0.0
        rec["dir_consistency"] = 1.0
        rec["shake"] = 0.0
        return rec
    hr = [abs(p["dx"]) / (p["shift_mag"] + 1e-6) for p in good]
    rec["horiz_ratio"] = round(float(np.mean(hr)), 4)
    angs = [math.atan2(p["dy"], p["dx"]) for p in good]
    ux = float(np.mean([math.cos(a) for a in angs]))
    uy = float(np.mean([math.sin(a) for a in angs]))
    rec["dir_consistency"] = round(float(math.hypot(ux, uy)), 4)
    mean_ang = math.atan2(uy, ux)
    mean_mag = float(np.mean([p["shift_mag"] for p in good]))
    perp = [abs(math.sin(a - mean_ang)) * p["shift_mag"] for a, p in zip(angs, good)]
    rec["shake"] = round(float(np.mean(perp)) / (mean_mag + 1e-6), 4)
    return rec


def motion_label(coarse: dict, dense: dict) -> str:
    mag = float(dense.get("mag") or 0.0)
    hr = float(dense.get("horiz_ratio") or 0.0)
    dc = float(dense.get("dir_consistency") or 0.0)
    sh = float(dense.get("shake") or 0.0)
    rel = int(dense.get("reliable_pairs") or 0)
    n_pairs = int(dense.get("n_pairs") or 0)

    if n_pairs == 0 and coarse.get("ab") is None:
        return "unknown"
    if mag < STILL_PX or rel == 0:
        return "lock"
    if hr >= 0.72 and dc >= 0.68 and sh <= 0.48:
        return "pan"
    if coarse.get("pan_candidate") and hr >= 0.68 and dc >= 0.60 and sh <= 0.40:
        return "pan"
    if rel >= 2 and mag >= STILL_PX:
        if sh >= 0.70 and dc < 0.62:
            return "handheld"
        if dc < 0.48 and sh >= 0.42:
            return "handheld"
        if coarse.get("handheld_candidate") and dc < 0.55 and sh >= 0.38:
            return "handheld"
    if mag >= STILL_PX:
        return "moving"
    return "unknown"


def clip_motion_row(
    filename: str,
    folder: str,
    duration_sec: float,
    frame_paths: list[Path],
    person_clip: float | None,
) -> dict[str, Any]:
    coarse = coarse_from_abc(frame_paths)
    dense = dense_from_images(frame_paths, "index/frames")
    return {
        "filename": filename,
        "folder": folder,
        "duration_sec": duration_sec,
        "coarse_3frame": coarse,
        "dense": dense,
        "person_clip": None if person_clip is None else round(float(person_clip), 6),
        "motion_label": motion_label(coarse, dense),
    }
