#!/usr/bin/env python3
"""binquery v0 — local CLIP shortlist CLI. Not a pass."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .intents import SPECS
from .split_local import (
    SECONDS_DEFAULT,
    SplitError,
    default_out_dir,
    run_split,
)


def cmd_list(_args: argparse.Namespace) -> int:
    print(f"{'slug':<34} {'gate':<32} aliases")
    for spec in SPECS:
        aliases = ", ".join(spec.get("aliases") or [])
        print(f"{spec['slug']:<34} {spec['gate']:<32} {aliases}")
        print(f"  {spec['intent']}")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    src = Path(args.input).expanduser()
    out = Path(args.out).expanduser() if args.out else default_out_dir(src)
    try:
        report = run_split(src, out, seconds=args.seconds, reencode=args.reencode)
    except SplitError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(
        f"split {report['clip_count']} clips -> {report['out']} "
        f"({report['mode']}, segment_time={report['seconds']})"
    )
    print(report["note"])
    for c in report["clips"]:
        print(f"  {c['path']}  {c['duration_sec']:.3f}s")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    from .index_box import IndexError_, run_index

    try:
        report = run_index(Path(args.input).expanduser(), Path(args.index).expanduser())
    except IndexError_ as e:
        print(str(e), file=sys.stderr)
        return 2
    print(
        f"indexed {report['clip_count']} clips / {report['frame_count']} stills "
        f"shape={tuple(report['shape'])} -> {report['box']}"
    )
    for w in report["wrote"]:
        print(f"  wrote {w}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from .query import doctor_index, print_doctor

    report = doctor_index(Path(args.index).expanduser())
    print_doctor(report)
    return 0 if report["can_query"] else 2


def cmd_query(args: argparse.Namespace) -> int:
    from .query import MissingIndex, dump_json, print_table, run_query

    box = Path(args.index).expanduser()
    try:
        payload = run_query(box, args.intent, limit=args.limit)
    except MissingIndex as e:
        print(str(e), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    print_table(payload)
    if args.out:
        out = Path(args.out).expanduser()
    else:
        index_dir = box / "index" if (box / "index").is_dir() else box
        out = index_dir / "queries" / f"cli-{payload['slug']}.json"
    dump_json(out, payload)
    print(f"wrote {out}", file=sys.stderr)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from .demo_local import DemoError, run_demo
    from .query import print_doctor, print_table

    try:
        report = run_demo(
            Path(args.out).expanduser(),
            intent=args.intent,
            limit=args.limit,
        )
    except DemoError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(
        f"generated and split {report['split']['clip_count']} synthetic clips; "
        f"indexed {report['index']['frame_count']} stills"
    )
    print_doctor(report["doctor"])
    print_table(report["query"])
    print(f"wrote {report['query_path']}", file=sys.stderr)
    print(f"demo complete -> {report['root']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="binquery",
        description="Local CLIP shortlist. Optional time-grid split, then index, then doctor/query.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser(
        "split",
        help="time-grid split one local video into a folder (ffmpeg segment; not highlights)",
    )
    sp.add_argument("--input", required=True, help="one local video file (the long take)")
    sp.add_argument(
        "--out",
        default=None,
        help="empty or new folder for clips (default: <input-dir>/split-out; never the program tree)",
    )
    sp.add_argument(
        "--seconds",
        type=int,
        default=SECONDS_DEFAULT,
        help=(
            "target clip length (default 8, clamped 4-60). "
            "Default -c copy cuts on keyframes, so duration is not exact."
        ),
    )
    sp.add_argument(
        "--reencode",
        action="store_true",
        help="reencode libx264+aac for nearer-exact duration (local ffmpeg only)",
    )
    sp.set_defaults(func=cmd_split)

    qq = sub.add_parser("query", help="shortlist 8-15 clips for an intent")
    qq.add_argument("--index", required=True, help="box root containing index/")
    qq.add_argument("intent", help="intent phrase, e.g. 工人與車")
    qq.add_argument("--limit", type=int, default=12, help="clamped 8-15, default 12")
    qq.add_argument("--out", default=None, help="JSON path (default <index>/queries/cli-<slug>.json)")
    qq.set_defaults(func=cmd_query)

    sl = sub.add_parser("list", help="list frozen director intents")
    sl.set_defaults(func=cmd_list)

    dd = sub.add_parser("doctor", help="check index files; exit 2 if query cannot run")
    dd.add_argument("--index", required=True, help="box root containing index/")
    dd.set_defaults(func=cmd_doctor)

    ix = sub.add_parser("index", help="build index/ from a local video folder")
    ix.add_argument("--input", required=True, help="folder of videos (mov/mp4/mkv/...)")
    ix.add_argument("--index", required=True, help="box root to write index/ into")
    ix.set_defaults(func=cmd_index)

    dm = sub.add_parser(
        "demo",
        help="generate synthetic footage and run split/index/doctor/query locally",
    )
    dm.add_argument(
        "--out",
        required=True,
        help="new or empty directory for all generated demo files",
    )
    dm.add_argument(
        "--intent",
        default="color test pattern",
        help="query text (default: color test pattern)",
    )
    dm.add_argument("--limit", type=int, default=8, help="clamped 8-15, default 8")
    dm.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
