# 墨寒桌面助理變更紀錄／墨寒桌面助手变更日志／MoHan Desktop Assistant Changelog／墨寒デスクトップアシスタント変更履歴

## 繁體中文

本文件記錄墨寒桌面助理所有值得注意的公開變更。

## [4.7.0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.6.0...v4.7.0) (2026-09-16)

### 未發布 — 遷移說明（issue #140，選項 3）／未发布 — 迁移说明（issue #140，选项 3）／Unreleased — migration note (issue #140, option 3)／未リリース — 移行メモ（issue #140、選択肢 3）

* 官方預設外觀包「藍白漢服」與內建妝容素材入庫：`assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit`（衣袍、散髮、銀髮飾，31 個 silhouette 齊全）與 `assets/official-packs/mohan.makeup.builtin.mohan-outfit`（`classic`／`light`，淡雅為原妝 alpha × 0.55）由 `tools/assemble_official_default_pack.py` 自產線分層對映、裁切、封裝而成；官方套件目錄由 `assets/makeup/` 改為 `assets/official-packs/`（`assets/makeup/builtin/` 仍是妝容範本與素材來源）。全新設定檔與「還原內建預設」的 `builtin` 哨兵改由 `domain/outfit_pack_official.py` 解析：衣裝／髮型／頭飾指向官方包 ensemble、妝容指向內建原妝，官方檔案待補時仍回退至素體；官方 id 與其內容受保留保護，匯入與移除僅適用外加套件。雲裳閣的「內建預設服裝」即官方包，統一列出一次；`assets/makeup-safe-regions.json` 依二代半身 rig 重生。／官方默认外观包「蓝白汉服」与内置妆容素材入库：`assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit`（衣袍、散发、银发饰，31 个 silhouette 齐全）与 `assets/official-packs/mohan.makeup.builtin.mohan-outfit`（`classic`／`light`，淡雅为原妆 alpha × 0.55）由 `tools/assemble_official_default_pack.py` 自产线分层映射、裁切、封装而成；官方套件目录由 `assets/makeup/` 改为 `assets/official-packs/`（`assets/makeup/builtin/` 仍是妆容模板与素材来源）。全新配置文件与「还原内置默认」的 `builtin` 哨兵改由 `domain/outfit_pack_official.py` 解析：服装／发型／头饰指向官方包 ensemble、妆容指向内置原妆，官方文件待补时仍回退至素体；官方 id 与其内容受保留保护，导入与移除仅适用于附加套件。云裳阁的「内置默认服装」即官方包，统一列出一次；`assets/makeup-safe-regions.json` 按二代半身 rig 重新生成。／The official default appearance pack "Blue-and-White Hanfu" and the built-in makeup art land in the repository: `assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit` (robe, loose hair, silver hairpiece, all 31 silhouettes) and `assets/official-packs/mohan.makeup.builtin.mohan-outfit` (`classic`/`light`, light being classic with alpha × 0.55), mapped, cropped and sealed from the pipeline layers by `tools/assemble_official_default_pack.py`; the official pack directory moves from `assets/makeup/` to `assets/official-packs/` (`assets/makeup/builtin/` stays the makeup template and asset source). The `builtin` sentinel of a fresh profile and of "restore built-in" is now resolved by `domain/outfit_pack_official.py`: garment/hairstyle/headwear point at the official ensemble and makeup at the built-in classic look, falling back to the bare base while an official archive awaits restoration; official ids and their contents remain protected, with import and removal restricted to add-on packs. The Wardrobe Pavilion's "built-in default outfit" is the official pack itself and is listed once; `assets/makeup-safe-regions.json` is regenerated from the generation-2 half-body rigs.／公式の既定外観パック「藍白漢服」と内蔵メイク素材をリポジトリに収録：`assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit`（袍、下ろした髪、銀の髪飾り、31 silhouette 完備）と `assets/official-packs/mohan.makeup.builtin.mohan-outfit`（`classic`／`light`、淡めは基本メイクの alpha × 0.55）を `tools/assemble_official_default_pack.py` がパイプラインのレイヤーから対応付け・切り落とし・封止して生成。公式パックのディレクトリは `assets/makeup/` から `assets/official-packs/` へ移動（`assets/makeup/builtin/` はメイクのテンプレートと素材元のまま）。新規プロファイルと「内蔵の既定へ戻す」の `builtin` センチネルは `domain/outfit_pack_official.py` が解決し、衣装／髪型／頭飾りは公式 ensemble、メイクは内蔵の基本メイクを指し、公式ファイルの復元待ちでは従来どおり素体へ戻る。公式 id と内容は保護され、インポートと削除は追加パックだけを対象とする。雲裳閣の「内蔵の既定衣装」は公式パックそのもので、一度だけ表示する。`assets/makeup-safe-regions.json` は第二世代の半身 rig から再生成。
* 妝容成為可拆卸圖層（`makeup` 選擇槽）：素體維持素顏＋髮髻，外袍、散髮、銀髮飾與妝容全是可開關的圖層，全身 24 視角與半身 7 輪廓同一標準。外觀包 manifest 新增選用的 `makeup` 集合（item → 多個 variant → 每個 silhouette 三張全畫布 RGBA 圖層 `eyes`／`cheeks`／`lips`，可選 `intensity`）；省略 `makeup` 的既有套件與雲端一鍵製衣產物維持有效。妝容於執行期固定疊在膚色之上、髮型／頭飾／衣裝之下，獨立於保護臉部遮罩，並由 `assets/makeup-safe-regions.json`（`tools/build_makeup_safe_regions.py` 由分層 rig 產生）的安全區裁切，並保持可見虹膜與口腔原有畫面；跑出安全區的圖層於匯入（`WardrobeService.install`、`tools/build_outfit_pack.py`）與執行期一律拒絕。雲裳閣新增妝容選單（素顏／內建「原妝」「淡雅」／已安裝套件）與 0–100% 濃淡滑桿，濃淡以 `makeup.json` 持久保存並同時作用於全身與半身路徑；純妝容 DLC 走既有「匯入服裝套件」按鈕與同一驗證、清單、移除流程。內建妝容素材由工作室依 `assets/makeup/builtin/manifest.json` 範本補產後放入 `assets/makeup/`；素材到位前，選擇原妝／淡雅會顯示「內建妝容素材待補」並以素顏呈現。／妆容成为可拆卸图层（`makeup` 选择槽）：素体维持素颜＋发髻，外袍、散发、银发饰与妆容全是可开关的图层，全身 24 视角与半身 7 轮廓同一标准。外观包 manifest 新增可选的 `makeup` 集合（item → 多个 variant → 每个 silhouette 三张全画布 RGBA 图层 `eyes`／`cheeks`／`lips`，可选 `intensity`）；省略 `makeup` 的现有套件与云端一键制衣产物保持有效。妆容在运行时固定叠在肤色之上、发型／头饰／服装之下，独立于保护脸部遮罩，并由 `assets/makeup-safe-regions.json`（`tools/build_makeup_safe_regions.py` 由分层 rig 生成）的安全区裁切，并保持可见虹膜与口腔原有画面；跑出安全区的图层在导入（`WardrobeService.install`、`tools/build_outfit_pack.py`）与运行时一律拒绝。云裳阁新增妆容菜单（素颜／内置「原妆」「淡雅」／已安装套件）与 0–100% 浓淡滑块，浓淡以 `makeup.json` 持久保存并同时作用于全身与半身路径；纯妆容 DLC 走既有「导入服装套件」按钮与同一验证、列表、删除流程。内置妆容素材由工作室按 `assets/makeup/builtin/manifest.json` 模板补产后放入 `assets/makeup/`；素材到位前，选择原妆／淡雅会显示「内置妆容素材待补」并以素颜呈现。／Makeup becomes a detachable layer (the `makeup` selection slot): the base body stays bare-faced with a bun, and the robe, loose hair, silver hairpiece, and makeup are all switchable layers under one standard for the 24 full-body views and the 7 half-body silhouettes. The appearance-pack manifest gains an optional `makeup` collection (item → several variants → three full-canvas RGBA layers `eyes`/`cheeks`/`lips` per silhouette, optional `intensity`); existing packs and one-click cloud outfits without `makeup` stay valid. At runtime makeup always sits above the skin and below hairstyles/headwear/garments, exempt from the protected-face mask but clipped to the safe region in `assets/makeup-safe-regions.json` (derived from the layered rig by `tools/build_makeup_safe_regions.py`) while preserving the original visible iris and oral-cavity pixels; a layer that leaves its safe region is rejected at import (`WardrobeService.install`, `tools/build_outfit_pack.py`) and at runtime. The Wardrobe Pavilion gains a makeup menu (bare face / built-in "classic" and "light" / installed packs) and a 0–100% intensity slider persisted in `makeup.json` that applies to both the full-body and the half-body path; makeup-only DLC uses the existing "Import outfit package" button and the same validation, listing, and removal pipeline. The built-in makeup art is produced by the studio from the `assets/makeup/builtin/manifest.json` template and dropped into `assets/makeup/`; until it lands, choosing classic/light shows "built-in makeup art pending" and renders a bare face.／メイクを着脱可能なレイヤー（`makeup` 選択 slot）に：素体はすっぴん＋お団子のまま、上衣、下ろした髪、銀の髪飾り、メイクはすべて切り替え可能なレイヤーで、全身 24 視点と半身 7 輪郭は同一基準です。外観パックの manifest に任意の `makeup` 集合（item → 複数の variant → silhouette ごとに全キャンバス RGBA 三層 `eyes`／`cheeks`／`lips`、任意の `intensity`）を追加。`makeup` を省略した既存パックとクラウドのワンクリック衣装はそのまま有効です。実行時のメイクは常に肌の上、髪型／頭飾り／衣装の下に重なり、保護顔マスクの対象外ですが、`assets/makeup-safe-regions.json`（`tools/build_makeup_safe_regions.py` がレイヤー rig から生成）の安全領域でクリップされ、見えている虹彩と口腔の元の画素を保持します。安全領域を外れるレイヤーはインポート時（`WardrobeService.install`、`tools/build_outfit_pack.py`）も実行時も拒否します。雲裳閣にメイクメニュー（すっぴん／内蔵「基本メイク」「淡めメイク」／インストール済みパック）と 0–100% の濃さスライダーを追加。濃さは `makeup.json` に永続保存され、全身と半身の両経路に効きます。メイク専用 DLC は既存の「衣装パッケージをインポート」ボタンと同じ検証・一覧・削除の流れを通ります。内蔵メイク素材はスタジオが `assets/makeup/builtin/manifest.json` テンプレートに従って制作し `assets/makeup/` に配置します。素材が届くまで、基本メイク／淡めメイクを選ぶと「内蔵メイク素材は準備中」と表示され、すっぴんで描画されます。
* 素體升為二代：`BODY_PROFILE_ID` 由 `mohan-body-v1` 升為 `mohan-body-v2`（版本 2），並以測試釘住 `domain/constants.py` 的 `POSE_ATLAS_GENERATION`，三處常數須持續保持一致。官方與 DLC 服裝套件由工作室在二代素體上重製；使用者自製套件自切換日起，須符合二代契約才可匯入及執行。已安裝的一代套件會在雲裳閣清單標示「不相容」，匯入或套用時顯示「這套服裝是為一代素體製作的，穿在二代素體上會對不準；請用一鍵製衣重新生成」；若它正是啟用中的服裝，執行期會自動還原內建服裝並明確提示一次。任何在儲存庫之外散布的 `.mohan-outfit` 都必須以 `tools/build_outfit_pack.py` 對二代範本重建；雲端一鍵製衣直接產出二代套件。／素体升为二代：`BODY_PROFILE_ID` 由 `mohan-body-v1` 升为 `mohan-body-v2`（版本 2），并以测试钉住 `domain/constants.py` 的 `POSE_ATLAS_GENERATION`，三处常量须持续保持一致。官方与 DLC 服装套件由工作室在二代素体上重制；用户自制套件自切换日起，须符合二代契约才可导入及运行。已安装的一代套件会在云裳阁列表标示「不兼容」，导入或应用时显示「这套服装是为一代素体制作的，穿在二代素体上会对不准；请用一键制衣重新生成」；若它正是启用中的服装，运行时会自动恢复内置服装并明确提示一次。任何在仓库之外分发的 `.mohan-outfit` 都必须以 `tools/build_outfit_pack.py` 针对二代模板重建；云端一键制衣直接产出二代套件。／Body profile moved to generation 2: `BODY_PROFILE_ID` goes from `mohan-body-v1` to `mohan-body-v2` (version 2) and is pinned by test to `POSE_ATLAS_GENERATION` in `domain/constants.py`, keeping all three constants synchronized. Official and DLC outfit packs are remade on the generation-2 body by the studio; user-made packs must satisfy the generation-2 contract for import and runtime use from the cutover date. An already-installed generation-1 pack is listed as "Incompatible" in the Wardrobe Pavilion, and importing or applying it shows "This outfit was made for the generation-1 body and will not line up on the generation-2 body; regenerate it with one-click outfit creation."; if it is the active outfit, the runtime restores the built-in outfit and explicitly notifies once. Any `.mohan-outfit` distributed outside the repository must be rebuilt with `tools/build_outfit_pack.py` against the generation-2 template; one-click cloud outfit creation produces generation-2 packs directly.／素体を第二世代へ更新：`BODY_PROFILE_ID` を `mohan-body-v1` から `mohan-body-v2`（バージョン 2）へ引き上げ、`domain/constants.py` の `POSE_ATLAS_GENERATION` とテストで固定したため、三つの定数を常に一致させます。公式および DLC の衣装パックはスタジオが第二世代素体で作り直します。ユーザー自作パックは切替日から第二世代契約への適合をインポート時と実行時の必須条件とします。インストール済みの第一世代パックは雲裳閣の一覧で「非互換」と表示され、インポートまたは適用時に「この衣装は第一世代素体向けに作られたもので、第二世代素体では位置が合いません。ワンクリック衣装生成で作り直してください」と表示されます。それが使用中の衣装だった場合、実行時は内蔵衣装へ自動的に戻し、一度だけ通知します（明示的な通知を伴います）。リポジトリ外で配布されるあらゆる `.mohan-outfit` は `tools/build_outfit_pack.py` で第二世代テンプレートに対して再構築する必要があります。クラウドのワンクリック衣装生成は第二世代パックを直接生成します。

### 未發布 — 行銷肖像改為二代合成外觀（2026-09-03）／未发布 — 营销肖像改为二代合成外观（2026-09-03）／Unreleased — marketing portraits in the generation-2 composed look (2026-09-03)／未リリース — マーケティング肖像を第二世代の合成後の姿へ（2026-09-03）

* README 六張表情卡、安裝精靈圖（`installer/artwork/*`）、工作列圖示（`assets/mohan-taskbar-icon.png`）與 `assets/mohan-halfbody.ico` 全部改為二代「合成後」外觀：`tools/render_marketing_portraits.py` 以全新空白儲存區驅動執行期同一條 `ActiveOutfitOverlay`（官方「藍白漢服」＋內建原妝 100%），輸出可重現的 `docs/media/portraits/*.png`（1254×1254 RGBA）；README 四語表情卡改引用該目錄，安裝精靈圖與圖示由 `tools/build_installer_artwork.py --source` 與 `tools/build_app_icon.ps1 -Source` 自合成後的 `idle_front.png` 重建，`tests/test_release_automation.py` 重新釘住各檔 SHA-256。執行期素顏 sprite 與官方套件皆未更動。／README 六张表情卡、安装向导图（`installer/artwork/*`）、任务栏图标（`assets/mohan-taskbar-icon.png`）与 `assets/mohan-halfbody.ico` 全部改为二代「合成后」外观：`tools/render_marketing_portraits.py` 以全新空白存储区驱动运行时同一条 `ActiveOutfitOverlay`（官方「蓝白汉服」＋内置原妆 100%），输出可复现的 `docs/media/portraits/*.png`（1254×1254 RGBA）；README 四语表情卡改引用该目录，安装向导图与图标由 `tools/build_installer_artwork.py --source` 与 `tools/build_app_icon.ps1 -Source` 从合成后的 `idle_front.png` 重建，`tests/test_release_automation.py` 重新钉住各文件 SHA-256。运行时素颜 sprite 与官方套件均未改动。／The six README expression cards, the installer wizard artwork (`installer/artwork/*`), the taskbar icon (`assets/mohan-taskbar-icon.png`) and `assets/mohan-halfbody.ico` now show the generation-2 *composed* look: `tools/render_marketing_portraits.py` drives the very same runtime `ActiveOutfitOverlay` with a fresh empty store (official Blue-and-White Hanfu pack plus built-in classic makeup at 100 %) and writes reproducible `docs/media/portraits/*.png` (1254×1254 RGBA); the README cards in all four languages reference that directory, the wizard art and the icon are rebuilt from the composed `idle_front.png` via `tools/build_installer_artwork.py --source` and `tools/build_app_icon.ps1 -Source`, and `tests/test_release_automation.py` re-pins every SHA-256. The bare runtime sprites and the official packs are untouched.／README の表情カード 6 枚、インストーラーのウィザード画像（`installer/artwork/*`）、タスクバーアイコン（`assets/mohan-taskbar-icon.png`）と `assets/mohan-halfbody.ico` をすべて第二世代の「合成後」の姿に更新しました。`tools/render_marketing_portraits.py` が空の新規ストアで実行時と同じ `ActiveOutfitOverlay`（公式「藍白漢服」＋内蔵基本メイク 100%）を駆動し、再現可能な `docs/media/portraits/*.png`（1254×1254 RGBA）を出力します。四言語の README カードはこのディレクトリを参照し、ウィザード画像とアイコンは合成後の `idle_front.png` から `tools/build_installer_artwork.py --source` と `tools/build_app_icon.ps1 -Source` で再構築、`tests/test_release_automation.py` は各ファイルの SHA-256 を釘付けし直しました。実行時の素顔スプライトと公式パックは変更していません。

### 未發布 — 半身素體二代（2026-09-02）／未发布 — 半身素体二代（2026-09-02）／Unreleased — generation-2 half-body base (2026-09-02)／未リリース — 半身素体の第二世代化（2026-09-02）

* 半身素體重製為二代素顏版：`assets/expressions/` 下 113 張表情、75 張分層與 21 張 `v120_*` 物理切層全部由工作室自有產線自 `assets/pose-atlas/v5-base/` 重新生成，美術來源完整採工作室自有二代素材；外袍、髮型、髮飾與妝容改為執行期圖層。`v120_*` 的頭髮、袖子與髮飾切層依契約為全透明（`tests/test_v120_asset_integrity.py` 的 `LICENSED_EMPTY`），臉部偏移表改為實測值；已退出程式載入範圍的 `physics_*` 與 `skeptical_front.png` 共 22 張已移除。／半身素体重制为二代素颜版：`assets/expressions/` 下 113 张表情、75 张分层与 21 张 `v120_*` 物理切层全部由工作室自有产线自 `assets/pose-atlas/v5-base/` 重新生成，美术来源完整采用工作室自有二代素材；外袍、发型、发饰与妆容改为运行时图层。`v120_*` 的头发、袖子与发饰切层按契约为全透明（`tests/test_v120_asset_integrity.py` 的 `LICENSED_EMPTY`），脸部偏移表改为实测值；已退出程序加载范围的 `physics_*` 与 `skeptical_front.png` 共 22 张已移除。／The half-body base is regenerated bare-faced on generation 2: the 113 expressions, 75 layers and 21 `v120_*` physics cutouts under `assets/expressions/` are all rebuilt by the studio's own pipeline from `assets/pose-atlas/v5-base/` and use only studio-owned generation-2 artwork; robe, hairstyle, hairpiece and makeup are now runtime layers. The `v120_*` hair, sleeve and ornament cutouts are fully transparent by contract (`LICENSED_EMPTY` in `tests/test_v120_asset_integrity.py`), the face-offset tables now hold measured values, and the 22 `physics_*` and `skeptical_front.png` files outside the code loading paths are removed.／半身素体を第二世代の素顔版として作り直しました。`assets/expressions/` 配下の表情 113 枚、レイヤー 75 枚、`v120_*` 物理切り出し 21 枚はすべてスタジオ自前のパイプラインが `assets/pose-atlas/v5-base/` から再生成したもので、美術はすべてスタジオ所有の第二世代素材に統一しました。外衣、髪型、髪飾り、化粧は実行時レイヤーになりました。`v120_*` の髪・袖・髪飾りの切り出しは契約上完全に透明で（`tests/test_v120_asset_integrity.py` の `LICENSED_EMPTY`）、顔オフセット表は実測値に更新し、コードの読み込み対象外となった `physics_*` と `skeptical_front.png` の計 22 枚を削除しました。

### 未發布 — README 首屏重排（2026-09-04）／未发布 — README 首屏重排（2026-09-04）／Unreleased — README first-screen reorder (2026-09-04)／未リリース — README 第一画面の再構成（2026-09-04）

* README 四語首屏改為主視覺、價值主張、下載、快速開始、跨平台能力矩陣、作者與版本資訊；Windows CI、MIT 授權與最新公開版本徽章保留在外層，其餘徽章移入四語折疊區／README 四语首屏改为主视觉、价值主张、下载、快速开始、跨平台能力矩阵、作者与版本信息；Windows CI、MIT 许可与最新公开版本徽章保留在外层，其余徽章移入四语折叠区／The four-language README first screen now leads with the hero, value proposition, download, Quick Start, cross-platform capability matrix, and author and release information; Windows CI, MIT License, and latest public release badges remain visible while the other badges move into four-language collapsible sections／README の四言語ファーストビューをメインビジュアル、価値提案、ダウンロード、クイックスタート、クロスプラットフォーム機能表、作者とリリース情報の順に変更し、Windows CI、MIT ライセンス、最新公開版バッジを表示したまま、その他のバッジを四言語の折りたたみセクションへ移動

### 未發布 — README 四語重編與 DLC 教學（2026-09-03）／未发布 — README 四语重编与 DLC 教学（2026-09-03）／Unreleased — README four-language restructuring and DLC tutorial (2026-09-03)／未リリース — README の四言語再編と DLC チュートリアル（2026-09-03）

* README 依「這是什麼、畫面與功能、安裝更新、首次使用、隱私、DLC、贊助授權、疑難排解、開發者入口」重編四語同構內容，刪除重複與過時段落；新增 `.mohan-outfit` 外觀、妝容包與 `.mohan-theme` 主題檔的安裝、選用、還原、容量數量上限、二代素體相容性及 Ko-fi 單次、每月贊助雙軌教學／README 依「这是什么、画面与功能、安装更新、首次使用、隐私、DLC、赞助授权、疑难排解、开发者入口」重编四语同构内容，删除重复与过时段落；新增 `.mohan-outfit` 外观、妆容包与 `.mohan-theme` 主题文件的安装、选用、还原、容量数量上限、二代素体兼容性及 Ko-fi 单次、每月赞助双轨教学／The README is restructured into parallel four-language content organized around “What is it, screens and features, installation and updates, first use, privacy, DLC, sponsorship and licensing, troubleshooting, developer entry”; duplicate and outdated sections are removed; tutorials are added for installing, selecting, restoring, capacity and item-count limits, and generation-2 body compatibility of the `.mohan-outfit` appearance/makeup packs and `.mohan-theme` theme files, with separate one-time and monthly Ko-fi sponsorship tracks／README を「これは何か、画面と機能、インストールと更新、初回利用、プライバシー、DLC、スポンサーとライセンス、トラブルシューティング、開発者向け入口」の順で四言語の同構成に再編し、重複した段落と古い段落を削除。`.mohan-outfit` の外観/メイクパックと `.mohan-theme` テーマファイルについて、インストール、選択、復元、容量と個数の上限、第二世代素体との互換性、および Ko-fi の単発/月次支援という二つの方式を説明するチュートリアルを追加。

### 未發布 — 凌霄主題包 B、C（2026-09-03）／未发布 — 凌霄主题包 B、C（2026-09-03）／Unreleased — Lingxiao B/C theme packs (2026-09-03)／未リリース — 凌霄 B/C テーマパック（2026-09-03）

* 新增凌霄 B「霧靄青瓷」與 C「赤焰劍光」主題包，設定頁可切換且預設仍為 A「墨金・凌霄」／新增凌霄 B「雾霭青瓷」与 C「赤焰剑光」主题包，设置页可切换且默认仍为 A「墨金・凌霄」／add the Lingxiao B “Misty Celadon” and C “Crimson Swordlight” theme packs with a settings-page switch while keeping A “Ink-Gold” as default／凌霄 B「霧靄青磁」と C「赤焔剣光」のテーマパックを追加し、設定画面で切り替え可能にしつつ A「墨金・凌霄」を既定値として維持

### 未發布 — 執行期合成效能預算（2026-09-03）／未发布 — 运行时合成性能预算（2026-09-03）／Unreleased — Runtime compositing performance budget (2026-09-03)／未リリース — 実行時合成パフォーマンス予算（2026-09-03）

* 新增離屏執行期合成基準 `tools/bench_composite.py`、預算與量測依據 `tools/perf_budget.json`、以及 CI 閘門 `tests/test_perf_budget.py`。五輪、每輪五次的基準中，冷啟全身視角為中位數 1389.922 ms、p95 1468.653 ms，熱切全身視角為 2.485、3.157 ms，半身剪影切換為 5.043、5.600 ms；冷啟超過擁有者 300 ms 目標，預算如實標記 `over_target: true`，暫不改動合成演算法。重複解碼稽核證實首次全身與半身切換會重複解碼部分 PNG，熱切換則無新增解碼／新增离屏运行时合成基准 `tools/bench_composite.py`、预算与测量依据 `tools/perf_budget.json`、以及 CI 闸门 `tests/test_perf_budget.py`。五轮、每轮五次的基准中，冷启动全身视角为中位数 1389.922 ms、p95 1468.653 ms，热切换全身视角为 2.485、3.157 ms，半身剪影切换为 5.043、5.600 ms；冷启动超过所有者 300 ms 目标，预算如实标记 `over_target: true`，暂不改动合成算法。重复解码稽核证实首次全身与半身切换会重复解码部分 PNG，热切换则无新增解码／Added the offscreen runtime compositing benchmark `tools/bench_composite.py`, the budget and measurement basis `tools/perf_budget.json`, and the CI gate `tests/test_perf_budget.py`. In five rounds of five runs each, the cold-start full-body view measured a median of 1389.922 ms and p95 of 1468.653 ms, the warm-switch full-body view measured 2.485 and 3.157 ms, and the half-body silhouette switch measured 5.043 and 5.600 ms; cold start exceeds the owner's 300 ms target, the budget truthfully marks `over_target: true`, and the compositing algorithm is unchanged for now. A duplicate-decoding audit confirmed that the first full-body and half-body switches decode some PNGs again, while warm switches add no decoding／オフスクリーン実行時合成ベンチマーク `tools/bench_composite.py`、予算と測定根拠 `tools/perf_budget.json`、CI ゲート `tests/test_perf_budget.py` を追加。5 ラウンド、各 5 回の基準測定では、コールドスタートの全身視点は中央値 1389.922 ms、p95 1468.653 ms、ウォーム切替の全身視点は 2.485、3.157 ms、半身シルエット切替は 5.043、5.600 ms。コールドスタートは所有者の 300 ms 目標を超えるため、予算には `over_target: true` と正直に記録し、現時点では合成アルゴリズムを変更しない。重複デコードの監査で、初回の全身・半身切替では一部の PNG が再度デコードされる一方、ウォーム切替では追加のデコードがないことを確認。

### 未發布 — README 展示影片改為可自動重產（2026-09-04）／未发布 — README 演示视频改为可自动重生成（2026-09-04）／Unreleased — README demonstration video is now regenerable (2026-09-04)／未リリース — README デモ動画を自動再生成可能に変更（2026-09-04）

* 重錄 `docs/media/mohan-demo.mp4`：新增 `tools/record_demo_video.py`，以二代執行期合成外觀、OneCore `Microsoft Yating` 正常語速、50 Hz 嘴型 cues 與離屏 PNG 逐幀編碼；媒體 provenance、音訊與畫面規格、SHA-256 測試閘門同步更新／重录 `docs/media/mohan-demo.mp4`：新增 `tools/record_demo_video.py`，使用二代运行时合成外观、OneCore `Microsoft Yating` 正常语速、50 Hz 嘴型 cues 与离屏 PNG 逐帧编码；同步更新媒体 provenance、音视频规格与 SHA-256 测试闸门／Re-records `docs/media/mohan-demo.mp4` with the new `tools/record_demo_video.py`: generation-2 runtime composition, normal-speed OneCore `Microsoft Yating`, 50 Hz viseme cues, and offscreen PNG frame encoding; media provenance, A/V specification, and SHA-256 test gates are updated together／`docs/media/mohan-demo.mp4` を再録し、新しい `tools/record_demo_video.py` で第二世代の実行時合成、通常速度の OneCore `Microsoft Yating`、50 Hz の viseme cues、オフスクリーン PNG 逐フレームエンコードを使用。メディア provenance、音声・映像仕様、SHA-256 のテストゲートも同時に更新しました。

### 未發布 — README 媒體世代清單與重產閘門（2026-09-04）／未发布 — README 媒体世代清单与重生成闸门（2026-09-04）／Unreleased — README media generation ledger and regeneration gate (2026-09-04)／未リリース — README メディア世代台帳と再生成ゲート（2026-09-04）

* 新增 `docs/media/MEDIA-PROVENANCE.json`，登錄 README 21 個媒體檔的產生工具、素體世代、SHA-256 與可否自動重產；測試會列出落後當前 `POSE_ATLAS_GENERATION` 的自動素材／新增 `docs/media/MEDIA-PROVENANCE.json`，登记 README 21 个媒体文件的生成工具、素体世代、SHA-256 与是否可自动重生成；测试会列出落后当前 `POSE_ATLAS_GENERATION` 的自动素材／Adds `docs/media/MEDIA-PROVENANCE.json`, recording the generator, body generation, SHA-256, and regeneration capability for all 21 README media files; tests list any auto-regenerable media left behind the current `POSE_ATLAS_GENERATION`／`docs/media/MEDIA-PROVENANCE.json` を追加し、README の 21 メディアについて生成ツール、素体世代、SHA-256、自動再生成可否を記録しました。テストは現在の `POSE_ATLAS_GENERATION` より遅れた自動再生成対象を一覧化します。

### 未發布 — 原生 RGBA 加速補強／未发布 — 原生 RGBA 加速补强／Unreleased — Native RGBA acceleration hardening／未発布 — ネイティブ RGBA アクセラレーション補強

* 原生 RGBA 加速的型別轉接、可斷言的停用狀態 API 與 README 說明，接在 #181 之上／原生 RGBA 加速的类型转接、可断言的停用状态 API 与 README 说明，接在 #181 之上／Buffer adaptation, an assertable disabled-state API and README notes for native RGBA acceleration, layered on #181／ネイティブ RGBA アクセラレーションのバッファ変換、検証可能な無効化状態 API、README 説明（#181 の上に構築）

### 新增 multimodal 模型資產驗證測試／新增 multimodal 模型資產驗證測試／Add multimodal model asset verification tests／マルチモーダル資産検証テストを追加

