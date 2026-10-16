# 素體包與角色圖層／素体包与角色图层／Body packs and character layers／素体パックとキャラクターレイヤー

## 繁體中文

產品規則：「素體」表示完整素體加上角色預設髮型，只保留 base 與 hair-back、hair-front、ornament，並依宣告順序合成；body-fix、makeup、garment、look-fix 及 base_hide 均不納入素體合成。光頭素體包影格供內部疊圖使用；雲裳閣、桌面全身、半身、截圖與匯出共用有髮合成畫面。載入時顯示載入提示，缺少頭髮或渲染失敗時顯示錯誤。未宣告素體包的墨寒維持原影格與原髮髻。

炎劍鑄魂引擎只提供機制；素體包提供人物光頭素體的全身、半身、眨眼與嘴型影格；角色包提供髮型、服裝、身體修正與妝容圖層。引擎對衣著保持中立。墨寒素體 ID 為 `mohan-body-v2`。素體包與角色包分別下載；素體包依 lock 由 `tools/fetch_body_pack.py` 安裝。Reader 先驗證 manifest 與所有宣告檔案的 SHA-256，再記錄 PNG 畫布尺寸；只有請求影格或遮罩時才解碼像素。已驗證 PNG 位元組使用上限 16 MiB 的 LRU 快取，命中時仍核對檔案 stat。執行期快取保留量總上限為 64 MiB：素體驗證位元組 16 MiB、角色圖層位元組 8 MiB、pixmap 與合成影像 32 MiB、Alpha 區域 8 MiB；Qt 影像操作在 GUI 執行緒執行。

使用者資料目錄的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字串 version、非空 license、full_body、half_body、fingerprint。影格表以視角或姿勢 ID 為鍵，值是 `{path, sha256}`（rest）或狀態至檔案記錄的表。全身閉嘴狀態是 rest、half、closed；發聲狀態是 small、a、o 加連字號與眼睛狀態。只宣告 rest 的視角在發聲時回退至自身 rest，並記錄專用 family。此 renderer 不支援 wink；wink 請求會回報 `unsupported_wink`。半身使用 neutral、small、a、o 加連字號與眼睛狀態，例如 neutral-rest、a-closed；可用表情名稱作姿勢鍵，優先於 motion.pose。A 嘴型對應 a，O 與 U 對應 o，其餘發聲對應 small。

路徑是包內相對 POSIX 路徑，SHA-256 是 64 字元小寫十六進位。同一路徑使用同一 hash。Fingerprint 為每個影格與核心遮罩建立 `(section, view, state, path, sha256)` 正規化紀錄；文字欄位採 Unicode NFC，依整筆 tuple 排序，再以 compact JSON 陣列和 UTF-8 計算 SHA-256。每筆關聯都納入，因此交換視角、狀態、路徑或核心遮罩都會改變指紋。選填 face_core_masks 是視角至檔案記錄的表，Alpha 權重定義臉部核心保護程度。全身與半身各自保持一致 RGBA PNG 畫布，遮罩與對應影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 與 layer_views。缺包、ID、版本、指紋或檔案 hash 不符時，BodyPackMismatchError 明確報錯並記錄診斷。已宣告角色直接使用素體 renderer；未宣告的舊角色與服裝保持原路徑，墨寒預設完整影格保持原樣。

每個 layer_views 條目含選填 order、layers 和 base_hide。Layer 是 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。省略 order 時為 hair-back、base、body-fix、makeup、garment、hair-front、ornament；makeup 必須位於 base 之後、garment 之前。明確宣告可用 base、hair-back、body-fix、makeup、garment、hair-front、ornament；背面可把 hair-back 放 garment 後。同 kind 保持宣告順序。Base_hide 每視角一張，記錄為 `{path, sha256, anchor: [0, 0]}`；非零 Alpha 清除素體。所有層與遮罩同畫布、同原點，並列入角色 files 且 hash 一致。

H 是 base_hide：任一 H.alpha>0 都在混合前完全清除素體 B，不讀取或套用 F_alpha。依 plan.order 逐項建立 X；base 項放入 H 清除後的 B，其餘非 makeup 角色層以原始 alpha 一般 SourceOver 疊加。B′ 是 B 加上 makeup SourceAtop，makeup 不加入 X。base 項遵守宣告順序，hair-back 沒有例外；角色層 L 與遮罩 H 都不預乘 F_alpha。有角色圖層或隱藏遮罩的視角須提供素體核心遮罩；無可見臉部用全透明核心遮罩明確宣告。缺影格明確報錯。技術驗證與外觀核可分開；新測試、架構邊界與 GOLDEN_MATCH 交 CI。

