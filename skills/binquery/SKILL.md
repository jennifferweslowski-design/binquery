---
name: binquery
description: Local Python CLI that can time-grid split one long local video into a folder, index that folder, then answer one editing-intent sentence with an 8–15 clip shortlist (path, score, gate, reasons). Use when the user wants a local footage shortlist from an edit intent, has one long recording to break into clips, or asks to run binquery split, index, doctor, query, or list. Split is ffmpeg segment, not highlight detection. Query encodes only the sentence. Not a browser, not an auto-editor, not a cloud vision API, not on PyPI.
license: MIT
compatibility: Local machine with Python 3.10+, ffmpeg, ffprobe, and OpenCLIP. Install by cloning this repo and running pip install -e . — not on PyPI.
---

# binquery

Local CLIP shortlist CLI. Optionally time-grid split one long local file, index a video folder the user already has, then query with one sentence. Return 8–15 clips: `path`, `score`, `gate`, `reasons`. People still watch. This is not a cut.

## When to use

Use this skill when the user wants a **local footage shortlist from an edit intent**, has **one long recording to break into clips**, or asks to run `binquery` `split` / `index` / `doctor` / `query` / `list`.

That includes **this kind of ask** (public editor talk; not a claim we ran it):

- Many separately-cut scenes headed for a Premiere master, and the original scene order is getting lost. For each scene, pass **one** visual-intent sentence to `query`. Keep the **query order** as the user's sequence memory. Humans still watch. binquery does not paste into Premiere, assemble a timeline, restore NLE markers, or read original sequence from the media files. (r/VideoEditing, 2026-08-16: [How can I paste a lot of scenes in the master](https://www.reddit.com/r/VideoEditing/comments/1vppcap/how_can_i_paste_a_lot_of_scenes_in_the_master/))
- Trailer work from the user's own rushes/dailies folder, not a locked master. Index that folder, then one trailer-intent sentence → 8–15 clip shortlist. This is not an auto-cut trailer, and we have not run this on a real rushes bin. (r/editors, 2026-08-16: [Do trailer editors typically work from raw rushes](https://www.reddit.com/r/editors/comments/1vq6rbv/do_trailer_editors_typically_work_from_raw_rushes/))
- A small streamer with one long recording who does not know how to break it into postable clips. `split` that file on a time grid (local ffmpeg segment), `index` the clip folder, `doctor`, then one "what kind of clip" sentence → 8–15 shortlist. This is not highlight detection, not silence-based cuts, and not auto-clip for YouTube/TikTok. We have not run this on a real VOD. (r/NewTubers, 2026-08-17: [How do small streamers handle clipping workflows](https://www.reddit.com/r/NewTubers/comments/1vqdvah/how_do_small_streamers_handle_clipping_workflows/))

Do not use this skill to:

- browse or stream video
- auto-edit, assemble a timeline, or export a finished piece
- paste into Premiere, restore NLE markers, or recover scene order from the files
- auto-cut a trailer
- detect highlights, cut on silence, or auto-clip for YouTube/TikTok
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
2. If they have **one long file** instead of a folder of clips: **split** it first (time grid). Then **index** that clip folder into a box.
3. If they already have a folder of clips: **index** that folder into a box.
4. **doctor** the box. If a required file is `MISS`, **stop**. Do not query. Do not unpack. Do not pretend.
5. Optionally **list** frozen director intents.
6. **query** with one sentence. Show the shortlist. The user watches.

```
export BINQUERY_INDEX=./my-box

./binquery split --input ./long.mp4 --out ./split-out --seconds 8
./binquery index --input ./split-out --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "<intent>" [--limit 12] [--out path.json]
./binquery list
```

`split --input` is one local video file. `split --out` is an empty or new folder next to the user's file (default `<input-dir>/split-out`). Do not write clips into this repo. `--seconds` defaults to 8 and is clamped to 4–60. Default split is `-c copy`; cuts land on keyframes, so duration is not exact. `--reencode` is optional (local libx264+aac) for nearer-exact duration.

`--input` for `index` is the user's video folder (`.mov` / `.mp4` / `.mkv` / `.m4v` / `.avi` / `.webm`) — the split folder, or any folder they already have. `--index` is the box root (writes `index/` under it). `--limit` defaults to 12 and is clamped to 8–15.

Example from the project README (frozen director alias; `list` has the rest):

```
export BINQUERY_INDEX=./my-box
./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "工人與車" --limit 12
```

Unknown sentences still run as unmatched pictorial (`resolve_query`). Do not rewrite the frozen Chinese director lines in `src/binquery/intents.py`. Do not add SPECS.

## Example intents

Pass **one unmatched pictorial sentence** per `query`. These are generic examples for an agent to type — not frozen director lines, not golds, not a claim we ranked a real bin.

Scene-sequence style (scene name or one-line visual per scene; Chinese or English):

```
./binquery query --index "$BINQUERY_INDEX" "scene 2 empty hallway lock-off"
./binquery query --index "$BINQUERY_INDEX" "kitchen table medium two people"
./binquery query --index "$BINQUERY_INDEX" "第三場：傍晚空街遠景"
```

Rushes / trailer style (one intent → shortlist from the user's own rushes folder):

```
./binquery query --index "$BINQUERY_INDEX" "cold open wide empty night"
./binquery query --index "$BINQUERY_INDEX" "close-up reaction pause"
./binquery query --index "$BINQUERY_INDEX" "locked-off receding wide"
```

Long-recording / clip-folder style (after `split` + `index` of that folder; unmatched pictorial, not highlight detection):

```
./binquery query --index "$BINQUERY_INDEX" "highlight reaction close-up"
./binquery query --index "$BINQUERY_INDEX" "talking to chat medium"
```

Each call returns 8–15 rows: `path`, `score`, `gate`, `reasons`. CLIP ranks stills that look alike. Humans still watch.

## When the user has many scenes / rushes

1. Videos stay in the user's own folder. Do not copy footage into this repo.
2. `index` that folder into a box, then `doctor`. If a required file is `MISS`, **stop**.
3. One `query` per scene (scene-sequence), or one trailer-intent sentence (rushes).
4. Show each shortlist. Keep the **query order** as the user's sequence memory. The box does not remember Premiere order.
5. The user watches. Do not assemble a timeline.

This is not Premiere, not auto-edit, and not a 500-clip run.

## When the user has one long recording

1. The long file stays where the user already has it. Do not copy it into this repo.
2. `split` that file into an empty or new folder (default next to the file). Time grid only.
3. `index` that folder, then `doctor`. If a required file is `MISS`, **stop**.
4. One "what kind of clip" sentence to `query`. Show the shortlist.
5. The user watches. Do not auto-post to YouTube/TikTok.

This is not highlight detection and not a real-VOD run. CI lavfi 3 clips is not this demo.

## What we have not done

We have **not** run `query` against a ~500-clip real bin for these asks. We have **not** run `split` on a real streamer VOD.

CI can lavfi a 30s test pattern, `split` it into a few parts, then `index` → `doctor` those parts. That is a mechanical ffmpeg check. It is not a clipping-workflow demo and not a real VOD.

A real demo needs the user's own long file (then `split` → `index` → `doctor` → `query`), or a local video folder plus a local box (`BINQUERY_INDEX`). If they have no long file and no box, say exactly:

需要本機長片先 split 再 index 成盒，或本機影片資料夾先 index 成盒，才能演示。不要假裝對過真 bin，也不要假裝對真實況跑過。

Do not invent star counts, downloads, user counts, or screenshots. Do not claim we pasted into Premiere, auto-cut a trailer, detected highlights, or ran this on a real VOD.

## Commands

### split

Time-grid one local video into a folder of clips. Requires local `ffmpeg` / `ffprobe` on PATH (same as `index`).

- `--input` one local video file (the long take)
- `--out` empty or new directory (default `<input-dir>/split-out`, next to the user's file; never the program tree)
- `--seconds` target length (default 8, clamped 4–60)
- default: `ffmpeg -c copy -f segment -reset_timestamps 1` — cuts land on keyframes, so duration is not exact
- `--reencode`: local libx264 + aac for nearer-exact duration

Prints each output path and ffprobe duration. Exit non-zero if ffmpeg is missing, the input is missing, `--out` is not empty/new, or ffmpeg fails.

Does **not** index. Does **not** query. Does **not** unpack archives. Does **not** call a cloud API. Does **not** detect highlights or cut on silence.

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
- `split` is a time grid. Not highlights. Not silence cuts. Not auto-clip.
- Query encodes the sentence only.
- First `index` may download OpenCLIP weights into the local cache above.
- `doctor` `MISS` on a required file means stop.
- Do not commit footage, frames, `*.npy`, or `index/` into this repo.
