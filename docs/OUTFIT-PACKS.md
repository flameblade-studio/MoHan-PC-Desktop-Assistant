# 墨寒角色外觀包 ／ 墨寒角色外观包 ／ MoHan Character Appearance Packs ／ 墨寒キャラクター外観パック

## 繁體中文

角色外觀包是單一、自含、可直接上傳與下載的 ZIP 相容 `.mohan-outfit` 容器。使用者只需下載並選取一個檔案；不得有旁附資料夾、外部相依套件、網路下載、外部 URL 或跨包必需引用。每項 PNG、WebP 或安全 SVG 都必須在同一 archive，由 manifest 以 SHA-256、尺寸、anchor、z-order 與穩定 slot 完整引用。未引用、重複、缺漏、越權或危險成員一律拒絕。匯入先完整驗證，再於同一目的目錄原子安裝；失敗不留下半套，也不破壞既有版本。安裝只加入內容，不等於預覽或啟用；套用與保存由 UI 的全域 Save/Cancel 流程控制。

一包可同時包含多件衣裝及色系、髮型、頭飾和配件，也可只含純衣裝、純髮型或純頭飾。穩定選擇槽為 `garment`、`hairstyle`、`headwear`、`weapon`、`handheld`、`jewelry`、`foreground-effect`；各槽以 `category/pack_id/item_id/variant_id` 分開列舉、保存、解析與移除保護，所以長劍／短劍與劍鞘、手持物、珠寶及前景效果可以同時存在並跨包混搭。Manifest 的單一 `accessories` 集合中，每個 item 必須宣告明確 `accessory_kind`。Typed `ensemble` 必須涵蓋全部七槽；衣裝與髮型必須指定同包項目，頭飾及四個配件槽可明確為 `none`。一鍵套用後仍可逐槽改選。Ensemble 只改外觀，不可改臉型、五官、身份或核心提示詞。

衣裝沿用官方 `mohan-body-v1`。官方美術規格為成人女性，168 公分、54 公斤、86/71/62/90 公分，約 C70-equivalent；數值只供官方美術製作與驗收，不是外掛拉伸公式。真正相容性由版本化 rig anchors、masks 與 geometry 判斷。肩頸線、胸廓、腰胯線、四肢比例、膚色和本體輪廓都由核心掌握。外掛只能以 `visible`／`covered` 宣告官方膚色區域，並從 `structured`、`draped`、`stretch`、`loose` 選擇布料行為，不得換臉、換膚色或改身材。

衣裝必須完整覆蓋 v2 的 31 個精確視角：既有七個演出輪廓 `cheek-rest`、`left-neutral`、`front-crossed`、`front-mock-scold`、`front-mock-hit`、`front-eureka`、`front-exasperated`，以及 PoseAtlas 的 24 個正式視角。每個視角都必須有自己的素材、anchor 與遮擋資料；不得以 alias 或舊衣回退冒充。舊 v1 三姿勢包不再載入，必須以官方範本一次升級為完整 v2 包；缺少、增加或拼錯任一視角都整包拒絕。

每個 ensemble 都必須提供 `autonomous_profile`，明確標示適用溫度帶、天氣、墨寒當下心境、場合與排序權重。自主選裝使用單一決策器，遵守手動鎖定、六小時冷卻與雨雪／特殊節日安全優先；沒有完整匹配時維持目前衣裝，不暗中改穿別套。自創新衣與流行趨勢搜尋是分開保存的開關，可能產生雲端費用，只有使用者明確啟用後才可執行。趨勢只能萃取抽象特徵，不能複製或打包第三方照片與設計；生成結果先進隔離區，完成 31 視角、角色身分、手部、遮擋、來源與授權稽核後才可封裝安裝。

自創衣裝預設至少間隔七天，最多保留 16 個已安裝包、5 個待修隔離工作與 6 GiB；使用者可在控制台調整已安裝數量及容量上限。達到上限時停止生成並保留既有內容，絕不自行刪除使用者上傳的包。新衣成功套用後會留下「首次展示待辦」；只有使用者在場、看向墨寒、目前未說話且不在專注／會議／全螢幕狀態時，墨寒才以全身鏡位主動問新衣是否好看。成功說完才標記完成；使用者追問來源時，墨寒可用四語詞庫幽默表示是自己上網尋得靈感並改良，系統提示與內部標記永不朗讀。