角色包作者契約：素體包獨佔臉部核心；H.alpha>0 不受 F_alpha 影響，會完全清除 B。依 plan.order 建立 X：base 項是 H 清除後的 B，所有非 makeup 角色層以原始 alpha 一般 SourceOver；B′ 是 B 加 makeup SourceAtop，makeup 不在 X 內。唯一合成公式為 R = B′ * F_alpha + X * (1 - F_alpha)，逐像素對預乘 RGBA 做線性插值。base 依宣告順序定位，hair-back 同樣參與公式；L 與 H 均不預乘 F_alpha。建置時以空集合 F 產生 H＝B.alpha>0 且 A.alpha<255、L 包含 A 與 B 不同處的 A，也重畫 H 清除後相同的半透明 A；保留原始分層與深度。

妝容：B′ 由角色預設的妝容包依目前選擇的經典、淡妝、華麗妝或素顏套用在素體上，視角、姿勢、眨眼與嘴型狀態跟隨素體影格。素顏保留原始素體；最終公式只在 F 內使用 B′，F 外的角色圖層與服裝保持原樣。

### 建置流程

以下是候選生成參考流程，採用 --mode all --recompute-layers；重用重算圖層前會核對 SHA-256。本工單使用已指定來源，不執行這套外觀重算。重算沿用核准 F1／F2／H 腳本並將輸出導向候選的 lin-keyun-layers/recomputed/。face-core 以靜止遮罩非零 Alpha 包圍盒計算頭部 ROI：左右各外擴盒寬的 40%，上方外擴盒高的 40%，下方外擴盒高的 25%，距離向上取整並裁至畫布。只在 ROI 比較各狀態與靜止原影格的 RGBA 最大通道差；差異須大於 8，兩側皆透明時忽略 RGB。S 為靜止 F 的二值核心（alpha≥128）。聯集各狀態差異後做 3×3 開運算，動作像素 M 限制在 dilate(S, 6 px) 內。先聯集 U＝S ∪ M，再以來源宣告的靜止羽化半徑（F1 為 4 px，F2／半身／三手勢為 5 px）對 U 整體做距離線性羽化；共用素體姿勢的表情先合併二值 M，最後只羽化一次。manifest 以 missing_body_poses 明列三種缺姿勢狀態。Qt 合成數值驗收比較預乘 RGB 與 Alpha：羽化帶相對公式參考最大通道差須 ≤1；F_alpha=0（臉部核心外）與核准 A 最大差須 ≤1；F_alpha=255 處與 B′ 最大差須 ≤1。羽化帶另以 3 倍圖審查額際、太陽穴、鬢角與下巴的接縫、雙影和硬切；外觀審查結果獨立記錄。核准重組使用 F_LK；原始 RGBA 差僅供診斷，完全透明像素的 RGB 不參與數值驗收。

`--layers-root` 指向 `mohan-lk-native/.quality-tmp`，其中包含 F1／F2／H 來源，也可選擇包含 `gestures3/{pose}/`。建置器以產品原影格將 face-core 移植到核准光頭，依來源 `z_order` 建立暫存 `layer_views`，並輸出候選包 manifest、fingerprint 和 `face_core_masks`。`--mode eyes` 只產生 neutral 嘴型的 rest、half、closed 眼睛狀態；`--mode all` 另外加入 small、a、o 嘴型。全身只產生原 manifest 有列出 states 的視角，其餘視角明確保留 `rest-only`。半身缺少可對應素體幾何的姿勢不會產生，並在候選包 `inventory.json` 明列缺漏。`gestures3` 缺席時，front-eureka、front-mock-scold、front-mock-hit 保留 `missing_body_pose`。提供 gestures3 時，三個姿勢都必須各有完整來源：`bald-natural.png`、`bald-blink-half.png`、`bald-blink-closed.png`、`A.png`、`F-core.png`、`face-core-mask.png`、`hair-owned-mask.png`、`skin-owned-mask.png` 和 `garment-owned-mask.png`；任一來源不完整便停止建置。建置器各自使用來源素體建立獨立姿勢。本工單沿用「28 格先前核准」與「林可芸三個手勢同意」範圍，不重算或重新核准外觀。第七輪未預扣來源依本工單指定；舊 round9/pending metadata 保留原始狀態，不作為 round9 候選獲得外觀核准的證據。角色包 1.0.4 依附 `mohan-body-v2` 1.0.0，使用第七輪 31 個視角的 155 張 layer PNG；不封裝 MoHan 原生完整表情或姿勢影格。素體與林可芸素材採 CC BY-NC-ND 4.0，擁有者同意另於 GitHub Release 供使用者下載；本工單不執行上傳。證據見 `docs/release-evidence/lin-keyun-body-layers-approval.json`。

命令將候選包寫到指定輸出路徑，並把核准的授權識別傳給 `--license`。對每個候選輸出執行 `tools/verify_body_pack_build.py`，使用相同的 `--layers-root`，並讓 `--build-root` 指向該候選、`--output` 指向驗證報告；檢查報告與 `inventory.json` 中列出的缺漏姿勢。驗證通過只代表候選符合建置技術檢查；正式安裝和發布仍須分別通過各自授權與門檻。

