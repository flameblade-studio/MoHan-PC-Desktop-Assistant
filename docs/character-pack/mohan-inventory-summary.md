# 墨寒角色內容清冊摘要／墨寒角色内容清册摘要／MoHan Character Inventory Summary／墨寒キャラクター内容一覧

## 繁體中文

這份清冊逐檔點名既有內容，供後續拆分接線。現行素體 24 張、核心圖層 600 張；衍生圖 234 張＝眨眼 24、可見手部 8、完整表情影格 156、替換遮罩 13、口腔遮罩 33。

產品資料合計 1689 個實體檔案：執行期 1641 個，產品自測必需 48 個（landmarks 與 hands 中繼資料）。兩個外觀包的 1332 個內部成員另列細項，已包含在封存包內，不重複計算實體檔案。另有 1105 個排除檔案與 120 個程式定位檔。下表只計執行期實體檔案。

| 類別 | 檔案數 |
|---|---:|
| 正式外觀包 (`appearance_pack`) | 2 |
| 外觀替換遮罩 (`appearance_replacement_mask`) | 13 |
| 服裝輪廓 (`appearance_silhouette`) | 19 |
| 身體覆蓋圖 (`body_overlay`) | 15 |
| 全身眨眼圖 (`fullbody_blink`) | 24 |
| 全身完整表情影格 (`fullbody_complete_frames`) | 156 |
| 全身完整表情替換遮罩 (`fullbody_complete_masks`) | 13 |
| 全身口腔遮罩 (`fullbody_complete_oral`) | 33 |
| 全身核心圖層 (`fullbody_core_layer`) | 600 |
| 全身表情與嘴部清單 (`fullbody_expression_rules`) | 2 |
| 全身主視角 (`fullbody_master`) | 24 |
| 全身中繼資料與綁定 (`fullbody_sidecar`) | 14 |
| 全身可見手部 (`fullbody_visible_hand`) | 8 |
| 服裝可見區與手部 (`garment_visibility`) | 48 |
| 半身完整表情與遮罩 (`halfbody_complete_expression`) | 148 |
| 半身表情與原生來源 (`halfbody_expression`) | 147 |
| 半身分層 (`halfbody_layer`) | 77 |
| 手部覆蓋圖 (`hand_overlay`) | 40 |
| 妝容眼睛開口遮罩 (`makeup_eye_aperture`) | 39 |
| 粉底安全區 (`makeup_foundation_mask`) | 39 |
| 妝容區域規則 (`makeup_region_rules`) | 1 |
| 妝容安全遮罩 (`makeup_safe_mask`) | 42 |
| 原生衣裝與動作資料 (`native_garment_motion`) | 55 |
| 來源綁定表情與妝容 (`source_bound_expression`) | 77 |
| 介面角色背景 (`ui_background`) | 2 |
| 介面品牌裝飾 (`ui_brand_decoration`) | 1 |
| 角色圖示 (`ui_character_icon`) | 1 |
| 初次設定角色圖 (`ui_onboarding`) | 1 |

正式包內點名：服裝項目 1、髮型項目 1、髮飾項目 1、妝容項目 1。變體與四語名稱見清冊 appearance_catalog。

有 120 個程式檔包含角色內容或規則，需先按清冊的 symbol 與行號改成讀資料：名字、稱謂、人格與系統提示、提醒與節日台詞、聲音偏好、角度、表情、姿勢、嘴型與圖層順序。清冊也搜尋額外角色字串位置；整個模組不等於全部要搬。

圖片、JSON 與兩個正式外觀封存包是純資料；髮型與髮飾在包內、核心圖層與正式原生衣裝中逐項列出。搬資料時仍需調整讀取路徑，這次只列清冊。

v4 一代校準、artifacts 候選、.quality-tmp 暫存、docs/release-evidence 審閱證據、tests/golden 回歸證據、製作鏡像與未引用審閱原圖都不進產品包；完整機器分類見 non_product_roots。reviewed-garments 與 source-bound-exasperated 內被正式載入或驗證的資料保留。

