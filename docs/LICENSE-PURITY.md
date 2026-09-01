# 授權純淨承諾／授权纯净承诺／License Purity Commitment／ライセンス純度に関する約束

## 繁體中文

**墨寒可以商用。整條產線沒有一顆非商用權重、沒有一份 copyleft 素材、沒有一個授權不明的檔案。**

多數 AI 專案做不到這件事。它們的模型往往帶著「僅供研究」「非商用」或 share-alike 條款，而這些限制會傳染到你用它做出來的任何東西——通常是在你已經投入很久之後才發現。

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

上表是**隨產品出貨、在你電腦上執行**的模型。另有一條本機素材生產鏈（FLUX.2-klein-4B 與 Chroma1-HD，皆為 Apache 2.0）不隨發行產物散布，但同樣受本白名單約束——這正是 FLUX dev 全系被排除的原因。角色圖目前另借助託管生圖服務繪製：本機模型在角色一致性上尚未達到要求，待其迭代到位即轉回本機生產。這不動搖上述承諾——白名單約束的是工具與權重，而角色美術本身是擁有者的專有財產（見 [ASSETS-LICENSE](../ASSETS-LICENSE.md)），不受任何開源條款約束。

### 白名單

只有這四種授權能進產線：**MIT、Apache 2.0、CC0、CC BY**（BSD 等同級視為等同）。不在名單上的一律先查證，查不過就進黑名單。

### 我們拒絕過什麼

拒絕的紀錄比宣稱更有說服力。完整清單見 [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md)，以下是代價最高的幾項：

- **ComfyUI（GPL-3.0）** — 生態系最主流的工具，完全出局，不留備援副本。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系** — 非商用條款會傳染整棵衍生樹。改用 Apache 2.0 的 FLUX.2-klein-4B 與 Chroma1-HD 作為安全基底。
- **CC BY-SA 素材** — share-alike 的傳染性與盡調成本不可接受，已徹底移除。
- **Chroma-DC-2K** — 只存在於 `lodestones/chroma-debug-development-only`，該 repo 的授權是 CC BY-NC-SA 4.0，同時踩到非商用與 share-alike 兩條線；repo 自述「純供研究」，Apache 2.0 版本尚未存在。轉載站上的重新上傳不改變上游授權。同門的 **Chroma1-Radiance 是 Apache 2.0，不在排除之列**，未採用的原因是技術面而非授權面。
- **OpenPose 官方實作** — 商用年費 US$25,000，改用 Apache 授權的 DWPose／RTMPose／MediaPipe。
- **nvdiffrast、Illustrious-XL、SD3／3.5、Hunyuan 影像系** — 逐一查證、逐一排除。

每一項都是實際評估後放棄的選項，不是沒遇到。

### 三個經裁決的例外

例外必須寫明理由，不能默默放行：

| 項目 | 授權 | 為什麼可以 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 動態連結、About 內聲明、授權全文隨包，不影響你的程式碼授權 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外條款明文保證打包產物不受 GPL 約束；建置工具不進產物 |
| Azure Speech SDK | Microsoft 專有 | 可商用、可再散布、不傳染 |

### 這對你代表什麼

墨寒本體是 **MIT 授權**。你可以自由使用、修改、再散布，可以拿去做商業產品，不必公開你的原始碼，不必擔心某顆權重的非商用條款在事後追上來。

