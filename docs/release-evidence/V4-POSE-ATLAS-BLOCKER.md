# v4.0.0 PoseAtlas 正式資產阻擋／v4.0.0 PoseAtlas 正式资产阻挡／v4.0.0 PoseAtlas Release-Asset Blocker／v4.0.0 PoseAtlas 正式素材の阻害事項

## 繁體中文

### 結論

v4.0.0 的 PoseAtlas 發布門檻目前必須維持阻擋。`assets/pose-atlas/v4/` 不存在，repo 內也沒有具明確來源與再散布權、可重現產生墨寒 24 個完整全身旋轉視角的原始視覺資產。現有表情圖、半身圖示、入門圖片與文件截圖無法推導不可見的背面、四肢、足底與雙手；不得用補畫、鏡射、幾何假人、測試 fixture 或不明授權素材冒充正式資產。

### 2026-08-14 開發進度（不是正式發布證據）

`assets/pose-atlas/v4-source/` 現已保存 24 張候選透明 PNG，涵蓋 `yaw-180` 至 `yaw+165` 的 15 度間隔視角。離線檔案檢查已確認每張圖片為 1024×1536、RGBA、具有非空 alpha 邊界、主體未貼齊畫布邊緣，且 24 張均通過這項機械檢查。這只代表候選檔案的基本完整性；來源／再散布權、人物身分連續性、服裝與配件轉面邏輯、身體 landmarks、雙手 21 點、相鄰視角連續性與正式稽核證據仍未完成。候選檔案必須與正式 `assets/pose-atlas/v4/` 分離保存，不得據此解除發布阻擋。

### 精確缺件

下列 24 個 canonical view ID 全部缺少；每個 ID 必須各有一份原生 RGBA PNG、全身 landmark sidecar 與雙手 sidecar，共缺 72 個視角檔：

`yaw-180-pitch+00`、`yaw-165-pitch+00`、`yaw-150-pitch+00`、`yaw-135-pitch+00`、`yaw-120-pitch+00`、`yaw-105-pitch+00`、`yaw-090-pitch+00`、`yaw-075-pitch+00`、`yaw-060-pitch+00`、`yaw-045-pitch+00`、`yaw-030-pitch+00`、`yaw-015-pitch+00`、`yaw+000-pitch+00`、`yaw+015-pitch+00`、`yaw+030-pitch+00`、`yaw+045-pitch+00`、`yaw+060-pitch+00`、`yaw+075-pitch+00`、`yaw+090-pitch+00`、`yaw+105-pitch+00`、`yaw+120-pitch+00`、`yaw+135-pitch+00`、`yaw+150-pitch+00`、`yaw+165-pitch+00`。

每個 view 的三個檔名固定為 `<view-id>.png`、`<view-id>.landmarks.json`、`<view-id>.hands.json`。另外缺少 `assets/pose-atlas/v4/release-audits.json`，因此現在的正式 gate 先回報 `audit_evidence_invalid`。即使新增空白或自行宣告通過的 JSON，後續 72 個實體檔、雜湊、畫布、透明邊界、完整四肢／足底、雙手 21 點、身高／基線一致性、身分一致性、相鄰視角與載入證據仍會 fail closed。

### 來源與證據要求

原始素材必須是炎劍文化工作室擁有再散布權的原創墨寒完整全身 360° 素材，或具有可驗證授權、允許修改與再散布的來源；必須保留作者、授權、取得位置、不可變來源 revision 及原始檔 SHA-256。所有 24 視角必須是同一人物、同一核心服裝／身體設定與一致畫布，不得由目前三姿態半身資產推測不可見內容。`release-audits.json` 必須記錄真實的 source、identity、body profile、rig、load、identity audit 與 pose-atlas audit 結果；任何 `passed: true` 都必須有可重現的機器證據，不得人工虛構。

### 可執行解除步驟

1. 取得或製作具完整權利證明的墨寒全身 24 視角原始素材，固定來源 revision 並計算原始 SHA-256。
2. 將每一視角輸出為具有真透明背景與安全邊界的原生 RGBA PNG，檔名使用上述 canonical ID。
3. 依真實像素標註 crown、雙側 hip／knee／ankle／heel／toe／sole，建立 `.landmarks.json`；依真實雙手建立每手 21 點與保護區域的 `.hands.json`。不可由不存在的手或腿造資料。
4. 使用既有正式工具建立 manifest／接觸表與稽核證據；`tools/compose_body_profile_candidate.py` 只能在已有同畫布 base／donor 時替換核准軀幹，`tools/build_pose_contact_sheet.py` 只能整理並稽核既有視角，兩者都不是 360° 圖像生成器。
5. 執行完整身體、身分、PoseAtlas、雙手與實際載入稽核，將可重現結果及來源 revision SHA-256 寫入 `release-audits.json`。
6. 執行 `python tools/check_pose_atlas_release.py --version 4.0.0 --asset-root assets/pose-atlas/v4 --audit-evidence assets/pose-atlas/v4/release-audits.json`；只有輸出 `status: releasable` 才解除本阻擋。