髮型的最小穩定 slot 為必要的 `back`、`front`，以及選用但跨全部 silhouette 必須一致的 `side-left`、`side-right`、`bangs`、`bun`、`ponytail`。每一 silhouette 都有自己的 anchor、z-order，並必須選擇核心白名單的 face-occlusion mask、hand occlusion 與 garment/collar occlusion 規則，避免穿臉、穿手或穿衣領。外掛可替換可見髮絲，但不能提供核心頭骨、臉型、眼睛、嘴型、五官、膚色或身份輪廓。

頭飾使用 `headwear` 素材 slot，並必須指定 `crown`、左右 `temple`、左右 `ear` 或 `back-head` attachment point，以及對應的核心安全遮罩。武器可含 `weapon` 與 `sheath` 層，placement 限背部、左右腰側或左右手；每個 silhouette 都必須提供手部、衣裝、髮型遮擋規則及 `back-harness`、`waist-sheath`、左右握持之一的 attachment／握持契約，避免漂浮或穿模。手持物 placement 限左右手，並要求每個 silhouette 的手部遮擋；可承載通用道具，不寫死節慶或角色。珠寶與前景效果各有獨立槽。所有類型都要求四語名稱，順序為繁體中文、簡體中文、英文、日文。

Manifest 的 `source` 必須記錄 `kind`（`original`、`concept`、`reference-derived`）、作者、授權與 `reference_included: false`。參考作品可作靈感紀錄，但參考照片或作品素材不得直接打包。封裝拒絕 Python、JavaScript、EXE、DLL、腳本、絕對／穿越路徑、符號連結、加密成員、解壓炸彈、超限尺寸，以及含 script、事件、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD 或 entity 的 SVG。

刪除使用 typed remove API。內建預設永不可刪；任何正在 active 或 preview 的單項或 ensemble，都必須先切換或還原內建才能刪除。刪除前會再次驗證安全 pack ID、檔名與 archive manifest ID 完全一致，然後只移除該自含單檔，不碰其他包、核心本體或個人資料。刪除後不再出現在清單。不存在 ID、路徑穿越、識別不符與損壞狀態都會 fail closed。若保存設定稍後指向已遺失的包，解析 API 明確回報 `missing` 並維持目前有效外觀；不會崩潰、默默改選、退回舊格式或套用另一個同名外觀。四語刪除確認由 UI 主線負責。

## 简体中文

角色外观包是单一、自包含、可直接上传与下载的 ZIP 兼容 `.mohan-outfit` 容器。用户只需下载并选择一个文件；不得有附带文件夹、外部依赖包、网络下载、外部 URL 或跨包必需引用。每项 PNG、WebP 或安全 SVG 都必须位于同一 archive，并由 manifest 以 SHA-256、尺寸、anchor、z-order 与稳定 slot 完整引用。未引用、重复、缺漏、越权或危险成员一律拒绝。导入先完整验证，再在同一目标目录原子安装；失败不留下半套，也不破坏现有版本。安装只添加内容，不等于预览或启用；应用与保存由 UI 的全局 Save/Cancel 流程控制。

一个包可同时包含多件服装及配色、发型、头饰和配件，也可只包含纯服装、纯发型或纯头饰。稳定选择槽为 `garment`、`hairstyle`、`headwear`、`weapon`、`handheld`、`jewelry`、`foreground-effect`；各槽以 `category/pack_id/item_id/variant_id` 分别列出、保存、解析与保护删除，因此长剑／短剑与剑鞘、手持物、珠宝和前景效果可以同时存在并跨包混搭。Manifest 的单一 `accessories` 集合中，每个 item 必须声明明确 `accessory_kind`。Typed `ensemble` 必须覆盖全部七槽；服装与发型必须指定同包项目，头饰及四个配件槽可明确为 `none`。一键应用后仍可逐槽改选。Ensemble 只改变外观，不可改变脸型、五官、身份或核心提示词。

服装沿用官方 `mohan-body-v1`。官方美术规格为成年女性，168 厘米、54 公斤、86/71/62/90 厘米，约 C70-equivalent；数字只用于官方美术制作与验收，不是插件拉伸公式。真正兼容性由版本化 rig anchors、masks 与 geometry 判断。颈肩线、胸廓、腰胯线、四肢比例、肤色和本体轮廓都由核心掌握。插件只能用 `visible`／`covered` 声明官方肤色区域，并从 `structured`、`draped`、`stretch`、`loose` 选择布料行为，不得换脸、换肤色或改变身材。

