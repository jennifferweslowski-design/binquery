from __future__ import annotations

import json
from pathlib import Path

import pytest

from binquery.cli import main as cli_main
from binquery.demo_local import DemoError, run_demo


def test_demo_rejects_nonempty_output(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    out.mkdir()
    (out / "keep.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(DemoError, match="not empty"):
        run_demo(out)

    assert (out / "keep.txt").read_text(encoding="utf-8") == "user data"


def test_demo_runs_complete_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import binquery.demo_local as demo

    calls: list[str] = []

    def fake_generate(path: Path) -> None:
        calls.append("generate")
        path.write_bytes(b"synthetic")

    def fake_split(src: Path, out: Path, *, seconds: int) -> dict:
        calls.append("split")
        assert src.name == "synthetic-long.mp4"
        assert seconds == 8
        out.mkdir()
        return {"clip_count": 3, "out": str(out)}

    def fake_index(src: Path, box: Path) -> dict:
        calls.append("index")
        assert src.name == "clips"
        return {"clip_count": 3, "frame_count": 9, "box": str(box)}

    def fake_doctor(box: Path) -> dict:
        calls.append("doctor")
        return {"can_query": True, "missing": []}

    def fake_query(box: Path, intent: str, *, limit: int) -> dict:
        calls.append("query")
        assert intent == "red test pattern"
        assert limit == 9
        return {"results": [{"path": "part000.mp4", "score": 1.0}]}

    monkeypatch.setattr(demo, "_generate_long_video", fake_generate)
    monkeypatch.setattr(demo, "run_split", fake_split)
    monkeypatch.setattr(demo, "run_index", fake_index)
    monkeypatch.setattr(demo, "doctor_index", fake_doctor)
    monkeypatch.setattr(demo, "run_query", fake_query)

    report = run_demo(tmp_path / "demo", intent="red test pattern", limit=9)

    assert calls == ["generate", "split", "index", "doctor", "query"]
    assert json.loads(Path(report["query_path"]).read_text(encoding="utf-8")) == report[
        "query"
    ]


def test_demo_cli_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "demo"
    out.mkdir()
    (out / "existing.txt").write_text("keep", encoding="utf-8")

    exit_code = cli_main(["demo", "--out", str(out)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "not empty" in captured.err
