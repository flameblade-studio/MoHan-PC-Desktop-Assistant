# 代理能力重用索引 / Agent Capabilities Index

> **給接手的 AI 代理與未來的自己。** 本專案先後由 ChatGPT Codex 5.6 Sol、DeepSeek V4 Pro、Claude 參與，
> 產出散在 `artifacts/` 底下以 `agent-a` / `agent-b` / `agent-c` 命名的平行目錄裡。
> 每一份都具備 SHA256 釘選、exit code、驗證閘門與可重現指令；本索引提供新接手者統一入口。
>
> **動手前先讀這裡。** 本文件用來直接重用既有能力，並採用已驗證有效的路徑。

**維護規則**：發現本文件與現況有差異時，**修正本文件**。新增能力或驗證出適用邊界時，補上一列。

---

## 一、已建成的能力（直接重用）

> ### `artifacts/` 採本機保存，幾何控制權威產出納入版本控制
>
> `.gitignore` 預設排除 `/artifacts/`（該目錄本機約 20 GB，多為虛擬環境、可重新
> 下載的模型、隔離 worktree 與可重建的發行封存），但**幾何控制的權威產出已納入
> 版本控制**，共 725 檔／54.2 MB——那是具唯一性的權威產出。
>
> **原始 NetPBM 採本機可重建形式（`.ppm` / `.pgm`，180 MB）**：光柵化器是確定性的
> （固定正交相機、無隨機性、輸入頂點與面皆 SHA256 釘選），可用庫內的執行檔位元
> 重生並比對已記錄的雜湊。重生指令與預期輸出見
> `allowed-15deg-control-path-audit-agent-a/audit.json` 的 `fresh_regeneration_next_step`。
>
> **`.gitattributes` 對 `artifacts/pose-atlas-rebuild/**` 固定採二進位處理**——換行正規化
> 會改動位元組並使 `sha256-sums.txt` 與 `audit.json` 記錄的雜湊全部失效。**這條規則維持整條證據鏈的位元組一致性。**
>
> `artifacts/` 位於打包白名單範圍之外（`build.ps1` 以 `--add-data` 逐項指定，Inno Setup 的
> `SourceDir` 指向 PyInstaller 產出目錄），**納入版控後，安裝檔大小維持原值**。注意 `assets/`
> 是整個目錄照收——放進 `assets/` 的東西會被打包進安裝檔。
>
> 產線腳本（`lora_loader.py`、`chroma_mass_produce_v9.py` 等）統一位於本機 scratchpad。

