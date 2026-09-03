# README 媒體世代來源清單／README 媒体世代来源清单／README Media Generation Provenance／README メディア世代プロヴェナンス

## 繁體中文

`docs/media/MEDIA-PROVENANCE.json` 是 README 所引用媒體的唯一清單。每個項目記錄產生工具、產生時的 `domain/constants.py` `POSE_ATLAS_GENERATION`、SHA-256 與 `auto_regenerable`。不可自動重產的 Q 版插畫與影片必須保留明確的 `reason`。

換代時，先依清單中 `generator` 重產所有 `auto_regenerable: true` 項目，再以實際檔案更新世代與 SHA-256；不可手動只改世代或只改雜湊。確認 README 的引用集合仍與 `entries` 完全相同後，執行 `py -3.15 tests/test_release_automation.py` 與完整測試。

## 简体中文

`docs/media/MEDIA-PROVENANCE.json` 是 README 所引用媒体的唯一清单。每个条目记录生成工具、生成时 `domain/constants.py` 的 `POSE_ATLAS_GENERATION`、SHA-256 与 `auto_regenerable`。不可自动重生成的 Q 版插画和视频必须保留明确的 `reason`。

换代时，先按清单中的 `generator` 重生成所有 `auto_regenerable: true` 条目，再用实际文件更新世代与 SHA-256；不得只手工修改世代或哈希。确认 README 引用集合仍与 `entries` 完全一致后，运行 `py -3.15 tests/test_release_automation.py` 和完整测试。

## English

`docs/media/MEDIA-PROVENANCE.json` is the single ledger for every media file referenced by the README. Each entry records its generator, the `domain/constants.py` `POSE_ATLAS_GENERATION` at creation time, SHA-256, and `auto_regenerable`. Non-regenerable chibi illustrations and video must carry an explicit `reason`.

When the body generation changes, rerun the recorded `generator` for every `auto_regenerable: true` entry, then update generation and SHA-256 from the actual files. Do not hand-edit only the generation or digest. Confirm that the README reference set exactly matches `entries`, then run `py -3.15 tests/test_release_automation.py` and the full suite.

## 日本語

`docs/media/MEDIA-PROVENANCE.json` は README が参照するメディアの唯一の台帳です。各項目には生成ツール、生成時点の `domain/constants.py` の `POSE_ATLAS_GENERATION`、SHA-256、`auto_regenerable` を記録します。自動再生成できない Q 版イラストと動画には明確な `reason` を必ず付けます。

世代を更新するときは、台帳の `generator` に従って `auto_regenerable: true` の全項目を再生成し、実ファイルから世代と SHA-256 を更新してください。世代またはダイジェストだけを手作業で変更してはいけません。README の参照集合と `entries` が完全一致することを確認し、`py -3.15 tests/test_release_automation.py` と全テストを実行してください。
