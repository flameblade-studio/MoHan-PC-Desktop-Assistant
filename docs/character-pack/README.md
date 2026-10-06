# 角色包格式與驗證／角色包格式与验证／Character Pack Format and Validation／キャラクターパック形式と検証

## 繁體中文

角色包是一份可以單獨下載的「角色行李箱」，把角色身分、資料清冊與權利說明放在一起。驗證器會確認行李箱完整、符合引擎版本，並安全拒絕可疑內容。墨寒仍由原產品提供原有體驗；本階段只新增格式與獨立驗證工具。可獨立下載是格式能力，公開、私有、素材授權與 DLC 關係依擁有者決定。

### 入口與身分

v1 使用 `flameblade.character-pack.v1`，資料夾與 ZIP 根目錄都放 `manifest.json`。採 UTF-8 JSON，鍵值唯一，物件鍵順序自由；每一層拒絕未知或缺少的欄位。`components`、`dependencies` 與 `signature` 可省略；其他頂層欄位必填。陣列順序保留，字串大小寫依契約比對。

`pack_id` 與 `character.id` 是 1 至 128 字元的小寫 ASCII 識別碼，首尾限英數，中間可用句點、底線與連字號。`pack_version` 是三段版本，各段最多 9 位 ASCII 數字，零以外無前導零，首版只接受穩定版。`display_names` 恰含 `zh-TW`、`zh-CN`、`en`、`ja-JP`。`character` 恰含 `id`、`canonical_name`、`aliases`；名稱與別名為非空文字，上限 160 字元，別名大小寫折疊後唯一，允許空陣列。

### 引擎與依賴

`engine_compatibility` 恰含 `api_version`、`min_engine_version`、`max_engine_version_exclusive`、`required_features`。API 是正整數；版本範圍下限包含、上限排除，且下限小於上限。必要功能識別碼採相同字元規則、上限 64 字元且唯一；驗證時由呼叫端明確提供目前版本、API 與功能。布林值不當成整數。

可選 `dependencies` 是陣列，每筆恰含 `id`、`kind`、`min_version`、`max_version_exclusive`、`required`。ID 唯一，種類為 `outfit_pack` 或 `dlc`，版本採同一範圍規則，必要旗標為布林值。這只表達關係；本階段不下載、安裝或解析依賴，DLC 的授權與角色歸屬另行決定。

### 權利與散布

`distribution` 恰含 `standalone_downloadable`、`access`、`redistribution`，首項必須為 true。存取狀態為 `public`、`private`、`owner_decision_pending`；再散布狀態為 `allowed`、`prohibited`、`owner_decision_pending`。這些是宣告，驗證成功不代表發布授權。

`licenses` 恰含 `program_data`、`character_art`、`persona_dialogue`、`voice`，即使某類目前無檔案也要完整宣告。每類恰含 `status`、`rights_holder`、`license_expression`、`notice_path`。狀態接受 `declared_license`、`all_rights_reserved`、`owner_decision_pending`；權利人須為非空文字，上限 500 字元。已宣告授權須附非空授權表達式，上限 500 字元，可使用 SPDX 或 LicenseRef；其餘狀態的表達式為 null。說明文件路徑可為 null，有值時必須列入檔案清冊。工具核對完整性，授權的法律效力與發布資格由擁有者審定。

### 檔案、來源與核准

`files` 是非空完整清冊，每筆恰含 `path`、`sha256`、`bytes`、`media_type`、`license_component`。路徑為 NFC 相對 POSIX 路徑，上限 512 字元；SHA-256 為 64 位小寫十六進位；長度是非負整數；媒體類型採小寫 type/subtype，各段最長 64 字元；權利分類引用上述四類之一。入口清單不列自身，其他檔案皆須列入。重複、大小寫衝突、缺檔、額外檔案、位元組長度或雜湊不符皆拒絕。

`source_refs` 必須為非空陣列，`approval_refs` 可為空；每筆恰含 `path`、`sha256`、`scope`。引用檔案必須列入清冊且雜湊一致，範圍文字上限 500 字元，各陣列內路徑唯一。核准沿原有範圍有效，不能推論成整包散布許可。可引用經核定的摘要收據；完整私人證據是否隨包由擁有者決定。

可選 `components` 是既有子格式的具型別入口。每筆恰含 `id`、`kind`、`schema`、`path`、`sha256`、`required`、`body_profile`；元件 ID 與路徑各自唯一，路徑與雜湊必須對上 `files`。種類可為 body profile、全身／半身 rig、表情 manifest、服裝包、姿勢包、人格、台詞、聲音設定、UI 素材或回歸 manifest。會影響身形的元件必須以 ID 與正整數版本綁定 body profile，且同一包的非 null 綁定必須完全一致；其他元件可填 null。`schema` 點名應使用的既有子格式與版本，例如 `mohan-outfit-pack.v2` 或 `mohan.complete-expression-manifest.v1`；外層驗證器只驗證引用，真正載入時仍須交給已註冊的子格式驗證器，未知子 schema 必須拒絕。

