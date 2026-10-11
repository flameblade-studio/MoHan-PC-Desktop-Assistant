# 素體包與角色圖層／素体包与角色图层／Body packs and character layers／素体パックとキャラクターレイヤー

## 繁體中文

炎劍鑄魂引擎只提供機制；素體包提供人物光頭素體的全身、半身、眨眼與嘴型影格；角色包提供髮型、服裝、身體修正與妝容圖層。引擎對衣著保持中立。墨寒素體 ID 為 `mohan-body-v2`。素材安裝由下一張工單負責。Reader 先驗證 manifest 與所有宣告檔案的 SHA-256，再記錄 PNG 畫布尺寸；只有請求影格或遮罩時才解碼像素。已驗證 PNG 位元組使用上限 16 MiB 的 LRU 快取，命中時仍核對檔案 stat。執行期快取保留量總上限為 64 MiB：素體驗證位元組 16 MiB、角色圖層位元組 8 MiB、pixmap 與合成影像 32 MiB、Alpha 區域 8 MiB；Qt 影像操作在 GUI 執行緒執行。

使用者資料目錄的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字串 version、非空 license、full_body、half_body、fingerprint。影格表以視角或姿勢 ID 為鍵，值是 `{path, sha256}`（rest）或狀態至檔案記錄的表。全身閉嘴狀態是 rest、half、closed；發聲狀態是 small、a、o 加連字號與眼睛狀態。只宣告 rest 的視角在發聲時回退至自身 rest，並記錄專用 family。此 renderer 不支援 wink；wink 請求會回報 `unsupported_wink`。半身使用 neutral、small、a、o 加連字號與眼睛狀態，例如 neutral-rest、a-closed；可用表情名稱作姿勢鍵，優先於 motion.pose。A 嘴型對應 a，O 與 U 對應 o，其餘發聲對應 small。

路徑是包內相對 POSIX 路徑，SHA-256 是 64 字元小寫十六進位。同一路徑使用同一 hash。Fingerprint 為每個影格與核心遮罩建立 `(section, view, state, path, sha256)` 正規化紀錄；文字欄位採 Unicode NFC，依整筆 tuple 排序，再以 compact JSON 陣列和 UTF-8 計算 SHA-256。每筆關聯都納入，因此交換視角、狀態、路徑或核心遮罩都會改變指紋。選填 face_core_masks 是視角至檔案記錄的表，非零 Alpha 定義臉部核心保護區。全身與半身各自保持一致 RGBA PNG 畫布，遮罩與對應影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 與 layer_views。缺包、ID、版本、指紋或檔案 hash 不符時，BodyPackMismatchError 明確報錯並記錄診斷。已宣告角色直接使用素體 renderer；未宣告的舊角色與服裝保持原路徑，墨寒預設完整影格保持原樣。

每個 layer_views 條目含選填 order、layers 和 base_hide。Layer 是 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。省略 order 時為 hair-back、base、body-fix、makeup、garment、hair-front、ornament；makeup 必須位於 base 之後、garment 之前。明確宣告可用 base、hair-back、body-fix、makeup、garment、hair-front、ornament；背面可把 hair-back 放 garment 後。同 kind 保持宣告順序。Base_hide 每視角一張，記錄為 `{path, sha256, anchor: [0, 0]}`；非零 Alpha 清除素體。所有層與遮罩同畫布、同原點，並列入角色 files 且 hash 一致。

合成選擇素體表情與嘴型眨眼端點，清除 base_hide，再按 order 疊圖。makeup 使用 SourceAtop 疊在 base/body-fix 後並裁切至 face_core；garment、hair-front、ornament 依序在其後疊加。其他角色圖層與清除遮罩都避開素體核心。有角色圖層或隱藏遮罩的視角須提供素體核心遮罩；無可見臉部用全透明核心遮罩明確宣告。缺影格明確報錯。技術驗證與外觀核可分開；新測試、架構邊界與 GOLDEN_MATCH 交 CI。

## 简体中文

炎剑铸魂引擎只提供机制；素体包提供人物光头素体的全身、半身、眨眼和嘴型影格；角色包提供头发、服装、身体修正和妆容图层。引擎对衣着保持中立。墨寒素体 ID 是 `mohan-body-v2`，素材由下一张工单安装。Reader 先验证 manifest 和所有声明文件的 SHA-256，再记录 PNG 画布尺寸；只有请求影格或遮罩时才解码像素。已验证 PNG 字节使用上限 16 MiB 的 LRU 缓存，命中时仍检查文件 stat。运行期缓存保留量总上限为 64 MiB：素体验证字节 16 MiB、角色图层字节 8 MiB、pixmap 与合成图像 32 MiB、Alpha 区域 8 MiB；Qt 图像操作在 GUI 线程执行。

