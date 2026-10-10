# 墨寒角色內容清冊摘要／墨寒角色内容清册摘要／MoHan Character Inventory Summary／墨寒キャラクター内容一覧

## 繁體中文

這份清冊逐檔點名既有內容，供後續拆分接線。現行素體 24 張、核心圖層 600 張；衍生圖 234 張＝眨眼 24、可見手部 8、完整表情影格 156、替換遮罩 13、口腔遮罩 33。

產品資料合計 1726 個實體檔案：執行期 1678 個，產品自測必需 48 個（landmarks 與 hands 中繼資料）。兩個外觀包的 1547 個內部成員另列細項，已包含在封存包內，不重複計算實體檔案。另有 1109 個排除檔案與 22 個程式定位檔。下表只計執行期實體檔案。

| 類別 | 檔案數 |
|---|---:|
| 正式外觀包 (`appearance_pack`) | 3 |
| 外觀替換遮罩 (`appearance_replacement_mask`) | 13 |
| 服裝輪廓 (`appearance_silhouette`) | 19 |
| 身體覆蓋圖 (`body_overlay`) | 15 |
| 角色外觀預設資料 (`character_appearance_defaults`) | 2 |
| 角色台詞與事件資料 (`character_dialogue_data`) | 10 |
| 角色表情狀態目錄 (`character_expression_catalog`) | 2 |
| 角色授權通知 (`character_license_notice`) | 2 |
| 角色身分與人格資料 (`character_persona_data`) | 10 |
| 角色外觀骨架資料 (`character_rig_data`) | 2 |
| 角色執行期素材綁定資料 (`character_runtime_binding_data`) | 2 |
| 角色執行期台詞資料 (`character_runtime_dialogue_data`) | 2 |
| 角色介面識別資料 (`character_ui_identifier_data`) | 2 |
| 角色聲音偏好資料 (`character_voice_data`) | 2 |
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

正式包內點名：服裝項目 2、髮型項目 2、髮飾項目 1、妝容項目 1。變體與四語名稱見清冊 appearance_catalog。

實際內容規則找到 22 個程式檔；其中真正待搬或參數化 4 個，產品殼允許保留 18 個。舊名單另有 64 個檔案只有人工提示、沒有實際內容證據，不計入進度。每筆證據都保存行號、內容與規則名。

圖片、JSON 與兩個正式外觀封存包是純資料；髮型與髮飾在包內、核心圖層與正式原生衣裝中逐項列出。搬資料時仍需調整讀取路徑，這次只列清冊。

v4 一代校準、artifacts 候選、.quality-tmp 暫存、docs/release-evidence 審閱證據、tests/golden 回歸證據、製作鏡像與未引用審閱原圖都不進產品包；完整機器分類見 non_product_roots。reviewed-garments 與 source-bound-exasperated 內被正式載入或驗證的資料保留。

角色包自開始就支援獨立下載；墨寒與林可芸角色包公開附於墨寒專案發布頁，角色素材與付費 DLC 均採 CC BY-NC-ND 4.0；DLC 與角色包的關係待擁有者決定。引擎與炎劍畫譜採 MIT。既有使用者設定與外觀核准保持原範圍。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## 简体中文

本清册逐文件列出现有内容，供后续拆分接线。现行素体 24 张、核心图层 600 张；衍生图 234 张＝眨眼 24、可见手部 8、完整表情帧 156、替换遮罩 13、口腔遮罩 33。

产品数据合计 1726 个实体文件：运行时 1678 个，产品自测必需 48 个（landmarks 与 hands 元数据）。两个外观包的 1547 个内部成员另列细项，已包含在归档包内，不重复计算实体文件。另有 1109 个排除文件和 22 个程序定位文件。下表只计运行时实体文件。