現有 `.mohan-outfit` v2、`mohan.complete-expression-manifest.v1`、`mohan.complete-halfbody-expressions.v1`、`mohan-body-v2` 與來源、建置、放置、核准紀錄可原樣保存在清冊中。本驗證器驗證外層契約與檔案位元組；子格式、圖片尺寸與模式、素體、表情能力及 352 格外觀驗收仍由既有檢查負責。檔名副檔名限制用於資料包入口，任何載入器也須保持資料模式，避免執行包內內容。

### 整包雜湊與簽章

`package_hash` 是邏輯整包 SHA-256，資料夾與 ZIP 可得到相同值。移除頂層 `package_hash`、`signature`，其餘清單用 Python JSON 規則排序鍵、無空白分隔、直接輸出 Unicode、拒絕非有限數字，再以 UTF-8 編碼。雜湊輸入是 ASCII schema 加一個零位元組再接該 JSON。每個 payload 另行驗證雜湊，所以所有宣告與檔案位元組都受涵蓋；ZIP 容器與清單空白不受涵蓋。各陣列順序會影響整包雜湊。

可選 `signature` 為 null 或恰含 `algorithm`、`key_id`、`value` 的物件。演算法只接受 `ed25519`，值為 canonical Base64 編碼的 64 位元組簽章；鍵 ID 是 1 至 128 字元 ASCII 英數識別碼，中間可含句點、底線、冒號、連字號。簽章訊息是整包雜湊的原始 32 位元組。簽章存在時必須注入可信驗證函式，回傳 true 才通過；缺少驗證函式、false 或例外均拒絕。未簽章包可通過完整性驗證，並回報簽章 absent；這不證明發行者身分。

### 安全與資源上限

| 項目 | 預設上限 |
|---|---|
| ZIP 容器 | 256 MiB |
| ZIP 中央目錄 metadata | 8 MiB |
| 入口清單 | 1 MiB |
| 單一 payload | 64 MiB |
| 清單與解壓後 payload 合計 | 512 MiB |
| 目錄或 ZIP 項目數，含目錄 | 4096 |
| 單成員解壓長度對壓縮長度比例 | 100 |

`ValidationLimits` 允許呼叫端調整正整數上限；依實際大小與串流讀取雙重檢查，ZIP 不解壓到磁碟。拒絕絕對路徑、父目錄跳脫、反斜線、空段、點段、Windows 保留名與特殊字元、尾端點或空白、symlink、junction、特殊檔案、加密成員及常見執行檔副檔名。ZIP 目錄項允許尾端斜線且必須無 payload。檢驗中的資料夾須保持唯讀且不受其他行程修改；本工具不建立防止外部並行置換的作業系統快照。

ZIP 建立記憶體索引前，先串流核對中央目錄的實際項目數、宣告數與範圍，並套用 metadata 大小上限。首版接受單磁碟、一般結尾紀錄的 ZIP；ZIP64 結尾紀錄與跨磁碟封包會被拒絕，小型封包的 ZIP64 本地標頭可接受。ZIP 名稱須符合宣告的檔案或目錄類型；檔案也不得成為其他項目的父目錄，包括大小寫折疊後的衝突。Windows 保留裝置名稱檢查涵蓋 COM 與 LPT 的上標數字 ¹、²、³。

ZIP 大小、預檢與內容讀取使用同一個已開啟檔案，避免預檢後因路徑置換而讀取另一個 ZIP。資料夾讀取器記錄盤點時的檔案身分，並在讀取前後核對實際開啟的 regular-file handle；置換檔案或祖先路徑會被拒絕。資料夾與 ZIP 都須在驗證期間保持不被並行改寫。

資料夾逐項串流列舉，項目數超過上限一筆就停止，避免先把大量目錄項目收集到記憶體。

### API 與最小範例

`validate_character_pack` 回傳 `CharacterPackValidationResult`，包含 valid、來源種類、已驗證 manifest、問題碼與路徑、成功檢查檔數與位元組數、邏輯雜湊及簽章狀態。失敗不回傳 manifest，停止於第一個問題；失敗時計數僅保留已完成階段的數據。可搜尋的問題碼包括 `unsupported_schema`、`missing_file`、`file_hash_mismatch`、`unsafe_path`、`suspicious_compression_ratio`、`file_too_large`、`license_incomplete`、`incompatible_engine`。工具只讀本機資料，未接入產品執行期。

完整有效清單見 [最小清單](minimal-manifest.json)，對應合成資料見 [來源資料](example-source.json)。下例由專案根目錄執行，複製兩份合成資料建立最小包；例中權利與公開決策均保留未決定。

