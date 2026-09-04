# 墨寒多感官視覺專案代理鐵則／墨寒多感官视觉项目代理铁则／MoHan Multisensory Vision Agent Iron Rules／墨寒マルチセンサリービジョン エージェント鉄則

## 繁體中文

本檔案對所有在本專案工作的 AI 代理（Codex、Claude 或其他）具有強制力，優先於任何代理自身的工作習慣。

### 鐵則一：開工先盤點（2026-08-26 由專案擁有者核定）

- 每輪開工的第一件事，必須先清點正式輸出目錄的實際檔案：數量、尺寸、模式、SHA-256，並以實測結果更新正式計數。
- 在盤點完成之前，禁止提出或啟動任何新模型、新工具、新技術路線。
- 候選成品堆積超過一輪未驗收，視為交接失職。
- 「保守計數」必須搭配「主動驗收」：只保守不驗收，等於永遠是零；攻下的山頭要插旗，沒攻下的山頭不准謊報插旗。

背景教訓：PoseAtlas 24 主視角與 600 分層素材早於 2026-08-16 前後即已實質完成並存放於 `assets/pose-atlas/`（v4-source／v4-working／v4-layered），但因連續多輪只開新技術路線（LoRA、3D 拓撲、模型升級）而未回頭驗收，交接計數停留在 0／24、0／600，造成專案擁有者誤以為技術卡關持續存在，浪費三天。2026-08-26 完成逐張驗收後確認：唯一真實缺陷僅為分層重組時的頸部接縫 Alpha 縫隙（已修復並備份）。

### 正式素材目錄狀態（2026-08-26 驗收）

- `assets/pose-atlas/v4-working/`：24 主視角，1024×1536 RGBA，全部通過檔案閘門與 SHA-256 對照（BUILD-METADATA.json）。
- `assets/pose-atlas/v4-layered/`：600 層（24 視角 × 25 層），全部通過檔案閘門；Z-order 重組與母圖 RGB 零差；層邊界接縫 Alpha 已修復（證據見 docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身份權威：使用者 2026-08-26 三批「真墨寒」展示確認；授權：v4-source/PROVENANCE.json（權利人 2026-08-16 確認）。
- 修改任何上述素材前必須備份並記錄修改前 SHA-256。
- 2026-09-02 執行期切換：`assets/pose-atlas/v5-base/`（24 主視角）與 `assets/pose-atlas/v5-base-layered/`（600 層）成為執行期、封裝與 packaged self-test 實際載入的二代素體；目前世代的目錄名只在 `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）定義一次。`v4`／`v4-layered` 保留為封存與 golden 建置器的一代校準參考，不刪除；`BODY_PROFILE_ID` 已於同日升為 `mohan-body-v2`（issue #140 選項 3：一代服裝套件於匯入與執行期一律拒絕，不設寬限）。

### 通用要求

- 回報一律使用台灣繁體中文，遵循「打到哪裡就報到哪裡」格式：【完成】（命令、退出碼、路徑、雜湊、目視結論）、【目前阻塞】、【下一步】。
- 遵循上層 `D:\FlamebladeStudio\CodexProjects\AGENTS.md` 與 `CODEX_PROJECT_HANDOFF.md` 的全域原則。
- 測試分層：開發過程用 `fast`，提交前跑一次 `gate`；若影響對照表找不到改動檔案，必須接受 fast 的完整套 fallback。

### CHANGELOG 片段規則

每個 Pull Request 的變更都必須新增 `changelog.d/<name>.md`，不要直接編輯 `CHANGELOG.md` 的未發布段落。新片段的標題與條列依繁中／簡中／English／日本語以全形斜線 `／` 分隔並保持平行；既有未發布內容的遷移片段可保留原文。Release Please 先產生版本標題，再由 `tools/assemble_changelog.py` 組裝。

## 简体中文

本文件对所有在本项目工作的 AI 代理（Codex、Claude 或其他）具有强制力，优先于任何代理自身的工作习惯。

### 铁则一：开工先盘点（2026-08-26 由项目所有者核定）

- 每轮开工的第一件事，必须先清点正式输出目录的实际文件：数量、尺寸、模式、SHA-256，并以实测结果更新正式计数。
- 在盘点完成之前，禁止提出或启动任何新模型、新工具、新技术路线。
- 候选成品堆积超过一轮未验收，视为交接失职。
- 「保守计数」必须搭配「主动验收」：只保守不验收，等于永远是零；攻下的山头要插旗，没攻下的山头不准谎报插旗。

背景教训：PoseAtlas 24 主视角与 600 分层素材早于 2026-08-16 前后即已实质完成并存放于 `assets/pose-atlas/`（v4-source／v4-working／v4-layered），但因连续多轮只开新技术路线（LoRA、3D 拓扑、模型升级）而未回头验收，交接计数停留在 0／24、0／600，造成项目所有者误以为技术卡关持续存在，浪费三天。2026-08-26 完成逐张验收后确认：唯一真实缺陷仅为分层重组时的颈部接缝 Alpha 缝隙（已修复并备份）。

### 正式素材目录状态（2026-08-26 验收）

- `assets/pose-atlas/v4-working/`：24 主视角，1024×1536 RGBA，全部通过文件闸门与 SHA-256 对照（BUILD-METADATA.json）。
- `assets/pose-atlas/v4-layered/`：600 层（24 视角 × 25 层），全部通过文件闸门；Z-order 重组与母图 RGB 零差；层边界接缝 Alpha 已修复（证据见 docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身份权威：用户 2026-08-26 三批「真墨寒」展示确认；授权：v4-source/PROVENANCE.json（权利人 2026-08-16 确认）。
- 修改任何上述素材前必须备份并记录修改前 SHA-256。
- 2026-09-02 运行时切换：`assets/pose-atlas/v5-base/`（24 主视角）与 `assets/pose-atlas/v5-base-layered/`（600 层）成为运行时、封装与 packaged self-test 实际加载的二代素体；当前世代的目录名只在 `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）定义一次。`v4`／`v4-layered` 保留为封存与 golden 构建器的一代校准参考，不删除；`BODY_PROFILE_ID` 已于同日升为 `mohan-body-v2`（issue #140 选项 3：一代服装套件在导入与运行时一律拒绝，不设宽限）。

