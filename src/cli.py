#!/usr/bin/env python3
"""binquery v0 — local CLIP shortlist CLI. Not a pass."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from index_box import IndexError_, run_index  # noqa: E402
from intents import SPECS  # noqa: E402
from query import (  # noqa: E402
    LIMIT_DEFAULT,
    MissingIndex,
    doctor_index,
    dump_json,
    print_doctor,
    print_table,
    run_query,
)


def cmd_list(_args: argparse.Namespace) -> int:
    print(f"{'slug':<34} {'gate':<32} aliases")
    for spec in SPECS:
        aliases = ", ".join(spec.get("aliases") or [])
        print(f"{spec['slug']:<34} {spec['gate']:<32} {aliases}")
        print(f"  {spec['intent']}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
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
    report = doctor_index(Path(args.index).expanduser())
    print_doctor(report)
    return 0 if report["can_query"] else 2


def cmd_query(args: argparse.Namespace) -> int:
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="binquery",
        description="Local CLIP shortlist. Build a box with index, then doctor/query.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    qq = sub.add_parser("query", help="shortlist 8-15 clips for an intent")
    qq.add_argument("--index", required=True, help="box root containing index/")
    qq.add_argument("intent", help="intent phrase, e.g. 工人與車")
    qq.add_argument("--limit", type=int, default=LIMIT_DEFAULT, help="clamped 8-15, default 12")
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
