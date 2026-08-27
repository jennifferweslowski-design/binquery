# Test binquery on real footage

binquery is an early, MIT-licensed command-line tool that builds a local
OpenCLIP index of a video folder and returns a ranked shortlist for a sentence
query. It does not edit footage or export a finished cut.

We are looking for three editors or video makers to try version 0.3.0 and report
the honest result—including installation failures and irrelevant rankings. This
is a small usability pilot, not a request for stars, votes, testimonials, or
private footage.

## What you need

- Python 3.10 or newer;
- `ffmpeg` available on `PATH`;
- 20–100 short, non-client video clips that you are allowed to process locally;
- enough time for the synthetic demo and for indexing your clips.

The first run may download OpenCLIP model weights. Video processing, indexing,
and inference then run locally.

## 1. Install in a clean environment

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install binquery==0.3.0
.venv/bin/binquery --help
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install binquery==0.3.0
.venv\Scripts\binquery --help
```

If installation fails, stop there and use the report template below. The
failure is useful pilot evidence.

## 2. Run the synthetic demo

macOS or Linux:

```bash
.venv/bin/binquery demo --out /tmp/binquery-demo
```

Windows PowerShell:

```powershell
.venv\Scripts\binquery demo --out "$env:TEMP\binquery-demo"
```

The output directory must be new or empty. The demo generates synthetic clips
and runs `split → index → doctor → query`; it checks that the full pipeline runs,
not that semantic ranking is good.

## 3. Try one query on your own clips

Choose a small folder containing 20–100 short clips. Do not use client-confidential
material. Replace the example paths and query with your own:

macOS or Linux:

```bash
.venv/bin/binquery index --input ./my-clips --index ./binquery-pilot
.venv/bin/binquery doctor --index ./binquery-pilot
.venv/bin/binquery query --index ./binquery-pilot \
  "wide exterior shot with no people" \
  --limit 12 \
  --out ./binquery-pilot/query.json
```

Windows PowerShell:

```powershell
.venv\Scripts\binquery index --input .\my-clips --index .\binquery-pilot
.venv\Scripts\binquery doctor --index .\binquery-pilot
.venv\Scripts\binquery query --index .\binquery-pilot `
  "wide exterior shot with no people" `
  --limit 12 `
  --out .\binquery-pilot\query.json
```

Use a query for a shot you genuinely remember. Open the returned candidates and
judge them yourself. A bad shortlist is a valid and useful result.

## 4. Report the result

Copy this template into a GitHub issue or send it to the person who invited you:

```text
OS and version:
Python version:
ffmpeg version:
Install: PASS / FAIL
Synthetic demo: PASS / FAIL / NOT RUN
Approximate number of real clips:
Sanitized query:
Did any useful candidate appear? YES / NO / QUERY FAILED
Exact error text, with private paths and names removed:
One thing that was confusing:
```

Please do **not** send footage, extracted frames, index files, client names,
private paths, or screenshots containing confidential material. Do not publish
another person's feedback or identity without their permission.

GitHub: https://github.com/jennifferweslowski-design/binquery

PyPI: https://pypi.org/project/binquery/0.3.0/

## Maintainer evidence log

This section is for the maintainer, not a requirement for participants. Use an
anonymous identifier unless attribution is explicitly permitted.

| ID | Date | Environment | Demo | Real query | Useful candidate | Action | Public evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | | | | | | | |
| P2 | | | | | | | |
| P3 | | | | | | | |

Valid actions include improved installation guidance, a reproducible issue, a
verified fix, a regression test, or a release. A private message is not public
maintenance evidence by itself; the documented action it causes can be.

The pilot is complete after three independent environments have been attempted
and recorded honestly. It does not require three positive outcomes. One
reproducible failure that leads to a tested fix is stronger evidence than three
compliments.