### 通用要求

- 汇报一律使用台湾正体中文，遵循「打到哪里就报到哪里」格式：【完成】（命令、退出码、路径、哈希、目视结论）、【目前阻塞】、【下一步】。
- 遵循上层 `D:\FlamebladeStudio\CodexProjects\AGENTS.md` 与 `CODEX_PROJECT_HANDOFF.md` 的全局原则。
- 测试分层：开发过程中用 `fast`，提交前跑一次 `gate`；如果影响对照表找不到改动文件，必须接受 fast 的完整套 fallback。

### CHANGELOG 片段规则

每个 Pull Request 的变更都必须新增 `changelog.d/<name>.md`，不要直接编辑 `CHANGELOG.md` 的未发布段落。新片段的标题与列表项按繁中／简中／English／日本語以全角斜线 `／` 分隔并保持平行；既有未发布内容的迁移片段可保留原文。Release Please 先产生版本标题，再由 `tools/assemble_changelog.py` 组装。

## English

This file is binding for every AI agent (Codex, Claude, or any other) working in this project and overrides any agent's own working habits.

### Iron Rule 1: Inventory before anything else (ratified by the project owner on 2026-08-26)

- The first action of every work session must be a physical inventory of the formal output directories: file counts, dimensions, modes, and SHA-256 hashes, with the formal tallies updated from measured results.
- Until the inventory is complete, proposing or launching any new model, tool, or technical route is forbidden.
- Candidate deliverables left unreviewed for more than one session constitute a handoff failure.
- "Conservative counting" must be paired with "active acceptance": counting conservatively without ever verifying keeps the tally at zero forever. Plant the flag on captured hills; never fake a flag on hills not taken.

Background lesson: the PoseAtlas 24 master views and 600 layered assets were substantially complete around 2026-08-16 and stored under `assets/pose-atlas/` (v4-source / v4-working / v4-layered), but successive sessions kept opening new technical routes (LoRA, 3D topology, model upgrades) without ever re-inspecting the outputs. The handoff tally stayed at 0/24 and 0/600, making the owner believe a technical blocker still existed and wasting three days. The 2026-08-26 per-asset acceptance confirmed the only real defect was a neck-seam alpha gap in layer recomposition (fixed, with backups).

### Formal asset directory status (accepted 2026-08-26)

- `assets/pose-atlas/v4-working/`: 24 master views, 1024×1536 RGBA, all passing the file gate and SHA-256 cross-check (BUILD-METADATA.json).
- `assets/pose-atlas/v4-layered/`: 600 layers (24 views × 25 layers), all passing the file gate; Z-order recomposition matches the master views with zero RGB difference; layer-boundary seam alpha repaired (evidence in docs/release-evidence/pose-atlas-v4-layered-seam-qa/).
- Identity authority: the owner's three "true MoHan" batches confirmed on 2026-08-26; licensing: v4-source/PROVENANCE.json (rights holder confirmed 2026-08-16).
- Any modification to these assets requires a prior backup and a recorded pre-modification SHA-256.
- Runtime switch on 2026-09-02: `assets/pose-atlas/v5-base/` (24 master views) and `assets/pose-atlas/v5-base-layered/` (600 layers) are the second-generation body that the runtime, packaging, and the packaged self-test actually load; the current generation's directory names are defined once, in `domain/constants.py` (`POSE_ATLAS_ROOT_NAME` / `POSE_ATLAS_LAYERED_ROOT_NAME`). `v4` / `v4-layered` stay as the archive and as the generation-1 calibration reference of the golden builder and are not deleted; `BODY_PROFILE_ID` was bumped to `mohan-body-v2` the same day (issue #140, option 3: generation-1 outfit packs are rejected at import and at runtime with no grace period).

### General requirements