```python
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from domain.character_pack.validation import validate_character_pack

examples = Path("docs/character-pack")
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "provenance").mkdir()
    (root / "manifest.json").write_text(
        (examples / "minimal-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "provenance/source.json").write_bytes(
        (examples / "example-source.json").read_bytes()
    )
    result = validate_character_pack(root, engine_version="1.2.3")
    assert result.valid
```

## 简体中文

角色包是一份可以单独下载的“角色行李箱”，把角色身份、数据清单与权利说明放在一起。验证器确认行李箱完整、符合引擎版本，并安全拒绝可疑内容。墨寒仍由原产品提供原有体验；本阶段只新增格式与独立验证工具。可独立下载是格式能力，公开、私有、素材授权与 DLC 关系由所有者决定。

### 入口与身份

v1 使用 `flameblade.character-pack.v1`，文件夹与 ZIP 根目录都放 `manifest.json`。采用 UTF-8 JSON，键值唯一，对象键顺序自由；每一层拒绝未知或缺少的字段。`components`、`dependencies` 与 `signature` 可省略；其他顶层字段必填。数组顺序保留，字符串大小写依契约比较。

`pack_id` 与 `character.id` 是 1 至 128 字符的小写 ASCII 标识码，首尾限字母数字，中间可用句点、下划线与连字符。`pack_version` 是三段版本，各段最多 9 位 ASCII 数字，零以外无前导零，首版只接受稳定版。`display_names` 恰含 `zh-TW`、`zh-CN`、`en`、`ja-JP`。`character` 恰含 `id`、`canonical_name`、`aliases`；名称与别名为非空文本，上限 160 字符，别名大小写折叠后唯一，允许空数组。

### 引擎与依赖

`engine_compatibility` 恰含 `api_version`、`min_engine_version`、`max_engine_version_exclusive`、`required_features`。API 是正整数；版本范围包含下限、排除上限，且下限小于上限。必要功能标识码采用相同字符规则、上限 64 字符且唯一；验证时由调用端明确提供当前版本、API 与功能。布尔值不当作整数。

可选 `dependencies` 是数组，每项恰含 `id`、`kind`、`min_version`、`max_version_exclusive`、`required`。ID 唯一，种类为 `outfit_pack` 或 `dlc`，版本采用同一范围规则，必要标记为布尔值。这只表达关系；本阶段不下载、安装或解析依赖，DLC 的授权与角色归属另行决定。

### 权利与分发

`distribution` 恰含 `standalone_downloadable`、`access`、`redistribution`，首项必须为 true。访问状态为 `public`、`private`、`owner_decision_pending`；再分发状态为 `allowed`、`prohibited`、`owner_decision_pending`。这些是声明，验证成功不代表发布授权。

`licenses` 恰含 `program_data`、`character_art`、`persona_dialogue`、`voice`，即使某类目前无文件也要完整声明。每类恰含 `status`、`rights_holder`、`license_expression`、`notice_path`。状态接受 `declared_license`、`all_rights_reserved`、`owner_decision_pending`；权利人须为非空文本，上限 500 字符。已声明授权须附非空授权表达式，上限 500 字符，可使用 SPDX 或 LicenseRef；其余状态的表达式为 null。说明文件路径可为 null，有值时必须列入文件清单。工具核对完整性，授权的法律效力与发布资格由所有者审定。

### 文件、来源与批准

`files` 是非空完整清单，每项恰含 `path`、`sha256`、`bytes`、`media_type`、`license_component`。路径为 NFC 相对 POSIX 路径，上限 512 字符；SHA-256 为 64 位小写十六进制；长度是非负整数；媒体类型采用小写 type/subtype，各段最长 64 字符；权利分类引用上述四类之一。入口清单不列自身，其他文件均须列入。重复、大小写冲突、缺失、多余文件、字节长度或哈希不符均拒绝。

`source_refs` 必须为非空数组，`approval_refs` 可为空；每项恰含 `path`、`sha256`、`scope`。引用文件必须列入清单且哈希一致，范围文本上限 500 字符，各数组内路径唯一。批准沿原有范围有效，不能推断成整包分发许可。可引用经批准的摘要记录；完整私人证据是否随包由所有者决定。

可选 `components` 是现有子格式的强类型入口。每项恰含 `id`、`kind`、`schema`、`path`、`sha256`、`required`、`body_profile`；组件 ID 与路径分别唯一，路径和哈希必须与 `files` 对应。种类可为 body profile、全身／半身 rig、表情 manifest、服装包、姿势包、人格、台词、声音设置、UI 素材或回归 manifest。影响体型的组件必须用 ID 与正整数版本绑定 body profile，并且同一包内所有非 null 绑定必须完全一致；其他组件可填 null。`schema` 指明应使用的现有子格式与版本，例如 `mohan-outfit-pack.v2` 或 `mohan.complete-expression-manifest.v1`；外层验证器只验证引用，实际加载时仍须交给已注册的子格式验证器，未知子 schema 必须拒绝。