| 类别 | 文件数 |
|---|---:|
| 正式外观包 (`appearance_pack`) | 3 |
| 外观替换遮罩 (`appearance_replacement_mask`) | 13 |
| 服装轮廓 (`appearance_silhouette`) | 19 |
| 身体覆盖图 (`body_overlay`) | 15 |
| 角色外观默认数据 (`character_appearance_defaults`) | 2 |
| 角色台词与事件数据 (`character_dialogue_data`) | 10 |
| 角色表情状态目录 (`character_expression_catalog`) | 2 |
| 角色授权通知 (`character_license_notice`) | 2 |
| 角色身份与人格数据 (`character_persona_data`) | 10 |
| 角色外观骨架数据 (`character_rig_data`) | 2 |
| 角色运行期素材绑定数据 (`character_runtime_binding_data`) | 2 |
| 角色运行期台词数据 (`character_runtime_dialogue_data`) | 2 |
| 角色界面标识数据 (`character_ui_identifier_data`) | 2 |
| 角色声音偏好数据 (`character_voice_data`) | 2 |
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

正式包内列明：服装项目 2、发型项目 2、发饰项目 1、妆容项目 1。变体与四语名称见清册 appearance_catalog。

实际内容规则找到 22 个程序文件；其中真正待迁移或参数化 4 个，产品壳允许保留 18 个。旧名单另有 64 个文件只有人工提示、没有实际内容证据，不计入进度。每条证据都保存行号、内容与规则名。

图片、JSON 和两个正式外观封存包是纯数据；发型与发饰在包内、核心图层和正式原生衣装中逐项列出。搬数据时仍需调整读取路径，本次只列清册。

v4 一代校准、artifacts 候选、.quality-tmp 暂存、docs/release-evidence 审阅证据、tests/golden 回归证据、制作镜像和未引用审阅原图均不进入产品包；完整机器分类见 non_product_roots。reviewed-garments 与 source-bound-exasperated 中正式加载或验证的数据予以保留。

角色包从开始就支持独立下载；墨寒与林可芸角色包公开附于墨寒项目发布页，角色素材与付费 DLC 均采用 CC BY-NC-ND 4.0；DLC 与角色包的关系待所有者决定。引擎与炎剑画谱采用 MIT。现有用户设置与外观批准保持原范围。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## English

This measured index names existing content for subsequent extraction. There are 24 master views, 600 core layers and 234 derivatives: 24 blinks, 8 visible hands, 156 complete expression frames, 13 replacement masks and 33 oral masks.

Product data totals 1726 physical files: 1678 runtime files and 48 required self-test sidecars (landmarks and hands). The 1547 members inside two appearance archives are indexed separately and already included in those archives. There are also 1109 excluded files and 22 source-location files. The table counts runtime physical files only.

| Category | Files |
|---|---:|
| Official appearance archives (`appearance_pack`) | 3 |
| Appearance replacement masks (`appearance_replacement_mask`) | 13 |
| Garment silhouettes (`appearance_silhouette`) | 19 |
| Body overlays (`body_overlay`) | 15 |
| Character appearance defaults (`character_appearance_defaults`) | 2 |
| Character dialogue and event data (`character_dialogue_data`) | 10 |
| Character expression state catalog (`character_expression_catalog`) | 2 |
| Character license notices (`character_license_notice`) | 2 |
| Character identity and persona data (`character_persona_data`) | 10 |
| Character rig data (`character_rig_data`) | 2 |
| Character runtime binding data (`character_runtime_binding_data`) | 2 |
| Character runtime dialogue data (`character_runtime_dialogue_data`) | 2 |
| Character UI identifier data (`character_ui_identifier_data`) | 2 |
| Character voice preference data (`character_voice_data`) | 2 |
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

Official archives declare 2 garment, 2 hairstyle, 1 headwear and 1 makeup item. Variants and names are indexed in appearance_catalog.

Actual-content rules find 22 source files: 4 require extraction or parameterization and 18 are allowed product-shell files. Another 64 files appear only as manual hints with no actual-content evidence and do not count toward progress. Every evidence item records a line, content and rule name.

Images, JSON and two official appearance archives are data. Hairstyles and headwear are indexed within archives, core layers and native garments. Moving data still requires changing reader paths; this step only inventories it.