* 新增 `tests/test_verify_multimodal_model_assets.py`，以本機合成模型與 SBOM 驗證 4 種門檻：通過、缺檔、雜湊不符、SBOM 清單損壞，並提供直接執行入口輸出 `MULTIMODAL_MODEL_ASSETS_OK`。／新增 `tests/test_verify_multimodal_model_assets.py`，使用本機合成模型與 SBOM 驗證 4 種門檻：通過、缺檔、雜湊不符、SBOM 清單損壞，並提供直接執行入口輸出 `MULTIMODAL_MODEL_ASSETS_OK`。／Add `tests/test_verify_multimodal_model_assets.py` with four gate checks using synthetic multimodal model files and SBOM fixtures: pass, missing file, hash mismatch, and corrupted manifest; include a direct execution entry that prints `MULTIMODAL_MODEL_ASSETS_OK`.／`tests/test_verify_multimodal_model_assets.py` を追加し、合成モデルと SBOM フィクスチャを用いた 4 つのゲート（正常、ファイル欠損、ハッシュ不一致、SBOM リスト破損）を検証、`MULTIMODAL_MODEL_ASSETS_OK` を出力する直接実行エントリを追加した。

### 未發布 — Tachyon 證據擷取重試／未发布 — Tachyon 证据采集重试／Unreleased — Tachyon evidence capture retries／未リリース — Tachyon 証拠キャプチャの再試行

* 對 runtime evidence 缺失或 sample-read error 超過既有門檻的單一 target，最多重新取樣兩次並記錄各次結果；所有樣本、漏採樣、JIT 與效能門檻維持不變／对于 runtime evidence 缺失或 sample-read error 超过既有门槛的单个 target，最多重新采样两次并记录各次结果；所有样本、漏采样、JIT 与性能门槛保持不变／A single target with missing runtime evidence or a sample-read error above the existing threshold is freshly captured up to two more times with every result recorded; all sample, missed-sample, JIT, and performance thresholds remain unchanged／runtime evidence が欠落した、または既存の閾値を超える sample-read error の単一 target は最大二回まで新しく再取得し、各結果を記録します。サンプル、欠落サンプル、JIT、パフォーマンスの閾値は変更しません。

### 未發布 — 托腮姿勢嘴型連續性測試改用離散端點契約／未发布 — 托腮姿势嘴型连续性测试改用离散端点契约／Unreleased — Chin-rest mouth continuity test adopts the discrete endpoint contract／未リリース — 頬杖ポーズの口形連続性テストを離散エンドポイント契約に更新

* `tests/test_mouth_visual_continuity.py` 在 `supports_discrete_speech` 回報托腮姿勢由已審核原生完整嘴型端點驅動時，改斷言掃描只出現 rest 與 open 兩個端點、每個方向各切換一次、沒有混合幀且兩側嘴角同步跟隨；其他姿勢維持原本 `MIN_TRANSITION_SIGNATURES` 參數式門檻／`tests/test_mouth_visual_continuity.py` 在 `supports_discrete_speech` 报告托腮姿势由已审核原生完整嘴型端点驱动时，改断言扫描只出现 rest 与 open 两个端点、每个方向各切换一次、没有混合帧且两侧嘴角同步跟随；其他姿势维持原本 `MIN_TRANSITION_SIGNATURES` 参数式门槛／When `supports_discrete_speech` reports that the chin-rest pose is driven by reviewed native complete mouth endpoints, `tests/test_mouth_visual_continuity.py` now asserts that the sweep shows exactly the rest and open endpoints, switches once in each direction with no blended frame, and that both mouth corners follow; other poses keep the original `MIN_TRANSITION_SIGNATURES` parametric threshold／`supports_discrete_speech` が頬杖ポーズをレビュー済みネイティブの完全な口形エンドポイントで駆動すると報告する場合、`tests/test_mouth_visual_continuity.py` はスイープに rest と open の二つのエンドポイントだけが現れ、各方向に一回ずつ切り替わり、混合フレームがなく、両口角が追従することを検証します。他のポーズは従来の `MIN_TRANSITION_SIGNATURES` パラメトリック閾値を維持します。

### 已審核姿勢宣告動態來源，避免新原生下的未綁定表情崩潰／已审核姿势声明动态来源，避免新原生下的未绑定表情崩溃／Declare a reviewed pose's dynamic source so unbound expressions stop raising on the new native／レビュー済みポーズが動的ソースを宣言し、新ネイティブで未バインド表情が例外を出さないようにする

* `infrastructure/reviewed_garment_assets.py` 的姿勢契約新增選填欄位 `dynamic_source`（唯一合法值 `complete-expressions`，未知值載入即失敗），`ReviewedGarmentPose` 隨之攜帶該宣告。`infrastructure/reviewed_pose_overlay.py` 的 `_native_motion`/`has_native_motion` 在姿勢宣告（或已安裝的 `assets/expressions/complete-expressions/manifest.json` 綁定該姿勢）時回傳 `None` 而非載入保留的舊動作根，因此未綁定表情改為落到 `native_neutral(silhouette)` 的同一顆已批准原生靜態幀；`motion_required` 維持 `true`、不釋放任何來源綁定，未宣告的姿勢仍以原本的 `Reviewed pose motion native body SHA-256 mismatch.` 失敗關閉。／`infrastructure/reviewed_garment_assets.py` 的姿势契约新增可选字段 `dynamic_source`（唯一合法值 `complete-expressions`，未知值加载即失败），`ReviewedGarmentPose` 随之携带该声明。`infrastructure/reviewed_pose_overlay.py` 的 `_native_motion`/`has_native_motion` 在姿势声明（或已安装的 `assets/expressions/complete-expressions/manifest.json` 绑定该姿势）时返回 `None` 而不加载保留的旧动作根，因此未绑定表情改为落到 `native_neutral(silhouette)` 的同一张已批准原生静帧；`motion_required` 维持 `true`、不释放任何来源绑定，未声明的姿势仍以原本的 `Reviewed pose motion native body SHA-256 mismatch.` 失败关闭。／the reviewed pose contract in `infrastructure/reviewed_garment_assets.py` gains an optional `dynamic_source` field (the only legal value is `complete-expressions`; any unknown value fails while loading) and `ReviewedGarmentPose` carries it. `_native_motion` / `has_native_motion` in `infrastructure/reviewed_pose_overlay.py` now return `None` instead of loading the retained motion root when the pose declares that source — or when the installed `assets/expressions/complete-expressions/manifest.json` binds the pose — so an unbound expression falls through to `native_neutral(silhouette)`, a still frame of the same approved native. `motion_required` stays `true`, no source binding is released, and an undeclared pose still fails closed with the original `Reviewed pose motion native body SHA-256 mismatch.`／`infrastructure/reviewed_garment_assets.py` のポーズ契約に任意フィールド `dynamic_source`（唯一の正当値は `complete-expressions`、未知の値は読み込み時に失敗）を追加し、`ReviewedGarmentPose` がそれを保持します。`infrastructure/reviewed_pose_overlay.py` の `_native_motion`/`has_native_motion` は、ポーズがそのソースを宣言している場合（またはインストール済みの `assets/expressions/complete-expressions/manifest.json` がそのポーズを束縛している場合）に、保持された旧モーションルートを読み込まず `None` を返します。そのため未バインドの表情は `native_neutral(silhouette)`、すなわち同じ承認済みネイティブの静止フレームにフォールバックします。`motion_required` は `true` のまま、ソース束縛は一切解放されず、宣言のないポーズは従来どおり `Reviewed pose motion native body SHA-256 mismatch.` でフェイルクローズします。

### 未發布 — 閘門測試與素體中繼資料同步到分支現況／未发布 — 关卡测试与素体元数据同步到分支现状／Unreleased — Gate tests and atlas metadata synced to the branch state／未リリース — ゲートテストと素体メタデータをブランチ現状に同期

* `tests/test_expression_speech_runtime.py` 在托腮姿勢由已審核原生嘴型端點驅動時，改以 `speech_current_expression` 與 `mouth_transition_to` 斷言「眨眼中音訊持續推進」，像素比較只保留給參數式姿勢／`tests/test_expression_speech_runtime.py` 在托腮姿势由已审核原生嘴型端点驱动时，改以 `speech_current_expression` 与 `mouth_transition_to` 断言“眨眼中音频持续推进”，像素比较只保留给参数式姿势／When the chin-rest pose is driven by reviewed native mouth endpoints, `tests/test_expression_speech_runtime.py` now asserts "audio keeps advancing during a blink" through `speech_current_expression` and `mouth_transition_to`, keeping pixel comparisons for parametric poses only／頬杖ポーズがレビュー済みネイティブの口形エンドポイントで駆動される場合、`tests/test_expression_speech_runtime.py` は「まばたき中も音声が進む」ことを `speech_current_expression` と `mouth_transition_to` で検証し、ピクセル比較はパラメトリックなポーズにのみ残します
* `tests/test_pose_atlas_assets.py` 的控制圖層、手部/身體覆蓋層、官方輪廓與替換遮罩期望集合更新為分支實際追蹤的檔案；`tests/test_native_blink_alpha.py` 與 `tests/test_reviewed_pose_overlay.py` 的探針假物件補上 `_complete_halfbody` 與 `patches`／`tests/test_pose_atlas_assets.py` 的控制图层、手部/身体覆盖层、官方轮廓与替换遮罩期望集合更新为分支实际跟踪的文件；`tests/test_native_blink_alpha.py` 与 `tests/test_reviewed_pose_overlay.py` 的探针假对象补上 `_complete_halfbody` 与 `patches`／The expected control-layer, hand/body overlay, official silhouette and replacement-mask sets in `tests/test_pose_atlas_assets.py` now match the files tracked on the branch; the probe fakes in `tests/test_native_blink_alpha.py` and `tests/test_reviewed_pose_overlay.py` gain `_complete_halfbody` and `patches`／`tests/test_pose_atlas_assets.py` の制御レイヤー、手・身体オーバーレイ、公式シルエット、置換マスクの期待集合をブランチで追跡中のファイルに合わせ、`tests/test_native_blink_alpha.py` と `tests/test_reviewed_pose_overlay.py` のプローブ用フェイクに `_complete_halfbody` と `patches` を追加
* `assets/pose-atlas/v5-base/BUILD-METADATA.json` 的 `source_authorization` 還原為發布工具寫入的字串 `confirmed_by_rights_holder_2026-08-16`，原本的核准證據指標改存於 `source_authorization_evidence`，並補回 `redistribution`／`assets/pose-atlas/v5-base/BUILD-METADATA.json` 的 `source_authorization` 还原为发布工具写入的字符串 `confirmed_by_rights_holder_2026-08-16`，原有的核准证据指针改存于 `source_authorization_evidence`，并补回 `redistribution`／`source_authorization` in `assets/pose-atlas/v5-base/BUILD-METADATA.json` is restored to the release-tool string `confirmed_by_rights_holder_2026-08-16`, the approval evidence pointer moves to `source_authorization_evidence`, and `redistribution` is restored／`assets/pose-atlas/v5-base/BUILD-METADATA.json` の `source_authorization` をリリースツールが書き込む文字列 `confirmed_by_rights_holder_2026-08-16` に戻し、承認証拠のポインタは `source_authorization_evidence` に移し、`redistribution` を復元
* `tests/test_visual_acceptance_regressions.py` 在 `idle_front` 帶有登錄的半閉眼權威 `idle_front_half` 時，改斷言 HALF 幀同時異於 rest 與 CLOSED，並以該權威鍵驗證路由；沒有半閉眼權威時維持原本的零變化契約／`tests/test_visual_acceptance_regressions.py` 在 `idle_front` 带有登录的半闭眼权威 `idle_front_half` 时，改断言 HALF 帧同时异于 rest 与 CLOSED，并以该权威键验证路由；没有半闭眼权威时维持原本的零变化契约／When `idle_front` carries the registered half-blink authority `idle_front_half`, `tests/test_visual_acceptance_regressions.py` now asserts that the HALF frame differs from both rest and CLOSED and proves routing through that authority key; without a half authority the original zero-change contract stays／`idle_front` に登録済みの半まばたき権威 `idle_front_half` がある場合、`tests/test_visual_acceptance_regressions.py` は HALF フレームが rest と CLOSED の両方と異なることを検証し、その権威キーでルーティングを確認します。半まばたき権威がない場合は従来のゼロ変化契約を維持します

### 未發布 — yaw-090 退回 main 版本、+075 眨眼圖層移除、原生臉部證據入庫／未发布 — yaw-090 退回 main 版本、+075 眨眼图层移除、原生脸部证据入库／Unreleased — yaw-090 restored to main, +075 blink layers removed, native-face artifacts tracked in-repo／未リリース — yaw-090 を main 版に戻し、+075 まばたきレイヤーを除去、ネイティブ顔証拠をリポジトリ内に配置

* 依擁有者 2026-09-16 裁決，`yaw-090-pitch+00` 的素體、25 個分層、旁車與 v4 中繼資料退回 `main` 版本，分支新增的 blink 圖層、身體與手部覆蓋層、官方輪廓與替換遮罩一併移除；`identity-audit-baseline.json` 的 `yaw-090` 條目改回 `main` 的 SHA 與兩項前額豁免，並以 `tools/audit_pose_atlas_identity.py` 重產靜態稽核證據（24 檔、0 問題、4 豁免）／依所有者 2026-09-16 裁决，`yaw-090-pitch+00` 的素体、25 个分层、旁车与 v4 元数据退回 `main` 版本，分支新增的 blink 图层、身体与手部覆盖层、官方轮廓与替换遮罩一并移除；`identity-audit-baseline.json` 的 `yaw-090` 条目改回 `main` 的 SHA 与两项前额豁免，并以 `tools/audit_pose_atlas_identity.py` 重新生成静态审计证据（24 文件、0 问题、4 豁免）／Per the owner's 2026-09-16 decision, the `yaw-090-pitch+00` body, its 25 layers, sidecars and v4 metadata return to the `main` versions, and the branch-added blink layers, body and hand overlays, official silhouette and replacement mask are removed; the `yaw-090` entry of `identity-audit-baseline.json` returns to the `main` SHA with its two forehead waivers, and the static audit evidence is regenerated with `tools/audit_pose_atlas_identity.py` (24 files, 0 issues, 4 waived)／所有者の 2026-09-16 の裁定により、`yaw-090-pitch+00` の素体、25 レイヤー、サイドカー、v4 メタデータを `main` 版に戻し、ブランチで追加された blink レイヤー、身体・手オーバーレイ、公式シルエット、置換マスクを除去。`identity-audit-baseline.json` の `yaw-090` 項目は `main` の SHA と二つの額の免除に戻し、静的監査証拠を `tools/audit_pose_atlas_identity.py` で再生成（24 ファイル、0 問題、4 免除）
* `BUILD-METADATA.json` 的 `status` 恢復為 `release-assets`，`yaw-090` 視角條目改為未量測原生臉部（`landmark_count` 0）；16 個視角的原生 478 點證據從未追蹤的暫存目錄搬進 `assets/pose-atlas/v5-base/<view>.native-landmarks.json`，`source.path` 改為相對路徑，旁車與 `body_sidecar_sha256` 同步更新，`tests/test_pose_atlas_identity_measurements.py` 的可用原生臉部數改為 16／`BUILD-METADATA.json` 的 `status` 恢复为 `release-assets`，`yaw-090` 视角条目改为未测量原生脸部（`landmark_count` 0）；16 个视角的原生 478 点证据从未跟踪的暂存目录搬进 `assets/pose-atlas/v5-base/<view>.native-landmarks.json`，`source.path` 改为相对路径，旁车与 `body_sidecar_sha256` 同步更新，`tests/test_pose_atlas_identity_measurements.py` 的可用原生脸部数改为 16／`status` in `BUILD-METADATA.json` returns to `release-assets` and the `yaw-090` view record declares an unmeasured native face (`landmark_count` 0); the native 478-point artifacts of 16 views move from the untracked scratch directory into `assets/pose-atlas/v5-base/<view>.native-landmarks.json` with a relative `source.path`, the sidecars and `body_sidecar_sha256` follow, and the available native-face count in `tests/test_pose_atlas_identity_measurements.py` becomes 16／`BUILD-METADATA.json` の `status` を `release-assets` に戻し、`yaw-090` ビュー項目はネイティブ顔未計測（`landmark_count` 0）を宣言。16 ビューのネイティブ 478 点証拠を未追跡の作業ディレクトリから `assets/pose-atlas/v5-base/<view>.native-landmarks.json` へ移し、`source.path` を相対パスに変更、サイドカーと `body_sidecar_sha256` を同期、`tests/test_pose_atlas_identity_measurements.py` の利用可能ネイティブ顔数を 16 に更新
* `yaw+075-pitch+00` 的 blink 圖層與 `blink-binding.json` 移除（+075 尚未通過驗收）；`assets/makeup-safe-regions.json` 的 `yaw-090` 槽位改回 `main` 的矩形；`tests/test_official_default_pack.py` 的 `front-crossed` 與 `yaw+000` 唇色探針依已核准的四妝容內建包重錄／`yaw+075-pitch+00` 的 blink 图层与 `blink-binding.json` 移除（+075 尚未通过验收）；`assets/makeup-safe-regions.json` 的 `yaw-090` 槽位改回 `main` 的矩形；`tests/test_official_default_pack.py` 的 `front-crossed` 与 `yaw+000` 唇色探针按已核准的四妆容内置包重新记录／The `yaw+075-pitch+00` blink layers and `blink-binding.json` are removed (+075 has not passed acceptance); the `yaw-090` slots in `assets/makeup-safe-regions.json` return to the `main` rectangles; the `front-crossed` and `yaw+000` lip probes in `tests/test_official_default_pack.py` are re-recorded from the approved four-look built-in pack／`yaw+075-pitch+00` の blink レイヤーと `blink-binding.json` を除去（+075 は未承認）。`assets/makeup-safe-regions.json` の `yaw-090` スロットを `main` の矩形に戻し、`tests/test_official_default_pack.py` の `front-crossed` と `yaw+000` の唇プローブを承認済み四メイク内蔵パックから再記録
* `tests/test_layered_full_body.py` 的 `VISIBLE_SPEECH_MOUTH_VIEWS` 移除 `yaw-090-pitch+00`：`main` 版本的 −90 側面沒有口腔圖層，可見嘴型校準視角回到十二個／`tests/test_layered_full_body.py` 的 `VISIBLE_SPEECH_MOUTH_VIEWS` 移除 `yaw-090-pitch+00`：`main` 版本的 −90 侧面没有口腔图层，可见嘴型校准视角回到十二个／`VISIBLE_SPEECH_MOUTH_VIEWS` in `tests/test_layered_full_body.py` drops `yaw-090-pitch+00`: the `main` yaw-090 profile paints no oral cavity, so the calibrated visible-mouth views return to twelve／`tests/test_layered_full_body.py` の `VISIBLE_SPEECH_MOUTH_VIEWS` から `yaw-090-pitch+00` を除外：`main` 版の −90 側面には口腔レイヤーがなく、校正済み可視口形ビューは十二に戻る
* `assets/pose-atlas/v5-base-layered/mouth_authority_manifest.json` 的 `yaw-090` 條目以 `tools/recalibrate_mouth_authority.py` 對還原後的唇部圖層重算（`mouth_center_x` 568.2014，與 `main` 一致），並釘住還原圖層的 SHA／`assets/pose-atlas/v5-base-layered/mouth_authority_manifest.json` 的 `yaw-090` 条目以 `tools/recalibrate_mouth_authority.py` 对还原后的唇部图层重算（`mouth_center_x` 568.2014，与 `main` 一致），并钉住还原图层的 SHA／The `yaw-090` entry of `assets/pose-atlas/v5-base-layered/mouth_authority_manifest.json` is recomputed with `tools/recalibrate_mouth_authority.py` from the restored lip layers (`mouth_center_x` 568.2014, identical to `main`) and pins the restored layer SHAs／`assets/pose-atlas/v5-base-layered/mouth_authority_manifest.json` の `yaw-090` 項目を `tools/recalibrate_mouth_authority.py` で復元後の唇レイヤーから再計算（`mouth_center_x` 568.2014、`main` と一致）し、復元レイヤーの SHA を固定

### 未發布 — 未遷移模組補齊 PEP 810 lazy 匯入／未发布 — 未迁移模块补齐 PEP 810 lazy 导入／Unreleased — Migrate the remaining modules to PEP 810 lazy imports／未リリース — 未移行モジュールに PEP 810 の lazy インポートを適用

* `tools/migrate_python315_imports.py` 對本分支新增而從未遷移的 62 個追蹤檔（半身完整表情、已審核姿勢、可拆半身、art_pipeline 工具與對應測試）套用 lazy 匯入，共 467 條；`tools/migrate_python315_imports.py --check` 在 CI 閘門 `tests/test_python315_runtime.py` 回到 `pending=0`／`tools/migrate_python315_imports.py` 对本分支新增而从未迁移的 62 个跟踪文件（半身完整表情、已审核姿势、可拆半身、art_pipeline 工具与对应测试）套用 lazy 导入，共 467 条；`tools/migrate_python315_imports.py --check` 在 CI 关卡 `tests/test_python315_runtime.py` 回到 `pending=0`／`tools/migrate_python315_imports.py` applies lazy imports to the 62 tracked files this branch added without migrating (complete half-body expressions, reviewed poses, detachable half-body, art_pipeline tools and their tests), 467 imports in total, so `tools/migrate_python315_imports.py --check` returns to `pending=0` in the `tests/test_python315_runtime.py` gate／`tools/migrate_python315_imports.py` を、本ブランチで追加されながら未移行だった 62 の追跡ファイル（半身完全表情、レビュー済みポーズ、着脱式半身、art_pipeline ツールとそのテスト）に適用し、合計 467 件を lazy インポート化。CI ゲート `tests/test_python315_runtime.py` の `tools/migrate_python315_imports.py --check` が `pending=0` に戻る
* `EAGER_IMPORT_EXCEPTIONS` 新增兩筆刻意保留的 eager 再匯出：`infrastructure/layered_full_body_renderer.py` 的 `MOUTH_APERTURE_THRESHOLD` 與 `CompleteExpressionRendering`（測試以 lazy 匯入取得該常數，lazy 再匯出會交出未解析代理）與 `presentation/ui_localization.py` 的標籤表／`EAGER_IMPORT_EXCEPTIONS` 新增两条刻意保留的 eager 再导出：`infrastructure/layered_full_body_renderer.py` 的 `MOUTH_APERTURE_THRESHOLD` 与 `CompleteExpressionRendering`（测试以 lazy 导入获取该常量，lazy 再导出会交出未解析代理）与 `presentation/ui_localization.py` 的标签表／`EAGER_IMPORT_EXCEPTIONS` gains two deliberate eager re-exports: `MOUTH_APERTURE_THRESHOLD` and `CompleteExpressionRendering` in `infrastructure/layered_full_body_renderer.py` (tests import the constant lazily and a lazy re-export would hand them an unresolved proxy) and the label tables in `presentation/ui_localization.py`／`EAGER_IMPORT_EXCEPTIONS` に意図的な eager 再エクスポートを二件追加：`infrastructure/layered_full_body_renderer.py` の `MOUTH_APERTURE_THRESHOLD` と `CompleteExpressionRendering`（テストがこの定数を lazy インポートするため、lazy 再エクスポートは未解決プロキシを渡してしまう）と `presentation/ui_localization.py` のラベル表
* 補齊 Python 3.15 治理稽核在本分支新增程式碼上的缺口：`HEADWEAR_NONE_NAMES` 與 `EXPRESSION_VARIANTS` 改為 `frozendict`，11 處測試的 `read_text` 與 `write_text` 補上 `encoding`，7 處 `lazy import a.b as x` 改為 `lazy from a import b as x`，8 處巢狀推導式改用 `itertools.product`、PEP 798 解包推導式或明確迴圈，`MISSING` 哨兵改為 `Enum`；`tests/test_python315_runtime.py` 在乾淨匯出下全數通過／补齐 Python 3.15 治理审计在本分支新增代码上的缺口：`HEADWEAR_NONE_NAMES` 与 `EXPRESSION_VARIANTS` 改为 `frozendict`，11 处测试的 `read_text` 与 `write_text` 补上 `encoding`，7 处 `lazy import a.b as x` 改为 `lazy from a import b as x`，8 处嵌套推导式改用 `itertools.product`、PEP 798 解包推导式或明确循环，`MISSING` 哨兵改为 `Enum`；`tests/test_python315_runtime.py` 在干净导出下全部通过／Closes the Python 3.15 governance-audit gaps in code this branch added: `HEADWEAR_NONE_NAMES` and `EXPRESSION_VARIANTS` become `frozendict`, 11 test `read_text` and `write_text` calls gain `encoding`, 7 `lazy import a.b as x` statements become `lazy from a import b as x`, 8 nested comprehensions use `itertools.product`, PEP 798 unpacking comprehensions or explicit loops, and the `MISSING` sentinel becomes an `Enum`; `tests/test_python315_runtime.py` passes in a clean export／本ブランチで追加されたコードに対する Python 3.15 ガバナンス監査の不足を解消：`HEADWEAR_NONE_NAMES` と `EXPRESSION_VARIANTS` を `frozendict` に、テストの `read_text` と `write_text` 11 箇所に `encoding` を付与、`lazy import a.b as x` 7 箇所を `lazy from a import b as x` に、ネストした内包表記 8 箇所を `itertools.product`、PEP 798 のアンパック内包表記または明示ループに、`MISSING` センチネルを `Enum` に変更。`tests/test_python315_runtime.py` はクリーンなエクスポートで合格

### 未發布 — Tachyon 啟動證據擷取窗放寬至 40 秒／未发布 — Tachyon 启动证据采集窗放宽至 40 秒／Unreleased — Widen the Tachyon startup evidence capture window to 40 seconds／未リリース — Tachyon 起動証拠の取得ウィンドウを 40 秒に拡大

* `windows-ci.yml` 與 `release.yml` 的 `tools/profile_mohan_tachyon.py` 步驟加上 `--duration 40`：本分支的冷啟動在本機量到 17 到 18 秒（`main` 為 9 到 12 秒），超過預設 12 秒擷取窗，`startup` 目標在視窗到期前來不及寫出 runtime evidence；主因是衣櫃分頁啟動時對 33MB 官方外觀包的 437 張 PNG 逐張解碼驗證（cProfile 約 6.9 秒），啟動效能回歸另開工單處理／`windows-ci.yml` 与 `release.yml` 的 `tools/profile_mohan_tachyon.py` 步骤加上 `--duration 40`：本分支的冷启动在本机测得 17 到 18 秒（`main` 为 9 到 12 秒），超过默认 12 秒采集窗，`startup` 目标在窗口到期前来不及写出 runtime evidence；主因是衣柜标签页启动时对 33MB 官方外观包的 437 张 PNG 逐张解码验证（cProfile 约 6.9 秒），启动性能回归另开工单处理／The `tools/profile_mohan_tachyon.py` step in `windows-ci.yml` and `release.yml` gains `--duration 40`: this branch's cold start measures 17 to 18 seconds locally (`main`: 9 to 12 seconds), beyond the default 12-second capture window, so the `startup` target could not write its runtime evidence before the window expired; the main cost is the wardrobe tab decoding and validating all 437 PNGs of the 33MB official outfit pack at startup (about 6.9 seconds in cProfile), and that startup regression is tracked as separate work／`windows-ci.yml` と `release.yml` の `tools/profile_mohan_tachyon.py` ステップに `--duration 40` を追加：本ブランチのコールドスタートはローカルで 17〜18 秒（`main` は 9〜12 秒）と既定の 12 秒取得ウィンドウを超え、`startup` ターゲットが期限前に runtime evidence を書き出せなかった。主因はワードローブタブが起動時に 33MB の公式衣装パックの PNG 437 枚を逐一デコード検証すること（cProfile で約 6.9 秒）で、この起動性能の後退は別作業として追跡する

### 肯定句與清楚指引／肯定句与清晰指引／Affirmative wording and clear guidance／肯定形と明確な案内

- 文件、AI 提示詞、介面訊息與程式說明改用肯定句，直接說明動作、條件及實際狀態。／文档、AI 提示词、界面消息与代码说明改用肯定句，直接说明动作、条件及实际状态。／Documentation, AI prompts, UI messages, and code explanations use affirmative wording to state actions, conditions, and actual status.／文書、AI プロンプト、画面メッセージ、コード説明を肯定形にし、行動、条件、実際の状態を明示します。
- 錯誤提示提供具體處理方向，並保留既有授權、機器狀態、資料契約與驗證門檻。／错误提示提供具体处理方向，并保留现有授权、机器状态、数据契约与验证门槛。／Error messages provide concrete next steps while preserving authorization, machine states, data contracts, and validation gates.／エラーには具体的な対処を示し、承認範囲、機械状態、データ契約、検証ゲートを維持します。

### 固定 AI 協作手冊與工作入口／固定 AI 协作手册与工作入口／Pin the AI collaboration playbook and workflow router／AI 共同作業手冊と作業入口の版を固定

- 固定已審查的 Playbook 版本，沿用現有工作進度、三層代理設定與分項驗收證據。／固定已审查的 Playbook 版本，沿用现有工作进度、三层代理设置与分项验收证据。／Pin the reviewed Playbook revision while retaining existing coordination, three-tier profiles and scoped acceptance evidence.／確認済み Playbook の版を固定し、既存の進捗管理、三層代理設定、範囲別の検証証拠を継続使用します。

### 動態換裝完整回退／动态换装完整回退／Atomic animated outfit fallback／動的衣装合成の一括フォールバック

- 服裝或妝容素材需要修正才能通過驗證時，整張動態合成回退至保留眨眼與嘴型的素體，並清除舊成功計數。／服装或妆容素材需要修正才能通过验证时，整张动态合成回退至保留眨眼与嘴型的素体，并清除旧成功计数。／If appearance or makeup assets require corrections to pass validation, roll back the entire animated outfit to the bare frame while preserving core blink and mouth motion, and clear stale success counts.／衣装またはメイク素材が検証合格に向けた修正を必要とする場合、まばたきと口の動きを維持して素体へ一括で戻し、古い成功件数を消去します。
- 保留既有合成介面，以及省略眨眼補丁時的既有眼妝行為；畫布尺寸改變後重新驗證素材與遮罩。／保留现有合成接口，以及省略眨眼补丁时的现有眼妆行为；画布尺寸改变后重新验证素材与遮罩。／Preserve legacy combined adapters and existing eye makeup behavior when authored blink patches are omitted; revalidate layers and masks after canvas size changes.／従来の合成インターフェースとまばたき素材を省略した場合のアイメイク動作を維持し、キャンバス寸法変更時に素材とマスクを再検証します。

### 外觀模組職責拆分／外观模块职责拆分／Appearance module responsibilities／外観モジュールの責務分離

- 將服裝資料模型與衣櫃分頁組裝移至各自模組，保留公開匯入介面與既有衣櫃行為，並下調行數上限。／将服装数据模型与衣橱分页组装移至各自模块，保留公开导入接口与现有衣橱行为，并下调行数上限。／Move outfit data models and wardrobe tab assembly into dedicated modules, preserve public imports and wardrobe behavior, and lower the line-count baselines.／衣装データモデルと衣装タブの組み立てを専用モジュールへ分離し、公開インポートと既存動作を維持して行数上限を引き下げます。