服装必须完整覆盖 v2 的 31 个精确视角：既有七个演出轮廓 `cheek-rest`、`left-neutral`、`front-crossed`、`front-mock-scold`、`front-mock-hit`、`front-eureka`、`front-exasperated`，以及 PoseAtlas 的 24 个正式视角。每个视角都必须拥有独立素材、anchor 与遮挡数据；不得用 alias 或旧衣回退冒充。旧 v1 三姿势包不再加载，必须通过官方模板一次升级为完整 v2 包；缺少、增加或拼错任一视角都整包拒绝。

每个 ensemble 都必须提供 `autonomous_profile`，明确标记适用温度带、天气、墨寒当前心境、场合与排序权重。自主选装使用单一决策器，遵守手动锁定、六小时冷却与雨雪／特殊节日安全优先；没有完整匹配时保留当前服装，不暗中换成别套。自创新衣与流行趋势搜索是分别保存的开关，可能产生云端费用，只有用户明确启用后才能执行。趋势只能提取抽象特征，不可复制或打包第三方照片与设计；生成结果先进入隔离区，完成 31 视角、角色身份、手部、遮挡、来源与许可审核后才可封装安装。

自创服装默认至少间隔七天，最多保留 16 个已安装包、5 个待修隔离任务与 6 GiB；用户可在控制台调整已安装数量和容量上限。达到上限时停止生成并保留现有内容，绝不自行删除用户上传的包。新衣成功应用后会留下“首次展示待办”；只有用户在场、看向墨寒、当前未说话且不处于专注／会议／全屏状态时，墨寒才用全身镜位主动询问新衣是否好看。成功说完后才标记完成；用户追问来源时，墨寒可通过四语词库幽默表示自己上网寻找灵感并作了改良，系统提示和内部标记永不朗读。

发型最小稳定 slot 为必需的 `back`、`front`，以及可选但在全部 silhouette 中必须一致的 `side-left`、`side-right`、`bangs`、`bun`、`ponytail`。每个 silhouette 都有自己的 anchor、z-order，并必须选择核心白名单的 face-occlusion mask、hand occlusion 与 garment/collar occlusion 规则，避免穿脸、穿手或穿衣领。插件可替换可见发丝，但不能提供核心头骨、脸型、眼睛、嘴型、五官、肤色或身份轮廓。

头饰使用 `headwear` 素材 slot，并必须指定 `crown`、左右 `temple`、左右 `ear` 或 `back-head` attachment point，以及相应的核心安全遮罩。武器可包含 `weapon` 与 `sheath` 层，placement 限背部、左右腰侧或左右手；每个 silhouette 都必须提供手部、服装、发型遮挡规则及 `back-harness`、`waist-sheath`、左右握持之一的 attachment／握持契约，避免漂浮或穿模。手持物 placement 限左右手，并要求每个 silhouette 的手部遮挡；可承载通用道具，不写死节日或角色。珠宝与前景效果各有独立槽。所有类型都要求四语名称，顺序统一为繁体中文、简体中文、英文、日文。

Manifest 的 `source` 必须记录 `kind`（`original`、`concept`、`reference-derived`）、作者、许可与 `reference_included: false`。参考作品可作为灵感记录，但参考照片或作品素材不得直接打包。封装拒绝 Python、JavaScript、EXE、DLL、脚本、绝对／穿越路径、符号链接、加密成员、解压炸弹、超限尺寸，以及包含 script、事件、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD 或 entity 的 SVG。

删除使用 typed remove API。内置默认永不可删除；任何正在 active 或 preview 的单项或 ensemble，都必须先切换或恢复内置才能删除。删除前会再次验证安全 pack ID、文件名与 archive manifest ID 完全一致，然后只移除该自包含单文件，不影响其他包、核心本体或个人数据。删除后不再出现在列表。不存在 ID、路径穿越、身份不符与损坏状态都会 fail closed。若保存设置后来指向已丢失的包，解析 API 明确返回 `missing` 并保持当前有效外观；不会崩溃、静默改选、退回旧格式或应用另一个同名外观。四语删除确认由 UI 主线负责。

