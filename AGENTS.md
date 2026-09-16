# 墨寒多感官視覺專案代理鐵則／墨寒多感官视觉项目代理铁则／MoHan Multisensory Vision Agent Iron Rules／墨寒マルチセンサリービジョン エージェント鉄則

## 跨模型交接入口（2026-09-15）／跨模型交接入口／Cross-model handoff／モデル間引き継ぎ

繁體中文：擁有者已授權 Codex 與 DeepSeek Harness 輪流接續本工作樹。每次接手先讀 `D:/FlamebladeStudio/CodexProjects/shared/agent-handoff/START_HERE.md`，核對 checkpoint 與接手鎖，再沿用本檔其餘規則。Codex 專屬的模型、技能及助理設定只適用於 Codex；其他執行環境須如實登記可用能力，不得假稱具有相同工具。藝術批准、原圖來源、可拆圖層、測試與發布門檻不因模型切換而改變。

简体中文：所有者已授权 Codex 与 DeepSeek Harness 轮流接续此工作树。接手先读上述共享入口，核对 checkpoint 和接手锁。Codex 专属工具设置仅用于 Codex；其他环境如实登记能力。艺术批准、来源、可拆图层、测试和发布门槛保持有效。

English: The owner authorizes alternating Codex and DeepSeek Harness work in this checkout. Read the shared entry above and verify its checkpoint and ownership lock before taking over. Codex-specific model and tool settings apply to Codex only; other hosts must record actual capabilities. Art approval, provenance, detachable layers, testing, and release gates remain binding.

日本語：所有者は Codex と DeepSeek Harness による交代作業を承認しています。上記の共有入口を読み、チェックポイントと担当ロックを確認してから引き継いでください。Codex 専用設定は Codex にのみ適用し、他環境は実際の機能を記録します。原画承認、出所、着脱レイヤー、検証・公開条件は引き続き適用されます。

## 繁體中文

### AI Development Playbook

本專案採用 `masini1491/ai-development-playbook` 作為 AI 協作基準。

Playbook 基準參照（同英文宣告）：`d68d585c2fbdc1fbcaaf38a382fdaceba414248e`

