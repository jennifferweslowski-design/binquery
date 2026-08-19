# binquery v0

剪輯助理的痛是盒很大：幾百條片子，一句意圖要立刻拿到 8–15 條短名單，而不是把整庫翻一遍。

本機 CLI。對自己的影片資料夾建盒，再用一句意圖撈短名單 JSON（path、score、gate、reasons）。不是瀏覽器、不是自動成片。查詢只編碼句子，不重抽幀、不重算整庫。建盒用本機 ffmpeg + 本機 OpenCLIP。

## 安裝

```
python3 -m venv .venv
.venv/bin/pip install -e .
```

也可以 `pip install -r requirements.txt` 再跑 `./binquery`。

還要本機有 `ffmpeg` / `ffprobe`。

CPU。模型是 OpenCLIP ViT-B-32 / `laion2b_s34b_b79k`。權重快取：

- `$BINQUERY_CLIP_CACHE`，或
- `~/.cache/binquery/open_clip`

第一次跑可能把權重下載進這個快取（本機檔，不是查詢 API）。之後可設 `BINQUERY_OFFLINE=1`。

Python 順序：`$BINQUERY_PYTHON` → `./.venv/bin/python` → `python3`。

## Agent Skill

給 agent 用：一句剪輯意圖 → 本機短名單。裝這個倉庫的 Skill：

```
npx -y skills add jennifferweslowski-design/binquery
```

或把 `skills/binquery/` 拷進專案的 `.agents/skills/binquery` 或 `.claude/skills/binquery`（夾裡要有 `SKILL.md`）。

這只裝給 agent 的說明，不會裝 Python 套件。CLI 仍要 clone 後 `pip install -e .`。不在 PyPI，不要寫 `pip install binquery`。

## 用法

```
export BINQUERY_INDEX=./my-box

./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "<intent>" [--limit 12] [--out path.json]
./binquery list
```

`--input` 是你自己的影片資料夾。`--index` 是盒根（會寫入 `index/`）。limit 預設 12，夾在 8–15。

`query` 用一句 pictorial 意圖回 8–15 條短名單。CLIP 看靜幀，長得像的會排在一起（例如白天岩縫透天，分數可以像月亮）。長片仍可能排高；時長是加分，不是硬切。人還是要看。這是短名單，不是自動剪輯。

`doctor` 只檢查檔在不在、能不能讀。缺必備 index 就列檔名、exit 2，不假裝能查、不解包。

## 自備盒

1. 影片放在你自己的資料夾，不要拷進這個倉庫。
2. 建盒：

```
export BINQUERY_INDEX=./my-box
./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
```

會用本機 ffmpeg 每條抽 3 幀（約 1s／中點／結尾前 1s），再用本機 ViT-B-32 算向量，寫出：

- `index/clip.json`
- `index/clip_vectors.npy`
- `index/mechanical.json`
- `index/empty_hard.json`（`person_clip`：每條 max(cos 人 − cos 空)，空鏡 gate 直接讀。不必自己加 json。）
- `index/motion.json`（`motion_label`：lock／pan／handheld／moving；coarse 三幀幀差＋phaseCorrelate。查詢讀這份，不必自己加。）

3. 先 `doctor`，再 `query`。MISS 就停。
4. pictorial 不需要 person。空鏡 gate 用 `person_clip`。鏡頭運動用 `motion_label`（lock／pan／handheld）。
5. `.mov`、幀、向量留在盒裡。本倉庫只放程式和說明。`.gitignore` 已擋 `__pycache__`、`.venv`、`*.npy`、`*.mov`、`index/`。

## 例子

```
export BINQUERY_INDEX=./my-box
./binquery index --input ./my-videos --index "$BINQUERY_INDEX"
./binquery doctor --index "$BINQUERY_INDEX"
./binquery query --index "$BINQUERY_INDEX" "工人與車" --limit 12
```

凍結分數見 [test-run.md](test-run.md)（相對檔名，不含素材）。

## 禁止

雲端視覺查詢 API、unpack 素材進本倉庫、把影片或 index 向量提交上來。

## CI

推 `main` 或開 PR 時，[ci](.github/workflows/ci.yml) 在官方 runner 上 lavfi 自製 3 條短片，跑 `index` → `doctor`。素材和 index 只活在 runner，不進倉庫。

怎麼提 issue／PR 見 [CONTRIBUTING.md](CONTRIBUTING.md)。