## English

A character appearance pack is one self-contained, directly uploadable and downloadable ZIP-compatible `.mohan-outfit` container. A user downloads and selects one file. Sidecar folders, external packages, network downloads, external URLs, and required cross-pack references are forbidden. Every PNG, WebP, or safe SVG is inside the same archive and fully referenced by the manifest with SHA-256, dimensions, anchor, z-order, and a stable slot. Unreferenced, duplicate, missing, privileged, or dangerous members are rejected. Import validates the complete archive before atomically installing it in the destination directory. Failure leaves neither a partial pack nor damage to the installed version. Installation only adds content; preview and activation remain controlled by the UI and global Save/Cancel flow.

A package may contain multiple outfits and colorways, hairstyles, headwear, and accessories, or it may be a garment-only, hairstyle-only, or headwear-only file. Stable selection slots are `garment`, `hairstyle`, `headwear`, `weapon`, `handheld`, `jewelry`, and `foreground-effect`. Each is independently listed, saved, resolved, and protected during removal by `category/pack_id/item_id/variant_id`, so long or short swords and sheaths, handheld props, jewelry, and foreground effects can coexist and mix across packages. Each item in the single manifest `accessories` collection declares an explicit `accessory_kind`. A typed `ensemble` covers all seven slots: garment and hairstyle reference same-pack items, while headwear and all four accessory slots may explicitly be `none`. Every slot remains independently replaceable after one-click application. An ensemble changes appearance only, never face shape, features, identity, or core prompts.

Garments target official `mohan-body-v1`. The official art specification is an adult woman at 168 cm, 54 kg, and 86/71/62/90 cm—approximately C70-equivalent. Measurements guide official asset production and acceptance and are not a package-controlled scaling formula. Runtime compatibility uses versioned rig anchors, masks, and geometry. Neck-and-shoulder line, ribcage, waist and hip lines, limb proportions, skin tone, and body contour remain core-owned. A pack may only mark official skin regions `visible` or `covered` and select `structured`, `draped`, `stretch`, or `loose` fabric behavior. It cannot replace identity or skin or reshape the body.

Garments cover all 31 exact v2 views: the seven established performance silhouettes `cheek-rest`, `left-neutral`, `front-crossed`, `front-mock-scold`, `front-mock-hit`, `front-eureka`, and `front-exasperated`, plus all 24 formal PoseAtlas views. Every view has its own asset, anchor, and occlusion data; aliases and old-outfit fallback cannot stand in for it. Legacy three-pose v1 packages are not loaded and must be rebuilt once with the official complete v2 template. A missing, extra, or misspelled view rejects the whole package.

Every ensemble supplies an `autonomous_profile` describing suitable thermal bands, weather, MoHan mood, occasions, and priority. One deterministic director handles autonomous choice, manual lock, a six-hour cooldown, and protective weather or special-occasion urgency. With no complete match, the current outfit stays active. Self-generation and trend search are separately saved, potentially billable options and run only after explicit enablement. Trend sources contribute abstract traits only; third-party photographs and designs are never copied into a package. A generated draft remains quarantined until all 31 views, identity, hands, occlusion, provenance, and licensing pass audit.

Generation defaults to at least seven days apart, no more than 16 installed packages, five repairable quarantine jobs, and 6 GiB total storage. The installed-count and capacity limits are configurable. Reaching a limit stops generation without deleting user-uploaded packages. A newly applied outfit creates one pending first reveal. MoHan asks whether it looks good in full-body framing only while the user is present and looking, speech is idle, and focus, meetings, and full-screen activity are not being disturbed. Completion is recorded only after successful speech. If asked where it came from, MoHan can jokingly say through the four-language phrasebook that she found inspiration online and refined it herself; system prompts and internal tags are never spoken.

The minimum stable hairstyle slots are required `back` and `front`, plus optional `side-left`, `side-right`, `bangs`, `bun`, and `ponytail` slots that must remain consistent across every silhouette. Each silhouette has its own anchor and z-order and selects core-allowlisted face-occlusion mask, hand-occlusion rule, and garment/collar-occlusion rule so hair cannot pass through a face, hand, or collar. A pack may replace visible hair strands but cannot provide the core skull, face shape, eyes, mouth, facial identity, skin, or identity contour.

