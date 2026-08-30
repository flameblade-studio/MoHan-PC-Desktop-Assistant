# 代理防重工索引 / Agent Capabilities Index

> **給接手的 AI 代理與未來的自己。** 本專案先後由 ChatGPT Codex 5.6 Sol、DeepSeek V4 Pro、Claude 參與，
> 產出散在 `artifacts/` 底下以 `agent-a` / `agent-b` / `agent-c` 命名的平行目錄裡。
> 每一份都嚴謹（SHA256 釘選、exit code、驗證閘門、可重現指令），但**沒有一個新來的人會自然讀到的入口**。
>
> **動手前先讀這裡。** 本文件的唯一目的是阻止「重造已存在的輪子」與「重試已證明失敗的路」。

**維護規則**：發現本文件與現況不符時，**修正本文件**，不要繞過它。新增能力或證明某條路走不通時，補上一列。

---

## 一、已建成的能力（不要重做）

> ### `artifacts/` 大部分不入庫，幾何控制的權威產出例外
>
> `.gitignore` 預設排除 `/artifacts/`（該目錄本機約 20 GB，多為虛擬環境、可重新
> 下載的模型、隔離 worktree 與可重建的發行封存），但**幾何控制的權威產出已納入
> 版本控制**，共 725 檔／54.2 MB——那是唯一不可重製的部分。
>
> **未入庫的是原始 NetPBM（`.ppm` / `.pgm`，180 MB）**：光柵化器是確定性的
> （固定正交相機、無隨機性、輸入頂點與面皆 SHA256 釘選），可用庫內的執行檔位元
> 重生並比對已記錄的雜湊。重生指令與預期輸出見
> `allowed-15deg-control-path-audit-agent-a/audit.json` 的 `fresh_regeneration_next_step`。
>
> **`.gitattributes` 對 `artifacts/pose-atlas-rebuild/**` 停用文字轉換**——換行正規化
> 會改動位元組並使 `sha256-sums.txt` 與 `audit.json` 記錄的雜湊全部失效。**改動這條
> 規則等於毀掉整條證據鏈。**
>
> `artifacts/` 不在打包白名單內（`build.ps1` 以 `--add-data` 逐項指定，Inno Setup 的
> `SourceDir` 指向 PyInstaller 產出目錄），**入庫不會讓安裝檔變大**。注意 `assets/`
> 是整個目錄照收——放進 `assets/` 的東西會被打包進安裝檔。
>
> 產線腳本（`lora_loader.py`、`chroma_mass_produce_v9.py` 等）仍只在本機 scratchpad，未入庫。

| 能力 | 位置 | 實況 |
|---|---|---|
| **授權乾淨的 24 視角幾何控制** | `artifacts/pose-atlas-rebuild/2026-08-25/candidate3-formal-controls-bundle-agent-a/formal-controls/` | 72 個 PNG＝24 視角 × silhouette／depth／normal，1024×1536，真 15° 步進。**自寫 CPU 光柵化器**＋MHR 網格（Apache-2.0）＋ufbx（MIT），稽核記載 `prohibited_components_used = 0` |
| **更完整的控制套件** | `artifacts/pose-atlas-rebuild/2026-08-26/canonical24-control-bundles-agent-b/bundles/yaw*/` | 另含 `base-render`、`shaded-render`、`part-id`、`ownership-{anatomy,hair,ornament,outfit}` 四層遮罩、`jaw13-conditioning`、`ornament_mask`、`registration-anchor.json` |
| **確定性軀幹形變器** | `artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/body-morph-candidate3/` | 168 cm 身高下命中 bust 86／underbust 71／waist 62／hip 90，**全部誤差 ≤ 0.5 cm**。SciPy CubicSpline C2＋以骨架為中心的局部徑向縮放 |
| **控制路徑授權稽核** | `artifacts/pose-atlas-rebuild/2026-08-25/allowed-15deg-control-path-audit-agent-a/audit.json` | 裁決 `USE_EXISTING_CANDIDATE3_CPU_FORMAL_CONTROLS`，含相依套件授權判定與 `blocks_and_limits` |
| **README 媒體資產** | `docs/media/` | `mohan-hero.png`（1600×900）、六張功能截圖（含 `security-permissions.png`）、`mohan-demo.mp4`（36 秒）、`mohan-demo.gif`（1.45 MB）、三張支持者立繪（640×640）。**全部由 `tests/test_readme_media.py` 以 CI 強制** |
| **授權出處證據鏈** | `docs/LICENSE-PURITY.md`（對外總覽）、`docs/LICENSE-BLACKLIST.md`、`ASSETS-LICENSE.md`、`THIRD_PARTY_NOTICES.md`、`THIRD_PARTY_DENYLIST.json`、`docs/{VISION,MULTIMODAL,HAND}-MODEL-PROVENANCE.json`、`docs/UI-ASSET-PROVENANCE.md`、`third_party_licenses/` | 隨產品出貨的八個模型全部 MIT 或 Apache-2.0，**每顆以 SHA256 與上游 commit 雙重釘選** |
| **能見度量測** | `tools/measure_visibility.py` | 一鍵產出月報指標並對照 2026-08-30 基準；自動標記 0 資產的 release。需已登入的 `gh` |
| **臉部偵測／視角驗證** | `assets/vision-models/face_detection_yunet_2023mar.onnx`（YuNet, MIT） | 用於臉譜稽核、視角自動驗證、臉部細修裁切、訓練集視角分布量化 |