现有 `.mohan-outfit` v2、`mohan.complete-expression-manifest.v1`、`mohan.complete-halfbody-expressions.v1`、`mohan-body-v2` 与来源、构建、放置、批准记录可原样保存在清单中。本验证器验证外层契约与文件字节；子格式、图片尺寸与模式、素体、表情能力及 352 格外观验收仍由既有检查负责。文件扩展名限制用于数据包入口，任何加载器也须保持数据模式，避免执行包内内容。

### 整包哈希与签名

`package_hash` 是逻辑整包 SHA-256，文件夹与 ZIP 可得到相同值。移除顶层 `package_hash`、`signature`，其余清单用 Python JSON 规则排序键、无空白分隔、直接输出 Unicode、拒绝非有限数字，再以 UTF-8 编码。哈希输入是 ASCII schema 加一个零字节再接该 JSON。每个 payload 另行验证哈希，所以所有声明与文件字节都受覆盖；ZIP 容器与清单空白不受覆盖。各数组顺序会影响整包哈希。

可选 `signature` 为 null 或恰含 `algorithm`、`key_id`、`value` 的对象。算法只接受 `ed25519`，值为 canonical Base64 编码的 64 字节签名；键 ID 是 1 至 128 字符 ASCII 字母数字标识码，中间可含句点、下划线、冒号、连字符。签名消息是整包哈希的原始 32 字节。签名存在时必须注入可信验证函数，返回 true 才通过；缺少验证函数、false 或异常均拒绝。未签名包可通过完整性验证，并报告签名 absent；这不证明发行者身份。

### 安全与资源上限

| 项目 | 默认上限 |
|---|---|
| ZIP 容器 | 256 MiB |
| ZIP 中央目录 metadata | 8 MiB |
| 入口清单 | 1 MiB |
| 单个 payload | 64 MiB |
| 清单与解压后 payload 合计 | 512 MiB |
| 目录或 ZIP 项目数，含目录 | 4096 |
| 单成员解压长度对压缩长度比例 | 100 |

`ValidationLimits` 允许调用端调整正整数上限；根据实际大小与流式读取双重检查，ZIP 不解压到磁盘。拒绝绝对路径、父目录跳脱、反斜线、空段、点段、Windows 保留名称与特殊字符、末尾点或空格、symlink、junction、特殊文件、加密成员及常见可执行文件扩展名。ZIP 目录项允许末尾斜线且必须无 payload。检验中的文件夹须保持只读且不受其他进程修改；本工具不建立防止外部并行替换的操作系统快照。

ZIP 建立内存索引前，先流式核对中央目录的实际项目数、声明数与范围，并应用 metadata 大小上限。首版接受单磁盘、普通结尾记录的 ZIP；ZIP64 结尾记录与跨磁盘包会被拒绝，小型包的 ZIP64 本地头可接受。ZIP 名称须符合声明的文件或目录类型；文件也不得成为其他项目的父目录，包括大小写折叠后的冲突。Windows 保留设备名称检查涵盖 COM 与 LPT 的上标数字 ¹、²、³。

ZIP 大小、预检与内容读取使用同一个已打开文件，避免预检后因路径替换而读取另一个 ZIP。文件夹读取器记录盘点时的文件身份，并在读取前后核对实际打开的 regular-file handle；替换文件或祖先路径会被拒绝。文件夹与 ZIP 都须在验证期间保持不被并行改写。

文件夹逐项流式枚举，项目数超过上限一项就停止，避免先把大量目录项目收集到内存。

### API 与最小示例

`validate_character_pack` 返回 `CharacterPackValidationResult`，包含 valid、来源类型、已验证 manifest、问题码与路径、成功检查文件数与字节数、逻辑哈希及签名状态。失败不返回 manifest，停止于首个问题；失败时计数仅保留已完成阶段的数据。可搜索的问题码包括 `unsupported_schema`、`missing_file`、`file_hash_mismatch`、`unsafe_path`、`suspicious_compression_ratio`、`file_too_large`、`license_incomplete`、`incompatible_engine`。工具只读本地数据，未接入产品运行时。

完整有效清单见 [最小清单](minimal-manifest.json)，对应合成数据见 [来源数据](example-source.json)。下例从项目根目录执行，复制两份合成数据建立最小包；例中权利与公开决策均保留未决定。

```python
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from domain.character_pack.validation import validate_character_pack

examples = Path("docs/character-pack")
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "provenance").mkdir()
    (root / "manifest.json").write_text(
        (examples / "minimal-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "provenance/source.json").write_bytes(
        (examples / "example-source.json").read_bytes()
    )
    result = validate_character_pack(root, engine_version="1.2.3")
    assert result.valid
```

## English

A character pack is a downloadable suitcase containing a character's identity, file inventory, and rights declarations. The validator checks completeness and engine compatibility and safely rejects suspicious content. MoHan continues to provide its existing experience through the original product; this phase adds a format and a standalone validator. Standalone download is a format capability; the owner decides public or private access, asset licensing, and DLC relationships.