```powershell
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode all --recompute-layers
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode eyes --recompute-layers
python tools/verify_body_pack_build.py --build-root "PATH_TO_ALL_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_VERIFICATION_REPORT"
python tools/verify_body_pack_build.py --build-root "PATH_TO_EYES_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_VERIFICATION_REPORT"
```

## 简体中文

产品规则：「素体」表示完整素体加上角色默认发型，只保留 base、hair-back、hair-front 与 ornament，并按声明顺序合成；body-fix、makeup、garment、look-fix 及 base_hide 均不纳入素体合成。光头素体包帧供内部叠图使用；云裳阁、桌面全身、半身、截图与导出共用有发合成画面。加载时显示加载提示，缺少头发或渲染失败时显示错误。未声明素体包的墨寒维持原帧与原发髻。

炎剑铸魂引擎只提供机制；素体包提供人物光头素体的全身、半身、眨眼和嘴型影格；角色包提供头发、服装、身体修正和妆容图层。引擎对衣着保持中立。墨寒素体 ID 是 `mohan-body-v2`，素体包与角色包分别下载；素体包按 lock 由 `tools/fetch_body_pack.py` 安装。Reader 先验证 manifest 和所有声明文件的 SHA-256，再记录 PNG 画布尺寸；只有请求影格或遮罩时才解码像素。已验证 PNG 字节使用上限 16 MiB 的 LRU 缓存，命中时仍检查文件 stat。运行期缓存保留量总上限为 64 MiB：素体验证字节 16 MiB、角色图层字节 8 MiB、pixmap 与合成图像 32 MiB、Alpha 区域 8 MiB；Qt 图像操作在 GUI 线程执行。

用户数据目录的 `body-packs/<id>/manifest.json` 使用 schema `mohan.body-pack.v1`。必填 id、字符串 version、非空 license、full_body、half_body、fingerprint。影格表以视角或姿势 ID 为键，值是 `{path, sha256}`（rest）或状态至文件记录的表。全身闭嘴是 rest、half、closed；发声是 small、a、o 加连字符与眼睛状态。仅有 rest 的视角在发声时回退至自身 rest，并记录专用 family。此 renderer 不支持 wink；wink 请求会回报 `unsupported_wink`。半身使用 neutral、small、a、o 加连字符与眼睛状态，例如 neutral-rest、a-closed；表情名称可作为姿势键，优先于 motion.pose。A 对应 a，O 和 U 对应 o，其余发声对应 small。

路径是包内相对 POSIX 路径，SHA-256 是 64 位小写十六进制。同一路径使用同一 hash。Fingerprint 为每个影格和核心遮罩建立 `(section, view, state, path, sha256)` 正规化记录；文本字段采用 Unicode NFC，按完整 tuple 排序，再以 compact JSON 数组和 UTF-8 计算 SHA-256。每条关联都会纳入，因此交换视角、状态、路径或核心遮罩都会改变指纹。可选 face_core_masks 是视角至文件记录的表，alpha 权重保护脸部核心。全身与半身分别保持一致 RGBA PNG 画布，遮罩与对应影格同尺寸。

角色 manifest 可加入 `body_pack: {id, version, fingerprint}` 和 layer_views。缺包、ID、版本、指纹或文件 hash 不符时，BodyPackMismatchError 明确报错并记录诊断。已声明角色使用素体 renderer；未声明的旧角色与服装保持原路径，墨寒默认完整影格保持原样。

Layer_views 含可选 order、layers、base_hide。Layer 为 `{kind, path, sha256, anchor: [0, 0]}`；kind 是 hair-back、body-fix、garment、hair-front、ornament 或 makeup。默认顺序是 hair-back、base、body-fix、makeup、garment、hair-front、ornament；makeup 必须在 base 之后、garment 之前。明确声明可将 base 放前，背面可将 hair-back 放 garment 后。同 kind 保持声明顺序。每视角一张 base_hide，记录为 `{path, sha256, anchor: [0, 0]}`，非零 Alpha 清除素体。所有层与遮罩同画布、同原点，列入角色 files 且 hash 一致。

H 是 base_hide：任一 H.alpha>0 都在混合前完全清除素体 B，不读取或应用 F_alpha。按 plan.order 逐项建立 X；base 项放入 H 清除后的 B，其余非 makeup 角色层以原始 alpha 一般 SourceOver 叠加。B′ 是 B 加 makeup SourceAtop，makeup 不加入 X。base 项遵循声明顺序，hair-back 没有例外；角色层 L 与遮罩 H 都不预乘 F_alpha。有图层或隐藏遮罩的视角必须有核心遮罩，无可见脸部用全透明核心遮罩明确声明。缺影格明确报错。技术验证与外观批准分开；测试、边界和 GOLDEN_MATCH 交 CI。