| 能力 | 位置 | 實況 |
|---|---|---|
| **授權乾淨的 24 視角幾何控制** | `artifacts/pose-atlas-rebuild/2026-08-25/candidate3-formal-controls-bundle-agent-a/formal-controls/` | 72 個 PNG＝24 視角 × silhouette／depth／normal，1024×1536，真 15° 步進。**自寫 CPU 光柵化器**＋MHR 網格（Apache-2.0）＋ufbx（MIT），稽核記載 `prohibited_components_used = 0` |
| **更完整的控制套件** | `artifacts/pose-atlas-rebuild/2026-08-26/canonical24-control-bundles-agent-b/bundles/yaw*/` | 另含 `base-render`、`shaded-render`、`part-id`、`ownership-{anatomy,hair,ornament,outfit}` 四層遮罩、`jaw13-conditioning`、`ornament_mask`、`registration-anchor.json` |
| **確定性軀幹形變器** | `artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/body-morph-candidate3/` | 168 cm 身高下命中 bust 86／underbust 71／waist 62／hip 90，**全部誤差 ≤ 0.5 cm**。SciPy CubicSpline C2＋以骨架為中心的局部徑向縮放 |
| **控制路徑授權稽核** | `artifacts/pose-atlas-rebuild/2026-08-25/allowed-15deg-control-path-audit-agent-a/audit.json` | 裁決 `USE_EXISTING_CANDIDATE3_CPU_FORMAL_CONTROLS`，含相依套件授權判定與 `blocks_and_limits` |
| **README 媒體資產** | `docs/media/` | `mohan-hero.png`（1600×900）、六張功能截圖（含 `security-permissions.png`）、`mohan-demo.mp4`（正常語速隨音訊，二代 OneCore/Yating）、`mohan-demo.gif`（1.45 MB）、三張支持者立繪（640×640）。**全部由 `tests/test_readme_media.py` 以 CI 強制** |
| **授權出處證據鏈** | `docs/LICENSE-PURITY.md`（對外總覽）、`docs/LICENSE-BLACKLIST.md`、`ASSETS-LICENSE.md`、`THIRD_PARTY_NOTICES.md`、`THIRD_PARTY_DENYLIST.json`、`docs/{VISION,MULTIMODAL,HAND}-MODEL-PROVENANCE.json`、`docs/UI-ASSET-PROVENANCE.md`、`third_party_licenses/` | 隨產品出貨的八個模型全部 MIT 或 Apache-2.0，**每顆以 SHA256 與上游 commit 雙重釘選** |
| **能見度量測** | `tools/measure_visibility.py` | 一鍵產出月報指標並對照 2026-08-30 基準；自動標記 0 資產的 release。需已登入的 `gh` |
| **臉部偵測／視角驗證** | `assets/vision-models/face_detection_yunet_2023mar.onnx`（YuNet, MIT） | 用於臉譜稽核、視角自動驗證、臉部細修裁切、訓練集視角分布量化 |
| **外觀 port 與停用適配器／外观 port 与停用适配器／Appearance port and disabled adapter／外観 port と無効 adapter** | `application/appearance_ports.py` | 新增 `OutfitOverlayPort` protocol 與維持原外觀的 null adapter；由 `tests/test_null_outfit_overlay.py` 覆核眨眼 eye-state 參數契約，供 composition root 注入／新增 `OutfitOverlayPort` protocol 和保持原外观的 null adapter；由测试覆核眨眼参数契约，供 composition root 注入／Adds the `OutfitOverlayPort` protocol and an appearance-preserving null adapter; the null adapter’s eye-state contract is covered by the test and is injected at the composition root／`OutfitOverlayPort` protocol と既存外観を維持する null adapter を追加し、眨眼の eye-state 契約をテストで確認して composition root から注入 |
| **半身眨眼妝容後疊／半身眨眼妆容后叠／Half-body blink makeup compositing／半身まばたきメイクの後段合成** | `infrastructure/blink_makeup_composition.py` | `paint_blink_makeup` 在已註冊眼皮 patch 後，以原生 half-body 畫布疊加眼妝；`tests/test_half_body_blink_makeup_order.py` 覆核 patch 內外像素與輸入不變／`paint_blink_makeup` 在已注册眼皮 patch 后以原生半身画布叠加眼妆；测试覆核 patch 内外像素与输入不变／`paint_blink_makeup` composites authored eye pigment after the registered eyelid patch on the native half-body canvas; the test checks pixels inside and outside the patch and input immutability／`paint_blink_makeup` は登録済みまぶた patch の後に原生半身 canvas へアイメイクを合成し、patch 内外の画素と入力不変性をテストで確認 |

### 產線腳本（本機 scratchpad）

`lora_loader.py`（ai-toolkit→diffusers 鍵名轉換，掛不上即拋錯）、`chroma_mass_produce_v9.py`（24 視角 t2i＋內建 YuNet 驗證）、`face_detailer.py`＋`run_face_detail_v9.py`（臉部放大重繪貼回）、`mirror_positive_views.py`、`measure_rotation*.py`、`geo_conditioning_probe.py`。

---

## 一之二、幾何條件化：已驗證可行的配方（2026-08-31）

純 t2i 的適用範圍是粗方位；**把 3D 控制圖當 img2img 初始圖，可提供精確鏡頭角度控制**。
授權上完全乾淨，直接使用 `ChromaImg2ImgPipeline` 與庫內既有的控制圖。

| 參數 | 值 | 依據 |
|---|---|---|
| 初始圖 | `*_shaded-render.png` 的明暗 **× 膚色重映射**，裁到人物並補到 2:3 | 灰模原樣會讓輸出一路灰皮膚，見下方「顏色是低頻」 |
| strength | **0.85** | 六檔量測中唯一同時守住幾何與完成上色的一檔，見下表 |
| LoRA 權重 | 0.85 | 1.0 壓不住髮型、0.70 正面臉型變窄 |
| 尺寸 | **顯式傳 `height=1248, width=832`** | 不傳會退回 1024×1024 方形，見下方「一定要顯式傳」 |
| 手臂措辭 | 提示詞需明確指定 | 原提示詞完全沒寫手臂，姿勢全交給模型先驗，各視角不一致 |

### 顏色是低頻，頭髮跟著顏色走

灰模初始圖在 0.55～0.85 全程輸出灰皮膚且光頭，**提高強度的實測結果維持灰色低頻先驗**——
前景彩度全程貼著灰模自身的 0.120 不動。原因是顏色屬低頻訊號，加噪後存活最久，
而初始圖的低頻先驗說「這是一尊灰色的東西」。