### Entry point and identity

v1 uses `flameblade.character-pack.v1`, with `manifest.json` at the directory or ZIP root. Use UTF-8 JSON with unique keys and arbitrary object key order; unknown or missing fields are rejected at every level. `components`, `dependencies`, and `signature` may be omitted; all other top-level fields are required. Array order is preserved, and string case follows the contract.

`pack_id` and `character.id` are lowercase ASCII identifiers of 1 to 128 characters, with alphanumeric endpoints and dots, underscores, or hyphens inside. `pack_version` has three numeric components of at most 9 ASCII digits each, with no leading zero except zero itself; the first version accepts stable releases only. `display_names` contains exactly `zh-TW`, `zh-CN`, `en`, and `ja-JP`. `character` contains exactly `id`, `canonical_name`, and `aliases`; names and aliases are nonempty text limited to 160 characters, aliases are unique after case folding, and an empty array is allowed.

### Engine and dependencies

`engine_compatibility` contains exactly `api_version`, `min_engine_version`, `max_engine_version_exclusive`, and `required_features`. The API is a positive integer; version ranges include the lower bound and exclude the upper bound, with a strictly smaller lower bound. Required feature identifiers use the same character rules, are unique, and allow at most 64 characters; callers explicitly supply their engine version, API, and features. Booleans are not treated as integers.

Optional `dependencies` is an array whose entries contain exactly `id`, `kind`, `min_version`, `max_version_exclusive`, and `required`. IDs are unique, kinds are `outfit_pack` or `dlc`, version ranges follow the same rules, and the required flag is boolean. This only declares relationships; this phase does not download, install, or resolve dependencies. DLC licensing and character ownership remain separate decisions.

### Rights and distribution

`distribution` contains exactly `standalone_downloadable`, `access`, and `redistribution`, with the first value set to true. Access states are `public`, `private`, and `owner_decision_pending`; redistribution states are `allowed`, `prohibited`, and `owner_decision_pending`. These are declarations; successful validation does not grant publication permission.

`licenses` contains exactly `program_data`, `character_art`, `persona_dialogue`, and `voice`, including categories with no current files. Each category contains exactly `status`, `rights_holder`, `license_expression`, and `notice_path`. States are `declared_license`, `all_rights_reserved`, and `owner_decision_pending`; the rights holder is nonempty text limited to 500 characters. A declared license requires a nonempty expression of at most 500 characters, which can use SPDX or LicenseRef; other states use null expressions. Notice paths may be null and otherwise must appear in the file inventory. The tool checks completeness; the owner reviews legal validity and publication eligibility.

### Files, sources, and approvals

`files` is a complete nonempty inventory; entries contain exactly `path`, `sha256`, `bytes`, `media_type`, and `license_component`. Paths are NFC relative POSIX paths limited to 512 characters; SHA-256 uses 64 lowercase hexadecimal digits; sizes are nonnegative integers; media types use lowercase type/subtype syntax with each part limited to 64 characters; rights categories name one of the four categories above. The entry manifest excludes itself; every other file is listed. Duplicates, case collisions, missing or extra files, and byte count or hash mismatches are rejected.

`source_refs` is a nonempty array; `approval_refs` may be empty. Each entry contains exactly `path`, `sha256`, and `scope`. Referenced files must be inventoried with matching hashes, scopes are limited to 500 text characters, and paths are unique within each array. Approvals retain their original scope and do not imply whole-package distribution permission. Approved summary receipts may be referenced; the owner decides whether complete private evidence accompanies a pack.

Optional `components` entries are typed entry points to existing child formats. Each contains exactly `id`, `kind`, `schema`, `path`, `sha256`, `required`, and `body_profile`; component IDs and paths are independently unique, and each path and hash must match `files`. Kinds cover body profiles, full-body or half-body rigs, expression manifests, outfit packs, pose packs, persona, dialogue, voice profiles, UI assets, and regression manifests. Components that affect body geometry require a body-profile ID and positive integer version, and every non-null binding in one pack must match exactly; other components may use null. `schema` identifies the registered child format and version, such as `mohan-outfit-pack.v2` or `mohan.complete-expression-manifest.v1`. The envelope validator verifies the reference only; loading must still invoke the registered child validator and reject an unsupported child schema.

Existing `.mohan-outfit` v2, `mohan.complete-expression-manifest.v1`, `mohan.complete-halfbody-expressions.v1`, `mohan-body-v2`, and source, build, placement, and approval records can remain unchanged in the inventory. This validator checks the outer contract and file bytes; existing checks still own child formats, image dimensions and modes, body profiles, expression capabilities, and the 352-cell appearance gate. Extension restrictions apply to the data package entry point; any loader must also preserve data-only handling to avoid executing packaged content.

### Package hash and signature

