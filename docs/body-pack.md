# 素體包與角色圖層／素体包与角色图层／Body packs and character layers／素体パックとキャラクターレイヤー

## 繁體中文

炎劍鑄魂引擎只提供機制；素體包提供人物光頭素體的全身、半身、眨眼與嘴型影格；角色包提供髮型、服裝、身體修正與妝容圖層。引擎對衣著保持中立。墨寒素體 ID 為 `mohan-body-v2`。素材安裝由下一張工單負責。

使用者資料目錄的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字串 version、非空 license、full_body、half_body、fingerprint。影格表以視角或姿勢 ID 為鍵，值是 `{path, sha256}`（rest）或狀態至檔案記錄的表。全身閉嘴狀態是 rest、half、closed；發聲狀態是 small、a、o 加連字號與眼睛狀態。只宣告 rest 的無可見眼睛視角使用自身 rest。半身使用 neutral、small、a、o 加連字號與眼睛狀態，例如 neutral-rest、a-closed；可用表情名稱作姿勢鍵，優先於 motion.pose。A 嘴型對應 a，O 與 U 對應 o，其餘發聲對應 small。

路徑是包內相對 POSIX 路徑，SHA-256 是 64 字元小寫十六進位。同一路徑使用同一 hash。Fingerprint 先依唯一檔案路徑去重，再將其 hash 排序，以 LF 串接（末尾沒有 LF），對 UTF-8 位元組計算 SHA-256；不同路徑的相同 hash 保留重複。選填 face_core_masks 是視角至檔案記錄的表，非零 Alpha 定義臉部核心保護區。全身與半身各自保持一致 RGBA PNG 畫布，遮罩與對應影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 與 layer_views。缺包、版本、指紋或檔案 hash 不符時，BodyPackMismatchError 明確報錯並記錄診斷。已宣告角色直接使用素體 renderer；未宣告的舊角色與服裝保持原路徑，墨寒預設完整影格保持原樣。

每個 layer_views 條目含選填 order、layers 和 base_hide。Layer 是 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。省略 order 時為 hair-back、base、body-fix、garment、makeup、hair-front、ornament。明確宣告可用 base、hair-back、body-fix、garment、hair-front、ornament；背面可把 hair-back 放 garment 後。同 kind 保持宣告順序。Base_hide 每視角一張，記錄為 `{path, sha256, anchor: [0, 0]}`；非零 Alpha 清除素體。所有層與遮罩同畫布、同原點，並列入角色 files 且 hash 一致。

合成選擇素體表情與嘴型眨眼端點，清除 base_hide，再按 order 疊圖。清除與角色圖層都避開素體核心。有角色圖層或隱藏遮罩的視角須提供素體核心遮罩；無可見臉部用全透明核心遮罩明確宣告。缺影格明確報錯。技術驗證與外觀核可分開；新測試、架構邊界與 GOLDEN_MATCH 交 CI。

## 简体中文

炎剑铸魂引擎只提供机制；素体包提供人物光头素体的全身、半身、眨眼和嘴型影格；角色包提供头发、服装、身体修正和妆容图层。引擎对衣着保持中立。墨寒素体 ID 是 `mohan-body-v2`，素材由下一张工单安装。

用户数据目录的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字符串 version、非空 license、full_body、half_body、fingerprint。影格表以视角或姿势 ID 为键，值是 `{path, sha256}`（rest）或状态至文件记录的表。全身闭嘴是 rest、half、closed；发声是 small、a、o 加连字符与眼睛状态。仅有 rest 的无可见眼睛视角使用自身 rest。半身使用 neutral、small、a、o 加连字符与眼睛状态，例如 neutral-rest、a-closed；表情名称可作为姿势键，优先于 motion.pose。A 对应 a，O 和 U 对应 o，其余发声对应 small。

路径是包内相对 POSIX 路径，SHA-256 是 64 位小写十六进制。同一路径使用同一 hash。Fingerprint 按唯一文件路径去重，再将 hash 排序，以 LF 连接（末尾没有 LF），对 UTF-8 字节计算 SHA-256；不同路径的相同 hash 保留重复。可选 face_core_masks 是视角至文件记录的表，非零 Alpha 保护脸部核心。全身与半身分别保持一致 RGBA PNG 画布，遮罩与对应影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 和 layer_views。缺包、版本、指纹或文件 hash 不符时，BodyPackMismatchError 明确报错并记录诊断。已声明角色使用素体 renderer；未声明的旧角色与服装保持原路径，墨寒默认完整影格保持原样。

Layer_views 含可选 order、layers、base_hide。Layer 为 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。默认顺序是 hair-back、base、body-fix、garment、makeup、hair-front、ornament。明确声明可将 base 放前，背面可将 hair-back 放 garment 后。同 kind 保持声明顺序。每视角一张 base_hide，记录为 `{path, sha256, anchor: [0, 0]}`，非零 Alpha 清除素体。所有层与遮罩同画布、同原点，列入角色 files 且 hash 一致。

合成选择素体表情与嘴型眨眼端点，清除 base_hide，再按 order 叠图。清除与图层避开核心；有图层或隐藏遮罩的视角必须有核心遮罩，无可见脸部用全透明核心遮罩明确声明。缺影格明确报错。技术验证与外观批准分开；测试、边界和 GOLDEN_MATCH 交 CI。