**光頭現象的歸因需與「網格沒有頭髮」分開**（本輪一度這樣推論）。實測把灰模染成
膚色、其餘完全不變，輸出自己就長出了合規髮型（後梳髮髻、後頸裸露）。
**主導變因是灰色低頻先驗；頭髮幾何是另一項變因。** 額外在頭頂補低頻暗色髮罩會讓髮量更飽滿，
但同時把手臂帶成交握身前——同種子同強度只換初始圖的對照可證。

### 強度選擇：以剪影 IoU 為準

以 yaw+090 為例，控制遮罩取自 bundle 的 `_silhouette.png`（控制遮罩固定採 bundle 的權威剪影，灰模門檻推導僅供比較，
灰模亮部與淺灰底板太接近會把剪影侵蝕約 8%）。彩度是前景平均飽和度，
用來判斷風格轉換完成了沒有。

| strength | 幾何 IoU | 彩度 | 實際長相 |
|---|---|---|---|
| 純 t2i 基準 | 0.396 | 0.206 | 幾何無關，這是「隨便畫個人剛好重疊」的下界 |
| 0.55 | 0.863 | 0.117 | 灰模原樣通過，完全沒轉換 |
| 0.65 | 0.814 | 0.134 | 已是女性、泳裝長出，但全身灰、光頭 |
| 0.75 | 0.876 | 0.149 | 同上 |
| **0.85** | **0.839** | **0.177** | **手臂自 A-pose 垂回身側、皮膚有真實質感、側面精準** |
| 0.95 | 0.325 | 0.123 | **低於基準**，幾何完全脫鉤 |

灰模自身彩度 0.120 是風格軸的下界。0.55–0.75 三檔全貼著它，代表**單靠提高強度
維持灰色低頻先驗**——顏色是低頻訊號，初始圖是灰的就一路灰。同理，網格的頭髮低頻訊號為空時，
輸出會延續相同先驗，0.65 到 0.85 全程光頭。

**推論**：要同時拿到幾何與外觀，得修初始圖的低頻先驗，而不是調強度——
把灰模的明暗當光照、顏色換成膚色，並在頭頂補一塊低頻暗色髮罩。

### 修正：strength 0.95 的幾何條件化接近零

本表原本寫 strength 0.95，理由是「0.70／0.80／0.88 皆殘留人偶體型，0.95 才乾淨」。
觀察無誤，**後續量測修正了原結論**。diffusers 的 img2img 起點由這兩行決定：

```python
init_timestep = min(num_inference_steps * strength, num_inference_steps)
t_start       = int(max(num_inference_steps - init_timestep, 0))
```

`steps=34、strength=0.95` 時 `t_start = 1`——34 步只跳過 1 步，初始圖被加噪到幾乎全是雜訊。
低強度之所以「殘留人偶體型」正是因為幾何有進去；0.95 之所以「乾淨」是因為**幾何完全沒進去**。

實測佐證：拿兩張構圖差異極大的初始圖（人物佔畫面 9% 與 17%）餵同一個種子，
**輸出只差 2.1% 的像素、平均色差 2.0／255**。

這個實驗的證據範圍是**構圖與比例保留率接近零**；初始圖仍保有局部色彩作用——
同一份證據樹裡的腳掌翹起現象顯示，normal map 與灰模在 0.95 下仍會產生系統性差異，
可見低頻色彩訊號還是滲得進來。要主張的精確版本是：
**0.95 保不住幾何構圖，只留下一點局部色彩偏壓；而後者恰好是有害的那半。**

**教訓**：選 strength 同時使用視覺品質與可證偽指標，直接量
「幾何有沒有進去」——例如輸出剪影與控制網格剪影的 IoU，並且要跟純 t2i 基準比，
如此可排除「隨便畫個人剛好也會重疊」。

### 上表的適用範圍是 yaw+090

必須先標明範圍：那六檔量測全部來自 **yaw+090 一個視角**。把「0.85 是唯一同時
成立的一檔」需由其他視角逐一驗證後才擴大適用範圍——**正面視角在 0.85 會翻成背面**，
連續兩次，眼距比 0.077 與 0.081。

### 兩段式 img2img 分別完成幾何與外觀

yaw+000 是最難的視角，證據在它身上最完整：

| strength | 幾何與方位 | 外觀 |
|---|---|---|
| 0.55–0.75 | 守得住 | 壞掉：灰皮膚，或臉糊掉、胸部結構錯誤 |
| 0.85 | 側面守得住，**正面翻成背面** | 好 |
| 0.95 | 完全脫鉤（IoU 0.325 低於基準 0.396） | 好 |