### 保留臉部邊緣透明度／保留脸部边缘透明度／Preserve face edge transparency／顔輪郭の透明度を保持

- 繁體中文：全身接縫與臉部復原直接替換權威像素，避免重複疊畫使半透明輪廓變厚，並新增重複復原的回歸檢查。／简体中文：全身接缝与脸部复原直接替换权威像素，避免重复叠画使半透明轮廓变厚，并新增重复复原的回归检查。／English: Full-body seam and face restoration replace authority pixels directly, preventing repeated painting from thickening translucent edges; add repeated-restoration regression coverage.／日本語：全身の継ぎ目と顔の復元で基準画素を直接置換し、重ね描きによる半透明輪郭の肥厚を防止。反復復元の回帰検証を追加。

### 眨眼透明來源檢查／眨眼透明来源检查／Validate transparent blink sources／まばたき画像の透明度検証

- 全身眨眼素材載入時，解碼並要求 8 位元 RGBA 與透明背景，通過格式、透明度及解碼檢查後才進入角色合成。沿用既有 OpenCV 相依套件。／全身眨眼素材加载时，解码并要求 8 位 RGBA 与透明背景，通过格式、透明度及解码检查后才进入角色合成。沿用现有 OpenCV 依赖。／Decode full-body blink sources and require 8-bit RGBA with a transparent background. Admit frames to character composition only after format, transparency, and decoding checks pass. Uses the existing OpenCV dependency.／全身まばたき素材をデコードし、8 ビット RGBA と透明背景を必須とします。形式・透明度・デコードの検証に合格した画像だけをキャラクター合成へ渡します。既存の OpenCV 依存関係を使用します。

### 候選眨眼來源綁定／候选眨眼来源绑定／Candidate blink source binding／候補まばたき素材の参照元固定

- 明確指定素體來源的候選渲染器，會在載入時核對眨眼配對、來源路徑、畫布與 SHA-256，並使用同一份已驗證 PNG 位元組繪製，確保舊眼皮維持隔離，且驗證後持續使用同一檔案；省略候選來源的既有模式維持相容。／明确指定素体来源的候选渲染器，会在加载时核对眨眼配对、来源路径、画布与 SHA-256，并使用同一份已验证 PNG 字节绘制，确保旧眼皮维持隔离，且验证后持续使用同一文件；省略候选来源的现有模式保持兼容。／Candidate renderers with an explicit body authority validate blink pairs, source paths, canvas dimensions and SHA-256 at load time, then render the same verified PNG bytes to keep stale eyelids isolated and preserve the verified file after validation. Existing rendering that omits an explicit candidate authority remains compatible.／素体の参照元を明示した候補レンダラーは、読み込み時にまばたきの組、参照パス、キャンバス寸法、SHA-256 を検証し、検証済みの同じ PNG バイト列を描画します。古いまぶたを隔離し、検証後も同じファイルを維持して、候補の参照元を省略した既存の描画との互換性を維持します。

- 此檢查確認宣告的檔案綁定；美術核可、24 視角與 600 分層完成度仍各自以正式驗收為準。／此检查确认声明的文件绑定；美术批准、24 视角与 600 分层完成度仍各自以正式验收为准。／This check validates declared file bindings; visual acceptance and completion of 24 views and 600 layers remain separate formal gates.／この検証は宣言されたファイルの対応関係を確認します。美術承認と 24 視点・600 レイヤーの完成度は、それぞれ別の正式な関門で確認します。

### 批次試跑來源與嘴型裁切／批次试跑来源与嘴型裁切／Batch trial source and mouth clipping／バッチ試行の参照元と口形のクリップ

- 候選試跑使用指定母圖；分離下巴後，嘴型裁切仍依完整臉部範圍計算。／候选试跑使用指定母图；分离下巴后，嘴型裁切仍按完整面部范围计算。／Render candidate trials against their selected authority and include the separate jaw when bounding mouth animation.／候補の試行では指定された参照画像を使い、口形のクリップ範囲には分離した顎を含めます。

### 仙境介面與獨立造型分類／仙境界面与独立造型分类／Celestial dashboard and independent appearance categories／仙境ダッシュボードと独立した外見カテゴリ

- 套用核可的深藍、白玉與金色介面，保留八個功能頁面；衣櫥提供衣裝、髮型、髮飾、妝容及自主選裝分類。／应用获准的深蓝、白玉与金色界面，保留八个功能页面；衣橱提供衣装、发型、发饰、妆容及自主选装分类。／Apply the approved navy, jade and gold interface while retaining all eight feature pages; separate wardrobe controls into clothing, hair, headwear, makeup and automatic outfit selection.／承認済みの紺・白玉・金の外観を適用し、8 つの機能ページを維持。衣装・髪型・髪飾り・メイク・自動衣装選択をカテゴリ別に配置。
- 獨立套用髮型與髮飾並更新角色預覽，保留其他外觀選擇；外部主題的色彩、字型與背景繼續套用，切回內建主題時還原。／独立应用发型与发饰并更新角色预览，保留其他外观选择；外部主题的色彩、字体与背景继续应用，切回内置主题时恢复。／Apply hair and headwear independently and refresh the character preview while preserving other appearance selections; retain external theme colors, fonts and backgrounds and restore defaults when returning to built-in themes.／髪型と髪飾りを個別に適用してプレビューを更新し、他の外見設定を維持。外部テーマの色・書体・背景を反映し、内蔵テーマに戻すと既定値に復元。

### 保護半透明手部邊緣／保护半透明手部边缘／Protect translucent hand edges／半透明の手の輪郭を保護

- 手部遮擋範圍納入所有 Alpha 大於零的像素，使較淡的手部邊緣也保持在服裝前方；保留素材原始色彩、透明度與座標。／手部遮挡范围纳入所有 Alpha 大于零的像素，使较淡的手部边缘也保持在服装前方；保留素材原始色彩、透明度与坐标。／Hand occlusion includes every pixel with alpha greater than zero, keeping faint hand edges in front of clothing and preserving original asset colors, alpha, and coordinates.／手の遮蔽領域にアルファ値がゼロより大きい全画素を含め、薄い手の輪郭も衣服の前に保持します。素材の元の色、アルファ値、座標を維持します。

### 固定沒有手部遮罩的組裝狀態／固定没有手部遮罩的组装状态／Preserve absent hand-mask snapshots／手部マスクがない状態を固定

- 組裝入口已確認沒有手部遮罩時，所有合成器共用該結果；稍後新增遮罩須重新建立組裝入口才生效。直接建立合成器且未指定提供者時仍自動載入。／组装入口已确认没有手部遮罩时，所有合成器共用该结果；稍后新增遮罩须重新建立组装入口才生效。直接建立合成器且未指定提供者时仍自动加载。／All compositors share a composition root's confirmed absence of hand masks. Masks added later take effect after rebuilding the composition root. Direct construction still loads masks automatically when no provider is supplied.／組み立て入口で手部マスクがないと確認した結果を全合成器で共有します。後から追加したマスクは組み立て入口の再作成後に反映されます。提供元を指定せず合成器を直接作成する場合は引き続き自動読み込みします。

### 載入核心手部遮罩／加载核心手部遮罩／Load core hand masks／コアの手マスクを読み込み

- 正式組裝入口讀取成對的核心手部遮罩，保留舊素材行為，並只接受完整資料。／正式组装入口读取成对的核心手部遮罩，保留旧素材行为，并只接受完整数据。／The production composition root reads paired core hand masks, preserves legacy behavior and accepts intact data.／正式な組み立て入口でコアの手マスクのペアを読み込み、従来の動作を維持し、完全なデータを受け入れます。

### 核心手部遮擋接點／核心手部遮挡接点／Core hand occlusion boundary／コアの手の遮蔽境界

- 外觀合成器接收核心提供的固定姿勢可見手部遮罩，讓衣料及手後素材避開手部，同時保留手前配件的遮擋；首批正式視角已接入遮罩，省略遮罩時沿用既有流程。／外观合成器接收核心提供的固定姿势可见手部遮罩，让衣料及手后素材避开手部，同时保留手前配件的遮挡；首批正式视角已接入遮罩，省略遮罩时沿用现有流程。／The appearance compositor uses core-owned visible-hand masks for fixed poses, keeping garments and behind-hand layers off the hands while preserving front-of-hand accessories. The first production views now include these masks, while paths that omit masks retain their prior behavior.／外観合成器は固定ポーズのコア所有の可視手マスクを使用し、衣服と手の後方の素材が手を覆うことを防ぎ、手の前方のアクセサリーによる遮蔽を維持します。最初の正式視点にはマスクを導入し、マスクを省略した既存経路は従来の動作を維持します。

### 可拆卸粉底妝容與跨姿勢設定保存／可拆卸粉底妆容与跨姿势设置保存／Detachable foundation makeup and cross-pose settings／着脱式ファンデーションメイクと姿勢間設定保持

- `front classic4` 提供粉底、眼妝、頰彩與唇妝四個獨立槽位；半閉眼與閉眼狀態同步替換粉底及眼妝素材，合成採用 SourceAtop 並保留原生 Alpha。／`front classic4` 提供粉底、眼妆、腮红与唇妆四个独立槽位；半闭眼与闭眼状态同步替换粉底及眼妆素材，合成采用 SourceAtop 并保留原生 Alpha。／`front classic4` exposes independent foundation, eyes, cheeks, and lips slots; half-closed and closed states replace foundation and eye makeup together, using SourceAtop while preserving native alpha.／`front classic4` はファンデーション、アイ、チーク、リップを独立した4スロットで提供します。半閉眼と閉眼ではファンデーションとアイメイクを同時に状態別素材へ切り替え、SourceAtopで元のアルファを保持します。
- 共用妝容設定在四槽前姿勢切換至三槽姿勢或 `light` 變體時保留各槽濃度；legacy 三槽讀取只回傳眼妝、頰彩與唇妝要求的子集，舊套件仍可使用。／共享妆容设置在四槽前姿势切换至三槽姿势或 `light` 变体时保留各槽浓度；legacy 三槽读取只返回眼妆、腮红与唇妆要求的子集，旧套件仍可使用。／Shared makeup settings retain each intensity when a four-slot front pose changes to a three-slot pose or the `light` variant; legacy three-slot reads return only the requested eyes, cheeks, and lips subset, while older packs remain compatible.／共有メイク設定は4スロットの正面姿勢から3スロット姿勢または `light` バリアントへ切り替えても各濃度を保持します。従来の3スロット読み取りは要求されたアイ、チーク、リップだけを返し、旧パックとの互換性を維持します。

### 原生無奈與可選彩妝／原生无奈与可选彩妆／Native exasperated portrait and optional makeup／ネイティブ困惑表情と任意の化粧

* 將核准的無奈七個原生部件、三種語音嘴型及可拆衣裝設為預設；安裝收據綁定來源與逐檔雜湊，缺件或漂移時停止載入。／将批准的无奈七个原生部件、三种语音口型及可拆衣装设为默认；安装收据绑定来源与逐文件哈希，缺件或变更时停止加载。／Use the approved seven native exasperated parts, three speech mouths, and removable garment by default; the installation receipt pins sources and file hashes, and loading fails closed on missing or changed files.／承認済みの困惑表情のネイティブ 7 パーツ、音声用口形 3 種、着脱可能な衣装を既定にしました。配置記録で原画とファイルのハッシュを固定し、欠落や変更時は読み込みを停止します。
* 將核准配色接入 30 個既有視角，新無奈另用 12 個嘴型對應彩妝圖層；保留淡妝、標準妝、分項濃度與卸妝，既有使用者設定及粉底素材不變。／将批准配色接入 30 个既有视角，新无奈另用 12 个口型对应彩妆图层；保留淡妆、标准妆、分项浓度与卸妆，既有用户设置及粉底素材不变。／Apply the approved palette to 30 existing views and 12 separate mouth-specific exasperated cosmetic layers; retain light and classic variants, slot intensities, removal, existing user settings, and foundation assets.／承認済み配色を既存 30 視点と困惑表情の口形別化粧 12 レイヤーに適用しました。薄化粧と標準化粧、部位別濃度、化粧の解除、既存設定、ファンデーション素材を保持します。
* 移除彩妝新增的臉緣紫線、眉區與耳前髮際誤選，並保留手勢眨眼時的原眉；低透明度 Qt 量化造成的藍色數值不再誤列為原圖可見缺陷。／移除彩妆新增的脸缘紫线、眉区与耳前发际误选，并保留手势眨眼时的原眉；低透明度 Qt 量化造成的蓝色数值不再误列为原图可见缺陷。／Remove added cosmetic fringe and unintended brow and preauricular pigment, and preserve gesture brows during blinking; distinguish low-alpha Qt quantization from visible source defects.／化粧による輪郭の紫線と眉・耳前の意図しない着色を除き、身振り中のまばたきでも元の眉を保持します。低 alpha の Qt 量子化と目視できる原画の欠陥を区別します。
* 49 張產品合成與相關範圍回歸已通過；撤回的七姿勢素材仍停用，其他姿勢衣裝接合及全視角人工外觀驗收尚未完成。／49 张产品合成与相关范围回归已通过；撤回的七姿势素材仍停用，其他姿势衣装接合及全视角人工外观验收尚未完成。／Validation passed for 49 product compositions and affected regressions; the withdrawn seven-pose assets remain disabled, while other garment seams and human visual acceptance across all views remain incomplete.／製品合成 49 画像と関連範囲の回帰検証が成功しました。撤回した 7 姿勢は無効のままで、他の衣装の接合と全視点の人による目視受入れは未完了です。

### 四視角素體與外觀接入／四视角素体与外观接入／Four-view body and appearance integration／4視点の素体と外観の統合

- 接入正面、30 度、45 度與 60 度的可拆素體、漢服、髮型、髮飾與眨眼妝容，保留其他視角素材。／接入正面、30 度、45 度与 60 度的可拆素体、汉服、发型、发饰与眨眼妆容，保留其他视角素材。／Integrate detachable bodies, Hanfu, hair, ornaments and blink-aware makeup for front, 30-degree, 45-degree and 60-degree views while retaining other view assets.／正面、30度、45度、60度の分離可能な素体、漢服、髪型、髪飾り、まばたき対応メイクを統合し、他の視点素材を保持。

### 保留手部半透明邊緣／保留手部半透明边缘／Preserve translucent hand edges／手の半透明エッジを保持

- 將可重畫的原生手部依深度合成在衣料上方，保留逐像素 Alpha 並消除衣袖接合處的漏空鋸齒。／将可重画的原生手部按深度合成在衣料上方，保留逐像素 Alpha 并消除衣袖接合处的漏空锯齿。／Composite repaintable native hands above garments by depth, preserving per-pixel alpha and eliminating transparent serrations at sleeve joins.／再描画可能なネイティブの手を衣服より前面に深度合成し、ピクセル単位のアルファを保持して袖の接合部の透明なギザギザを解消しました。

### 修正 front-eureka 髮飾分層／修正 front-eureka 发饰分层／Fix front-eureka headwear partition／front-eureka の髪飾りレイヤーを修正

- 移除髮飾層誤收的額頭髮際殘片，消除正裝合成時的鋸齒雜線；保留原本臉部、髮型與髮飾。／移除发饰层误收的额头发际残片，消除正装合成时的锯齿杂线；保留原有脸部、发型与发饰。／Remove an incorrectly assigned forehead hair fragment from the headwear layer, eliminating the jagged line in formal appearance composition while preserving the face, hairstyle and ornaments.／髪飾りレイヤーに誤って含まれた生え際の断片を除去し、顔・髪型・髪飾りを維持したまま正装の合成時に生じるギザギザの線を解消します。
- 此項修正不代表其他視角的 V4/V5 臉部對齊已完成。／此项修正不代表其他视角的 V4/V5 面部对齐已完成。／This correction does not mark V4/V5 facial identity alignment in other views as complete.／この修正は、他の視点の V4/V5 の顔の同一性調整の完了を意味しません。

### 前髮與動態妝容分段深度／前发与动态妆容分段深度／Animated front-hair and makeup split depth／前髪と動的メイクの段階別奥行き

- `apply_animated` 以 `behind_body` 與 `DestinationOver` 合成後髮，依既有順序繪製 garment、headwear 與配件，執行 `paint_motion`，以 `SourceAtop` 套用妝容，再以 `SourceOver` 將前髮各畫一次。／`apply_animated` 以 `behind_body` 与 `DestinationOver` 合成后发，按既有顺序绘制 garment、headwear 与配件，执行 `paint_motion`，以 `SourceAtop` 套用妆容，再以 `SourceOver` 将前发各画一次。／`apply_animated` composites rear hair through `behind_body` and `DestinationOver`, draws garment, headwear, and accessory layers in their established order, runs `paint_motion`, applies makeup with `SourceAtop`, and draws each front-hair layer once with `SourceOver`.／`apply_animated` は `behind_body` と `DestinationOver` で後ろ髪を合成し、衣装・頭飾り・アクセサリーを既存順序で描き、`paint_motion` を実行し、`SourceAtop` でメイクを適用してから、各前髪レイヤーを `SourceOver` で1回だけ描きます。
- `AppearanceLayerStack` 記錄 `front_hair_indices`，`split_front_hair` 只延後前髮，因此 garment 與 headwear 保持既有順序。／`AppearanceLayerStack` 记录 `front_hair_indices`，`split_front_hair` 只延后前发，因此 garment 与 headwear 保持现有顺序。／`AppearanceLayerStack` records `front_hair_indices`; `split_front_hair` delays only front hair, so garment and headwear retain their established order.／`AppearanceLayerStack` は `front_hair_indices` を記録し、`split_front_hair` は前髪だけを遅延させるため、衣装と頭飾りの既存の順序を維持します。
- 素材階段出現錯誤時以 `_AppearanceCompositionError` 包裝錯誤、用 `_invalidate_view` 清除視角快取，並在原始 `frame` 上重播 `paint_motion`；`tests/test_animated_makeup_depth.py` 驗證像素順序與回退。／素材阶段出现错误时以 `_AppearanceCompositionError` 包装错误、用 `_invalidate_view` 清除视角缓存，并在原始 `frame` 上重播 `paint_motion`；`tests/test_animated_makeup_depth.py` 验证像素顺序与回退。／When an asset phase reports an error, `_AppearanceCompositionError` wraps that error, `_invalidate_view` clears the view cache, and `paint_motion` replays on the original `frame`; `tests/test_animated_makeup_depth.py` verifies pixel order and rollback.／素材段階でエラーが発生した場合は `_AppearanceCompositionError` でエラーを包み、`_invalidate_view` で視点キャッシュを消去し、元の `frame` に `paint_motion` を再生します。`tests/test_animated_makeup_depth.py` が画素順序とロールバックを検証します。
- 這是執行期合成與回歸修正；長髮圖像仍須擁有者視覺核可，程式驗證目前仍在進行。／这是运行时合成与回归修正；长发图像仍须拥有者视觉核可，程序验证目前仍在进行。／This is a runtime composition and regression change; the long-hair artwork still requires the owner's visual approval, and code verification remains in progress.／これは実行時合成と回帰修正です。長髪アートには所有者の外観承認が必要で、コード検証は継続中です。

### 全身母圖來源綁定／全身母图来源绑定／Full-body authority binding／全身原画像の関連付け

- 相對母圖路徑在建立渲染器時固定，切換工作目錄後仍使用同一份參考圖。／相对母图路径在创建渲染器时固定，切换工作目录后仍使用同一份参考图。／Relative authority paths are resolved at renderer construction, keeping the same reference through later working-directory changes.／相対原画像パスを描画器の作成時に確定し、作業ディレクトリ変更後も同じ参照画像を使用します。

- 全身渲染可明確指定母圖目錄，讓補縫與臉部還原使用同一套素材；不同渲染器的母圖快取相互獨立。／全身渲染可明确指定母图目录，让补缝与脸部还原使用同一套素材；不同渲染器的母图缓存相互独立。／Full-body rendering accepts an explicit authority directory for both seam repair and face restoration, with independent caches per renderer.／全身描画では継ぎ目の補修と顔の復元に使用する原画像ディレクトリを明示でき、キャッシュは描画器ごとに独立します。
- 明確指定的母圖須具備可讀取的檔案、可解碼內容與相符尺寸；任一條件需要修正時直接報錯，來源持續綁定指定母圖。省略目錄參數時沿用既有預設行為。／明确指定的母图须具备可读取的文件、可解码内容与相符尺寸；任一条件需要修正时直接报错，来源持续绑定指定母图。省略目录参数时沿用现有默认行为。／Explicit authority images require readable files, decodable content, and matching dimensions. Any correction required raises an error while the source stays bound to that authority. Omitted directories preserve existing defaults.／明示した原画像には読み取り可能なファイル、デコード可能な内容、正しい寸法を必須とします。修正が必要な条件はエラーとして報告し、参照元は指定画像に固定します。ディレクトリ引数を省略した場合は既存の既定動作を維持します。

### 全身視角輪廓淡出修正／全身视角轮廓淡出修正／Fix full-body silhouette cross-fades／全身ビュー輪郭のクロスフェード修正

- 相鄰視角合成函式 render_blended 採預乘色彩加權合成，使舊輪廓依權重完整淡出，保留重疊區域的不透明度，權重為 1 時精確回傳下一視角。本次修正範圍為函式層級；桌面轉向流程接入仍待完成，角色素材保持原樣。／相邻视角合成函数 render_blended 采用预乘色彩加权合成，使旧轮廓按权重完整淡出，保留重叠区域的不透明度，权重为 1 时精确返回下一视角。本次修正范围为函数级；桌面转向流程接入仍待完成，角色素材保持原样。／The render_blended helper uses weighted premultiplied pixels to fade the old silhouette fully, preserve opaque overlap, and return the exact next view at weight 1. This change covers the helper; desktop-turn integration remains pending, and character assets stay intact.／隣接ビュー合成関数 render_blended は乗算済みカラーの重み付き合成により旧輪郭を完全にフェードし、不透明な重なりを保持して、重み 1 で次のビューをそのまま返します。変更範囲は関数単位です。デスクトップ方向転換への接続は今後の作業として残り、キャラクター素材は保持します。

### 全身原生說話幀／全身原生说话帧／Native full-body speech frames／全身の原生発話フレーム

* 新增可選的原生全身嘴型幀，依發音選取已對齊原圖，保留牙齒比例；沒有該組素材時維持既有說話路徑。／新增可选的原生全身嘴型帧，依发音选取已对齐原图，保留牙齿比例；没有该组素材时维持原有说话路径。／Add optional registered full-body speech frames that preserve tooth proportions while retaining the existing speech path for views without them.／歯の比率を保つ位置合わせ済み全身発話フレームを追加し、未導入の視点では従来の発話経路を維持します。
* 載入時檢查完整嘴型組、透明度與原生尺寸，並固定實際繪製的來源位元組；素材外觀驗收與正式替換仍各自記錄。／载入时检查完整嘴型组、透明度与原生尺寸，并固定实际绘制的来源字节；素材外观验收与正式替换仍分别记录。／Validate complete speech sets, transparency and native canvas size; freeze the bytes drawn and retain separate records for visual acceptance and installation.／口形セットの完全性、透明度と原生サイズを検証し、描画するデータを固定します。外観確認と正式導入は別途記録します。
* 新增口腔遮罩，在唇妝之後保護齒列，並保留前髮遮擋順序；隔離外觀介面對靜態快取的修改，拒絕空透明說話素材。／新增口腔遮罩，在唇妆之后保护牙齿，并保留前发遮挡顺序；隔离外观接口对静态缓存的修改，拒绝空透明说话素材。／Add oral masks that protect teeth after lipstick while retaining foreground-hair occlusion; isolate adapter mutations from static caches and reject empty speech assets.／口紅の後に歯を保護する口腔マスクを追加し、前髪の遮蔽順序を維持します。アダプターによる静的キャッシュの変更を防ぎ、空の発話素材を拒否します。

### 全身閉眼妝容相容性／全身闭眼妆容兼容性／Full-body closed-eye makeup compatibility／全身の閉眼時メイク互換性

- 全身閉眼時沿用半身的眼妝避讓規則，保留腮紅與唇妝，重新睜眼後恢復眼妝。／全身闭眼时沿用半身的眼妆避让规则，保留腮红与唇妆，重新睁眼后恢复眼妆。／Apply the existing half-body eye-makeup suppression rule to closed full-body eyes, preserving blush and lip makeup and restoring eye makeup on reopening.／全身の閉眼時にも半身と同じアイメイク抑制規則を適用し、チークとリップを維持して、開眼時にアイメイクを復元します。
- 支援成對的選填半閉眼與閉眼圖層，載入前要求檔案齊全且尺寸正確；省略此選項時沿用既有動作，正式素材維持原樣。／支持成对的可选半闭眼与闭眼图层，加载前要求文件齐全且尺寸正确；省略此选项时沿用现有动作，正式素材保持原样。／Support optional paired half-closed and closed eyelid layers, requiring complete files and correct dimensions before loading. Omitted layers retain legacy motion, and shipped artwork stays intact.／任意の半閉眼・閉眼レイヤーを対で扱い、読み込み前にファイルの完備と正しい寸法を必須とします。この指定を省略した場合は既存の動作を維持し、正式素材を保持します。

### 衣裝妝容遮擋深度 v2／衣装妆容遮挡深度 v2／Garment makeup occlusion depth v2／衣装メイク遮蔽の奥行き v2

* `occludes_makeup` 是供 `GARMENT_SLOTS` 衣裝或 `headwear` 髮飾資產使用的可選布林欄位；省略時等同 `false`。／`occludes_makeup` 是供 `GARMENT_SLOTS` 衣装或 `headwear` 发饰资源使用的可选布尔字段；省略时等同 `false`。／`occludes_makeup` is an optional boolean field for garment assets in `GARMENT_SLOTS` or `headwear` assets; omission means `false`.／`occludes_makeup` は `GARMENT_SLOTS` の衣装または `headwear` の髪飾りアセットに使える任意ブール欄で、省略時は `false` と同じです。
* 靜態 `apply` 保留 `makeup_prefix_count` 與 `SourceAtop` 的妝容前綴；動畫 `apply_animated` 透過 `split_makeup_depth` 將 `front_hair_indices` 和 `makeup_occluder_indices` 延後。／静态 `apply` 保留 `makeup_prefix_count` 与 `SourceAtop` 的妆容前缀；动画 `apply_animated` 通过 `split_makeup_depth` 将 `front_hair_indices` 和 `makeup_occluder_indices` 延后。／Static `apply` retains the makeup `makeup_prefix_count` and `SourceAtop` prefix; animated `apply_animated` uses `split_makeup_depth` to delay `front_hair_indices` and `makeup_occluder_indices`.／静的な `apply` はメイクの `makeup_prefix_count` と `SourceAtop` プレフィックスを保ち、動的な `apply_animated` は `split_makeup_depth` で `front_hair_indices` と `makeup_occluder_indices` を遅らせます。
* `true` 的前景衣裝在動畫流程於妝容後合成，`false` 或省略則保留 `legacy` 前段；後髮仍在 `behind_body`。／`true` 的前景衣装在动画流程于妆容后合成，`false` 或省略则保留 `legacy` 前段；后发仍在 `behind_body`。／A foreground garment marked `true` is composed after makeup in the animated path; `false` or omission keeps the `legacy` early phase, while rear hair remains in `behind_body`.／`true` の前景衣装は動的な流れでメイクの後に合成し、`false` または省略時は `legacy` の前段に残し、後ろ髪は `behind_body` に保持します。
* 遮擋採用非零 `RGBA` `Alpha`；只有 `Alpha` `0` 透明，部分透明也參與，沒有只接受不透明像素的門檻。／遮挡采用非零 `RGBA` `Alpha`；只有 `Alpha` `0` 透明，部分透明也参与，没有只接受不透明像素的门槛。／Occlusion uses nonzero `RGBA` `Alpha`; only `Alpha` `0` is transparent, partial alpha participates, and there is no opaque-only threshold.／遮蔽は非ゼロの `RGBA` `Alpha` を使い、`Alpha` `0` だけを透明とし、部分透明も参加させ、不透明ピクセルだけの閾値は設けません。
* `tests/test_garment_makeup_occlusion.py` 覆蓋宣告邊界與回歸；技術測試通過不等於素材外觀或外觀包品質核可。此欄位只改變 paint depth，不放寬 protected identity 或手部安全界線。／`tests/test_garment_makeup_occlusion.py` 覆盖声明边界与回归；技术测试通过不等于素材外观或外观包质量核可。该字段只改变 paint depth，不放宽 protected identity 或手部安全边界。／`tests/test_garment_makeup_occlusion.py` covers the declaration boundary and regression; passing technical tests does not approve artwork appearance or outfit-pack quality. The field changes paint depth only and does not relax protected identity or hand-safety boundaries.／`tests/test_garment_makeup_occlusion.py` は宣言境界と回帰をカバーします。技術テストの成功は素材の外観や外観パック品質の承認を意味しません。この欄は paint depth だけを変え、protected identity や手部安全境界を緩和しません。

### 修正手勢匯出的載入順序／修正手势导出的加载顺序／Fix gesture export import order／ジェスチャー公開項目の読み込み順序を修正

- 手勢設定儲存介面的公開型別與匯入匯出函式保持為實際物件，避免先建立主程式服務後暴露未解析的延遲匯入。／手势设置存储接口的公开类型与导入导出函数保持为实际对象，避免先建立主程序服务后暴露未解析的延迟导入。／Keep the gesture store's public types and import/export functions concrete after the presentation composition root loads them.／メインサービスを先に構築した場合も、ジェスチャー設定ストアの公開型と入出力関数を実際のオブジェクトとして保持します。

### 素材核可證據修正／素材核准证据修正／Artwork approval evidence correction／素材承認記録の修正

- 分層建置工具保留輸入素材的來源雜湊，並明示使用者目視核可須以獨立證據查證。／分层构建工具保留输入素材的来源哈希，并明确用户目视核准须以独立证据查证。／The layer builder retains the input artwork source hash and explicitly requires independent evidence of user visual approval.／レイヤー生成ツールは入力素材の出所ハッシュを保持し、ユーザーの目視承認には独立した証拠の確認が必要であることを明示します。

### 墨寒產線永久排除 Krita／墨寒产线永久排除 Krita／Keep Krita permanently outside the MoHan pipeline／Krita を墨寒産線の対象から永久に除外