用户数据目录的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字符串 version、非空 license、full_body、half_body、fingerprint。影格表以视角或姿势 ID 为键，值是 `{path, sha256}`（rest）或状态至文件记录的表。全身闭嘴是 rest、half、closed；发声是 small、a、o 加连字符与眼睛状态。仅有 rest 的视角在发声时回退至自身 rest，并记录专用 family。此 renderer 不支持 wink；wink 请求会回报 `unsupported_wink`。半身使用 neutral、small、a、o 加连字符与眼睛状态，例如 neutral-rest、a-closed；表情名称可作为姿势键，优先于 motion.pose。A 对应 a，O 和 U 对应 o，其余发声对应 small。

路径是包内相对 POSIX 路径，SHA-256 是 64 位小写十六进制。同一路径使用同一 hash。Fingerprint 为每个影格和核心遮罩建立 `(section, view, state, path, sha256)` 正规化记录；文本字段采用 Unicode NFC，按完整 tuple 排序，再以 compact JSON 数组和 UTF-8 计算 SHA-256。每条关联都会纳入，因此交换视角、状态、路径或核心遮罩都会改变指纹。可选 face_core_masks 是视角至文件记录的表，非零 alpha 保护脸部核心。全身与半身分别保持一致 RGBA PNG 画布，遮罩与对应影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 和 layer_views。缺包、ID、版本、指纹或文件 hash 不符时，BodyPackMismatchError 明确报错并记录诊断。已声明角色使用素体 renderer；未声明的旧角色与服装保持原路径，墨寒默认完整影格保持原样。

Layer_views 含可选 order、layers、base_hide。Layer 为 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。默认顺序是 hair-back、base、body-fix、makeup、garment、hair-front、ornament；makeup 必须在 base 之后、garment 之前。明确声明可将 base 放前，背面可将 hair-back 放 garment 后。同 kind 保持声明顺序。每视角一张 base_hide，记录为 `{path, sha256, anchor: [0, 0]}`，非零 Alpha 清除素体。所有层与遮罩同画布、同原点，列入角色 files 且 hash 一致。

合成选择素体表情与嘴型眨眼端点，清除 base_hide，再按 order 叠图。makeup 使用 SourceAtop 叠在 base/body-fix 后并裁切至 face_core；garment、hair-front、ornament 依序在其后叠加。其他图层与清除遮罩避开核心；有图层或隐藏遮罩的视角必须有核心遮罩，无可见脸部用全透明核心遮罩明确声明。缺影格明确报错。技术验证与外观批准分开；测试、边界和 GOLDEN_MATCH 交 CI。

## English

Soulforge owns mechanisms. Body packs own bald full-body and half-body frames, blinks and mouth states. Character packs own hair, garments, body fixes and makeup. Clothing is neutral. MoHan uses `mohan-body-v2`; assets belong to the next work order. The reader verifies the manifest and every declared SHA-256 before use, records PNG canvas dimensions, and decodes pixels only when a frame or mask is requested. Verified PNG bytes use an LRU cache capped at 16 MiB, with a stat check on every cache hit. The retained runtime cache budget is 64 MiB: 16 MiB verified body bytes, 8 MiB verified layer bytes, 32 MiB pixmaps and composed images, and 8 MiB alpha regions. Qt image work runs on the GUI thread.

The user data directory contains `body-packs/<id>/manifest.json`, schema `mohan.body-pack.v1`. Required fields are id, string version, nonempty license, full_body, half_body and fingerprint. Frame maps use view or pose IDs, pointing to `{path, sha256}` (rest) or state-to-file maps. Full-body neutral states use rest, half and closed; speaking uses small, a or o plus a hyphen and the eye state. A rest-only view falls back to its rest frame while speaking and records a dedicated family. This renderer does not support wink; wink requests raise `unsupported_wink`. Half-body uses neutral, small, a or o plus eye state, such as neutral-rest and a-closed. Expression names may be pose keys and precede motion.pose. A maps to a; O and U map to o; other speaking visemes map to small.

Paths are relative POSIX paths. SHA-256 uses 64 lowercase hexadecimal characters. Repeated paths use one hash. Fingerprinting creates a normalized `(section, view, state, path, sha256)` record for each frame and core mask, normalizes text to Unicode NFC, sorts the records, and hashes their compact JSON arrays as UTF-8. Every binding contributes, so changing a view, state, path or core-mask assignment changes the fingerprint. Optional face_core_masks maps view IDs to file records whose nonzero alpha protects the core. Full-body and half-body each share an RGBA PNG canvas; core masks match their views.

Character manifests may declare `body_pack: {id, version, fingerprint}` and layer_views. Missing packs and ID, version, fingerprint or payload mismatches raise BodyPackMismatchError and produce diagnostics. Declared characters use the body renderer. Undeclared characters and outfits retain existing behavior, including MoHan's original default frames.