`package_hash` is a logical package SHA-256 shared by equivalent directories and ZIPs. Remove top-level `package_hash` and `signature`; serialize the rest using Python JSON rules with sorted keys, compact separators, direct Unicode, and nonfinite numbers rejected, then encode as UTF-8. Hash the ASCII schema followed by one zero byte and that JSON. Every payload hash is separately verified, covering all declarations and file bytes; ZIP container bytes and manifest whitespace are excluded. Array order affects the package hash.

Optional `signature` is null or an object containing exactly `algorithm`, `key_id`, and `value`. Only `ed25519` is accepted, with canonical Base64 encoding of a 64-byte signature; the key ID is an ASCII alphanumeric identifier of 1 to 128 characters, allowing dots, underscores, colons, and hyphens inside. The signed message is the raw 32-byte package digest. Signed packs require an injected trusted verifier returning true; missing verifiers, false, or exceptions are rejected. Unsigned packs can pass integrity validation with signature status absent; this does not authenticate their publisher.

### Safety and resource ceilings

| Item | Default ceiling |
|---|---|
| ZIP container | 256 MiB |
| ZIP central-directory metadata | 8 MiB |
| Entry manifest | 1 MiB |
| Individual payload | 64 MiB |
| Manifest plus expanded payload | 512 MiB |
| Directory or ZIP entries, including directories | 4096 |
| Per-member expanded to compressed size ratio | 100 |

`ValidationLimits` lets callers set positive integer ceilings; actual sizes and bounded stream reads are checked, and ZIPs are never extracted to disk. Reject absolute paths, parent traversal, backslashes, empty or dot segments, Windows reserved names and special characters, trailing dots or spaces, symlinks, junctions, special files, encrypted members, and common executable extensions. ZIP directory entries may have trailing slashes and must have no payload. Directories being validated must remain read-only and untouched by other processes; the tool does not create an operating-system snapshot against concurrent external replacement.

Before allocating the ZIP index, stream through the central directory to check actual and declared entry counts and bounds, and enforce the metadata size limit. v1 accepts single-disk ZIPs with classic end records. ZIP64 end records and multi-disk packages are rejected; local ZIP64 headers in small packages are accepted. ZIP names must agree with their declared file or directory types. A file must also remain separate from the parent directories of other entries, including case-folded collisions. Windows device-name checks cover COM and LPT with superscript digits ¹, ², and ³.

ZIP size checks, preflight, and payload reads share one open file so replacing the path after preflight cannot select another ZIP. The directory reader records inventoried file identity and checks the opened regular-file handle before and after each read; replacing a file or ancestor path is rejected. Both directories and ZIPs must remain untouched by concurrent writers during validation.

Directory enumeration streams entries and stops after one entry beyond the ceiling, avoiding allocation of a complete directory listing before enforcing the limit.

### API and minimal example

`validate_character_pack` returns `CharacterPackValidationResult`, containing valid, source kind, a validated manifest, issue codes and paths, successfully checked file and byte counts, logical hash, and signature status. Failure returns no manifest and stops at the first issue; failure counts retain only completed-stage data. Searchable codes include `unsupported_schema`, `missing_file`, `file_hash_mismatch`, `unsafe_path`, `suspicious_compression_ratio`, `file_too_large`, `license_incomplete`, and `incompatible_engine`. The tool reads local data and is not connected to the product runtime.

See the complete valid [minimal manifest](minimal-manifest.json) and its [synthetic source data](example-source.json). Run the following from the repository root to copy both synthetic files into a minimal pack; rights and publication decisions remain pending in this example.

```python
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from domain.character_pack.validation import validate_character_pack

examples = Path("docs/character-pack")
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "provenance").mkdir()
    (root / "manifest.json").write_text(
        (examples / "minimal-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "provenance/source.json").write_bytes(
        (examples / "example-source.json").read_bytes()
    )
    result = validate_character_pack(root, engine_version="1.2.3")
    assert result.valid
```

## 日本語

キャラクターパックは、キャラクターの身元、ファイル一覧、権利の宣言をまとめた、単独でダウンロードできる「荷物箱」です。検証器は完全性とエンジンの互換性を確認し、疑わしい内容を安全に拒否します。墨寒の既存体験は元の製品が引き続き提供し、この段階では形式と独立した検証器を追加します。単独ダウンロードは形式の能力であり、公開・非公開、素材のライセンス、DLC の関係は所有者が決めます。

### 入口と身元

v1 は `flameblade.character-pack.v1` を使用し、フォルダーまたは ZIP のルートに `manifest.json` を置きます。UTF-8 JSON を使用し、キーは一意、オブジェクトのキー順は自由です。各階層で未知または不足するフィールドを拒否します。`components`、`dependencies`、`signature` は省略でき、他の最上位フィールドは必須です。配列の順序を保持し、文字列の大小文字は契約に従って比較します。

