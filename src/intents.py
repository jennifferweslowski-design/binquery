"""Frozen director intents + alias match. Do not rewrite the Chinese sentences."""
from __future__ import annotations

from typing import Any

SPECS: list[dict[str, Any]] = [
    {
        "slug": "pictorial-est-worker-train",
        "intent": "建立，地面中景工人與車同框，火車已在畫裡，3–5 秒",
        "visual_zh": "建立，地面中景工人與車同框，火車已在畫裡，3–5 秒",
        "visual_en": "medium shot of a worker and a train already in frame",
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 3.0,
        "dur_hi": 5.0,
        "golds": ["0182"],
        "gold_any": False,
        "aliases": ["工人與車", "中景工人與車", "工人與火車"],
    },
    {
        "slug": "pictorial-empty-fog-freight-side",
        "intent": "空鏡，霧裡人看貨車側面，2–4 秒，不要車頭正面",
        "visual_zh": "空鏡，霧裡人看貨車側面，2–4 秒，不要車頭正面",
        "visual_en": "person looking at the side of a freight train in fog",
        "negative_en": "front of a train locomotive facing the camera",
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 4.0,
        "golds": ["0183"],
        "gold_any": False,
        "aliases": ["霧裡人看貨車側面", "霧裡人看貨車"],
    },
    {
        "slug": "pictorial-empty-crossing-signal",
        "intent": "空鏡，平交道號誌，無人臉，2–3 秒",
        "visual_zh": "空鏡，平交道號誌，無人臉，2–3 秒",
        "visual_en": "railroad crossing signal, no people, no faces",
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 3.0,
        "golds": ["0250"],
        "gold_any": False,
        "aliases": ["平交道號誌", "平交道號誌，無人臉"],
    },
    {
        "slug": "pictorial-empty-night-wide",
        "intent": "空鏡，夜間地面遠景無人，2–3 秒，不要車窗特寫",
        "visual_zh": "空鏡，夜間地面遠景無人，2–3 秒，不要車窗特寫",
        "visual_en": "empty night wide shot of ground tracks or platform, no people",
        "negative_en": "close-up of a train window",
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 3.0,
        "golds": ["0258", "0266"],
        "gold_any": True,
        "aliases": ["夜間地面遠景無人", "夜間地面遠景"],
    },
    {
        "slug": "pictorial-buffer-steam-recede",
        "intent": "緩衝，蒸汽火車遠去餘韻，鎖死遠景，2–3 秒，不要車頭特寫",
        "visual_zh": "緩衝，蒸汽火車遠去餘韻，鎖死遠景，2–3 秒，不要車頭特寫",
        "visual_en": "locked-off wide lingering shot of a steam train receding into the distance",
        "negative_en": "close-up of a train locomotive front",
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 3.0,
        "golds": ["0248"],
        "gold_any": False,
        "aliases": ["蒸汽火車遠去餘韻", "蒸汽火車遠去"],
    },
    {
        "slug": "pictorial-est-night-window-person",
        "intent": "建立，夜間車側窗裡有人，2–4 秒，不要只有車身中段無窗",
        "visual_zh": "建立，夜間車側窗裡有人，2–4 秒，不要只有車身中段無窗",
        "visual_en": "person visible in a train side window at night",
        "negative_en": "train car body with no windows",
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 4.0,
        "golds": ["0075"],
        "gold_any": False,
        "aliases": ["夜間車側窗裡有人", "車側窗裡有人"],
    },
    {
        "slug": "sea-est-yardang-empty",
        "intent": "建立，地面遠景雅丹空岩，無人",
        "visual_zh": "建立，地面遠景雅丹空岩，無人",
        "visual_en": "wide ground shot of empty yardang rocks, no people",
        "negative_en": None,
        "gate": "clip_noun+no_person",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": ["0158", "0124"],
        "gold_any": False,
        "nouns": ["yardang", "sandstone rock formation", "desert rock, no people"],
        "aliases": ["雅丹空岩", "地面遠景雅丹空岩", "地面遠景雅丹"],
    },
    {
        "slug": "sea-est-person-yardang",
        "intent": "建立，人站雅丹前，地面中景",
        "visual_zh": "建立，人站雅丹前，地面中景",
        "visual_en": "person standing in front of yardang rocks, ground medium shot",
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": ["0197"],
        "gold_any": False,
        "aliases": ["人站雅丹前", "人站在雅丹前"],
    },
    {
        "slug": "sea-react-face-pause",
        "intent": "反應，臉或身體停頓特寫，不是揭曉之後",
        "visual_zh": "反應，臉或身體停頓特寫，不是揭曉之後",
        "visual_en": "close-up of a face or body pausing, not after a reveal",
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": ["0148", "0149", "0144"],
        "gold_any": False,
        "aliases": ["臉或身體停頓特寫", "臉或身體停頓"],
    },
    {
        "slug": "sea-empty-moon-rock",
        "intent": "空鏡，孤月或石縫或雅丹無人",
        "visual_zh": "空鏡，孤月或石縫或雅丹無人",
        "visual_en": "empty shot of a lone moon, rock crevice, or yardang, no people",
        "negative_en": None,
        "gate": "clip_noun+soft_person+fire_neg",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": ["0312", "0130", "0162"],
        "gold_any": False,
        "nouns": ["lone moon", "moon over rock crevice", "moon above yardang, no people"],
        "aliases": ["孤月", "孤月或石縫", "孤月或石縫或雅丹"],
    },
    {
        "slug": "sea-buffer-fire-night",
        "intent": "緩衝，地面火塘或遠處夜燈或月下山脊",
        "visual_zh": "緩衝，地面火塘或遠處夜燈或月下山脊",
        "visual_en": "ground fire pit or distant night lights or ridgeline under the moon",
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": ["0255", "0142", "0308"],
        "gold_any": False,
        "aliases": ["地面火塘", "火塘或遠處夜燈", "月下山脊"],
    },
]


def _unmatched_spec(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    return {
        "slug": "unmatched",
        "intent": raw,
        "visual_zh": raw,
        "visual_en": raw,
        "negative_en": None,
        "gate": "pictorial",
        "dur_lo": 2.0,
        "dur_hi": 5.0,
        "golds": [],
        "gold_any": False,
        "aliases": [],
    }


def match_intent(text: str) -> dict[str, Any] | None:
    """Exact intent / visual_zh / slug / any alias. Prefer longest alias hit."""
    t = (text or "").strip()
    if not t:
        return None
    for spec in SPECS:
        if t in (spec["intent"], spec["visual_zh"], spec["slug"]):
            return spec
        if spec.get("visual_en") and t == spec["visual_en"]:
            return spec
    best: dict[str, Any] | None = None
    best_len = 0
    for spec in SPECS:
        for alias in spec.get("aliases") or []:
            if not alias:
                continue
            if alias == t or alias in t:
                if len(alias) > best_len:
                    best_len = len(alias)
                    best = spec
    return best


def resolve_query(text: str) -> dict[str, Any]:
    spec = match_intent(text)
    if spec is not None:
        return {
            "matched": True,
            "spec": spec,
            "intent": spec["intent"],
            "slug": spec["slug"],
            "gate": spec["gate"],
            "visual_zh": spec.get("visual_zh") or spec["intent"],
            "visual_en": spec.get("visual_en") or "",
            "query_text": text,
        }
    spec = _unmatched_spec(text)
    return {
        "matched": False,
        "spec": spec,
        "intent": spec["intent"],
        "slug": spec["slug"],
        "gate": spec["gate"],
        "visual_zh": spec["visual_zh"],
        "visual_en": spec["visual_en"],
        "query_text": text,
    }