此現象由兩個不同階段分別處理，是同一個物理量的兩面：**正反與五官都住在高頻，
而高頻在加噪後最先消失**。強度低到能保住方位，就低到留著灰模那張沒有五官的臉；
強度高到能長出五官，就高到讓模型改用自己的方位先驗。

**繞開的方法是分兩段**：第一段低強度鎖定幾何與方位，第二段以第一段的輸出
當初始圖修外觀——此時初始圖已是一張方位正確的人物照片，低頻先驗本身就
指向正確方位，第二段才能用較高強度修臉而維持正確方位。

### 兩段式：架構已驗證成立（2026-08-31）

以 yaw+000 這個最難的視角實測：

| 階段 | 眼距比（正反） | 頸下 IoU（幾何） |
|---|---|---|
| 第一段 s0.75（染色保留對比 + 髮量提示） | 0.481 | 0.671 |
| 第二段 s0.45（以第一段輸出為初始圖） | 0.444 | 0.670 |
| 第二段 s0.60 | 0.466 | 0.667 |

**第二段的幾何 IoU 變化為 0.004**（IoU 變化 0.004），卻明顯改善膚質與臉部。
兩段式確實把「保方位」與「修外觀」拆成職責分離的兩步。
同一視角的單段結果保留以下限制——0.85 會翻面，0.75 若染色壓縮明暗則臉會糊。

### 成品會繼承網格的一切，包括其既有幾何特徵

閉眼與低頭來源是控制網格的既有臉部狀態——**控制網格的臉本來就是閉眼的**，幾何條件化
忠實地搬了進來。與四肢問題同源。臉部可用既有的 `face_detailer`
（只重繪臉框區域、羽化橢圓貼回）修正並保持身體原狀；四肢則由形變器處理。

### candidate4：四肢圍度形變（2026-08-31，擁有者選定 P25）

擴充可形變區域是有解的，且不必動到已核可的軀幹。做法沿用 candidate3 的形狀
——沿一條軸做連續局部縮放——只是軸從「垂直的 y」換成「沿骨鏈的弧長」。

**分區直接採用 skin cluster 的逐頂點解剖 ID。** `skin-weight-parts-agent-a` 已從 MHR FBX 的 127 個
真實 skin cluster 推出逐頂點解剖 ID（明確覆蓋 97.97%），直接用它。
**375 個關節模糊頂點（part 255）必須跟著最近的肢鏈一起動**——第一版把它們
排除在形變外卻納入量測，上臂因此少縮了一半，關節處也會留摺痕。

**量測必須垂直骨軸。** A-pose 下手臂是斜的，水平切面量到的是斜截面。

**診斷結果比「四肢偏男性」精確得多**：對照中國成人女性 20-29 歲的 3D 體掃常模
（Alpha3Ds，n=215，PMC12620412），上臂 34.4 cm 落在 **第 94 百分位**，前臂約 P80，
而大腿與小腿只在 P60——**腿是正常的，問題幾乎全在手臂**。軀幹的腰圍 62 cm
約在 P10，這 84 個百分位的落差就是體態讀起來怪的來源。

**臀圍會被大腿縮放連帶改掉。** 大腿頂端在 88.1 cm、臀圍量測面在 84 cm，兩者重疊；
收斂起點若從弧長 0 起算，跨過量測面時尚未收斂完成，臀圍被改掉 0.15 cm。
把收斂起點推到量測面之下即可，改後偏差 0.0008 cm。

**大腿結果由髖部 1.0 保護條件決定**：最粗處緊貼髖部，而那裡必須維持 1.0 以保住
核可的臀圍 90.07。**肩寬變化實測為 −1.3%**（−1.3%）——肩綁在鎖骨與軀幹上，不是手臂。

### 幾何條件化的美術上限，由控制網格的四肢決定

兩段式產出的角度受控，但體態偏運動員、肩線偏寬——這是形變器可動頂點範圍所決定的結果，
再怎麼調強度、換種子、改提示詞都一樣。原因在形變器自己的報告裡：

```
central_torso_component.eligible_vertices : 1731
protected_zero_weight_vertices           : 16708
protected_vertices_max_displacement      : 0.0
```

18,439 個頂點只有 **1,731 個（9.4%）可形變，且全部集中在軀幹**。形變器把胸腰臀圍
調到 86/71/62/90（誤差 ≤0.5 cm），但**肩、臂、腿、臉共 16,708 個頂點位移恆為零**，
原封保留基礎網格的偏男性比例。幾何條件化會忠實地把它們搬進成品。

