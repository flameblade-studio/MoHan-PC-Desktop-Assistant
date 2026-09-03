# 分層美術產線／分层美术产线／Layered art pipeline／レイヤー美術パイプライン

## 繁體中文

這是一套從 scratchpad 收進 repo 的可重現工具，負責半身精靈對位、說話／眨眼變體、參考圖裁切、差分抽層、妝容三槽切分、補鞋併入、去洋紅溢色與契約檔名組裝。

### 不可繞過的輸入邊界

- 每個檔案的輸入、輸出、模型與設定檔路徑都由 CLI 參數傳入；模組沒有使用者電腦的絕對路徑。
- 參考圖的第二個位置參數是 repo-relative git path，不是工作樹路徑。必須同時傳 `--repo .` 與 `--reference-ref <commit-or-tag>`；工具以 `git show <ref>:<path>` 寫入暫存檔後才讀取。
- `assets/` 不會被當成目前工作樹參考來源。若要重跑，請固定同一個提交並把產出寫到明確的工作目錄；不要把輸出目錄指向既有正式素材。
- 所有透明像素的 RGB 會歸零；對位、縮放與配準均先預乘 alpha，再還原 straight alpha。

### 步驟、輸入與輸出

1. `align_to_template`：輸入本地生成的洋紅圖與 git 鎖定的半身模板，YuNet 五點估算相似變換，輸出 1254×1254 BGRA 與可選 JSON 報告。
2. `derive_variants`：將已對位圖的嘴框或眼框貼到母圖，矩形外保持逐像素不變。
3. `align_ref_to_base`：用 git 取出的樣式參考圖對齊 base 的臉中心與腳底，輸出供後續編輯使用的 BGR 洋紅圖。
4. `make_ref_crops`：把對齊參考切成 `garment`、`headwear`，有臉時另切 `face`。
5. `extract_layers`：逐步差分、形態學清理、alpha 羽化、局部配準、去溢色；L1 另依 safe-regions 輸出互斥的 `eyes`／`lips`／`cheeks`，可選的鞋步併入 `L2_garment`。
6. `assemble_set`：依既有 `domain.companion_animation_contract` 的檔名與矩形契約組出 idle、blink、speaking、viseme 與表情變體。
7. `flatten_magenta`：把 BGRA 結果鋪回不透明洋紅 BGR，作為編輯模式輸入。

### 重跑範例

以下命令只使用明確的相對路徑；`<commit>` 必須是包含參考檔的提交。第二個參數 `assets/...` 是 git 內的 path，不會從工作樹讀檔。

```powershell
python -m tools.art_pipeline.align_to_template generated.png assets/expressions/layered/front_base.png work/aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx --report work/aligned.json
python -m tools.art_pipeline.align_ref_to_base base.png assets/pose-atlas/v4-working/yaw+000-pitch+00.png work/ref.aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.make_ref_crops work/ref.aligned.png work/ref --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.extract_layers work/halfbody/base.magenta.png full_yaw+000-pitch+00 --source-dir work/halfbody/out --output-root work/layers/out --model assets/vision-models/face_detection_yunet_2023mar.onnx --safe-regions assets/makeup-safe-regions.json
python -m tools.art_pipeline.assemble_set work/expressions --input-dir work/halfbody/out
python -m tools.art_pipeline.derive_variants speech work/expressions/happy.png work/halfbody/out/bare_speaking_cheek.keyed.png happy work/expressions/happy_speech_mid.png
python -m tools.art_pipeline.flatten_magenta work/aligned.png work/aligned.magenta.png
python -m pytest -q tests/test_art_pipeline.py
```

`constants.py` 集中記錄畫布尺寸、鍵色門檻、羽化、形態學、臉部安全區、補鞋比例與連通塊門檻；每組旁邊都有 scratchpad 來源及量測依據。改數值時要同步更新回歸測試與本說明。

## 简体中文

这是一套从 scratchpad 纳入 repo 的可复现工具，负责半身精灵对位、说话／眨眼变体、参考图裁切、差分拆层、妆容三槽切分、补鞋合并、去洋红溢色和契约文件名组装。

### 不可绕过的输入边界

- 每个文件的输入、输出、模型和配置文件路径都通过 CLI 参数传入；模块不使用用户电脑的绝对路径。
- 参考图的第二个位置参数是 repo-relative git path，而不是工作树路径。必须同时传 `--repo .` 与 `--reference-ref <commit-or-tag>`；工具通过 `git show <ref>:<path>` 写入临时文件后才读取。
- `assets/` 不会被作为当前工作树的参考来源。重跑时固定同一个提交并将产出写入明确的工作目录；不要将输出目录指向已有正式素材。
- 所有透明像素的 RGB 均归零；对位、缩放和配准都先预乘 alpha，再还原为 straight alpha。

### 步骤、输入与输出