角色包作者契约：素体包独占脸部核心；H.alpha>0 不受 F_alpha 影响，会完全清除 B。按 plan.order 建立 X：base 项是 H 清除后的 B，所有非 makeup 角色层以原始 alpha 一般 SourceOver；B′ 是 B 加 makeup SourceAtop，makeup 不在 X 内。唯一合成公式为 R = B′ * F_alpha + X * (1 - F_alpha)，逐像素对预乘 RGBA 做线性插值。base 按声明顺序定位，hair-back 同样参与公式；L 与 H 均不预乘 F_alpha。构建时以空集合 F 生成 H＝B.alpha>0 且 A.alpha<255、L 包含 A 与 B 不同处的 A，也重画 H 清除后相同的半透明 A；保留原始分层与深度。

妆容：B′ 由角色默认的妆容包按当前选择的经典、淡妆、华丽妆或素颜应用在素体上，视角、姿势、眨眼与口型状态跟随素体帧。素颜保留原始素体；最终公式只在 F 内使用 B′，F 外的角色图层与服装保持原样。

### 构建流程

以下是候选生成参考流程，采用 --mode all --recompute-layers；复用重算图层前会核对 SHA-256。本工单使用已指定来源，不执行这套外观重算。重算沿用批准的 F1／F2／H 脚本，并将输出导向候选的 lin-keyun-layers/recomputed/。face-core 由静止遮罩非零 Alpha 包围盒计算头部 ROI：左右各外扩盒宽的 40%，上方外扩盒高的 40%，下方外扩盒高的 25%，距离向上取整并裁至画布。只在 ROI 比较各状态与静止原影格的 RGBA 最大通道差；差异须大于 8，两侧都透明时忽略 RGB。S 为静止 F 的二值核心（alpha≥128）。合并各状态差异后做 3×3 开运算，动作像素 M 限制在 dilate(S, 6 px) 内。先合并 U＝S ∪ M，再以来源声明的静止羽化半径（F1 为 4 px，F2／半身／三手势为 5 px）对 U 整体做距离线性羽化；共用素体姿势的表情先合并二值 M，最后只羽化一次。manifest 以 missing_body_poses 列明三种缺失姿势状态。Qt 合成数值验收比较预乘 RGB 和 Alpha：羽化带相对公式参考最大通道差须 ≤1；F_alpha=0（脸部核心外）与批准 A 最大差须 ≤1；F_alpha=255 处与 B′ 最大差须 ≤1。羽化带另以 3 倍图审查额际、太阳穴、鬓角与下巴的接缝、双影和硬切；外观审查结果独立记录。批准重组使用 F_LK；原始 RGBA 差仅供诊断，完全透明像素的 RGB 不参与数值验收。

`--layers-root` 指向 `mohan-lk-native/.quality-tmp`，其中包含 F1／F2／H 来源，也可选择包含 `gestures3/{pose}/`。构建器以产品原始影格将 face-core 移植到批准的光头，按来源 `z_order` 建立临时 `layer_views`，并输出候选包 manifest、fingerprint 和 `face_core_masks`。`--mode eyes` 只生成 neutral 嘴型的 rest、half、closed 眼睛状态；`--mode all` 另外加入 small、a、o 嘴型。全身只生成原始 manifest 列出的 states 视角，其余视角明确保留 `rest-only`。半身缺少可对应素体几何的姿势不会生成，并在候选包 `inventory.json` 中列明缺失项。`gestures3` 缺少时，front-eureka、front-mock-scold、front-mock-hit 保持 `missing_body_pose`。提供 gestures3 时，三个姿势都必须各自包含完整来源：`bald-natural.png`、`bald-blink-half.png`、`bald-blink-closed.png`、`A.png`、`F-core.png`、`face-core-mask.png`、`hair-owned-mask.png`、`skin-owned-mask.png` 和 `garment-owned-mask.png`；任一来源不完整就停止构建。构建器分别使用各自的素体生成独立姿势。本工单沿用“28 格先前核准”和“林可芸三个手势同意”的范围，不重算或重新批准外观。第七轮未预扣来源由本工单指定；旧 round9/pending 元数据保留原始状态，不作为 round9 候选获得外观批准的证据。角色包 1.0.4 依附 `mohan-body-v2` 1.0.0，使用第七轮 31 个视角的 155 张 layer PNG；不封装 MoHan 原生完整表情或姿势帧。素体与林可芸素材采用 CC BY-NC-ND 4.0，所有者同意另在 GitHub Release 供用户下载；本工单不执行上传。证据见 `docs/release-evidence/lin-keyun-body-layers-approval.json`。

命令将候选包写入指定输出路径，并把批准的授权标识传给 `--license`。对每个候选输出运行 `tools/verify_body_pack_build.py`，使用相同的 `--layers-root`，让 `--build-root` 指向该候选、`--output` 指向验证报告；检查报告和 `inventory.json` 列出的缺失姿势。验证通过只表示候选符合构建技术检查；正式安装和发布仍须分别通过各自授权与门槛。

```powershell
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode all --recompute-layers
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode eyes --recompute-layers
python tools/verify_body_pack_build.py --build-root "PATH_TO_ALL_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_VERIFICATION_REPORT"
python tools/verify_body_pack_build.py --build-root "PATH_TO_EYES_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_VERIFICATION_REPORT"
```