先讀專案規則，再讀[固定版 CHAT_INIT.md](https://github.com/masini1491/ai-development-playbook/blob/d68d585c2fbdc1fbcaaf38a382fdaceba414248e/CHAT_INIT.md) 與同版的任務相關章節。從[本地流程入口](docs/ai-workflow.md) 找現有負責文件；重用同一工作階段已核對的內容，載入範圍聚焦於相關章節，版本固定於上述 commit。

- 技術事實來源：`ARCHITECTURE.md`、相關模組及測試；素材契約見 `tools/art_pipeline/REVIEWED_PARTITIONS.md`。
- 目前工作入口：docs/ai-workflow.md
- 必要驗證：既有 fast/gate 政策、相關 `python -m pytest`、全庫 `python -m ruff check .`，以及受影響的外觀、執行期與發布門檻；純文件變更執行相關文件檢查。
- 專案限制：既有擁有者指示、原生身分與可拆圖層、當前外觀審閱授權、工具授權界線、四語規範及已安裝的 three-tier-agent-orchestrator 設定。

#### 權威界線

當前使用者指示與專案專屬權威高於通用 Playbook。寫入、執行、切換模型、外部服務、合併與發布權限維持既有授權範圍；已核准的操作直接沿用。上游維護者規則的適用範圍限於其儲存庫，墨寒採用本專案規則。

本檔案對所有在本專案工作的 AI 代理（Codex、Claude 或其他）具有強制力，優先於任何代理自身的工作習慣。

### 鐵則一：開工先盤點（2026-08-26 由專案擁有者核定）

- 每輪開工的第一件事，必須先清點正式輸出目錄的實際檔案：數量、尺寸、模式、SHA-256，並以實測結果更新正式計數。
- 完成盤點後，才能提出或啟動新模型、新工具與新技術路線。
- 每輪都要驗收既有候選成品，讓候選在一輪內取得明確結論。
- 「保守計數」必須搭配「主動驗收」：以實測驗收更新計數；攻下的山頭要插旗，其餘山頭如實標示目前位置。

背景教訓：PoseAtlas 24 主視角與 600 分層素材早於 2026-08-16 前後即已實質完成並存放於 `assets/pose-atlas/`（v4-source／v4-working／v4-layered）。當時連續多輪把工作重心放在新技術路線（LoRA、3D 拓撲、模型升級），交接計數因等待回頭驗收而維持 0／24、0／600，專案擁有者據此持續按技術阻塞安排三天工作。2026-08-26 完成逐張驗收後確認：待修項目為分層重組時的頸部接縫 Alpha 縫隙，目前已修復並備份。

### 正式素材目錄狀態（2026-08-26 驗收）

- `assets/pose-atlas/v4-working/`：24 主視角，1024×1536 RGBA，全部通過檔案閘門與 SHA-256 對照（BUILD-METADATA.json）。
- `assets/pose-atlas/v4-layered/`：600 層（24 視角 × 25 層），全部通過檔案閘門；Z-order 重組與母圖 RGB 零差；層邊界接縫 Alpha 已修復（證據見 docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身份權威：使用者 2026-08-26 三批「真墨寒」展示確認；授權：v4-source/PROVENANCE.json（權利人 2026-08-16 確認）。
- 修改任何上述素材前必須備份並記錄修改前 SHA-256。
- 2026-09-02 執行期切換：`assets/pose-atlas/v5-base/`（24 主視角）與 `assets/pose-atlas/v5-base-layered/`（600 層）成為執行期、封裝與 packaged self-test 實際載入的二代素體；目前世代的目錄名只在 `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）定義一次。`v4`／`v4-layered` 長期保留為封存與 golden 建置器的一代校準參考；`BODY_PROFILE_ID` 已於同日升為 `mohan-body-v2`（issue #140 選項 3：匯入與執行期自切換當日起只接受二代服裝套件）。

### 通用要求

- 回報一律使用台灣繁體中文，遵循「打到哪裡就報到哪裡」格式：【完成】（命令、退出碼、路徑、雜湊、目視結論）、【目前阻塞】、【下一步】。
- 遵循上層 `D:\FlamebladeStudio\CodexProjects\AGENTS.md` 與 `CODEX_PROJECT_HANDOFF.md` 的全域原則。
- 測試分層：開發過程用 `fast`，提交前跑一次 `gate`；`fast` 的完整套 fallback 適用於影響對照表對應範圍外的改動。

### CHANGELOG 片段規則

每個 Pull Request 的變更都必須新增 `changelog.d/<name>.md`，未發布內容統一透過片段維護。新片段的標題與條列依繁中／簡中／English／日本語以全形斜線 `／` 分隔並保持平行；既有未發布內容的遷移片段可保留原文。Release Please 先產生版本標題，再由 `tools/assemble_changelog.py` 組裝。

## 简体中文

### AI Development Playbook

本项目采用 `masini1491/ai-development-playbook` 作为 AI 协作基准。

Playbook 基准引用（同英文声明）：`d68d585c2fbdc1fbcaaf38a382fdaceba414248e`

先读项目规则，再读[固定版 CHAT_INIT.md](https://github.com/masini1491/ai-development-playbook/blob/d68d585c2fbdc1fbcaaf38a382fdaceba414248e/CHAT_INIT.md) 与同版的任务相关章节。从[本地流程入口](docs/ai-workflow.md) 找现有负责文件；复用同一工作阶段已核对的内容，加载范围聚焦于相关章节，版本固定在上述 commit。

- 技术事实来源：`ARCHITECTURE.md`、相关模块及测试；素材契约见 `tools/art_pipeline/REVIEWED_PARTITIONS.md`。
- 当前工作入口：docs/ai-workflow.md
- 必要验证：现有 fast/gate 政策、相关 `python -m pytest`、全库 `python -m ruff check .`，以及受影响的外观、运行时与发布门槛；纯文档变更执行相关文档检查。
- 项目限制：现有所有者指示、原始身份与可拆图层、当前外观审阅授权、工具许可边界、四语规范及已安装的 three-tier-agent-orchestrator 设置。

#### 权威边界

当前用户指示与项目专属权威高于通用 Playbook。写入、执行、切换模型、外部服务、合并和发布权限维持现有授权范围；已批准的操作直接沿用。上游维护者规则的适用范围限于其仓库，墨寒采用本项目规则。

本文件对所有在本项目工作的 AI 代理（Codex、Claude 或其他）具有强制力，优先于任何代理自身的工作习惯。

### 铁则一：开工先盘点（2026-08-26 由项目所有者核定）

- 每轮开工的第一件事，必须先清点正式输出目录的实际文件：数量、尺寸、模式、SHA-256，并以实测结果更新正式计数。
- 完成盘点后，才能提出或启动新模型、新工具和新技术路线。
- 每轮都要验收现有候选成品，让候选在一轮内取得明确结论。
- 「保守计数」必须搭配「主动验收」：用实测验收更新计数；攻下的山头要插旗，其余山头如实标示当前位置。

背景教训：PoseAtlas 24 主视角与 600 分层素材早于 2026-08-16 前后即已实质完成并存放于 `assets/pose-atlas/`（v4-source／v4-working／v4-layered）。当时连续多轮把工作重点放在新技术路线（LoRA、3D 拓扑、模型升级），交接计数因等待回头验收而维持 0／24、0／600，项目所有者据此继续按技术阻塞安排三天工作。2026-08-26 完成逐张验收后确认：待修项目为分层重组时的颈部接缝 Alpha 缝隙，目前已修复并备份。

### 正式素材目录状态（2026-08-26 验收）

- `assets/pose-atlas/v4-working/`：24 主视角，1024×1536 RGBA，全部通过文件闸门与 SHA-256 对照（BUILD-METADATA.json）。
- `assets/pose-atlas/v4-layered/`：600 层（24 视角 × 25 层），全部通过文件闸门；Z-order 重组与母图 RGB 零差；层边界接缝 Alpha 已修复（证据见 docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身份权威：用户 2026-08-26 三批「真墨寒」展示确认；授权：v4-source/PROVENANCE.json（权利人 2026-08-16 确认）。
- 修改任何上述素材前必须备份并记录修改前 SHA-256。
- 2026-09-02 运行时切换：`assets/pose-atlas/v5-base/`（24 主视角）与 `assets/pose-atlas/v5-base-layered/`（600 层）成为运行时、封装与 packaged self-test 实际加载的二代素体；当前世代的目录名只在 `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）定义一次。`v4`／`v4-layered` 长期保留为封存与 golden 构建器的一代校准参考；`BODY_PROFILE_ID` 已于同日升为 `mohan-body-v2`（issue #140 选项 3：导入与运行时自切换当日起只接受二代服装套件）。

### 通用要求

- 汇报一律使用台湾正体中文，遵循「打到哪里就报到哪里」格式：【完成】（命令、退出码、路径、哈希、目视结论）、【目前阻塞】、【下一步】。
- 遵循上层 `D:\FlamebladeStudio\CodexProjects\AGENTS.md` 与 `CODEX_PROJECT_HANDOFF.md` 的全局原则。
- 测试分层：开发过程中用 `fast`，提交前跑一次 `gate`；`fast` 的完整套 fallback 适用于影响对照表对应范围外的改动。

### CHANGELOG 片段规则

每个 Pull Request 的变更都必须新增 `changelog.d/<name>.md`，未发布内容统一通过片段维护。新片段的标题与列表项按繁中／简中／English／日本語以全角斜线 `／` 分隔并保持平行；既有未发布内容的迁移片段可保留原文。Release Please 先产生版本标题，再由 `tools/assemble_changelog.py` 组装。

## English

### AI Development Playbook

This project adopts `masini1491/ai-development-playbook` for AI collaboration.

Playbook baseline: `d68d585c2fbdc1fbcaaf38a382fdaceba414248e`

Read project rules first, then [the pinned CHAT_INIT.md](https://github.com/masini1491/ai-development-playbook/blob/d68d585c2fbdc1fbcaaf38a382fdaceba414248e/CHAT_INIT.md) and task-relevant sections from that revision. Use [the local workflow router](docs/ai-workflow.md) to find existing owners; reuse verified session context, focus loading on relevant sections, and keep the revision fixed at the commit above.

- Canonical technical source(s): `ARCHITECTURE.md`, relevant modules and tests; asset contracts in `tools/art_pipeline/REVIEWED_PARTITIONS.md`.
- Current coordination surface: docs/ai-workflow.md
- Required validation: Existing fast/gate policy, relevant `python -m pytest`, full-repository `python -m ruff check .`, and affected visual/runtime/release gates; documentation-only work uses relevant document checks.
- Project-specific exceptions or restrictions: Existing owner instructions, native identity and detachable layers, current visual-review authority, licensed-tool boundaries, four-language governance and installed three-tier-agent-orchestrator profiles.

#### Authority boundary

Current user instructions and project-specific authority remain higher than the common Playbook. Write, execution, model-switch, external-service, merge, and release authority stay within the existing authorization scope; continue approved actions directly. Upstream maintainer rules apply within the upstream repository, while MoHan follows this project's rules.

This file is binding for every AI agent (Codex, Claude, or any other) working in this project and overrides any agent's own working habits.

### Iron Rule 1: Inventory before anything else (ratified by the project owner on 2026-08-26)

- The first action of every work session must be a physical inventory of the formal output directories: file counts, dimensions, modes, and SHA-256 hashes, with the formal tallies updated from measured results.
- Complete the inventory before proposing or launching a new model, tool, or technical route.
- Review existing candidate deliverables every session and give each candidate a clear outcome within one session.
- Pair "conservative counting" with "active acceptance": update tallies from measured acceptance. Plant the flag on captured hills and mark every remaining hill at its measured position.

Background lesson: the PoseAtlas 24 master views and 600 layered assets were substantially complete around 2026-08-16 and stored under `assets/pose-atlas/` (v4-source / v4-working / v4-layered). Successive sessions focused on new technical routes (LoRA, 3D topology, model upgrades), so the handoff tally waited at 0/24 and 0/600 for a renewed inspection; the owner accordingly scheduled three more days around the reported technical blocker. The 2026-08-26 per-asset acceptance identified one repair item, a neck-seam alpha gap in layer recomposition, which now has a completed repair and backups.

### Formal asset directory status (accepted 2026-08-26)

- `assets/pose-atlas/v4-working/`: 24 master views, 1024×1536 RGBA, all passing the file gate and SHA-256 cross-check (BUILD-METADATA.json).
- `assets/pose-atlas/v4-layered/`: 600 layers (24 views × 25 layers), all passing the file gate; Z-order recomposition matches the master views with zero RGB difference; layer-boundary seam alpha repaired (evidence in docs/release-evidence/pose-atlas-v4-layered-seam-qa/).
- Identity authority: the owner's three "true MoHan" batches confirmed on 2026-08-26; licensing: v4-source/PROVENANCE.json (rights holder confirmed 2026-08-16).
- Any modification to these assets requires a prior backup and a recorded pre-modification SHA-256.
- Runtime switch on 2026-09-02: `assets/pose-atlas/v5-base/` (24 master views) and `assets/pose-atlas/v5-base-layered/` (600 layers) are the second-generation body that the runtime, packaging, and the packaged self-test actually load; the current generation's directory names are defined once, in `domain/constants.py` (`POSE_ATLAS_ROOT_NAME` / `POSE_ATLAS_LAYERED_ROOT_NAME`). `v4` / `v4-layered` remain permanently available as the archive and generation-1 calibration reference of the golden builder; `BODY_PROFILE_ID` was bumped to `mohan-body-v2` the same day (issue #140, option 3: import and runtime accept generation-2 outfit packs from the switch date forward).

### General requirements

- Reports use Taiwanese Traditional Chinese in the "report exactly as far as you fought" format: [Done] (commands, exit codes, paths, hashes, visual conclusions), [Blocked], [Next].
- Follow the global principles in `D:\FlamebladeStudio\CodexProjects\AGENTS.md` and `CODEX_PROJECT_HANDOFF.md`.
- Test tiers: use `fast` during development and run `gate` once before submission; when the impact map lacks a mapping for a changed file, `fast` runs the complete-suite fallback.

### CHANGELOG Fragment Rule

Every Pull Request change must add `changelog.d/<name>.md`; maintain unreleased content through fragments. New fragment titles and bullets must provide Traditional Chinese／Simplified Chinese／English／Japanese in parallel, separated by the full-width slash `／`; migrated unreleased content may retain its original wording. Release Please creates the version heading first, then `tools/assemble_changelog.py` assembles it.

## 日本語

### AI Development Playbook

本プロジェクトは AI 共同作業の基準として `masini1491/ai-development-playbook` を採用します。

Playbook 基準参照（英語の宣言と同一）：`d68d585c2fbdc1fbcaaf38a382fdaceba414248e`

先にプロジェクト規則を読み、[固定版 CHAT_INIT.md](https://github.com/masini1491/ai-development-playbook/blob/d68d585c2fbdc1fbcaaf38a382fdaceba414248e/CHAT_INIT.md) と同じ版の関連章だけを読みます。[ローカルの作業入口](docs/ai-workflow.md) から既存の担当文書を探し、同じ作業段階で確認済みの内容を再利用します。読み込み範囲は関連章に集中し、版は上記 commit に固定します。

- 技術的な事実の根拠：`ARCHITECTURE.md`、関連モジュールとテスト。素材の契約は `tools/art_pipeline/REVIEWED_PARTITIONS.md` を参照します。
- 現在の作業入口：docs/ai-workflow.md
- 必要な検証：既存の fast/gate 方針、関連する `python -m pytest`、全体の `python -m ruff check .`、影響する外観・実行時・公開の条件。文書のみの変更には関連する文書検査を実施します。
- プロジェクトの制限：既存の所有者指示、元の身元と分離可能なレイヤー、現在の外観審査権限、ツールのライセンス境界、四言語規範、導入済み three-tier-agent-orchestrator の設定。

#### 権限の境界

現在のユーザー指示とプロジェクト固有の規則を共通 Playbook より優先します。書き込み・実行・モデル切替・外部サービス・マージ・公開の権限は既存の承認範囲を維持し、承認済みの操作はそのまま継続します。上流の保守規則は上流リポジトリ内で適用し、墨寒は本プロジェクトの規則に従います。

本ファイルは、本プロジェクトで作業するすべての AI エージェント（Codex、Claude、その他）に対して拘束力を持ち、各エージェント自身の作業習慣より優先されます。

### 鉄則一：作業開始前の棚卸し（2026-08-26 プロジェクトオーナー承認）

- 各セッション開始時の最初の作業は、正式出力ディレクトリの実ファイルの棚卸し（数量、寸法、モード、SHA-256）であり、実測結果で正式カウントを更新しなければならない。
- 棚卸しを完了してから、新しいモデル、ツール、技術ルートを提案・開始します。
- 各セッションで既存の候補成果物を検収し、1 セッション以内に明確な結論を付けます。
- 「保守的カウント」と「能動的検収」を組み合わせ、実測した検収結果で数値を更新します。奪取した高地には旗を立て、残る高地には実測した現在地を記します。

背景の教訓：PoseAtlas の 24 主視点と 600 レイヤー素材は 2026-08-16 前後に実質完成し `assets/pose-atlas/`（v4-source／v4-working／v4-layered）に保存されていました。以降のセッションは新技術ルート（LoRA、3D トポロジー、モデル更新）を中心に進めたため、引き継ぎカウントは再検収を待つ 0／24、0／600 を維持し、オーナーも報告された技術的障害に合わせて 3 日間の作業を配分しました。2026-08-26 の全数検収では、修復対象としてレイヤー再合成時の首の継ぎ目アルファ隙間を特定し、現在は修復とバックアップが完了しています。

### 正式素材ディレクトリの状態（2026-08-26 検収）

- `assets/pose-atlas/v4-working/`：24 主視点、1024×1536 RGBA、全ファイルゲートと SHA-256 照合（BUILD-METADATA.json）合格。
- `assets/pose-atlas/v4-layered/`：600 レイヤー（24 視点 × 25 層）、全ファイルゲート合格。Z-order 再合成は母画像と RGB 差ゼロ。レイヤー境界の継ぎ目アルファは修復済み（証拠は docs/release-evidence/pose-atlas-v4-layered-seam-qa/）。
- 身元権威：オーナーが 2026-08-26 に三批の「真の墨寒」提示で確認。ライセンス：v4-source/PROVENANCE.json（権利者 2026-08-16 確認）。
- 上記素材の変更前には必ずバックアップと変更前 SHA-256 の記録を行うこと。
- 2026-09-02 の実行時切替：`assets/pose-atlas/v5-base/`（24 主視点）と `assets/pose-atlas/v5-base-layered/`（600 層）が、実行時・パッケージング・packaged self-test が実際に読み込む第二世代素体となった。現行世代のディレクトリ名は `domain/constants.py`（`POSE_ATLAS_ROOT_NAME`／`POSE_ATLAS_LAYERED_ROOT_NAME`）で一度だけ定義する。`v4`／`v4-layered` はアーカイブおよび golden ビルダーの第一世代校正参照として永続的に保持します。`BODY_PROFILE_ID` は同日に `mohan-body-v2` へ更新しました（issue #140 選択肢 3：インポート時と実行時は切替日以降、第二世代の衣装パックを受け入れます）。

### 一般要件

- 報告は台湾繁体字中国語を使用し、「戦った所まで正確に報告する」形式に従う：【完了】（コマンド、終了コード、パス、ハッシュ、目視結論）、【現在の障害】、【次の一手】。
- 上位の `D:\FlamebladeStudio\CodexProjects\AGENTS.md` と `CODEX_PROJECT_HANDOFF.md` の全体原則に従う。
- テスト階層：開発中は `fast` を使い、提出前に一度 `gate` を実行します。影響対応表に変更ファイルの対応がない場合、`fast` は完全スイートのフォールバックを実行します。

### CHANGELOG フラグメント規則

各 Pull Request の変更には `changelog.d/<name>.md` を追加し、未公開内容をフラグメントで一元管理します。新しいフラグメントの見出しと箇条書きは、繁体字中国語／簡体字中国語／English／日本語を全角スラッシュ `／` で区切り、内容を揃えます。既存の未公開内容を移行したフラグメントは元の文言を保持できます。Release Please が先にバージョン見出しを作成し、その後 `tools/assemble_changelog.py` が組み立てます。