## English

Soulforge owns mechanisms. Body packs own bald full-body and half-body frames, blinks and mouth states. Character packs own hair, garments, body fixes and makeup. Clothing is neutral. MoHan uses `mohan-body-v2`; assets belong to the next work order.

The user data directory contains `body-packs/<id>/manifest.json`, schema `mohan.body-pack.v1`. Required fields are id, string version, nonempty license, full_body, half_body and fingerprint. Frame maps use view or pose IDs, pointing to `{path, sha256}` (rest) or state-to-file maps. Full-body neutral states use rest, half and closed; speaking uses small, a or o plus a hyphen and the eye state. Rest-only invisible-eye views use their own rest. Half-body uses neutral, small, a or o plus eye state, such as neutral-rest and a-closed. Expression names may be pose keys and precede motion.pose. A maps to a; O and U map to o; other speaking visemes map to small.

Paths are relative POSIX paths. SHA-256 uses 64 lowercase hexadecimal characters. Repeated paths use one hash. Fingerprint deduplicates paths, sorts their hashes, joins them with LF without a trailing LF, then hashes the UTF-8 bytes. Equal hashes for distinct paths retain repetitions. Optional face_core_masks maps view IDs to file records whose nonzero alpha protects the core. Full-body and half-body each share an RGBA PNG canvas; core masks match their views.

Character manifests may declare `body_pack: {id, version, fingerprint}` and layer_views. Missing packs and version, fingerprint or payload mismatches raise BodyPackMismatchError and produce diagnostics. Declared characters use the body renderer. Undeclared characters and outfits retain existing behavior, including MoHan's original default frames.

Layer_views entries have optional order, layers and base_hide. Layer records are `{kind, path, sha256, anchor: [0, 0]}`; kinds are hair-back, body-fix, garment, hair-front, ornament and makeup. Default order is hair-back, base, body-fix, garment, makeup, hair-front, ornament. Explicit order may place base first and rear hair after garment. Same-kind layers keep declaration order. One base_hide per view uses `{path, sha256, anchor: [0, 0]}`; nonzero alpha clears the body. Layers and masks share the canvas and origin and match character files hashes.

Composition selects body-owned expression, mouth and blink endpoints, clears base_hide and paints in order. Clearing and layers exclude the core. Views with layers or hide masks require a body-owned core mask; a transparent core mask declares an invisible face. Missing frames raise. Technical checks and appearance approval remain separate; tests, boundaries and GOLDEN_MATCH run in CI.

## 日本語

炎剣鋳魂エンジンは仕組みを所有し、素体パックは人物の坊主素体の全身・半身・まばたき・口形フレームを所有します。キャラクターパックは髪・服・身体修正・化粧レイヤーを所有します。衣服条件は設けません。墨寒 ID は `mohan-body-v2`、素材導入は次の作業です。

ユーザーデータの `body-packs/<id>/manifest.json` は schema `mohan.body-pack.v1` です。id、文字列 version、空でない license、full_body、half_body、fingerprint が必須です。視点・姿勢 ID に `{path, sha256}`（rest）または状態からファイルへの表を対応付けます。全身閉口は rest・half・closed、発声は small・a・o とハイフンと目状態です。rest のみの目が見えない視点は自身の rest を使います。半身は neutral・small・a・o と目状態、例は neutral-rest・a-closed。表情名の姿勢キーは motion.pose より優先します。A は a、O と U は o、他の発声は small です。

パスは相対 POSIX パス、hash は64文字の小文字16進数です。同じパスは同じ hash を使います。Fingerprint は一意のパスの hash をソートし、末尾 LF なしの LF 連結 UTF-8 を SHA-256 にします。別パスの同じ hash は重複を保持します。任意の face_core_masks は視点からファイルへの表で、非ゼロ Alpha が顔核心保護域です。全身・半身はそれぞれ同一 RGBA PNG キャンバスで、マスクは対応視点と同寸法です。

キャラクター manifest に `body_pack: {id, version, fingerprint}` と layer_views を追加できます。欠落・版・指紋・ファイル hash 不一致は BodyPackMismatchError と診断記録で明示します。宣言した人物は素体 renderer を使用し、宣言のない既存人物・服装と墨寒の既定フレームは元の処理を維持します。

Layer_views は任意の order・layers・base_hide を持ちます。レイヤーは `{kind, path, sha256, anchor: [0, 0]}` で、kind は hair-back・body-fix・garment・hair-front・ornament・makeup です。既定順序は hair-back・base・body-fix・garment・makeup・hair-front・ornament。明示順序では base を先に、背面の hair-back を garment 後に置けます。同 kind は宣言順です。Base_hide は視点ごと一枚の `{path, sha256, anchor: [0, 0]}` で、非ゼロ Alpha が素体を消去します。全素材は同キャンバス・同原点で files の hash と一致します。

素体の表情・口形・まばたき端点を選び、base_hide を消去して順番に合成します。消去とレイヤーは核心を避けます。レイヤーか非表示マスクがある視点には核心マスクを必須とし、顔が見えない視点は全透明マスクで宣言します。欠落フレームは明示エラーです。技術検証と外観承認を分け、テスト・境界・GOLDEN_MATCH は CI で検証します。