1. `align_to_template`：输入本地生成的洋红图和由 git 锁定的半身模板，使用 YuNet 五点估算相似变换，输出 1254×1254 BGRA 以及可选 JSON 报告。
2. `derive_variants`：将已对位图的嘴框或眼框贴到母图，矩形外保持逐像素不变。
3. `align_ref_to_base`：使用 git 取出的样式参考图对齐 base 的脸部中心和脚底，输出供后续编辑使用的 BGR 洋红图。
4. `make_ref_crops`：将对齐后的参考裁成 `garment`、`headwear`；包含脸部时另切 `face`。
5. `extract_layers`：逐步差分、形态学清理、alpha 羽化、局部配准、去溢色；L1 另按 safe-regions 输出互斥的 `eyes`／`lips`／`cheeks`，可选的鞋步合并到 `L2_garment`。
6. `assemble_set`：按既有 `domain.companion_animation_contract` 的文件名和矩形契约组装 idle、blink、speaking、viseme 及表情变体。
7. `flatten_magenta`：将 BGRA 结果铺回不透明洋红，作为编辑模式输入。

### 重跑示例

以下命令仅使用明确的相对路径；`<commit>` 必须是包含参考文件的提交。第二个参数 `assets/...` 是 git 内的 path，不会从工作树读取文件。

```powershell
python -m tools.art_pipeline.align_to_template generated.png assets/expressions/layered/front_base.png work/aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx --report work/aligned.json
python -m tools.art_pipeline.align_ref_to_base base.png assets/pose-atlas/v4-working/yaw+000-pitch+00.png work/ref.aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.make_ref_crops work/ref.aligned.png work/ref --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.extract_layers work/halfbody/base.magenta.png full_yaw+000-pitch+00 --source-dir work/halfbody/out --output-root work/layers/out --model assets/vision-models/face_detection_yunet_2023mar.onnx --safe-regions assets/makeup-safe-regions.json
python -m tools.art_pipeline.assemble_set work/expressions --input-dir work/halfbody/out
python -m tools.art_pipeline.derive_variants speech work/expressions/happy.png work/halfbody/out/bare_speaking_cheek.keyed.png happy work/expressions/happy_speech_mid.png
python -m tools.art_pipeline.flatten_magenta work/aligned.png work/aligned.magenta.png
python -m pytest -q tests/test_art_pipeline.py
```

`constants.py` 集中记录画布尺寸、键色阈值、羽化、形态学、脸部安全区、补鞋比例和连通块阈值；每组旁边都有 scratchpad 来源和测量依据。修改数值时要同步更新回归测试与本说明。

## English

This is the reproducible repo version of the scratchpad layered-art line. It covers half-body alignment, speech/blink variants, reference alignment and crops, differential layer extraction, mutually exclusive makeup slots, shoe merging, despill, and contractual expression filenames.

### Input boundaries that must not be bypassed

- Pass every file input, output, model, and configuration path through CLI arguments; the module contains no absolute path tied to a user's computer.
- The second positional argument for a reference image is a repo-relative git path, not a worktree path. Pass `--repo .` and `--reference-ref <commit-or-tag>` together; the tool materializes it with `git show <ref>:<path>` in a temporary directory before reading it.
- Never treat `assets/` as a reference source in the current worktree. For a rerun, pin the same commit and write outputs to an explicit work directory; do not point the output directory at existing formal assets.
- Zero the RGB channels of every transparent pixel; perform alignment, resizing, and registration with premultiplied alpha before restoring straight alpha.

### Steps, inputs, and outputs

1. `align_to_template`: Read the locally generated magenta image and git-pinned half-body template, estimate a similarity transform from five YuNet points, and write 1254×1254 BGRA plus an optional JSON report.
2. `derive_variants`: Paste the mouth or eye rectangle from the aligned image onto the master; keep every pixel outside the rectangle unchanged.
3. `align_ref_to_base`: Use the git-materialized style reference to align the face center and foot baseline to base, then write a BGR magenta image for downstream editing.
4. `make_ref_crops`: Cut the aligned reference into `garment` and `headwear`, and also cut `face` when a face is present.
5. `extract_layers`: Compute stepwise differences, clean morphologically, feather alpha, locally register, and despill; for L1 also write mutually exclusive `eyes`／`lips`／`cheeks` under safe-regions, with an optional shoe-step merge into `L2_garment`.
6. `assemble_set`: Assemble idle, blink, speaking, viseme, and expression variants under the existing `domain.companion_animation_contract` filename and rectangle contract.
7. `flatten_magenta`: Flatten the BGRA result back onto opaque magenta for use as editing-mode input.

### Rerun example

Use only explicit relative paths in the commands below; `<commit>` must contain the reference file. The second argument `assets/...` is a path inside git and is never read from the worktree.

