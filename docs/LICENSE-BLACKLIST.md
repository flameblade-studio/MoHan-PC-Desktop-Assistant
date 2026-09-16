# 墨寒專案授權允收邊界與具名隔離清單／墨寒项目授权接收边界与具名隔离清单／MoHan Project License Acceptance Boundary and Named Isolation List／墨寒プロジェクト・ライセンス受入境界と指名隔離リスト

## 繁體中文

擁有者 2026-09-07 最新裁決：MPL-2.0 完成[合規補全](MPL-2.0-COMPLIANCE.md)後納入白名單，須逐項維持授權、源碼、通知及版本雜湊證據。下列具名工具的既有隔離裁決持續有效。

擁有者 2026-08-28 裁決：本機生產工具集合以授權已查明且符合允收條件者為限；下列項目**持續隔離於下載、安裝與各種產線入口之外**。本清單與白名單（MIT／Apache 2.0／CC0／CC BY＋BSD 等同級）共同界定允收範圍；白名單以外的候選先完成查證，符合條件後再引入，其餘候選納入本清單隔離。

擁有者 2026-09-07 追加裁決：授權查核在下載前完成，範圍涵蓋實際出貨的 bundle、直接與遞移相依套件及工具頂層授權。GPL／AGPL、非商用、禁止修改、Share-Alike、來源不明或授權待驗證者維持下載與使用隔離。墨寒本體與產線的允收集合限定為明列白名單及既有具名例外。

### 工具類（持續隔離）

| 項目 | 授權 | 裁決 |
|---|---|---|
| ComfyUI | GPL-3.0 | 擁有者裁決完全排除並維持零備援（2026-08-28）；本機舊副本已刪除 |
| Krita | GPL-3.0 | 擁有者 2026-09-07 裁決完全排除；下載、安裝、留存、使用與墨寒產線素材生成皆維持隔離，本機套件、壓縮檔及相關候選產物已刪除 |
| miniPaint／AlertifyJS | 頂層 MIT，但正式 bundle 內含 GPL-3.0 AlertifyJS | 下載後在開啟任何墨寒素材前發現並立即完整刪除；兩者永久維持在安裝與使用範圍之外，並以此事故要求往後下載前查核完整相依樹與實際 bundle |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | 其 AGPL-3.0 條件超出允收邊界，持續隔離 |
| SwarmUI | MIT 殼＋ComfyUI 後端 | 核心採用 ComfyUI，因此隨同隔離 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 盤點揪出，本機已刪除 |
| OpenPose 官方實作 | CMU 學術授權（商用年費 US$25k） | 骨架萃取改用 DWPose／RTMPose／MediaPipe（Apache） |

### 模型權重類（下載隔離）

| 項目 | 授權 | 裁決 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 及其一切衍生模型 | flux-1-dev-non-commercial | 非商用條件涵蓋整個衍生樹，與商用允收邊界不相容 |
| XLabs／InstantX／Shakker-Labs／Jasper 的 Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 衍生） | 2026-08-28 盤點確認全數隔離，下載數為 0 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 維持隔離 |
| Pony Diffusion 系 | 附加商用限制 | 維持隔離 |
| SD3／SD3.5 | Stability Community License | 位於白名單範圍之外，維持隔離 |
| Hunyuan 影像系 | Tencent Community License | 位於白名單範圍之外，維持隔離 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 查證：只存在於 `chroma-debug-development-only`，同時觸及非商用與 share-alike；repo 自述純供研究，Apache 2.0 版狀態為待發布。轉載站的重新上傳沿用上游授權。**同門 Chroma1-Radiance 為 Apache 2.0，屬於本清單範圍之外** |

### 素材類（資產鏈隔離）

| 項目 | 裁決 |
|---|---|
| CC BY-SA | 擁有者裁決徹底移除（share-alike 傳染＋盡調成本） |
| CC BY-NC／CC BY-ND 系 | 非商用／禁止修改條件超出允收邊界，維持隔離 |
| 來源或授權不明之任何素材 | 依既有治理維持隔離，完成來源與授權查明後才具備正式封裝資格 |

### 例外欄（白名單外但經裁決許可）

| 項目 | 授權 | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | App 執行期 UI 框架；onedir 動態連結＋About 聲明＋授權全文隨包 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外條款明文保證打包產物位於 GPL 適用範圍之外；建置工具留在建置環境 |
| Azure Speech SDK | Microsoft 專有（可商用可再散布） | 平台 SDK；允許商用並維持授權邊界 |

