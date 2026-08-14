# binquery v0

本機 CLI。對已建好的素材盒 index 輸入一句意圖，吐 8–15 條短名單 JSON（path、score、gate、reasons）。

不是瀏覽器、不是自動成片、不當過關。只編碼查詢句，不重抽幀、不重算整庫 `clip_vectors.npy`。

## 安裝

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

CPU。模型是 OpenCLIP ViT-B-32 / `laion2b_s34b_b79k`。權重快取：

- `$BINQUERY_CLIP_CACHE`，或
- `~/.cache/binquery/open_clip`

第一次跑可能把權重下載進這個快取（本機檔，不是查詢 API）。之後可設 `BINQUERY_OFFLINE=1`。

Python 順序：`$BINQUERY_PYTHON` → `./.venv/bin/python` → `python3`。

## 用法

```
export BINQUERY_INDEX=./my-box

./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "<intent>" [--limit 12] [--out path.json]
./binquery list
```

`--index` 是盒根（內含 `index/`）。limit 預設 12，夾在 8–15。stdout 印短表，並寫 JSON（`--out` 或 `<index>/queries/cli-<slug>.json`）。

`doctor` 只檢查檔在不在、能不能讀。缺必備 index 就列檔名、exit 2，不假裝能查、不解包。

## 自備盒

素材和向量留在你自己的盒，不要拷進這個倉庫。

1. 盒根自己放，用 `--index` 或 `$BINQUERY_INDEX` 指過去。例如 `--index ./my-box`。
2. 盒根要有 `index/`，裡面最少三個檔：
   - `clip.json`（每幀路徑、時長、npy 列號）
   - `clip_vectors.npy`（已算好的 ViT-B-32 向量，列數對得上 clip.json）
   - `mechanical.json`（時長；欄位 `clips` 或 `items`）
3. 要跑空鏡 gate 再加一個 `person_clip` 來源：`empty_hard.json` 或 `motion.json`。沒有的話 pictorial 仍可查；雅丹硬濾會停，孤月軟罰當 0。
4. 換盒前先跑 `./binquery doctor --index "$BINQUERY_INDEX"`。MISS 就停，不要解包、不要重抽幀。
5. `.mov`、幀、整包素材留在盒裡。本倉庫只放程式和說明。`.gitignore` 已擋 `__pycache__`、`.venv`、`*.npy`、`*.mov`、`index/`。

## 例子

```
export BINQUERY_INDEX=./my-box
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "工人與車" --limit 12
./binquery query --index "$BINQUERY_INDEX" "孤月" --limit 12
```

凍結分數見 [test-run.md](test-run.md)（相對檔名，不含素材）。

## 禁止

雲端視覺查詢 API、unpack 素材進本倉庫、重抽幀、重算整庫向量、把影片或 index 向量提交上來。
