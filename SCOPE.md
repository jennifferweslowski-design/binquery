# binquery v0 範圍

本機 CLI。對已有素材盒 index 輸入意圖句，吐 8–15 條短名單 JSON。不是瀏覽器，不是自動成片，不當過關。

## 進 v0

1. 輸入：已建好的盒 index。最少要有 `index/clip.json`、`index/clip_vectors.npy`、`index/mechanical.json`。空鏡 gate 再讀 `index/empty_hard.json` 或 `index/motion.json` 的 `person_clip`。
2. 查詢：一句剪輯意圖。導演句原文凍結，可用短別名對上（工人與車、孤月）。
3. 輸出：8–15 條。每條 `path`、`score`、`gate`、`reasons`。可寫 JSON 檔，也可印 stdout。
4. gate 凍結，不重調公式：
   - `pictorial`：CLIP `visual_en`（可負向）+ 時長 +0.02 加分，不硬濾時長。
   - `clip_noun+no_person`：CLIP 名詞先找岩／雅丹，再硬濾 `person_clip < 0`。
   - `clip_noun+soft_person+fire_neg`：CLIP 名詞找孤月／石縫，`person_clip` 軟罰，火光負向壓 0308。
5. 大海道類查詢排除 0304／0305。
6. 介面：`binquery index --input <videos> --index <box>` 建盒；`query` 只編碼查詢句。
7. 可選：`binquery split` 用本機 ffmpeg 把一條長片切成時間格 clips（預設 `-c copy` segment，切在 keyframe）。不是 highlight、不是依靜音切、不是自動成片。

## 不進 v0

重抽幀、重算整庫 embedding、新雲端視覺 API、素材進倉庫、改導演句、當過關、NLE、美學分、口播轉寫、時間軸、GUI、highlight 偵測、YouTube/TikTok 自動 clip。

## 完成標準

倉庫只有程式 + README + 本頁。對兩個自備盒各跑通「工人與車」「孤月」。召回只報數字，不當過關。缺 index 就停。

## runtime／成本

Python 3 + `requirements.txt`（open_clip ViT-B-32 / laion2b_s34b_b79k、torch、numpy、pillow）。CPU。只編碼查詢句。輸出是短名單 JSON，不是成片。權重進 `$BINQUERY_CLIP_CACHE` 或 `~/.cache/binquery`。