## English

Product rule: Base body means the full body composed with the character default hairstyle. Keep only base, hair-back, hair-front, and ornament in their declared order; omit body-fix, makeup, garment, look-fix, and base_hide. Bald body frames are internal composition inputs. Wardrobe previews, desktop full-body, half-body, screenshots and exports share the composed character with hair. Loading shows a loading message; missing hair or rendering failure shows an error. MoHan without a declared body pack retains the original frames and bun.

Soulforge owns mechanisms. Body packs own bald full-body and half-body frames, blinks and mouth states. Character packs own hair, garments, body fixes and makeup. Clothing is neutral. MoHan uses `mohan-body-v2`; Body packs and character packs are downloaded separately; `tools/fetch_body_pack.py` installs the body pack pinned by its lock. The reader verifies the manifest and every declared SHA-256 before use, records PNG canvas dimensions, and decodes pixels only when a frame or mask is requested. Verified PNG bytes use an LRU cache capped at 16 MiB, with a stat check on every cache hit. The retained runtime cache budget is 64 MiB: 16 MiB verified body bytes, 8 MiB verified layer bytes, 32 MiB pixmaps and composed images, and 8 MiB alpha regions. Qt image work runs on the GUI thread.

The user data directory contains `body-packs/<id>/manifest.json`, schema `mohan.body-pack.v1`. Required fields are id, string version, nonempty license, full_body, half_body and fingerprint. Frame maps use view or pose IDs, pointing to `{path, sha256}` (rest) or state-to-file maps. Full-body neutral states use rest, half and closed; speaking uses small, a or o plus a hyphen and the eye state. A rest-only view falls back to its rest frame while speaking and records a dedicated family. This renderer does not support wink; wink requests raise `unsupported_wink`. Half-body uses neutral, small, a or o plus eye state, such as neutral-rest and a-closed. Expression names may be pose keys and precede motion.pose. A maps to a; O and U map to o; other speaking visemes map to small.

Paths are relative POSIX paths. SHA-256 uses 64 lowercase hexadecimal characters. Repeated paths use one hash. Fingerprinting creates a normalized `(section, view, state, path, sha256)` record for each frame and core mask, normalizes text to Unicode NFC, sorts the records, and hashes their compact JSON arrays as UTF-8. Every binding contributes, so changing a view, state, path or core-mask assignment changes the fingerprint. Optional face_core_masks maps view IDs to file records whose alpha weights protect the core. Full-body and half-body each share an RGBA PNG canvas; core masks match their views.

Character manifests may declare `body_pack: {id, version, fingerprint}` and layer_views. Missing packs and ID, version, fingerprint or payload mismatches raise BodyPackMismatchError and produce diagnostics. Declared characters use the body renderer. Undeclared characters and outfits retain existing behavior, including MoHan's original default frames.

Layer_views entries have optional order, layers and base_hide. Layer records are `{kind, path, sha256, anchor: [0, 0]}`; kinds are hair-back, body-fix, garment, hair-front, ornament and makeup. Default order is hair-back, base, body-fix, makeup, garment, hair-front, ornament; makeup must follow base and precede garment. Explicit order may place base first and rear hair after garment. Same-kind layers keep declaration order. One base_hide per view uses `{path, sha256, anchor: [0, 0]}`; nonzero alpha clears the body. Layers and masks share the canvas and origin and match character file hashes.

H is base_hide: any H.alpha>0 fully clears body B before blending, regardless of F_alpha. Build X by walking plan.order: the base stage paints B after H clearing, and each other non-makeup character layer uses native alpha with ordinary SourceOver. B′ is B with makeup applied SourceAtop; makeup is excluded from X. The base stage follows its declared position, and hair-back has no exception; role layers L and mask H are not preweighted by F_alpha. Views with layers or hide masks require a body-owned core mask; a transparent core mask declares an invisible face. Missing frames raise. Technical checks and appearance approval remain separate; tests, boundaries and GOLDEN_MATCH run in CI.

Character-package author contract: the body pack owns the face core. Any H.alpha>0 fully clears B, independent of F_alpha. Walk plan.order to build X: paint H-cleared B at the base stage and SourceOver every other non-makeup role layer with native alpha; B′ is B with makeup applied SourceAtop, and makeup is excluded from X. The sole composition formula is R = B′ * F_alpha + X * (1 - F_alpha), a per-pixel linear interpolation of premultiplied RGBA. The base stage follows its declared position; hair-back follows the same formula. Do not preweight role layers L or mask H by F_alpha. Build with empty F: H＝B.alpha>0 and A.alpha<255; L contains A where A differs from B and repaints identical translucent A after H clears B. Preserve semantic partitions and depth.

Makeup: B′ applies the character?s default makeup pack to the body using the selected classic, light, glamorous, or bare-face option and the body frame?s view, pose, blink, and mouth state. Bare face preserves the original body. The final formula uses B′ inside F, preserving character layers and clothing outside F.