角色包自開始就支援獨立下載；墨寒角色包放在私有倉庫（擁有者 2026-10-05 裁定）；角色素材授權及 DLC 關係待擁有者決定。引擎與炎劍畫譜採 MIT。既有使用者設定與外觀核准保持原範圍。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## 简体中文

本清册逐文件列出现有内容，供后续拆分接线。现行素体 24 张、核心图层 600 张；衍生图 234 张＝眨眼 24、可见手部 8、完整表情帧 156、替换遮罩 13、口腔遮罩 33。

产品数据合计 1689 个实体文件：运行时 1641 个，产品自测必需 48 个（landmarks 与 hands 元数据）。两个外观包的 1332 个内部成员另列细项，已包含在归档包内，不重复计算实体文件。另有 1105 个排除文件和 120 个程序定位文件。下表只计运行时实体文件。

| 类别 | 文件数 |
|---|---:|
| 正式外观包 (`appearance_pack`) | 2 |
| 外观替换遮罩 (`appearance_replacement_mask`) | 13 |
| 服装轮廓 (`appearance_silhouette`) | 19 |
| 身体覆盖图 (`body_overlay`) | 15 |
| 全身眨眼图 (`fullbody_blink`) | 24 |
| 全身完整表情帧 (`fullbody_complete_frames`) | 156 |
| 全身完整表情替换遮罩 (`fullbody_complete_masks`) | 13 |
| 全身口腔遮罩 (`fullbody_complete_oral`) | 33 |
| 全身核心图层 (`fullbody_core_layer`) | 600 |
| 全身表情与嘴部清单 (`fullbody_expression_rules`) | 2 |
| 全身主视角 (`fullbody_master`) | 24 |
| 全身元数据与绑定 (`fullbody_sidecar`) | 14 |
| 全身可见手部 (`fullbody_visible_hand`) | 8 |
| 服装可见区与手部 (`garment_visibility`) | 48 |
| 半身完整表情与遮罩 (`halfbody_complete_expression`) | 148 |
| 半身表情与原生来源 (`halfbody_expression`) | 147 |
| 半身分层 (`halfbody_layer`) | 77 |
| 手部覆盖图 (`hand_overlay`) | 40 |
| 妆容眼睛开口遮罩 (`makeup_eye_aperture`) | 39 |
| 粉底安全区 (`makeup_foundation_mask`) | 39 |
| 妆容区域规则 (`makeup_region_rules`) | 1 |
| 妆容安全遮罩 (`makeup_safe_mask`) | 42 |
| 原生衣装与动作数据 (`native_garment_motion`) | 55 |
| 来源绑定表情与妆容 (`source_bound_expression`) | 77 |
| 界面角色背景 (`ui_background`) | 2 |
| 界面品牌装饰 (`ui_brand_decoration`) | 1 |
| 角色图标 (`ui_character_icon`) | 1 |
| 首次设置角色图 (`ui_onboarding`) | 1 |

正式包内列明：服装项目 1、发型项目 1、发饰项目 1、妆容项目 1。变体与四语名称见清册 appearance_catalog。

有 120 个程序文件包含角色内容或规则，需要按清册的 symbol 和行号改为读取数据：名字、称谓、人格与系统提示、提醒与节日台词、声音偏好、角度、表情、姿势、嘴型与图层顺序。清册也搜索额外角色字符串位置；整个模块不等于全部要搬。

图片、JSON 和两个正式外观封存包是纯数据；发型与发饰在包内、核心图层和正式原生衣装中逐项列出。搬数据时仍需调整读取路径，本次只列清册。

v4 一代校准、artifacts 候选、.quality-tmp 暂存、docs/release-evidence 审阅证据、tests/golden 回归证据、制作镜像和未引用审阅原图均不进入产品包；完整机器分类见 non_product_roots。reviewed-garments 与 source-bound-exasperated 中正式加载或验证的数据予以保留。

