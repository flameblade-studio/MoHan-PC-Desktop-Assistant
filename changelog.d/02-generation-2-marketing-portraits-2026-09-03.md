### 未發布 — 行銷肖像改為二代合成外觀（2026-09-03）

* README 六張表情卡、安裝精靈圖（`installer/artwork/*`）、工作列圖示（`assets/mohan-taskbar-icon.png`）與 `assets/mohan-halfbody.ico` 全部改為二代「合成後」外觀：`tools/render_marketing_portraits.py` 以全新空白儲存區驅動執行期同一條 `ActiveOutfitOverlay`（官方「藍白漢服」＋內建原妝 100%），輸出可重現的 `docs/media/portraits/*.png`（1254×1254 RGBA）；README 四語表情卡改引用該目錄，安裝精靈圖與圖示由 `tools/build_installer_artwork.py --source` 與 `tools/build_app_icon.ps1 -Source` 自合成後的 `idle_front.png` 重建，`tests/test_release_automation.py` 重新釘住各檔 SHA-256。執行期素顏 sprite 與官方套件皆未更動。

### 未发布 — 营销肖像改为二代合成外观（2026-09-03）

* README 六张表情卡、安装向导图（`installer/artwork/*`）、任务栏图标（`assets/mohan-taskbar-icon.png`）与 `assets/mohan-halfbody.ico` 全部改为二代「合成后」外观：`tools/render_marketing_portraits.py` 以全新空白存储区驱动运行时同一条 `ActiveOutfitOverlay`（官方「蓝白汉服」＋内置原妆 100%），输出可复现的 `docs/media/portraits/*.png`（1254×1254 RGBA）；README 四语表情卡改引用该目录，安装向导图与图标由 `tools/build_installer_artwork.py --source` 与 `tools/build_app_icon.ps1 -Source` 从合成后的 `idle_front.png` 重建，`tests/test_release_automation.py` 重新钉住各文件 SHA-256。运行时素颜 sprite 与官方套件均未改动。

### Unreleased — marketing portraits in the generation-2 composed look (2026-09-03)

* The six README expression cards, the installer wizard artwork (`installer/artwork/*`), the taskbar icon (`assets/mohan-taskbar-icon.png`) and `assets/mohan-halfbody.ico` now show the generation-2 *composed* look: `tools/render_marketing_portraits.py` drives the very same runtime `ActiveOutfitOverlay` with a fresh empty store (official Blue-and-White Hanfu pack plus built-in classic makeup at 100 %) and writes reproducible `docs/media/portraits/*.png` (1254×1254 RGBA); the README cards in all four languages reference that directory, the wizard art and the icon are rebuilt from the composed `idle_front.png` via `tools/build_installer_artwork.py --source` and `tools/build_app_icon.ps1 -Source`, and `tests/test_release_automation.py` re-pins every SHA-256. The bare runtime sprites and the official packs are untouched.

### 未リリース — マーケティング肖像を第二世代の合成後の姿へ（2026-09-03）

* README の表情カード 6 枚、インストーラーのウィザード画像（`installer/artwork/*`）、タスクバーアイコン（`assets/mohan-taskbar-icon.png`）と `assets/mohan-halfbody.ico` をすべて第二世代の「合成後」の姿に更新しました。`tools/render_marketing_portraits.py` が空の新規ストアで実行時と同じ `ActiveOutfitOverlay`（公式「藍白漢服」＋内蔵基本メイク 100%）を駆動し、再現可能な `docs/media/portraits/*.png`（1254×1254 RGBA）を出力します。四言語の README カードはこのディレクトリを参照し、ウィザード画像とアイコンは合成後の `idle_front.png` から `tools/build_installer_artwork.py --source` と `tools/build_app_icon.ps1 -Source` で再構築、`tests/test_release_automation.py` は各ファイルの SHA-256 を釘付けし直しました。実行時の素顔スプライトと公式パックは変更していません。
