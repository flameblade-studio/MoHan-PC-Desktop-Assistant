# 墨寒專案授權黑名單／墨寒项目授权黑名单／MoHan Project License Blacklist／墨寒プロジェクト・ライセンス黒名単

## 繁體中文

擁有者 2026-08-28 裁決：任何授權有疑慮的生產工具，即使閒置未用也不得留在本機；下列項目**禁止下載、禁止安裝、禁止以任何形式進入產線**。本名單與白名單（MIT／Apache 2.0／CC0／CC BY＋BSD 等同級）互為表裡；不在白名單者一律先查證再引入，查證不過即入此名單。

### 工具類（禁裝禁用）

| 項目 | 授權 | 裁決 |
|---|---|---|
| ComfyUI | GPL-3.0 | 擁有者明令完全出局，不列任何備援（2026-08-28）；本機舊副本已刪除 |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | 比 GPL 更強傳染，禁用 |
| SwarmUI | MIT 殼＋ComfyUI 後端 | 心臟是 ComfyUI，一併禁用 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 盤點揪出，本機已刪除 |
| OpenPose 官方實作 | CMU 學術授權（商用年費 US$25k） | 骨架萃取改用 DWPose／RTMPose／MediaPipe（Apache） |

### 模型權重類（禁下載）

| 項目 | 授權 | 裁決 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 及其一切衍生模型 | flux-1-dev-non-commercial | 非商用傳染整個衍生樹 |
| XLabs／InstantX／Shakker-Labs／Jasper 的 Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 衍生） | 2026-08-28 盤點確認全滅，一顆未下載 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 禁用 |
| Pony Diffusion 系 | 附加商用限制 | 禁用 |
| SD3／SD3.5 | Stability Community License | 非白名單，禁用 |
| Hunyuan 影像系 | Tencent Community License | 非白名單，禁用 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 查證：只存在於 `chroma-debug-development-only`，同時觸及非商用與 share-alike；repo 自述純供研究，Apache 2.0 版尚未存在。轉載站的重新上傳不改變上游授權。**同門 Chroma1-Radiance 為 Apache 2.0，不在此名單** |

### 素材類（禁入資產鏈）

| 項目 | 裁決 |
|---|---|
| CC BY-SA | 擁有者裁決徹底移除（share-alike 傳染＋盡調成本） |
| CC BY-NC／CC BY-ND 系 | 非商用／禁改作，禁入 |
| 來源或授權不明之任何素材 | 依既有治理：不得進入正式封裝 |

### 例外欄（白名單外但經裁決許可）

| 項目 | 授權 | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | App 執行期 UI 框架；onedir 動態連結＋About 聲明＋授權全文隨包 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外條款明文保證打包產物不受 GPL 約束；建置工具不進產物 |
| Azure Speech SDK | Microsoft 專有（可商用可再散布） | 平台 SDK，不傳染、不禁商用 |

## 简体中文

所有者 2026-08-28 裁决：任何授权有疑虑的生产工具，即使闲置未用也不得留在本机；下列项目**禁止下载、禁止安装、禁止以任何形式进入产线**。本名单与白名单（MIT／Apache 2.0／CC0／CC BY＋BSD 等同级）互为表里；不在白名单者一律先查证再引入，查证不过即入此名单。

### 工具类（禁装禁用）

| 项目 | 授权 | 裁决 |
|---|---|---|
| ComfyUI | GPL-3.0 | 所有者明令完全出局，不列任何备援（2026-08-28）；本机旧副本已删除 |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | 比 GPL 更强传染，禁用 |
| SwarmUI | MIT 壳＋ComfyUI 后端 | 心脏是 ComfyUI，一并禁用 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 盘点揪出，本机已删除 |
| OpenPose 官方实现 | CMU 学术授权（商用年费 US$25k） | 骨架提取改用 DWPose／RTMPose／MediaPipe（Apache） |

### 模型权重类（禁下载）

| 项目 | 授权 | 裁决 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 及其一切衍生模型 | flux-1-dev-non-commercial | 非商用传染整个衍生树 |
| XLabs／InstantX／Shakker-Labs／Jasper 的 Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 衍生） | 2026-08-28 盘点确认全灭，一颗未下载 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 禁用 |
| Pony Diffusion 系 | 附加商用限制 | 禁用 |
| SD3／SD3.5 | Stability Community License | 非白名单，禁用 |
| Hunyuan 图像系 | Tencent Community License | 非白名单，禁用 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 查证：只存在于 `chroma-debug-development-only`，同时触及非商用与 share-alike；repo 自述纯供研究，Apache 2.0 版尚未存在。转载站的重新上传不改变上游许可。**同门 Chroma1-Radiance 为 Apache 2.0，不在此名单** |

### 素材类（禁入资产链）

| 项目 | 裁决 |
|---|---|
| CC BY-SA | 所有者裁决彻底移除（share-alike 传染＋尽调成本） |
| CC BY-NC／CC BY-ND 系 | 非商用／禁改作，禁入 |
| 来源或授权不明的任何素材 | 依既有治理：不得进入正式封装 |

### 例外栏（白名单外但经裁决许可）

| 项目 | 授权 | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | App 运行期 UI 框架；onedir 动态链接＋About 声明＋授权全文随包 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条款明文保证打包产物不受 GPL 约束；构建工具不进产物 |
| Azure Speech SDK | Microsoft 专有（可商用可再分发） | 平台 SDK，不传染、不禁商用 |

## English

Owner ruling, 2026-08-28: any production tool with a questionable license must not remain on this machine even if idle; the items below are **banned from downloading, installing, or entering the pipeline in any form**. This blacklist complements the whitelist (MIT / Apache 2.0 / CC0 / CC BY, plus BSD-tier permissive equivalents); anything outside the whitelist must be verified before adoption, and failures land here.