### Build workflow

The following is a reference candidate-generation procedure using --mode all --recompute-layers; reused layers are checked by SHA-256. This ticket uses its designated source without recomputing appearance. Run the approved F1/F2/H scripts and redirect output to candidate lin-keyun-layers/recomputed/. Compute the head ROI from the nonzero-alpha static-mask box: expand left and right by the ceiling of 40% of its width, top by 40% of its height and bottom by 25%, clamped to the canvas. Compare each state with rest only inside the ROI; include pixels whose maximum absolute RGBA channel difference is greater than 8, ignoring RGB when both pixels are fully transparent. S is the binary static F core (alpha≥128). Union state differences, apply a 3×3 morphological opening and restrict motion M to dilate(S, 6 px). Form U = S ∪ M before applying one distance-linear feather to the entire union with the source's static radius (4 px for F1; 5 px for F2, half-body and gestures). Expressions sharing a body pose union their binary motion masks before the single feather step. The manifest lists all three missing poses under missing_body_poses. Numeric Qt composition acceptance compares premultiplied RGB and Alpha: the feather band must differ from the formula reference by at most 1; pixels outside the core (F_alpha=0) must differ from approved A by at most 1; pixels with F_alpha=255 must differ from B′ by at most 1. Review the feather band at 3x for seams, double images or hard cuts at the forehead, temples, sideburns and chin, and record appearance review separately. Approved reconstructions use F_LK. Raw RGBA differences remain diagnostic; RGB in fully transparent pixels is excluded from numeric acceptance.

Set `--layers-root` to `mohan-lk-native/.quality-tmp`, which contains the F1/F2/H sources and may also contain `gestures3/{pose}/`. The builder transfers face-core from the original product frames to the approved bald frames, creates temporary `layer_views` in source `z_order`, and writes a candidate manifest, fingerprint, and `face_core_masks`. `--mode eyes` builds only neutral-mouth rest, half and closed eye states; `--mode all` also adds small, a and o mouth shapes. Full-body output includes views with states in the original manifest and explicitly keeps other views `rest-only`. Half-body poses without matching body geometry are omitted and listed in the candidate `inventory.json`. When `gestures3` is absent, front-eureka, front-mock-scold and front-mock-hit remain `missing_body_pose`. When provided, all three pose directories must contain complete sources: `bald-natural.png`, `bald-blink-half.png`, `bald-blink-closed.png`, `A.png`, `F-core.png`, `face-core-mask.png`, `hair-owned-mask.png`, `skin-owned-mask.png` and `garment-owned-mask.png`; an incomplete source stops the build. Each pose uses its own bald body. This ticket retains the “28 views previously approved” and “The three Lin Keyun gestures are approved” scope without recomputing or reapproving appearance. It uses the unreserved seventh-round source designated by BODY-RELEASE-1; older round9/pending metadata remains a record of its original state and is not evidence that the round9 candidate was visually approved. Character pack 1.0.4 depends on `mohan-body-v2` 1.0.0 and uses 155 layer PNGs across the 31 seventh-round views; it excludes MoHan native complete-expression and pose frames. The body and Lin Keyun assets use CC BY-NC-ND 4.0, and the owner authorized a separate GitHub Release download. This ticket performs no upload. Evidence: `docs/release-evidence/lin-keyun-body-layers-approval.json`.

Write each candidate to its designated output path and pass the authorized license identifier through `--license`. Run `tools/verify_body_pack_build.py` for each candidate with the same `--layers-root`; point `--build-root` at that candidate and `--output` at its verification report. Review the report and the omitted poses in `inventory.json`. A passing verification establishes only that the candidate meets the build's technical checks; formal installation and release still require their respective authorization and gates.

```powershell
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode all --recompute-layers
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode eyes --recompute-layers
python tools/verify_body_pack_build.py --build-root "PATH_TO_ALL_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_VERIFICATION_REPORT"
python tools/verify_body_pack_build.py --build-root "PATH_TO_EYES_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_VERIFICATION_REPORT"
```

## 日本語

製品規則：「素体」は素体フレームにキャラクターの既定髪型を重ねた表示です。base、hair-back、hair-front、ornament のみを宣言順で保持し、body-fix、makeup、garment、look-fix、base_hide は素体合成に含めません。坊主素体フレームは内部合成の入力です。衣装プレビュー、デスクトップ全身、半身、スクリーンショットと書き出しは髪を含む合成画像を共有します。読み込み中は案内を表示し、髪の欠落や描画失敗はエラーを表示します。素体パックを宣言しない墨寒は元のフレームと髷を保持します。