## 简体中文

所有者 2026-09-07 最新裁决：MPL-2.0 完成[合规补全](MPL-2.0-COMPLIANCE.md)后纳入白名单，须逐项维持授权、源代码、通知及版本哈希证据。下列具名工具的现有隔离裁决持续有效。

所有者 2026-08-28 裁决：本机生产工具集合以授权已查明且符合接收条件者为限；下列项目**持续隔离于下载、安装与各种产线入口之外**。本清单与白名单（MIT／Apache 2.0／CC0／CC BY＋BSD 等同级）共同界定接收范围；白名单以外的候选先完成查证，符合条件后再引入，其余候选纳入本清单隔离。

所有者 2026-09-07 追加裁决：授权核查在下载前完成，范围覆盖实际发布的 bundle、直接及传递依赖和工具顶层许可。GPL／AGPL、非商业、禁止修改、Share-Alike、来源不明或授权待验证者维持下载与使用隔离。墨寒本体与产线的接收集合限定为明确列入白名单及既有具名例外。

### 工具类（持续隔离）

| 项目 | 授权 | 裁决 |
|---|---|---|
| ComfyUI | GPL-3.0 | 所有者裁决完全排除并维持零备援（2026-08-28）；本机旧副本已删除 |
| Krita | GPL-3.0 | 所有者 2026-09-07 裁决完全排除；下载、安装、留存、使用与墨寒产线素材生成均维持隔离，本机套件、压缩包及相关候选产物已删除 |
| miniPaint／AlertifyJS | 顶层 MIT，但正式 bundle 内含 GPL-3.0 AlertifyJS | 下载后在打开任何墨寒素材前发现并立即完整删除；两者永久维持在安装与使用范围之外，并以此事故要求此后下载前核查完整依赖树与实际 bundle |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | 其 AGPL-3.0 条件超出接收边界，持续隔离 |
| SwarmUI | MIT 壳＋ComfyUI 后端 | 核心采用 ComfyUI，因此随同隔离 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 盘点揪出，本机已删除 |
| OpenPose 官方实现 | CMU 学术授权（商用年费 US$25k） | 骨架提取改用 DWPose／RTMPose／MediaPipe（Apache） |

### 模型权重类（下载隔离）

| 项目 | 授权 | 裁决 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 及其一切衍生模型 | flux-1-dev-non-commercial | 非商业条件覆盖整个衍生树，与商业接收边界不兼容 |
| XLabs／InstantX／Shakker-Labs／Jasper 的 Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 衍生） | 2026-08-28 盘点确认全数隔离，下载数为 0 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 维持隔离 |
| Pony Diffusion 系 | 附加商用限制 | 维持隔离 |
| SD3／SD3.5 | Stability Community License | 位于白名单范围之外，维持隔离 |
| Hunyuan 图像系 | Tencent Community License | 位于白名单范围之外，维持隔离 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 查证：只存在于 `chroma-debug-development-only`，同时触及非商用与 share-alike；repo 自述纯供研究，Apache 2.0 版状态为待发布。转载站的重新上传沿用上游许可。**同门 Chroma1-Radiance 为 Apache 2.0，属于本清单范围之外** |

### 素材类（资产链隔离）

| 项目 | 裁决 |
|---|---|
| CC BY-SA | 所有者裁决彻底移除（share-alike 传染＋尽调成本） |
| CC BY-NC／CC BY-ND 系 | 非商业／禁止修改条件超出接收边界，维持隔离 |
| 来源或授权不明的任何素材 | 按现有治理维持隔离，完成来源与授权查明后才具备正式封装资格 |

### 例外栏（白名单外但经裁决许可）

| 项目 | 授权 | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | App 运行期 UI 框架；onedir 动态链接＋About 声明＋授权全文随包 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条款明文保证打包产物位于 GPL 适用范围之外；构建工具留在构建环境 |
| Azure Speech SDK | Microsoft 专有（可商用可再分发） | 平台 SDK；允许商业使用并维持授权边界 |

## English

Latest owner ruling, 2026-09-07: MPL-2.0 joins the allowlist after [compliance remediation](MPL-2.0-COMPLIANCE.md), with retained license, source, notice and version/hash evidence for each component. The existing isolation rulings for the named tools below remain effective.