## 简体中文

### 结论

v4.0.0 的 PoseAtlas 发布门槛目前必须保持阻挡。`assets/pose-atlas/v4/` 不存在，repo 内也没有来源与再分发权明确、可重现生成墨寒 24 个完整全身旋转视角的原始视觉资产。现有表情图、半身图标、入门图片与文档截图无法推导不可见的背面、四肢、脚底与双手；不得使用补画、镜像、几何假人、测试 fixture 或许可不明的素材冒充正式资产。

### 2026-08-14 开发进度（不是正式发布证据）

`assets/pose-atlas/v4-source/` 现已保存 24 张候选透明 PNG，覆盖 `yaw-180` 至 `yaw+165` 的 15 度间隔视角。离线文件检查已确认每张图片为 1024×1536、RGBA、具有非空 alpha 边界、主体未贴齐画布边缘，并且 24 张全部通过这项机械检查。这只代表候选文件的基本完整性；来源／再分发权、人物身份连续性、服装与配件转面逻辑、身体 landmarks、双手 21 点、相邻视角连续性与正式审计证据仍未完成。候选文件必须与正式 `assets/pose-atlas/v4/` 分开保存，不得据此解除发布阻挡。

### 精确缺件

以下 24 个 canonical view ID 全部缺失；每个 ID 必须分别具有一份原生 RGBA PNG、全身 landmark sidecar 与双手 sidecar，共缺少 72 个视角文件：

`yaw-180-pitch+00`、`yaw-165-pitch+00`、`yaw-150-pitch+00`、`yaw-135-pitch+00`、`yaw-120-pitch+00`、`yaw-105-pitch+00`、`yaw-090-pitch+00`、`yaw-075-pitch+00`、`yaw-060-pitch+00`、`yaw-045-pitch+00`、`yaw-030-pitch+00`、`yaw-015-pitch+00`、`yaw+000-pitch+00`、`yaw+015-pitch+00`、`yaw+030-pitch+00`、`yaw+045-pitch+00`、`yaw+060-pitch+00`、`yaw+075-pitch+00`、`yaw+090-pitch+00`、`yaw+105-pitch+00`、`yaw+120-pitch+00`、`yaw+135-pitch+00`、`yaw+150-pitch+00`、`yaw+165-pitch+00`。

每个 view 的三个文件名固定为 `<view-id>.png`、`<view-id>.landmarks.json`、`<view-id>.hands.json`。另外缺少 `assets/pose-atlas/v4/release-audits.json`，因此当前正式 gate 首先报告 `audit_evidence_invalid`。即使添加空白或自行声明通过的 JSON，后续 72 个实体文件、哈希、画布、透明边界、完整四肢／脚底、双手 21 点、身高／基线一致性、身份一致性、相邻视角与加载证据仍会 fail closed。

### 来源与证据要求

原始素材必须是炎剑文化工作室拥有再分发权的原创墨寒完整全身 360° 素材，或具有可验证许可、允许修改与再分发的来源；必须保留作者、许可、获取位置、不可变来源 revision 及原始文件 SHA-256。全部 24 个视角必须是同一人物、同一核心服装／身体设置与一致画布，不得从当前三个姿态的半身资产推测不可见内容。`release-audits.json` 必须记录真实的 source、identity、body profile、rig、load、identity audit 与 pose-atlas audit 结果；任何 `passed: true` 都必须具有可重现的机器证据，不得人工虚构。

### 可执行解除步骤

1. 获取或制作具有完整权利证明的墨寒全身 24 视角原始素材，固定来源 revision 并计算原始 SHA-256。
2. 将每个视角输出为具有真实透明背景与安全边界的原生 RGBA PNG，文件名使用上述 canonical ID。
3. 根据真实像素标注 crown、两侧 hip／knee／ankle／heel／toe／sole，建立 `.landmarks.json`；根据真实双手建立每只手 21 点与保护区域的 `.hands.json`。不得为不存在的手或腿伪造数据。
4. 使用现有正式工具建立 manifest／接触表与审计证据；`tools/compose_body_profile_candidate.py` 只能在已有相同画布 base／donor 时替换获准躯干，`tools/build_pose_contact_sheet.py` 只能整理并审计现有视角，两者都不是 360° 图像生成器。
5. 执行完整身体、身份、PoseAtlas、双手与实际加载审计，将可重现结果及来源 revision SHA-256 写入 `release-audits.json`。
6. 执行 `python tools/check_pose_atlas_release.py --version 4.0.0 --asset-root assets/pose-atlas/v4 --audit-evidence assets/pose-atlas/v4/release-audits.json`；只有输出 `status: releasable` 才能解除本阻挡。