### 產線腳本（在 scratchpad，未入庫）

`lora_loader.py`（ai-toolkit→diffusers 鍵名轉換，掛不上即拋錯）、`chroma_mass_produce_v9.py`（24 視角 t2i＋內建 YuNet 驗證）、`face_detailer.py`＋`run_face_detail_v9.py`（臉部放大重繪貼回）、`mirror_positive_views.py`、`measure_rotation*.py`、`geo_conditioning_probe.py`。

---

## 一之二、幾何條件化：已驗證可行的配方（2026-08-31）

純 t2i 無法控制精確鏡頭角度（見下節），**但把 3D 控制圖當 img2img 初始圖可以**。
授權上完全乾淨——不需要任何 ControlNet，只用 `ChromaImg2ImgPipeline` 與庫內既有的控制圖。

| 參數 | 值 | 依據 |
|---|---|---|
| 初始圖 | **`*_shaded-render.png`**（灰模渲染） | 見下方「不要用 normal map」 |
| strength | **待重新選定** | 原本填 0.95，已於同日撤回，理由見下 |
| LoRA 權重 | 0.85 | 1.0 壓不住髮型、0.70 正面臉型變窄 |
| 尺寸 | 控制圖 1024×1536 與素體 832×1248 同為 2:3，直接縮放即可 |

### 強度該怎麼選：用剪影 IoU，不要用觀感

以 yaw+090 為例，控制遮罩取自 bundle 的 `_silhouette.png`（**不要**用門檻從灰模推，
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
治不了顏色**——顏色是低頻訊號，初始圖是灰的就一路灰。同理，網格沒有頭髮，
低頻就一路說「沒有頭髮」，0.65 到 0.85 全程光頭。

**推論**：要同時拿到幾何與外觀，得修初始圖的低頻先驗，而不是調強度——
把灰模的明暗當光照、顏色換成膚色，並在頭頂補一塊低頻暗色髮罩。

### 撤回：strength 0.95 等於沒有幾何條件化

本表原本寫 strength 0.95，理由是「0.70／0.80／0.88 皆殘留人偶體型，0.95 才乾淨」。
觀察無誤，**結論下反了**。diffusers 的 img2img 起點由這兩行決定：

```python
init_timestep = min(num_inference_steps * strength, num_inference_steps)
t_start       = int(max(num_inference_steps - init_timestep, 0))
```

`steps=34、strength=0.95` 時 `t_start = 1`——34 步只跳過 1 步，初始圖被加噪到幾乎全是雜訊。
低強度之所以「殘留人偶體型」正是因為幾何有進去；0.95 之所以「乾淨」是因為**幾何完全沒進去**。

實測佐證：拿兩張構圖差異極大的初始圖（人物佔畫面 9% 與 17%）餵同一個種子，
**輸出只差 2.1% 的像素、平均色差 2.0／255**。

