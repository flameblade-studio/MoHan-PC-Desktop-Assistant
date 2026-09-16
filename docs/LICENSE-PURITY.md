# 授權純淨承諾／授权纯净承诺／License Purity Commitment／ライセンス純度に関する約束

## 繁體中文

**墨寒可以商用。整條產線的每一顆權重均具商用資格、每一份素材均符合允收授權、每一個檔案均具明確來源。**

墨寒從投入前的查核開始維持這項承諾：模型的「僅供研究」「非商用」與 share-alike 條款都會沿衍生關係評估，只有符合商用允收邊界的工具、權重與素材才進入產線。

### 產線實際使用的每一個模型

| 模型 | 用途 | 授權 | 來源與釘選 |
|---|---|---|---|
| YuNet `face_detection_yunet_2023mar.onnx` | 臉部偵測 | **MIT** | opencv_zoo `f12e127` |
| SFace `face_recognition_sface_2021dec.onnx` | 臉部辨識 | **Apache-2.0** | opencv_zoo `ba91a3b` |
| NanoDet `object_detection_nanodet_2022nov.onnx` | 物件偵測 | **Apache-2.0** | opencv_zoo `510899a` |
| MediaPipe Face Mesh `face_landmark_468.tflite` | 468 點臉部特徵 | **Apache-2.0** | mediapipe-assets |
| MediaPipe Iris `iris_landmark.tflite` | 虹膜與視線 | **Apache-2.0** | mediapipe-assets |
| MediaPipe `palm_detection_mediapipe_2023feb.onnx` | 手掌偵測 | **Apache-2.0** | opencv_zoo `8de3653` |
| MediaPipe `handpose_estimation_mediapipe_2023feb.onnx` | 手部姿態 | **Apache-2.0** | opencv_zoo `56cef36` |
| Silero VAD `silero_vad_v4.0.onnx` | 語音活動偵測 | **MIT** | silero-vad `v4.0` |

八個模型，全部是 MIT 或 Apache 2.0。**每一顆都用 SHA256 與上游 commit 雙重釘選**，出處記錄在 [`VISION-MODEL-PROVENANCE.json`](VISION-MODEL-PROVENANCE.json)、[`MULTIMODAL-MODEL-PROVENANCE.json`](MULTIMODAL-MODEL-PROVENANCE.json)、[`HAND-MODEL-PROVENANCE.json`](HAND-MODEL-PROVENANCE.json)，可逐一驗證。

上表是**隨產品出貨、在你電腦上執行**的模型。另有一條本機素材生產鏈（FLUX.2-klein-4B 與 Chroma1-HD，皆為 Apache 2.0）留在發行產物範圍之外，但同樣受本白名單約束——這正是 FLUX dev 全系被排除的原因。角色圖目前另借助託管生圖服務繪製：本機模型正持續迭代至角色一致性要求，達標後即轉回本機生產。上述承諾持續完整有效——白名單約束的是工具與權重，而角色美術本身是擁有者的專有財產（見 [ASSETS-LICENSE](../ASSETS-LICENSE.md)），其權利邊界依專有資產條款管理。

### 白名單

白名單包含 **MIT、Apache 2.0、BSD、CC0、CC BY**，以及擁有者 2026-09-07 核可、完成合規補全後加入的 **MPL-2.0**。MPL 元件須保留完整授權、原通知及對應源碼；散布時提供收件者取得方式，並通過版本與雜湊檢查。詳見 [MPL 合規規則](MPL-2.0-COMPLIANCE.md)。其他授權候選先完成查證；既有工具隔離清單持續有效。

**SIL Open Font License, Version 1.1（SIL OFL 1.1）**依擁有者 2026-09-02 裁定加入白名單，適用範圍限定為字型：須隨附 `OFL.txt` 與版權聲明，販售範圍須包含搭載字型的產品或服務。若日後子集化或修改，便成為 `Modified Version`，必須依保留字型名改名並續用 OFL；OFL 的約束範圍限定為字型檔本身；使用它的文件與軟體沿用各自授權。已入庫字型的版本、來源與 SHA-256 見 [`FONTS.md`](../third_party_licenses/FONTS.md)；檔案皆以原始內容與原始名稱散布。

### 保護允收邊界的取捨

實際取捨紀錄讓純淨承諾可受稽核。完整清單見 [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md)，以下是代價最高的幾項：