Owner ruling, 2026-08-28: the local production-tool set is limited to tools with verified licenses that meet the acceptance conditions; the items below **remain isolated from downloading, installation, and every pipeline entry point**. This list and the allowlist (MIT / Apache 2.0 / CC0 / CC BY, plus BSD-tier permissive equivalents) jointly define the acceptance boundary. Candidates outside the allowlist undergo verification before adoption; the remaining candidates enter this isolation list.

Additional owner ruling, 2026-09-07: licensing evidence is verified before download and covers the shipped bundle, direct and transitive dependencies, and the tool's top-level licence. GPL/AGPL, non-commercial, no-derivatives, share-alike, unknown-origin, or pending-verification items remain isolated from download and use. The MoHan product and production pipeline accept the explicit allowlist and existing named exceptions.

### Tools (continuously isolated)

| Item | License | Ruling |
|---|---|---|
| ComfyUI | GPL-3.0 | Owner ruling: fully excluded with zero fallback (2026-08-28); local copy deleted |
| Krita | GPL-3.0 | Owner ruling on 2026-09-07: fully excluded; downloading, installation, retention, use, and creation of MoHan pipeline assets remain isolated; the local package, archive, and related candidates were deleted |
| miniPaint / AlertifyJS | MIT top level, but the shipped bundle includes GPL-3.0 AlertifyJS | Detected after download and deleted in full before any MoHan asset was opened; both remain permanently outside installation and use, and this incident requires future pre-download audits of the complete dependency tree and shipped bundle |
| Stable Diffusion WebUI Forge / reForge / SD.Next | AGPL-3.0 | Its AGPL-3.0 conditions exceed the acceptance boundary; continuously isolated |
| SwarmUI | MIT shell over a ComfyUI backend | Its core is ComfyUI; isolated together |
| nvdiffrast | NVIDIA Source Code License (non-commercial) | Caught in the 2026-08-28 audit; deleted locally |
| Official OpenPose implementation | CMU academic license (US$25k/yr commercial) | Skeleton extraction uses DWPose / RTMPose / MediaPipe (Apache) instead |

### Model weights (download isolation)

| Item | License | Ruling |
|---|---|---|
| FLUX.1-dev / FLUX.2-dev / FLUX.2-klein-9B and every derivative | flux-1-dev-non-commercial | Non-commercial terms cover the entire derivative tree and conflict with the commercial acceptance boundary |
| All Flux ControlNets from XLabs / InstantX / Shakker-Labs / Jasper | flux-1-dev-non-commercial (dev derivatives) | Audit 2026-08-28 confirmed full isolation; download count: 0 |
| Illustrious-XL / NoobAI-XL | Fair AI Public License (copyleft) | Remains isolated |
| Pony Diffusion family | Additional commercial restrictions | Remains isolated |
| SD3 / SD3.5 | Stability Community License | Outside the allowlist; remains isolated |
| Hunyuan image family | Tencent Community License | Outside the allowlist; remains isolated |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | Verified 2026-08-31: it exists only inside `chroma-debug-development-only`, tripping both the non-commercial and share-alike wires; the repository calls its contents research-only and the Apache 2.0 release remains pending. A mirror on a sharing site inherits the upstream licence. **Its sibling Chroma1-Radiance is Apache 2.0 and remains outside this list's scope** |

### Materials (asset-chain isolation)

| Item | Ruling |
|---|---|
| CC BY-SA | Removed entirely by owner ruling (share-alike contagion plus due-diligence cost) |
| CC BY-NC / CC BY-ND family | Non-commercial / no-derivatives terms exceed the acceptance boundary; remains isolated |
| Any material of unknown origin or license | Remains isolated under existing governance and becomes eligible for release packaging after origin and licensing are verified |

### Exceptions (outside the whitelist but permitted by ruling)

| Item | License | Reason |
|---|---|---|
| PySide6 | LGPL-3.0 | Runtime UI framework; onedir dynamic linking, About notice, full license texts shipped |
| PyInstaller | GPL-2.0 with bootloader exception | The exception explicitly keeps packaged output free of GPL; the tool remains confined to the build environment |
| Azure Speech SDK | Microsoft proprietary (commercial use and redistribution allowed) | Platform SDK; permits commercial use and preserves licensing boundaries |

## 日本語

所有者の最新裁定（2026-09-07）：MPL-2.0 は[義務の補完](MPL-2.0-COMPLIANCE.md)後にホワイトリストへ追加し、各コンポーネントのライセンス、ソース、通知、バージョンとハッシュ証拠を維持します。以下の指名ツールに対する既存の隔離裁定を継続します。

