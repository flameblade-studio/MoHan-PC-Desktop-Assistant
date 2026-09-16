# 專案交接文件／项目交接文件／Project Handoff／プロジェクト引き継ぎ文書

## 繁體中文

本文件記錄 MoHan-PC-Desktop-Assistant 專案的發行交接資訊，供後續維護者與協作者參考。

### 最新發行狀態

- 版本：v4.2.1
- 發行狀態：已完成發行
- 標籤：`v4.2.1`
- 來源分支：`release/v4.2.1`（合併後已刪除）
- 目標分支：`main`

### 本次修復的問題（v4.2.1）

- 疊影：全身模式（v4 full-body）的嘴型與表情動態是未完成 stub，`resolve_speech` 只回傳 `None`，導致說話時全身渲染被 bypass、嘴型靜止；legacy 表情路徑會重置 `_adaptive_full_body_active` 造成疊影。
- 嘴型同步：實作 `resolve_speech` 從 `.hands.json` 的 `protected_regions.face` 讀取臉部座標，產生程序化嘴型圖層，並讓 `update_speech_layers` 在嘴型閉合時回到靜態照片。
- 揮手回應：`set_state` 在全身模式下跳過 legacy 表情切換，保留肢體動畫，讓揮手/走動仍有可見的肢體回應。

### 發行流程記錄

- 完整回歸測試 280/280 全綠。
- squash 合併 PR，建立標籤 `v4.2.1` 並推送，觸發 release.yml。
- 產出正式 Release（draft=false、prerelease=false）。

### 後續維護注意事項

- 發行來源（分支、合併後 main、版本、標籤、GitHub Release）必須指向同一不可變提交。
- 遵循 PUBLISHING.md 的 squash-only 與四語治理規範。
- 遵循 .clinerules.md 的排除清單與 Token 節省規範。

## 简体中文

本文件记录 MoHan-PC-Desktop-Assistant 项目的发行交接信息，供后续维护者与协作者参考。

### 最新发行状态

- 版本：v4.2.1
- 发行状态：已完成发行
- 标签：`v4.2.1`
- 来源分支：`release/v4.2.1`（合并后已删除）
- 目标分支：`main`

### 本次修复的问题（v4.2.1）

- 叠影：全身模式（v4 full-body）的嘴型与表情动态是未完成 stub，`resolve_speech` 只返回 `None`，导致说话时全身渲染被 bypass、嘴型静止；legacy 表情路径会重置 `_adaptive_full_body_active` 造成叠影。
- 嘴型同步：实现 `resolve_speech` 从 `.hands.json` 的 `protected_regions.face` 读取脸部坐标，产生程序化嘴型图层，并让 `update_speech_layers` 在嘴型闭合时回到静态照片。
- 挥手回应：`set_state` 在全身模式下跳过 legacy 表情切换，保留肢体动画，让挥手/走动仍有可见的肢体回应。

### 发行流程记录

- 完整回归测试 280/280 全绿。
- squash 合并 PR，建立标签 `v4.2.1` 并推送，触发 release.yml。
- 产出正式 Release（draft=false、prerelease=false）。

### 后续维护注意事项

- 发行来源（分支、合并后 main、版本、标签、GitHub Release）必须指向同一不可变提交。
- 遵循 PUBLISHING.md 的 squash-only 与四语治理规范。
- 遵循 .clinerules.md 的排除清单与 Token 节省规范。

## English

This document records the release handoff information for the MoHan-PC-Desktop-Assistant project, for future maintainers and collaborators.

### Latest release status

- Version: v4.2.1
- Release status: released
- Tag: `v4.2.1`
- Source branch: `release/v4.2.1` (deleted after merge)
- Target branch: `main`

### Issues fixed in this release (v4.2.1)

- Double image: the full-body mode (v4 full-body) mouth and expression dynamics were an unfinished stub; `resolve_speech` only returned `None`, so speech bypassed the full-body render and the mouth stayed still, while the legacy expression path reset `_adaptive_full_body_active` and caused the double image.
- Lip sync: implemented `resolve_speech` to read the face region from `.hands.json` `protected_regions.face`, produce a procedural mouth layer, and make `update_speech_layers` restore the static photograph when the mouth closes.
- Wave response: `set_state` now skips the legacy expression switch in full-body mode while keeping the gesture animation, so a wave or arrival still gets a visible body response.

### Release process record

- Full regression suite 280/280 green.
- Squash-merged the PR, created the `v4.2.1` tag, pushed it, and triggered release.yml.
- Produced a formal Release (draft=false, prerelease=false).

### Maintenance notes

- The release source (branch, merged main, version, tag, GitHub Release) must point to the same immutable commit.
- Follow PUBLISHING.md squash-only and four-language governance.
- Follow .clinerules.md exclusion list and token-saving rules.

## 日本語

本ファイルは MoHan-PC-Desktop-Assistant プロジェクトのリリース引き継ぎ情報を記録し、後続の保守者と協力者の参考に供します。

### 最新リリース状況

- バージョン：v4.2.1
- リリース状況：リリース済み
- タグ：`v4.2.1`
- ソースブランチ：`release/v4.2.1`（マージ後に削除）
- ターゲットブランチ：`main`

### 本リリースで修正した問題（v4.2.1）

- 二重像：全身モード（v4 full-body）の口元と表情の動的処理は未完成のスタブで、`resolve_speech` は `None` のみを返すため、発話時に全身レンダリングがバイパスされて口元が静止し、レガシー表情経路が `_adaptive_full_body_active` をリセットして二重像を引き起こしました。
- リップシンク：`resolve_speech` を実装し、`.hands.json` の `protected_regions.face` から顔領域を読み取り、手続き的な口元レイヤーを生成し、口を閉じた際に `update_speech_layers` が静的写真へ戻すようにしました。
- 手振り応答：`set_state` は全身モードでレガシー表情切り替えをスキップしつつジェスチャーアニメーションを維持し、手振りや来訪に可視の身体応答を残します。

### リリース工程の記録

- 完全回帰テスト 280/280 全緑。
- PR を squash マージし、タグ `v4.2.1` を作成してプッシュし、release.yml を起動しました。
- 正式な Release（draft=false、prerelease=false）を生成しました。

### 保守上の注意

- リリース元（ブランチ、マージ後の main、バージョン、タグ、GitHub Release）は同一の不変コミットを指す必要があります。
- PUBLISHING.md の squash-only と四言語ガバナンスに従います。
- .clinerules.md の除外リストとトークン節約ルールに従います。