角色包从开始就支持独立下载；墨寒角色包放在私有仓库（所有者 2026-10-05 裁定）；角色素材授权及 DLC 关系待所有者决定。引擎与炎剑画谱采用 MIT。现有用户设置与外观批准保持原范围。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## English

This measured index names existing content for subsequent extraction. There are 24 master views, 600 core layers and 234 derivatives: 24 blinks, 8 visible hands, 156 complete expression frames, 13 replacement masks and 33 oral masks.

Product data totals 1689 physical files: 1641 runtime files and 48 required self-test sidecars (landmarks and hands). The 1332 members inside two appearance archives are indexed separately and already included in those archives. There are also 1105 excluded files and 120 source-location files. The table counts runtime physical files only.

| Category | Files |
|---|---:|
| Official appearance archives (`appearance_pack`) | 2 |
| Appearance replacement masks (`appearance_replacement_mask`) | 13 |
| Garment silhouettes (`appearance_silhouette`) | 19 |
| Body overlays (`body_overlay`) | 15 |
| Full-body blinks (`fullbody_blink`) | 24 |
| Complete full-body frames (`fullbody_complete_frames`) | 156 |
| Full-body replacement masks (`fullbody_complete_masks`) | 13 |
| Full-body oral masks (`fullbody_complete_oral`) | 33 |
| Core full-body layers (`fullbody_core_layer`) | 600 |
| Full-body expression manifests (`fullbody_expression_rules`) | 2 |
| Full-body master views (`fullbody_master`) | 24 |
| Full-body metadata and bindings (`fullbody_sidecar`) | 14 |
| Full-body visible hands (`fullbody_visible_hand`) | 8 |
| Garment visibility and hands (`garment_visibility`) | 48 |
| Complete half-body expressions and masks (`halfbody_complete_expression`) | 148 |
| Half-body expressions and native sources (`halfbody_expression`) | 147 |
| Half-body layers (`halfbody_layer`) | 77 |
| Hand overlays (`hand_overlay`) | 40 |
| Makeup eye aperture masks (`makeup_eye_aperture`) | 39 |
| Foundation safe regions (`makeup_foundation_mask`) | 39 |
| Makeup region rules (`makeup_region_rules`) | 1 |
| Makeup safe masks (`makeup_safe_mask`) | 42 |
| Native garment and motion data (`native_garment_motion`) | 55 |
| Source-bound expressions and makeup (`source_bound_expression`) | 77 |
| Character UI backgrounds (`ui_background`) | 2 |
| UI brand decoration (`ui_brand_decoration`) | 1 |
| Character icon (`ui_character_icon`) | 1 |
| Onboarding character image (`ui_onboarding`) | 1 |

Official archives declare 1 garment, 1 hairstyle, 1 headwear and 1 makeup item. Variants and names are indexed in appearance_catalog.

120 source files contain character content or rules. Use indexed symbols and lines to extract names, titles, persona and system prompts, reminders and occasion dialogue, voice preferences, angles, expressions, poses, mouth geometry and layer order. Additional character literals are searched; entire modules are not extraction payloads.

Images, JSON and two official appearance archives are data. Hairstyles and headwear are indexed within archives, core layers and native garments. Moving data still requires changing reader paths; this step only inventories it.

Generation-1 v4 calibration, artifacts candidates, .quality-tmp temporaries, docs/release-evidence reviews, tests/golden regression evidence, authoring mirrors and unreferenced review originals stay outside the product pack; non_product_roots records the machine-readable boundary. Formally loaded or verified reviewed-garments and source-bound-exasperated data remains included.

Independent download is a design requirement from inception. The MoHan character pack lives in a private repository (owner decision, 2026-10-05); character asset licensing and DLC relationships await owner decisions. The engine and art tool use MIT. Existing user settings and appearance approvals retain their scope.

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## 日本語

この実測一覧は今後の分離に向け既存の内容を列挙します。主視点 24 枚、主要レイヤー 600 枚、派生画像 234 枚です。内訳は瞬き 24、可視の手 8、完全表情フレーム 156、置換マスク 13、口腔マスク 33 です。