炎剣鋳魂エンジンは仕組みを所有し、素体パックは人物の坊主素体の全身・半身・まばたき・口形フレームを所有します。キャラクターパックは髪・服・身体修正・化粧レイヤーを所有します。衣服条件は設けません。墨寒 ID は `mohan-body-v2`、素体パックとキャラクターパックは別々に取得し、素体パックは lock に従って `tools/fetch_body_pack.py` で導入します。Reader は manifest と宣言ファイルすべての SHA-256 を検証して PNG キャンバス寸法を記録し、フレームまたはマスクが要求された時にだけピクセルをデコードします。検証済み PNG バイト列は上限 16 MiB の LRU キャッシュを使い、キャッシュヒット時もファイル stat を確認します。 実行時の保持キャッシュ上限は 64 MiB です。内訳は素体の検証済みバイト列 16 MiB、検証済みレイヤーバイト列 8 MiB、pixmap と合成画像 32 MiB、Alpha 領域 8 MiB です。Qt の画像処理は GUI スレッドで行います。

ユーザーデータの `body-packs/<id>/manifest.json` は schema `mohan.body-pack.v1` です。id、文字列 version、空でない license、full_body、half_body、fingerprint が必須です。視点・姿勢 ID に `{path, sha256}`（rest）または状態からファイルへの表を対応付けます。全身閉口は rest・half・closed、発声は small・a・o とハイフンと目状態です。rest のみの視点は発声時に自身の rest フレームへ戻り、専用 family を記録します。この renderer は wink をサポートせず、wink 要求は `unsupported_wink` を返します。半身は neutral・small・a・o と目状態、例は neutral-rest・a-closed。表情名の姿勢キーは motion.pose より優先します。A は a、O と U は o、他の発声は small です。

パスは相対 POSIX パス、hash は64文字の小文字16進数です。同じパスは同じ hash を使います。Fingerprint は各フレームと顔核心マスクの `(section, view, state, path, sha256)` 正規化レコードを作成し、文字列を Unicode NFC に正規化して、レコードをソートした compact JSON 配列の UTF-8 を SHA-256 にします。すべての関連付けを含むため、視点・状態・パス・核心マスクの変更は指紋を変えます。任意の face_core_masks は視点からファイルへの表で、Alpha の重みで顔核心を保護します。全身・半身はそれぞれ同一 RGBA PNG キャンバスで、マスクは対応視点と同寸法です。

キャラクター manifest に `body_pack: {id, version, fingerprint}` と layer_views を追加できます。欠落・ID・版・指紋・ファイル hash 不一致は BodyPackMismatchError と診断記録で明示します。宣言した人物は素体 renderer を使用し、宣言のない既存人物・服装と墨寒の既定フレームは元の処理を維持します。

Layer_views は任意の order・layers・base_hide を持ちます。レイヤーは `{kind, path, sha256, anchor: [0, 0]}` で、kind は hair-back・body-fix・garment・hair-front・ornament・makeup です。既定順序は hair-back・base・body-fix・makeup・garment・hair-front・ornament。makeup は base の後、garment の前に置きます。明示順序では base を先に、背面の hair-back を garment 後に置けます。同 kind は宣言順です。Base_hide は視点ごと一枚の `{path, sha256, anchor: [0, 0]}` で、非ゼロ Alpha が素体を消去します。全素材は同キャンバス・同原点で files の hash と一致します。

H は base_hide で、H.alpha>0 の画素では F_alpha に関係なく合成前に素体 B を完全に消去します。plan.order を順にたどって X を作り、base の位置に H 消去後の B を描き、makeup 以外の各レイヤーを元の Alpha のまま通常の SourceOver で重ねます。B′ は B に makeup を SourceAtop で重ねた結果で、makeup は X に含めません。base は宣言順に従い、hair-back に例外はありません。レイヤー L とマスク H に F_alpha を事前適用しません。レイヤーか非表示マスクがある視点には核心マスクを必須とし、顔が見えない視点は全透明マスクで宣言します。欠落フレームは明示エラーです。技術検証と外観承認を分け、テスト・境界・GOLDEN_MATCH は CI で検証します。

キャラクターパック作者の契約：顔核心は素体パックが所有します。H.alpha>0 は F_alpha に関係なく B を完全に消去します。plan.order に従い X を作り、base の位置に H 消去後の B を描き、makeup 以外の各レイヤーを元の Alpha のまま通常の SourceOver で重ねます。B′ は B に makeup を SourceAtop で重ねた結果で、makeup は X に含めません。唯一の合成式は R = B′ * F_alpha + X * (1 - F_alpha) で、乗算済み RGBA の画素ごとの線形補間です。base は宣言順に従い、hair-back も同じ式に従います。レイヤー L とマスク H に F_alpha を事前適用しません。空の F で H＝B.alpha>0 かつ A.alpha<255、L は A と B が異なる画素の A を含み、H 消去後に同じ半透明 A も再描画します。元の分層と深度を維持します。

メイク：B′ はキャラクター既定のメイクパックを素体に適用し、選択したクラシック・薄化粧・華やか・素顔と、素体フレームの視点・姿勢・まばたき・口形に従います。素顔は元の素体を維持します。最終式は F 内で B′ を使い、F 外のキャラクターレイヤーと服装を維持します。

### ビルド手順

