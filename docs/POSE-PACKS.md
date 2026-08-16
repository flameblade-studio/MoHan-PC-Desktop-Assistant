# 墨寒 2.5D 姿態包 ／ 墨寒 2.5D 姿态包 ／ MoHan 2.5D Pose Packs ／ 墨寒 2.5D 姿勢パック

## 繁體中文

姿態包是版本化、資料驅動、單一自包含 ZIP。使用者只需下載並選取一個檔案；所有 PNG/WebP 資產、manifest、hash、來源與授權都在同一 archive。禁止旁附資料夾、外部套件、網路下載、跨包必需引用、Python、JavaScript、EXE、DLL 或腳本。匯入會先完整驗證，再於目的目錄原子安裝；失敗不留下半套，也不覆寫有效舊包。安裝不會自動啟用或改變目前三姿態。

格式 v1 固定相容 `mohan-body-v1`。Canonical yaw 每 15 度一格，由 `-180` 完整背面開始，依序到 `165`，共 24 個不重複方向；不另外接受與 `-180` 重複的 `180`。每個包可宣告一個或多個 pitch band，並可在未來版本增量增加。每個 `pose_id × pitch_band` 必須完整涵蓋全部 24 個 yaw；未知、重複或缺漏方向均 fail closed。

每個 view 都是透明分層資料，至少包含 `body`、左右臂校正與左右手校正。每層必須宣告 SHA-256、PNG/WebP 路徑、尺寸、anchor、唯一 depth、遮擋規則及 `transparent: true`。可另加臉、髮型、衣裝、頭飾與武器對齊層，但臉仍為核心掌握。Manifest 必須明確宣告 face、hair、garment、headwear、weapon 的相容責任，避免外觀槽誤套或穿模。資產缺少、hash／尺寸不符、深度衝突、非法遮擋或未引用／重複檔案都會拒絕。

安全限制涵蓋 archive／單檔／解壓總量、成員數、壓縮比與最大尺寸。絕對路徑、`..`、反斜線、符號連結、加密成員、執行碼與非 PNG/WebP 成員均被拒絕。來源必須記錄 `original`、`concept` 或 `reference-derived`、作者、授權、provenance，且 `reference_included` 必須為 false，避免把參考作品直接打包。

安裝只新增經驗證的單檔，不寫 active 狀態。列舉 API 只回傳已驗證套件。刪除前再次驗證安全 ID、檔名與 manifest ID；內建姿態不可刪，active 或 preview 中的包也不可刪，必須先切換。刪除只碰指定 archive，不碰其他包、核心本體、個人資料或原有 `cheek-rest`、`left-neutral`、`front-crossed` 三姿態。任何擴充包失敗時，這三姿態仍完整保留。

## 简体中文

姿态包是版本化、数据驱动、单一自包含 ZIP。用户只需下载并选择一个文件；所有 PNG/WebP 资产、manifest、hash、来源与许可都位于同一 archive。禁止附带文件夹、外部包、网络下载、跨包必需引用、Python、JavaScript、EXE、DLL 或脚本。导入会先完整验证，再在目标目录原子安装；失败不留下半套，也不覆盖有效旧包。安装不会自动启用或改变现有三姿态。

格式 v1 固定兼容 `mohan-body-v1`。Canonical yaw 每 15 度一格，从 `-180` 完整背面开始，依次到 `165`，共 24 个不重复方向；不另接受与 `-180` 重复的 `180`。每个包可声明一个或多个 pitch band，并可在未来版本增量增加。每个 `pose_id × pitch_band` 必须完整覆盖全部 24 个 yaw；未知、重复或缺漏方向均 fail closed。

每个 view 都是透明分层数据，至少包含 `body`、左右臂校正与左右手校正。每层必须声明 SHA-256、PNG/WebP 路径、尺寸、anchor、唯一 depth、遮挡规则及 `transparent: true`。可另加脸、发型、服装、头饰与武器对齐层，但脸仍由核心掌握。Manifest 必须明确声明 face、hair、garment、headwear、weapon 的兼容责任，避免外观槽误用或穿模。资产缺少、hash／尺寸不符、深度冲突、非法遮挡或未引用／重复文件都会被拒绝。

安全限制覆盖 archive／单文件／解压总量、成员数、压缩比与最大尺寸。绝对路径、`..`、反斜线、符号链接、加密成员、执行代码与非 PNG/WebP 成员均被拒绝。来源必须记录 `original`、`concept` 或 `reference-derived`、作者、许可、provenance，且 `reference_included` 必须为 false，避免直接打包参考作品。

安装只添加已验证的单文件，不写 active 状态。列出 API 只返回已验证包。删除前再次验证安全 ID、文件名与 manifest ID；内置姿态不可删除，active 或 preview 中的包也不可删除，必须先切换。删除只影响指定 archive，不影响其他包、核心本体、个人数据或原有 `cheek-rest`、`left-neutral`、`front-crossed` 三姿态。任何扩展包失败时，这三姿态仍完整保留。