- 依擁有者 2026-09-07 裁決，將 GPL-3.0 的 Krita 加入工具黑名單，使其永久處於下載、安裝、留存、使用及墨寒素材生成的許可範圍之外；本機套件、下載壓縮檔及相關候選產物均已刪除。／依所有者 2026-09-07 裁决，将 GPL-3.0 的 Krita 加入工具黑名单，使其永久处于下载、安装、留存、使用及墨寒素材生成的许可范围之外；本机套件、下载压缩包及相关候选产物均已删除。／Per the owner's 2026-09-07 ruling, add GPL-3.0 Krita to the tool denylist and keep it permanently outside the permitted scope of downloading, installation, retention, use, and MoHan asset creation; the local package, download archive, and related candidates were deleted.／所有者の 2026-09-07 裁定に従い、GPL-3.0 の Krita をツール除外リストへ追加し、ダウンロード、インストール、保持、使用、墨寒素材生成の許可対象から永久に除外；ローカルパッケージ、ダウンロード書庫、関連候補成果物は削除済み。
- 頂層為 MIT 的 miniPaint 因正式 bundle 內含 GPL-3.0 AlertifyJS 而在開啟任何墨寒素材前完整刪除並永久列入黑名單；下載前授權閘門擴大為實際 bundle、直接與遞移相依的完整查核。／顶层为 MIT 的 miniPaint 因正式 bundle 内含 GPL-3.0 AlertifyJS 而在打开任何墨寒素材前完整删除并永久列入黑名单；下载前许可门禁扩展为实际 bundle、直接与传递依赖的完整核查。／miniPaint was deleted in full and permanently denied before any MoHan asset was opened because its MIT top level ships GPL-3.0 AlertifyJS; the pre-download gate now requires review of the shipped bundle plus direct and transitive dependencies.／最上位が MIT の miniPaint は配布 bundle に GPL-3.0 AlertifyJS を含むため、墨寒素材を一切開く前に完全削除し許可対象から永久に除外；ダウンロード前ゲートを実配布 bundle、直接依存、推移的依存の完全監査へ拡張。

### 修正輪廓外髮絲淡化／修正轮廓外发丝淡化／Fix hair fading outside the body／輪郭外の髪の透過を修正

- 新素體提供可信輪廓後，頭髮只在皮膚交界淡出，並保持桌面背景前方髮絲的覆蓋；五官擴張保護與既有門檻持續有效。／新素体提供可信轮廓后，头发仅在皮肤交界淡出，并保持桌面背景前方发丝的覆盖；五官扩张保护与现有门槛持续有效。／With a trusted body outline, feather hair only against skin and retain hair coverage over the desktop background; preserve dilated feature protection and existing gates.／信頼できる素体輪郭がある場合、肌との境界でのみ髪をぼかし、デスクトップ背景の手前にある髪の被覆を保持します。五官の拡張保護と既存のゲートを維持します。

### 修正半身來源目錄綁定／修正半身来源目录绑定／Fix half-body authority directory binding／半身の参照元ディレクトリの固定を修正

- 半身渲染器建立時固定指定來源目錄的絕對路徑，工作目錄切換後仍載入同一份指定肖像。／半身渲染器创建时固定指定来源目录的绝对路径，工作目录切换后仍加载同一份指定肖像。／Resolve the specified half-body authority directory at renderer construction so the same designated portrait remains bound across working-directory changes.／半身レンダラーの作成時に指定された参照元ディレクトリを絶対パスに固定し、作業ディレクトリ変更後も同じ指定ポートレートを読み込みます。

### 半身眼皮與妝容合成順序／半身眼皮与妆容合成顺序／Half-body eyelid and makeup composition order／半身のまぶたとメイクの合成順序

- 半閉眼及閉眼的原圖遮罩完成後，在同一遮罩範圍補上已驗證的對應眼妝；維持原尺寸校準、妝容濃度、嘴型及遮罩外的像素，舊套件省略狀態素材時，眼線沿用原始畫面。／半闭眼及闭眼的原图遮罩完成后，在同一遮罩范围补上已验证的对应眼妆；维持原尺寸校准、妆容浓度、嘴型及遮罩外的像素，旧套件省略状态素材时，眼线沿用原始画面。／After the authored half or closed eyelid patch, composite its validated eye-state pigment within the same alpha mask. Preserve native calibration, makeup intensity, speech and pixels outside the mask; legacy packs that omit state assets preserve the original eyeliner pixels.／半閉眼または閉眼の原画パッチの後に、検証済みの状態別アイメイクを同じアルファマスク内で合成します。原寸の位置合わせ、濃度、発話中の口とマスク外の画素を維持し、状態素材を省略した従来パックでは元のアイライン画素を保持します。
- 將外觀介面及無外觀實作集中於獨立模組，眨眼執行期負責保留發話畫面，並下修原模組行數基準。／将外观接口及无外观实现集中于独立模块，眨眼运行时负责保留说话画面，并下调原模块行数基准。／Extract appearance contracts and the disabled adapter into a focused module, move archived speech-frame handling to the blink runtime, and lower the original module line baselines.／外観契約と無効時アダプターを専用モジュールに分離し、保存した発話フレームの処理をまばたき実行部へ移し、元のモジュールの行数上限を引き下げます。

### 髮飾動畫繪製順序／发饰动画绘制顺序／Animated headwear paint order／髪飾りの動的描画順序

* 髮飾可明確宣告 `occludes_makeup: true`，與前髮在同一階段依原定順序繪製，避免髮飾被後畫的前髮蓋住。／发饰可明确声明 `occludes_makeup: true`，与前发在同一阶段按原定顺序绘制，避免发饰被后画的前发盖住。／Headwear may explicitly declare `occludes_makeup: true` to share the front-hair paint phase in authored order, preventing later front hair from hiding it.／髪飾りは `occludes_makeup: true` を明示して前髪と同じ段階で指定順に描画でき、後から描く前髪による隠れを防ぎます。
* 省略或 `false` 保留舊繪製階段；身分保護、Alpha、雜湊與錨點驗證不變。測試涵蓋明確啟用、舊預設及半透明髮飾只繪製一次。／省略或 `false` 保留旧绘制阶段；身份保护、Alpha、哈希与锚点验证不变。测试覆盖明确启用、旧默认及半透明发饰只绘制一次。／Omission or `false` preserves the legacy phase and identity, alpha, hash and anchor validation. Tests cover opt-in, legacy defaults and translucent headwear painted exactly once.／省略または `false` では従来の段階と、本人性・Alpha・ハッシュ・アンカー検証を維持します。明示的有効化、従来値、半透明の髪飾りを一度だけ描く動作をテストします。

### 待機姿勢切換競爭／待机姿势切换竞争／Idle pose transition race／待機ポーズ切替の競合

- 自動待機換姿勢會等目前切換完成，避免計時器在淡入途中取代目標姿勢；語音打斷與過期回呼檢查仍保留。所有測試結果都會完成視窗與資料庫清理，並保留原始錯誤。／自动待机换姿势会等当前切换完成，避免计时器在淡入途中替换目标姿势；保留语音中断与过期回调检查。所有测试结果都会完成窗口与数据库清理，并保留原始错误。／Automatic idle pose changes defer while a pose transition is active, preventing timer requests from replacing its target mid-fade. Speech interruption and stale-callback checks remain; all test outcomes close the window and database while preserving the original error.／待機ポーズの自動変更は進行中の切替が終わるまで延期し、フェード途中のタイマーによる切替先の上書きを防ぎます。音声割り込みと古いコールバックの検証は維持し、すべてのテスト結果でウィンドウとデータベースを閉じ、元のエラーを保持します。

### 安裝後穿衣與眨眼回歸／安装后穿衣与眨眼回归／Installed outfit blink regression／インストール後の衣装と瞬きの回帰検証

- 新增實際封裝、安裝、選用外觀後的睜眼、半閉、閉眼與再睜眼合成檢查，核對衣物整區、座標及安裝包雜湊；再睜眼須完整回復原畫面。此測試使用合成素材驗證程式行為。／新增实际封装、安装、选择外观后的睁眼、半闭、闭眼与再次睁眼合成检查，核对完整衣物区域、坐标和安装包哈希；再次睁眼必须恢复原画面。测试使用合成素材验证程序行为。／Add a build-install-select-render regression across rest, half, closed, and reopened eyes. Check the entire garment tile, coordinates, installed archive digest, and exact return to the rest frame using synthetic fixtures.／パックの作成・インストール・選択後に、開眼・半閉眼・閉眼・再開眼を合成して検証します。合成テスト素材で衣装全域、座標、インストール済みアーカイブのハッシュ、元の画像への完全復帰を確認します。

### 眨眼妝容切換／眨眼妆容切换／Blink makeup switching／まばたき時のメイク切替

- 半身與全身切換對應眼妝，保留濃度與保護閘門。／半身与全身切换对应眼妆，保留浓度与保护门槛。／Switch half-body and full-body eye makeup with intensity and protection gates preserved.／半身と全身のアイメイクを切り替え、濃度と保護ゲートを維持。

### 妝容細節獨立調整／妆容细节独立调整／Independent makeup detail controls／メイク詳細の個別調整

- 雲裳閣增加眼妝、腮紅、唇妝濃淡控制，保留整體濃度、舊設定及既有安全區。／云裳阁增加眼妆、腮红、唇妆浓淡控制，保留整体浓度、旧设置及现有安全区。／Add independent eye, blush and lip intensity controls while preserving overall intensity, legacy settings and existing safe regions.／アイメイク、チーク、リップの濃さを個別に調整でき、全体の濃さ、旧設定、既存の安全領域を維持します。

### 妝容設定並行一致性與容錯／妆容设置并行一致性与容错／Concurrent makeup settings consistency and recovery／メイク設定の並行整合性と復旧

* 以設定鎖保護整體與個別妝容濃度的讀改寫，讓平行滑桿更新各自保留。／使用设置锁保护整体与单项妆容浓度的读改写，让并行滑块更新各自保留。／Protect read-modify-write updates for overall and per-slot makeup intensity with a settings lock so each parallel slider update is retained.／設定ロックで全体とスロット別のメイク濃度の読み取り・変更・書き込みを保護し、並行スライダー更新をそれぞれ保持します。
* 未設通知 callback 的讀取失敗會保留後續通知；超大 JSON 整數會安全回退至上一個有效值。／未设置通知 callback 的读取失败会保留后续通知；超大 JSON 整数会安全回退到上一个有效值。／A read that has no notification callback preserves the later notification when it fails, and oversized JSON integers safely fall back to the last valid value.／通知 callback を設定していない読み取りが失敗した場合も後続通知を保持し、巨大な JSON 整数は直前の有効値へ安全にフォールバックします。

### 局部外觀對位固定整圈邊界／局部外观对位固定整圈边界／Local appearance registration pins the full patch boundary／局所的な外観位置合わせで境界全体を固定

* 局部外觀對位可固定整圈邊界，避免袖口周圍產生接縫；移動控制點須位於過渡區內側，完成對位後仍檢查變形折疊。／局部外观对位可固定整圈边界，避免袖口周围产生接缝；移动控制点须位于过渡区内侧，完成对位后仍检查变形折叠。／Local appearance registration can fix the entire patch boundary to prevent cuff seams. Moving controls must stay beyond the transition band, and the final map is checked for folds.／局所的な外観位置合わせで領域の境界全体を固定し、袖口周囲の継ぎ目を防げます。移動する制御点は遷移帯より内側に配置し、最終変換の折り返しも検証します。

### 修正嘴型中心資料驗證／修正嘴型中心数据验证／Fix mouth authority metadata validation／口形状の参照データ検証を修正

- 只採用格式正確且版本為整數的嘴型資料容器；布林值、非有限值及畫布外座標維持在有效輸入契約之外，其他有效視角持續保留，載入與嘴型位置維持穩定。／仅采用格式正确且版本为整数的嘴型数据容器；布尔值、非有限值及画布外坐标维持在有效输入契约之外，其他有效视角持续保留，加载与嘴型位置维持稳定。／Use well-formed mouth metadata containers with integer versions; keep boolean, non-finite and out-of-canvas centers outside the accepted input contract, retain other valid views, and keep loading and mouth placement stable.／形式が正しくバージョンが整数の口形状メタデータだけを使用し、真偽値・非有限値・キャンバス外の中心座標は受け入れ対象外として扱います。有効な他の視点を保持し、読み込みと口形状の配置を安定させます。

### MPL-2.0 合規條件與所有權文件／MPL-2.0 合规条件与所有权文件／MPL-2.0 Compliance Conditions and Ownership Documentation／MPL-2.0 コンプライアンス条件と所有権文書

- 新增 ownership docs/MPL-2.0-COMPLIANCE.md，整理 MPL-2.0 §1.4、§1.10、§2.1、§3.1–§3.5 與 FAQ Q5、Q6、Q8、Q11 的內部使用、對外散布、檔案級 source、notices、修改紀錄與商業使用條件／新增 ownership docs/MPL-2.0-COMPLIANCE.md，整理 MPL-2.0 §1.4、§1.10、§2.1、§3.1–§3.5 以及 FAQ Q5、Q6、Q8、Q11 的内部使用、对外分发、文件级 source、notices、修改记录和商业使用条件／Added ownership docs/MPL-2.0-COMPLIANCE.md covering MPL-2.0 §§1.4, 1.10, 2.1, 3.1–3.5 and FAQ Q5, Q6, Q8, Q11 for internal use, external distribution, file-level source delivery, notices, modification records, and commercial use／ownership docs/MPL-2.0-COMPLIANCE.md を追加し、MPL-2.0 §1.4、§1.10、§2.1、§3.1–§3.5 と FAQ Q5、Q6、Q8、Q11 の内部利用、外部配布、ファイル単位の source 提供、notices、変更記録、商用利用条件を整理
- 引用正式套件級 manifest third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1），保留 certifi 2026.7.22 的 MPL-2.0、tqdm 4.70.0 的 MPL-2.0 AND MIT、orjson 3.12.0 的 MPL-2.0 AND (Apache-2.0 OR MIT) 與對應 source、license、notice 路徑／引用正式软件包级 manifest third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1），保留 certifi 2026.7.22 的 MPL-2.0、tqdm 4.70.0 的 MPL-2.0 AND MIT、orjson 3.12.0 的 MPL-2.0 AND (Apache-2.0 OR MIT) 及对应 source、license、notice 路径／Referenced the formal package-level manifest at third_party_licenses/mpl/components.json (schema mohan.mpl-compliance.v1), preserving certifi 2026.7.22 as MPL-2.0, tqdm 4.70.0 as MPL-2.0 AND MIT, orjson 3.12.0 as MPL-2.0 AND (Apache-2.0 OR MIT), and their source, license, and notice paths／正式なパッケージ単位 manifest third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1）を参照し、certifi 2026.7.22 の MPL-2.0、tqdm 4.70.0 の MPL-2.0 AND MIT、orjson 3.12.0 の MPL-2.0 AND (Apache-2.0 OR MIT) と対応する source、license、notice の場所を保持
- 依來源紀錄保留 MIT AND MPL，不改寫成 MIT OR MPL；不含 MPL 程式碼的本專案自有檔案維持原授權，並保留第三方著作權、專利、商標、免責與責任限制／依据来源记录保留 MIT AND MPL，不改写成 MIT OR MPL；不含 MPL 代码的本项目自有文件维持原许可，并保留第三方著作权、专利、商标、免责声明和责任限制／Preserve MIT AND MPL source records as written; first-party files with no MPL code keep their own licensing, while third-party copyright, patent, trademark, disclaimer, and limitation rights remain intact／出所記録の MIT AND MPL をそのまま保持し、MPL コードを含まない自社ファイルは元のライセンスを維持します。第三者の著作権、特許、商標、免責、責任制限も保持します。
- 文件建立條件與審查輸入，並讓白名單、runtime 狀態及完整正式發行驗證維持在既有邊界；root 仍須以套件級 receipt 完成最終授權／文档建立条件和审查输入，并让白名单、runtime 状态及完整正式发布验证维持在既有边界；root 仍须通过软件包级 receipt 完成最终授权／The document adds conditions and review inputs while keeping the allowlist, runtime state, and formal-release verification status within their existing boundaries. Root completes final authorization with a package-level receipt／本文書は条件とレビュー入力を追加し、allowlist、runtime の状態、正式リリース検証の状態を既存の境界内に保ちます。最終認可は root がパッケージ単位 receipt で完了します。

### 保留原生去背資料／保留原生去背数据／Preserve native matting data／元の切り抜きデータを保持

- 分層審閱新增明確的原生 Alpha 模式，保留可見像素與柔邊，讓透明度由 Alpha 通道判定並維持 RGB 棋盤格的實色內容；既有洋紅鍵色流程保持相容。／分层审阅新增明确的原生 Alpha 模式，保留可见像素与柔边，让透明度由 Alpha 通道判定并维持 RGB 棋盘格的实色内容；既有洋红键色流程保持兼容。／Partition review adds an explicit native-alpha mode that preserves visible pixels and soft edges, derives transparency from the alpha channel, and keeps RGB checkerboards as visible source content; existing magenta keying remains compatible.／分割レビューに明示的な元のアルファモードを追加し、可視画素と半透明の輪郭を保持します。透明度はアルファチャンネルで判定し、RGB の市松模様は可視の元データとして扱います。従来のマゼンタキー処理との互換性を維持します。

### −15° 可拆漢服對齊原生手腳／−15° 可拆汉服对齐原生手脚／Align the −15° detachable hanfu to native hands and feet／−15° の着脱可能な漢服を元の手足に合わせる

* −15° 可拆漢服的袖口接回原生雙手，裙襬與鞋底對齊原生腳掌。可拆外觀的四個眼睛狀態通過正式合成比對，24 張原生來源維持原雜湊。／−15° 可拆汉服的袖口接回原生双手，裙摆与鞋底对齐原生脚掌。可拆外观的四个眼睛状态通过正式合成比对，24 张原生来源保持原哈希。／Connect the −15° detachable hanfu cuffs to native hands, and register the hem and soles to native feet. Formal renders match the detachable candidate across four eye states; all 24 native source hashes remain unchanged.／−15° の着せ替え可能な漢服の袖口を元の両手に接続し、裾と靴底を元の足に合わせました。四つの目の状態で正式合成と着せ替え候補が一致し、24 枚の元画像のハッシュは維持されています。

### −30° 可拆漢服對齊原生手腳／−30° 可拆汉服对齐原生手脚／Align the −30° detachable hanfu to native hands and feet／−30° の着脱可能な漢服を元の手足に合わせる

* −30° 可拆漢服的袖口接回原生雙手，裙襬與鞋底對齊原生腳掌。可拆外觀的四個眼睛狀態通過正式合成比對，24 張原生來源維持原雜湊。／−30° 可拆汉服的袖口接回原生双手，裙摆与鞋底对齐原生脚掌。可拆外观的四个眼睛状态通过正式合成比对，24 张原生来源保持原哈希。／Connect the −30° detachable hanfu cuffs to native hands, and register the hem and soles to native feet. Formal renders match the detachable candidate across four eye states; all 24 native source hashes remain unchanged.／−30° の着せ替え可能な漢服の袖口を元の両手に接続し、裾と靴底を元の足に合わせました。四つの目の状態で正式合成と着せ替え候補が一致し、24 枚の元画像のハッシュは維持されています。

### 原生嘴部校準／原生嘴部校准／Native mouth calibration／原画像の口位置校正

- 依目前 13 個可見唇層重建嘴部中心資料，記錄來源雜湊，並核對口腔範圍與原生嘴唇一致。／根据当前 13 个可见唇层重建嘴部中心数据，记录来源哈希，并核对口腔范围与原生嘴唇一致。／Rebuild mouth centers from the current 13 visible lip-layer pairs, record their hashes, and check that speech cavities stay within the authored lip bounds.／現在の可視な 13 組の唇レイヤーから口の中心を再計測し、ハッシュを記録して発話領域が元の唇の範囲内に収まることを確認します。

### 停用外觀時的眨眼介面／停用外观时的眨眼接口／Blink contract with appearances disabled／外観無効時のまばたきインターフェース

- 統一外觀介面與空白實作的眼睛狀態參數，讓半閉眼及閉眼沿用相容參數持續顯示，並保留原始畫面。／统一外观接口与空白实现的眼睛状态参数，让半闭眼及闭眼沿用兼容参数持续显示，并保留原始画面。／Align the appearance port and disabled adapter with the shared eye-state argument contract so half and closed blinks preserve the frame.／外観ポートと無効時アダプターの目の状態引数を統一し、半閉眼と閉眼が共通の互換引数でフレームを保持できるようにします。

### 以墨寒原型作為藍白漢服設計依據／以墨寒原型作为蓝白汉服设计依据／Adopt the original MoHan prototype as the hanfu design authority／墨寒の原型を漢服デザインの基準とする

* 以擁有者提供的墨寒原型作為整套藍白漢服的設計依據，明列左右前襟各一個白色寶劍劍紋。加入原圖雜湊、視角遮擋與推補範圍的審閱規則；既有 V4 衍生衣服依新原型重新審閱。／以所有者提供的墨寒原型作为整套蓝白汉服的设计依据，明确左右前襟各有一个白色宝剑剑纹。加入原图哈希、视角遮挡与补全范围的审阅规则；现有 V4 衍生衣服按新原型重新审阅。／Establish the owner's original MoHan prototype as the design authority for the complete blue-white hanfu, with one white sword motif on each front panel. Document source hashes, view occlusion and inferred extensions; review existing V4-derived garments against this original.／所有者が提供した墨寒の原型を青白漢服全体のデザイン基準とし、左右の前身頃に白い宝剣文様を一つずつ配置することを明記しました。原画のハッシュ、視点による遮蔽、補完範囲の確認規則を追加し、既存の V4 由来の衣装を原型に基づいて再確認します。
* 正面、左右 15° 及左右 30° 衣層改用原型的深藍薄紗、雙劍紋及兩排腰帶白紋，保留原生臉、身體與雙手。袖口依手腕對位並修整遮擋邊界，裙襬保留薄紗軟邊；＋30° 同時清除耳下髮層的膚色殘邊、恢復銀鏈並修正髮飾遮擋順序。其餘視角持續逐一重建與審閱。／正面、左右 15° 及左右 30° 衣层改用原型的深蓝薄纱、双剑纹及两排腰带白纹，保留原生脸、身体与双手。袖口按手腕对齐并修整遮挡边界，裙摆保留薄纱软边；＋30° 同时清除耳下发层的肤色残边、恢复银链并修正发饰遮挡顺序。其余视角继续逐一重建与审阅。／Rebuild the front, both 15° and both 30° garments with the prototype's deep blue gauze, two sword motifs and two sash embroidery rows while retaining the native face, body and hands. Register cuffs to the wrists and refine their occlusion boundaries while preserving the soft gauze hem. The +30° view also removes donor-skin residue below the ear, restores the silver chains and corrects headwear occlusion order. Other views remain under individual reconstruction and review.／正面、左右 15°、左右 30° の衣装を原型の濃い青の薄絹、二つの剣文様、二段の帯の白い文様で再構成し、元の顔、身体、両手を保持しました。袖口を手首に合わせて遮蔽境界を調整し、薄絹の裾の柔らかい縁を保持します。＋30° では耳の下の髪レイヤーに残った肌色を除去し、銀の鎖と髪飾りの遮蔽順序も修正しました。他の視点は個別に再構成と確認を続けます。
* −45° 加入原型衣裝與繡鞋，清除手指間夾帶的腿部皮膚，保留原生手部像素。完整髮片與前髮束的疊放修正衣領截斷；髮飾恢復原圖可見的上段雙銀鏈，保留中段被頭髮遮住的部分。／−45° 加入原型衣装与绣鞋，清除手指间夹带的腿部皮肤，保留原生手部像素。完整发片与前发束的叠放修正衣领截断；发饰恢复原图可见的上段双银链，保留中段被头发遮住的部分。／Add the prototype outfit and embroidered shoes at −45°, removing leg pixels between the fingers while preserving native hand pixels. Restore complete hair and place the front locks over the collar. Recover the donor-visible upper twin silver chains while retaining the middle section's natural occlusion by hair.／−45° に原型の衣装と刺繍靴を追加し、元の手の画素を保持しながら指の間に残った脚の画素を除去しました。完全な髪レイヤーと前髪束の重なりを修正し、襟による切断を解消しました。髪飾りは原画で見える上部の二本の銀鎖を復元し、中間部分が髪に隠れる状態を保持します。
* −60° 加入原型衣裝與繡鞋，依原生手掌對齊袖口並清除夾帶的短褲與腿部碎片。可拆前髮束銜接原生鬢髮，保留原生臉與髮飾；實際程式的四種眼睛狀態均維持完整衣裝。／−60° 加入原型衣装与绣鞋，按原生手掌对齐袖口并清除夹带的短裤与腿部碎片。可拆前发束衔接原生鬓发，保留原生脸与发饰；实际程序的四种眼睛状态均保持完整衣装。／Add the prototype outfit and embroidered shoes at −60°, register cuffs to native palms, and remove shorts and leg fragments carried by the hand masks. Join detachable front locks to native temple hair while preserving the native face and headwear. All four runtime eye states retain the complete outfit.／−60° に原型の衣装と刺繍靴を追加し、元の手のひらに袖口を合わせ、手のマスクに残った短パンと脚の断片を除去しました。着脱可能な前髪束を元のこめかみの髪につなぎ、元の顔と髪飾りを保持します。実行時の四つの目の状態で衣装全体が維持されます。

### 外觀包畫布與透明通道契約／外观包画布与透明通道契约／Outfit-pack canvas and alpha contract／外観パックのキャンバスとアルファ契約

- 封裝與匯入時即核對 runtime appearance PNG 的透明通道、garment 可見像素，以及每一視角的 half-body/full-body 畫布邊界；保留裁切圖、正 anchor 與合法空白 hairstyle back 的相容性。／封装与导入时即核对 runtime appearance PNG 的透明通道、garment 可见像素，以及每一视角的 half-body/full-body 画布边界；保留裁切图、正 anchor 与合法空白 hairstyle back 的兼容性。／Validate runtime appearance PNG alpha, visible garment pixels, and per-view half-body/full-body canvas bounds during sealing and import, while retaining cropped tiles, positive anchors, and intentionally empty hairstyle back layers.／パックの封印・取り込み時に、runtime appearance PNG のアルファ、衣装の可視ピクセル、視点ごとの half-body/full-body キャンバス境界を検証します。切り抜きタイル、正の anchor、意図的に空の hairstyle back レイヤーとの互換性は維持します。

- 妝容先驗證整張畫布及原點對齊要求，保留既有明確錯誤，再執行共用邊界與 PNG 檢查。／妆容先验证整张画布及原点对齐要求，保留既有明确错误，再执行共用边界与 PNG 检查。／Makeup validates its full-canvas, zero-anchor contract before shared bounds and PNG checks, preserving the existing precise error.／メイクは共通の境界と PNG 検証の前に全面キャンバスと原点配置を検証し、従来の明確なエラーを維持します。

### 分層審閱來源鎖定／分层审阅来源锁定／Bind partition review sources／レイヤーレビュー元画像の固定

- 分層預覽可指定已審閱候選的 SHA-256，並在輸出前維持原圖與分區圖的雜湊綁定；既有呼叫保持相容，藝術驗收與正式接入仍各自依正式閘門判定。／分层预览可指定已审阅候选的 SHA-256，并在输出前维持原图与分区图的哈希绑定；现有调用保持兼容，美术批准与正式接入仍分别按正式关卡判定。／Partition previews accept a reviewed candidate SHA-256 and keep source and semantic-map bytes bound to that digest through output; existing callers remain compatible, while visual acceptance and production integration stay as separate formal gates.／レイヤープレビューはレビュー済み候補の SHA-256 を指定でき、出力まで元画像と領域マップのバイト列をそのダイジェストに固定します。既存の呼び出し互換性を維持し、外観承認と正式導入はそれぞれ正式な関門で判定します。

### 產線匯入契約／产线导入契约／Pipeline import contract／パイプラインのインポート契約

- 分層、授權檢查及新增回歸測試遵循 Python 3.15 延遲匯入規則；外觀包既有例外型別的相容匯出保持直接匯入，內部驗證函式分開載入。／分层、授权检查及新增回归测试遵循 Python 3.15 延迟导入规则；外观包既有异常类型的兼容导出保持直接导入，内部验证函数分开加载。／Partition tools, license checks, and added regression tests follow Python 3.15 lazy imports. Existing outfit exception re-exports remain eager, with internal validation functions imported separately.／分割ツール、ライセンス検査、追加回帰テストに Python 3.15 の遅延インポート規則を適用します。既存の衣装例外型の再エクスポートは即時読み込みを維持し、内部検証関数を分離します。

### 可攜式眨眼綁定／可移植眨眼绑定／Portable blink binding／移動可能なまばたきバインディング

- 新增 v2 相對路徑契約，素材搬移後持續驗證來源與眨眼 PNG 雜湊；保留 v1 相容性。／新增 v2 相对路径契约，素材移动后持续验证来源与眨眼 PNG 哈希；保留 v1 兼容性。／Add a v2 relative-path contract that verifies source and blink PNG hashes after atlas relocation, retaining v1 compatibility.／v2 相対パス契約を追加し、atlas 移動後もソースとまばたき PNG のハッシュを検証し、v1 互換性を維持します。

### 視角來源雜湊驗證／视角来源哈希验证／View source digest validation／視点参照元のハッシュ検証

- 建立 PoseAtlas 時只接受格式正確、來源可讀且內容相符的已宣告 PNG 雜湊；未宣告雜湊的舊格式 metadata 仍沿用相容路徑。／创建 PoseAtlas 时只接受格式正确、源文件可读且内容相符的已声明 PNG 哈希；未声明哈希的旧格式 metadata 仍沿用兼容路径。／Construct PoseAtlas with declared PNG digests only when their format, source readability, and content match; older metadata without a declared digest continues through the compatibility path.／PoseAtlas の構築時は、形式、参照元の読み取り、内容が一致する宣言済み PNG ダイジェストを使用し、ダイジェストを宣言しない旧メタデータは互換経路で処理します。

### 姿態圖集身分量測邊界／姿态图集身份测量边界／PoseAtlas identity measurement boundary／PoseAtlas 本人性計測境界

- 新增來源綁定的 24 視角人物高度與原生臉部點盤點，沿用既有尺度稽核並如實保留缺少幾何簽章及尺度漂移的阻擋狀態。／新增来源绑定的 24 视角人物高度与原生脸部点盘点，沿用现有尺度审计并如实保留缺少几何签名及尺度漂移的阻挡状态。／Add source-bound 24-view subject-height and native-face inventory, reuse the existing scale audit, and preserve the blocked state for missing geometry signatures and scale drift.／原画に結び付けた 24 視点の人物高とネイティブ顔点の一覧を追加し、既存の尺度監査を再利用して、形状シグネチャ欠落と尺度ずれによる阻止状態をそのまま記録します。

### 全身圖層與來源一致性／全身图层与来源一致性／Full-body layer and source consistency／全身レイヤーと参照元の整合性

- 前面與側面視角的載入條件要求標準圖層齊全；背面保留既有透明臉層省略規則。／正面与侧面视角的加载条件要求标准图层齐全；背面保留现有透明脸层省略规则。／Require complete standard layers for front and side views while retaining the existing rear-view omission rule for invisible facial layers.／正面と側面では標準レイヤーの完備を読み込み条件とし、背面で不可視の顔レイヤーを省略できる既存規則を維持します。
- PoseAtlas 素材目錄對齊目前渲染器的來源，讓各世代中繼資料與實際畫面保持一致。／PoseAtlas 素材目录对齐当前渲染器的来源，让各代元数据与实际画面保持一致。／Keep the PoseAtlas metadata directory aligned with the current renderer authority so metadata and rendered content stay within the same generation.／PoseAtlas のメタデータディレクトリを現在のレンダラーの参照元に合わせ、メタデータと描画内容を同じ世代に保ちます。
- 檢查 24 筆視角是否唯一且與角度相符，確保完整視角由互異紀錄構成。／检查 24 条视角是否唯一且与角度相符，确保完整视角由互异记录构成。／Validate unique canonical view identities and matching yaw values, ensuring that a complete view ring consists of unique records.／24 件の視点が重複せず正規の角度と一致することを検証し、重複レコードによる完全な視点集合の誤認を防ぎます。
- 載入時檢查圖層 PNG 結構與 RGBA 格式，首次渲染解碼失敗會報錯並保留明確診斷，讓每個圖層結果都可追蹤。／加载时检查图层 PNG 结构与 RGBA 格式，首次渲染解码失败会报错并保留明确诊断，让每个图层结果都可追踪。／Check layer PNG structure and RGBA format on load, and report decoding failures on first render with explicit diagnostics so every layer result remains traceable.／読み込み時にレイヤー PNG の構造と RGBA 形式を検証し、初回描画でデコードに失敗した場合は明示的な診断を報告して、各レイヤーの結果を追跡可能にします。