- Reports use Taiwanese Traditional Chinese in the "report exactly as far as you fought" format: [Done] (commands, exit codes, paths, hashes, visual conclusions), [Blocked], [Next].
- Follow the global principles in `D:\FlamebladeStudio\CodexProjects\AGENTS.md` and `CODEX_PROJECT_HANDOFF.md`.
- Test tiers: use `fast` during development and run `gate` once before submission; if the impact map cannot find a changed file, accept fast's complete-suite fallback.

### CHANGELOG Fragment Rule

Every Pull Request change must add `changelog.d/<name>.md`; do not edit the unreleased part of `CHANGELOG.md` directly. New fragment titles and bullets must provide Traditional Chinese／Simplified Chinese／English／Japanese in parallel, separated by the full-width slash `／`; migrated unreleased content may retain its original wording. Release Please creates the version heading first, then `tools/assemble_changelog.py` assembles it.

## 日本語

本ファイルは、本プロジェクトで作業するすべての AI エージェント（Codex、Claude、その他）に対して拘束力を持ち、各エージェント自身の作業習慣より優先されます。

### 鉄則一：作業開始前の棚卸し（2026-08-26 プロジェクトオーナー承認）

- 各セッション開始時の最初の作業は、正式出力ディレクトリの実ファイルの棚卸し（数量、寸法、モード、SHA-256）であり、実測結果で正式カウントを更新しなければならない。
- 棚卸し完了前に、新しいモデル、ツール、技術ルートを提案・開始してはならない。
- 候補成果物を 1 セッション以上未検収のまま放置することは、引き継ぎの職務怠慢とみなす。
- 「保守的カウント」は「能動的検収」とセットでなければならない。検収なき保守は永遠にゼロである。奪取した高地には旗を立て、奪取していない高地に偽りの旗を立ててはならない。

背景の教訓：PoseAtlas の 24 主視点と 600 レイヤー素材は 2026-08-16 前後に実質完成し `assets/pose-atlas/`（v4-source／v4-working／v4-layered）に保存されていたが、以降のセッションが新技術ルート（LoRA、3D トポロジー、モデル更新）ばかりを開き検収に戻らなかったため、引き継ぎカウントは 0／24、0／600 のままとなり、オーナーに技術的行き詰まりが続いているという誤解を与え、3 日間を浪費した。2026-08-26 の全数検収により、唯一の実欠陥はレイヤー再合成時の首の継ぎ目アルファ隙間のみ（修復済み・バックアップあり）と確認された。

### 正式素材ディレクトリの状態（2026-08-26 検収）

- `assets/pose-atlas/v4-working/`：24 主視点、1024×1536 RGBA、全ファイルゲートと SHA-256 照合（BUILD-METADATA.json）合格。
- `assets/pose-atlas/v4-layered/`：600 レイヤー（24 視点 × 25 層）、全ファイルゲート合格。Z-order 再合成は母画像と RGB 差ゼロ。レイヤー境界の継ぎ目アルファは修復済み（証拠は docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身元権威：オーナーが 2026-08-26 に三批の「真の墨寒」提示で確認。ライセンス：v4-source/PROVENANCE.json（権利者 2026-08-16 確認）。
- 上記素材の変更前には必ずバックアップと変更前 SHA-256 の記録を行うこと。
- 2026-09-02 の実行時切替：`assets/pose-atlas/v5-base/`（24 主視点）と `assets/pose-atlas/v5-base-layered/`（600 層）が、実行時・パッケージング・packaged self-test が実際に読み込む第二世代素体となった。現行世代のディレクトリ名は `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）で一度だけ定義する。`v4`／`v4-layered` はアーカイブおよび golden ビルダーの第一世代校正参照として残し、削除しない。`BODY_PROFILE_ID` は同日に `mohan-body-v2` へ更新した（issue #140 選択肢 3：第一世代の衣装パックはインポート時と実行時に必ず拒否し、猶予は設けない）。

### 一般要件

- 報告は台湾繁体字中国語を使用し、「戦った所まで正確に報告する」形式に従う：【完了】（コマンド、終了コード、パス、ハッシュ、目視結論）、【現在の障害】、【次の一手】。
- 上位の `D:\FlamebladeStudio\CodexProjects\AGENTS.md` と `CODEX_PROJECT_HANDOFF.md` の全体原則に従う。
- テスト階層：開発中は `fast` を使い、提出前に一度 `gate` を実行します。影響対応表に変更ファイルがない場合は、fast が完全スイートへフォールバックすることを受け入れます。

### CHANGELOG フラグメント規則

各 Pull Request の変更には `changelog.d/<name>.md` を追加し、`CHANGELOG.md` の未公開部分を直接編集してはいけません。新しいフラグメントの見出しと箇条書きは、繁体字中国語／簡体字中国語／English／日本語を全角スラッシュ `／` で区切り、内容を揃えます。既存の未公開内容を移行したフラグメントは元の文言を保持できます。Release Please が先にバージョン見出しを作成し、その後 `tools/assemble_changelog.py` が組み立てます。
