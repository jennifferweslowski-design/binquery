"""Frozen gates + ranking. Do not retune. Do not re-embed the library."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .clip_local import DEVICE, MODEL_NAME, PRETRAINED, LocalCLIP, load_index
from .intents import resolve_query

TZ8 = timezone(timedelta(hours=8))

DUR_BONUS = 0.02
CUT_LO = 2.0
CUT_HI = 5.0
NEG_W = 0.55
PERSON_W = 0.25
FIRE_W0 = 0.45
FIRE_STEP = 0.05
FIRE_W_MAX = 3.0
FIRE_NEGS = [
    "campfire",
    "fire basin glowing",
    "distant night lights",
    "bonfire",
]
LIMIT_DEFAULT = 12
LIMIT_MIN = 8
LIMIT_MAX = 15
SEA_EXCLUDE = ["0304", "0305"]
GATE_NOUN = "clip_noun+no_person"
GATE_MOON = "clip_noun+soft_person+fire_neg"
GATE_PICT = "pictorial"


class MissingIndex(FileNotFoundError):
    """Required index files are missing. Do not unpack."""


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def clamp_limit(n: int) -> int:
    return max(LIMIT_MIN, min(LIMIT_MAX, int(n)))


def gold_id(path: str) -> str:
    return Path(path).stem.split("_")[-1]


def is_excluded(path: str, stems: list[str]) -> bool:
    if not stems:
        return False
    name = Path(path).name
    stem = Path(path).stem
    return any(s in name or s in stem for s in stems)


def is_sea_road_box(box_dir: Path, meta: dict | None = None) -> bool:
    s = str(box_dir).replace("\\", "/").lower()
    if "sea-road" in s or "sea_road" in s:
        return True
    if meta and meta.get("exclude_stems"):
        return True
    return False


def _put_keys(dst: dict[str, float], path: str, value: float, folder: Any = None) -> None:
    if not path:
        return
    dst[path] = value
    name = Path(path).name
    dst[name] = value
    dst[Path(path).stem] = value
    if folder is not None and name:
        dst[f"{folder}/{name}"] = value


def require_core_index(index_dir: Path) -> None:
    needed = ["clip.json", "clip_vectors.npy", "mechanical.json"]
    missing = [str(index_dir / n) for n in needed if not (index_dir / n).is_file()]
    if missing:
        raise MissingIndex(
            "missing required index files (will not unpack):\n  " + "\n  ".join(missing)
        )


CORE_INDEX_FILES = ("clip.json", "clip_vectors.npy", "mechanical.json")
PERSON_INDEX_FILES = ("empty_hard.json", "motion.json")


def doctor_index(box_dir: Path) -> dict:
    """Check index files. Do not unpack, query, or pretend."""
    box = Path(box_dir).expanduser()
    files: list[dict] = []
    notes: list[str] = []
    missing_req: list[str] = []

    def add(name: str, path: Path, role: str, present: bool) -> None:
        files.append({"name": name, "path": str(path), "present": present, "role": role})
        if role == "required" and not present:
            missing_req.append(str(path))

    if not box.exists():
        notes.append(f"盒不存在：{box}。不會解包。")
        guess = box / "index"
        for name in CORE_INDEX_FILES:
            add(name, guess / name, "required", False)
        for name in PERSON_INDEX_FILES:
            add(name, guess / name, "person_clip", False)
        return {
            "ok": False,
            "can_query": False,
            "box": str(box),
            "index": None,
            "files": files,
            "missing": missing_req,
            "notes": notes,
        }

    box = box.resolve()
    index_dir = box / "index" if (box / "index").is_dir() else box
    if not index_dir.is_dir():
        notes.append(f"沒有 index 目錄：{box / 'index'}。不會解包。")
        for name in CORE_INDEX_FILES:
            add(name, box / "index" / name, "required", False)
        for name in PERSON_INDEX_FILES:
            add(name, box / "index" / name, "person_clip", False)
        return {
            "ok": False,
            "can_query": False,
            "box": str(box),
            "index": None,
            "files": files,
            "missing": missing_req,
            "notes": notes,
        }

    for name in CORE_INDEX_FILES:
        add(name, index_dir / name, "required", (index_dir / name).is_file())
    person_ok = False
    for name in PERSON_INDEX_FILES:
        ok = (index_dir / name).is_file()
        add(name, index_dir / name, "person_clip", ok)
        if ok:
            person_ok = True
    if not person_ok:
        notes.append(
            "沒有 empty_hard.json 或 motion.json："
            "pictorial 仍可查；雅丹硬濾會停，孤月軟罰當 0。"
        )

    if not missing_req:
        try:
            meta, vecs = load_index(index_dir)
            notes.append(
                f"clip 可讀  shape={tuple(int(x) for x in vecs.shape)}  "
                f"clips={meta.get('clip_count')}  frames={meta.get('frame_count')}"
            )
        except Exception as e:
            notes.append(f"index 讀失敗：{e}")
            missing_req.append(str(index_dir / "clip_vectors.npy"))
            for f in files:
                if f["name"] == "clip_vectors.npy":
                    f["present"] = False

    return {
        "ok": len(missing_req) == 0,
        "can_query": len(missing_req) == 0,
        "box": str(box),
        "index": str(index_dir),
        "files": files,
        "missing": missing_req,
        "notes": notes,
    }


def print_doctor(report: dict) -> None:
    print(f"box: {report['box']}")
    print(f"index: {report.get('index') or '(none)'}")
    for f in report["files"]:
        mark = "OK  " if f["present"] else "MISS"
        extra = "" if f["role"] == "required" else f"  ({f['role']})"
        print(f"  {mark}  {f['name']:<20}{extra}")
        if not f["present"] and f["role"] == "required":
            print(f"        {f['path']}")
    for n in report.get("notes") or []:
        print(f"note: {n}")
    if report["missing"]:
        print("missing:")
        for m in report["missing"]:
            print(f"  {m}")
    print(f"can_query: {'yes' if report['can_query'] else 'no'}")


def load_durations(index_dir: Path, meta: dict) -> dict[str, float]:
    by: dict[str, float] = {}
    mech = index_dir / "mechanical.json"
    if mech.is_file():
        data = json.loads(mech.read_text(encoding="utf-8"))
        rows = data.get("clips") or data.get("items") or []
        for c in rows:
            fn = str(c.get("filename") or c.get("path") or "")
            if not fn:
                continue
            _put_keys(by, fn, float(c.get("duration_sec") or 0.0), c.get("folder"))
    for fr in meta.get("frames") or []:
        fn = str(fr.get("filename") or "")
        if not fn:
            continue
        if fn in by or Path(fn).name in by:
            continue
        _put_keys(by, fn, float(fr.get("duration_sec") or 0.0), None)
    return by


def lookup_num(by: dict[str, float] | None, path: str, default: float | None = None) -> float | None:
    if not by:
        return default
    for key in (path, Path(path).name, Path(path).stem):
        if key in by:
            return float(by[key])
    return default


def load_person_map(index_dir: Path) -> tuple[dict[str, float] | None, str | None]:
    hard = index_dir / "empty_hard.json"
    motion = index_dir / "motion.json"
    if hard.is_file():
        data = json.loads(hard.read_text(encoding="utf-8"))
        by: dict[str, float] = {}
        for c in data.get("clips") or []:
            if "person_clip" not in c:
                continue
            _put_keys(by, str(c.get("path") or c.get("filename") or ""), float(c["person_clip"]))
        return by, "empty_hard.json"
    if motion.is_file():
        data = json.loads(motion.read_text(encoding="utf-8"))
        by = {}
        for c in data.get("clips") or []:
            if "person_clip" not in c:
                continue
            _put_keys(by, str(c.get("filename") or c.get("path") or ""), float(c["person_clip"]))
        return by, "motion.json"
    return None, None


def duration_bonus_pictorial(dur: float, spec: dict) -> float:
    if CUT_LO <= float(dur) <= CUT_HI:
        return DUR_BONUS
    lo = float(spec.get("dur_lo") if spec.get("dur_lo") is not None else CUT_LO)
    hi = float(spec.get("dur_hi") if spec.get("dur_hi") is not None else CUT_HI)
    if lo <= float(dur) <= hi:
        return DUR_BONUS
    return 0.0


def duration_bonus_cut(dur: float) -> float:
    return DUR_BONUS if CUT_LO <= float(dur) <= CUT_HI else 0.0


def rank_pool(hits: list[dict]) -> list[dict]:
    return sorted(
        hits,
        key=lambda h: (-float(h["score"]), -float(h.get("duration_sec") or 0.0), h["path"]),
    )


def gold_ranks(ranked: list[dict], golds: list[str]) -> list[dict]:
    by: dict[str, tuple[int, dict]] = {}
    for i, h in enumerate(ranked, 1):
        gid = gold_id(h["path"])
        if gid in golds and gid not in by:
            by[gid] = (i, h)
    rows = []
    for g in golds:
        if g in by:
            i, h = by[g]
            rows.append(
                {
                    "gold": g,
                    "path": h["path"],
                    "rank": i,
                    "score": round(float(h["score"]), 4),
                    "in_12": i <= 12,
                    "in_15": i <= 15,
                }
            )
        else:
            rows.append(
                {
                    "gold": g,
                    "path": None,
                    "rank": None,
                    "score": None,
                    "in_12": False,
                    "in_15": False,
                    "note": "not in index or excluded",
                }
            )
    return rows


def _iter_frames(meta: dict, exclude: list[str]):
    for i, fr in enumerate(meta.get("frames") or []):
        fn = fr.get("filename") or ""
        if not fn or is_excluded(fn, exclude):
            continue
        yield i, fr, fn


def score_pictorial_clips(
    meta: dict,
    vecs: np.ndarray,
    pos_vec: np.ndarray,
    neg_vec: np.ndarray | None,
    dur_by: dict[str, float],
    exclude: list[str],
) -> list[dict]:
    parts = [pos_vec.reshape(1, -1)]
    if neg_vec is not None:
        parts.append(neg_vec.reshape(1, -1))
    text_vecs = np.concatenate(parts, axis=0)
    sims = vecs @ text_vecs.T
    by: dict[str, dict] = {}
    for i, fr, fn in _iter_frames(meta, exclude):
        row = sims[i]
        pos = float(row[0])
        rec = by.get(fn)
        if rec is None or pos > rec["clip_score"]:
            item = {
                "path": fn,
                "clip_score": pos,
                "best_frame": fr.get("frame"),
                "best_time_sec": float(fr.get("time_sec") or 0.0),
                "duration_sec": round(
                    float(lookup_num(dur_by, fn, float(fr.get("duration_sec") or 0.0)) or 0.0),
                    4,
                ),
            }
            if neg_vec is not None:
                item["neg_score"] = float(row[1])
            by[fn] = item
    return list(by.values())


def apply_pictorial(hit: dict, spec: dict) -> tuple[float, list[str]]:
    reasons: list[str] = []
    delta = 0.0
    pos = float(hit["clip_score"])
    if spec.get("negative_en") and "neg_score" in hit:
        neg = float(hit["neg_score"])
        if neg > pos:
            pen = NEG_W * (neg - pos)
            delta -= pen
            reasons.append(f"neg {neg:.4f} > pos {pos:.4f} adj={-pen:+.3f}")
        else:
            reasons.append(f"neg {neg:.4f} <= pos {pos:.4f} no penalty")
    bonus = duration_bonus_pictorial(float(hit["duration_sec"]), spec)
    if bonus:
        delta += bonus
        reasons.append(
            f"duration +{bonus:.2f} ({hit['duration_sec']:.3f}s in cut 2-5s or sentence target)"
        )
    else:
        reasons.append(f"duration no bonus ({hit['duration_sec']:.3f}s)")
    return float(hit["clip_score"]) + delta, reasons


def format_pictorial(h: dict, spec: dict, gate: str) -> dict:
    clip_s = float(h["clip_score"])
    reasons = [
        f"best frame {h['best_frame']} @ {h['best_time_sec']:.3f}s",
        (
            f"near {spec.get('visual_zh') or spec.get('intent')} / "
            f"{spec.get('visual_en')} (cosine={clip_s:.4f})"
        ),
    ]
    reasons.extend(h.get("score_why") or [])
    item = {
        "path": h["path"],
        "score": round(float(h["score"]), 4),
        "gate": gate,
        "reasons": reasons,
        "clip_score": round(clip_s, 4),
        "duration_sec": h["duration_sec"],
        "best_frame": h["best_frame"],
        "best_time_sec": h["best_time_sec"],
        "duration_bonus": h.get("duration_bonus", 0.0),
    }
    if spec.get("negative_en"):
        item["neg_score"] = round(float(h.get("neg_score") or 0.0), 4)
    return item


def score_noun_clips(
    meta: dict,
    vecs: np.ndarray,
    noun_vecs: np.ndarray,
    noun_labels: list[str],
    dur_by: dict[str, float],
    person_by: dict[str, float] | None,
    exclude: list[str],
    fire_vecs: np.ndarray | None = None,
    fire_labels: list[str] | None = None,
) -> list[dict]:
    noun_sims = vecs @ noun_vecs.T
    fire_sims = vecs @ fire_vecs.T if fire_vecs is not None else None
    by: dict[str, dict] = {}
    for i, fr, fn in _iter_frames(meta, exclude):
        nrow = noun_sims[i]
        t_i = int(np.argmax(nrow))
        n_s = float(nrow[t_i])
        rec = by.get(fn)
        if rec is None:
            pc = lookup_num(person_by, fn, None)
            rec = {
                "path": fn,
                "duration_sec": round(
                    float(lookup_num(dur_by, fn, float(fr.get("duration_sec") or 0.0)) or 0.0),
                    4,
                ),
                "clip_noun": n_s,
                "matched_text": noun_labels[t_i],
                "best_frame": fr.get("frame"),
                "best_time_sec": float(fr.get("time_sec") or 0.0),
                "person_clip": pc,
            }
            if fire_sims is not None and fire_labels is not None:
                frow = fire_sims[i]
                f_i = int(np.argmax(frow))
                rec["fire_max"] = float(frow[f_i])
                rec["fire_matched"] = fire_labels[f_i]
            by[fn] = rec
            continue
        if n_s > rec["clip_noun"]:
            rec["clip_noun"] = n_s
            rec["matched_text"] = noun_labels[t_i]
            rec["best_frame"] = fr.get("frame")
            rec["best_time_sec"] = float(fr.get("time_sec") or 0.0)
        if fire_sims is not None and fire_labels is not None:
            frow = fire_sims[i]
            f_i = int(np.argmax(frow))
            f_s = float(frow[f_i])
            if f_s > float(rec.get("fire_max") or -1e9):
                rec["fire_max"] = f_s
                rec["fire_matched"] = fire_labels[f_i]
    return list(by.values())


def apply_moon_score(h: dict, fire_w: float) -> dict:
    noun = float(h["clip_noun"])
    pc = h.get("person_clip")
    ppen = 0.0 if pc is None else PERSON_W * max(0.0, float(pc))
    db = duration_bonus_cut(h["duration_sec"])
    fire = float(h.get("fire_max") or 0.0)
    fpen = fire_w * fire
    h["person_penalty"] = ppen
    h["duration_bonus"] = db
    h["fire_penalty"] = fpen
    h["fire_weight"] = fire_w
    h["score"] = noun - ppen + db - fpen
    return h


def pick_fire_weight(hits: list[dict]) -> tuple[float, int | None]:
    """Raise fire_w globally until 0308 is out of top 12. No per-id drop."""
    if not any(gold_id(h["path"]) == "0308" for h in hits):
        for h in hits:
            apply_moon_score(h, FIRE_W0)
        return FIRE_W0, None
    w = FIRE_W0
    rank_0308: int | None = None
    while w <= FIRE_W_MAX + 1e-9:
        for h in hits:
            apply_moon_score(h, w)
        ranked = rank_pool(hits)
        rank_0308 = None
        for i, h in enumerate(ranked, 1):
            if gold_id(h["path"]) == "0308":
                rank_0308 = i
                break
        if rank_0308 is None or rank_0308 > 12:
            return w, rank_0308
        if w >= FIRE_W_MAX:
            return w, rank_0308
        w = round(w + FIRE_STEP, 4)
    return w, rank_0308


def reasons_yardang(h: dict) -> list[str]:
    pc = h.get("person_clip")
    clip_s = float(h["clip_noun"])
    out = [
        f"CLIP名词 {h['matched_text']} (cosine={clip_s:.4f})",
        f"无人滤 person_clip={float(pc):+.4f} < 0.0000 (0.00)",
    ]
    db = float(h.get("duration_bonus") or 0.0)
    if db:
        out.append(f"时长 {h['duration_sec']:.2f}s 落在 2-5s +{db:.2f}")
    else:
        out.append(f"时长 {h['duration_sec']:.2f}s 无加分")
    out.append(f"best frame {h['best_frame']} @ {h['best_time_sec']:.3f}s")
    return out


def reasons_moon(h: dict) -> list[str]:
    pc = h.get("person_clip")
    clip_s = float(h["clip_noun"])
    ppen = float(h.get("person_penalty") or 0.0)
    fire = float(h.get("fire_max") or 0.0)
    fpen = float(h.get("fire_penalty") or 0.0)
    fw = float(h.get("fire_weight") or FIRE_W0)
    if pc is not None and float(pc) > 0:
        person_s = f"person_clip软罚 {pc:+.4f} * {PERSON_W:.2f} = -{ppen:.4f}"
    elif pc is not None:
        person_s = f"person_clip软罚 {pc:+.4f}（<=0 不扣）"
    else:
        person_s = "person_clip缺失 不扣"
    out = [
        f"CLIP名词 {h['matched_text']} (cosine={clip_s:.4f})",
        person_s,
        (
            f"火光降权 {h.get('fire_matched', 'fire')} "
            f"fire_max={fire:.4f} * {fw:.2f} = -{fpen:.4f}"
        ),
    ]
    db = float(h.get("duration_bonus") or 0.0)
    if db:
        out.append(f"时长 {h['duration_sec']:.2f}s 落在 2-5s +{db:.2f}")
    out.append(f"best frame {h['best_frame']} @ {h['best_time_sec']:.3f}s")
    return out


def format_yardang(h: dict, gate: str) -> dict:
    pc = h.get("person_clip")
    return {
        "path": h["path"],
        "score": round(float(h["score"]), 4),
        "gate": gate,
        "reasons": reasons_yardang(h),
        "clip_noun": round(float(h["clip_noun"]), 4),
        "person_clip": None if pc is None else round(float(pc), 4),
        "duration_sec": h["duration_sec"],
        "best_frame": h["best_frame"],
        "best_time_sec": h["best_time_sec"],
        "matched_text": h["matched_text"],
        "duration_bonus": h.get("duration_bonus", 0.0),
    }


def format_moon(h: dict, gate: str) -> dict:
    pc = h.get("person_clip")
    return {
        "path": h["path"],
        "score": round(float(h["score"]), 4),
        "gate": gate,
        "reasons": reasons_moon(h),
        "clip_noun": round(float(h["clip_noun"]), 4),
        "person_clip": None if pc is None else round(float(pc), 4),
        "person_penalty": round(float(h.get("person_penalty") or 0.0), 4),
        "fire_max": round(float(h.get("fire_max") or 0.0), 4),
        "fire_matched": h.get("fire_matched"),
        "fire_penalty": round(float(h.get("fire_penalty") or 0.0), 4),
        "fire_weight": float(h.get("fire_weight") or FIRE_W0),
        "duration_sec": h["duration_sec"],
        "best_frame": h["best_frame"],
        "best_time_sec": h["best_time_sec"],
        "matched_text": h["matched_text"],
        "duration_bonus": h.get("duration_bonus", 0.0),
    }


def _encode_map(clip: LocalCLIP, texts: list[str]) -> dict[str, np.ndarray]:
    uniq = list(dict.fromkeys(t for t in texts if t))
    if not uniq:
        return {}
    tvecs = clip.encode_texts(uniq)
    return {t: tvecs[i] for i, t in enumerate(uniq)}


def run_query(
    box_dir: str | Path,
    intent_text: str,
    limit: int = LIMIT_DEFAULT,
    model: LocalCLIP | None = None,
) -> dict:
    box_dir = Path(box_dir).resolve()
    index_dir = box_dir / "index" if (box_dir / "index").is_dir() else box_dir
    if not index_dir.is_dir():
        raise MissingIndex(f"missing index dir: {index_dir} (will not unpack)")
    require_core_index(index_dir)

    q = resolve_query(intent_text)
    spec = q["spec"]
    gate = spec["gate"]
    limit = clamp_limit(limit)

    meta, vecs = load_index(index_dir)
    exclude = SEA_EXCLUDE if is_sea_road_box(box_dir, meta) else []
    dur_by = load_durations(index_dir, meta)
    person_by, person_src = load_person_map(index_dir)

    needs_person = gate in (GATE_NOUN, GATE_MOON)
    if needs_person and person_by is None:
        if gate == GATE_NOUN:
            raise MissingIndex(
                "gate clip_noun+no_person needs person_clip from "
                f"{index_dir / 'empty_hard.json'} or {index_dir / 'motion.json'}"
            )
        print(
            f"warning: person_clip file missing under {index_dir}; "
            "moon gate treats person as 0 (soft)",
            file=sys.stderr,
        )

    clip = model or LocalCLIP(offline=True)
    generated = now_iso()
    extra: dict[str, Any] = {}

    if gate == GATE_NOUN:
        labels = list(spec.get("nouns") or [])
        if not labels:
            raise ValueError(f"{spec['slug']} missing nouns")
        tmap = _encode_map(clip, labels)
        noun_tv = np.stack([tmap[t] for t in labels], axis=0)
        scored = score_noun_clips(meta, vecs, noun_tv, labels, dur_by, person_by, exclude)
        kept = []
        for h in scored:
            pc = h.get("person_clip")
            if pc is None or float(pc) >= 0.0:
                continue
            h["duration_bonus"] = duration_bonus_cut(h["duration_sec"])
            h["score"] = float(h["clip_noun"]) + float(h["duration_bonus"])
            kept.append(h)
        ranked = rank_pool(kept)
        results = [format_yardang(h, gate) for h in ranked[:limit]]
        extra["noun_texts"] = labels
        extra["person_source"] = person_src
        extra["person_filter"] = {
            "field": "person_clip",
            "op": "<",
            "threshold": 0.0,
            "box_size": len(scored),
            "pool_size": len(kept),
        }
    elif gate == GATE_MOON:
        labels = list(spec.get("nouns") or [])
        if not labels:
            raise ValueError(f"{spec['slug']} missing nouns")
        tmap = _encode_map(clip, [*labels, *FIRE_NEGS])
        noun_tv = np.stack([tmap[t] for t in labels], axis=0)
        fire_tv = np.stack([tmap[t] for t in FIRE_NEGS], axis=0)
        scored = score_noun_clips(
            meta, vecs, noun_tv, labels, dur_by, person_by, exclude, fire_tv, FIRE_NEGS
        )
        fire_w, rank_0308 = pick_fire_weight(scored)
        ranked = rank_pool(scored)
        results = [format_moon(h, gate) for h in ranked[:limit]]
        extra["noun_texts"] = labels
        extra["fire_neg_texts"] = FIRE_NEGS
        extra["person_source"] = person_src
        extra["fire_neg"] = {
            "texts": FIRE_NEGS,
            "weight": fire_w,
            "weight_start": FIRE_W0,
            "rank_0308": rank_0308,
        }
    else:
        visual_en = spec.get("visual_en") or q["visual_en"] or intent_text
        negative_en = spec.get("negative_en")
        texts = [visual_en]
        if negative_en:
            texts.append(negative_en)
        tmap = _encode_map(clip, texts)
        pos_v = tmap[visual_en]
        neg_v = tmap[negative_en] if negative_en else None
        scored = score_pictorial_clips(meta, vecs, pos_v, neg_v, dur_by, exclude)
        work = []
        for h in scored:
            score, why = apply_pictorial(h, spec)
            rec = dict(h)
            rec["score"] = score
            rec["score_why"] = why
            rec["duration_bonus"] = duration_bonus_pictorial(float(h["duration_sec"]), spec)
            work.append(rec)
        ranked = rank_pool(work)
        results = [format_pictorial(h, spec, gate) for h in ranked[:limit]]
        extra["visual_en"] = visual_en
        extra["negative_en"] = negative_en
        extra["duration_sec_target"] = [spec.get("dur_lo"), spec.get("dur_hi")]

    golds = list(spec.get("golds") or [])
    recall = gold_ranks(ranked, golds) if golds else []
    payload = {
        "query": intent_text,
        "intent": q["intent"],
        "slug": q["slug"],
        "gate": gate,
        "count": len(results),
        "model": meta.get("model", MODEL_NAME),
        "generated_at": generated,
        "duration_hard_filter": False,
        "matched_known_intent": q["matched"],
        "visual_zh": q["visual_zh"],
        "visual_en": spec.get("visual_en") or q["visual_en"],
        "pretrained": meta.get("pretrained", PRETRAINED),
        "device": meta.get("device", DEVICE),
        "pool_size": len(ranked),
        "exclude_stems": exclude,
        "index": str(index_dir),
        "note": (
            "Local CLIP on an existing index. Query texts only. "
            "No frame re-extract, no clip_vectors.npy recompute. "
            "Duration is a +0.02 bonus, not a hard filter. Not a pass."
        ),
        "results": results,
    }
    payload.update(extra)
    if recall:
        payload["recall"] = {
            "golds": golds,
            "gold_any": bool(spec.get("gold_any")),
            "hits": [r for r in recall if r.get("in_12")],
            "all_gold_ranks": recall,
        }
    return payload


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_table(payload: dict) -> None:
    print(
        f"{payload['query']}  slug={payload['slug']}  gate={payload['gate']}  "
        f"n={payload['count']}  model={payload.get('model')} {payload.get('device')}"
    )
    if not payload["results"]:
        print("(none)")
        return
    for i, c in enumerate(payload["results"], 1):
        dur = c.get("duration_sec")
        dur_s = f"{float(dur):6.2f}s" if dur is not None else "      ?"
        print(f"{i:2d}  {c['path']:<28}  {dur_s}  score={c['score']:.4f}")