**所以下一步投入四肢形變。** 現有架構的適用範圍是軀幹——
保護區是硬性零位移，需要擴充可形變區域並重新驗證斷面量測。

### 說「這是 X 的代價」之前，先確認 X 是唯一的變因

本輪一度判定「strength 0.75 會讓臉糊掉，那是低強度的代價」。實際上糊臉來自
**染色實作把明暗動態範圍壓掉 28%**，與強度無關——把染色改成保留對比後，
同樣的 0.75、同樣的種子、同樣的提示詞，臉就完整了，而且方位正確。

歸因給某個參數之前，先列出兩次執行之間**所有**改變的東西。本輪同型錯誤
出現六次，全部都是觀察無誤但歸因接錯人。

### 染色維持完整明暗動態範圍

把亮度重映射到窄的膚色帶會把動態範圍從 148 壓到 106（**少 28%**），
而明暗正是承載正反 3D 資訊的訊號。為了給對顏色先驗反而削弱判別正反的線索。
改成只換色度、亮度沿用灰模，動態範圍 168、前景彩度 0.220，兩軸都更好。

### 正反判斷採眼距比，剪影 IoU 與臉部偵測負責其他指標

幾何條件化守得住細角度，卻分不出正面與背面——A-pose 的正反剪影幾乎相同。
實測：yaw+000 的**正面**控制圖產出了**背面**，而頸下 IoU 仍給 0.573，遠高於門檻。

臉部偵測也救不了。YuNet 的信心分數在正反之間完全不可分（正面 0.932、背面 0.891），
而且它會在背面的髮髻上偵測出「臉」，臉部面積也重疊（正面 0.0109、背面 0.0061~0.0069）。

目前能清楚區分的量是**眼距佔臉寬**：正面 0.511，各種背面落在 0.077~0.277。
以 0.35 為門檻可攔下正反顛倒。**但正面樣本只有一個**（v9 yaw+000），
n=1 訂出的門檻定位為絆線，正式證明仍由量產目視覆核成立，量產後仍須目視覆核。

### 粗方位使用提示詞，細角度使用幾何

v9 量測證明提示詞的適用範圍是正面／四分之三／側面／背面
的粗分（v9 的 yaw+000 確實是正面）。幾何條件化恰好相反。
撰寫量產腳本時把方位措辭整個拿掉，正是上述正反顛倒的直接原因。

### 既有有效元素由反證驅動變更

v9 每個視角都帶方位措辭，那是已驗證有效的部分（v9 的 yaw+000 確實是正面）。
撰寫 v10／v11 時把它整段拿掉，理由只是「幾何條件化應該就夠了」——
當時的實測支持數為 0。代價是連續兩次量產在第一張就翻面。

改寫既有產線時，先分清楚哪些是**已被證明有效**、哪些是**只是慣例**。
前者的變更以前置反證為條件。

### 閘門自己必須先被驗證

本輪的閘門出過三個錯，每一個都會讓整批量產帶著缺陷跑完或中途炸掉：

| 閘門的錯 | 症狀 | 根因 |
|---|---|---|
| `person_count` 把一個人數成兩人 | 正確的圖被擋下 | 用灰階、門檻 18，而淺膚色頸部亮度 205 與背景 194 只差 11，被判成背景，頭與身體因此斷開 |
| 尺寸對齊後比較 | 量產中途整批崩潰 | 影像與控制遮罩在比對前需要完成尺寸對齊 |
| 正反顛倒被放行 | 缺陷混進成品 | 當時只查「背面臉部可見度」，正面臉部可見度與檢查有效性也需納入（見上節） |

**做法**：閘門寫完後，先拿既有的正例與反例各跑一遍，確認判讀方向正確再出跑。
反例要包含實際觸發過缺陷的圖。

另記錄兩個實測閘門邊界，兩者都不是「判讀錯」而是「根本沒在看」：

| 缺陷 | 症狀 |
|---|---|
| **守備範圍有空洞** | 只檢查 \|yaw\|≤22 與 ≥150，23–149 度無人看守。yaw+030 產出背面、眼距比 0.034（比任何背面樣本都低）卻被判通過 |
| **只在第一張判定** | 角度相依結果需要逐張判定；第一張通過後仍持續檢查 |
| **未通過圖使用隔離檔名** | 續跑時被當成已完成而略過，缺陷靜默留在成品裡。未通過圖統一改名歸檔 |