以下は候補生成の参考手順で、mode all の再計算を使います。再利用前には SHA-256 を照合します。本チケットは指定済みの素材を使い、外観を再計算しません。承認済み F1／F2／H スクリプトの出力は候補の lin-keyun-layers/recomputed/ に保存します。静止マスクの非ゼロ Alpha 外接矩形から ROI を求め、左右は矩形幅の 40%、上は高さの 40%、下は高さの 25% を切り上げて広げ、キャンバス内に収めます。各状態と静止元フレームの RGBA 最大チャンネル差を ROI 内だけで比較し、8 を超える画素を含めます。両方が完全透明なら RGB 差を無視します。S は静止 F の二値核心（alpha≥128）です。各状態の差分を統合して 3×3 開演算を行い、動作画素 M を dilate(S, 6 px) 内に制限します。U＝S ∪ M を先に作り、元素材の静止半径（F1 は 4 px、F2／半身／ジェスチャーは 5 px）で全体を距離に基づき線形にぼかします。共通の素体姿勢を使う表情は二値 M を先に統合し、最後に一度だけぼかします。manifest は三つの欠落ポーズを missing_body_poses に列挙します。Qt 合成の数値検収は乗算済み RGB と Alpha を比較し、ぼかし領域では公式参照との差を最大 1、顔核心外（F_alpha=0）では承認済み A との差を最大 1、F_alpha=255 では B′ との差を最大 1 とします。額・こめかみ・もみあげ・顎のぼかし領域を 3 倍で目視検収し、継ぎ目・二重像・硬い切断を確認します。外観検収の結果は別途記録します。承認済み再構成は F_LK を使います。元の RGBA 差は診断用とし、完全透明画素の RGB は数値検収から除外します。

`--layers-root` は `mohan-lk-native/.quality-tmp` とし、F1／F2／H 素材を置きます。同じルートに任意で `gestures3/{pose}/` を置けます。ビルダーは製品の元フレームから承認済みの頭髪なしフレームへ face-core を移し、ソースの `z_order` に従って一時的な `layer_views` を作成し、候補の manifest、fingerprint、`face_core_masks` を出力します。`--mode eyes` は neutral の口元に対する rest、half、closed の目の状態だけを生成し、`--mode all` は small、a、o の口形も追加します。全身は元 manifest に states がある視点を生成し、その他の視点は `rest-only` として明示します。素体の形状に対応しない半身ポーズは生成せず、候補の `inventory.json` に記録します。`gestures3` がない場合、front-eureka、front-mock-scold、front-mock-hit は `missing_body_pose` のままです。ある場合、三つの姿勢フォルダーにそれぞれ `bald-natural.png`、`bald-blink-half.png`、`bald-blink-closed.png`、`A.png`、`F-core.png`、`face-core-mask.png`、`hair-owned-mask.png`、`skin-owned-mask.png`、`garment-owned-mask.png` がすべて必要です。不完全な入力があるとビルドを停止します。各姿勢は固有の坊主素体から独立して生成します。本チケットは「以前に承認された 28 視点」と「林可芸の三つのジェスチャーに同意します」の範囲を引き継ぎ、外観の再計算・再承認を行いません。BODY-RELEASE-1 が指定する未予約の第七ラウンド素材を使い、旧 round9/pending メタデータは元の状態の記録として保持します。これは round9 候補が外観承認済みである証拠ではありません。キャラクターパック 1.0.4 は `mohan-body-v2` 1.0.0 に依存し、第七ラウンドの 31 視点から 155 枚のレイヤー PNG を使用します。墨寒のネイティブ完全表情・ポーズフレームは含めません。素体と林可芸の素材には CC BY-NC-ND 4.0 を適用し、所有者は GitHub Releases での個別ダウンロードを承認しました。本チケットではアップロードを行いません。証拠：`docs/release-evidence/lin-keyun-body-layers-approval.json`。

候補ごとに指定した出力先へ保存し、承認済みライセンス識別子を `--license` に渡します。同じ `--layers-root` を使用して候補ごとに `tools/verify_body_pack_build.py` を実行し、`--build-root` を候補、`--output` を検証レポートの出力先にします。レポートと `inventory.json` の欠落ポーズを確認します。検証の合格が示すのは候補の技術的なビルド条件のみです。正式導入と公開には、それぞれの承認とゲートが必要です。

```powershell
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode all --recompute-layers
python tools/build_body_pack.py --product-root "PATH_TO_PRODUCT_FRAMES" --bald-root "PATH_TO_APPROVED_BALD" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_CANDIDATE" --license "APPROVED_LICENSE_ID" --mode eyes --recompute-layers
python tools/verify_body_pack_build.py --build-root "PATH_TO_ALL_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_ALL_VERIFICATION_REPORT"
python tools/verify_body_pack_build.py --build-root "PATH_TO_EYES_CANDIDATE" --layers-root "mohan-lk-native/.quality-tmp" --output "PATH_TO_EYES_VERIFICATION_REPORT"
```
