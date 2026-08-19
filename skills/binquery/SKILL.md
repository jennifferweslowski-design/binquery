---
name: binquery
description: Local Python CLI that indexes your own video folder, then answers one editing-intent sentence with an 8–15 clip shortlist (path, score, gate, reasons). Use when the user wants a local footage shortlist from an edit intent, or asks to run binquery index, doctor, query, or list. Query encodes only the sentence. Not a browser, not an auto-editor, not a cloud vision API, not on PyPI.
license: MIT
compatibility: Local machine with Python 3.10+, ffmpeg, ffprobe, and OpenCLIP. Install by cloning this repo and running pip install -e . — not on PyPI.
---

# binquery

Local CLIP shortlist CLI. Index a video folder the user already has, then query with one sentence. Return 8–15 clips: `path`, `score`, `gate`, `reasons`. People still watch. This is not a cut.

## When to use

Use this skill when the user wants a **local footage shortlist from an edit intent**, or asks to run `binquery` `index` / `doctor` / `query` / `list`.

Do not use this skill to:

- browse or stream video
- auto-edit, assemble a timeline, or export a finished piece
- call a cloud vision / video API
- re-extract frames or re-embed the library on query
- install from PyPI (`pip install binquery` is wrong)

## Install the CLI (not PyPI)

binquery is **not on PyPI**. Do not write `pip install binquery`.

Clone this repo, then editable-install:

```
python3 -m venv .venv
.venv/bin/pip install -e .
```

Or `pip install -r requirements.txt` and run `./binquery` from the clone.

Also required on PATH: `ffmpeg` and `ffprobe`.

After `pip install -e .`, the command is `binquery`. From the clone without installing the script, use `./binquery`. Same subcommands either way.

Python lookup for `./binquery`: `$BINQUERY_PYTHON` → `./.venv/bin/python` → `python3`.

CPU only. Model: OpenCLIP ViT-B-32 / `laion2b_s34b_b79k`.

## Weights cache (first run)

Cache directory:

- `$BINQUERY_CLIP_CACHE`, or
- `~/.cache/binquery/open_clip`

`index` may download OpenCLIP weights **into that local cache** on the first run. That is a local file cache, not a query API.

After the cache is populated, `BINQUERY_OFFLINE=1` is safe. `query` loads CLIP in offline mode and only encodes the sentence. If the cache is empty, run `index` first (or unset `BINQUERY_OFFLINE` once so weights can land in the cache). Do not call a cloud vision API as a fallback.

## Workflow

1. Videos stay in the user's own folder. Do not copy footage into this repo. Do not unpack archives into the repo.
2. **index** the folder into a box.
3. **doctor** the box. If a required file is `MISS`, **stop**. Do not query. Do not unpack. Do not pretend.
4. Optionally **list** frozen director intents.
5. **query** with one sentence. Show the shortlist. The user watches.

```
export BINQUERY_INDEX=./my-box

./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "<intent>" [--limit 12] [--out path.json]
./binquery list
```

`--input` is the user's video folder (`.mov` / `.mp4` / `.mkv` / `.m4v` / `.avi` / `.webm`). `--index` is the box root (writes `index/` under it). `--limit` defaults to 12 and is clamped to 8–15.

Example from the project README:

```
export BINQUERY_INDEX=./my-box
./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "工人與車" --limit 12
```

## Commands

### index

Build `index/` from a local video folder. Uses local ffmpeg (3 stills per clip: about 1s / midpoint / 1s before end) and local OpenCLIP. Writes:

- `index/clip.json`
- `index/clip_vectors.npy`
- `index/mechanical.json`
- `index/empty_hard.json` (`person_clip`)
- `index/motion.json` (`motion_label`: lock / pan / handheld / moving)

Does not unpack archives. Does not write footage into the program tree. Does not call a cloud vision API.

### doctor

Checks that index files exist and can be read. Prints `OK` or `MISS` per file, then `can_query: yes|no`.

Required (query cannot run without them): `clip.json`, `clip_vectors.npy`, `mechanical.json`.

`empty_hard.json` and `motion.json` supply `person_clip`. If both are missing, pictorial queries can still run; noun empty-gates that need `person_clip` will fail or soften as the CLI reports.

Exit `0` if `can_query` is yes. Exit `2` if required files are `MISS` or unreadable.

**If doctor prints `MISS` on a required file: stop.** Do not query. Do not unpack. Tell the user to run `index` (or fix the box path).

### query

One intent sentence in, 8–15 rows out. Encodes **only the query text**. Does not re-extract frames. Does not recompute `clip_vectors.npy`.

Prints a table (`path`, duration, `score`) and writes JSON (default `<index>/queries/cli-<slug>.json`, or `--out`). Each result includes `path`, `score`, `gate`, `reasons`.

CLIP ranks stills that look alike. Near-misses can sit together (for example a daytime rock crevice can score like a moon). Long clips can still rank high: duration is a `+0.02` bonus, not a hard cut. Humans still watch. This is a shortlist, not an auto-edit.

Unknown sentences still run (pictorial gate, raw text). Known director lines and aliases are listed by `list`.

### list

Print frozen director intents: slug, gate, aliases, and the intent sentence. Use this when the user asks what queries exist. Do not rewrite those Chinese sentences.

## Output contract

Show the shortlist. Do not treat scores as a pass/fail. Do not assemble an edit. Do not claim the tool found "the" shot.

Do not invent star counts, download counts, or user counts. Do not add screenshots.

## Hard limits

- Local only. User's disk, user's ffmpeg, user's OpenCLIP cache.
- No cloud vision API. No substitute hosted embedder.
- Not a browser. Not an NLE. Not auto-edit.
- Query encodes the sentence only.
- First `index` may download OpenCLIP weights into the local cache above.
- `doctor` `MISS` on a required file means stop.
- Do not commit footage, frames, `*.npy`, or `index/` into this repo.