**閘門的守備範圍要涵蓋完整參數值域與已知邊界。**
寫閘門時列出參數的完整值域，逐段問「這一段出錯會長什麼樣、我查得到嗎」。

### 配方變更後重新檢視所有既有排除紀錄

相同配方下直接略過已驗證排除的重試組合（生成是確定性的，同參數同種子必得同圖），
但那個機制以「同視角同嘗試序號」為鍵，**適用前提是配方相同**。
2026-08-31 改了方位措辭之後，舊的 `_rejected-*-tryN.png` 轉為舊配方證據——
留著會讓新措辭的第一次嘗試被錯誤跳過，而那次嘗試很可能才是對的。

處置是改名為 `.stale-recipe.png` 而非刪除：保留證據，同時讓該視角從頭重跑。

### 背面段同時檢查頭部與身體方位一致性

yaw+105 產出「身體 105 度但頭轉回鏡頭」：角度、服裝、人數全部合格，
單看那一張也好看，**做成轉盤才顯得突兀**——只有那一格的視線朝前。
擁有者一眼看出，而當時六道自動檢查的涵蓋範圍缺少「一致性」。

根因不只是缺檢查，是措辭：`orientation()` 的側面帶原本到 112 度，
於是 105 度拿到「pure side profile, **her face in profile against the
background**」——那句話本身就在留住臉，而 105 度物理上已轉進背面段。
帶界改為側面 68–97、背面 98–157 後，105 度改拿「her face turned away」。

**邊界要成套地改**：`orientation_negative()` 原本在 113 度才停止排除背面，
於是 98–112 度會同時拿到「從背後看」的正向詞與「不要從背後看」的負向詞，
兩者直接打架。改一個帶界就要檢查所有以角度分段的地方。

閘門新增：95–149 度的眼距比須 < 0.30（合格背面段實測 0.000/0.059/0.125/0.218，
頭轉回來的是 0.351/0.378）。兩側餘裕僅約 0.08，樣本也少，定位為絆線，正式證明仍由量產目視覆核成立。

### 量產程序以單一實例執行

2026-08-31 實際發生：修完閘門後直接啟動新的量產，**在前一個仍運作時啟動新實例**。
兩個程序同時佔用 GPU（15.2 GB＋18.8 GB）並交錯寫入同一個輸出目錄，
結果新程序判定通過的 `body2-yaw+120.png` 被舊程序的重試邏輯改名成
`_rejected-try2`——**兩個程序的交錯寫入覆蓋了合格產出**。

症狀是時間戳錯序：`_rejected-yaw+120-try2.png` 的時間晚於 `body2-yaw+135.png`。
單看日誌看不出來，日誌只顯示「通過」而檔案不存在。

**工程修法是在腳本加入單一實例鎖**：量產前檢查鎖檔，
偵測到另一個實例就直接退出。程序會自動維持單一實例條件。

### 方位措辭必須明白斷言正面

`"turned to a three-quarter angle with one shoulder toward the camera,
her face still visible"` 讀起來像正面四分之三，**而背面四分之三同樣符合該句語意**
——一邊肩膀確實朝向鏡頭，側臉確實可見。實測 yaw+030 就這樣被模型的背面先驗
奪走；而 0°／15° 因為措辭裡有「her chest and navel toward the camera」這句
明確斷言而守住。

改成每個非背面段落都明寫「the front of her chest and her navel are visible,
her back is away from the camera」，並在 |yaw| < 113 時於負向詞加上
`seen from behind, back view, rear view`，眼距比從 0.034 回到 0.337。

`ChromaImg2ImgPipeline.__call__` 的預設是 `height = height or self.default_sample_size * self.vae_scale_factor`。
**省略尺寸時會使用 1024×1024 預設值；初始圖尺寸不參與此預設。**
2:3 的初始圖被壓成正方形後，方形畫布誘導模型畫成「正面＋側面」的角色設定表，
一張圖裡出現兩個人；同樣的提示詞在 832×1248 下從未出過這個問題。
負向詞（`multiple people, twins, split screen`…）對此構圖結果的影響有限——那是構圖問題不是語意問題。

### 初始圖採用 shaded render

實測 strength 0.90 與 0.95 兩檔，**normal map 都造成系統性的腳掌翹起**（腳跟離地、腳尖下壓），
灰模在同樣強度下雙腳平貼。成因是 normal map 在腳背與腳趾之間有劇烈色相斷層，
模型把該色帶讀成「腳尖朝下的表面朝向」；灰模只有平滑明暗漸層，讀起來就是平放的腳掌。
**推論：任何法線劇變的部位（腳、手指、下顎、肩線）都可能被 normal map 誤讀成姿態。**