## English

A pose pack is a versioned, data-driven, single self-contained ZIP. A user downloads and selects one file. Every PNG/WebP asset, manifest, hash, source record, and license is inside the same archive. Sidecar folders, external packages, network downloads, required cross-pack references, Python, JavaScript, EXE, DLL, and scripts are forbidden. Import fully validates before atomically installing in the destination directory. Failure leaves no partial package and does not overwrite a valid installed version. Installation never activates a pack or changes the existing three poses.

Format v1 targets `mohan-body-v1`. Canonical yaw advances in 15-degree steps, beginning at the complete rear view `-180` and ending at `165`, for 24 unique directions. The duplicate `180`, equivalent to `-180`, is not accepted. A package declares one or more pitch bands, with future versions able to add bands incrementally. Every `pose_id × pitch_band` must cover all 24 yaw values. Unknown, duplicate, or missing directions fail closed.

Every view is transparent layered data containing at least `body`, left/right arm corrections, and left/right hand corrections. Each layer declares SHA-256, a PNG/WebP path, dimensions, anchor, unique depth, occlusion rule, and `transparent: true`. Optional alignment layers may describe face, hair, garment, headwear, and weapon placement, while the face remains core-owned. The manifest explicitly assigns compatibility responsibility for face, hair, garment, headwear, and weapon, preventing wrong-slot rendering and clipping. Missing assets, hash or dimension mismatch, ambiguous depth, invalid occlusion, and unreferenced or duplicate files are rejected.

Security limits cover archive, member, expanded size, member count, compression ratio, and dimensions. Absolute paths, `..`, backslashes, symlinks, encrypted members, executable code, and members other than PNG/WebP are rejected. Source records include `original`, `concept`, or `reference-derived` kind, author, license, and provenance. `reference_included` must be false so referenced works are never directly packaged.

Installation adds only the validated self-contained file and writes no active state. Listing returns only validated packages. Removal revalidates the safe ID and requires filename and manifest identity to match. Built-in poses cannot be removed, and an active or previewed pack must first be switched. Removal touches only the selected archive, never another package, core assets, personal data, or the original `cheek-rest`, `left-neutral`, and `front-crossed` poses. Those three remain fully available whenever an extension pack fails.

## 日本語

姿勢パックは、バージョン管理されたデータ駆動の単一自己完結 ZIP です。利用者がダウンロードして選ぶのは一つのファイルだけです。すべての PNG/WebP 素材、manifest、hash、出典、ライセンスは同じ archive 内にあります。付属フォルダー、外部パッケージ、ネットワークダウンロード、必須の別パック参照、Python、JavaScript、EXE、DLL、スクリプトは禁止です。インポートは全体検証後に配置先へアトミックにインストールします。失敗時は半端なパックを残さず、有効な旧パックも上書きしません。インストールだけで有効化したり、既存三姿勢を変更したりしません。

形式 v1 は `mohan-body-v1` に固定対応します。Canonical yaw は 15 度刻みで、完全な背面 `-180` から `165` までの重複しない 24 方向です。`-180` と同じ `180` は受け付けません。各パックは一つ以上の pitch band を宣言し、将来の版で段階的に追加できます。すべての `pose_id × pitch_band` が 24 yaw 全部を備える必要があり、未知、重複、不足方向は fail closed です。

各 view は透明な分層データで、最低限 `body`、左右の腕補正、左右の手補正を含みます。各層は SHA-256、PNG/WebP パス、寸法、anchor、一意の depth、遮蔽規則、`transparent: true` を宣言します。顔、髪、衣装、頭飾り、武器の位置合わせ層も追加できますが、顔はコア所有のままです。Manifest は face、hair、garment、headwear、weapon の互換責任を明記し、誤った外観 slot や貫通を防ぎます。素材不足、hash／寸法不一致、depth 競合、不正な遮蔽、未参照／重複ファイルは拒否します。

安全上限は archive、単一メンバー、展開合計、メンバー数、圧縮率、最大寸法を対象とします。絶対パス、`..`、バックスラッシュ、シンボリックリンク、暗号化メンバー、実行コード、PNG/WebP 以外のメンバーは拒否します。出典には `original`、`concept`、`reference-derived`、作者、ライセンス、provenance を記録し、`reference_included` は false 必須です。参照作品そのものを同梱しません。

インストールは検証済み単一ファイルを追加するだけで、active 状態を書きません。一覧 API は検証済みパックだけを返します。削除前に安全 ID を再検証し、ファイル名と manifest ID の一致を要求します。内蔵姿勢は削除できず、active または preview 中のパックは先に切り替える必要があります。削除は指定 archive だけを対象とし、他パック、コア本体、個人データ、既存の `cheek-rest`、`left-neutral`、`front-crossed` 三姿勢には触れません。拡張パックが失敗しても、この三姿勢は完全に残ります。