- **ComfyUI（GPL-3.0）** — 生態系最主流的工具，依裁決完全隔離，備援副本數維持為 0。
- **Krita（GPL-3.0）** — 依擁有者 2026-09-07 裁決永久維持安裝與使用隔離；本機套件、下載檔與相關候選產物均已刪除。
- **miniPaint／AlertifyJS** — miniPaint 頂層雖為 MIT，正式 bundle 卻含 GPL-3.0 AlertifyJS；在開啟任何墨寒素材前已完整刪除並永久隔離，證明查核須涵蓋實際 bundle 與完整相依樹。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系** — 非商用條款涵蓋整棵衍生樹，因此產線採用 Apache 2.0 的 FLUX.2-klein-4B 與 Chroma1-HD 作為安全基底。
- **CC BY-SA 素材** — share-alike 的適用範圍與盡調成本超出允收邊界，已徹底移除。
- **Chroma-DC-2K** — 只存在於 `lodestones/chroma-debug-development-only`，該 repo 的授權是 CC BY-NC-SA 4.0，同時踩到非商用與 share-alike 兩條線；repo 自述「純供研究」，Apache 2.0 版本狀態為待發布。轉載站上的重新上傳沿用上游授權。同門的 **Chroma1-Radiance 是 Apache 2.0，位於排除範圍之外**，目前狀態由技術條件決定。
- **OpenPose 官方實作** — 商用年費 US$25,000，改用 Apache 授權的 DWPose／RTMPose／MediaPipe。
- **nvdiffrast、Illustrious-XL、SD3／3.5、Hunyuan 影像系** — 逐一查證並逐一隔離。

每一項都來自實際評估，並記錄了隔離決策。

### 三個經裁決的例外

每項例外均明確記錄理由與允收條件：

| 項目 | 授權 | 為什麼可以 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 動態連結、About 內聲明、授權全文隨包；你的程式碼沿用自身授權 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外條款明文保證打包產物位於 GPL 適用範圍之外；建置工具留在建置環境 |
| Azure Speech SDK | Microsoft 專有 | 允許商用與再散布，並維持授權邊界 |

### 這對你代表什麼

墨寒本體是 **MIT 授權**。你可以自由使用、修改、再散布，可以拿去做商業產品，你保有原始碼公開與否的選擇；每顆納入的權重都已通過商用條款查核。