Headwear uses the `headwear` asset slot and declares a `crown`, left/right `temple`, left/right `ear`, or `back-head` attachment point plus a matching core-safe mask. A weapon may contain `weapon` and `sheath` layers. Placement is limited to back, left/right waist, or left/right hand; every silhouette declares hand, garment, and hair occlusion plus a `back-harness`, `waist-sheath`, left-grip, or right-grip attachment contract, preventing floating and clipping. Handheld placement is limited to either hand and requires per-silhouette hand occlusion; it supports generic props without hard-coded holidays or characters. Jewelry and foreground effects have independent slots. Every type requires complete Traditional Chinese, Simplified Chinese, English, and Japanese names.

Manifest `source` records `kind` (`original`, `concept`, or `reference-derived`), author, license, and `reference_included: false`. A reference work may be documented as inspiration, but its photographs or assets are not packaged. Python, JavaScript, EXE, DLL, scripts, absolute or traversing paths, symlinks, encrypted members, decompression bombs, excessive dimensions, and SVG containing scripts, events, `foreignObject`, external URLs, CSS `url()`, `data:`, DTDs, or entities are rejected.

Removal uses a typed API. Built-in defaults can never be removed. Any item or ensemble referenced by active or preview state must first be switched or restored to built-in. Before deletion, the core revalidates the safe pack ID and requires the filename and archive manifest ID to match exactly. It then removes only that self-contained file, never another package, core assets, or personal data. The package disappears from listings afterward. Missing IDs, traversal, identity mismatch, and corrupt state fail closed. If saved settings later reference a missing package, resolution explicitly reports `missing` and preserves the current valid look; it never crashes, silently changes identity, falls back to a legacy format, or applies a same-named item from another package. Four-language confirmation UI belongs to the main application.

## 日本語

キャラクター外観パックは、単一で自己完結し、そのままアップロード／ダウンロードできる ZIP 互換 `.mohan-outfit` コンテナです。利用者がダウンロードして選ぶのは一つのファイルだけです。付属フォルダー、外部依存パッケージ、ネットワークダウンロード、外部 URL、必須の別パック参照は禁止です。すべての PNG、WebP、安全な SVG は同一 archive 内に置き、manifest が SHA-256、寸法、anchor、z-order、安定 slot で完全に参照します。未参照、重複、不足、権限外、危険なメンバーは拒否します。インポートは全体検証後に同一配置先でアトミックにインストールします。失敗時は半端なパックを残さず、既存版も壊しません。インストールは内容の追加だけで、プレビューと有効化は UI と全体 Save/Cancel が管理します。

一つのパックには複数の衣装と配色、髪型、頭飾り、アクセサリーを含められます。また、衣装だけ、髪型だけ、頭飾りだけの単一ファイルも有効です。安定選択 slot は `garment`、`hairstyle`、`headwear`、`weapon`、`handheld`、`jewelry`、`foreground-effect` です。各 slot は `category/pack_id/item_id/variant_id` で個別に一覧、保存、解決、削除保護されるため、長剣／短剣と鞘、手持ち物、宝飾、前景効果を同時に使い、別パックとも組み合わせられます。一つの `accessories` 集合内で各 item は明確な `accessory_kind` を宣言します。Typed `ensemble` は七 slot 全部を含み、衣装と髪型は同パック項目を指定し、頭飾りと四アクセサリー slot は `none` にできます。一括適用後も各 slot を変更できます。Ensemble は顔型、顔部品、同一性、コアプロンプトを変更しません。

衣装は公式 `mohan-body-v1` を対象とします。公式美術仕様は成人女性、身長 168 cm、体重 54 kg、86/71/62/90 cm、約 C70 相当です。数値は公式素材制作と検収の指針で、パックによる伸縮式ではありません。実行時互換性はバージョン化された rig anchors、masks、geometry で判断します。首肩線、胸郭、腰・骨盤線、四肢比率、肌色、本体輪郭はコアが所有します。パックは公式肌領域を `visible`／`covered` と宣言し、布挙動を `structured`、`draped`、`stretch`、`loose` から選ぶだけで、顔や肌の交換、体形変更はできません。

