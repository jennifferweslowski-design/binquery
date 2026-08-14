# 怎麼參與 binquery

先 issue，再 PR。不要交素材。

## Issue

用 GitHub 模板開：

- **Bug**：哪條指令、期望、實際、`binquery doctor --index <盒>` 的出口碼
- **文檔**：哪一頁、哪段不清楚

不要在 issue 貼影片、npy、整份 index、或任何授權素材。相對檔名和分數可以。

## PR

1. Fork，對 `main` 開 PR。
2. 只改程式或說明。不要加 `.mov`、`.npy`、`index/`、幀、或素材包。
3. `.gitignore` 已擋這些；PR 裡出現就會被退。
4. 不改凍結查詢公式，除非 issue 先說清楚。
5. 本地先：

```
python3 -m venv .venv
.venv/bin/pip install -e .
export BINQUERY_INDEX=./my-box
binquery doctor --index "$BINQUERY_INDEX"
```

`doctor` 綠（exit 0）再查。缺檔是 exit 2，不要假裝能查。

本機還要 `ffmpeg` / `ffprobe`。權重快取在 `$BINQUERY_CLIP_CACHE` 或 `~/.cache/binquery/open_clip`。

## 不要交上來

`.mov`、`.mp4`、`.npy`、`index/`、幀、素材包、帳號、本機絕對路徑。