### 素體啟動降級診斷／素体启动降级诊断／Body startup fallback diagnostics／素体起動時のフォールバック診断

- 將既有半身畫面快照移至獨立模組，保持繪製行為並下修核心模組行數上限。／将既有半身画面快照移至独立模块，保持绘制行为并下调核心模块行数上限。／Move the existing half-body snapshot into a dedicated module, preserving rendering behavior and lowering the core module line-count limit.／既存の半身スナップショットを専用モジュールへ移し、描画動作を維持してコアモジュールの行数上限を引き下げます。

- 自適應素體需要復原時保留既有半身畫面，並記錄只含安全摘要的診斷事件；原始例外文字、路徑與秘密維持在事件之外。錯誤事件僅由啟動異常路徑產生。／自适应素体需要恢复时保留现有半身画面，并记录只含安全摘要的诊断事件；原始异常文本、路径和秘密维持在事件之外。错误事件仅由启动异常路径产生。／When adaptive body startup requires recovery, retain the existing half-body fallback and record a sanitized diagnostic event with raw exception text, paths, and secrets kept outside the event. Error events are emitted only on the startup-error path.／適応型素体の起動に復旧が必要な場合は既存の半身表示を維持し、安全な要約だけを診断イベントに記録します。例外の生テキスト、パス、秘密情報はイベントの外に保ち、エラーイベントは起動エラーの経路だけで記録します。

### 素體清冊讀取與安全回退／素体清册读取与安全回退／Body metadata reading and safe fallback／素体メタデータの読み込みと安全なフォールバック

- 素體清冊進入復原狀態時，角色視窗沿用半身畫面並記錄安全診斷；原始檔案路徑維持在診斷內容之外。／素体清册进入恢复状态时，角色窗口沿用半身画面并记录安全诊断；原始文件路径维持在诊断内容之外。／When body metadata requires recovery, keep the character window on its half-body fallback and record sanitized diagnostics with raw file paths kept outside the diagnostic content.／素体メタデータに復旧が必要な場合は半身表示で起動を継続し、安全な診断を記録します。生のファイルパスは診断内容の外に保ちます。

### 半身姿勢手部歸屬／半身姿势手部归属／Half-body pose hand ownership／半身姿勢の手の所有領域

- 半身優先讀取逐姿勢左右手，保留舊骨架相容性；載入條件要求逐姿勢檔案完整可用，且明確透明的雙手維持該姿勢的空集合。／半身优先读取逐姿势左右手，保留旧骨架兼容性；加载条件要求逐姿势文件完整可用，且明确透明的双手维持该姿势的空集合。／Prefer pose-specific half-body hand pairs while preserving legacy rig compatibility; require intact pairs and respect explicitly hidden hands.／半身の姿勢別手マスクを優先して既存リグとの互換性を維持し、完全で正常な組を読み込み条件とし、明示的に隠れた手を尊重します。

### 修正預覽版原生圖層封裝／修正预览版原生图层封装／Fix preview native layer packaging／プレビュー版のネイティブレイヤー同梱を修正

- 預覽版包含素體時，同步封裝現有身體、手部、外觀輪廓與替換遮罩，保留已修正的分層組裝效果。／预览版包含素体时，同步封装现有身体、手部、外观轮廓与替换遮罩，保留已修正的分层组装效果。／When the preview includes the body atlas, bundle existing body and hand overrides, appearance silhouettes, and replacement masks so layered composition retains its repairs.／プレビュー版に素体アトラスを含める場合、既存の身体・手の補正レイヤー、外観輪郭、置換マスクも同梱し、修正済みのレイヤー合成を維持します。

### 補齊專案規範查核索引／补齐项目规范检查索引／Add project rules verification index／プロジェクト規範の検証索引を追加

- 整理既有架構、安全、授權、四語、素材與發布規範的來源，區分歷史紀錄與現行裁決，並明訂自然遮擋屬於正常組裝關係，與解剖缺陷分開判定。／整理既有架构、安全、许可、四语、素材与发布规范的来源，区分历史记录与现行裁决，并明确自然遮挡属于正常组装关系，与解剖缺陷分别判定。／Index existing architecture, security, licensing, localization, asset and release rules, distinguish historical records from current decisions, and state that natural occlusion is a normal composition relationship assessed separately from anatomical defects.／既存のアーキテクチャ、安全性、ライセンス、四言語、素材、公開規範の参照先を整理し、履歴と現行判断を区別します。自然な遮蔽は通常の合成関係として、解剖上の欠陥とは分けて判定します。

### 後髮遮擋／后发遮挡／Rear-hair occlusion／後ろ髪の遮蔽

- 後髮先合成在身體後方，前髮維持覆在服裝上；保留原生半透明髮際，讓耳側覆蓋完整且邊緣維持原生透明度。／后发先合成在身体后方，前发保持覆盖服装；保留原生半透明发际，让耳侧覆盖完整且边缘保持原生透明度。／Composite rear hair behind the body while keeping front hair above clothing; preserve translucent native hairline edges so ear-side coverage stays complete and its edges retain native transparency.／後ろ髪を身体の背後に合成し、前髪は衣装の手前に維持します。元画像の半透明の生え際を保持し、耳側の被覆を完全にして輪郭の透明度を保ちます。

- 獨立卸下髮飾或切換髮型時，衣鞋持續遮擋身體，頭部區域維持所選髮型與輪廓。／独立卸下发饰或切换发型时，衣鞋持续遮挡身体，头部区域维持所选发型与轮廓。／Keep garment and shoe occlusion when switching hair or removing headwear independently, with the selected head silhouette and garment coverage retained.／髪飾りの取り外しや髪型の切り替えでも衣装と靴の遮蔽を維持し、選択した髪型と頭部の輪郭を保ちます。

### 核可分區批次入口／核可分区批次入口／Reviewed partition batch entry point／確認済み領域のバッチ入口

- 將不同已驗收批次的同視角分區彙整為單一原生組裝輸入，讓來源、角色與區域各自維持唯一且互斥，剩餘區域保持單次組裝。／将不同已验收批次的同视角分区汇总为单一原生组装输入，让来源、角色与区域各自保持唯一且互斥，剩余区域保持单次组装。／Consolidate completed same-view partitions into one native assembly input with source, role, and region uniqueness enforced; compose each remainder once.／完了済みバッチの同一視点領域を単一の原寸組立入力に統合し、原画、役割、領域の一意性と排他性を保ち、残部を一度だけ合成します。

- 驗證明列雜湊的審閱對照圖與修正紀錄，讓交付後及編碼期間的證據維持原值；保留舊版描述文字相容性。／验证明确哈希的审阅对照图与修正记录，让交付后及编码期间的证据保持原值；保留旧版描述文字兼容性。／Validate explicitly hashed review evidence and traces, keeping evidence fixed after review and throughout encoding while retaining compatibility with legacy descriptive notes.／ハッシュ付き確認画像と修正記録を検証し、確認後とエンコード中も証拠を固定して、旧形式の説明文との互換性を維持します。

- 統一接入原生可見分區並鎖定來源，讓遮罩互斥與覆寫受到保護，保留未分類區域與逐像素重組證據。／统一接入原始可见分区并锁定来源，让遮罩互斥与覆盖受到保护，保留未分类区域及逐像素重组证据。／Integrate native visible partitions with source binding, protected overlap and overwrite boundaries, an explicit unclassified remainder, and exact reconstruction evidence.／原寸の可視領域を統合して原画を固定し、マスクの排他性と上書き境界を保護し、未分類の残部と画素一致の証拠を保持します。
- 直接核對 PNG 原始位元深度，僅接受原生 8 位元來源，通過檢查後才可記錄精確保留證據。／直接核对 PNG 原始位深，仅接受原生 8 位来源，通过检查后才可记录精确保留证据。／Validate the original PNG bit depth and admit only native 8-bit sources before recording exact-preservation evidence.／PNG の元のビット深度を検証し、原生の 8 ビット画像だけを受け入れてから、完全保持の証拠を記録します。

- 彙整時交叉驗證完成收據、原生輸出像素與完整目錄，讓影像內容與宣告雜湊保持一致。／汇总时交叉验证完成收据、原始输出像素与完整目录，让图像内容与声明哈希保持一致。／Cross-check completed receipts, native output pixels, and complete directories so image content and declared hashes remain consistent.／完了受領記録、原寸出力画素、完全なディレクトリを照合し、画像内容と宣言ハッシュの整合性を保持します。

### 接入可見手部分區／接入可见手部分区／Integrate visible hand partitions／可視の手領域を統合

- 可見分區產線新增解剖學左手與右手角色，沿用來源、目視審閱、互斥像素與完成收據驗證；腕部分界留下原生座標，未顯露的手部維持待完成狀態。／可见分区产线新增解剖学左手与右手角色，沿用来源、目视审阅、互斥像素与完成收据验证；腕部分界保留原始坐标，未显露的手部维持待完成状态。／Support anatomical left/right visible hand partitions with the existing source, visual-review, disjoint-pixel and receipt checks; record native wrist seams, and keep hidden-hand coverage in a pending state.／解剖学的な左右の可視手領域を追加し、原画・目視確認・排他的画素・完了記録の検証を維持します。手首の原寸境界を記録し、隠れた手の範囲は保留状態にします。

### 手部遮擋資料共用／手部遮挡数据共用／Shared hand-region data／手の遮蔽領域の共有

- 角色與衣櫃共用同一組裝邊界已驗證的手部遮擋資料，減少重複讀取。每次取得的區域仍可各自修改；省略資料時沿用既有處理，左右配對完整為載入條件。新增單次載入、修改隔離及錯誤回歸測試。／角色与衣柜共用同一组装边界已验证的手部遮挡数据，减少重复读取。每次取得的区域仍可各自修改；缺失数据沿用既有处理，不完整的左右配对仍拒绝加载。新增单次加载、修改隔离及错误回归测试。／Character and wardrobe overlays share validated hand-region data within one composition root. Returned regions remain independently mutable. Omitted data retains legacy handling, and complete left/right pairs remain the loading condition. Regression tests cover one load, mutation isolation, and errors.／同一コンポジションルート内で、キャラクターと衣装表示が検証済みの手の遮蔽領域を共有し、重複読み込みを減らします。取得した領域は個別に変更でき、データ省略時の既存処理を維持し、左右ペアの完備を読み込み条件とします。読み込み回数、変更の分離、エラーを回帰テストで検証します。

### 共用已安裝外觀包驗證／共用已安装外观包验证／Shared installed outfit validation／インストール済み外観パック検証の共有

- 新增同一顯示實例暖切換兩個已安裝封包的整合測試，確認目前選擇與來源像素更新，封包內容保持不變。／新增同一显示实例暖切换两个已安装封包的集成测试，确认当前选择与来源像素更新，封包内容保持不变。／A warm-switch integration test verifies that one overlay changes its selection and rendered pixels between two installed packs while preserving both archives.／同じ表示インスタンスで二つのインストール済みパックを切り替え、選択と描画ピクセルの更新、および両アーカイブの不変性を検証します。

- 外觀選單與顯示端共用既有封包驗證快取，切換姿勢時降低重複解碼；封包時間或大小變動仍觸發驗證，完整且相容的封包才進入使用流程。／外观菜单与显示端共用现有封包验证缓存，切换姿势时降低重复解码；封包时间或大小变化时仍触发验证，完整且兼容的封包才进入使用流程。／Appearance selection and rendering share the existing validated archive cache to reduce duplicate decoding during pose changes. Timestamp or size changes still trigger validation, and only intact compatible archives enter use.／外観選択と描画で既存の検証済みアーカイブキャッシュを共有し、ポーズ変更時の重複デコードを削減します。更新時刻やサイズの変更時は再検証し、完全で互換性のあるパックだけを使用します。

- 全身眨眼測試直接從定義模組載入圖層順序，修正首次執行時讀到未解析延後載入物件的錯誤。／全身眨眼测试直接从定义模块加载图层顺序，修复首次执行时读取到未解析延迟加载对象的问题。／The full-body blink test imports layer order from its defining module, fixing unresolved lazy-import access on its first execution.／全身瞬きテストはレイヤー順序を定義元から直接インポートし、初回実行時の未解決遅延インポート参照を修正します。

### 語音關窗回呼生命週期修復／语音关窗回调生命周期修复／Fix speech callback lifetime during shutdown／音声コールバックの終了時ライフサイクルを修正

- 關閉墨寒視窗時使延遲語音完成回呼失效，讓資料庫關閉後晚到回呼維持無資料庫存取權。／关闭墨寒窗口时使延迟语音完成回调失效，让数据库关闭后迟到回调维持无数据库访问权。／Invalidate delayed speech completion callbacks when the MoHan window closes; late callbacks retain no database access after closure.／墨寒ウィンドウの終了時に遅延音声完了コールバックを無効化し、データベースの終了後も遅延コールバックにデータベースへのアクセス権を与えません。

### 眨眼影格待備時固定素體來源／眨眼帧待备时固定素体来源／Freeze body authorities while authored blink frames are pending／まばたきフレーム準備中の素体参照元を固定

- 指定素體來源目錄時，在眨眼影格仍待提供時，也會在載入清單時固定原圖位元組，確保磁碟檔案更新後修補區域仍使用原先固定的臉；預設素材路徑維持原行為。／指定素体来源目录时，在眨眼帧仍待提供时，也会在加载清单时固定原图字节，确保磁盘文件更新后修补区域仍使用原先固定的脸；默认素材路径维持原行为。／When a body authority directory is specified, snapshot source bytes on manifest load while authored blink frames remain pending, keeping restoration regions bound to the original face across later disk updates; default asset paths retain their existing behavior.／素体の参照元ディレクトリを指定した場合、まばたきフレームが準備中でもマニフェスト読み込み時に元画像のバイト列を固定し、その後のファイル更新時も復元領域を元の顔に固定します。既定の素材パスの動作は維持されます。

### 正面可拆漢服對齊原生手腳／正面可拆汉服对齐原生手脚／Align the front detachable hanfu to native hands and feet／正面の着脱可能な漢服を元の手足に合わせる

* 正面可拆漢服的袖口連接原生雙手，白鞋依原生足底位置對齊。保留可拆換外觀及四個眼睛狀態的組合。／正面可拆汉服的袖口连接原生双手，白鞋依原生足底位置对齐。保留可拆换外观及四个眼睛状态的组合。／Connect the front detachable hanfu cuffs to native hands, and register white shoes to the native soles. Preserve detachable appearance composition across four eye states.／正面の着せ替え可能な漢服の袖口を元の両手に接続し、白い靴を元の足底位置に合わせました。着せ替え可能な外観と四つの目の状態の合成を維持します。
* 預設外觀檢查保留原取樣位置的精確衣料色值，另以固定藍布取樣位置確認配色與覆蓋；沿用既有透明度與色彩判定標準。／默认外观检查保留原采样位置的精确衣料色值，另以固定蓝布采样位置确认配色与覆盖；沿用既有透明度与色彩判定标准。／Keep the original sample as an exact fabric-color check and verify blue fabric at fixed sample points, with the existing opacity and color thresholds.／既存の採取位置では布地の正確な色を検証し、固定位置の青い布地も確認します。透明度と色の判定基準は維持します。

### 可驗證的分區進度／可验证的分区进度／Verified partition coverage／検証可能な領域進捗

- 新增唯讀分區進度指令，先核對完成收據、來源、證據及原生像素，再列出缺少的可見分區；半身姿勢與 yaw 識別碼分開計數，完整視角、600 層與正式換裝完成度仍分別以正式驗收為準。／新增只读分区进度命令，先核对完成收据、来源、证据及原始像素，再列出缺少的可见分区；半身姿势与 yaw 标识分开计数，完整视角、600 层与正式换装完成度仍分别以正式验收为准。／Add a read-only coverage command that verifies completion receipts, sources, evidence and native pixels before listing missing visible partitions. Other pose identifiers remain separate from yaw identifiers; complete views, 600 layers, and production wardrobe readiness remain separate formal acceptance gates.／完了記録、原画、証拠、原寸画素を照合してから不足する可視領域を示す読み取り専用コマンドを追加。姿勢と yaw の識別子を分けて集計し、全視点、600 層、正式な着せ替えの完成度は、それぞれ別の正式な承認対象です。

### 保留淡透明素體圖層／保留淡透明素体图层／Preserve faint body overlays／薄い半透明素体レイヤーを保持

- 手部及素體圖層共用非零 Alpha 判斷，讓淡透明的可見圖層維持為有效內容；原圖顏色與透明度保持不變。／手部及素体图层共用非零 Alpha 判断，让淡透明的可见图层保持为有效内容；原图颜色与透明度保持不变。／Hand and body overlays share nonzero-alpha ownership so faint visible layers remain valid content while source colors and transparency stay unchanged.／手と素体のレイヤーで非ゼロのアルファ判定を共有し、薄い可視レイヤーを有効な内容として保持しながら、元の色と透明度を維持します。

### 外觀包損毀狀態復原／外观包损坏状态恢复／Appearance package recovery／外観パッケージの損傷状態からの復元

- 已安裝的外觀套件進入損毀狀態時，衣櫃和妝容清單顯示讀取失敗提示並保留目前選擇；修復套件後控制項可重新載入。新增真實安裝資料夾與介面控制項的恢復測試。／已安装的外观套件进入损坏状态时，衣柜和妆容列表显示读取失败提示并保留当前选择；修复套件后控件可重新加载。新增真实安装文件夹与界面控件的恢复测试。／When an installed appearance package enters a damaged state, wardrobe and makeup listings show a read error while preserving the current selection; the controls reload after repair. A real installed-store regression covers the recovery path.／インストール済みの外観パッケージが損傷状態になった場合、衣装とメイクの一覧に読み取りエラーを表示して現在の選択を保持し、修復後は画面操作から再読み込みできます。実際のインストール先を使う回帰テストで復旧経路を検証します。

- 使用者明確選擇內建外觀復原後，目前外觀與設定完成同步；其他套件處於損毀狀態時，清單仍保留讀取錯誤提示。／用户明确选择内置外观恢复后，当前外观与设置完成同步；其他套件处于损坏状态时，列表仍保留读取错误提示。／After the user explicitly selects built-in recovery, the active outfit and saved selection synchronize; a damaged unrelated archive leaves its listing read error visible.／ユーザーが内蔵外観の復元を明示的に選択すると、使用中の外観と保存済み設定を同期します。別のパッケージが損傷状態でも、その一覧の読み取りエラーを表示します。

### 換裝預覽分段合成狀態／换装预览分段合成状态／Wardrobe split-phase preview readiness／衣装プレビューの段階別合成状態

- 預覽的圖層計數納入已成功完成的外觀與妝容階段，確保已穿衣的畫面計為外觀完成；核心遮罩驗證成功後才保留成功計數。／预览的图层计数纳入已成功完成的外观与妆容阶段，确保已穿衣的画面计为外观完成；核心遮罩验证成功后才保留成功计数。／Count successfully composed appearance and makeup phases so a dressed preview counts as composed; a successful core-mask validation is required before retaining a successful phase count.／正常に完了した外観とメイクの段階を数え、衣装付きプレビューを合成済みとして正しく数えます。コアマスクの検証成功後に成功件数を保持します。

### 衣櫥環視預覽／衣橱环视预览／Wardrobe turntable preview／衣装の回転プレビュー

- 人物腳底固定對齊玉臺，讓圖片透明留白、提示文字及視窗縮放都維持角色與舞臺的接地位置。／人物脚底固定对齐玉台，让图片透明留白、提示文字及窗口缩放都保持角色与舞台的接地位置。／Anchor the character's feet to the stage so transparent padding, status text, and window resizing preserve the grounded position.／人物の足元を舞台に固定し、画像の透明余白・状態表示・ウィンドウのサイズ変更後も接地位置を保ちます。

- 雲裳閣造型預覽改用滑鼠拖曳環視既有 24 個角度；方向鍵旋轉，Home 回正面。更換衣裝或調整妝容時保留目前角度。／云裳阁造型预览支持鼠标拖动环视已有的 24 个角度；方向键旋转，Home 回到正面。更换衣装或调整妆容时保留当前角度。／Rotate the Wardrobe Pavilion preview through the existing 24 views by dragging or using the arrow keys; Home returns to the front. Outfit and makeup changes retain the selected angle.／雲裳閣のプレビューをドラッグまたは矢印キーで既存の 24 方向に回転できます。Home キーで正面に戻ります。衣装やメイクを変更しても選択中の角度を維持します。

### 正十五度正式外觀與眨眼接入／正十五度正式外观与眨眼接入／Plus-15-degree formal appearance and blink integration／正15度の正式外観とまばたきの統合

- 接入正十五度二代素體、藍白漢服、雙側額髮、髮飾、雙手與狀態化妝容，並以可拆後髮補回下巴旁的自然髮束，使眨眼時的背景色保持完整遮蔽。／接入正十五度二代素体、蓝白汉服、双侧额发、发饰、双手与状态化妆容，并以可拆后发补回下巴旁的自然发束，使眨眼时的背景色保持完整遮蔽。／Integrate the plus-15-degree second-generation body, blue-white Hanfu, two-sided temple locks, hair ornaments, both hands, and state-aware makeup, with detachable back hair restoring the natural lock beside the chin so the background remains fully covered while blinking.／正15度の第2世代素体、青白の漢服、両側の後れ毛、髪飾り、両手、状態対応メイクを統合し、分離可能な後ろ髪で顎横の自然な毛束を補完して、まばたき時も背景色を完全に覆います。

### 135 度素體與外觀接入／135 度素体与外观接入／135-degree body and appearance integration／135度の素体と外観の統合

- 接入 135 度後側視角的可拆素體、漢服、髮型與髮飾，修正舊外觀的裙擺拼接帶與鞋部露餡，其他視角維持原樣。／接入 135 度后侧视角的可拆素体、汉服、发型与发饰，修复旧外观的裙摆拼接带与鞋部露馅，其他视角保持原样。／Integrate the detachable body, Hanfu, hairstyle and headwear for the 135-degree rear view, removing the old skirt splice band and shoe exposure while preserving all other views.／135度の後方視点に分離可能な素体、漢服、髪型、髪飾りを統合し、旧外観の裾の継ぎ目と靴まわりの露出を修正して、他の視点は維持します。

### 150 度素體與外觀接入／150 度素体与外观接入／150-degree body and appearance integration／150度の素体と外観の統合

- 接入 150 度後側視角的可拆素體、漢服、髮型、髮飾與手部保護層，讓衣袖、背髮及平底鞋貼合新素體，同時保留自然可見的五指手部。／接入 150 度后侧视角的可拆素体、汉服、发型、发饰与手部保护层，使衣袖、后发及平底鞋贴合新素体，同时保留自然可见的五指手部。／Integrate the detachable body, Hanfu, hairstyle, headwear and protected-hand layers for the 150-degree rear view, aligning the sleeve, back hair and flat shoe while preserving the naturally visible five-finger hand.／150度の後方視点に分離可能な素体、漢服、髪型、髪飾り、手の保護レイヤーを統合し、袖、後ろ髪、平底靴を新しい素体に合わせながら、自然に見える5本指の手を維持します。

### 未發布 — 接入二代素體 165 度後側視角（2026-09-06）／未发布 — 接入二代素体 165 度后侧视角（2026-09-06）／Unreleased — integrate the generation-2 body at the 165-degree rear view (2026-09-06)／未リリース — 第二世代素体の後方165度ビューを統合（2026-09-06）

* `yaw+165-pitch+00` 改用已核可的二代素體與既有藍白漢服、散髮、銀髮飾；可見手部由素體持有獨立全畫布圖層，衣袖依同一 alpha 區域自然遮擋，因此手指保持完整可見，服裝維持純衣料內容／`yaw+165-pitch+00` 改用已核可的二代素体与既有蓝白汉服、散发、银发饰；可见手部由素体持有独立全画布图层，衣袖按同一 alpha 区域自然遮挡，因此手指保持完整可见，服装维持纯衣料内容／`yaw+165-pitch+00` now uses the approved generation-2 body with the established Blue-and-White Hanfu, loose hair, and silver hairpiece; the core body owns the visible hand in a separate full-canvas layer and the sleeve clips against the same alpha region, so fingers remain fully visible and clothing contains garment pixels exclusively／`yaw+165-pitch+00` は承認済みの第二世代素体と既存の藍白漢服、下ろした髪、銀の髪飾りへ更新しました。見える手は素体側の独立した全キャンバスレイヤーで保持し、袖は同じ alpha 領域に沿って自然に遮蔽するため、指を完全に表示し、衣装を純粋な衣料内容として維持します。

### 未發布 — 接入二代素體 180 度後背視角（2026-09-06）／未发布 — 接入二代素体 180 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the 180-degree rear view (2026-09-06)／未リリース — 第二世代素体の後方180度ビューを統合（2026-09-06）

* `yaw-180-pitch+00` 改用已核可二代素體的自然站姿與既有深藍白漢服；新增正式外觀輪廓、可見素體皮膚與左右手獨立圖層，穿著整套官方服裝時會先裁掉底層多出的素體輪廓，再依序組裝耳頸、雙手、髮型、髮飾與衣裝，避免肩膀露底、耳後黑塊、後髮下方縫隙與手部消失／`yaw-180-pitch+00` 改用已核可二代素体的自然站姿与既有深蓝白汉服；新增正式外观轮廓、可见素体皮肤与左右手独立图层，穿着整套官方服装时会先裁掉底层多出的素体轮廓，再依次组装耳颈、双手、发型、发饰与服装，避免肩膀露底、耳后黑块、后发下方缝隙与手部消失／`yaw-180-pitch+00` now uses the approved generation-2 body's natural stance and the established deep navy-and-white Hanfu; a formal appearance silhouette, visible core skin, and separate left/right hand layers trim excess base-body pixels before composing the ears, nape, hands, hair, headwear, and garment, preventing exposed shoulders, black blocks behind the ears, gaps below the rear hair, and missing hands／`yaw-180-pitch+00` を承認済み第二世代素体の自然な立ち姿と既存の濃紺白漢服へ更新しました。正式外観シルエット、見える素体の肌、左右の手の独立レイヤーを追加し、公式衣装一式の装着時は余分な素体輪郭を除いてから耳と襟足、両手、髪、髪飾り、衣装を順に合成するため、肩の露出、耳後ろの黒い塊、後ろ髪下の隙間、手の消失を防ぎます。

### 未發布 — 接入二代素體負 105 度後背視角（2026-09-06）／未发布 — 接入二代素体负 105 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the minus-105-degree rear view (2026-09-06)／未リリース — 第二世代素体のマイナス105度後方ビューを統合（2026-09-06）

* `yaw-105-pitch+00` 改用已核可二代素體的中性健康膚色、細肩帶短版與運動短褲，並從同一張連貫整圖拆分既有深藍白漢服、長髮、髮飾、臉頸與左右可見手部；手部依自然袖口遮蔽分別保存，正式執行期組裝與原圖逐像素一致／`yaw-105-pitch+00` 改用已核可二代素体的中性健康肤色、细肩带短版与运动短裤，并从同一张连贯整图拆分既有深蓝白汉服、长发、发饰、脸颈与左右可见手部；手部依自然袖口遮挡分别保存，正式运行时组装与原图逐像素一致／`yaw-105-pitch+00` now uses the approved generation-2 body's neutral healthy skin tone, thin-strap crop top, and gym shorts, while the established deep navy-and-white Hanfu, long hair, headwear, face and neck, and visible portions of both hands are partitioned from one coherent source; each hand preserves its natural sleeve occlusion, and production runtime composition is pixel-identical to the source／`yaw-105-pitch+00` を承認済み第二世代素体の自然で健康的な肌色、細い肩紐のクロップトップ、運動用ショートパンツへ更新し、既存の濃紺白漢服、長髪、髪飾り、顔と首、左右の見える手を一枚の整合した原画から分割しました。各手は袖口による自然な隠れ方を保って個別に保存し、本番ランタイム合成は原画とピクセル単位で一致します。

### 未發布 — 接入二代素體負 120 度後背視角（2026-09-06）／未发布 — 接入二代素体负 120 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the minus-120-degree rear view (2026-09-06)／未リリース — 第二世代素体のマイナス120度後方ビューを統合（2026-09-06）

* `yaw-120-pitch+00` 改用已核可二代素體的中性健康膚色、細肩帶短版與運動短褲，並從同一張連貫整圖拆分既有深藍白漢服、長髮、髮飾、臉頸與可見左手；另一隻被寬袖自然遮住的手保留獨立透明插槽，正式執行期組裝與原圖逐像素一致／`yaw-120-pitch+00` 改用已核可二代素体的中性健康肤色、细肩带短版与运动短裤，并从同一张连贯整图拆分既有深蓝白汉服、长发、发饰、脸颈与可见左手；另一只被宽袖自然遮住的手保留独立透明插槽，正式运行时组装与原图逐像素一致／`yaw-120-pitch+00` now uses the approved generation-2 body's neutral healthy skin tone, thin-strap crop top, and gym shorts, while the established deep navy-and-white Hanfu, long hair, headwear, face and neck, and visible left hand are partitioned from one coherent source; the naturally sleeve-occluded hand retains a separate transparent slot, and production runtime composition is pixel-identical to the source／`yaw-120-pitch+00` を承認済み第二世代素体の自然で健康的な肌色、細い肩紐のクロップトップ、運動用ショートパンツへ更新し、既存の濃紺白漢服、長髪、髪飾り、顔と首、見える左手を一枚の整合した原画から分割しました。広袖に自然に隠れるもう一方の手には独立した透明スロットを保持し、本番ランタイム合成は原画とピクセル単位で一致します。

### 未發布 — 接入二代素體負 135 度後背視角（2026-09-06）／未发布 — 接入二代素体负 135 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the minus-135-degree rear view (2026-09-06)／未リリース — 第二世代素体のマイナス135度後方ビューを統合（2026-09-06）