## English

### Conclusion

The v4.0.0 PoseAtlas release gate must remain blocked. `assets/pose-atlas/v4/` does not exist, and the repository contains no source visual set with clear provenance and redistribution rights from which MoHan's 24 complete full-body rotational views can be reproduced. Existing expression images, half-body icons, onboarding art, and documentation screenshots cannot recover unseen rear anatomy, limbs, soles, or hands. Inpainting, mirroring, geometric stand-ins, test fixtures, or material with unknown licensing must not impersonate release assets.

### Development evidence on 2026-08-14 (not release evidence)

`assets/pose-atlas/v4-source/` now contains 24 transparent PNG candidates covering 15-degree views from `yaw-180` through `yaw+165`. An offline file check confirmed that every image is 1024×1536 RGBA, has a non-empty alpha boundary, and keeps the subject away from the canvas edge; all 24 passed that mechanical check. This proves only basic candidate-file integrity. Provenance and redistribution rights, identity continuity, clothing and accessory turn consistency, body landmarks, 21-point hand evidence, adjacent-view continuity, and genuine release-audit evidence remain incomplete. Candidate files must remain separate from formal `assets/pose-atlas/v4/` and must not remove this release blocker.

### Exact missing files

All 24 canonical view IDs below are missing. Each ID requires one native RGBA PNG, one full-body landmark sidecar, and one two-hand sidecar, for 72 missing view files:

`yaw-180-pitch+00`, `yaw-165-pitch+00`, `yaw-150-pitch+00`, `yaw-135-pitch+00`, `yaw-120-pitch+00`, `yaw-105-pitch+00`, `yaw-090-pitch+00`, `yaw-075-pitch+00`, `yaw-060-pitch+00`, `yaw-045-pitch+00`, `yaw-030-pitch+00`, `yaw-015-pitch+00`, `yaw+000-pitch+00`, `yaw+015-pitch+00`, `yaw+030-pitch+00`, `yaw+045-pitch+00`, `yaw+060-pitch+00`, `yaw+075-pitch+00`, `yaw+090-pitch+00`, `yaw+105-pitch+00`, `yaw+120-pitch+00`, `yaw+135-pitch+00`, `yaw+150-pitch+00`, and `yaw+165-pitch+00`.

The three filenames for each view are fixed as `<view-id>.png`, `<view-id>.landmarks.json`, and `<view-id>.hands.json`. `assets/pose-atlas/v4/release-audits.json` is also missing, so the current production gate first reports `audit_evidence_invalid`. Adding an empty or self-certified JSON would not help: the 72 physical files, hashes, canvas, transparent bounds, complete limbs and soles, two 21-point hands, height and baseline consistency, identity continuity, adjacent views, and load evidence would still fail closed.

### Source and evidence requirements

The source must be original complete full-body 360° MoHan material for which Flameblade Studio owns redistribution rights, or a verifiably licensed source that permits modification and redistribution. Author, license, acquisition location, immutable source revision, and original SHA-256 must be retained. All 24 views must depict the same identity, core outfit and body setup on one consistent canvas. Unseen content must not be inferred from the current three-pose half-body assets. `release-audits.json` must record real source, identity, body-profile, rig, load, identity-audit, and pose-atlas-audit results. Every `passed: true` requires reproducible machine evidence and must not be invented manually.

### Executable unblocking steps

1. Obtain or author 24 full-body MoHan source views with complete rights evidence, pin the source revision, and calculate the original SHA-256 values.
2. Export every view as a native RGBA PNG with real transparency and safe margins, using the canonical IDs above as filenames.
3. Mark crown and left/right hip, knee, ankle, heel, toe, and sole from real pixels in `.landmarks.json`; create `.hands.json` from two real 21-point hands and protected regions. Never invent a hand or limb that is absent from the image.
4. Use the existing production tools to build the manifest, contact sheet, and audit evidence. `tools/compose_body_profile_candidate.py` only replaces an approved torso when same-canvas base and donor images already exist. `tools/build_pose_contact_sheet.py` only arranges and audits existing views. Neither generates 360° imagery.
5. Run full-body, identity, PoseAtlas, hand, and real-load audits, then record reproducible results and the source-revision SHA-256 in `release-audits.json`.
6. Run `python tools/check_pose_atlas_release.py --version 4.0.0 --asset-root assets/pose-atlas/v4 --audit-evidence assets/pose-atlas/v4/release-audits.json`. This blocker may be removed only when the output is `status: releasable`.

## 日本語

### 結論

