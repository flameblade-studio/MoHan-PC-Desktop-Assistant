# 墨寒 2.5D 姿態包 ／ 墨寒 2.5D 姿态包 ／ MoHan 2.5D Pose Packs ／ 墨寒 2.5D 姿勢パック

## 繁體中文

姿態包是版本化、資料驅動、單一自包含 ZIP。使用者只需下載並選取一個檔案；所有 PNG/WebP 資產、manifest、hash、來源與授權都在同一 archive。套件完整自含於單一 archive，成員範圍限定為 manifest 及其宣告的 PNG/WebP 資產。匯入會先完整驗證，再於目的目錄原子安裝；只有完整驗證成功才改變目的目錄，有效舊包持續受到保護。安裝完成後，目前三姿態與 active state 維持原值。

格式 v1 固定相容目前的素體世代 `mohan-body-v2`（2026-09-02 起）；一代 `mohan-body-v1` 姿態包須依現行範本重建。Canonical yaw 每 15 度一格，由 `-180` 完整背面開始，依序到 `165`，共 24 個互異方向；完整背面由 `-180` 唯一表示。每個包可宣告一個或多個 pitch band，並可在未來版本增量增加。每個 `pose_id × pitch_band` 的允收條件為完整涵蓋全部 24 個 canonical yaw，且方向互異、齊全。

每個 view 都是透明分層資料，至少包含 `body`、左右臂校正與左右手校正。每層必須宣告 SHA-256、PNG/WebP 路徑、尺寸、anchor、唯一 depth、遮擋規則及 `transparent: true`。可另加臉、髮型、衣裝、頭飾與武器對齊層，但臉仍為核心掌握。Manifest 必須明確宣告 face、hair、garment、headwear、weapon 的相容責任，避免外觀槽誤套或穿模。允收資產須齊全，hash 與尺寸相符，depth 互異，遮擋合法，且每個檔案恰好受到一次引用。

安全限制涵蓋 archive／單檔／解壓總量、成員數、壓縮比與最大尺寸。成員使用 archive 內的正規相對路徑、正斜線、未加密 PNG/WebP，並符合宣告與所有安全上限。來源必須記錄 `original`、`concept` 或 `reference-derived`、作者、授權、provenance，且 `reference_included` 必須為 false，確認參考作品保持在封裝範圍之外。

安裝新增經驗證的單檔，並維持 active 狀態。列舉 API 回傳已驗證套件。刪除前再次驗證安全 ID、檔名與 manifest ID；移除範圍限定為已切換離開的外部 archive；內建、active 與 preview 中的姿態持續受到保護。移除作業只處理指定 archive，其他套件、核心本體、個人資料與原有 `cheek-rest`、`left-neutral`、`front-crossed` 三姿態。擴充包發生失敗時，這三姿態仍完整保留。

## 简体中文

姿态包是版本化、数据驱动、单一自包含 ZIP。用户只需下载并选择一个文件；所有 PNG/WebP 资产、manifest、hash、来源与许可都位于同一 archive。套件完整自含于单一 archive，成员范围限定为 manifest 及其声明的 PNG/WebP 资源。导入会先完整验证，再在目标目录原子安装；只有完整验证成功才改变目标目录，有效旧包持续受到保护。安装完成后，现有三姿态与 active state 维持原值。

格式 v1 固定兼容当前的素体世代 `mohan-body-v2`（2026-09-02 起）；一代 `mohan-body-v1` 姿态包须按现行模板重建。Canonical yaw 每 15 度一格，从 `-180` 完整背面开始，依次到 `165`，共 24 个互异方向；完整背面由 `-180` 唯一表示。每个包可声明一个或多个 pitch band，并可在未来版本增量增加。每个 `pose_id × pitch_band` 的接收条件为完整覆盖全部 24 个 canonical yaw，并且方向互异、齐全。

每个 view 都是透明分层数据，至少包含 `body`、左右臂校正与左右手校正。每层必须声明 SHA-256、PNG/WebP 路径、尺寸、anchor、唯一 depth、遮挡规则及 `transparent: true`。可另加脸、发型、服装、头饰与武器对齐层，但脸仍由核心掌握。Manifest 必须明确声明 face、hair、garment、headwear、weapon 的兼容责任，避免外观槽误用或穿模。接收资源须齐全，hash 与尺寸相符，depth 互异，遮挡合法，并且每个文件恰好受到一次引用。

安全限制覆盖 archive／单文件／解压总量、成员数、压缩比与最大尺寸。成员使用 archive 内的正规相对路径、正斜线、未加密 PNG/WebP，并符合声明与所有安全上限。来源必须记录 `original`、`concept` 或 `reference-derived`、作者、许可、provenance，且 `reference_included` 必须为 false，确认参考作品保持在封装范围之外。

安装添加已验证的单文件，并维持 active 状态。列出 API 返回已验证包。删除前再次验证安全 ID、文件名与 manifest ID；删除范围限定为已切换离开的外部 archive；内置、active 与 preview 中的姿态持续受到保护。删除操作只处理指定 archive，其他包、核心本体、个人数据与原有 `cheek-rest`、`left-neutral`、`front-crossed` 三姿态。扩展包发生失败时，这三姿态仍完整保留。