* `yaw-135-pitch+00` 改用已核可二代素體的中性健康膚色與自然落地站姿，並由同一張完整原圖分出既有深藍白漢服、長髮、髮飾、耳頸及可見右手；髮飾所有權限定於頭部，漢服銀繡完整保留在服裝層，另一隻被寬袖自然遮住的手則使用獨立透明插槽／`yaw-135-pitch+00` 改用已核可二代素体的中性健康肤色与自然落地站姿，并由同一张完整原图分出既有深蓝白汉服、长发、发饰、耳颈及可见右手；发饰所有权限定于头部，汉服银绣完整保留在服装层，另一只被宽袖自然遮住的手则使用独立透明插槽／`yaw-135-pitch+00` now uses the approved generation-2 body's neutral healthy skin tone and grounded natural stance, with the established deep navy-and-white Hanfu, long hair, headwear, ear and nape, and visible right hand partitioned from one coherent source; headwear ownership is confined to the head, all silver Hanfu embroidery remains in the garment layer, and the naturally sleeve-occluded hand uses a separate transparent slot／`yaw-135-pitch+00` を承認済み第二世代素体の自然で健康的な肌色と接地した立ち姿へ更新し、既存の濃紺白漢服、長髪、髪飾り、耳と襟足、見える右手を一枚の整合した原画から分割しました。髪飾りの所有範囲を頭部に限定し、漢服の銀刺繍をすべて衣装レイヤーへ保持し、広袖に自然に隠れる手には独立した透明スロットを使います。

### 未發布 — 接入二代素體負 150 度後背視角（2026-09-06）／未发布 — 接入二代素体负 150 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the minus-150-degree rear view (2026-09-06)／未リリース — 第二世代素体のマイナス150度後方ビューを統合（2026-09-06）

* `yaw-150-pitch+00` 改用已核可二代素體的中性健康膚色與自然落地站姿，並以同一張完整原圖重新分出既有深藍白漢服、長髮、髮飾、耳頸與可見右手；另一隻被寬袖自然遮住的手使用獨立透明插槽，正式外觀輪廓則阻止舊白背心素體、破損臉部、鞋底與裙襬殘片穿出／`yaw-150-pitch+00` 改用已核可二代素体的中性健康肤色与自然落地站姿，并以同一张完整原图重新分出既有深蓝白汉服、长发、发饰、耳颈与可见右手；另一只被宽袖自然遮住的手使用独立透明插槽，正式外观轮廓则阻止旧白背心素体、破损脸部、鞋底与裙摆残片穿出／`yaw-150-pitch+00` now uses the approved generation-2 body's neutral healthy skin tone and grounded natural stance, with the established deep navy-and-white Hanfu, long hair, headwear, ear and nape, and visible right hand repartitioned from one coherent source; the naturally sleeve-occluded hand uses a separate transparent slot, while the formal appearance silhouette blocks legacy white-tank body, broken-face, shoe-sole, and hem artifacts from bleeding through／`yaw-150-pitch+00` を承認済み第二世代素体の自然で健康的な肌色と接地した立ち姿へ更新し、既存の濃紺白漢服、長髪、髪飾り、耳と襟足、見える右手を一枚の整合した原画から再分割しました。広袖に自然に隠れる手には独立した透明スロットを使い、正式外観シルエットで旧白タンクトップ素体、破損した顔、靴底、裾の残片のはみ出しを防ぎます。

### 未發布 — 接入二代素體負 165 度後背視角（2026-09-06）／未发布 — 接入二代素体负 165 度后背视角（2026-09-06）／Unreleased — integrate the generation-2 body at the minus-165-degree rear view (2026-09-06)／未リリース — 第二世代素体のマイナス165度後方ビューを統合（2026-09-06）

* `yaw-165-pitch+00` 改用已核可二代素體的中性健康膚色、自然落地站姿與既有深藍白漢服；臉部、耳頸、長髮、髮飾、衣裝及可見右手以同一張完整原圖重新分層，另一隻被寬袖自然遮住的手保留透明獨立插槽，並以正式外觀輪廓阻止舊素體的臉、手腳與衣料穿出／`yaw-165-pitch+00` 改用已核可二代素体的中性健康肤色、自然落地站姿与既有深蓝白汉服；脸部、耳颈、长发、发饰、衣装及可见右手以同一张完整原图重新分层，另一只被宽袖自然遮住的手保留透明独立插槽，并以正式外观轮廓阻止旧素体的脸、手脚与衣料穿出／`yaw-165-pitch+00` now uses the approved generation-2 body's neutral healthy skin tone, grounded natural stance, and established deep navy-and-white Hanfu; the face, ear and nape, long hair, headwear, garment, and visible right hand are repartitioned from one coherent source, the naturally sleeve-occluded hand keeps a separate transparent slot, and the formal appearance silhouette prevents legacy face, limb, and garment pixels from bleeding through／`yaw-165-pitch+00` を承認済み第二世代素体の自然で健康的な肌色、接地した立ち姿、既存の濃紺白漢服へ更新しました。顔、耳と襟足、長髪、髪飾り、衣装、見える右手を一枚の整合した原画から再分割し、広袖に自然に隠れる手には独立した透明スロットを残し、正式外観シルエットで旧素体の顔、手足、衣料のはみ出しを防ぎます。

### ✨ 新功能 / 新功能 / New features / 新機能