`pack_id` と `character.id` は 1～128 文字の小文字 ASCII 識別子で、先頭と末尾は英数字、内部はピリオド、下線、ハイフンも使えます。`pack_version` は三つの数値要素からなり、各要素は最大 9 桁の ASCII 数字、ゼロ以外に先頭のゼロを許しません。初版は安定版のみを受け入れます。`display_names` は `zh-TW`、`zh-CN`、`en`、`ja-JP` を正確に含みます。`character` は `id`、`canonical_name`、`aliases` のみを含みます。名前と別名は空でない最大 160 文字のテキストで、別名は大小文字を折り畳んだ後に一意、空の配列も許可します。

### エンジンと依存関係

`engine_compatibility` は `api_version`、`min_engine_version`、`max_engine_version_exclusive`、`required_features` のみを含みます。API は正の整数、バージョン範囲は下限を含み上限を除外し、下限は上限より小さくなります。必須機能の識別子は同じ文字規則を使用し、最大 64 文字で一意です。呼び出し側が現在のバージョン、API、機能を明示します。真偽値は整数として扱いません。

省略可能な `dependencies` は配列で、各項目は `id`、`kind`、`min_version`、`max_version_exclusive`、`required` のみを含みます。ID は一意、種類は `outfit_pack` または `dlc`、バージョン範囲は同じ規則、必須フラグは真偽値です。これは関係を宣言するだけで、この段階では依存先のダウンロード、インストール、解決を行いません。DLC のライセンスとキャラクターへの帰属は別途決定します。

### 権利と配布

`distribution` は `standalone_downloadable`、`access`、`redistribution` のみを含み、最初の値は true です。アクセス状態は `public`、`private`、`owner_decision_pending`、再配布状態は `allowed`、`prohibited`、`owner_decision_pending` です。これらは宣言であり、検証成功によって公開の許可が与えられることはありません。

`licenses` は `program_data`、`character_art`、`persona_dialogue`、`voice` を正確に含み、現時点でファイルがない分類にも完全な宣言が必要です。各分類は `status`、`rights_holder`、`license_expression`、`notice_path` のみを含みます。状態は `declared_license`、`all_rights_reserved`、`owner_decision_pending` を受け入れ、権利者は空でない最大 500 文字のテキストです。宣言済みライセンスには空でない最大 500 文字の式が必要で、SPDX または LicenseRef を使えます。他の状態は null の式を使います。説明文書のパスは null にでき、値がある場合は一覧に記載します。ツールは完全性を確認し、法的有効性と公開資格は所有者が審査します。

### ファイル、出典、承認

`files` は空でない完全な一覧で、各項目は `path`、`sha256`、`bytes`、`media_type`、`license_component` のみを含みます。パスは最大 512 文字の NFC 相対 POSIX パス、SHA-256 は 64 桁の小文字十六進数、長さは非負整数です。メディア型は小文字の type/subtype 構文で各部分は最大 64 文字、権利分類は上記の四分類の一つを指定します。入口の一覧は自身を除き、他の全ファイルを記載します。重複、大小文字の衝突、不足、余分なファイル、バイト数やハッシュの不一致を拒否します。

`source_refs` は空でない配列、`approval_refs` は空にできます。各項目は `path`、`sha256`、`scope` のみを含みます。参照ファイルは一覧に含まれ、ハッシュが一致し、範囲の説明は最大 500 文字、各配列内のパスは一意です。承認は元の範囲内で有効であり、パック全体の配布許可を意味しません。承認された要約記録を参照でき、完全な非公開証拠を同梱するかは所有者が決定します。

省略可能な `components` は、既存の子形式を型付きで参照する入口です。各項目は `id`、`kind`、`schema`、`path`、`sha256`、`required`、`body_profile` のみを含みます。コンポーネント ID とパスはそれぞれ一意で、パスとハッシュは `files` と一致する必要があります。種類は body profile、全身／半身 rig、表情 manifest、衣装パック、ポーズパック、人格、台詞、音声設定、UI 素材、回帰 manifest です。体型に影響するコンポーネントは body profile の ID と正の整数バージョンを必須とし、同じパック内の null でない指定はすべて完全に一致する必要があります。それ以外は null を使えます。`schema` は `mohan-outfit-pack.v2` や `mohan.complete-expression-manifest.v1` のように既存の子形式と版を指定します。外側の検証器は参照だけを検証し、実際の読み込みでは登録済みの子形式検証器を呼び出し、未対応の子 schema を拒否します。

既存の `.mohan-outfit` v2、`mohan.complete-expression-manifest.v1`、`mohan.complete-halfbody-expressions.v1`、`mohan-body-v2`、出典、ビルド、配置、承認記録は変更せず一覧に保存できます。この検証器は外側の契約とファイルのバイト列を検証し、子形式、画像の寸法とモード、素体、表情能力、352 セルの外観検収は既存の検査が担当します。拡張子の制限はデータパックの入口に適用し、各ローダーもデータとして扱い、内容を実行しない設計を維持します。

### パック全体のハッシュと署名