## English

A pose pack is a versioned, data-driven, single self-contained ZIP. A user downloads and selects one file. Every PNG/WebP asset, manifest, hash, source record, and license is inside the same archive. The package is fully self-contained in one archive, with membership limited to the manifest and its declared PNG/WebP assets. Import fully validates before atomically installing in the destination directory. The destination changes only after complete validation succeeds, and valid installed versions remain protected. Installation preserves the active state and the existing three poses.

Format v1 targets the current body generation `mohan-body-v2` (since 2026-09-02); generation-1 `mohan-body-v1` pose packs require rebuilding against the current template. Canonical yaw advances in 15-degree steps, beginning at the complete rear view `-180` and ending at `165`, for 24 unique directions. `-180` is the sole representation of the complete rear view. A package declares one or more pitch bands, with future versions able to add bands incrementally. Every `pose_id × pitch_band` is accepted when it covers all 24 canonical yaw values exactly once.

Every view is transparent layered data containing at least `body`, left/right arm corrections, and left/right hand corrections. Each layer declares SHA-256, a PNG/WebP path, dimensions, anchor, unique depth, occlusion rule, and `transparent: true`. Optional alignment layers may describe face, hair, garment, headwear, and weapon placement, while the face remains core-owned. The manifest explicitly assigns compatibility responsibility for face, hair, garment, headwear, and weapon, preventing wrong-slot rendering and clipping. Accepted assets are complete, match their hashes and dimensions, use unique depth, have valid occlusion, and are each referenced exactly once.

Security limits cover archive, member, expanded size, member count, compression ratio, and dimensions. Members use normalized in-archive relative paths, forward slashes, unencrypted PNG/WebP content, and comply with the manifest and every safety limit. Source records include `original`, `concept`, or `reference-derived` kind, author, license, and provenance. `reference_included` must be false, confirming that referenced works remain outside the package.

Installation adds the validated self-contained file and preserves active state. Listing returns validated packages. Removal revalidates the safe ID and requires filename and manifest identity to match. Removal scope is an external archive after switching away from it; built-in, active, and previewed poses remain protected. Removal touches the selected archive, while every other package, core assets, personal data, and the original `cheek-rest`, `left-neutral`, and `front-crossed` poses. Those three remain fully available whenever an extension pack encounters a failure.

## 日本語

姿勢パックは、バージョン管理されたデータ駆動の単一自己完結 ZIP です。利用者がダウンロードして選ぶのは一つのファイルだけです。すべての PNG/WebP 素材、manifest、hash、出典、ライセンスは同じ archive 内にあります。パッケージは一つの archive で完全に自己完結し、メンバーを manifest と宣言済み PNG/WebP 素材に限定します。インポートは全体検証後に配置先へアトミックにインストールします。完全な検証成功後にだけ配置先を変更し、有効な旧パックを保護します。インストール後も active 状態と既存三姿勢を維持します。

形式 v1 は現行の素体世代 `mohan-body-v2` に固定対応します（2026-09-02 以降）。第一世代 `mohan-body-v1` の姿勢パックは現行テンプレートで再構築します。Canonical yaw は 15 度刻みで、完全な背面 `-180` から `165` までの重複しない 24 方向です。完全な背面は `-180` で一意に表します。各パックは一つ以上の pitch band を宣言し、将来の版で段階的に追加できます。すべての `pose_id × pitch_band` は、24 個の canonical yaw を一度ずつ備えた場合に受け入れられます。

各 view は透明な分層データで、最低限 `body`、左右の腕補正、左右の手補正を含みます。各層は SHA-256、PNG/WebP パス、寸法、anchor、一意の depth、遮蔽規則、`transparent: true` を宣言します。顔、髪、衣装、頭飾り、武器の位置合わせ層も追加できますが、顔はコア所有のままです。Manifest は face、hair、garment、headwear、weapon の互換責任を明記し、誤った外観 slot や貫通を防ぎます。受入素材はすべて揃い、hash と寸法が一致し、depth が一意で、遮蔽が有効で、各ファイルが一度だけ参照されます。

安全上限は archive、単一メンバー、展開合計、メンバー数、圧縮率、最大寸法を対象とします。メンバーは archive 内の正規相対パスとスラッシュを使う未暗号化 PNG/WebP とし、manifest とすべての安全上限に適合させます。出典には `original`、`concept`、`reference-derived`、作者、ライセンス、provenance を記録し、`reference_included` は false 必須です。これにより参照作品そのものをパッケージ範囲外に保ちます。

インストールは検証済み単一ファイルを追加し、active 状態を維持します。一覧 API は検証済みパックを返します。削除前に安全 ID を再検証し、ファイル名と manifest ID の一致を要求します。削除範囲は切替え済みの外部 archive に限定し、内蔵、active、preview 中の姿勢を保護します。削除は指定 archive を対象とし、他パック、コア本体、個人データ、既存の `cheek-rest`、`left-neutral`、`front-crossed` 三姿勢には触れません。拡張パックで失敗が発生した場合も、この三姿勢は完全に残ります。