Generation-1 v4 calibration, artifacts candidates, .quality-tmp temporaries, docs/release-evidence reviews, tests/golden regression evidence, authoring mirrors and unreferenced review originals stay outside the product pack; non_product_roots records the machine-readable boundary. Formally loaded or verified reviewed-garments and source-bound-exasperated data remains included.

Independent download is a design requirement from inception. The public MoHan release page carries the MoHan and Lin Keyun character packs under CC BY-NC-ND 4.0. Paid DLC uses the same license; its relationship to a character pack remains an owner decision. The engine and art tool use MIT. Existing user settings and appearance approvals retain their scope.

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`

## 日本語

この実測一覧は今後の分離に向け既存の内容を列挙します。主視点 24 枚、主要レイヤー 600 枚、派生画像 234 枚です。内訳は瞬き 24、可視の手 8、完全表情フレーム 156、置換マスク 13、口腔マスク 33 です。

製品データは実ファイル 1726 個です。実行時に 1678 個、製品自己テストに landmarks と hands のメタデータ 48 個が必要です。外観アーカイブ 2 個に含まれる 1547 メンバーは別途列挙し、実ファイル数には重複計上しません。除外ファイル 1109 個とコード位置ファイル 22 個も記録します。下表は実行時の実ファイルのみを数えます。

| 分類 | ファイル数 |
|---|---:|
| 正式外観パック (`appearance_pack`) | 3 |
| 外観置換マスク (`appearance_replacement_mask`) | 13 |
| 衣装の輪郭 (`appearance_silhouette`) | 19 |
| 身体の重ね画像 (`body_overlay`) | 15 |
| キャラクター外観の既定値 (`character_appearance_defaults`) | 2 |
| キャラクターの台詞とイベントデータ (`character_dialogue_data`) | 10 |
| キャラクターの表情状態目録 (`character_expression_catalog`) | 2 |
| キャラクターライセンス通知 (`character_license_notice`) | 2 |
| キャラクターの身元と人格データ (`character_persona_data`) | 10 |
| キャラクターのリグデータ (`character_rig_data`) | 2 |
| キャラクターの実行時素材バインドデータ (`character_runtime_binding_data`) | 2 |
| キャラクターの実行時台詞データ (`character_runtime_dialogue_data`) | 2 |
| キャラクターの UI 識別データ (`character_ui_identifier_data`) | 2 |
| キャラクターの音声設定データ (`character_voice_data`) | 2 |
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

正式パック内には衣装 2、髪型 2、髪飾り 1、メイク 1 項目があります。差分と四言語の名称は appearance_catalog に記録します。

実内容の規則により 22 ソースファイルを検出しました。抽出またはパラメータ化が必要なのは 4、製品シェルで保持可能なのは 18 ファイルです。旧一覧のうち 64 ファイルは実内容の証拠がない人工確認専用の候補であり、進捗には数えません。各証拠に行番号、内容、規則名を保存します。

画像、JSON、正式な外観アーカイブ 2 個はデータです。髪型と髪飾りはアーカイブ、主要レイヤー、正式な衣装内で列挙します。移動時には読込先の変更も必要で、この段階は一覧作成のみです。

v4 の第一世代校正、artifacts の候補、.quality-tmp の一時出力、docs/release-evidence の審査証拠、tests/golden の回帰証拠、制作ミラー、未参照の審査原画は製品パックに含めません。機械可読の境界は non_product_roots に記録します。reviewed-garments と source-bound-exasperated の正式に読込または検証するデータは含めます。

独立ダウンロードは当初からの設計要件です。墨寒と林可芸のキャラクターパックは墨寒プロジェクトの公開ページで公開し、素材と有料 DLC には CC BY-NC-ND 4.0 を適用します。DLC とキャラクターパックの関係は所有者の決定待ちです。エンジンと素材管理ツールは MIT を採用し、既存の設定と外観承認の範囲を維持します。

`mohan-inventory.json` · `python tools/build_character_inventory.py --check`
