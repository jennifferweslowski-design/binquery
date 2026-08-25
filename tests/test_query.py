from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from binquery.cli import main as cli_main
from binquery.query import MissingIndex, doctor_index, run_query


class FakeModel:
    def __init__(self, vectors: dict[str, list[float]] | None = None) -> None:
        self.vectors = vectors or {}

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            [self.vectors.get(text, [1.0, 0.0]) for text in texts],
            dtype=np.float32,
        )


def make_box(
    tmp_path: Path,
    vectors: list[list[float]],
    *,
    durations: list[float] | None = None,
) -> tuple[Path, list[str]]:
    box = tmp_path / "box"
    index = box / "index"
    index.mkdir(parents=True)

    paths = [f"clip_{i:04d}.mp4" for i in range(len(vectors))]
    durations = durations or [1.0] * len(paths)
    assert len(durations) == len(paths)
    frames = [
        {
            "filename": path,
            "frame": 0,
            "time_sec": 0.0,
            "duration_sec": duration,
        }
        for path, duration in zip(paths, durations, strict=True)
    ]
    (index / "clip.json").write_text(
        json.dumps(
            {
                "model": "fake",
                "pretrained": "fake",
                "device": "cpu",
                "clip_count": len(paths),
                "frame_count": len(frames),
                "frames": frames,
            }
        ),
        encoding="utf-8",
    )
    np.save(index / "clip_vectors.npy", np.asarray(vectors, dtype=np.float32))
    (index / "mechanical.json").write_text(
        json.dumps(
            {
                "clips": [
                    {"filename": path, "duration_sec": duration}
                    for path, duration in zip(paths, durations, strict=True)
                ]
            }
        ),
        encoding="utf-8",
    )
    (index / "empty_hard.json").write_text(
        json.dumps(
            {
                "clips": [
                    {"path": path, "person_clip": -0.25} for path in paths
                ]
            }
        ),
        encoding="utf-8",
    )
    return box, paths


@pytest.mark.parametrize(
    ("query", "matched", "gate"),
    [
        ("an unknown visual description", False, "pictorial"),
        ("工人與車", True, "pictorial"),
        ("雅丹空岩", True, "clip_noun+no_person"),
        ("孤月", True, "clip_noun+soft_person+fire_neg"),
    ],
)
def test_matching_and_gate_are_independent(
    tmp_path: Path, query: str, matched: bool, gate: str
) -> None:
    box, _ = make_box(tmp_path, [[1.0, 0.0]])

    payload = run_query(box, query, model=FakeModel())

    assert payload["matched_known_intent"] is matched
    assert payload["gate"] == gate


def test_pictorial_ranking_and_output_shape(tmp_path: Path) -> None:
    box, paths = make_box(tmp_path, [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]])
    model = FakeModel({"an unknown visual description": [1.0, 0.0]})

    payload = run_query(box, "an unknown visual description", model=model)

    assert isinstance(payload, dict)
    assert [result["path"] for result in payload["results"]] == paths
    assert [result["score"] for result in payload["results"]] == pytest.approx(
        [1.0, 0.8, 0.0]
    )
    assert payload["pool_size"] == len(paths)
    expected_fields = {
        "path",
        "score",
        "gate",
        "reasons",
        "clip_score",
        "duration_sec",
        "best_frame",
        "best_time_sec",
        "duration_bonus",
    }
    assert all(expected_fields <= set(result) for result in payload["results"])
    assert {result["path"] for result in payload["results"]} <= set(paths)
    scores = [result["score"] for result in payload["results"]]
    assert scores == sorted(scores, reverse=True)


def test_limit_is_clamped_and_defaulted(tmp_path: Path) -> None:
    vectors = [[1.0 - i / 100.0, 0.0] for i in range(20)]
    box, _ = make_box(tmp_path, vectors)
    model = FakeModel({"unknown": [1.0, 0.0]})

    assert len(run_query(box, "unknown", model=model)["results"]) == 12
    assert len(run_query(box, "unknown", limit=3, model=model)["results"]) == 8
    assert len(run_query(box, "unknown", limit=100, model=model)["results"]) == 15


def test_duration_bonus_can_change_ranking(tmp_path: Path) -> None:
    box, paths = make_box(
        tmp_path,
        [[0.99, 0.0], [1.0, 0.0]],
        durations=[3.0, 1.0],
    )

    payload = run_query(box, "unknown", model=FakeModel())

    assert [result["path"] for result in payload["results"]] == paths
    assert [result["duration_bonus"] for result in payload["results"]] == pytest.approx(
        [0.02, 0.0]
    )
    assert [result["score"] for result in payload["results"]] == pytest.approx(
        [1.01, 1.0]
    )


def test_limit_can_return_fewer_than_minimum(tmp_path: Path) -> None:
    box, _ = make_box(tmp_path, [[1.0, 0.0], [0.5, 0.0], [0.0, 1.0]])

    payload = run_query(box, "unknown", limit=3, model=FakeModel())

    assert len(payload["results"]) == 3


def test_run_query_missing_index_raises_with_path(tmp_path: Path) -> None:
    missing_box = tmp_path / "missing-box"

    with pytest.raises(MissingIndex) as exc_info:
        run_query(missing_box, "unknown", model=FakeModel())

    assert str(missing_box) in str(exc_info.value)


def test_cli_missing_core_files_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    box = tmp_path / "box"
    index = box / "index"
    index.mkdir(parents=True)

    exit_code = cli_main(["query", "--index", str(box), "unknown"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert str(index / "clip.json") in captured.err
    assert doctor_index(box)["can_query"] is False
