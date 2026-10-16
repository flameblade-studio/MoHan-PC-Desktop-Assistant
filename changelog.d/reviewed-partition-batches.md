### 核可分區批次入口／核可分区批次入口／Reviewed partition batch entry point／確認済み領域のバッチ入口

- 將不同已驗收批次的同視角分區彙整為單一原生組裝輸入，讓來源、角色與區域各自維持唯一且互斥，剩餘區域保持單次組裝。／将不同已验收批次的同视角分区汇总为单一原生组装输入，让来源、角色与区域各自保持唯一且互斥，剩余区域保持单次组装。／Consolidate completed same-view partitions into one native assembly input with source, role, and region uniqueness enforced; compose each remainder once.／完了済みバッチの同一視点領域を単一の原寸組立入力に統合し、原画、役割、領域の一意性と排他性を保ち、残部を一度だけ合成します。

- 驗證明列雜湊的審閱對照圖與修正紀錄，讓交付後及編碼期間的證據維持原值；保留舊版描述文字相容性。／验证明确哈希的审阅对照图与修正记录，让交付后及编码期间的证据保持原值；保留旧版描述文字兼容性。／Validate explicitly hashed review evidence and traces, keeping evidence fixed after review and throughout encoding while retaining compatibility with legacy descriptive notes.／ハッシュ付き確認画像と修正記録を検証し、確認後とエンコード中も証拠を固定して、旧形式の説明文との互換性を維持します。

- 統一接入原生可見分區並鎖定來源，讓遮罩互斥與覆寫受到保護，保留未分類區域與逐像素重組證據。／统一接入原始可见分区并锁定来源，让遮罩互斥与覆盖受到保护，保留未分类区域及逐像素重组证据。／Integrate native visible partitions with source binding, protected overlap and overwrite boundaries, an explicit unclassified remainder, and exact reconstruction evidence.／原寸の可視領域を統合して原画を固定し、マスクの排他性と上書き境界を保護し、未分類の残部と画素一致の証拠を保持します。
- 直接核對 PNG 原始位元深度，僅接受原生 8 位元來源，通過檢查後才可記錄精確保留證據。／直接核对 PNG 原始位深，仅接受原生 8 位来源，通过检查后才可记录精确保留证据。／Validate the original PNG bit depth and admit only native 8-bit sources before recording exact-preservation evidence.／PNG の元のビット深度を検証し、原生の 8 ビット画像だけを受け入れてから、完全保持の証拠を記録します。

- 彙整時交叉驗證完成收據、原生輸出像素與完整目錄，讓影像內容與宣告雜湊保持一致。／汇总时交叉验证完成收据、原始输出像素与完整目录，让图像内容与声明哈希保持一致。／Cross-check completed receipts, native output pixels, and complete directories so image content and declared hashes remain consistent.／完了受領記録、原寸出力画素、完全なディレクトリを照合し、画像内容と宣言ハッシュの整合性を保持します。