Layer_views entries have optional order, layers and base_hide. Layer records are `{kind, path, sha256, anchor: [0, 0]}`; kinds are hair-back, body-fix, garment, hair-front, ornament and makeup. Default order is hair-back, base, body-fix, makeup, garment, hair-front, ornament; makeup must follow base and precede garment. Explicit order may place base first and rear hair after garment. Same-kind layers keep declaration order. One base_hide per view uses `{path, sha256, anchor: [0, 0]}`; nonzero alpha clears the body. Layers and masks share the canvas and origin and match character file hashes.

Composition selects body-owned expression, mouth and blink endpoints, clears base_hide and paints in order. Makeup uses SourceAtop over base/body-fix and is clipped to face_core; garment, hair-front and ornament are painted afterward in order. Other character layers and clear masks exclude the core. Views with layers or hide masks require a body-owned core mask; a transparent core mask declares an invisible face. Missing frames raise. Technical checks and appearance approval remain separate; tests, boundaries and GOLDEN_MATCH run in CI.

## 日本語

炎剣鋳魂エンジンは仕組みを所有し、素体パックは人物の坊主素体の全身・半身・まばたき・口形フレームを所有します。キャラクターパックは髪・服・身体修正・化粧レイヤーを所有します。衣服条件は設けません。墨寒 ID は `mohan-body-v2`、素材導入は次の作業です。Reader は manifest と宣言ファイルすべての SHA-256 を検証して PNG キャンバス寸法を記録し、フレームまたはマスクが要求された時にだけピクセルをデコードします。検証済み PNG バイト列は上限 16 MiB の LRU キャッシュを使い、キャッシュヒット時もファイル stat を確認します。 実行時の保持キャッシュ上限は 64 MiB です。内訳は素体の検証済みバイト列 16 MiB、検証済みレイヤーバイト列 8 MiB、pixmap と合成画像 32 MiB、Alpha 領域 8 MiB です。Qt の画像処理は GUI スレッドで行います。

ユーザーデータの `body-packs/<id>/manifest.json` は schema `mohan.body-pack.v1` です。id、文字列 version、空でない license、full_body、half_body、fingerprint が必須です。視点・姿勢 ID に `{path, sha256}`（rest）または状態からファイルへの表を対応付けます。全身閉口は rest・half・closed、発声は small・a・o とハイフンと目状態です。rest のみの視点は発声時に自身の rest フレームへ戻り、専用 family を記録します。この renderer は wink をサポートせず、wink 要求は `unsupported_wink` を返します。半身は neutral・small・a・o と目状態、例は neutral-rest・a-closed。表情名の姿勢キーは motion.pose より優先します。A は a、O と U は o、他の発声は small です。

パスは相対 POSIX パス、hash は64文字の小文字16進数です。同じパスは同じ hash を使います。Fingerprint は各フレームと顔核心マスクの `(section, view, state, path, sha256)` 正規化レコードを作成し、文字列を Unicode NFC に正規化して、レコードをソートした compact JSON 配列の UTF-8 を SHA-256 にします。すべての関連付けを含むため、視点・状態・パス・核心マスクの変更は指紋を変えます。任意の face_core_masks は視点からファイルへの表で、非ゼロ Alpha が顔核心保護域です。全身・半身はそれぞれ同一 RGBA PNG キャンバスで、マスクは対応視点と同寸法です。

キャラクター manifest に `body_pack: {id, version, fingerprint}` と layer_views を追加できます。欠落・ID・版・指紋・ファイル hash 不一致は BodyPackMismatchError と診断記録で明示します。宣言した人物は素体 renderer を使用し、宣言のない既存人物・服装と墨寒の既定フレームは元の処理を維持します。

Layer_views は任意の order・layers・base_hide を持ちます。レイヤーは `{kind, path, sha256, anchor: [0, 0]}` で、kind は hair-back・body-fix・garment・hair-front・ornament・makeup です。既定順序は hair-back・base・body-fix・makeup・garment・hair-front・ornament。makeup は base の後、garment の前に置きます。明示順序では base を先に、背面の hair-back を garment 後に置けます。同 kind は宣言順です。Base_hide は視点ごと一枚の `{path, sha256, anchor: [0, 0]}` で、非ゼロ Alpha が素体を消去します。全素材は同キャンバス・同原点で files の hash と一致します。

素体の表情・口形・まばたき端点を選び、base_hide を消去して順番に合成します。makeup は base/body-fix の後に SourceAtop で重ねて face_core 内に裁切し、その後 garment・hair-front・ornament を順番に重ねます。その他の役割レイヤーと消去マスクは核心を避けます。レイヤーか非表示マスクがある視点には核心マスクを必須とし、顔が見えない視点は全透明マスクで宣言します。欠落フレームは明示エラーです。技術検証と外観承認を分け、テスト・境界・GOLDEN_MATCH は CI で検証します。