所有者の裁定（2026-08-28）：本機の生産ツール集合は、ライセンスを確認済みで受入条件を満たすものに限定します。以下の項目は**ダウンロード、インストール、あらゆる産線入口から継続して隔離**します。本リストとホワイトリスト（MIT／Apache 2.0／CC0／CC BY＋BSD 同等の寛容ライセンス）は、共同で受入境界を定義します。ホワイトリスト外の候補は導入前に検証し、条件を満たした後に導入します。それ以外の候補は本リストで隔離します。

所有者の追加裁定（2026-09-07）：ライセンス証拠はダウンロード前に検証し、ツール最上位の表示、実際に配布される bundle、直接依存、推移的依存を確認します。GPL／AGPL、非商用、改変禁止、Share-Alike、出所不明、または検証待ちの項目は、ダウンロードと使用から隔離します。墨寒本体と産線の受入集合は、明示されたホワイトリストと既存の具名例外に限定します。

### ツール類（継続隔離）

| 項目 | ライセンス | 裁定 |
|---|---|---|
| ComfyUI | GPL-3.0 | 所有者の裁定で完全除外し、予備数も 0（2026-08-28）；ローカル旧コピーは削除済み |
| Krita | GPL-3.0 | 所有者の 2026-09-07 裁定で完全除外；ダウンロード、インストール、保持、使用、墨寒産線素材の生成から隔離し、ローカルパッケージ、書庫、関連候補成果物を削除済み |
| miniPaint／AlertifyJS | 最上位は MIT だが、配布 bundle に GPL-3.0 AlertifyJS を含む | ダウンロード後、墨寒素材を一切開く前に検出して完全削除；両方をインストールと使用の対象外として永久隔離し、今後はダウンロード前に完全な依存ツリーと実配布 bundle を監査する |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | AGPL-3.0 条件が受入境界を超えるため継続隔離 |
| SwarmUI | MIT の殻＋ComfyUI バックエンド | 心臓部が ComfyUI のため併せて隔離 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 の棚卸しで検出、ローカル削除済み |
| OpenPose 公式実装 | CMU 学術ライセンス（商用は年額 US$25k） | 骨格抽出は DWPose／RTMPose／MediaPipe（Apache）を使用 |

### モデル権重類（ダウンロード隔離）

| 項目 | ライセンス | 裁定 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B とその全派生モデル | flux-1-dev-non-commercial | 非商用条項が派生ツリー全体を対象とし、商用受入境界と不整合 |
| XLabs／InstantX／Shakker-Labs／Jasper の Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 派生） | 2026-08-28 の棚卸しで全数隔離を確認、取得数は 0 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 継続隔離 |
| Pony Diffusion 系 | 追加の商用制限 | 継続隔離 |
| SD3／SD3.5 | Stability Community License | ホワイトリスト範囲外のため継続隔離 |
| Hunyuan 画像系 | Tencent Community License | ホワイトリスト範囲外のため継続隔離 |
| Chroma-DC-2K | CC BY-NC-SA 4.0 | 2026-08-31 確認：`chroma-debug-development-only` にのみ存在し、非商用と share-alike の双方に抵触。リポジトリ自身が研究目的のみと明記し、Apache 2.0 版は公開待ちです。転載サイトでの再アップロードには上流ライセンスが引き続き適用されます。**姉妹モデルの Chroma1-Radiance は Apache 2.0 であり本リストの対象外** |

### 素材類（資産チェーン隔離）

| 項目 | 裁定 |
|---|---|
| CC BY-SA | 所有者裁定で完全撤去（share-alike の伝染＋デューデリジェンス費用） |
| CC BY-NC／CC BY-ND 系 | 非商用／改変禁止の条件が受入境界を超えるため継続隔離 |
| 出所またはライセンス不明の素材 | 既存ガバナンスに従って隔離し、出所とライセンスの確認後に正式パッケージ候補とする |

### 例外欄（ホワイトリスト外だが裁定により許可）

| 項目 | ライセンス | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | 実行時 UI フレームワーク；onedir 動的リンク＋About 表示＋ライセンス全文同梱 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条項によりパッケージ産物は GPL の適用外；ビルドツールは産物に入らない |
| Azure Speech SDK | Microsoft プロプライエタリ（商用・再配布可） | プラットフォーム SDK；商用利用を許可し、ライセンス境界を維持 |
