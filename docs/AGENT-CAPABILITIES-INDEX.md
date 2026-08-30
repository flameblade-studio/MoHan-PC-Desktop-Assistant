# 代理防重工索引 / Agent Capabilities Index

> **給接手的 AI 代理與未來的自己。** 本專案先後由 ChatGPT Codex 5.6 Sol、DeepSeek V4 Pro、Claude 參與，
> 產出散在 `artifacts/` 底下以 `agent-a` / `agent-b` / `agent-c` 命名的平行目錄裡。
> 每一份都嚴謹（SHA256 釘選、exit code、驗證閘門、可重現指令），但**沒有一個新來的人會自然讀到的入口**。
>
> **動手前先讀這裡。** 本文件的唯一目的是阻止「重造已存在的輪子」與「重試已證明失敗的路」。

**維護規則**：發現本文件與現況不符時，**修正本文件**，不要繞過它。新增能力或證明某條路走不通時，補上一列。

---

## 一、已建成的能力（不要重做）

> ### ⚠️ `artifacts/` 與 `work/` 不在 git 裡
>
> `.gitignore` 明文排除 `/artifacts/` 與 `work/`。下表凡是以 `artifacts/` 開頭的路徑
> **只存在於擁有者的本機**，clone 這個 repo 不會取得它們。
>
> **這代表兩件事**：①遠端代理或 CI 無法直接使用這些資產，需要擁有者提供
> ②**四天份、經 SHA256 釘選的幾何控制產出目前只有單一副本，沒有異地備援**。
> 若該磁碟失效即永久消失。建議另行備份到 D 槽以外的位置或私有 vault。
>
> 產線腳本（`lora_loader.py` 等）同樣只在本機 scratchpad，未入庫。

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

## 二、已驗證失敗的路（不要重試）

| 嘗試過的做法 | 結果 | 證據 |
|---|---|---|
| **Flux 系 ControlNet 做角度控制** | **授權死路** | XLabs／InstantX／Shakker-Labs／Jasper 全系皆 flux-dev 衍生，非商用條款傳染。見 `docs/LICENSE-BLACKLIST.md` |
| **用提示詞控制精確鏡頭角度** | **結構性失敗** | 一代與二代 atlas 皆量測到 15/30/45/60/75 被壓縮成約三個離散群集。擴散模型沒有連續鏡頭參數 |
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