衣装は v2 の 31 個の正確な視点をすべて備えます。既存の演出輪郭 `cheek-rest`、`left-neutral`、`front-crossed`、`front-mock-scold`、`front-mock-hit`、`front-eureka`、`front-exasperated` と、PoseAtlas の正式 24 視点です。各視点に専用素材、anchor、遮蔽データが必要で、alias や旧衣装への退避では代用できません。旧 v1 三姿勢パックは読み込まず、公式の完全 v2 テンプレートで一度作り直します。視点の不足、余分、綴り違いはパック全体を拒否します。

各 ensemble は適用温度帯、天候、墨寒の現在の気分、場面、優先度を示す `autonomous_profile` を持ちます。自律選択は一つの決定器が手動ロック、六時間のクールダウン、雨雪や特別な日の緊急性を処理します。完全一致がなければ現在の衣装を維持します。自己生成と流行検索は別々に保存する、料金が発生し得る設定で、利用者が明示的に有効化した後だけ動作します。流行情報から使うのは抽象的特徴だけで、第三者の写真やデザインをパックへ複製しません。生成案は 31 視点、同一性、手、遮蔽、出所、ライセンスの監査を通るまで隔離されます。

自己生成は既定で七日以上の間隔を置き、インストール済み 16 パック、修復待ち隔離 5 件、合計 6 GiB を上限とします。インストール数と容量は設定できます。上限到達時は生成を止め、利用者がアップロードしたパックを自動削除しません。新衣装の適用後は初回披露を一件だけ保留します。利用者が在席して墨寒を見ており、発話中ではなく、集中・会議・全画面を妨げない時だけ、全身画角で似合うか尋ねます。正常に話し終えた後だけ完了を記録します。入手元を尋ねられた時は、四言語の台詞集を使い、ネットで着想を見つけ自分で手直ししたと冗談めかして答えられます。システムプロンプトや内部タグは読み上げません。

髪型の最小安定 slot は必須の `back`、`front` と、任意ながら全 silhouette で一貫させる `side-left`、`side-right`、`bangs`、`bun`、`ponytail` です。各 silhouette は固有の anchor と z-order、およびコア許可済み face-occlusion mask、hand occlusion、garment/collar occlusion 規則を持ち、顔、手、襟を突き抜けないようにします。パックは見える髪を交換できますが、コア頭骨、顔型、目、口、顔部品、肌、同一性輪郭は提供できません。

頭飾りは `headwear` 素材 slot を使い、`crown`、左右 `temple`、左右 `ear`、`back-head` attachment point と対応するコア安全マスクを指定します。武器は `weapon` と `sheath` 層を持てます。placement は背中、左右の腰、左右の手に限定し、各 silhouette に手、衣装、髪の遮蔽と `back-harness`、`waist-sheath`、左右 grip の attachment／把持契約が必要です。これにより浮遊や貫通を防ぎます。手持ち物は左右の手だけに配置し、各 silhouette の手遮蔽が必須です。特定の祝日や人物を固定せず一般道具を扱えます。宝飾と前景効果は独立 slot です。全種類に繁体字中国語、簡体字中国語、英語、日本語の完全な名称が必要です。

Manifest の `source` は `kind`（`original`、`concept`、`reference-derived`）、作者、ライセンス、`reference_included: false` を記録します。参照作品は着想元として記録できますが、その写真や素材は同梱しません。Python、JavaScript、EXE、DLL、スクリプト、絶対／横断パス、シンボリックリンク、暗号化メンバー、解凍爆弾、過大寸法、および script、イベント、`foreignObject`、外部 URL、CSS `url()`、`data:`、DTD、entity を含む SVG は拒否します。

削除には typed remove API を使用します。内蔵既定は削除できません。active または preview が参照する単項目や ensemble は、先に別の外観へ切り替えるか内蔵へ復元する必要があります。削除前に安全な pack ID を再検証し、ファイル名と archive manifest ID の完全一致を要求します。その後、対象の自己完結ファイルだけを削除し、他パック、コア本体、個人データには触れません。削除後は一覧から消えます。存在しない ID、パストラバーサル、識別不一致、破損状態は fail closed です。保存設定が後に欠落パックを参照した場合、解決 API は `missing` を明示し、現在の有効な外観を維持します。クラッシュ、暗黙の変更、旧形式への退避、同名の別外観適用は行いません。四言語の削除確認 UI は本体側が担当します。