想自行查核，證據都在庫內：[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。

## 简体中文

**墨寒可以商用。整条产线没有一颗非商用权重、没有一份 copyleft 素材、没有一个授权不明的文件。**

多数 AI 项目做不到这件事。它们的模型往往带着「仅供研究」「非商用」或 share-alike 条款，而这些限制会传染到你用它做出来的任何东西——通常是在你已经投入很久之后才发现。

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

上表是**随产品出货、在你电脑上运行**的模型。另有一条本机素材生产链（FLUX.2-klein-4B 与 Chroma1-HD，均为 Apache 2.0）不随发行产物分发，但同样受本白名单约束——这正是 FLUX dev 全系被排除的原因。角色图目前另借助托管生图服务绘制：本机模型在角色一致性上尚未达到要求，待其迭代到位即转回本机生产。这不动摇上述承诺——白名单约束的是工具与权重，而角色美术本身是所有者的专有财产（见 [ASSETS-LICENSE](../ASSETS-LICENSE.md)），不受任何开源条款约束。

### 白名单

只有这四种授权能进产线：**MIT、Apache 2.0、CC0、CC BY**（BSD 等同级视为等同）。不在名单上的一律先核查，核查不过就进黑名单。

### 我们拒绝过什么

拒绝的记录比声明更有说服力。完整清单见 [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md)，以下是代价最高的几项：

- **ComfyUI（GPL-3.0）** — 生态里最主流的工具，完全出局，不保留备用副本。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 全系** — 非商用条款会传染整棵衍生树。改用 Apache 2.0 的 FLUX.2-klein-4B 与 Chroma1-HD 作为安全底座。
- **CC BY-SA 素材** — share-alike 的传染性与尽调成本不可接受，已彻底移除。
- **Chroma-DC-2K** — 只存在于 `lodestones/chroma-debug-development-only`，该 repo 的许可是 CC BY-NC-SA 4.0，同时触及非商用与 share-alike 两条线；repo 自述「纯供研究」，Apache 2.0 版本尚未存在。转载站上的重新上传不改变上游许可。同门的 **Chroma1-Radiance 是 Apache 2.0，不在排除之列**，未采用的原因是技术面而非许可面。
- **OpenPose 官方实现** — 商用年费 US$25,000，改用 Apache 授权的 DWPose／RTMPose／MediaPipe。
- **nvdiffrast、Illustrious-XL、SD3／3.5、混元图像系** — 逐项核查、逐项排除。

每一项都是实际评估后放弃的选项，不是没遇到。

### 三个经裁决的例外

例外必须写明理由，不能默默放行：

| 项目 | 授权 | 为什么可以 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 动态链接、About 内声明、授权全文随包，不影响你的代码授权 |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条款明文保证打包产物不受 GPL 约束；构建工具不进产物 |
| Azure Speech SDK | Microsoft 专有 | 可商用、可再分发、不传染 |

### 这对你意味着什么

墨寒本体是 **MIT 授权**。你可以自由使用、修改、再分发，可以拿去做商业产品，不必公开你的源代码，不必担心某颗权重的非商用条款在事后追上来。

想自行核查，证据都在仓库里：[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。

## English

**MoHan is safe to commercialise. Not one non-commercial weight, not one copyleft asset, not one file of unknown provenance sits anywhere in the pipeline.**

Most AI projects cannot say this. Their models arrive carrying research-only, non-commercial, or share-alike terms, and those restrictions spread to whatever you build — usually discovered long after the investment is made.

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

The table above lists models **shipped with the product and executed on your own machine**. A separate local asset-production chain — FLUX.2-klein-4B and Chroma1-HD, both Apache 2.0 — never travels inside a release artifact, yet the same allowlist governs it, which is precisely why the entire FLUX dev family was excluded. Character art is currently drawn with help from a hosted image service as well: the local models do not yet meet the bar for character consistency, and production returns to them once they do. That does not weaken the promise above — the allowlist governs tools and weights, while the character artwork itself is the owner's proprietary property (see [ASSETS-LICENSE](../ASSETS-LICENSE.md)) and carries no open-source terms.

### The allowlist

Four licenses may enter the pipeline: **MIT, Apache 2.0, CC0, CC BY** (BSD-class treated as equivalent). Anything else is investigated first and blacklisted if it does not clear.

### What was turned down

A record of refusals persuades more than a claim of purity. The full list lives in [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md); these cost the most to give up:

- **ComfyUI (GPL-3.0)** — the ecosystem's dominant tool, excluded outright, with no fallback copy retained.
- **The entire FLUX.1-dev / FLUX.2-dev / FLUX.2-klein-9B family** — non-commercial terms infect the whole derivative tree. Apache 2.0 alternatives FLUX.2-klein-4B and Chroma1-HD are used instead.
- **CC BY-SA material** — the share-alike reach and diligence burden were judged unacceptable, so it was removed entirely.
- **Chroma-DC-2K** — it exists only inside `lodestones/chroma-debug-development-only`, a repository licensed CC BY-NC-SA 4.0, which trips both the non-commercial and the share-alike wires; the repository calls its contents research-only and the Apache 2.0 release does not exist yet. A mirror on a model-sharing site does not change the upstream licence. Its sibling **Chroma1-Radiance is Apache 2.0 and is not excluded** — it is unused for technical reasons, not licensing ones.
- **The official OpenPose implementation** — US$25,000 annual commercial fee; replaced by Apache-licensed DWPose, RTMPose and MediaPipe.
- **nvdiffrast, Illustrious-XL, SD3 / 3.5, the Hunyuan image family** — each investigated, each excluded.

Every entry is an option evaluated and abandoned, not one never encountered.

### Three adjudicated exceptions

An exception must state its reasoning rather than pass quietly:

| Item | License | Why it is acceptable |
|---|---|---|
| PySide6 | LGPL-3.0 | Dynamically linked in a onedir layout, declared in About, full license shipped — your own code stays unaffected |
| PyInstaller | GPL-2.0 with bootloader exception | The exception explicitly frees packaged output from GPL terms; the build tool never enters the artifact |
| Azure Speech SDK | Microsoft proprietary | Commercial use and redistribution permitted, with no copyleft reach |

### What this means for you

MoHan itself is **MIT licensed**. Use it, modify it, redistribute it, build a commercial product on it. You need not open your source, and no weight buried in the stack will surface later with a non-commercial clause attached.

To audit it yourself, the evidence is in the repository: [`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md), [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json), [`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md) and `third_party_licenses/`.

## 日本語

**墨寒は商用利用できます。パイプライン全体に、非商用の重みも、copyleft の素材も、出所不明のファイルも一つとしてありません。**

多くの AI プロジェクトはこれを言えません。モデルには「研究用途のみ」「非商用」あるいは share-alike の条項が付いており、その制約は作ったものすべてに伝播します。しかも気づくのは、たいてい多くを投じた後です。

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

上の表は**製品に同梱され、利用者の PC 上で実行される**モデルです。これとは別にローカル素材生成チェーン（FLUX.2-klein-4B と Chroma1-HD、いずれも Apache 2.0）がありますが、リリース成果物には同梱されません。それでも同じホワイトリストの適用対象であり、FLUX dev 系列を全面的に除外したのはそのためです。キャラクター画像は現在、ホスト型の画像生成サービスの助けも借りて制作しています。ローカルモデルはキャラクターの同一性について要求水準にまだ届いておらず、届いた時点でローカル生産に戻します。これは上記の約束を揺るがしません。ホワイトリストが縛るのは道具と重みであり、キャラクター美術そのものは所有者の専有財産（[ASSETS-LICENSE](../ASSETS-LICENSE.md) を参照）でオープンソース条項の対象外です。

### ホワイトリスト

パイプラインに入れるのは四種類だけです。**MIT、Apache 2.0、CC0、CC BY**（BSD 系は同等とみなす）。それ以外は必ず調査し、通らなければ黒名単に入ります。

### 見送ったもの

純度の主張よりも、断った記録のほうが説得力を持ちます。全容は [`LICENSE-BLACKLIST.md`](LICENSE-BLACKLIST.md) にあります。代償が大きかったものを挙げます。

- **ComfyUI（GPL-3.0）** — エコシステム最大の主流ツールですが完全に除外し、予備の複製も残していません。
- **FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 系列すべて** — 非商用条項が派生ツリー全体に伝播します。Apache 2.0 の FLUX.2-klein-4B と Chroma1-HD を土台に採用しました。
- **CC BY-SA 素材** — share-alike の波及とデューデリジェンス費用が許容できず、完全に撤去しました。
- **Chroma-DC-2K** — `lodestones/chroma-debug-development-only` にのみ存在し、同リポジトリのライセンスは CC BY-NC-SA 4.0 で、非商用と share-alike の両方に抵触します。リポジトリ自身が「研究目的のみ」と明記しており、Apache 2.0 版はまだ存在しません。転載サイトでの再アップロードは上流のライセンスを変えません。姉妹モデルの **Chroma1-Radiance は Apache 2.0 であり除外対象ではありません**——採用していない理由はライセンスではなく技術面です。
- **OpenPose 公式実装** — 商用は年額 US$25,000。Apache ライセンスの DWPose／RTMPose／MediaPipe に置き換えました。
- **nvdiffrast、Illustrious-XL、SD3／3.5、Hunyuan 画像系** — 一件ずつ調査し、一件ずつ除外しました。

いずれも検討の末に手放した選択肢であり、出会わなかったわけではありません。

### 裁定した三つの例外

例外は黙って通さず、理由を明記します。

| 項目 | ライセンス | 許容できる理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | onedir 構成で動的リンクし、About に表示、全文を同梱。利用者のコードには影響しません |
| PyInstaller | GPL-2.0＋bootloader exception | 例外条項が成果物を GPL の適用外と明記。ビルドツールは成果物に入りません |
| Azure Speech SDK | Microsoft 独自 | 商用利用と再配布が可能で、copyleft の波及もありません |

### これが利用者にとって意味すること

墨寒本体は **MIT ライセンス**です。使用、改変、再配布は自由で、商用製品の土台にもできます。自身のソースを公開する必要はなく、奥に埋もれた重みの非商用条項が後から追いかけてくることもありません。

自ら監査する場合、証拠はリポジトリ内にあります。[`ASSETS-LICENSE.md`](../ASSETS-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)、[`THIRD_PARTY_DENYLIST.json`](../THIRD_PARTY_DENYLIST.json)、[`UI-ASSET-PROVENANCE.md`](UI-ASSET-PROVENANCE.md)、`third_party_licenses/`。