```powershell
python -m tools.art_pipeline.align_to_template generated.png assets/expressions/layered/front_base.png work/aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx --report work/aligned.json
python -m tools.art_pipeline.align_ref_to_base base.png assets/pose-atlas/v4-working/yaw+000-pitch+00.png work/ref.aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.make_ref_crops work/ref.aligned.png work/ref --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.extract_layers work/halfbody/base.magenta.png full_yaw+000-pitch+00 --source-dir work/halfbody/out --output-root work/layers/out --model assets/vision-models/face_detection_yunet_2023mar.onnx --safe-regions assets/makeup-safe-regions.json
python -m tools.art_pipeline.assemble_set work/expressions --input-dir work/halfbody/out
python -m tools.art_pipeline.derive_variants speech work/expressions/happy.png work/halfbody/out/bare_speaking_cheek.keyed.png happy work/expressions/happy_speech_mid.png
python -m tools.art_pipeline.flatten_magenta work/aligned.png work/aligned.magenta.png
python -m pytest -q tests/test_art_pipeline.py
```

`constants.py` centralizes canvas dimensions, key-color thresholds, feathering, morphology, face safe regions, shoe-zone ratios, and connected-component thresholds; every group includes scratchpad sources and measurement notes. Update the regression tests and this document whenever a value changes.

## 日本語

これは scratchpad から repo に取り込んだ再現可能なレイヤー美術工程です。半身スプライトの位置合わせ、発話／まばたき差分、参照画像の位置合わせと切り出し、差分レイヤー抽出、相互排他的なメイク三スロット、靴の統合、マゼンタの色かぶり除去、正式な表情ファイル名を扱います。

### バイパスできない入力境界

- 各ファイルの入力、出力、モデル、設定ファイルのパスは CLI 引数で渡してください。モジュールに利用者の PC 固有の絶対パスはありません。
- 参照画像の 2 番目の位置引数は repo-relative git path であり、作業ツリーのパスではありません。`--repo .` と `--reference-ref <commit-or-tag>` を同時に指定してください。ツールは `git show <ref>:<path>` で一時ファイルへ取り出してから読み込みます。
- `assets/` を現在の作業ツリーの参照元として扱いません。再実行する場合は同じコミットを固定し、明示した作業ディレクトリに出力してください。既存の正式素材を出力先に指定しないでください。
- 透明画素の RGB はすべてゼロにしてください。位置合わせ、リサイズ、登録は premultiplied alpha で実施してから straight alpha に戻します。

### 手順、入力、出力

1. `align_to_template`：ローカルで生成したマゼンタ画像と git で固定した半身テンプレートを入力し、YuNet の 5 点から相似変換を推定して、1254×1254 BGRA と任意の JSON レポートを出力します。
2. `derive_variants`：位置合わせ済み画像の口または目の矩形を母画像へ貼り付け、矩形の外側を画素単位で変更しません。
3. `align_ref_to_base`：git から取り出したスタイル参照画像を使って顔の中心と足元を base に合わせ、後続の編集用に BGR マゼンタ画像を出力します。
4. `make_ref_crops`：位置合わせ済みの参照を `garment`、`headwear` に切り出し、顔がある場合は `face` も切り出します。
5. `extract_layers`：段階的な差分、形態学的なクリーニング、alpha のフェザー、局所的な位置合わせ、色かぶり除去を行います。L1 では safe-regions に基づき、相互排他的な `eyes`／`lips`／`cheeks` も出力し、必要に応じて靴の工程を `L2_garment` に統合します。
6. `assemble_set`：既存の `domain.companion_animation_contract` にあるファイル名と矩形の契約に従い、idle、blink、speaking、viseme、表情バリエーションを組み立てます。
7. `flatten_magenta`：BGRA の結果を不透明なマゼンタへ戻し、編集モードの入力にします。

### 再実行例

以下のコマンドは明示した相対パスだけを使用します。`<commit>` は参照ファイルを含むコミットでなければなりません。2 番目の引数 `assets/...` は git 内の path であり、作業ツリーからファイルを読みません。

```powershell
python -m tools.art_pipeline.align_to_template generated.png assets/expressions/layered/front_base.png work/aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx --report work/aligned.json
python -m tools.art_pipeline.align_ref_to_base base.png assets/pose-atlas/v4-working/yaw+000-pitch+00.png work/ref.aligned.png --repo . --reference-ref <commit> --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.make_ref_crops work/ref.aligned.png work/ref --model assets/vision-models/face_detection_yunet_2023mar.onnx
python -m tools.art_pipeline.extract_layers work/halfbody/base.magenta.png full_yaw+000-pitch+00 --source-dir work/halfbody/out --output-root work/layers/out --model assets/vision-models/face_detection_yunet_2023mar.onnx --safe-regions assets/makeup-safe-regions.json
python -m tools.art_pipeline.assemble_set work/expressions --input-dir work/halfbody/out
python -m tools.art_pipeline.derive_variants speech work/expressions/happy.png work/halfbody/out/bare_speaking_cheek.keyed.png happy work/expressions/happy_speech_mid.png
python -m tools.art_pipeline.flatten_magenta work/aligned.png work/aligned.magenta.png
python -m pytest -q tests/test_art_pipeline.py
```

`constants.py` にはキャンバスサイズ、キー色のしきい値、フェザー、形態学処理、顔の安全領域、靴領域の比率、連結成分のしきい値を集約し、各項目の横に scratchpad の出典と計測根拠を記載しています。数値を変更する場合は回帰テストと本説明も同時に更新してください。
