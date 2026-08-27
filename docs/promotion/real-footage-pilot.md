# binquery real-footage pilot

Prepared on 2026-08-27. This is an outreach and evidence-collection plan, not a
claim that search quality has already been validated on real editing projects.

## Goal

Recruit three independent editors or video makers to install the published
package, run the synthetic demo, and then try one sentence query against a small
folder of their own non-client footage.

The useful outcome is not a star. It is a reproducible installation report, a
documented limitation, or a public issue that leads to a verified maintenance
action.

## Who counts as a pilot participant

- They are not the repository owner and did not work on binquery.
- They install the public PyPI release in their own environment.
- They run `binquery demo` before using their own footage.
- They test a small folder they are allowed to process locally.
- They report what happened, including failures or irrelevant rankings.

Friends can participate, but they must report their real result. Do not ask for a
star, vote, testimonial, or positive wording.

## Direct invitation

### English

> I maintain an early open-source CLI called binquery. It builds a local index of
> a video folder and returns a ranked clip shortlist for a sentence query. It does
> not edit the footage. Processing runs locally; the first run may download model
> weights.
>
> I am looking for three people willing to test the published package on a small
> folder of non-client footage and tell me where it fails. Please run the synthetic
> demo first, then try one real query. I need the honest result, including bad
> rankings or installation errors; I am not asking for a star or endorsement.
>
> GitHub: https://github.com/jennifferweslowski-design/binquery
>
> PyPI: https://pypi.org/project/binquery/0.3.0/

### 繁體中文

> 我在維護一個早期開源 CLI：binquery。它會在本機替影片資料夾建立索引，
> 再依一句描述回傳排序後的候選短名單；它不剪輯。處理在本機執行，首次
> 使用可能下載模型權重。
>
> 我想找 3 位願意實測的人：先跑合成素材 demo，再用一小份可以自行處理、
> 不含客戶機密的素材測一個真實查詢。我要的是誠實結果，包括安裝失敗、
> 排名不準或根本不適合你的工作流；不需要幫忙按星或寫好評。
>
> GitHub: https://github.com/jennifferweslowski-design/binquery
>
> PyPI: https://pypi.org/project/binquery/0.3.0/

## Participant steps

Use a clean virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install binquery==0.3.0
.venv/bin/binquery demo --out /tmp/binquery-demo
```

If the demo succeeds, follow the README to index a small local video folder and run
one query that reflects a shot the participant actually remembers. The first run
may download OpenCLIP model weights.

## What to report

Do not request footage, extracted frames, index files, client names, or private
paths. Ask for only:

- operating system and version;
- Python and ffmpeg versions;
- whether installation and the synthetic demo completed;
- a sanitized version of the real query;
- approximate candidate-pool size;
- whether any useful candidate appeared in the returned shortlist;
- exact error text for a failure, with private paths and names removed;
- permission before quoting or publicly attributing any feedback.

Convert reproducible defects into GitHub issues. Keep private feedback private
unless the participant explicitly agrees otherwise.

## Evidence log

Record one row per participant. Use an anonymous identifier unless attribution is
explicitly permitted.

| ID | Date | Environment | Demo | Real query | Useful candidate | Action | Public evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | | | | | | | |
| P2 | | | | | | | |
| P3 | | | | | | | |

Valid actions include: documented installation guidance, opened issue, verified
fix, regression test, or release. A private message by itself is not public proof;
the maintenance action it causes can be.

## Completion rule

The pilot is complete when three independent environments have been attempted and
each result is recorded honestly. Success does not require three positive results.
One reproducible failure that leads to a tested fix is stronger maintenance
evidence than three compliments.