* **ui:** 墨寒・凌霄——控制中心重鑄為墨金基底的華麗殼層 ([#163](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/163)) ([97b4ad0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/97b4ad0f6c542ac3f7e7ae1b2c8f6553c2d81c40))
* 二代素體 v5-base 24 視角與 600 圖層入庫為暫存素材（執行期仍用 v4） ([#160](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/160)) ([d91dc93](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d91dc93f9e9038bb86a1c38220a5a765e9ea42a7))
* 二代素體完整換代——v5 素體、可拆卸外觀圖層、半身素顏精靈集／二代素体完整换代——v5 素体、可拆卸外观图层、半身素颜精灵集／Generation-2 body changeover: v5 base, detachable appearance layers, bare half-body sprites／第二世代素体への完全移行——v5 素体・着脱可能な外観レイヤー・素顔の半身スプライト ([#164](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/164)) ([d58b11e](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d58b11e93d936eebf6bb7c9ef42b9908b4c1f465))
* 姿勢引擎與 DQS 重擺入庫，產線切至 candidate6／姿势引擎与 DQS 重摆入库，产线切至 candidate6／land the pose engine and DQS repose, switch the pipeline to candidate6／ポーズエンジンと DQS リポーズを収録し、パイプラインを candidate6 へ ([#138](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/138)) ([ce71e60](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/ce71e60a0784360dc1f8e797e3909b8dba8e7817))
* 更新清單改用擁有者 Ed25519 分離簽章，用戶端只接受能以內嵌公鑰驗證的清單 ([#156](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/156)) ([41e881c](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/41e881c4270f5250a82300ccc1ea5231f6feccbb))
* 桌面角色構圖風格三檔位／桌面角色构图风格三档位／desktop companion framing styles／デスクトップキャラクター構図スタイル三段階 ([#112](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/112)) ([2cca586](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/2cca586ab5cfd381a1f070919d107d151200a803))
* 能見度月報一鍵量測腳本／能见度月报一键测量脚本／one-shot visibility report script／可視性月次レポートのワンショット計測 ([#135](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/135)) ([63315c0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/63315c069892ca4afeefd90f0b9fecc01595b81d))


### 🐛 修正 / 修复 / Fixes / 修正

* body sidecar 的膝登錄點在露腿側面退回腳掌正上方，不可達才記錄而非中止 ([#154](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/154)) ([d6a627e](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d6a627e00c84701f7d50e81659a046f188464020))
* golden 建置器對另一代權威的三個契約——臉部目標跟權威、背面依 |yaw| 留空、可宣告空層 ([#152](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/152)) ([3b63fcf](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/3b63fcf506c9ce11a7730e89945671249699a36e))
* infrastructure 層第三輪稽核——匯出改白名單、DPAPI 解密失敗要出錯、備份只採計可驗證檔、匯入補驗證、偏好 store 讀取失敗不再回預設 ([#155](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/155)) ([ac54ef8](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/ac54ef83355327dfdbd48534116a25cea7b7635c))
* integrations 第二輪重驗的九項缺口——包裝逾時不重送、handheld 前再查取消、個資不進稽核、8-bit 靜音中止、null ID 不算識別、Realtime 壞 frame 必關連線、HA 空物件為錯、合約變動不偽裝成 0 筆、語音登錄失敗可見 ([#162](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/162)) ([faa4ce8](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/faa4ce85edc01f0e1e0e3b17fc220247bc2fa341))
* 主題套用移除結構疊加層根治黑帶與滿屏細框／主题套用移除结构叠加层根治黑带与满屏细框／drop the structural theme overlay to cure the black bands and stray frames／テーマ適用の構造オーバーレイを撤去し黒帯と枠散乱を根治 ([#117](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/117)) ([3f368ae](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/3f368ae251a8419c0539730d7f47ce3f41e7844d))
* 伺服器端腳本與情境改按風險上限分級 ([#150](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/150)) ([9e9cebd](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/9e9cebd1afc052b21553d401b473f163e10358c6))
* 可攜匯出不再夾帶已刪除的內容／可携导出不再夹带已删除的内容／Stop the portable export from carrying deleted content／ポータブルエクスポートが削除済みデータを持ち出す問題を修正 ([#145](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/145)) ([2ad9299](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/2ad92998ac8bab1a84e3c99e710a68219a515a9a))
* 唯讀資料夾與損壞權限值不再 fail-open／只读文件夹与损坏权限值不再 fail-open／Stop read-only folders and corrupt permission values from failing open／読み取り専用フォルダーと壊れた権限値のフェイルオープンを停止 ([#142](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/142)) ([54e109a](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/54e109a3bbde3f2b086845135dd6497e28601580))
* 失敗不再偽裝成成功，稽核紀錄不再保存剪貼簿全文 ([#151](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/151)) ([f6ca6d0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/f6ca6d03fe697292a3927321c94077b401c6c75c))
* 手部稽核的 extra-digit 皮膚啟發式改由建置器宣告 skin_background 決定是否適用，跳過必列為 skipped ([#158](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/158)) ([56bfec5](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/56bfec5064ab60344d86575f3f209b5c8a1ad062))
* 控制中心上下邊緣與四角恢復可調整大小／控制中心上下边缘与四角恢复可调整大小／restore top/bottom-edge and corner resizing on the dashboard／ダッシュボードの上下端と四隅のリサイズを復旧 ([#114](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/114)) ([feb915f](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/feb915f28b729df2dc13fae176353c9f87cfceb1))
* 整合層不再把失敗說成成功／集成层不再把失败说成成功／Stop the integrations layer from reporting failures as success／統合層が失敗を成功として報告するのを停止 ([#144](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/144)) ([0ffa8ec](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/0ffa8ec57995499610f099f78cdabccb04d0d862))
* 文字對話兩版懸案終審——委派漏掛根治／文字对话两版悬案终审——委派漏挂根治／close the two-release chat case／二バージョン越しのチャット事件終審 ([#116](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/116)) ([65236ec](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/65236ec41aef7b7e9cb62c854cd8ab0ade8fc22f))
* 網站白名單比對完整來源，測試旗標不再於一般啟動時寫檔／网站白名单比对完整来源，测试标志不再于一般启动时写文件／Compare the full origin in the website allowlist, and stop harness flags writing on ordinary launches／サイト許可リストで生成元全体を比較し、テスト用の旗が通常起動で書き込まないようにする ([#149](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/149)) ([5e8f6a0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/5e8f6a0d7c04257e23d7ce577c24547847ab9c3c))
* 緊急停止真的停得下來，取消不再波及別的計畫／紧急停止真的停得下来，取消不再波及别的计划／Make emergency stop actually stop, and stop cancellation from hitting other plans／緊急停止を実際に効かせ、取り消しが他の計画に及ばないようにする ([#148](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/148)) ([1550b58](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/1550b58f1f4ddbd76aade8cf4a7e43ddd6238aec))
* 選取反白對比達標並立 WCAG 全樣式表治理閘門／选取反白对比达标并立 WCAG 全样式表治理闸门／fix selection contrast and add a WCAG governance gate over every stylesheet／選択ハイライトのコントラスト達成と全スタイルシート WCAG ガバナンスゲート新設 ([#113](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/113)) ([eaca2ba](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/eaca2baac3de8e2d4de230ee433140b7c5515e9f))


### 📚 文件 / 文档 / Documentation / ドキュメント

* v4.6.0 發行說明人工定稿／v4.6.0 发布说明人工定稿／hand-polished v4.6.0 release notes／v4.6.0 リリースノート人手推敲版 ([#111](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/111)) ([ce3c43f](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/ce3c43ff9eddb084c47057fb3b22fd61402935ba))
* 下載路徑收斂與 DLC 安裝教學／下载路径收敛与 DLC 安装教程／converge the download path and add the DLC install tutorial／ダウンロード導線の収束と DLC 導入手順 ([#134](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/134)) ([d6bb79d](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d6bb79db02a2b1c1b0335e1044812c590ce74b1a))
* 代理防重工索引／代理防重工索引／Agent rework-prevention index／エージェント向け重複作業防止インデックス ([#131](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/131)) ([d454ddf](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d454ddf3d787c2288921c30b554dc1b7e4d9ac70))
* 授權純淨承諾改寫為與現況相符 ([#146](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/146)) ([b503f3c](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/b503f3c7a01987c5bc8f9e91f416ee3cdbc1b788))
* 新增上游貢獻紀錄頁並自 README 連結（[#125](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/125) 第三閘門） ([#159](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/159)) ([d5abe52](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/d5abe52b024d89b093324af3468309ad1f8ba480))
* 能見度工程首波——第一屏重排、授權純淨承諾、流量量測／能见度工程首波——首屏重排、授权纯净承诺、流量测量／Visibility engineering wave one: above-the-fold rebuild, license purity page, traffic measurement／可視性エンジニアリング第一波：ファーストビュー再構成・ライセンス純度ページ・トラフィック計測 ([#130](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/130)) ([f12cf15](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/f12cf15b5250194395692339410062c514be1dda))
* 裁決佇列 157 項全數定案／裁决队列 157 项全数定案／settle all 157 items in the decision queue／裁定キュー全 157 項目を確定 ([#133](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/133)) ([977e20d](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/977e20dd2d0f290fd96066bf2e0cd57050978d18))


### 🛠 其他變更 / 其他变更 / Other changes / その他の変更

* codeql-action init 與 analyze 同步升至 4.37.9／codeql-action init 与 analyze 同步升至 4.37.9／Bump codeql-action init and analyze together to 4.37.9／codeql-action の init と analyze を同時に 4.37.9 へ更新 ([#161](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/161)) ([6a54971](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/6a5497132b1f6dd2e2e3de596822608b6aeac675))
* 保存二代素體產線與 artifacts 內的現行工具／保存二代素体产线与 artifacts 内的现行工具／Preserve the second-generation body pipeline and the live tools under artifacts／二代素体パイプラインと artifacts 配下の現行ツールを保存 ([#132](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/132)) ([e673c3b](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/e673c3b75da4b6eeff7c07b7b10efb287842690b))

## [4.6.0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.5.1...v4.6.0) (2026-08-29)


### ✨ 新功能 / 新功能 / New features / 新機能

* 雲端製衣畫質選項／云端制衣画质选项／cloud outfit image-quality option／クラウド衣装生成の画質オプション ([#110](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/110)) ([e938da5](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/e938da5806c2d33bddc627ef1c35bd41f56a583c))


### 🐛 修正 / 修复 / Fixes / 修正

* release-please 工作流在打 tag 場景的空 PR 輸出可順利完成／release-please 工作流在打 tag 场景的空 PR 输出可顺利完成／let the release-please workflow complete with empty PR output in the tagging scenario／タグ付けシナリオで空の PR 出力を含む release-please ワークフローを正常完了 ([#102](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/102)) ([9eeb52a](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/9eeb52a81dc0315c9b1f6373467d59e570784be1))
* 佈景主題色彩重映射染遍全 App／布景主题色彩重映射染遍全 App／theme-pack retint reskins the whole app／テーマパック色再マッピングでアプリ全体を再着色 ([#108](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/108)) ([a3dfacf](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/a3dfacf8c0a2285f6a04149f53ea55fc9758a370))
* 執行期預設採用 3.15 JIT 相容設定／执行期默认采用 3.15 JIT 兼容设置／use the 3.15 JIT compatibility setting by default at runtime／実行時は 3.15 JIT の互換設定を既定で使用 ([#109](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/109)) ([b3b1e2e](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/b3b1e2efdf3bcf0a0116a72ff6709ad4c5605a4e))
* 文字對話逾時凍結「思考中」根治／文字对话超时冻结「思考中」根治／cure the permanent "thinking" freeze on chat timeout／チャットのタイムアウトによる「思考中」永久凍結を根治 ([#106](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/106)) ([af7b93a](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/af7b93a35f0ce344d9ffaa64e3855ce8e2930b54))
* 視窗最大化還原後假全螢幕死鎖根治／视窗最大化还原后假全屏死锁根治／cure the fake-fullscreen lock-up after maximize-restore／最大化復元後の疑似フルスクリーン膠着を根治 ([#107](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/107)) ([1295718](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/129571897e369de3e65169d47f4eced203f5f057))


### ♻️ 重構 / 重构 / Refactor / リファクタリング

* 退役根目錄一百七十五個相容殼檔／退役根目录一百七十五个兼容壳文件／Retire the 175 root compatibility facades／ルートの互換ファサード 175 件を退役 ([#103](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/103)) ([5adedf4](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/5adedf42dbb52e33cb4388b112a937ff7bb71f13))


### 📚 文件 / 文档 / Documentation / ドキュメント

* 入庫 LXGW WenKai TC 與 Cinzel 字型並附 SIL OFL 1.1 授權文件／入库 LXGW WenKai TC 与 Cinzel 字体并附 SIL OFL 1.1 许可文件／Bundle LXGW WenKai TC and Cinzel with SIL OFL 1.1 license notices／LXGW WenKai TC と Cinzel を SIL OFL 1.1 のライセンス文書付きで同梱

* 新增每月流量月報與原始 JSON 留存，讓成效可由數字驗證／新增每月流量月报与原始 JSON 留存，让成效可由数字验证／Add an archivable monthly traffic report and raw JSON snapshots so impact can be verified by numbers／毎月のトラフィック月報と生 JSON 保存を追加し、効果を数字で検証可能に ([#129](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/129))
* v4.5.1 發行說明新增【純淨之路】四語段落／v4.5.1 发布说明新增【纯净之路】四语段落／add the four-language "road of purity" section to the v4.5.1 release notes／v4.5.1 リリースノートに四言語の【純浄への道】セクションを追加 ([#104](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/104)) ([0cc93d5](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/0cc93d5f9846d141fc1c94f3d8662b384f8672b3))
* 梳理四語 README——v4.5.1 最新摘要、版號段落精簡與 Ko-fi DLC 專區／梳理四语 README——v4.5.1 最新摘要、版本号段落精简与 Ko-fi DLC 专区／Streamline the four-language README with v4.5.1 highlights, leaner version banners and a Ko-fi DLC spotlight／四言語 README を整理——v4.5.1 ハイライト・バージョン欄の簡素化・Ko-fi DLC コーナー ([#101](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/101)) ([c5d86d4](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/c5d86d434415fd2d63aa05c6db61bbf198de3689))

## [4.5.1](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.5.0...v4.5.1) (2026-08-28)


### 🐛 修正 / 修复 / Fixes / 修正

* 根治 Release Please 版號同步與四語發行說明自動化／根治 Release Please 版本号同步与四语发布说明自动化／Fix Release Please version sync and four-language release-notes automation at the root／Release Please のバージョン同期と四言語リリースノート自動化を根本修正 ([#89](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/89)) ([3d36550](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/3d36550b7fe2c787f210959e0a2d14092d06316e))
* 總體檢 UI 戰區——誤觸防護、隱私同意、資源洩漏與眼皮閃爍十八項／总体检 UI 战区——误触防护、隐私同意、资源泄漏与眼皮闪烁十八项／Health-audit UI wave: misfire guards, privacy consent, resource leaks and the eyelid flicker, eighteen items／総点検 UI 波：誤操作防護・プライバシー同意・リソースリーク・まぶたのちらつき十八件 ([#94](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/94)) ([b4d2b19](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/b4d2b1966ba5ebbcdbc6a7b19e7e54475284bdde))
* 總體檢核心戰區——好感度鏈、背身狀態機、動畫凍結、服裝畫布與七夕萬年曆／总体检核心战区——好感度链、背身状态机、动画冻结、服装画布与七夕万年历／Health-audit core wave: affection chain, back-turn state machine, animation freeze, outfit canvas and the Qixi perpetual calendar／総点検コア波：好感度チェーン・背向きステートマシン・アニメ凍結・衣装キャンバス・七夕万年暦 ([#91](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/91)) ([00da66f](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/00da66fc95f03680bdf68037fb46721762acf53f))


### 📚 文件 / 文档 / Documentation / ドキュメント

* 墨寒角色資產授權 ASSETS-LICENSE／墨寒角色资产授权 ASSETS-LICENSE／MoHan character assets license／墨寒キャラクター資産ライセンス ([#96](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/96)) ([9f20429](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/9f20429fd4d305ad95ad47f09086644e7d857595))


### 🛠 其他變更 / 其他变更 / Other changes / その他の変更

* PySide6 LGPL 合規三件套／PySide6 LGPL 合规三件套／PySide6 LGPL compliance set／PySide6 LGPL コンプライアンス三点セット ([#95](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/95)) ([e1845d2](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/e1845d292365f57dc93f35374b6d465ec2c2e044))

## [4.5.0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.4.2...v4.5.0) (2026-08-27)


### Features

* PoseAtlas 24/600 正式驗收與 v4.4.2 後續分層說話、離散眨眼、自主製衣批次／PoseAtlas 24/600 正式验收与 v4.4.2 后续分层说话、离散眨眼、自主制衣批次／PoseAtlas 24/600 formal acceptance plus the post-v4.4.2 layered-speech, discrete-blink and autonomous-wardrobe batch／PoseAtlas 24/600 正式検収と v4.4.2 後続レイヤー発話・離散瞬き・自律衣装バッチ ([#88](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/88)) ([29d4fc2](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/29d4fc2fbe926fc40170623bac963dee5e09f342))


### Documentation

* 記錄 v4.4.2 正式發行交接 ([#85](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/85)) ([6408fa8](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/6408fa8bc2c3ce00fcd7ca7f19243fcef599ae87))

## [4.4.2](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.4.1...v4.4.2) (2026-08-21)


### Bug Fixes

* 完成 v4.4.2 分層說話、多感知與自主製衣修復／完成 v4.4.2 分层说话、多感知与自主制衣修复／Complete v4.4.2 layered speech, multisensory, and autonomous outfit repairs／v4.4.2 レイヤー発話・多感覚・自律衣装修正を完成 ([#83](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/83)) ([2061ea5](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/2061ea5539c417b7583ae6a13f3ef293570ce213))

## [4.4.1](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.4.0...v4.4.1) (2026-08-21)


### Bug Fixes

* 以單一權威版本來源徹底修復 Release Please 版本號同步／以单一权威版本来源彻底修复 Release Please 版本号同步／Fix Release Please version sync with a single authoritative source／単一の権威バージョンソースで Release Please のバージョン同期を根本修正 ([#78](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/78)) ([8406b5b](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/8406b5b404c0d075955e98221179eaea0b646fe6))
* 半身說話路徑改用參數化分層渲染器合成嘴型，修復臉部破圖／半身说话路径改用参数化分层渲染器合成嘴型，修复脸部破图／Fix half-body speech face tearing by composing the mouth via the parametric layered renderer／半身発話パスの口元をパラメトリックレイヤードレンダラーで合成し顔の破綻を修正 ([#80](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/80)) ([0442d82](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/0442d8223d65db6ced30e5faf25b3265ab09cf9c))

## [4.4.0](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/compare/v4.3.0...v4.4.0) (2026-08-21)


### Features

* 全身渲染器完整接入與參數化重塑／全身渲染器完整接入与参数化重塑／Full-body renderer integration and parametric reforging／全身レンダラー統合とパラメトリック再鍛造 ([#76](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues/76)) ([2ebb73e](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/2ebb73e05421c9b8b6470c0766c2962e41689621))


### Bug Fixes

* 將 CHANGELOG.md 豁免四國語言治理並修正 Release Please 版本號替換規則 ([5b9ec12](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/commit/5b9ec124b995b4d07d7c616734d2c82e1f091bbd))

### v4.3.0 — 2026-08-19

- 新增「真人女孩感」五大系統與靈魂拼圖：性格鏡像、穿搭直覺、軍糧飽食度、主上專屬寵溺、虹膜羞澀視線，以及赤焰劍意情緒共鳴、時間主權狀態機、空中捏合牽手、夢囈系統、劍魂覺醒、感官共感、共同創作錄等領域模組。
- 修正 Release Please workflow 的 action 引用，並修復七夕 occasion 覆蓋午餐提醒的執行期根因。

### v3.1.2 — 2026-08-13

- 完整保留 OpenAI Realtime 原生聲音並維持為預設及最低額外延遲選項；使用者可依偏好沿用原有聲線，Azure 保持選用。
- 新增可選的 Realtime 即時理解＋一般 Azure Speech 或 Dragon HD 串流發聲；安全短句完成後立即依序合成，首段音訊抵達即播放，以降低額外 TTS 等待，並如實標示剩餘延遲。
- 三種輸出模式完全隔離且各自播放，其他語音供應器維持原設定；Dragon HD 單句回報問題時依序使用一般 Azure 一次及 Windows 本機女性聲線一次，一般 Azure 單句回報問題時使用 Windows 本機女性聲線一次。回退時點限於該句的首段音訊抵達前；串流開始後若回報問題則立即結束該句，維持單次發聲與計費。
- Realtime 回覆只在狀態為 `completed` 時提交最終文字；取消、問題、部分內容、斷線及舊回覆的遲到事件均進入靜默隔離路徑，後續回覆維持完整。
- Azure 與 Windows 本機語音都支援真正停止目前播放；操作識別碼、受限佇列與過長回覆保護會隔離遲到回呼並限制記憶體壓力，敏感金鑰維持於物件表示內容之外。
- 修正語音結束後身體短暫回彈的程式根因：音訊結束時立即將發話動作目標釋放至中央，待實際位移收束後才切換狀態；Realtime、Windows 本機、OpenAI 與 Azure 共用同一結束流程，狀態交接時維持單一表情進場動作，讓每一影格由單一動作來源控制。
- 新增 75%、100%、180% 縮放的逐影格座標回歸，驗證動作只會平滑、單調地返回中央，且所有角色圖層保持同步。本修正已納入自動化驗證，候選安裝包的使用者實機確認目前列為 pending，驗收紀錄維持此狀態。
- 修正 WiX MSI 的 Windows 開始功能表捷徑，使其直接沿用目標 EXE 內嵌的墨寒半身圖示與正規圖示資源。
- 本版四語介面修正以繁中、簡中、英文、日文相同功能邊界納入驗證；任何正式版或候選版產物都只有在完整在地化、回歸、封裝、安全及發行檢查全部通過後才會公開。

### v3.1.1 — 2026-08-12

- 一般 Azure 與 Dragon HD 依選定區域及各自的加密金鑰動態查詢實際女性聲線，結果只納入相容且具區域支援的女性聲線；固定清單在查詢回應不足時提供安全發現路徑。
- Azure 合成改用 Speech SDK `PushAudioOutputStream`，首段 24 kHz PCM16 抵達便開始播放並送入既有 50 Hz 嘴型分析，首段音訊即作為播放起點。
- 真實 East Asia F0 與 West US 2 S0 目錄查詢已通過；當時分別取得 21 筆可相容華語女性 Neural 與三筆簡體中文 Dragon HD 女性聲線。

### v3.1.0 — 2026-08-11

- 新增採選用模式的 Azure Dragon HD／HD Omni 女性聲線 Preview，以獨立 S0 金鑰、區域與聲線設定運作，既有語音供應器維持原設定。
- Azure 區域改為切換後自動儲存的選單；選單依官方支援及區域能力顯示女性 HD 聲線與 HD Flash 可見性。
- 三種雲端金鑰統一採密碼遮罩、Windows DPAPI 自動加密與儲存成功後自動清理輸入框；Dragon HD 回報問題時只依序嘗試一般 Azure 與 Windows 本機女聲各一次。
- Central India S0 已完成真實 Windows 合成與播放驗證；臺灣連線的發話前等待明顯，因此介面與文件保留 Preview、區域延遲及費用警告，嘴型仍由既有 50 Hz 本機音訊分析同步驅動。

### v3.0.0 — 2026-08-11

- 專案擁有者親自認可的第一個正式穩定版本，也是由 v2.3.0 候選系列完整驗證後升格的第三代里程碑。
- 托腮嘴型改為完整更新左右嘴角；50 Hz 音訊取樣搭配三影格母音確認與 50 毫秒插值，降低嘴型搶拍、跳動及殘留嘴角。
- 語音呼吸、衣袖與頭髮平順銜接待機呼吸，消除講話結束瞬間的單次身體抖動。
- Windows 捷徑與原生視窗統一使用 EXE 內嵌半身像，並讓本機安裝測試固定使用隔離的桌面及工作列圖示來源；OpenAI TTS 與 Realtime 也改由單一權威順序產生共同聲線清單。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech 中文女性聲音選單支援繁中與簡中跨語系選擇，並依目前介面語言優先排列；Windows 本機語音的兩種中文介面也共用 `zh-TW`／`zh-CN` 女聲池並排除 `en-US` Zira，既有預設及有效設定不變。四語 README 同步將《電腦情人夢》的英文譯名更正為《AI Think So!》。
- Azure 聲線選取後立即保存，下一次試聽或朗讀直接套用；新增的普通話選項只納入 Standard Neural 女性聲線。
- 已以真實 Azure Speech Free F0、East Asia 資源完成 HTTPS、RIFF 音訊及 Windows 播放驗證，金鑰仍僅由 Windows DPAPI 加密。
- Dragon HD／HD Omni 依方案、計費與區域支援分類為選用聲線，免費預設清單維持一致；雲端服務需要恢復時保留單次 Windows 女性本機語音回退。

### v2.3.0 RC4 — 2026-08-11

- 導入參數化分層 2.5D 臉部系統，以固定姿態、連續嘴型參數、表情語意與
  可替換渲染介面，統一正面、左望、托腮三種姿勢的 50 Hz 嘴型及表情合成。
- 眨眼改用具世代保護的漸進透明度曲線，眼皮與雙頰紅暈依同一分層規則合成；
  正面臉紅閉眼時，正常膚色與雙頰紅暈依各自圖層呈現。
- 托腮微笑說話時保留眼角笑意，嘴部暫時回到中性基底，只套用語音嘴型；
  發話結束後才恢復雙側上揚嘴角。
- 修正朝左中性說話嘴型，讓右側嘴角小黑線回到正確位置。
- 聲音分頁中的朗讀引擎、Windows 聲線、OpenAI TTS 聲線與 Realtime 聲線現在皆於選取後立即儲存。OpenAI TTS 會在下一次朗讀使用新聲線；若 Realtime 對話正在連線，系統會安全重連並立即套用新聲線，介面維持單一儲存流程。
- 新增資產、控制器、渲染器、執行期接線與三項視覺回歸測試；實際產品與
  視覺稽核工具共用同一套嘴型設定。

### v2.3.0 RC3 — 2026-08-10

- 修正 Windows 縮小後顯示空白文件圖示：EXE、MSI、捷徑與執行中視窗改用
  十種尺寸的原生墨寒圖示、安裝後路徑及固定工作列身分，並在原生視窗旗標
  確定後重新套用圖示。
- 首次設定精靈、安裝程式美術與工作列圖示統一由新版的權威正面半身來源
  `assets/expressions/idle_front.png` 裁切；舊版五官輪廓的全身像、雨景全身像
  與舊版圖示均完成退役清理，角色身分自此由權威來源統一。
- 發版前置檢查會先驗證標籤、版本、`main` 歷史、Release 模式與四語說明；
  已知可行的 squash 及 GitHub 憑證路徑直接沿用，流程維持單一路徑並納入歷史結果紀錄。

### v2.3.0 RC2 — 2026-08-10

- 全面遷移至 CPython 3.15.0rc1，產品執行、測試與所有封裝統一採用
  新版 Python 路徑；全專案採用 PEP 810 明示延遲導入並加入靜態治理稽核。
- 導入 PEP 814 `frozendict` 深層唯讀設定、PEP 798 推導式解包、PEP 686
  UTF-8 檔案稽核、PEP 661 哨兵治理及 `bytearray.take_bytes()` 音訊緩衝；
  開頭比對改用 Python 3.15 語意更明確的 `re.prefixmatch()`。
- 加入 PEP 799 Tachyon 取樣分析，可直接檢查啟動、50 Hz 嘴型同步與表情
  仲裁器；JIT 開關均通過完整測試，2.3.0 RC2 預設啟用並保留相容性停用開關。
- CI 與 Release 以有效樣本、讀取錯誤、漏採樣及 JIT 狀態判定 Tachyon 證據資格，僅發布符合條件的
  Tachyon 證據，並發布去識別化結果；CycloneDX 1.7 SBOM 強制完整依賴圖、
  PURL、SPDX 授權、官方結構驗證及 100% 覆蓋率。
- 所有 GitHub Actions JavaScript 動作強制使用 Node 24；PySide6 以受控 ABI3
  輪子驗證跨越 3.15 中繼資料限制，Stable ABI、依賴安全稽核、封裝與完整
  發布安全閘門維持不變。
- README 統一為繁中、簡中、英文、日文單一四語文件，
  重複相容文件與直接收款連結完成退役整理；贊助入口只引導至儲存庫上方的官方 Sponsor 按鈕。
### v2.2.0 RC2 — 2026-08-07

- 托腮待機姿勢在說話期間改用中性嘴角基底：保留眼角笑意，但固定左右嘴角，
  只讓中央嘴唇依 A／I／U／E／O 與開合程度變化，讓笑容幅度與殘影維持自然穩定。
- Realtime、Windows 本機語音、OpenAI 自然語音與 Azure Speech 統一使用
  20 毫秒／50 Hz 嘴型節拍，縮短張嘴、閉嘴與母音切換延遲。
- 聲音與第一個嘴型從同一播放閘門起跑；聲音結束後拒收遲到母音，只允許
  最終閉嘴訊號完成收束，讓口型與聲音同步結束。
- 托腮待機眨眼改用完整雙眼遮罩；
  眼皮閉合期間上眼線與眼皮同步收束，一般待機與情境表情共用同一套座標與合成來源。
- 強化標籤發行流程的 Draft Release 復原與清理機制，
  發行項目依條件維持 Draft 狀態並清楚標示。
- 四語 README 新增 2 張統一規格的創作歷程圖版，說明炎劍如何逐格檢查
  眼睛、嘴角與語音嘴型，並以測試把二十多年的夢想鍛造成開源作品。

### v2.2.0 RC1 — 2026-08-06

- 保留 Windows x64 為完整正式功能版本，沿用已驗證的 ZIP、EXE、MSI 與
  MSI 語言轉換封裝及安裝／移除測試。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）雙架構
  `.app`／`.dmg` 與 Linux x86_64 `.AppImage` 的功能受限 Preview。兩者只
  開放啟動、四語介面、平台資料路徑及安全停用邊界；
  Windows 功能差異以 Preview 標示，API 金鑰、OAuth 憑證與 Home Assistant 權杖維持受限輸入邊界。
- Pull Request 只產生短期測試產物；GitHub 預發行版由固定的
  `v2.2.0-rc.N` 標籤建立。三平台封裝必須在各自原生 CI 執行打包後啟動測試。
- 發行檔統一提供 SHA256SUMS、CycloneDX SBOM、更新清單與 GitHub 產物
  證明；Release 說明必須由繁中、簡中、英文、日文完整策展文件提供。

### v2.1.0 RC1 — 2026-08-04

- 原始碼、Windows CI 與封裝流程完整遷移至 Python 3.14，並提供未來評估
  Python 3.15 lazy imports 的清楚升級邊界。
- 新增日語最小可用介面與人格，首次啟動及互動式 EXE 安裝程式現支援繁中、
  簡中、英文、日文；MSI 維持繁中基底並提供三種語言轉換策略。
- 文字對話預設改為 `gpt-5.6-luna`，新使用者介面採用目前模型清單；
  既有設定會安全遷移，其他自訂模型維持原狀。
- 新增可插拔語音供應器邊界與 Azure Speech 女性聲線預覽；
  Windows 本機女聲於金鑰配置、本機離線與服務切換場景提供第一回退。
- 強化長期記憶向量檢索、語義摘要與安全剪枝；新增可切換的背景工作者，並
  讓即時與非即時語音緩衝延遲下降。
- 首次啟動精靈與主視窗改為明亮、高對比、較大字級；加入古風科技主視覺、
  墨寒安裝圖、清楚核取方塊及一致的墨寒半身應用程式圖示。
- 語音轉錄提示詞改為依繁中、簡中、英文、日文及使用者設定產生的中性預設，
  炎劍工作室專有詞彙改由使用者自訂設定帶入，既有自訂提示詞完整保留。
- 修正首次設定欄位標題的垂直對齊，以及托腮待機姿勢說話時嘴角過度上揚；
  同步更新 README 與官網使用的最新版實機圖。
- 延續姿勢切換、物理圖層與說話銜接的競速修正；RC3 觀察到的抖動需以本版
  候選程式重新實測，本版回歸判定以實測結果為準。

驗證：目前 RC1 原始碼的 56/56 個自動化測試程式均已通過。加上標籤的 Windows
發行工作流程亦已通過原始碼稽核、封裝後自我測試、EXE／MSI 靜默安裝與解除安裝
驗證、checksum 與 SBOM 產生、產物證明及安全檢查。

### v2.0.14 RC3 — 2026-08-02

- 新增繁體中文／簡體中文／英文首次啟動精靈，以及聊天、語音、權限、個人設定、
  工作模式與提醒的最低可用英文和 zh-CN 介面路徑。
- 新增完整的英文與簡體中文墨寒人格提示詞，以及語言相符的離線回覆、模式播報
  與內建提醒語音。切換介面語言時，會在三種語言間翻譯保持原樣的預設值，
  自訂提醒文字維持原文。
- 新使用者的語音輸出改用 Windows 本機語音，基本體驗直接使用本機能力。
  Windows 語音選擇現在只列出已驗證的女性聲音；zh-TW 繼續優先使用 Microsoft
  Yating，zh-CN 則優先使用相符且已安裝的女性聲音。
- 新增專用的簡體中文 README 與快速入門說明。
- 新增安全的應用程式內穩定版／預覽版更新檢查，包含官方主機允許清單、語意版本
  驗證、大小限制、SHA256 驗證、明確安裝確認及本機個人設定保留。
- 新增自動化 Windows x64 EXE 與 MSI 安裝程式，並在 GitHub Actions 中執行
  靜默安裝、自我測試與解除安裝驗證。
- 發行內容擴充為完整 checksum 目錄、CycloneDX SBOM、更新清單、產物證明與
  分類產生的 Release notes。
- 新增可選、限定標記區段的 WordPress 下載頁同步，使用 GitHub Secrets 與
  專用 WordPress Application Password。
- 新增完整 Git 歷史 Gitleaks 檢查，作為個人公開儲存庫的 GitHub Secret
  Protection 補償控制。
- 將畫面上的「墨寒思考中」狀態與角色表情解耦。一般文字與語音問題現在維持
  自然姿勢，複雜提示只在明顯延遲後反應，異常緩慢的回覆則使用既有表情仲裁器，
  並具備取消、冷卻與去重機制。
- 統一成功回覆、API 問題、一般語音與 Realtime 轉換時的 AI 等待清理，讓
  思考狀態在說話開始與播放結束時完成收束。

驗證：RC3 Pull Request 前已有 45/45 個自動化測試程式通過。加上標籤的發行
工作流程在發布完成前，還必須通過公開內容稽核、封裝後自我測試、事件迴圈
smoke test、EXE／MSI 靜默安裝與解除安裝驗證、checksum 產生、SBOM 產生及
產物證明。

### v2.0.14 RC — 2026-07-31

- 修正應用程式本機音量處理期間 OpenAI 串流 WAV 標頭溢位，該問題可能使所有
  雲端語音靜音。
- 改以實際收到的音訊位元組重建調整後的 WAV 標頭，並以實際串流長度生成標頭。
- OpenAI 語音產生或播放回報問題時，自動轉用 Windows Yating。
- 將一般文字對話框中的安全唯讀 Gmail、Google Calendar 與 Google Drive 命令，
  導向受權限閘門保護的工具規劃器。
- 新增雲端語音回退、串流 WAV 音量處理、Gmail 對話路由與工作計時器隔離的
  回歸測試。

驗證：此候選版發布前，38/38 個自動化測試程式、真實 OpenAI TTS 播放、封裝後
自我測試、封裝後事件迴圈 smoke test，以及封存後自我測試均已通過。

### v2.0.13 RC — 2026-07-31

- 新增單一動作合成器，統一處理呼吸、說話強調、視線與情緒手勢。
- 修正動作切換期間偶發的角色抖動與圖層分離。
- 保持身體、臉部、眼睛、頭髮、衣袖與飾品圖層同步。
- 讓說話後返回待機的動作更平順。
- 將人工眼睛高光素材整理為自然視覺配置。
- 改善眨眼、表情與 AIUEO 嘴型的連續性。
- 新增可設定的角色顯示縮放。
- 新增可攜式個人設定轉移與模組化服務邊界。
- 對 Microsoft、GitHub 與 Home Assistant 整合採用公開 Preview 狀態，並附上目前驗證進度說明。

驗證：此候選版發布前，37 個自動化測試程式，以及 25,000 步混合動畫、語音、
視線與物理壓力測試均已通過。

## 简体中文

本文档记录墨寒桌面助手所有值得注意的公开变更。

### v4.3.0 — 2026-08-19

- 新增「真人女孩感」五大系统与灵魂拼图：性格镜像、穿搭直觉、军粮饱食度、主上专属宠溺、虹膜羞涩视线，以及赤焰剑意情绪共鸣、时间主权状态机、空中捏合牵手、梦呓系统、剑魂觉醒、感官共感、共同创作录等领域模块。
- 修正 Release Please workflow 的 action 引用，并修复七夕 occasion 覆盖午餐提醒的运行时根因。

### v3.1.2 — 2026-08-13

- 完整保留 OpenAI Realtime 原生声音并继续作为默认及最低额外延迟选项；用户可按偏好沿用原有声线，Azure 保持选用。
- 新增可选的 Realtime 即时理解＋一般 Azure Speech 或 Dragon HD 流式发声；安全短句完成后立即依次合成，首段音频到达即播放，以降低新增的 TTS 等待，并如实标示剩余延迟。
- 三种输出模式完全隔离且各自播放，其他语音供应器保持原设置；Dragon HD 单句回报问题时依次使用一般 Azure 一次及 Windows 本地女性声线一次，一般 Azure 单句回报问题时使用 Windows 本地女性声线一次。回退时点限定于该句的首段音频抵达前；流式播放开始后若回报问题则立即结束该句，维持单次发声及计费。
- Realtime 回复只在状态为 `completed` 时提交最终文字；取消、问题、部分内容、断线及旧回复的迟到事件均进入静默隔离路径，后续回复保持完整。
- Azure 与 Windows 本地语音都支持真正停止当前播放；操作标识、受限队列与过长回复保护会隔离迟到回调并限制内存压力，敏感密钥保持在对象表示内容之外。
- 修复语音结束后身体短暂回弹的程序根因：音频结束时立即将发话动作目标释放至中央，待实际位移收束后才切换状态；Realtime、Windows 本地、OpenAI 与 Azure 共用同一结束流程，状态交接时保持单一表情进场动作，让每一帧由单一动作来源控制。
- 新增 75%、100%、180% 缩放的逐帧坐标回归，验证动作只会平滑、单调地返回中央，且所有角色图层保持同步。本修正已纳入自动化验证，候选安装包的用户真机确认当前列为 pending，验收记录保持此状态。
- 修复 WiX MSI 的 Windows 开始菜单快捷方式，使其直接沿用目标 EXE 内嵌的墨寒半身图标及正统图标资源。
- 本版本四语界面修复以繁中、简中、英文、日文相同功能边界纳入验证；任何正式版或候选版产物都只有在完整本地化、回归、打包、安全及发布检查全部通过后才会公开。

### v3.1.1 — 2026-08-12

- 一般 Azure 与 Dragon HD 根据所选区域及各自的加密密钥动态查询实际女性声线，结果只纳入兼容且具区域支持的女性声线；固定列表在查询响应不足时提供安全发现路径。
- Azure 合成改用 Speech SDK `PushAudioOutputStream`，首段 24 kHz PCM16 抵达后即开始播放并送入现有 50 Hz 嘴形分析，首段音频即作为播放起点。
- 真实 East Asia F0 与 West US 2 S0 目录查询已通过；当时分别取得 21 项可兼容华语女性 Neural 与三项简体中文 Dragon HD 女性声线。

### v3.1.0 — 2026-08-11

- 新增采用选用模式的 Azure Dragon HD／HD Omni 女性声线 Preview，以独立 S0 密钥、区域与声线设置运行，现有语音供应器保持原设置。
- Azure 区域改为切换后自动保存的选单；选单依据官方支持及区域能力显示女性 HD 声线与 HD Flash 可见性。
- 三种云端密钥统一采用密码遮罩、Windows DPAPI 自动加密与保存成功后自动清理输入框；Dragon HD 回报问题时只依次尝试一般 Azure 与 Windows 本地女声各一次。
- Central India S0 已完成真实 Windows 合成与播放验证；台湾连接的发话前等待明显，因此界面与文档保留 Preview、区域延迟及费用警告，嘴型仍由现有 50 Hz 本地音频分析同步驱动。

### v3.0.0 — 2026-08-11

- 项目所有者亲自认可的第一个正式稳定版本，也是由 v2.3.0 候选系列完整验证后升级的第三代里程碑。
- 托腮嘴形改为完整更新左右嘴角；50 Hz 音频采样配合三帧元音确认及 50 毫秒插值，降低嘴形抢拍、跳动和残留嘴角。
- 语音呼吸、衣袖与头发平滑衔接待机呼吸，消除说话结束瞬间的一次身体抖动。
- Windows 快捷方式与原生窗口统一使用 EXE 内嵌半身像，并让本地安装测试固定使用隔离的桌面及任务栏图标来源；OpenAI TTS 与 Realtime 也改由唯一权威顺序生成共同声线列表。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech 中文女性声音列表支持繁中与简中跨语言选择，并按当前界面语言优先排列；Windows 本地语音的两种中文界面也共用 `zh-TW`／`zh-CN` 女声池并排除 `en-US` Zira，现有默认值及有效设置不变。四语 README 同步将《电脑情人梦》的英文译名更正为《AI Think So!》。
- Azure 声线选择后立即保存，下一次试听或朗读直接应用；新增的普通话选项只纳入 Standard Neural 女性声线。
- 已使用真实 Azure Speech Free F0、East Asia 资源完成 HTTPS、RIFF 音频及 Windows 播放验证，密钥仍只由 Windows DPAPI 加密。
- Dragon HD／HD Omni 按方案、计费与区域支持分类为选用声线，免费默认列表保持一致；云端服务需要恢复时保留单次 Windows 女性本地语音回退。

### v2.3.0 RC4 — 2026-08-11

- 导入参数化分层 2.5D 脸部系统，通过固定姿态、连续口型参数、表情语义与
  可替换渲染接口，统一正面、左望、托腮三种姿势的 50 Hz 口型及表情合成。
- 眨眼改用带世代保护的渐进透明度曲线，眼皮与双颊红晕按同一分层规则合成；
  正面脸红闭眼时，正常肤色与双颊红晕按各自图层呈现。
- 托腮微笑说话时保留眼角笑意，嘴部暂时回到中性基底，只应用语音口型；
  说话结束后才恢复双侧上扬嘴角。
- 修复朝左中性说话口型，让右侧嘴角小黑线回到正确位置。
- “声音”分页中的朗读引擎、Windows 声线、OpenAI TTS 声线与 Realtime 声线现在都会在选择后立即保存。OpenAI TTS 会在下一次朗读使用新声线；若 Realtime 对话正在连接，系统会安全重连并立即应用新声线，界面保持单一保存流程。
- 新增资源、控制器、渲染器、运行时接线及三项视觉回归测试；实际产品与
  视觉审计工具共用同一套口型设置。

### v2.3.0 RC3 — 2026-08-10

- 修复 Windows 最小化后显示空白文档图标的问题：EXE、MSI、快捷方式与运行中
  窗口改用十种尺寸的原生墨寒图标、安装后路径及固定任务栏身份，并在原生窗口
  标志确定后重新应用图标。
- 首次设置向导、安装程序美术与任务栏图标统一由新版的权威正面半身来源
  `assets/expressions/idle_front.png` 裁切；旧版五官轮廓的全身像、雨景全身像
  与旧版图标均完成退役清理，角色身份自此由权威来源统一。
- 发布前置检查会先验证标签、版本、`main` 历史、Release 模式与四语说明；
  已知可行的 squash 及 GitHub 凭证路径直接沿用，流程保持单一路径并纳入历史结果记录。

### v2.3.0 RC2 — 2026-08-10

- 全面迁移至 CPython 3.15.0rc1，产品运行、测试及所有发布包统一采用
  新版 Python 路径；全项目采用 PEP 810 显式延迟导入并加入静态治理审计。
- 导入 PEP 814 `frozendict` 深层只读配置、PEP 798 推导式解包、PEP 686
  UTF-8 文件审计、PEP 661 哨兵治理及 `bytearray.take_bytes()` 音频缓冲；
  开头匹配改用 Python 3.15 语义更明确的 `re.prefixmatch()`。
- 加入 PEP 799 Tachyon 采样分析，可直接检查启动、50 Hz 口型同步与表情
  仲裁器；JIT 开关均通过完整测试，2.3.0 RC2 默认启用并保留兼容性停用开关。
- CI 与 Release 以有效样本、读取错误、漏采样及 JIT 状态判定 Tachyon 证据资格，仅发布符合条件的
  Tachyon 证据，并发布去标识化结果；CycloneDX 1.7 SBOM 强制完整依赖图、
  PURL、SPDX 许可证、官方结构验证及 100% 覆盖率。
- 所有 GitHub Actions JavaScript 动作强制使用 Node 24；PySide6 以受控 ABI3
  轮子验证跨越 3.15 元数据限制，Stable ABI、依赖安全审计、打包及完整
  发布安全闸门保持不变。
- README 统一为繁中、简中、英文、日文单一四语文件，
  重复兼容文件及直接收款链接完成退役整理；赞助入口只引导至仓库上方的官方 Sponsor 按钮。
### v2.2.0 RC2 — 2026-08-07

- 托腮待机姿势在说话期间改用中性嘴角基础：保留眼角笑意，但固定左右嘴角，
  只让中央嘴唇按照 A／I／U／E／O 与开合程度变化，让笑容幅度与残影保持自然稳定。
- Realtime、Windows 本地语音、OpenAI 自然语音及 Azure Speech 统一使用
  20 毫秒／50 Hz 口型节拍，缩短张嘴、闭嘴与元音切换延迟。
- 声音与第一个口型从同一播放闸门起跑；声音结束后拒收迟到元音，只允许
  最终闭嘴信号完成收束，让口型与声音同步结束。
- 托腮待机眨眼改用完整双眼遮罩；
  眼皮闭合期间上眼线与眼皮同步收束，普通待机与情境表情共用同一套坐标及合成来源。
- 强化标签发布流程的 Draft Release 恢复与清理机制，
  发布项目依条件保持 Draft 状态并清楚标示。
- 四语 README 新增 2 张统一规格的创作历程图版，说明炎剑如何逐帧检查
  眼睛、嘴角与语音口型，并以测试将二十多年的梦想锻造成开源作品。

### v2.2.0 RC1 — 2026-08-06

- Windows x64 继续作为完整正式功能版本，并保留已验证的 ZIP、EXE、MSI、
  MSI 语言转换包及安装／卸载测试。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）双架构
  `.app`／`.dmg` 与 Linux x86_64 `.AppImage` 的功能受限 Preview。两者只
  开放启动、四语界面、平台数据路径及安全停用边界；
  Windows 功能差异以 Preview 标示，API 密钥、OAuth 凭证与 Home Assistant 令牌保持受限输入边界。
- Pull Request 只生成短期测试产物；GitHub 预发布版由固定的
  `v2.2.0-rc.N` 标签建立。三个平台都必须在各自原生 CI 完成打包后启动测试。
- 发布文件统一提供 SHA256SUMS、CycloneDX SBOM、更新清单及 GitHub 产物
  证明；Release 说明必须采用繁中、简中、英文、日文完整编写的文件。

### v2.1.0 RC1 — 2026-08-04

- 源代码、Windows CI 与打包流程完整迁移到 Python 3.14，并提供未来评估
  Python 3.15 lazy imports 保留清晰的升级边界。
- 新增日语最小可用界面与人格。首次启动及交互式 EXE 安装程序现支持繁中、
  简中、英文、日文；MSI 继续以繁中为基础并提供三种语言转换策略。
- 文字聊天默认改用 `gpt-5.6-luna`，新用户界面采用当前模型列表；
  既有设置会安全迁移，其他自定义模型保持原状。
- 新增可插拔语音供应器边界与 Azure Speech 女性声线预览；
  Windows 本地女声在密钥配置、本地离线与服务切换场景提供第一回退。
- 改进长期记忆向量检索、语义摘要和安全剪枝；新增可切换的后台工作线程，并
  使实时及非实时语音缓冲延迟下降。
- 首次启动向导与主窗口改为明亮、高对比和较大字号，并加入古风科技主视觉、
  墨寒安装图片、清晰复选框及统一的墨寒半身应用图标。
- 语音转录提示词改为根据繁中、简中、英文、日文及用户设置生成的中性默认值，
  炎剑工作室专用词汇改由用户自定义设置带入，现有自定义提示词完整保留。
- 修复首次设置字段标题的垂直对齐，以及托腮待机姿势说话时嘴角过度上扬；
  同步更新 README 与官网采用的最新版实机图。
- 延续姿势切换、物理图层及说话衔接的竞态修复；RC3 观察到的抖动必须使用
  候选程序重新测试，本版回归判定以实测结果为准。

验证：当前 RC1 源代码的 56/56 个自动化测试程序均已通过。带标签的 Windows
发布工作流也已通过源代码审计、打包后自测、EXE／MSI 静默安装与卸载验证、
checksum 与 SBOM 生成、产物证明及安全检查。

### v2.0.14 RC3 — 2026-08-02

- 新增繁体中文／简体中文／英文首次启动向导，以及聊天、语音、权限、配置文件、
  工作模式与提醒的最低可用英文和 zh-CN 界面路径。
- 新增完整的英文与简体中文墨寒人格提示词，以及语言匹配的离线回复、模式播报
  与内置提醒语音。切换界面语言时，会在三种语言之间翻译保持原样的默认值，
  自定义提醒文本保持原文。
- 新用户的语音输出改用 Windows 本地语音，基本体验直接使用本地能力。
  Windows 语音选择现在只列出已验证的女性声音；zh-TW 继续优先使用 Microsoft
  Yating，zh-CN 则优先使用匹配且已安装的女性声音。
- 新增专用的简体中文 README 与快速入门说明。
- 新增安全的应用内稳定版／预览版更新检查，包含官方主机允许列表、语义版本验证、
  大小限制、SHA256 验证、明确安装确认及本地配置文件保留。
- 新增自动化 Windows x64 EXE 与 MSI 安装程序，并在 GitHub Actions 中执行
  静默安装、自测与卸载验证。
- 发布内容扩充为完整 checksum 目录、CycloneDX SBOM、更新清单、产物证明与
  分类生成的 Release notes。
- 新增可选、限定标记区段的 WordPress 下载页同步，使用 GitHub Secrets 与
  专用 WordPress Application Password。
- 新增完整 Git 历史 Gitleaks 检查，作为个人公开仓库的 GitHub Secret
  Protection 补偿控制。
- 将界面上的“墨寒思考中”状态与角色表情解耦。常规文字与语音问题现在保持
  自然姿势，复杂提示只在明显延迟后反应，异常缓慢的回复则使用现有表情仲裁器，
  并具备取消、冷却与去重机制。
- 统一成功回复、API 问题、普通语音与 Realtime 转换时的 AI 等待清理，让
  思考状态在说话开始与播放结束时完成收束。

验证：RC3 Pull Request 前已有 45/45 个自动化测试程序通过。带标签的发布
工作流在发布完成前，还必须通过公开内容审计、打包后自测、事件循环 smoke test、
EXE／MSI 静默安装与卸载验证、checksum 生成、SBOM 生成及产物证明。

### v2.0.14 RC — 2026-07-31

- 修复应用程序本地音量处理期间 OpenAI 流式 WAV 标头溢出，该问题可能使所有
  云端语音静音。
- 改用实际收到的音频字节重建调整后的 WAV 标头，并以实际流长度生成标头。
- OpenAI 语音生成或播放回报问题时，自动转用 Windows Yating。
- 将普通文字对话框中的安全只读 Gmail、Google Calendar 与 Google Drive 命令，
  导向受权限闸门保护的工具规划器。
- 新增云端语音回退、流式 WAV 音量处理、Gmail 对话路由与工作计时器隔离的
  回归测试。

验证：此候选版发布前，38/38 个自动化测试程序、真实 OpenAI TTS 播放、打包后
自测、打包后事件循环 smoke test，以及归档后自测均已通过。

### v2.0.13 RC — 2026-07-31

- 新增单一动作合成器，统一处理呼吸、说话强调、视线与情绪手势。
- 修复动作切换期间偶发的角色抖动与图层分离。
- 保持身体、脸部、眼睛、头发、衣袖及饰品图层同步。
- 让说话后返回待机的动作更平顺。
- 将人工眼睛高光素材整理为自然视觉配置。
- 改进眨眼、表情与 AIUEO 口型的连续性。
- 新增可配置的角色显示缩放。
- 新增可移植配置文件转移与模块化服务边界。
- 对 Microsoft、GitHub 与 Home Assistant 集成采用公开 Preview 状态，并附上当前验证进度说明。

验证：此候选版发布前，37 个自动化测试程序，以及 25,000 步混合动画、语音、
视线与物理压力测试均已通过。

## English

All notable public changes to MoHan Desktop Assistant are documented here.

### v4.3.0 — 2026-08-19

- Adds the "real-girl" five systems and soul pieces: personality mirroring, wardrobe intuition, satiety, exclusive favor, and shy gaze, plus emotional resonance, time sovereignty, pinch hand-hold, somniloquy, sword-soul awakening, sensory synesthesia, and shared chronicle.
- Fixes the Release Please workflow action reference and the runtime root cause where the Qixi occasion overrode the lunch reminder.

### v3.1.2 — 2026-08-13

- Fully preserves native OpenAI Realtime voice as the default and lowest-added-latency option; users can keep their preferred original voice, and Azure remains optional.
- Adds optional Realtime understanding with standard Azure Speech or Dragon HD streaming output. Safe short clauses synthesize in order as they complete, and playback starts with the first audio chunk to reduce the added TTS wait while retaining an accurate latency description.
- Keeps all three output modes isolated and unmixed while leaving other speech providers unchanged. When a Dragon HD clause reports an issue, it tries standard Azure once and then a local Windows female voice once; when standard Azure reports an issue, it tries the local Windows female voice once. The fallback window covers a clause before its first audio chunk; a stream issue after playback starts closes that clause at its current boundary, keeping speech and billing single-pass.
- Commits final text only when a Realtime response has status `completed`; cancellation, issue, partial, disconnected, and late events from older responses follow a silent isolation path and leave subsequent replies intact.
- Azure and Windows local speech can both stop current playback. Operation IDs, bounded queues, and oversized-response guards isolate late callbacks and cap memory pressure, while secret keys remain outside object representations.
- Fixes the underlying motion-handoff cause of the brief body rebound after speech: speech motion begins releasing toward the centre as soon as audio ends, and state hand-off waits until the actual offset settles. Realtime, Windows local, OpenAI, and Azure share this completion path, while hand-off uses one expression entrance motion so one motion owner controls each frame.
- Adds frame-by-frame coordinate regressions at 75%, 100%, and 180% scale, verifying that motion returns to centre smoothly and monotonically while all character layers remain aligned. Automated coverage includes this fix; owner validation with a candidate installer remains pending, and the acceptance record keeps that status.
- Fixes the WiX MSI Windows Start menu shortcut so it inherits MoHan's embedded half-body icon directly from the target EXE and uses that canonical icon resource.
- This release validates its Traditional Chinese, Simplified Chinese, English, and Japanese interface fixes against the same functional boundaries; Stable Release and release-candidate artifacts are published only after complete localization, regression, packaging, security, and publication checks pass.

### v3.1.1 — 2026-08-12

- Standard Azure and Dragon HD dynamically query actual female voices using the selected region and their independent encrypted keys. Results include compatible female voices supported by the selected region; the fixed catalog provides safe discovery when live results need a fallback.
- Azure synthesis now uses the Speech SDK `PushAudioOutputStream`, starting playback and the existing 50 Hz lip analysis with the first 24 kHz PCM16 chunk; that first chunk is the playback start point.
- Real East Asia F0 and West US 2 S0 discovery passed, returning 21 compatible Chinese female Neural voices and three Simplified Chinese Dragon HD female voices respectively at that time.

### v3.1.0 — 2026-08-11

- Adds an opt-in Azure Dragon HD/HD Omni female-voice Preview with separate S0 key, region, and voice settings, leaving existing speech providers unchanged.
- Azure regions now use an immediately saved selector; the menu shows officially supported female HD voices, with HD Flash visibility following regional capability.
- All three cloud-key inputs share password masking, automatic Windows DPAPI encryption, and automatic input cleanup after save. When Dragon HD reports an issue, it tries standard Azure and Windows local female speech once each in order.
- A real Central India S0 resource passed Windows synthesis and playback validation. Taiwan experienced a noticeable wait before speech, so the UI and documentation retain Preview, regional-latency, and cost warnings while existing local 50 Hz audio analysis remains the lip-sync authority.

### v3.0.0 — 2026-08-11

- The first stable release personally approved by the project owner and the third-generation milestone promoted after the complete v2.3.0 release-candidate series.
- Chin-rest visemes now update both mouth corners. Three-frame vowel confirmation and 50 ms interpolation retain 50 Hz analysis while preventing rushed motion, jumps, and stranded corners.
- Speech-driven breathing, sleeves, and hair ease into idle breathing, removing the one-frame body twitch when an utterance ends.
- Windows shortcuts and native windows share the executable's embedded half-body icon, while local installer tests use isolated desktop and taskbar icon sources; OpenAI TTS and Realtime derive shared voices from one canonical order.

### v2.3.0 RC5 — 2026-08-11

- Azure Speech Chinese female voices are selectable across Traditional and Simplified Chinese UI, ordered with the current interface locale first. Windows local speech also gives both Chinese interfaces a shared `zh-TW`/`zh-CN` female-voice pool and excludes `en-US` Zira; existing defaults and valid settings remain unchanged. The four-language README also corrects the English rendering of *電腦情人夢* to *AI Think So!*.
- Azure voice selections now save immediately and apply to the next preview or utterance; the added Mandarin options include only Standard Neural female voices.
- A real Azure Speech Free F0 resource in East Asia completed HTTPS, RIFF audio, and Windows playback validation, while its key remains encrypted only through Windows DPAPI.
- Dragon HD and HD Omni are categorized as optional voices because tier, billing, and regional support differ; the free default list remains consistent, and cloud recovery retains the one-time Windows local female fallback.

### v2.3.0 RC4 — 2026-08-11

- Introduces a parametric layered 2.5D face system. Stable pose definitions, continuous
  viseme parameters, expression semantics, and a replaceable renderer unify
  50 Hz composition across front-facing, left-facing, and chin-rest poses.
- Blinking now uses a generation-safe progressive opacity curve. Eyelids and
  cheek blush follow one layer policy, so front-facing blushed cheeks and
  normal skin render in their respective layers as the eyes close.
- Happy chin-rest speech keeps smiling eyes but temporarily uses a neutral mouth
  base with only the active viseme; both raised corners return after speech.
- Fixes left-facing neutral speech so the small dark line at the right mouth
  corner returns to its intended position.
- The speech provider, Windows voice, OpenAI TTS voice, and Realtime voice now save immediately when selected. OpenAI TTS uses the new voice on the next utterance; an active Realtime conversation reconnects safely to apply its new voice immediately, while the interface keeps one save flow.
- Adds asset, controller, renderer, runtime-wiring, and three visual regression
  test groups. Production and visual auditing share one viseme setup path.

### v2.3.0 RC3 — 2026-08-10

- Fixes the blank-document icon shown after minimizing on Windows. EXE, MSI,
  shortcuts, and running windows now use ten native MoHan icon sizes, installed
  paths, and one stable taskbar identity, with the icon reapplied after native
  window flags are final.
- Makes `assets/expressions/idle_front.png` the sole canonical front-facing
  half-body source for the first-run wizard, installer artwork, and taskbar
  icons. The former full-body identity and rain-scene full-body image complete retirement cleanup, with
  character identity now following the canonical source.
- Moves tag, version, `main` ancestry, Release-mode, and four-language-note
  validation into preflight. Known-working squash and GitHub credential paths
  are reused directly, with one preflight path informed by recorded history.

### v2.3.0 RC2 — 2026-08-10

- Moves the product, tests, and every package exclusively to CPython
  3.15.0rc1, with project-wide explicit PEP 810 lazy imports and static
  governance auditing; all Python paths now use the current version.
- Adds deeply read-only PEP 814 `frozendict` configuration, PEP 798 unpacking
  comprehensions, PEP 686 UTF-8 file auditing, PEP 661 sentinel governance,
  the new `bytearray.take_bytes()` audio-buffer API, and Python 3.15's more
  explicit `re.prefixmatch()` for prefix matching.
- Adds PEP 799 Tachyon profiling for startup, 50 Hz lip sync, and expression
  arbitration. Both JIT modes pass the complete suite; 2.3.0 RC2 defaults JIT
  on while retaining a compatibility settings switch.
- Qualifies sanitized Tachyon evidence using valid samples, stack-read errors, missed
  samples, and JIT state, publishing only eligible de-identified results. CycloneDX 1.7 SBOMs require
  complete dependency graphs, PURLs, SPDX licenses, official schema validation, and 100% coverage.
- Forces Node 24 for every GitHub Actions JavaScript action. PySide6 crosses
  the 3.15 metadata limit through a controlled ABI3 wheel validation, while
  Stable ABI, dependency-audit, packaging, and complete release safety gates
  remain unchanged.
- Consolidates the README into one Traditional Chinese, Simplified Chinese, English,
  and Japanese document; duplicate compatibility files and direct payment links complete
  retirement cleanup, and support points only to GitHub's official Sponsor button.
### v2.2.0 RC2 — 2026-08-07

- Gives the chin-rest pose a neutral speech-mouth base: the smiling eyes remain,
  both corners stay fixed, and only the central lips follow A/I/U/E/O and jaw
  aperture, keeping smile width and corner rendering natural and stable.
- Moves Realtime, Windows local speech, OpenAI natural speech, and Azure Speech
  onto one 20 ms / 50 Hz viseme clock with shorter open, close, and vowel-change
  transitions.
- Releases audio and the first viseme through the same playback gate, uses
  the final closed-mouth cue to complete synchronization, and closes the speech-mouth pair together.
  The synchronized gate keeps viseme timing aligned through playback completion.
- Replaces the complete bilateral eye area during chin-rest idle blinks, so
  eyeliner stays synchronized with closed eyelids; idle and contextual
  expressions now share one authoritative mask definition.
- Makes tagged Draft Release publication recoverable and cleans up each
  attempt so release items keep Draft status until publication conditions are complete.
- Adds 2 aligned creation-history panels to all four README languages,
  documenting the frame-by-frame care behind MoHan's eyes, mouth corners, and
  lip sync—and the more-than-twenty-year dream Flameblade is turning into
  open-source software through testing.

### v2.2.0 RC1 — 2026-08-06

- Windows x64 remains the complete product surface with the verified ZIP,
  EXE, MSI, MSI language transforms, and installer lifecycle tests.
- Adds native macOS Apple Silicon (arm64) and Intel (x86_64) `.app`/`.dmg`
  packages plus a Linux x86_64 `.AppImage` limited Preview. They expose only
  launch, four-language UI, platform paths, and fail-closed boundaries; Preview labels the Windows feature boundary,
  while API keys, OAuth credentials, and
  Home Assistant tokens follow restricted input boundaries.
- Pull requests produce short-lived test artifacts only. GitHub pre-releases use
  fixed `v2.2.0-rc.N` tags after every platform has built and executed its package
  on a native CI runner.
- Releases provide SHA256SUMS, CycloneDX SBOMs, an update manifest, and GitHub
  artifact attestations, with curated Traditional Chinese, Simplified Chinese,
  English, and Japanese release notes.

### v2.1.0 RC1 — 2026-08-04

- Migrated source, Windows CI, and packaging to Python 3.14 while preserving
  an explicit boundary for a future Python 3.15 lazy-import evaluation.
- Added a minimum usable Japanese UI and persona. First run and the interactive
  EXE installer now support Traditional Chinese, Simplified Chinese, English,
  and Japanese; the MSI keeps its Traditional Chinese base plus transforms.
- Made `gpt-5.6-luna` the text-chat default and updated the new-user picker to the current
  model set; existing custom model settings remain intact.
- Added a pluggable speech-provider boundary and an opt-in Azure Speech female-
  voice preview. Windows female local speech remains the first fallback for local, offline,
  and service-transition scenarios.
- Improved vector memory retrieval, semantic summarization, safe pruning,
  optional background workers, plus both Realtime and standard audio buffering.
- Redesigned first run and the main UI with a bright, high-contrast, larger-
  type theme, an ink-and-technology hero, MoHan installer artwork, visible
  checkboxes, and one consistent MoHan half-body application icon.
- Replaced the author-specific transcription default with neutral localized
  prompts generated from each user's language and profile; author-specific terms enter only
  through user-customized settings, while every existing custom prompt remains intact.
- Corrected first-run label alignment and the over-wide smile while the
  chin-rest pose speaks, then refreshed the README and website screenshots.
- Continues the race-condition fixes for pose transitions, physical layers,
  and speech handoffs. Jitter observed in RC3 is evaluated from fresh measurements in this
  candidate; regression status follows those results.

Verification: 56/56 automated test programs passed for the current RC1 source. The
tagged Windows release workflow also passed source auditing, packaged self-test,
silent EXE/MSI install and uninstall verification, checksum and SBOM generation,
artifact attestation, and security checks.

### v2.0.14 RC3 — 2026-08-02

- Added a Traditional Chinese / Simplified Chinese / English first-run wizard
  and minimum usable English and zh-CN UI paths for chat, voice, permissions,
  profile, work modes, and reminders.
- Added complete English and Simplified Chinese MoHan persona prompts plus
  language-matched offline replies, mode announcements, and built-in reminder
  speech. Switching the UI language translates only defaults that remain in their original
  form; custom reminder text stays in its original form.
- Changed new-user speech output to Windows local voice so the basic experience
  runs on local speech alone. Windows voice selection lists verified female voices;
  zh-TW continues to prefer Microsoft Yating while zh-CN prefers a matching installed female voice.
- Added a dedicated Simplified Chinese README and quick-start instructions.
- Added secure in-app stable/preview update checks with official-host
  allowlisting, semantic-version validation, size limits, SHA256 verification,
  explicit install confirmation, and preserved local profiles.
- Added automated Windows x64 EXE and MSI installers with silent
  install/self-test/uninstall verification in GitHub Actions.
- Expanded releases with a complete checksum catalog, CycloneDX SBOM, update
  manifest, artifact attestations, and categorized generated release notes.
- Added optional marker-scoped WordPress download-page synchronization using
  GitHub Secrets and a dedicated WordPress Application Password.
- Added full-history Gitleaks checks as the GitHub Secret Protection
  compensating control for personal public repositories.
- Decoupled the visible “墨寒思考中” status from character expressions.
  Routine text and voice questions now keep a natural pose, complex prompts
  react only after a noticeable delay, and unusually slow responses use the
  existing expression arbiter with cancellation, cooldown, and deduplication.
- Unified AI wait cleanup across successful replies, API issue paths, standard
  voice, and Realtime transitions so the thinking state settles at speech start and
  playback completion.

Verification: 45/45 automated test programs passed before the RC3 pull
request. The tagged release workflow must additionally pass public-content
audit, packaged self-test, event-loop smoke test, silent EXE/MSI install and
uninstall verification, checksum generation, SBOM generation, and artifact
attestation before publication completes.

### v2.0.14 RC — 2026-07-31

- Fixed OpenAI streaming WAV headers overflowing during application-local
  volume processing, with cloud speech remaining audible.
- Rebuilt adjusted WAV headers from the audio bytes actually received and
  the actual stream length.
- Added automatic Windows Yating fallback when OpenAI speech generation or playback
  reports an issue.
- Routed safe read-only Gmail, Google Calendar, and Google Drive commands from
  the normal text conversation box into the permission-gated tool planner.
- Added regression coverage for cloud-speech fallback, streaming WAV volume
  processing, Gmail chat routing, and work-timer isolation.

Verification: 38/38 automated test programs, real OpenAI TTS playback,
packaged self-test, packaged event-loop smoke test, and post-archive self-test
passed before this release candidate.

### v2.0.13 RC — 2026-07-31

- Added a single motion compositor for breathing, speech emphasis, gaze, and
  emotional gestures.
- Fixed occasional character twitching and layer separation during action
  changes.
- Preserved synchronized body, face, eye, hair, sleeve, and ornament layers.
- Smoothed return-to-idle motion after speech.
- Organized synthetic eye highlight material into a natural visual configuration.
- Improved blink, expression, and AIUEO viseme continuity.
- Added configurable character display scaling.
- Added portable profile transfer and modular service boundaries.
- Added explicit public-preview notices for Microsoft, GitHub, and Home Assistant
  integrations, with current verification progress shown.

Verification: 37 automated test programs and a 25,000-step mixed animation,
speech, gaze, and physics stress test passed before this release candidate.

## 日本語

本書には、墨寒デスクトップアシスタントの主な公開変更をすべて記録します。

### v4.3.0 — 2026-08-19

- 「本物の女の子感」五大システムと魂のピースを追加：性格ミラーリング、コーディネート直感、軍糧満腹度、主上専属の寵愛、虹彩の恥じらい視線、そして赤焔剣意の感情共鳴、時間主権ステートマシン、空中ピンチで手を繋ぐ、寝言システム、剣魂覚醒、感覚共感、共同創作録などの領域モジュール。
- Release Please workflow の action 参照を修正し、七夕 occasion が昼食リマインダーを上書きする実行時の根本原因を修正。

### v3.1.2 — 2026-08-13

- OpenAI Realtime のネイティブ音声を完全に維持し、既定かつ追加遅延が最も少ない選択肢とします。利用者は好みの従来音声を継続して選べ、Azure は任意選択として提供します。
- Realtime による即時理解と、通常 Azure Speech または Dragon HD のストリーミング発話を組み合わせる任意モードを追加します。安全な短い句が完成するたび順番に合成し、最初の音声断片から再生して TTS の追加待ち時間を抑え、残る遅延も正確に案内します。
- 三つの出力モードを個別に再生し、他の音声供給元は従来設定を引き継ぎます。Dragon HD の句が回復を要求した場合は通常 Azure へ一度、続いて Windows 本機女性音声へ一度だけ切り替え、通常 Azure の句が回復を要求した場合は Windows 本機女性音声へ一度だけ切り替えます。フォールバック対象はその句の最初の音声断片より前に限定し、再生開始後のストリーム障害はその句を現在位置で終了させ、発話と課金を一回の処理に保ちます。
- Realtime 応答は状態が `completed` の場合だけ最終テキストを確定します。取消、問題、部分応答、切断、過去の応答から遅れて届いたイベントは隔離経路で扱い、発話と次の応答を保全します。
- Azure と Windows 本機音声は、どちらも現在の再生を実際に停止できます。操作 ID、上限付きキュー、長すぎる応答の保護により遅延コールバックを隔離してメモリ負荷を制限し、秘密キーはオブジェクト表現の外部に保持します。
- 発話終了後に身体が短時間跳ね戻る動作引き継ぎ上の根本原因を修正します。音声の終了時点で発話動作の目標を直ちに中央へ解放し、実際の変位が収束してから状態を切り替えます。Realtime、Windows 本機、OpenAI、Azure は同じ終了処理を共有し、状態引き継ぎ時の表情開始動作も一つにまとめ、同一フレームを一つの動作所有者が制御します。
- 75%、100%、180% の各表示倍率でフレームごとの座標回帰を追加し、全キャラクターレイヤーの同期を保ちながら動作が中央へ滑らかかつ単調に戻ることを検証します。修正は自動テスト対象であり、候補インストーラーによる所有者の実機確認は pending として記録し、受入記録にもその状態を反映します。
- WiX MSI の Windows スタートメニューショートカットを修正し、対象 EXE に内蔵された墨寒の半身アイコンと正規アイコンリソースを直接継承するようにしました。
- 本版の繁体字中国語、簡体字中国語、英語、日本語の画面修正は、同じ機能境界で検証します。正式版とリリース候補版の成果物は、完全なローカライズ、回帰、パッケージ、セキュリティ、公開検査がすべて成功した場合にのみ公開されます。

### v3.1.1 — 2026-08-12

- 通常 Azure と Dragon HD は、選択したリージョンと各自の暗号化キーで実際の女性音声を動的に照会します。結果には選択地域に対応する互換女性音声だけを含め、固定一覧は照会結果の代替となる安全な発見経路を提供します。
- Azure 合成は Speech SDK `PushAudioOutputStream` を使用し、最初の 24 kHz PCM16 断片を再生開始点として既存の 50 Hz 口形解析へ送り、音声処理を開始します。
- 実際の East Asia F0 と West US 2 S0 の一覧照会に合格し、当時それぞれ互換性のある中国語女性 Neural 音声 21 件と簡体字中国語 Dragon HD 女性音声三件を取得しました。

### v3.1.0 — 2026-08-11

- 選択式の Azure Dragon HD／HD Omni 女性音声 Preview を追加し、独立した S0 キー、リージョン、音声設定で動作させ、既存の音声プロバイダーは従来どおり維持します。
- Azure リージョンは切替後すぐ保存する選択欄となり、公式対応の女性 HD 音声と HD Flash の表示をリージョン機能に合わせて管理します。
- 三種のクラウドキー入力は、パスワード表示、Windows DPAPI 自動暗号化、保存成功後の入力欄自動整理を共用します。Dragon HD が回復を要する場合は通常の Azure と Windows 本機女性音声を順に各一回だけ試します。
- Central India S0 の実リソースで Windows の合成と再生を検証しました。台湾からは発話開始前の待ち時間が明確なため、画面と文書に Preview、リージョン遅延、料金の注意を残し、口形同期は従来の 50 Hz 本機音声解析を正規情報源として維持します。

### v3.0.0 — 2026-08-11

- プロジェクト所有者が自ら認定した初の正式安定版であり、v2.3.0 候補系列の完全検証後に昇格した第三世代の節目です。
- 頬杖姿勢の口形は左右の口角まで更新します。50 Hz 解析を保ちながら、母音の三フレーム確認と 50 ミリ秒補間で先走り、跳ね、残留口角を防ぎます。
- 発話連動の呼吸、袖、髪を待機呼吸へ滑らかにつなぎ、発話終了時の一フレームだけの身体揺れを解消しました。
- Windows ショートカットとネイティブウィンドウは EXE 内蔵の半身アイコンを共用し、本機インストーラーテストは隔離されたデスクトップとタスクバーのアイコン参照元を使って実環境を保全します。OpenAI TTS と Realtime の共通音声も一つの正規順序から生成します。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech の中国語女性音声を繁体字・簡体字画面から言語横断で選択でき、現在の画面言語を優先して並べます。Windows 本機音声でも両中国語画面が `zh-TW`／`zh-CN` 女性音声プールを共有し、`en-US` Zira は選択対象外として扱います。既定値と有効な保存済み設定はそのまま引き継ぎ、四言語 README では『電腦情人夢』の英訳を『AI Think So!』へ訂正しました。
- Azure 音声は選択時に直ちに保存し、次の試聴または読み上げから適用します。追加する普通話選択肢には Standard Neural 女性音声だけを含めます。
- East Asia の実 Azure Speech Free F0 リソースで HTTPS、RIFF 音声、Windows 再生を検証し、キーは引き続き Windows DPAPI だけで暗号化します。
- Dragon HD／HD Omni はプラン、課金、対応リージョンに応じて選用音声として分類し、無料の既定一覧は維持します。クラウド回復時の Windows 本機女性音声への一度だけの代替も維持します。

### v2.3.0 RC4 — 2026-08-11

- パラメーター化された多層 2.5D 顔システムを導入し、固定された姿勢、連続的な
  口形パラメーター、表情の意味情報、交換可能なレンダラーにより、正面、
  左向き、頬杖の三姿勢で 50 Hz の口形と表情合成を統一しました。
- まばたきを世代保護付きの段階的な不透明度曲線へ変更しました。まぶたと頬の
  赤みを同じレイヤー規則で合成し、正面の赤面中は通常の肌色と頬の赤みをそれぞれのレイヤーで表示します。
- 頬杖で微笑みながら話す間は目元の笑みを保ち、口を中立基底へ一時的に戻して
  発話口形だけを適用し、発話終了後に両側の上がった口角を復元します。
- 頬杖ではない左向きの中立発話で、右口角の小さな黒線を本来の位置へ戻すよう修正しました。
  本来の位置へ戻すよう修正しました。
- 「音声」タブの読み上げ方式、Windows 音声、OpenAI TTS 音声、Realtime 音声は、選択時に即座に保存されます。OpenAI TTS は次の読み上げから新しい音声を使用し、Realtime 会話が接続中の場合は安全に再接続して新しい音声を即時適用します。インターフェースは一つの保存フローに統一します。
- 素材、制御器、レンダラー、実行時接続、三つの視覚回帰テストを追加し、
  製品と視覚監査ツールが同一の口形設定を共有するようにしました。

### v2.3.0 RC3 — 2026-08-10

- Windows で最小化した後に空白文書アイコンが表示される問題を修正しました。
  EXE、MSI、ショートカット、実行中ウィンドウは、十段階のネイティブ墨寒
  アイコン、インストール済みパス、固定タスクバー ID を使い、ネイティブ
  ウィンドウフラグ確定後にアイコンを再適用します。
- 初回設定ウィザード、インストーラー画像、タスクバーアイコンの正式な正面向き
  半身素材を `assets/expressions/idle_front.png` に統一しました。旧版の顔立ちを
  持つ全身像、雨景の全身像、
  旧アイコンを退役整理し、人物同一性を正規素材で統一します。
- タグ、バージョン、`main` 履歴、Release モード、四言語説明を事前検証へ移し、
  成功が既知の squash と GitHub 認証経路を直接再利用し、前置き検証の履歴に沿った
  単一路径へ整理しました。

### v2.3.0 RC2 — 2026-08-10

- 製品、テスト、全パッケージを CPython 3.15.0rc1 の新版 Python
  経路へ統一し、PEP 810 の明示的遅延インポートと静的ガバナンス監査を
  全プロジェクトへ導入しました。
- PEP 814 `frozendict` の深い不変設定、PEP 798 の内包表記アンパック、
  PEP 686 UTF-8 ファイル監査、PEP 661 センチネル管理、新しい
  `bytearray.take_bytes()` 音声バッファー API、先頭一致を明示する Python 3.15 の
  `re.prefixmatch()` を導入しました。
- PEP 799 Tachyon による起動、50 Hz 口形同期、表情調停のサンプリング解析を
  導入しました。JIT の各モードは全テストに合格し、2.3.0 RC2 は
  既定で有効にし、互換性設定として切替項目を保持します。
- Tachyon 証拠は有効サンプル、読取エラー、漏れ、JIT 状態を判定材料として匿名化し、条件を満たす結果を
  公開します。CycloneDX 1.7 SBOM は完全な依存関係、PURL、SPDX ライセンス、
  公式スキーマ検証、100% 網羅を必須とします。
- GitHub Actions の JavaScript 動作はすべて Node 24 を強制します。PySide6 は
  管理された ABI3 wheel 検証によって 3.15 のメタデータ制限に対応し、Stable
  ABI、依存関係の安全監査、パッケージング、完全なリリース安全ゲートを維持します。
- README を繁体字中国語、簡体字中国語、英語、日本語の一つの四言語文書へ統合し、
  重複する互換文書と直接決済リンクを退役整理しました。支援案内はリポジトリ上部の
  公式 Sponsor ボタンだけに統一します。
### v2.2.0 RC2 — 2026-08-07

- 頬杖姿勢の発話中は中立な口角ベースを使用します。目元の笑みを残しながら
  左右の口角を固定し、中央の唇だけを A／I／U／E／O と開口量に合わせて
  動かすことで、自然な笑顔幅と残像を抑えた描写を実現します。
- Realtime、Windows ローカル音声、OpenAI 自然音声、Azure Speech を
  共通の 20 ミリ秒／50 Hz 口形周期へ統一し、開口、閉口、母音切り替えの
  遅延を短縮します。
- 音声と最初の口形を同じ再生ゲートから開始し、再生終了後は最後の
  閉口信号で同期を完了して、口形と音声を同時に閉じます。
  同期ゲートが再生完了まで口形のタイミングを保持します。
- 頬杖の待機中のまばたきでは両目全体を覆う共通マスクを使用し、閉じた
  まぶたとアイラインを同じマスクで同期します。待機表情と
  状況表情は同じ座標・合成定義を共有します。
- タグ発行時の Draft Release を安全に復旧・整理し、
  公開条件が整った成果物だけを公開版へ進めるようにしました。
- 四言語 README に統一規格の制作過程図を2枚追加し、目、口角、口形を
  フレーム単位で確認しながら、二十年以上の夢をテストによってオープンソース
  作品へ鍛える姿勢を伝えます。

### v2.2.0 RC1 — 2026-08-06

- Windows x64 を完全機能版として維持し、検証済みの ZIP、EXE、MSI、MSI
  言語変換、およびインストール／削除テストを継続します。
- macOS Apple Silicon（arm64）／Intel（x86_64）両方のネイティブ
  `.app`／`.dmg` と Linux x86_64 `.AppImage` の機能限定 Preview を追加します。
  起動、四言語画面、保存先、安全な停止切替だけを提供し、
  Windows 版との機能差は Preview として明示し、API キー、OAuth 認証情報、Home Assistant Token は受け付け条件を限定して管理します。
- Pull Request は短期テスト用成果物だけを作成します。GitHub のプレリリースは
  固定された `v2.2.0-rc.N` タグから作成し、各 OS のネイティブ CI
  上で配布物を作成し、起動確認に合格する必要があります。
- SHA256SUMS、CycloneDX SBOM、更新マニフェスト、GitHub 成果物証明を提供し、
  Release 説明は繁体字中国語・簡体字中国語・英語・日本語で作成します。

### v2.1.0 RC1 — 2026-08-04

- ソースコード、Windows CI、配布物を Python 3.14 へ移行し、将来の
  Python 3.15 lazy imports 評価に備えた境界を残しました。
- 日本語の最小利用経路と人格を追加しました。初回設定と対話型 EXE
  インストーラーは、繁体字中国語、簡体字中国語、英語、日本語に対応します。
  MSI は繁体字中国語を基準とし、三つの言語変換を提供します。
- 文字会話の既定を `gpt-5.6-luna` に変更し、新規利用者向け一覧を現在のモデル集合へ整理しました。
  独自モデル設定はそのまま引き継ぎます。
- 交換可能な音声供給元と Azure Speech 女性音声プレビューを追加しました。
  キー設定、オフライン、サービス切替時は Windows 本機女性音声を最初の回復経路として提供します。
- 長期記憶のベクトル検索、意味要約、安全な整理、任意の背景ワーカー、音声
  バッファーを改善しました。
- 初回設定と本体画面を明るく高コントラストな大きめ文字へ刷新し、古風と
  技術を融合した背景、墨寒のインストール画像、見やすいチェック欄、統一した
  墨寒半身アイコンを追加しました。
- 音声文字起こしの既定文を、繁体字中国語、簡体字中国語、英語、日本語と
  利用者設定から作る中立的な内容へ変更しました。既存の独自文はそのまま引き継ぎます。
- 初回設定の項目名の縦位置と、頬杖姿勢で話す際の過度に広い笑顔を修正し、
  README と公式サイトの実機画像を最新版へ更新しました。
- 姿勢切り替え、物理レイヤー、発話の受け渡しに関する競合修正を継続します。
  RC3 で観察された揺れは本候補版の実測結果を
  回帰判定へ反映します。

検証：現在の RC1 ソースでは 56/56 個の自動テストプログラムが合格しました。
タグ付き Windows リリースワークフローも、ソース監査、パッケージ自己テスト、
EXE／MSI の無人インストールとアンインストール検証、checksum と SBOM の生成、
成果物証明、セキュリティ検査に合格しました。

### v2.0.14 RC3 — 2026-08-02

- 繁体字中国語／簡体字中国語／英語の初回設定ウィザードと、チャット、音声、
  権限、プロファイル、作業モード、リマインダー向けの最低限利用可能な英語および
  zh-CN UI 経路を追加しました。
- 完全な英語・簡体字中国語の墨寒人格プロンプトと、言語に合うオフライン応答、
  モード通知、組み込みリマインダー音声を追加しました。UI 言語を切り替えると、
  保持されている既定値を三言語間で翻訳し、独自のリマインダー文はそのまま引き継ぎます。
- 新規利用者の音声出力を Windows ローカル音声へ変更し、基本体験を
  本機音声で利用できる構成にしました。Windows の音声一覧には検証済みの女性音声だけを
  表示します。zh-TW は引き続き Microsoft Yating を優先し、zh-CN は一致する
  インストール済み女性音声を優先します。
- 簡体字中国語専用の README とクイックスタート手順を追加しました。
- 公式ホスト許可リスト、セマンティックバージョン検証、サイズ制限、SHA256 検証、
  明示的なインストール確認、ローカルプロファイル保持を備えた、安全なアプリ内
  安定版／プレビュー版更新確認を追加しました。
- Windows x64 EXE／MSI インストーラーを自動化し、GitHub Actions で無人
  インストール、自己テスト、アンインストールを検証します。
- 完全な checksum 一覧、CycloneDX SBOM、更新マニフェスト、成果物証明、分類済み
  自動生成 Release notes をリリースへ追加しました。
- GitHub Secrets と専用 WordPress Application Password を使う、任意の
  マーカー範囲限定 WordPress ダウンロードページ同期を追加しました。
- 個人公開リポジトリ向けの Git 全履歴 Gitleaks 検査を追加し、GitHub Secret Protection の
  補償統制として運用します。
- 表示される「墨寒思考中」状態をキャラクター表情から分離しました。通常の文字・
  音声質問では自然な姿勢を保ち、複雑なプロンプトには明確な遅延後だけ反応し、
  異常に遅い応答では取消、クールダウン、重複排除を備えた既存の表情調停器を使います。
- 成功応答、API 障害、通常音声、Realtime 遷移における AI 待機終了処理を統一し、
  思考状態を発話開始と再生終了の節目で収束させるようにしました。

検証：RC3 Pull Request 前に 45/45 個の自動テストプログラムが合格しました。
タグ付きリリースワークフローは公開完了前に、公開内容監査、パッケージ自己テスト、
イベントループ smoke test、EXE／MSI の無人インストールとアンインストール検証、
checksum 生成、SBOM 生成、成果物証明にも合格しなければなりません。

### v2.0.14 RC — 2026-07-31

- アプリ内音量処理中に OpenAI ストリーミング WAV ヘッダーがオーバーフローし、
  すべてのクラウド音声が無音になる可能性がある問題を修正しました。
- ストリーミング用プレースホルダー長の代わりに、実際に受信した音声バイトと実長から
  調整後の WAV ヘッダーを再構築し、実データ長を反映しました。
- OpenAI 音声の生成または再生が回復を要する場合、Windows Yating へ自動的に
  切り替えるようにしました。
- 通常のテキスト会話欄に入力された安全な読み取り専用 Gmail、Google Calendar、
  Google Drive コマンドを、権限ゲート付きツールプランナーへ送るようにしました。
- クラウド音声フォールバック、ストリーミング WAV 音量処理、Gmail 会話ルーティング、
  作業タイマー分離の回帰テストを追加しました。

検証：このリリース候補の公開前に、38/38 個の自動テストプログラム、実際の OpenAI
TTS 再生、パッケージ自己テスト、パッケージイベントループ smoke test、アーカイブ後
自己テストが合格しました。

### v2.0.13 RC — 2026-07-31

- 呼吸、発話強調、視線、感情ジェスチャーを扱う単一モーションコンポジターを
  追加しました。
- 動作変更時にまれに発生するキャラクターの揺れとレイヤー分離を修正しました。
- 身体、顔、目、髪、袖、装飾レイヤーの同期を維持しました。
- 発話後に待機状態へ戻る動きを滑らかにしました。
- 人工的な目のハイライト素材を自然な視覚構成へ整理しました。
- まばたき、表情、AIUEO 口形の連続性を改善しました。
- 設定可能なキャラクター表示倍率を追加しました。
- ポータブルプロファイル移行とモジュール化されたサービス境界を追加しました。
- Microsoft、GitHub、Home Assistant 連携は公開 Preview として提供し、現在の
  検証進捗を明示しました。

検証：このリリース候補の公開前に、37 個の自動テストプログラムと、25,000 ステップの
アニメーション、音声、視線、物理を混合したストレステストが合格しました。