製品データは実ファイル 1689 個です。実行時に 1641 個、製品自己テストに landmarks と hands のメタデータ 48 個が必要です。外観アーカイブ 2 個に含まれる 1332 メンバーは別途列挙し、実ファイル数には重複計上しません。除外ファイル 1105 個とコード位置ファイル 120 個も記録します。下表は実行時の実ファイルのみを数えます。

| 分類 | ファイル数 |
|---|---:|
| 正式外観パック (`appearance_pack`) | 2 |
| 外観置換マスク (`appearance_replacement_mask`) | 13 |
| 衣装の輪郭 (`appearance_silhouette`) | 19 |
| 身体の重ね画像 (`body_overlay`) | 15 |
| 全身の瞬き (`fullbody_blink`) | 24 |
| 全身の完全表情フレーム (`fullbody_complete_frames`) | 156 |
| 全身の置換マスク (`fullbody_complete_masks`) | 13 |
| 全身の口腔マスク (`fullbody_complete_oral`) | 33 |
| 全身の主要レイヤー (`fullbody_core_layer`) | 600 |
| 全身表情と口部の定義 (`fullbody_expression_rules`) | 2 |
| 全身の主視点 (`fullbody_master`) | 24 |
| 全身メタデータと紐付け (`fullbody_sidecar`) | 14 |
| 全身の可視の手 (`fullbody_visible_hand`) | 8 |
| 衣装の可視領域と手 (`garment_visibility`) | 48 |
| 半身の完全表情とマスク (`halfbody_complete_expression`) | 148 |
| 半身表情と元画像 (`halfbody_expression`) | 147 |
| 半身レイヤー (`halfbody_layer`) | 77 |
| 手の重ね画像 (`hand_overlay`) | 40 |
| メイクの眼開口マスク (`makeup_eye_aperture`) | 39 |
| ファンデーションの安全領域 (`makeup_foundation_mask`) | 39 |
| メイク領域の規則 (`makeup_region_rules`) | 1 |
| メイク安全マスク (`makeup_safe_mask`) | 42 |
| 元の衣装と動作データ (`native_garment_motion`) | 55 |
| 出典に紐付いた表情とメイク (`source_bound_expression`) | 77 |
| キャラクター背景 (`ui_background`) | 2 |
| ブランド装飾 (`ui_brand_decoration`) | 1 |
| キャラクターアイコン (`ui_character_icon`) | 1 |
| 初回設定のキャラクター画像 (`ui_onboarding`) | 1 |

正式パック内には衣装 1、髪型 1、髪飾り 1、メイク 1 項目があります。差分と四言語の名称は appearance_catalog に記録します。

120 個のソースファイルにキャラクター内容や規則があります。symbol と行番号に従い、名前、呼称、人格とシステムプロンプト、通知と行事の台詞、声の好み、角度、表情、姿勢、口の形とレイヤー順をデータ化します。追加の文字列も検索し、モジュール全体を移行対象とは扱いません。

画像、JSON、正式な外観アーカイブ 2 個はデータです。髪型と髪飾りはアーカイブ、主要レイヤー、正式な衣装内で列挙します。移動時には読込先の変更も必要で、この段階は一覧作成のみです。

v4 の第一世代校正、artifacts の候補、.quality-tmp の一時出力、docs/release-evidence の審査証拠、tests/golden の回帰証拠、制作ミラー、未参照の審査原画は製品パックに含めません。機械可読の境界は non_product_roots に記録します。reviewed-garments と source-bound-exasperated の正式に読込または検証するデータは含めます。

独立ダウンロードは当初からの設計要件です。墨寒キャラクターパックは非公開リポジトリに置きます（所有者決定、2026-10-05）。素材ライセンスと DLC との関係は所有者の決定待ちです。エンジンと素材管理ツールは MIT を採用します。既存の設定と外観承認の範囲を維持します。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`