這個實驗證明的是**構圖與比例沒有被保留**，不等於「初始圖毫無作用」——
同一份證據樹裡的腳掌翹起現象顯示，normal map 與灰模在 0.95 下仍會產生系統性差異，
可見低頻色彩訊號還是滲得進來。要主張的精確版本是：
**0.95 保不住幾何構圖，只留下一點局部色彩偏壓；而後者恰好是有害的那半。**

**教訓**：選 strength 不能只看「哪張順眼」，必須有一個能證偽的指標直接量
「幾何有沒有進去」——例如輸出剪影與控制網格剪影的 IoU，並且要跟純 t2i 基準比，
否則量到的只是「隨便畫個人剛好也會重疊」。

### 一定要顯式傳 height／width

`ChromaImg2ImgPipeline.__call__` 的預設是 `height = height or self.default_sample_size * self.vae_scale_factor`。
**不傳就退回 1024×1024 方形，初始圖自己的尺寸完全不算數。**
2:3 的初始圖被壓成正方形後，方形畫布誘導模型畫成「正面＋側面」的角色設定表，
一張圖裡出現兩個人；同樣的提示詞在 832×1248 下從未出過這個問題。
負向詞（`multiple people, twins, split screen`…）壓不住它——那是構圖問題不是語意問題。

### 不要用 normal map 當初始圖

實測 strength 0.90 與 0.95 兩檔，**normal map 都造成系統性的腳掌翹起**（腳跟離地、腳尖下壓），
灰模在同樣強度下雙腳平貼。成因是 normal map 在腳背與腳趾之間有劇烈色相斷層，
模型把該色帶讀成「腳尖朝下的表面朝向」；灰模只有平滑明暗漸層，讀起來就是平放的腳掌。
**推論：任何法線劇變的部位（腳、手指、下顎、肩線）都可能被 normal map 誤讀成姿態。**

先前 2026-08-26 的 `yaw090-flux-img2img-lora-3d-agent-d` 用 normal map ＋ FLUX.1-schnell ＋
strength 0.90，產出美術品質良好但識別度漂移（其 depth 變體已被標記
`REJECTED_IDENTITY_DRIFT`）——該實驗使用的是側臉權威注入之前的 identity LoRA。

**變因分離的教訓**：本輪一度誤判「normal map 優於灰模，因為它不帶體型訊號」。
把灰模也拉到 0.95 當對照組才發現**主導變因是 strength 而非初始圖種類**，
兩者在 0.95 下體型同樣纖細。差別只在腳部誤讀。

## 二、已驗證失敗的路（不要重試）

| 嘗試過的做法 | 結果 | 證據 |
|---|---|---|
| **Flux 系 ControlNet 做角度控制** | **授權死路** | XLabs／InstantX／Shakker-Labs／Jasper 全系皆 flux-dev 衍生，非商用條款傳染。見 `docs/LICENSE-BLACKLIST.md` |
| **用提示詞控制精確鏡頭角度** | **結構性失敗，且比先前記載的更嚴重** | 一代與二代 atlas 記載「壓縮成約三群」；2026-08-31 對 v9 的 24 張逐張量鼻眼偏移，實測是**只有兩個狀態**：yaw+000 為 −0.04，而 +015 到 +105 全落在 +0.50～+0.62（全距的 82% 集中在 0°→15° 那一跳）。並排對照確認身體也沒轉。所謂 17 張可用素體，實際上只有 2 個角度 |
| **`rotated N degrees to her right / left`** | **左右完全失效** | ±yaw 四組對照全部面向同一邊。以角色為基準的方位模型做不到；改用畫面相對措辭，或只生成一側再水平鏡像 |
| **背面段（\|yaw\| ≥ 135）避免露臉** | **三種手段全滅** | ①負向禁令（v8，7/7 失敗）②語意正向描述（v9，7/7 失敗）③幾何錨點「鼻子與腳趾同向」＋部位級負向詞＋三組新 seed（7/7 失敗）。**提示詞工程已到頂，不要再換措辭** |
| **LoRA caption 寫入髮型或服裝** | **綁進身份** | 權威圖 caption 誤寫 `with long black hair`，導致 LoRA 把長髮學成身份，權重 1.0 時任何提示詞壓不住。補救是降權重至 0.85 |
| **LoRA 權重降到 0.70 換嘴形** | **正面臉型跑掉** | 側面看不出差別，正面明顯變窄變尖。**降權重前必須測正面**，側面不足以判斷 |
| **img2img 以既有人像當底稿** | **底稿身份壓過 LoRA** | 側面「像別人」，是 v8 起改為純 t2i 的原因。註：無材質灰模是否適用尚未定論（探針進行中） |
| **`FILE_ATTRIBUTE_PINNED` 觸發 iCloud 背景下載** | **完全無效** | 120 檔釘選後 10.5 分鐘零下載。iCloud for Windows 只在檔案被實際讀取時水化，不理會 OneDrive 那套釘選語意 |