先前 2026-08-26 的 `yaw090-flux-img2img-lora-3d-agent-d` 用 normal map ＋ FLUX.1-schnell ＋
strength 0.90，產出美術品質良好但識別度漂移（其 depth 變體已被標記
`REJECTED_IDENTITY_DRIFT`）——該實驗使用的是側臉權威注入之前的 identity LoRA。

**變因分離的教訓**：本輪一度誤判「normal map 優於灰模，因其體型訊號較少」。
把灰模也拉到 0.95 當對照組才發現**主導變因是 strength 而非初始圖種類**，
兩者在 0.95 下體型同樣纖細。差別只在腳部誤讀。

## 一之三、模型評估與採用邊界（2026-08-31）

**Chroma-DC-2K —— 授權條件位於商用允收範圍之外。** 只存在於 `lodestones/chroma-debug-development-only`，
該 repo 的 README 前置欄位是 `license: cc-by-nc-sa-4.0`，同時觸及非商用與
share-alike 兩條紅線，且自述「purely for research purpose」。repo 明說
「once it's ready it will be uploaded to a separate repo under apache 2.0 license」
——**Apache 2.0 版本狀態為待發布**。轉載站上的重新上傳不改變上游授權。
技術上 DC 是 DC-AE（深度壓縮自編碼器），換掉的是 VAE，所以現有的 identity LoRA
與今晚整套門檻都要重新校準，需要完整重新校準。已列入 `docs/LICENSE-BLACKLIST.md`。

**Chroma1-Radiance —— 授權符合 Apache 2.0；技術採用條件仍待完成。**
三個理由由重到輕：

1. **diffusers 的像素空間 Chroma 管線狀態為待提供**。只有 `ChromaPipeline` 與
   `ChromaImg2ImgPipeline`（潛在空間）。Radiance 目前需要 ComfyUI 的功能分支，
   而 ComfyUI 已由擁有者裁決完全出局。採用前提是具備允收的像素空間管線。
2. **checkpoint 每小時更新**，作者自述「expect some squiggles on the details part
   of the image」。本專案的產線建立在 SHA256 釘選的證據鏈上，
   **治理要求基底版本固定並具可驗證 SHA256**。
3. 早期實測回報比 Chroma1-HD 慢 30%+、提示詞遵循度較差（2025-09，可能已改善）。

**它的方向仍值得追蹤**：像素空間、無 VAE，消除的正是壓縮失真，而全身圖裡臉只有
約 106 px，那正是壓縮失真最傷的地方。等它出穩定版且 diffusers 支援後重評。

**Chroma1-HD 為何是目前的正解**：同時滿足三個彼此拉扯的條件——Apache 2.0 乾淨、
diffusers 原生支援 img2img（今晚整條幾何條件化的前提）、8.9B 經 GGUF Q4_K_M
量化後峰值約 8.5 GB，16 GB 顯存跑得動且留得下 LoRA 與兩段式的空間。

**篩選前沿模型的兩道關**：授權白名單，以及「可否釘選」。DC-2K 兩關皆不過，
Radiance 過第一關、不過第二關。

## 二、已驗證的決策邊界（採用有效替代方案）

| 嘗試過的做法 | 結果 | 證據 |
|---|---|---|
| **Flux 系 ControlNet 做角度控制** | **位於授權允收範圍之外** | XLabs／InstantX／Shakker-Labs／Jasper 全系皆 flux-dev 衍生，非商用條款傳染。見 `docs/LICENSE-BLACKLIST.md` |
| **用提示詞控制精確鏡頭角度** | **已驗證結構性限制** | 一代與二代 atlas 記載「壓縮成約三群」；2026-08-31 對 v9 的 24 張逐張量鼻眼偏移，實測是**只有兩個狀態**：yaw+000 為 −0.04，而 +015 到 +105 全落在 +0.50～+0.62（全距的 82% 集中在 0°→15° 那一跳）。並排對照確認身體也沒轉。所謂 17 張可用素體，實測角度數為 2 |
| **`rotated N degrees to her right / left`** | **實測左右辨識率為 0** | ±yaw 四組對照全部面向同一邊。以角色為基準的方位模型做不到；改用畫面相對措辭，或只生成一側再水平鏡像 |
| **背面段（\|yaw\| ≥ 135）避免露臉** | **三種手段實測通過數為 0** | ①負向禁令（v8，7/7 失敗）②語意正向描述（v9，7/7 失敗）③幾何錨點「鼻子與腳趾同向」＋部位級負向詞＋三組新 seed（7/7 失敗）。**後續直接採用幾何控制與目視覆核** |
| **LoRA caption 寫入髮型或服裝** | **綁進身份** | 權威圖 caption 誤寫 `with long black hair`，導致 LoRA 把長髮學成身份，權重 1.0 時任何提示詞壓不住。補救是降權重至 0.85 |
| **LoRA 權重降到 0.70 換嘴形** | **正面臉型跑掉** | 側面看不出差別，正面明顯變窄變尖。**降權重前必須測正面**，側面不足以判斷 |
| **img2img 以既有人像當底稿** | **底稿身份壓過 LoRA** | 側面「像別人」，是 v8 起改為純 t2i 的原因。註：無材質灰模是否適用尚未定論（探針進行中） |
| **`FILE_ATTRIBUTE_PINNED` 觸發 iCloud 背景下載** | **實測下載數為 0** | 120 檔釘選後 10.5 分鐘零下載。iCloud for Windows 只在檔案被實際讀取時水化，不理會 OneDrive 那套釘選語意 |