想自行查核，證據都在庫內：[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。

## 简体中文

**墨寒可以商用。整条产线的每一颗权重均具商业资格、每一份素材均符合接收授权、每一个文件均具明确来源。**

墨寒从投入前的核查开始维持这项承诺：模型的「仅供研究」「非商业」与 share-alike 条款都会沿衍生关系评估，只有符合商业接收边界的工具、权重与素材才进入产线。

### 产线实际使用的每一个模型

| 模型 | 用途 | 授权 | 来源与锁定 |
|---|---|---|---|
| YuNet `face_detection_yunet_2023mar.onnx` | 人脸检测 | **MIT** | opencv_zoo `f12e127` |
| SFace `face_recognition_sface_2021dec.onnx` | 人脸识别 | **Apache-2.0** | opencv_zoo `ba91a3b` |
| NanoDet `object_detection_nanodet_2022nov.onnx` | 目标检测 | **Apache-2.0** | opencv_zoo `510899a` |
| MediaPipe Face Mesh `face_landmark_468.tflite` | 468 点面部关键点 | **Apache-2.0** | mediapipe-assets |
| MediaPipe Iris `iris_landmark.tflite` | 虹膜与视线 | **Apache-2.0** | mediapipe-assets |
| MediaPipe `palm_detection_mediapipe_2023feb.onnx` | 手掌检测 | **Apache-2.0** | opencv_zoo `8de3653` |
| MediaPipe `handpose_estimation_mediapipe_2023feb.onnx` | 手部姿态 | **Apache-2.0** | opencv_zoo `56cef36` |
| Silero VAD `silero_vad_v4.0.onnx` | 语音活动检测 | **MIT** | silero-vad `v4.0` |

八个模型，全部是 MIT 或 Apache 2.0。**每一颗都用 SHA256 与上游 commit 双重锁定**，来源记录在 [`VISION-MODEL-PROVENANCE.json`](VISION-MODEL-PROVENANCE.json)、[`MULTIMODAL-MODEL-PROVENANCE.json`](MULTIMODAL-MODEL-PROVENANCE.json)、[`HAND-MODEL-PROVENANCE.json`](HAND-MODEL-PROVENANCE.json)，可逐一验证。

上表是**随产品出货、在你电脑上运行**的模型。另有一条本机素材生产链（FLUX.2-klein-4B 与 Chroma1-HD，均为 Apache 2.0）留在发行产物范围之外，但同样受本白名单约束——这正是 FLUX dev 全系被排除的原因。角色图目前另借助托管生图服务绘制：本机模型正持续迭代至角色一致性要求，达标后即转回本机生产。上述承诺持续完整有效——白名单约束的是工具与权重，而角色美术本身是所有者的专有财产（见 [ASSETS-LICENSE](../ASSETS-LICENSE.md)），其权利边界按专有资产条款管理。

### 白名单

白名单包含 **MIT、Apache 2.0、BSD、CC0、CC BY**，以及所有者 2026-09-07 批准、完成合规补全后加入的 **MPL-2.0**。MPL 组件须保留完整授权、原通知及对应源代码；分发时提供接收者获取方式，并通过版本与哈希检查。详见 [MPL 合规规则](MPL-2.0-COMPLIANCE.md)。其他授权候选先完成核查；现有工具隔离清单持续有效。

**SIL Open Font License, Version 1.1（SIL OFL 1.1）**依据所有者 2026-09-02 的裁定加入白名单，适用范围限定为字体：须随附 `OFL.txt` 与版权声明，销售范围须包含搭载字体的产品或服务。若日后子集化或修改，便成为 `Modified Version`，必须依保留字体名改名并继续使用 OFL；OFL 的约束范围限定为字体文件本身；使用它的文档与软件沿用各自许可。已入库字体的版本、来源与 SHA-256 见 [`FONTS.md`](../third_party_licenses/FONTS.md)；文件均以原始内容与原始名称分发。

### 保护接收边界的取舍

实际取舍记录使纯净承诺可以审计。完整清单见 [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md)，以下是代价最高的几项：

- **ComfyUI（GPL-3.0）** — 生态里最主流的工具，按裁决完全隔离，备用副本数维持为 0。
- **Krita（GPL-3.0）** — 按所有者 2026-09-07 裁决永久维持安装与使用隔离；本机套件、下载文件及相关候选产物均已删除。
- **miniPaint／AlertifyJS** — miniPaint 顶层虽然是 MIT，正式 bundle 却含 GPL-3.0 AlertifyJS；在打开任何墨寒素材前已完整删除并永久隔离，证明核查须覆盖实际 bundle 与完整依赖树。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系** — 非商业条款覆盖整棵衍生树，因此产线采用 Apache 2.0 的 FLUX.2-klein-4B 与 Chroma1-HD 作为安全底座。
- **CC BY-SA 素材** — share-alike 的适用范围与尽调成本超出接收边界，已彻底移除。
- **Chroma-DC-2K** — 只存在于 `lodestones/chroma-debug-development-only`，该 repo 的许可是 CC BY-NC-SA 4.0，同时触及非商用与 share-alike 两条线；repo 自述「纯供研究」，Apache 2.0 版本状态为待发布。转载站上的重新上传沿用上游许可。同门的 **Chroma1-Radiance 是 Apache 2.0，位于排除范围之外**，当前状态由技术条件决定。
- **OpenPose 官方实现** — 商用年费 US$25,000，改用 Apache 授权的 DWPose／RTMPose／MediaPipe。
- **nvdiffrast、Illustrious-XL、SD3／3.5、混元图像系** — 逐项核查并逐项隔离。

每一项都来自实际评估，并记录了隔离决定。

### 三个经裁决的例外

每项例外均明确记录理由与接收条件：

| 项目 | 授权 | 为什么可以 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 动态链接、About 内声明、授权全文随包；你的代码沿用自身授权 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条款明文保证打包产物位于 GPL 适用范围之外；构建工具留在构建环境 |
| Azure Speech SDK | Microsoft 专有 | 允许商业使用与再分发，并维持授权边界 |

### 这对你意味着什么

墨寒本体是 **MIT 授权**。你可以自由使用、修改、再分发，可以拿去做商业产品，你保有源代码公开与否的选择；每颗纳入的权重都已通过商业条款核查。

想自行核查，证据都在仓库里：[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。

## English

**MoHan is safe to commercialise. Every pipeline weight qualifies for commercial use, every asset meets the accepted licensing terms, and every file has verified provenance.**

MoHan sustains this commitment through checks before investment: research-only, non-commercial, and share-alike terms are evaluated across derivative relationships, and the pipeline accepts tools, weights, and assets that meet its commercial-use boundary.

### Every model actually shipped

| Model | Purpose | License | Source and pin |
|---|---|---|---|
| YuNet `face_detection_yunet_2023mar.onnx` | Face detection | **MIT** | opencv_zoo `f12e127` |
| SFace `face_recognition_sface_2021dec.onnx` | Face recognition | **Apache-2.0** | opencv_zoo `ba91a3b` |
| NanoDet `object_detection_nanodet_2022nov.onnx` | Object detection | **Apache-2.0** | opencv_zoo `510899a` |
| MediaPipe Face Mesh `face_landmark_468.tflite` | 468-point face mesh | **Apache-2.0** | mediapipe-assets |
| MediaPipe Iris `iris_landmark.tflite` | Iris and gaze | **Apache-2.0** | mediapipe-assets |
| MediaPipe `palm_detection_mediapipe_2023feb.onnx` | Palm detection | **Apache-2.0** | opencv_zoo `8de3653` |
| MediaPipe `handpose_estimation_mediapipe_2023feb.onnx` | Hand pose | **Apache-2.0** | opencv_zoo `56cef36` |
| Silero VAD `silero_vad_v4.0.onnx` | Voice activity detection | **MIT** | silero-vad `v4.0` |

Eight models, every one MIT or Apache 2.0. **Each is pinned twice — by SHA256 and by upstream commit** — with provenance recorded in [`VISION-MODEL-PROVENANCE.json`](VISION-MODEL-PROVENANCE.json), [`MULTIMODAL-MODEL-PROVENANCE.json`](MULTIMODAL-MODEL-PROVENANCE.json) and [`HAND-MODEL-PROVENANCE.json`](HAND-MODEL-PROVENANCE.json), so any claim here can be checked independently.

The table above lists models **shipped with the product and executed on your own machine**. A separate local asset-production chain — FLUX.2-klein-4B and Chroma1-HD, both Apache 2.0 — remains outside release artifacts, yet the same allowlist governs it, which is precisely why the entire FLUX dev family was excluded. Character art is currently drawn with help from a hosted image service as well: the local models continue iterating toward the character-consistency bar, and production returns to them once they meet it. The promise above remains fully effective — the allowlist governs tools and weights, while the character artwork itself is the owner's proprietary property (see [ASSETS-LICENSE](../ASSETS-LICENSE.md)) and follows its proprietary asset terms.

### The allowlist

The allowlist includes **MIT, Apache 2.0, BSD, CC0, CC BY**, plus **MPL-2.0**, approved by the owner on 2026-09-07 after compliance remediation. MPL components must retain full license text, original notices and corresponding sources; distribution must provide recipient access and pass version/hash verification. See [MPL compliance rules](MPL-2.0-COMPLIANCE.md). Other license candidates undergo review; existing tool-isolation rulings remain effective.

By the owner's 2026-09-02 ruling, **SIL Open Font License, Version 1.1 (SIL OFL 1.1)** is allowlisted with scope limited to fonts: each font ships with `OFL.txt` and its copyright notice, and sales include a product or service that uses the font. If it is later subsetted or modified, it becomes a `Modified Version`; rename it according to the Reserved Font Name rule and keep using the OFL. The OFL's scope is the font file itself; documents and software that use it retain their respective licenses. Versions, sources, and SHA-256 values for the bundled fonts are in [`FONTS.md`](../third_party_licenses/FONTS.md); the files are redistributed with their original content and names.

### Decisions that protect the acceptance boundary

The record of actual tradeoffs makes the purity commitment auditable. The full list lives in [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md); these carried the greatest cost:

- **ComfyUI (GPL-3.0)** — the ecosystem's dominant tool, fully isolated by ruling, with the fallback-copy count held at zero.
- **Krita (GPL-3.0)** — permanently isolated from installation and use by the owner's 2026-09-07 ruling; the local package, download, and related candidates were deleted.
- **miniPaint / AlertifyJS** — miniPaint is MIT at the top level, but its shipped bundle includes GPL-3.0 AlertifyJS; it was deleted in full before any MoHan asset was opened and remains permanently isolated, proving that audits cover the shipped bundle and complete dependency tree.
- **The entire FLUX.1-dev / FLUX.2-dev / FLUX.2-klein-9B family** — non-commercial terms cover the whole derivative tree, so the pipeline uses Apache 2.0 alternatives FLUX.2-klein-4B and Chroma1-HD are used instead.
- **CC BY-SA material** — the share-alike reach and diligence burden exceed the acceptance boundary, so it was removed entirely.
- **Chroma-DC-2K** — it exists only inside `lodestones/chroma-debug-development-only`, a repository licensed CC BY-NC-SA 4.0, which trips both the non-commercial and the share-alike wires; the repository calls its contents research-only and the Apache 2.0 release remains pending. A mirror on a model-sharing site inherits the upstream licence. Its sibling **Chroma1-Radiance is Apache 2.0 and remains outside the isolation scope**; its current status follows technical conditions.
- **The official OpenPose implementation** — US$25,000 annual commercial fee; replaced by Apache-licensed DWPose, RTMPose and MediaPipe.
- **nvdiffrast, Illustrious-XL, SD3 / 3.5, the Hunyuan image family** — each investigated and individually isolated.

Every entry comes from an actual evaluation with its isolation decision recorded.

### Three adjudicated exceptions

Each exception records its reasoning and acceptance conditions explicitly:

| Item | License | Why it is acceptable |
|---|---|---|
| PySide6 | LGPL-3.0 | Dynamically linked in a onedir layout, declared in About, full license shipped; your own code retains its license |
| PyInstaller | GPL-2.0 with bootloader exception | The exception explicitly places packaged output outside GPL terms; the build tool remains in the build environment |
| Azure Speech SDK | Microsoft proprietary | Commercial use and redistribution permitted while preserving the licensing boundary |

### What this means for you

MoHan itself is **MIT licensed**. Use it, modify it, redistribute it, build a commercial product on it. You retain the choice of whether to publish your source, and every included weight has already passed the commercial-terms review.

To audit it yourself, the evidence is in the repository: [`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md), [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json), [`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md) and `third_party_licenses/`.

## 日本語

**墨寒は商用利用できます。パイプラインの各重みは商用資格を持ち、各素材は受入ライセンス条件を満たし、各ファイルは明確な出所を備えています。**

墨寒は投入前の検証からこの約束を維持します。「研究用途のみ」「非商用」、share-alike の条項を派生関係全体で評価し、商用受入境界を満たすツール、重み、素材を産線に採用します。

### 実際に同梱している全モデル

| モデル | 用途 | ライセンス | 出所と固定 |
|---|---|---|---|
| YuNet `face_detection_yunet_2023mar.onnx` | 顔検出 | **MIT** | opencv_zoo `f12e127` |
| SFace `face_recognition_sface_2021dec.onnx` | 顔認識 | **Apache-2.0** | opencv_zoo `ba91a3b` |
| NanoDet `object_detection_nanodet_2022nov.onnx` | 物体検出 | **Apache-2.0** | opencv_zoo `510899a` |
| MediaPipe Face Mesh `face_landmark_468.tflite` | 468 点顔ランドマーク | **Apache-2.0** | mediapipe-assets |
| MediaPipe Iris `iris_landmark.tflite` | 虹彩と視線 | **Apache-2.0** | mediapipe-assets |
| MediaPipe `palm_detection_mediapipe_2023feb.onnx` | 手のひら検出 | **Apache-2.0** | opencv_zoo `8de3653` |
| MediaPipe `handpose_estimation_mediapipe_2023feb.onnx` | 手指姿勢 | **Apache-2.0** | opencv_zoo `56cef36` |
| Silero VAD `silero_vad_v4.0.onnx` | 音声区間検出 | **MIT** | silero-vad `v4.0` |

八つのモデルはすべて MIT または Apache 2.0 です。**いずれも SHA256 と上流コミットの二重で固定**しており、出所は [`VISION-MODEL-PROVENANCE.json`](VISION-MODEL-PROVENANCE.json)、[`MULTIMODAL-MODEL-PROVENANCE.json`](MULTIMODAL-MODEL-PROVENANCE.json)、[`HAND-MODEL-PROVENANCE.json`](HAND-MODEL-PROVENANCE.json) に記録され、第三者が個別に検証できます。

上の表は**製品に同梱され、利用者の PC 上で実行される**モデルです。これとは別にローカル素材生成チェーン（FLUX.2-klein-4B と Chroma1-HD、いずれも Apache 2.0）がありますが、リリース成果物の範囲外に保持します。それでも同じホワイトリストの適用対象であり、FLUX dev 系列を全面的に除外したのはそのためです。キャラクター画像は現在、ホスト型の画像生成サービスの助けも借りて制作しています。ローカルモデルはキャラクターの同一性について要求水準へ向けて継続的に改善し、到達時点でローカル生産に戻します。上記の約束は完全に維持します。ホワイトリストが縛るのは道具と重みであり、キャラクター美術そのものは所有者の専有財産（[ASSETS-LICENSE](../ASSETS-LICENSE.md) を参照）で、専有資産条項に従います。

### ホワイトリスト

ホワイトリストは **MIT、Apache 2.0、BSD、CC0、CC BY** と、2026-09-07 に所有者が承認し義務の補完後に追加した **MPL-2.0** を含みます。MPL コンポーネントはライセンス全文、元の通知と対応ソースを保持し、配布時に受領者の取得方法を示し、バージョンとハッシュ検証を通過する必要があります。[MPL 遵守規則](MPL-2.0-COMPLIANCE.md)を参照してください。その他のライセンス候補は引き続き審査し、既存ツールの隔離裁定を維持します。

所有者による 2026-09-02 の裁定に基づき、**SIL Open Font License, Version 1.1（SIL OFL 1.1）**は適用範囲をフォントに限定してホワイトリストへ追加します。各フォントには `OFL.txt` と著作権表示を添付し、販売時はフォントを使用する製品またはサービスに含めます。後日サブセット化または改変した場合は `Modified Version` となるため、Reserved Font Name の規則に従って改名し、OFL を継続して使用します。OFL の適用範囲はフォントファイル自体です。それを使用する文書やソフトウェアは、それぞれのライセンスを維持します。同梱フォントのバージョン、出所、SHA-256 は [`FONTS.md`](../third_party_licenses/FONTS.md) に記録しています。ファイルは元の内容と名前で再配布します。

### 受入境界を守る選択

実際の選択記録により、純度の約束を監査できます。全容は [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md) にあります。代償が大きかったものを挙げます。

- **ComfyUI（GPL-3.0）** — エコシステム最大の主流ツールですが、裁定により完全隔離し、予備複製数を 0 に維持します。
- **Krita（GPL-3.0）** — 所有者の 2026-09-07 裁定により導入と使用から永久隔離；ローカルパッケージ、ダウンロード、関連候補成果物は削除済みです。
- **miniPaint／AlertifyJS** — miniPaint の最上位表示は MIT ですが、配布 bundle に GPL-3.0 AlertifyJS が含まれます。墨寒素材を一切開く前に完全削除して永久隔離し、監査対象が実配布 bundle と完全な依存ツリーまで必要であることを記録しました。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 系列すべて** — 非商用条項が派生ツリー全体を対象とするため、Apache 2.0 の FLUX.2-klein-4B と Chroma1-HD を土台に採用しました。
- **CC BY-SA 素材** — share-alike の波及とデューデリジェンス費用が受入境界を超えるため、完全に撤去しました。
- **Chroma-DC-2K** — `lodestones/chroma-debug-development-only` にのみ存在し、同リポジトリのライセンスは CC BY-NC-SA 4.0 で、非商用と share-alike の両方に抵触します。リポジトリ自身が「研究目的のみ」と明記しており、Apache 2.0 版は公開待ちです。転載サイトでの再アップロードには上流ライセンスが引き続き適用されます。姉妹モデルの **Chroma1-Radiance は Apache 2.0 で隔離対象範囲外**であり、現在の状態は技術条件によって決まります。
- **OpenPose 公式実装** — 商用は年額 US$25,000。Apache ライセンスの DWPose／RTMPose／MediaPipe に置き換えました。
- **nvdiffrast、Illustrious-XL、SD3／3.5、Hunyuan 画像系** — 一件ずつ調査し、一件ずつ隔離しました。

いずれも実際に検討し、隔離判断を記録した選択肢です。

### 裁定した三つの例外

各例外は理由と受入条件を明記します。

| 項目 | ライセンス | 許容できる理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 構成で動的リンクし、About に表示、全文を同梱。利用者のコードは自身のライセンスを維持 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条項が成果物を GPL の適用外と明記。ビルドツールはビルド環境に保持 |
| Azure Speech SDK | Microsoft 独自 | 商用利用と再配布が可能で、ライセンス境界を維持 |

### これが利用者にとって意味すること

墨寒本体は **MIT ライセンス**です。使用、改変、再配布は自由で、商用製品の土台にもできます。自身のソースを公開するかを選択でき、採用済みの各重みは商用条項の審査を通過しています。

自ら監査する場合、証拠はリポジトリ内にあります。[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。
