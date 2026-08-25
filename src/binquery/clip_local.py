"""Local OpenCLIP helpers. CPU only. No cloud vision API."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
DEVICE = "cpu"


def resolve_cache_dir(cache_dir: str | Path | None = None) -> Path:
    if cache_dir:
        return Path(cache_dir).expanduser()
    env = (os.environ.get("BINQUERY_CLIP_CACHE") or "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "binquery" / "open_clip"


def _l2(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True).clamp_min(1e-8)


class LocalCLIP:
    """Encode query texts, or stills when building an index. No cloud vision API."""

    def __init__(self, offline: bool | None = None, cache_dir: str | Path | None = None):
        cache = resolve_cache_dir(cache_dir)
        cache.mkdir(parents=True, exist_ok=True)
        if offline is None:
            offline = (os.environ.get("BINQUERY_OFFLINE") or "").strip() in {"1", "true", "yes"}
        if offline:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            if not any(cache.iterdir()):
                raise FileNotFoundError(
                    f"missing OpenCLIP cache: {cache}. "
                    "Put ViT-B-32 / laion2b_s34b_b79k weights there, "
                    "or unset BINQUERY_OFFLINE for a one-time local download."
                )
        import open_clip

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME,
            pretrained=PRETRAINED,
            device=DEVICE,
            cache_dir=str(cache),
        )
        self.model.eval()
        self.model.to(DEVICE)
        self.tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        visual = getattr(self.model, "visual", None)
        self.dim = int(getattr(visual, "output_dim", 512) or 512)

    def encode_images(self, paths: list[Path], batch: int = 16) -> np.ndarray:
        vecs: list[np.ndarray] = []
        with torch.no_grad():
            for i in range(0, len(paths), batch):
                chunk = paths[i : i + batch]
                tensors = []
                for pth in chunk:
                    im = Image.open(pth).convert("RGB")
                    tensors.append(self.preprocess(im))
                x = torch.stack(tensors, dim=0).to(DEVICE)
                feat = _l2(self.model.encode_image(x))
                vecs.append(feat.cpu().numpy().astype(np.float32))
        return np.concatenate(vecs, axis=0) if vecs else np.zeros((0, self.dim), dtype=np.float32)

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        with torch.no_grad():
            tok = self.tokenizer(texts)
            feat = _l2(self.model.encode_text(tok.to(DEVICE)))
            return feat.cpu().numpy().astype(np.float32)


def load_index(index_dir: str | Path) -> tuple[dict, np.ndarray]:
    index_dir = Path(index_dir)
    clip_json = index_dir / "clip.json"
    clip_npy = index_dir / "clip_vectors.npy"
    if not clip_json.is_file() or not clip_npy.is_file():
        raise FileNotFoundError(
            f"missing CLIP index: {clip_json} / {clip_npy}. Will not unpack or re-embed."
        )
    meta = json.loads(clip_json.read_text(encoding="utf-8"))
    vecs = np.load(clip_npy)
    if vecs.ndim != 2:
        raise ValueError(f"clip_vectors.npy shape {vecs.shape}, expected (N, D)")
    n_frames = len(meta.get("frames") or [])
    if n_frames and n_frames != int(vecs.shape[0]):
        raise ValueError(
            f"clip.json frames={n_frames} != clip_vectors.npy rows={vecs.shape[0]}"
        )
    return meta, vecs