### 授權具名隔離清單

ComfyUI（GPL-3.0）、Krita（GPL-3.0）、SD WebUI Forge／reForge／SD.Next（AGPL-3.0）、SwarmUI、nvdiffrast（非商用）、OpenPose 官方實作（商用年費 US$25,000）、FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系、Illustrious-XL／NoobAI-XL、Pony Diffusion 系、SD3／SD3.5、Hunyuan 影像系、InstantMesh、Zero123++、CC BY-SA 素材。完整清單見 `docs/LICENSE-BLACKLIST.md`。

---

## 三、會咬人的治理閘門

| 閘門 | 硬性要求 |
|---|---|
| `tests/test_readme_media.py` | 九個認證徽章必須是全檔**第一個** `<p align="center">` 區塊且順序完全相符；語言導覽列恰好四次；十個 PNG 與 `mohan-demo.mp4` 全部被引用；支持者立繪固定 `width="220" height="220"`；`width="33%"` 對齊格恰 3 次、`width="25%"` 恰 4 次；README 的作者資訊維持非時效性 |
| `tools/check_four_language_docs.py` | H1 需四個標題以 `／` 分隔；**唯一允許的 H2 是四個語言名稱**，子章節請用 H3；各語言段維持相互獨立；**行內程式碼必須跨語言一致**（曾因中文段少一組反引號而失敗）。內部 AI 對 AI 文件可加入 `NON_DOCUMENT_BASENAMES` 豁免 |
| `tools/migrate_python315_imports.py --check` | 新增 import 一律用 `lazy import` / `lazy from`，否則 `EAGER_ELIGIBLE` 會擋 |
| 在地化完整性測試 | `self._t()` 的 key 必須是字面量，統一使用字面量 |
| 棘輪行數閘門 | 新檔 800 行、既有檔基線只降不升、絕對天花板 1200。瘦身低於基線時**必須在同一 PR 下修基線** |

---

## 四、環境陷阱

- **PowerShell 5.1 讀 `.ps1` 需要 UTF-8 BOM**，否則含中文的腳本會以 cp950 解讀而語法崩潰。`$args`、`$pid` 是自動變數，保留為 PowerShell 自動變數。
- **Bash 工具會吃掉 Windows 路徑中的 `\a`、`\b`** 等跳脫序列——Windows 路徑一律用 Python 端組字串或 Write 工具。
- **同時啟動多個重工作會互相拖垮**：兩個 Chroma 管線搶一張 16 GB 顯卡會讓後者靜默 OOM；大量磁碟 I/O 會讓 LoRA 訓練從 8 秒／步退化到 113 秒／步。**啟動前先查現有負載。**
- **共用 worktree 紀律**：多 session 共用同一個 repo，動分支前先看 HEAD，修補另開 worktree，統一使用可追蹤的獨立 worktree。

---

## 五、給下一個代理的四項作業原則

1. **陳述現況前，先跑當下檢查。** 本專案的完成度高於一般專案，預設「缺失」會系統性地猜錯。
2. **全域結論使用全域證據。** 讀 README 前 25 行不等於讀過 README。
3. **指標通過自我驗證後再報數字。** 例：剪影寬度指標若量出「正面比側面窄」，那是指標壞了，代表指標需要修正。
4. **比較兩張圖的某個特徵前，先確認其他變因相同。** 否則會把污染變因誤判成主因，並為此付出額外代價。