### Tools (banned from install and use)

| Item | License | Ruling |
|---|---|---|
| ComfyUI | GPL-3.0 | Owner decree: fully out, not even as a fallback (2026-08-28); local copy deleted |
| Stable Diffusion WebUI Forge / reForge / SD.Next | AGPL-3.0 | Stronger contagion than GPL; banned |
| SwarmUI | MIT shell over a ComfyUI backend | Its heart is ComfyUI; banned together |
| nvdiffrast | NVIDIA Source Code License (non-commercial) | Caught in the 2026-08-28 audit; deleted locally |
| Official OpenPose implementation | CMU academic license (US$25k/yr commercial) | Skeleton extraction uses DWPose / RTMPose / MediaPipe (Apache) instead |

### Model weights (banned from download)

| Item | License | Ruling |
|---|---|---|
| FLUX.1-dev / FLUX.2-dev / FLUX.2-klein-9B and every derivative | flux-1-dev-non-commercial | Non-commercial taint spreads across the whole derivative tree |
| All Flux ControlNets from XLabs / InstantX / Shakker-Labs / Jasper | flux-1-dev-non-commercial (dev derivatives) | Audit 2026-08-28 confirmed all affected; none downloaded |
| Illustrious-XL / NoobAI-XL | Fair AI Public License (copyleft) | Banned |
| Pony Diffusion family | Additional commercial restrictions | Banned |
| SD3 / SD3.5 | Stability Community License | Not whitelisted; banned |
| Hunyuan image family | Tencent Community License | Not whitelisted; banned |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | Verified 2026-08-31: it exists only inside `chroma-debug-development-only`, tripping both the non-commercial and share-alike wires; the repository calls its contents research-only and the Apache 2.0 release does not exist yet. A mirror on a sharing site does not change the upstream licence. **Its sibling Chroma1-Radiance is Apache 2.0 and is not on this list** |

### Materials (banned from the asset chain)

| Item | Ruling |
|---|---|
| CC BY-SA | Removed entirely by owner ruling (share-alike contagion plus due-diligence cost) |
| CC BY-NC / CC BY-ND family | Non-commercial / no-derivatives; banned |
| Any material of unknown origin or license | Per existing governance: must not enter a release package |

### Exceptions (outside the whitelist but permitted by ruling)

| Item | License | Reason |
|---|---|---|
| PySide6 | LGPL-3.0 | Runtime UI framework; onedir dynamic linking, About notice, full license texts shipped |
| PyInstaller | GPL-2.0 with bootloader exception | The exception explicitly keeps packaged output free of GPL; build tool never ships |
| Azure Speech SDK | Microsoft proprietary (commercial use and redistribution allowed) | Platform SDK; no contagion, no commercial ban |

## 日本語

所有者の裁定（2026-08-28）：ライセンスに疑義のある生産ツールは、未使用であっても本機に残してはならない。以下の項目は**ダウンロード・インストール・いかなる形での産線への持ち込みも禁止**。本黒名単はホワイトリスト（MIT／Apache 2.0／CC0／CC BY＋BSD 同等の寛容ライセンス）と表裏一体であり、ホワイトリスト外は必ず検証してから導入し、検証に落ちたものはここに載る。

### ツール類（導入・使用禁止）

| 項目 | ライセンス | 裁定 |
|---|---|---|
| ComfyUI | GPL-3.0 | 所有者の明令で完全除外、予備としても不採用（2026-08-28）；ローカル旧コピーは削除済み |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | GPL より強い伝染性のため禁止 |
| SwarmUI | MIT の殻＋ComfyUI バックエンド | 心臓部が ComfyUI のため併せて禁止 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 の棚卸しで検出、ローカル削除済み |
| OpenPose 公式実装 | CMU 学術ライセンス（商用は年額 US$25k） | 骨格抽出は DWPose／RTMPose／MediaPipe（Apache）を使用 |

### モデル権重類（ダウンロード禁止）

| 項目 | ライセンス | 裁定 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B とその全派生モデル | flux-1-dev-non-commercial | 非商用条項が派生ツリー全体に伝染 |
| XLabs／InstantX／Shakker-Labs／Jasper の Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 派生） | 2026-08-28 の棚卸しで全滅を確認、一つも未取得 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 禁止 |
| Pony Diffusion 系 | 追加の商用制限 | 禁止 |
| SD3／SD3.5 | Stability Community License | ホワイトリスト外のため禁止 |
| Hunyuan 画像系 | Tencent Community License | ホワイトリスト外のため禁止 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 確認：`chroma-debug-development-only` にのみ存在し、非商用と share-alike の双方に抵触。リポジトリ自身が研究目的のみと明記し、Apache 2.0 版は未公開。転載サイトでの再アップロードは上流ライセンスを変えません。**姉妹モデルの Chroma1-Radiance は Apache 2.0 であり本リストの対象外** |

### 素材類（資産チェーンへの持ち込み禁止）

| 項目 | 裁定 |
|---|---|
| CC BY-SA | 所有者裁定で完全撤去（share-alike の伝染＋デューデリジェンス費用） |
| CC BY-NC／CC BY-ND 系 | 非商用／改変禁止のため持ち込み禁止 |
| 出所またはライセンス不明の素材 | 既存ガバナンスに従い正式パッケージへ入れない |

### 例外欄（ホワイトリスト外だが裁定により許可）

| 項目 | ライセンス | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | 実行時 UI フレームワーク；onedir 動的リンク＋About 表示＋ライセンス全文同梱 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条項によりパッケージ産物は GPL の適用外；ビルドツールは産物に入らない |
| Azure Speech SDK | Microsoft プロプライエタリ（商用・再配布可） | プラットフォーム SDK；伝染なし・商用禁止なし |