`package_hash` は論理パック全体の SHA-256 で、同等のフォルダーと ZIP は同じ値になります。最上位の `package_hash` と `signature` を除き、残りを Python JSON の規則でキー順に並べ、空白なしの区切り、Unicode の直接出力、非有限数値の拒否を適用して UTF-8 にします。ASCII schema、一つのゼロバイト、この JSON を連結してハッシュを計算します。各 payload のハッシュも別途検証し、全宣言とファイルのバイト列を対象にします。ZIP 容器と一覧の空白は対象外です。配列の順序は全体ハッシュに影響します。

省略可能な `signature` は null、または `algorithm`、`key_id`、`value` のみを含むオブジェクトです。`ed25519` のみを受け入れ、値は 64 バイト署名の canonical Base64 です。キー ID は 1～128 文字の ASCII 英数字識別子で、内部にピリオド、下線、コロン、ハイフンを使えます。署名対象は全体ハッシュの生の 32 バイトです。署名がある場合は信頼できる検証関数を注入し、true の場合だけ合格します。関数の不足、false、例外は拒否します。未署名パックは完全性検証に合格でき、署名状態 absent を返しますが、発行者の身元は証明しません。

### 安全性と資源上限

| 項目 | 既定の上限 |
|---|---|
| ZIP 容器 | 256 MiB |
| ZIP 中央ディレクトリーの metadata | 8 MiB |
| 入口の一覧 | 1 MiB |
| 個別 payload | 64 MiB |
| 一覧と展開後 payload の合計 | 512 MiB |
| ディレクトリーを含むフォルダーまたは ZIP 項目数 | 4096 |
| 各メンバーの展開長と圧縮長の比率 | 100 |

`ValidationLimits` で呼び出し側が正整数の上限を設定できます。実際のサイズと制限付きストリーム読み取りを確認し、ZIP はディスクへ展開しません。絶対パス、親への移動、逆斜線、空または点の区間、Windows の予約名と特殊文字、末尾の点や空白、symlink、junction、特殊ファイル、暗号化メンバー、一般的な実行形式拡張子を拒否します。ZIP のディレクトリー項目は末尾の斜線を許し、payload は空である必要があります。検証対象のフォルダーは読み取り専用で、他のプロセスが変更しない状態を維持します。本ツールは外部からの並行置換を防ぐ OS スナップショットを作成しません。

ZIP のメモリー索引を作る前に、中央ディレクトリーをストリームで読み、実際と宣言上の項目数、範囲、metadata のサイズ上限を確認します。v1 は単一ディスクと通常の終端レコードを持つ ZIP を受け入れます。ZIP64 終端レコードと複数ディスクのパックは拒否し、小型パックの ZIP64 ローカルヘッダーは受け入れます。ZIP の名前は宣言されたファイルまたはディレクトリーの種類と一致する必要があります。大小文字の正規化後も、ファイルが他の項目の親ディレクトリーになる構成を拒否します。Windows の予約デバイス名検査は、COM と LPT の上付き数字 ¹、²、³ も対象にします。

ZIP のサイズ確認、事前検査、内容の読み取りには同じ開いたファイルを使い、検査後のパス置換で別の ZIP を読むことを防ぎます。フォルダー読取器は棚卸し時のファイル識別情報を記録し、各読み取りの前後に実際に開いた regular-file handle を照合します。ファイルまたは祖先パスの置換は拒否されます。検証中は、フォルダーと ZIP の両方を他の処理が書き換えない状態に保ちます。

フォルダーは項目を一つずつ列挙し、上限を一項目超えた時点で停止します。大量の項目を先にメモリーへ集める処理を避けます。

### API と最小例

`validate_character_pack` は `CharacterPackValidationResult` を返し、valid、出典種別、検証済み manifest、問題コードとパス、成功したファイル数とバイト数、論理ハッシュ、署名状態を含みます。失敗時は manifest を返さず最初の問題で停止し、件数は完了済み段階のデータだけを保持します。検索可能なコードには `unsupported_schema`、`missing_file`、`file_hash_mismatch`、`unsafe_path`、`suspicious_compression_ratio`、`file_too_large`、`license_incomplete`、`incompatible_engine` があります。ツールはローカルデータを読み取り、製品の実行時には接続されていません。

有効な完全一覧は [最小一覧](minimal-manifest.json)、対応する合成データは [出典データ](example-source.json) を参照してください。次の例をリポジトリーのルートから実行し、二つの合成ファイルをコピーして最小パックを作成します。この例では権利と公開の決定を保留しています。

```python
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from domain.character_pack.validation import validate_character_pack

examples = Path("docs/character-pack")
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "provenance").mkdir()
    (root / "manifest.json").write_text(
        (examples / "minimal-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "provenance/source.json").write_bytes(
        (examples / "example-source.json").read_bytes()
    )
    result = validate_character_pack(root, engine_version="1.2.3")
    assert result.valid
```