v4.0.0 の PoseAtlas 公開ゲートは、現時点で阻害状態を維持しなければなりません。`assets/pose-atlas/v4/` は存在せず、墨寒の完全な全身回転 24 視角を再現できる、出典と再配布権が明確な元視覚素材もリポジトリ内にありません。既存の表情画像、半身アイコン、導入画像、文書スクリーンショットから、見えていない背面、四肢、足裏、両手を復元することはできません。補完描画、鏡像、幾何学的な代用品、テスト fixture、不明なライセンス素材を正式素材として扱ってはなりません。

### 2026-08-14 の開発進捗（公開証拠ではありません）

`assets/pose-atlas/v4-source/` に、`yaw-180` から `yaw+165` まで 15 度間隔の 24 視角候補透明 PNG を保存しました。オフラインのファイル検査では、全画像が 1024×1536、RGBA、空でない alpha 境界を持ち、主体が canvas の端に接していないことを確認し、24 枚すべてがこの機械検査に合格しました。これは候補ファイルの基本完全性だけを示します。出典／再配布権、人物同一性、衣装と装飾品の回転整合性、body landmarks、両手 21 点、隣接視角の連続性、正式監査証拠は未完了です。候補ファイルは正式な `assets/pose-atlas/v4/` と分離し、これを根拠に公開阻害を解除してはいけません。

### 正確な不足ファイル

次の canonical view ID は 24 個すべて不足しています。各 ID に native RGBA PNG、全身 landmark sidecar、両手 sidecar が一つずつ必要であり、合計 72 個の視角ファイルが不足しています。

`yaw-180-pitch+00`、`yaw-165-pitch+00`、`yaw-150-pitch+00`、`yaw-135-pitch+00`、`yaw-120-pitch+00`、`yaw-105-pitch+00`、`yaw-090-pitch+00`、`yaw-075-pitch+00`、`yaw-060-pitch+00`、`yaw-045-pitch+00`、`yaw-030-pitch+00`、`yaw-015-pitch+00`、`yaw+000-pitch+00`、`yaw+015-pitch+00`、`yaw+030-pitch+00`、`yaw+045-pitch+00`、`yaw+060-pitch+00`、`yaw+075-pitch+00`、`yaw+090-pitch+00`、`yaw+105-pitch+00`、`yaw+120-pitch+00`、`yaw+135-pitch+00`、`yaw+150-pitch+00`、`yaw+165-pitch+00`。

各 view の三つのファイル名は `<view-id>.png`、`<view-id>.landmarks.json`、`<view-id>.hands.json` に固定されます。`assets/pose-atlas/v4/release-audits.json` も不足しているため、現在の正式 gate は最初に `audit_evidence_invalid` を報告します。空の JSON や自己申告の合格 JSON を追加しても、72 個の実体ファイル、hash、canvas、透明境界、完全な四肢／足裏、両手 21 点、身長／基準線の一貫性、同一人物性、隣接視角、load evidence は引き続き fail closed になります。

### 出典と証拠の要件

元素材は、炎剣文化スタジオが再配布権を持つ墨寒のオリジナル完全全身 360° 素材、または改変と再配布を許可する検証可能なライセンス素材でなければなりません。作者、ライセンス、取得場所、不変の source revision、元ファイルの SHA-256 を保持する必要があります。24 視角すべてが同一人物、同一の中核衣装／身体設定、一貫した canvas でなければならず、現在の三姿勢の半身素材から不可視部分を推測してはいけません。`release-audits.json` には実際の source、identity、body profile、rig、load、identity audit、pose-atlas audit の結果を記録します。すべての `passed: true` は再現可能な機械証拠を必要とし、手作業で捏造してはなりません。

### 実行可能な解除手順

1. 完全な権利証明を備えた墨寒の全身 24 視角元素材を取得または制作し、source revision を固定して元 SHA-256 を計算します。
2. 各視角を真の透明背景と安全余白を持つ native RGBA PNG として出力し、上記 canonical ID をファイル名に使用します。
3. 実際の pixel に基づいて crown、左右の hip／knee／ankle／heel／toe／sole を `.landmarks.json` に記録し、実在する両手の各 21 点と保護領域を `.hands.json` に記録します。画像に存在しない手や脚のデータを作ってはいけません。
4. 既存の正式ツールで manifest、contact sheet、監査証拠を作成します。`tools/compose_body_profile_candidate.py` は同一 canvas の base／donor が既にある場合だけ承認済み torso を置換します。`tools/build_pose_contact_sheet.py` は既存視角の整理と監査だけを行います。どちらも 360° 画像生成器ではありません。
5. 全身、同一人物性、PoseAtlas、両手、実 load の監査を実行し、再現可能な結果と source revision SHA-256 を `release-audits.json` に記録します。
6. `python tools/check_pose_atlas_release.py --version 4.0.0 --asset-root assets/pose-atlas/v4 --audit-evidence assets/pose-atlas/v4/release-audits.json` を実行します。出力が `status: releasable` の場合に限り、この阻害を解除できます。