### 授權黑名單（禁裝禁用禁下載）

ComfyUI（GPL-3.0）、SD WebUI Forge／reForge／SD.Next（AGPL-3.0）、SwarmUI、nvdiffrast（非商用）、OpenPose 官方實作（商用年費 US$25,000）、FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系、Illustrious-XL／NoobAI-XL、Pony Diffusion 系、SD3／SD3.5、Hunyuan 影像系、InstantMesh、Zero123++、CC BY-SA 素材。完整清單見 `docs/LICENSE-BLACKLIST.md`。

---

## 三、會咬人的治理閘門

| 閘門 | 硬性要求 |
|---|---|
| `tests/test_readme_media.py` | 九個認證徽章必須是全檔**第一個** `<p align="center">` 區塊且順序完全相符；語言導覽列恰好四次；十個 PNG 與 `mohan-demo.mp4` 全部被引用；支持者立繪固定 `width="220" height="220"`；`width="33%"` 對齊格恰 3 次、`width="25%"` 恰 4 次；README 不得出現作者年齡的時效性敘述 |
| `tools/check_four_language_docs.py` | H1 需四個標題以 `／` 分隔；**唯一允許的 H2 是四個語言名稱**，子章節請用 H3；各語言段不得互相重複；**行內程式碼必須跨語言一致**（曾因中文段少一組反引號而失敗）。內部 AI 對 AI 文件可加入 `NON_DOCUMENT_BASENAMES` 豁免 |
| `tools/migrate_python315_imports.py --check` | 新增 import 一律用 `lazy import` / `lazy from`，否則 `EAGER_ELIGIBLE` 會擋 |
| 在地化完整性測試 | `self._t()` 的 key 必須是字面量，不可用變數 |
| 棘輪行數閘門 | 新檔 800 行、既有檔基線只降不升、絕對天花板 1200。瘦身低於基線時**必須在同一 PR 下修基線** |

---

## 四、環境陷阱

- **PowerShell 5.1 讀 `.ps1` 需要 UTF-8 BOM**，否則含中文的腳本會以 cp950 解讀而語法崩潰。`$args`、`$pid` 是自動變數，不可賦值。
- **Bash 工具會吃掉 Windows 路徑中的 `\a`、`\b`** 等跳脫序列——Windows 路徑一律用 Python 端組字串或 Write 工具。
- **同時啟動多個重工作會互相拖垮**：兩個 Chroma 管線搶一張 16 GB 顯卡會讓後者靜默 OOM；大量磁碟 I/O 會讓 LoRA 訓練從 8 秒／步退化到 113 秒／步。**啟動前先查現有負載。**
- **共用 worktree 紀律**：多 session 共用同一個 repo，動分支前先看 HEAD，修補另開 worktree，不可用裸 `git stash`。

---

## 五、給下一個代理的四條紀律

1. **宣稱「沒有 X」之前，先跑那一秒的檢查。** 本專案的完成度高於一般專案，預設「缺失」會系統性地猜錯。
2. **不從局部證據下全域結論。** 讀 README 前 25 行不等於讀過 README。
3. **指標沒自我驗證過就不要報數字。** 例：剪影寬度指標若量出「正面比側面窄」，那是指標壞了，不是資料奇怪。
4. **比較兩張圖的某個特徵前，先確認其他變因相同。** 否則會把污染變因誤判成主因，並為此付出不必要的代價。
