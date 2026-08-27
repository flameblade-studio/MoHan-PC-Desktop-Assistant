# 第三方聲明／第三方声明／Third-Party Notices／第三者ソフトウェアに関する通知

## 繁體中文

### 概要

MoHan Desktop Assistant 採用 MIT License，但其原始碼及 Release 安裝包會使用依各自授權條款提供的第三方元件。`LICENSE` 中的墨寒 MIT License 不會變更這些第三方條款。

### 直接 Python 相依套件

| 元件 | 目前固定版本 | 授權 |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 條款） |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |
| [cryptography](https://cryptography.io/) | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| [NumPy](https://numpy.org/) | 2.5.2 | BSD-3-Clause |
| [OpenCV Python](https://pypi.org/project/opencv-python/) | 5.0.0.93 | Apache-2.0 |

### 建置專用工具鏈

下列元件只用於建置、檢查或封裝，不是墨寒的 Python 執行期相依套件。v4.0.0 Windows 正式套件必須包含由這套工具鏈編譯的第一方 MIT 授權 `_mohan_accel` 模組，但不會把 Rust、Maturin 或 PyO3 當成使用者必須安裝的執行期元件；封裝後會由 CI 逐項驗證包內模組與證據。

| 元件 | 固定版本 | 授權 | 用途 |
| --- | ---: | --- | --- |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception | Windows／Preview 封裝 |
| [Rust compiler and standard library](https://www.rust-lang.org/) | 1.97.1 | MIT OR Apache-2.0 | 第一方原生模組編譯與檢查 |
| [Maturin](https://github.com/PyO3/maturin) | 1.14.1 | MIT OR Apache-2.0 | 建置並驗證 Python wheel |
| [PyO3](https://github.com/PyO3/pyo3) | 0.29.2 | MIT OR Apache-2.0 | Rust／Python 邊界的建置期繫結 |
| [Rayon](https://github.com/rayon-rs/rayon) | 1.12.0 | MIT OR Apache-2.0 | 編譯進第一方原生模組；RGBA 達 262,144 pixels 且執行環境有多個工作執行緒時，條件式啟用平行處理 |
| [BiRefNet HR Matting](https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting) | `5d6b6f8adcb5b417c871b1d84ceaae9871355b7f` | MIT | 僅供本機美術製作流程進行高解析度人物去背；模型權重、推論環境及快取不屬於墨寒執行期，亦不隨安裝程式散布 |
| [InstantMesh（TencentARC 官方實作）](https://github.com/TencentARC/InstantMesh) | `08822c52fdc399b93ea00e4fa9e596344ed52ccc` | Apache-2.0 | 原始碼僅保留作授權與來源證據；完整推論管線已停用，模型權重、推論環境及快取不得進入正式 24／600 產線、墨寒執行期或安裝程式 |

`native-wheels/` 與 `native-wheels-<id>/` 只保存本機或 CI 建置產物與證據，已由 Git 忽略且不列為 Release 資產。macOS／Linux 目前只在核心 CI 建置並執行等價與效能測試，不宣稱 Preview 已封裝相同原生能力。Rayon 1.12.0 的 Rust serial／Rayon 邊界測試與 Python／native 實測提供結果等價及效能證據。PyO3 `PyBackedBytes` 借用輸入，避免額外複製輸入；輸出仍建立新的 Python `bytes`，因此不宣稱端到端零複製。沒有 SIMD 實作證據，故不宣稱 SIMD。

BiRefNet 使用官方 `ZhengPeng7/BiRefNet_HR-matting` 原始碼與權重，固定於上列不可變 revision；兩者均依 MIT 授權使用。完整授權文字保存在 `third_party_licenses/BiRefNet-LICENSE.txt`，本機美術工具清冊記錄於 `sbom/local-art-tooling-components.toml`。本專案未使用或再散布 BRIA／RMBG-2.0 權重。

InstantMesh 的 TencentARC 官方原始碼固定於上列不可變 commit，只保留作授權與來源證據。上游在該版本提供 Apache 2.0 `LICENSE`，但沒有獨立 `NOTICE` 或具名 copyright header；本清單因此不虛構著作權人，並原樣保留完整授權文字於 `third_party_licenses/InstantMesh-LICENSE.txt`。官方論文歸屬：*InstantMesh: Efficient 3D Mesh Generation from a Single Image with Sparse-view Large Reconstruction Models*，Jiale Xu、Weihao Cheng、Yiming Gao、Xintao Wang、Shenghua Gao、Ying Shan，arXiv:2404.07191（2024）。因完整管線依賴永久禁用的 `nvdiffrast` 與未獲充分權重授權證據的 Zero123++，該管線不得再次下載、建置、載入或用於正式 24／600 產線。

### v4.0.0 本機視覺模型

### 隨包提供的 Face Mesh、虹膜與語音活動模型

Face Mesh、虹膜與 Silero VAD 已隨 Windows 正式封裝提供；它們由 OpenCV 5 DNN 在本機載入，模型檔、授權、來源、大小與 SHA-256 均記錄於 `sbom/components.toml` 與 `docs/MULTIMODAL-MODEL-PROVENANCE.json`。Windows 正式封裝規格要求模型資產在建置前完成雜湊驗證；若模型或執行引擎不可用，既有視覺、語音與 2.5D 功能會安全退回既有路徑。

| 模型檔案 | 用途 | 來源與授權 | SHA-256 |
| --- | --- | --- | --- |
| `face_landmark_468.tflite` | MediaPipe Face Mesh 468 點 | [MediaPipe 官方資產](https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite)；Apache-2.0 | `1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814` |
| `iris_landmark.tflite` | 每眼 5 點虹膜定位 | [MediaPipe 官方資產](https://storage.googleapis.com/mediapipe-assets/iris_landmark.tflite)；Apache-2.0 | `d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f` |
| `silero_vad_v4.0.onnx` | 16 kHz 語音活動偵測 | [Silero VAD v4.0](https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx)；MIT | `a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28` |

下列 ONNX 模型位於 `assets/vision-models/`，只供使用者明確啟用的本機視覺功能使用。五個模型均已從表列不可變 OpenCV Zoo commit 的官方 Git LFS 實體來源取得，並核對官方 LFS pointer、精確 byte size、本機檔案及 SHA-256；模型目錄內的官方 LICENSE／README 也已在相同 commit 確認。完整機器可讀證據分別見 `docs/VISION-MODEL-PROVENANCE.json` 與 `docs/HAND-MODEL-PROVENANCE.json`，不以移動中的 `main` 分支作為來源版本。

| 模型檔 | 用途 | 官方來源 | 個別授權 | SHA-256 |
| --- | --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | YuNet 臉部偵測；232,589 bytes | [OpenCV Zoo commit `f12e12798e8314f7c074a6656816c048dcc95b7a`](https://github.com/opencv/opencv_zoo/tree/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet) | MIT；Copyright (c) 2020 Shiqi Yu | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `face_recognition_sface_2021dec.onnx` | SFace 臉部特徵；38,696,353 bytes | [OpenCV Zoo commit `ba91a3b91d00d76e86540d4013f944bd6b514e39`](https://github.com/opencv/opencv_zoo/tree/ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface) | Apache-2.0 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| `object_detection_nanodet_2022nov.onnx` | NanoDet 常見物品偵測；3,800,954 bytes | [OpenCV Zoo commit `510899a2a0adb8c25957915fd030d66dbd553919`](https://github.com/opencv/opencv_zoo/tree/510899a2a0adb8c25957915fd030d66dbd553919/models/object_detection_nanodet) | Apache-2.0 | `4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186` |
| `palm_detection_mediapipe_2023feb.onnx` | 手掌偵測；3,905,734 bytes | [OpenCV Zoo commit `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5`](https://github.com/opencv/opencv_zoo/tree/8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5/models/palm_detection_mediapipe) | Apache-2.0 | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` |
| `handpose_estimation_mediapipe_2023feb.onnx` | 每手 21 點手部姿態估計；4,099,621 bytes | [OpenCV Zoo commit `56cef36ae45e5a6da7eba01a91631f6d7e955da1`](https://github.com/opencv/opencv_zoo/tree/56cef36ae45e5a6da7eba01a91631f6d7e955da1/models/handpose_estimation_mediapipe) | Apache-2.0 | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` |

五個模型已由 `sbom/components.toml` 的機器可讀資產清單及 CycloneDX SBOM 驗證器管理；名稱、版本、封裝路徑、大小、SHA-256、不可變來源與授權缺一即失敗。`build.ps1` 會把整個 `assets` 目錄納入 Windows 套件，因此五個已驗證模型會沿既有封裝路徑列入成品與 SBOM。未來 theme／outfit pack 若含第三方素材，也必須在 package manifest 提供相同欄位並納入 SBOM；來源或授權不明的素材不得進入正式封裝。

換裝套件可包含多套服裝、配色與配件，但只能提供 `garment`、`accessory`、`occlusion` 資產，並以核准的 ID 與 SHA-256 引用官方受保護 `core_body_skin`。套件不得提供或覆寫 identity、face、skin tone、body shape 或核心膚色本體。頸、肩、手臂等露膚區域只能由官方本體透過可見／遮蔽遮罩呈現。現實服裝照片只可登記為 `design-reference-only`，預設不可再散布且不得封裝；交付素材必須標示為具再散布權的原創衍生設計。

### Preview 封裝工具

Linux x86_64 功能受限 Preview 使用官方 [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) 組裝。建置流程會下載上游 `continuous` x86_64 資產，但只有在其 SHA-256 等於 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` 時才接受。所記錄的上游來源 commit 為 `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`，GitHub 資產 ID 為 `324406882`。

`appimagetool` 仍受其自身的上游授權條款約束。

### 封裝所含執行階段元件

Windows 單一目錄安裝包亦可能包含 Python（PSF License）、Qt 及 Shiboken（LGPL／GPL／商業條款）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain），以及它們所需的執行階段函式庫。macOS 與 Linux 功能受限 Preview 安裝包只包含 `requirements-preview.txt` 宣告的較小 Preview 相依集合。

封裝版面會將動態連結的 Qt／PySide 函式庫保留為 `_internal` 下的獨立檔案，讓接收者可以檢查或替換這些函式庫。對應的 Qt for Python 原始碼 Release 可從 [Qt 官方下載封存](https://download.qt.io/official_releases/QtForPython/)取得。

完整授權文字及原始碼連結可在各上游專案與已安裝套件的中繼資料中取得。散布者應檢查實際交付的精確相依版本，並保留所有上游著作權及授權聲明。

### Windows 安裝程式語言檔

隨附的 `installer/languages/ChineseTraditional.isl` 是來自 [Inno Setup 原始碼儲存庫](https://github.com/jrsoftware/issrc)的官方繁體中文訊息翻譯，固定於來源 commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）。該檔案依 [Inno Setup 授權](https://jrsoftware.org/files/is/license.txt)散布，並保留檔頭中的上游翻譯者資訊。

### 服務與商標

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE 及其他服務名稱均為其各自權利人的商標。API 存取、雲端生成語音、OAuth 使用及服務配額均受各供應商自身條款約束。

OpenAI Responses API 由 Python 標準庫 `urllib.request` 經 HTTPS 直接存取；墨寒沒有 `openai` Python SDK 執行期相依。OpenAI 是使用者自行授權的外部服務，不是隨安裝包散布的元件，因此不會在 CycloneDX 元件清單中虛構 SDK 版本或授權；`sbom/components.toml` 另以機器可讀外部服務政策記錄此邊界。

## 简体中文

### 概要

MoHan Desktop Assistant 采用 MIT License，但其源代码及 Release 安装包会使用依各自许可条款提供的第三方组件。`LICENSE` 中的墨寒 MIT License 不会变更这些第三方条款。

### 直接 Python 依赖包

| 组件 | 当前固定版本 | 许可 |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 条款） |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |
| [cryptography](https://cryptography.io/) | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| [NumPy](https://numpy.org/) | 2.5.2 | BSD-3-Clause |
| [OpenCV Python](https://pypi.org/project/opencv-python/) | 5.0.0.93 | Apache-2.0 |

### 构建专用工具链

以下组件仅用于构建、检查或打包，不是墨寒的 Python 运行时依赖包。v4.0.0 Windows 正式软件包必须包含由这套工具链编译的第一方 MIT 许可 `_mohan_accel` 模块，但不会将 Rust、Maturin 或 PyO3 作为用户必须安装的运行时组件；打包后会由 CI 逐项验证软件包内模块与证据。

| 组件 | 固定版本 | 许可 | 用途 |
| --- | ---: | --- | --- |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception | Windows／Preview 打包 |
| [Rust 编译器与标准库](https://www.rust-lang.org/) | 1.97.1 | MIT OR Apache-2.0 | 第一方原生模块编译与检查 |
| [Maturin](https://github.com/PyO3/maturin) | 1.14.1 | MIT OR Apache-2.0 | 构建并验证 Python wheel |
| [PyO3](https://github.com/PyO3/pyo3) | 0.29.2 | MIT OR Apache-2.0 | Rust／Python 边界的构建期绑定 |
| [Rayon](https://github.com/rayon-rs/rayon) | 1.12.0 | MIT OR Apache-2.0 | 编译进第一方原生模块；RGBA 达到 262,144 pixels 且运行环境有多个工作线程时，条件式启用并行处理 |
| [BiRefNet HR Matting](https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting) | `5d6b6f8adcb5b417c871b1d84ceaae9871355b7f` | MIT | 仅用于本地美术制作流程的高分辨率人物去背；模型权重、推理环境与缓存不属于墨寒运行时，也不随安装程序分发 |
| [InstantMesh（TencentARC 官方实现）](https://github.com/TencentARC/InstantMesh) | `08822c52fdc399b93ea00e4fa9e596344ed52ccc` | Apache-2.0 | 源代码仅保留为许可与来源证据；完整推理管线已停用，模型权重、推理环境与缓存不得进入正式 24／600 产线、墨寒运行时或安装程序 |

`native-wheels/` 与 `native-wheels-<id>/` 只保存本地或 CI 构建产物与证据，已被 Git 忽略且不列为 Release 资产。macOS／Linux 目前仅在核心 CI 构建并运行等价与性能测试，不声明 Preview 已打包相同原生能力。Rayon 1.12.0 的 Rust serial／Rayon 边界测试与 Python／native 实测提供结果等价和性能证据。PyO3 `PyBackedBytes` 借用输入，避免额外复制输入；输出仍创建新的 Python `bytes`，因此不声明端到端零复制。没有 SIMD 实现证据，故不声明 SIMD。

BiRefNet 使用官方 `ZhengPeng7/BiRefNet_HR-matting` 源代码与权重，并固定到上列不可变 revision；两者均按 MIT 许可证使用。完整许可证文本保存在 `third_party_licenses/BiRefNet-LICENSE.txt`，本地美术工具清单记录于 `sbom/local-art-tooling-components.toml`。本项目未使用或再分发 BRIA／RMBG-2.0 权重。

InstantMesh 的 TencentARC 官方源代码固定到上列不可变 commit，仅保留为许可与来源证据。上游在该版本提供 Apache 2.0 `LICENSE`，但没有独立 `NOTICE` 或具名 copyright header；本清单因此不虚构著作权人，并在 `third_party_licenses/InstantMesh-LICENSE.txt` 原样保留完整许可证文本。官方论文署名：*InstantMesh: Efficient 3D Mesh Generation from a Single Image with Sparse-view Large Reconstruction Models*，Jiale Xu、Weihao Cheng、Yiming Gao、Xintao Wang、Shenghua Gao、Ying Shan，arXiv:2404.07191（2024）。由于完整管线依赖永久禁用的 `nvdiffrast` 与缺乏充分权重许可证据的 Zero123++，该管线不得再次下载、构建、加载或用于正式 24／600 产线。

### v4.0.0 本地视觉模型

### 随包提供的 Face Mesh、虹膜与语音活动模型

Face Mesh、虹膜与 Silero VAD 已随 Windows 正式封装提供；它们由 OpenCV 5 DNN 在本机加载，模型文件、许可证、来源、大小与 SHA-256 均记录于 `sbom/components.toml` 与 `docs/MULTIMODAL-MODEL-PROVENANCE.json`。Windows 正式打包规范要求模型资产在构建前完成哈希验证；若模型或运行引擎不可用，既有视觉、语音与 2.5D 功能会安全退回既有路径。

| 模型文件 | 用途 | 来源与许可证 | SHA-256 |
| --- | --- | --- | --- |
| `face_landmark_468.tflite` | MediaPipe Face Mesh 468 点 | [MediaPipe 官方资产](https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite)；Apache-2.0 | `1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814` |
| `iris_landmark.tflite` | 每眼 5 点虹膜定位 | [MediaPipe 官方资产](https://storage.googleapis.com/mediapipe-assets/iris_landmark.tflite)；Apache-2.0 | `d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f` |
| `silero_vad_v4.0.onnx` | 16 kHz 语音活动检测 | [Silero VAD v4.0](https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx)；MIT | `a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28` |

以下 ONNX 模型位于 `assets/vision-models/`，仅供用户明确启用的本地视觉功能使用。五个模型均从表列不可变 OpenCV Zoo commit 的官方 Git LFS 实体来源取得，并核对官方 LFS pointer、精确 byte size、本地文件及 SHA-256；模型目录内的官方 LICENSE／README 也已在相同 commit 确认。完整机器可读证据分别见 `docs/VISION-MODEL-PROVENANCE.json` 与 `docs/HAND-MODEL-PROVENANCE.json`，不以持续变动的 `main` 分支作为来源版本。

| 模型文件 | 用途 | 官方来源 | 单独许可 | SHA-256 |
| --- | --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | YuNet 人脸检测；232,589 bytes | [OpenCV Zoo commit `f12e12798e8314f7c074a6656816c048dcc95b7a`](https://github.com/opencv/opencv_zoo/tree/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet) | MIT；Copyright (c) 2020 Shiqi Yu | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `face_recognition_sface_2021dec.onnx` | SFace 人脸特征；38,696,353 bytes | [OpenCV Zoo commit `ba91a3b91d00d76e86540d4013f944bd6b514e39`](https://github.com/opencv/opencv_zoo/tree/ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface) | Apache-2.0 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| `object_detection_nanodet_2022nov.onnx` | NanoDet 常见物品检测；3,800,954 bytes | [OpenCV Zoo commit `510899a2a0adb8c25957915fd030d66dbd553919`](https://github.com/opencv/opencv_zoo/tree/510899a2a0adb8c25957915fd030d66dbd553919/models/object_detection_nanodet) | Apache-2.0 | `4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186` |
| `palm_detection_mediapipe_2023feb.onnx` | 手掌检测；3,905,734 bytes | [OpenCV Zoo commit `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5`](https://github.com/opencv/opencv_zoo/tree/8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5/models/palm_detection_mediapipe) | Apache-2.0 | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` |
| `handpose_estimation_mediapipe_2023feb.onnx` | 每手 21 点手部姿态估计；4,099,621 bytes | [OpenCV Zoo commit `56cef36ae45e5a6da7eba01a91631f6d7e955da1`](https://github.com/opencv/opencv_zoo/tree/56cef36ae45e5a6da7eba01a91631f6d7e955da1/models/handpose_estimation_mediapipe) | Apache-2.0 | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` |

五个模型现由 `sbom/components.toml` 的机器可读资产清单及 CycloneDX SBOM 验证器管理；名称、版本、打包路径、大小、SHA-256、不可变来源和许可缺一即失败。`build.ps1` 会将整个 `assets` 目录纳入 Windows 安装包，因此五个已验证模型会沿现有打包路径列入成品与 SBOM。未来 theme／outfit pack 如含第三方素材，也必须在 package manifest 提供相同字段并纳入 SBOM；来源或许可不明的素材不得进入正式打包。

换装包可以包含多套服装、配色和配件，但只能提供 `garment`、`accessory`、`occlusion` 资产，并以获准的 ID 和 SHA-256 引用官方受保护 `core_body_skin`。套件不得提供或覆盖 identity、face、skin tone、body shape 或核心肤色本体。颈、肩、手臂等露肤区域只能由官方本体通过可见／遮挡蒙版呈现。现实服装照片只能登记为 `design-reference-only`，默认不可再分发且不得打包；交付素材必须标明为具有再分发权的原创衍生设计。

### Preview 封装工具

Linux x86_64 功能受限 Preview 使用官方 [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) 组装。构建流程会下载上游 `continuous` x86_64 资产，但只有在其 SHA-256 等于 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` 时才接受。所记录的上游源 commit 为 `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`，GitHub 资产 ID 为 `324406882`。

`appimagetool` 仍受其自身的上游许可条款约束。

### 封装所含运行时组件

Windows 单一目录安装包也可能包含 Python（PSF License）、Qt 及 Shiboken（LGPL／GPL／商业条款）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain），以及它们所需的运行时库。macOS 与 Linux 功能受限 Preview 安装包只包含 `requirements-preview.txt` 声明的较小 Preview 依赖集合。

封装布局会将动态链接的 Qt／PySide 库保留为 `_internal` 下的独立文件，让接收者可以检查或替换这些库。对应的 Qt for Python 源代码 Release 可从 [Qt 官方下载存档](https://download.qt.io/official_releases/QtForPython/)取得。

完整许可文本及源代码链接可在各上游项目与已安装软件包的元数据中取得。分发者应检查实际交付的精确依赖版本，并保留所有上游著作权及许可声明。

### Windows 安装程序语言文件

随附的 `installer/languages/ChineseTraditional.isl` 是来自 [Inno Setup 源代码仓库](https://github.com/jrsoftware/issrc)的官方繁体中文消息翻译，固定于源 commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）。该文件依 [Inno Setup 许可](https://jrsoftware.org/files/is/license.txt)分发，并保留文件头中的上游翻译者信息。

### 服务与商标

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE 及其他服务名称均为其各自权利人的商标。API 访问、云端生成语音、OAuth 使用及服务配额均受各提供商自身条款约束。

OpenAI Responses API 由 Python 标准库 `urllib.request` 通过 HTTPS 直接访问；墨寒没有 `openai` Python SDK 运行时依赖。OpenAI 是用户自行授权的外部服务，不是随安装包分发的组件，因此不会在 CycloneDX 组件清单中虚构 SDK 版本或许可；`sbom/components.toml` 另以机器可读外部服务策略记录此边界。

## English

### Overview

MoHan Desktop Assistant is MIT licensed, but its source and Release packages use third-party components under their own license terms. Nothing in the MoHan MIT License in `LICENSE` changes those third-party terms.

### Direct Python dependencies

| Component | Current pinned version | License |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License (Microsoft Speech SDK terms) |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |
| [cryptography](https://cryptography.io/) | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| [NumPy](https://numpy.org/) | 2.5.2 | BSD-3-Clause |
| [OpenCV Python](https://pypi.org/project/opencv-python/) | 5.0.0.93 | Apache-2.0 |

### Build-only toolchain

The following components are used only to build, check, or package MoHan; they are not Python runtime dependencies. The v4.0.0 formal Windows package must contain the first-party, MIT-licensed `_mohan_accel` module compiled by this toolchain, but users do not need Rust, Maturin, or PyO3 installed at runtime; CI verifies the packaged module and evidence item by item after the build.

| Component | Pinned version | License | Purpose |
| --- | ---: | --- | --- |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception | Windows／Preview packaging |
| [Rust compiler and standard library](https://www.rust-lang.org/) | 1.97.1 | MIT OR Apache-2.0 | Compile and check the first-party native module |
| [Maturin](https://github.com/PyO3/maturin) | 1.14.1 | MIT OR Apache-2.0 | Build and validate the Python wheel |
| [PyO3](https://github.com/PyO3/pyo3) | 0.29.2 | MIT OR Apache-2.0 | Build-time Rust／Python bindings |
| [Rayon](https://github.com/rayon-rs/rayon) | 1.12.0 | MIT OR Apache-2.0 | Compiled into the first-party native module; conditionally enables parallel RGBA processing at 262,144 pixels when the runtime has multiple worker threads |
| [BiRefNet HR Matting](https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting) | `5d6b6f8adcb5b417c871b1d84ceaae9871355b7f` | MIT | High-resolution human matting for the local art-production workflow only; model weights, inference environment, and cache are not MoHan runtime components and are not distributed in installers |
| [InstantMesh (official TencentARC implementation)](https://github.com/TencentARC/InstantMesh) | `08822c52fdc399b93ea00e4fa9e596344ed52ccc` | Apache-2.0 | Source retained only as license and provenance evidence; the complete inference pipeline is disabled, and its weights, environment, and cache must not enter the formal 24/600 pipeline, MoHan runtime, or installers |

`native-wheels/` and `native-wheels-<id>/` store only local or CI build outputs and evidence. Git ignores them, and they are not Release assets. macOS／Linux currently build the module and run equivalence and performance tests only in core CI; equivalent Preview packaging is not claimed. Rayon 1.12.0 Rust serial／Rayon boundary tests and Python／native measurements provide equivalence and performance evidence. PyO3 `PyBackedBytes` borrows inputs and avoids an additional input copy; outputs still allocate new Python `bytes`, so end-to-end zero-copy is not claimed. There is no SIMD implementation evidence, so SIMD is not claimed.

BiRefNet uses the official `ZhengPeng7/BiRefNet_HR-matting` source and weights pinned to the immutable revision above; both are used under the MIT License. The complete license text is preserved at `third_party_licenses/BiRefNet-LICENSE.txt`, and the local art-tooling inventory is recorded in `sbom/local-art-tooling-components.toml`. This project does not use or redistribute BRIA／RMBG-2.0 weights.

InstantMesh source from the official TencentARC repository is pinned to the immutable commit above and retained only as license and provenance evidence. At that revision upstream provides an Apache 2.0 `LICENSE` but no separate `NOTICE` or named copyright header; this notice therefore does not invent a copyright holder. It preserves the license verbatim at `third_party_licenses/InstantMesh-LICENSE.txt`. Official paper attribution: *InstantMesh: Efficient 3D Mesh Generation from a Single Image with Sparse-view Large Reconstruction Models* by Jiale Xu, Weihao Cheng, Yiming Gao, Xintao Wang, Shenghua Gao, and Ying Shan, arXiv:2404.07191 (2024). Because the complete pipeline depends on permanently denied `nvdiffrast` and Zero123++ weights without sufficient license evidence, it must not be downloaded, built, loaded, or used for the formal 24/600 pipeline.

### v4.0.0 local vision models

### Bundled Face Mesh, iris, and voice-activity models

Face Mesh, iris, and Silero VAD are bundled in the formal Windows package and loaded locally through OpenCV 5 DNN. Their files, licenses, sources, sizes, and SHA-256 values are recorded in `sbom/components.toml` and `docs/MULTIMODAL-MODEL-PROVENANCE.json`. The formal Windows packaging contract requires model hashes to be verified before the build; if a model or runtime engine is unavailable, existing vision, speech, and 2.5D behavior falls back safely to its established path.

| Model file | Purpose | Source and license | SHA-256 |
| --- | --- | --- | --- |
| `face_landmark_468.tflite` | MediaPipe Face Mesh with 468 points | [Official MediaPipe asset](https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite); Apache-2.0 | `1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814` |
| `iris_landmark.tflite` | Five iris points per eye | [Official MediaPipe asset](https://storage.googleapis.com/mediapipe-assets/iris_landmark.tflite); Apache-2.0 | `d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f` |
| `silero_vad_v4.0.onnx` | Voice activity detection at 16 kHz | [Silero VAD v4.0](https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx); MIT | `a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28` |

The following ONNX models reside under `assets/vision-models/` and are used only by the explicitly enabled local-vision feature. All five were retrieved from official Git LFS media at the immutable OpenCV Zoo commits shown below and verified against the official LFS pointers, exact byte sizes, local files, and SHA-256 values. The official LICENSE and README in each model directory were also checked at the same commit. Complete machine-readable evidence is in `docs/VISION-MODEL-PROVENANCE.json` and `docs/HAND-MODEL-PROVENANCE.json`; the moving `main` branch is not used as a source revision.

| Model file | Purpose | Official source | Model-specific license | SHA-256 |
| --- | --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | YuNet face detection; 232,589 bytes | [OpenCV Zoo commit `f12e12798e8314f7c074a6656816c048dcc95b7a`](https://github.com/opencv/opencv_zoo/tree/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet) | MIT; Copyright (c) 2020 Shiqi Yu | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `face_recognition_sface_2021dec.onnx` | SFace facial features; 38,696,353 bytes | [OpenCV Zoo commit `ba91a3b91d00d76e86540d4013f944bd6b514e39`](https://github.com/opencv/opencv_zoo/tree/ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface) | Apache-2.0 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| `object_detection_nanodet_2022nov.onnx` | NanoDet common-object detection; 3,800,954 bytes | [OpenCV Zoo commit `510899a2a0adb8c25957915fd030d66dbd553919`](https://github.com/opencv/opencv_zoo/tree/510899a2a0adb8c25957915fd030d66dbd553919/models/object_detection_nanodet) | Apache-2.0 | `4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186` |
| `palm_detection_mediapipe_2023feb.onnx` | Palm detection; 3,905,734 bytes | [OpenCV Zoo commit `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5`](https://github.com/opencv/opencv_zoo/tree/8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5/models/palm_detection_mediapipe) | Apache-2.0 | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` |
| `handpose_estimation_mediapipe_2023feb.onnx` | 21-point hand-pose estimation per hand; 4,099,621 bytes | [OpenCV Zoo commit `56cef36ae45e5a6da7eba01a91631f6d7e955da1`](https://github.com/opencv/opencv_zoo/tree/56cef36ae45e5a6da7eba01a91631f6d7e955da1/models/handpose_estimation_mediapipe) | Apache-2.0 | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` |

The five models are governed by the machine-readable asset inventory in `sbom/components.toml` and the CycloneDX SBOM validator; name, version, package path, byte size, SHA-256, immutable source, and license are all mandatory. `build.ps1` packages the complete `assets` directory into the Windows distribution, so all five verified models enter the product and its SBOM through the established package path. Any future theme or outfit pack containing third-party material must expose the same fields in its package manifest and enter the SBOM. Material with unknown source or license must not enter a release package.

An outfit pack may contain multiple garments, colorways, and accessories, but may provide only `garment`, `accessory`, and `occlusion` assets while referencing the protected official `core_body_skin` by an approved ID and SHA-256. It must not provide or override identity, face, skin tone, body shape, or core skin assets. Exposed neck, shoulders, arms, or other skin must come from the official body through visibility or occlusion masks. Real-world garment photos are `design-reference-only`, non-redistributable and unpackaged by default; delivered assets must be identified as original derivative designs with redistribution rights.

### Preview packaging tool

The Linux x86_64 limited Preview is assembled with the official [AppImage `appimagetool`](https://github.com/AppImage/appimagetool). The build downloads the upstream `continuous` x86_64 asset but accepts it only when its SHA-256 equals `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`. The recorded upstream source commit is `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`, and the GitHub asset ID is `324406882`.

`appimagetool` remains governed by its own upstream license.

### Runtime components included by packaging

The Windows one-directory package may also contain Python (PSF License), Qt and Shiboken (LGPL/GPL/commercial terms), NumPy (BSD-3-Clause), CFFI (MIT), PortAudio (MIT), OpenSSL (Apache-2.0), SQLite (public domain), and their required runtime libraries. The macOS and Linux limited Preview packages contain only the smaller Preview dependency set declared in `requirements-preview.txt`.

The packaged layout keeps dynamically linked Qt/PySide libraries as separate files under `_internal`, so recipients can inspect or replace those libraries. Corresponding Qt for Python source releases are available from the [official Qt download archive](https://download.qt.io/official_releases/QtForPython/).

Complete license texts and source links are available in each upstream project and installed package metadata. Distributors should review the exact dependency versions they ship and preserve all upstream copyright and license notices.

### Windows installer language file

The bundled `installer/languages/ChineseTraditional.isl` file is the official Traditional Chinese message translation from the [Inno Setup source repository](https://github.com/jrsoftware/issrc), pinned to source commit `0c0b463621963243e430420b6c633039e562e1e3` (blob `8eb13d2c45e9d434aa5435a2877234418186ad87`). It is distributed under the [Inno Setup license](https://jrsoftware.org/files/is/license.txt) and retains its upstream translator credits in the file header.

### Services and trademarks

OpenAI, Microsoft, Google, GitHub, Home Assistant, LINE, and other service names are trademarks of their respective owners. API access, cloud-generated voices, OAuth use, and service quotas are governed by each provider's own terms.

The OpenAI Responses API is accessed directly over HTTPS through Python's standard-library `urllib.request`; MoHan has no `openai` Python SDK runtime dependency. OpenAI is a user-authorized external service, not a component distributed in the installer, so the CycloneDX component inventory does not invent an SDK version or license. `sbom/components.toml` records this boundary through a separate machine-readable external-service policy.

## 日本語

### 概要

MoHan Desktop Assistant は MIT License で提供されますが、そのソースコードと Release パッケージは、独自のライセンス条件を持つ第三者コンポーネントを使用します。`LICENSE` に記載された墨寒の MIT License が、それらの第三者条件を変更することはありません。

### Python の直接依存パッケージ

| コンポーネント | 現在の固定バージョン | ライセンス |
| --- | ---: | --- |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| [Microsoft Azure Cognitive Services Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) | 1.50.0 | Other/Proprietary License（Microsoft Speech SDK 条件） |
| [python-sounddevice](https://python-sounddevice.readthedocs.io/) | 0.5.5 | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | 1.9.0 | Apache-2.0 |
| [OpenCC Python reimplementation](https://github.com/yichen0831/opencc-python) | 0.1.7 | Apache-2.0 |
| [cryptography](https://cryptography.io/) | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| [NumPy](https://numpy.org/) | 2.5.2 | BSD-3-Clause |
| [OpenCV Python](https://pypi.org/project/opencv-python/) | 5.0.0.93 | Apache-2.0 |

### ビルド専用ツールチェーン

次のコンポーネントはビルド、検査、パッケージ化だけに使用し、墨寒の Python 実行時依存ではありません。v4.0.0 Windows 正式パッケージには、このツールチェーンでコンパイルした第一者 MIT ライセンスの `_mohan_accel` モジュールを必ず含めますが、利用者が実行時に Rust、Maturin、PyO3 をインストールする必要はありません。ビルド後、CI がパッケージ内モジュールと証拠を項目別に検証します。

| コンポーネント | 固定バージョン | ライセンス | 用途 |
| --- | ---: | --- | --- |
| [PyInstaller](https://pyinstaller.org/) | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception | Windows／Preview のパッケージ化 |
| [Rust コンパイラと標準ライブラリ](https://www.rust-lang.org/) | 1.97.1 | MIT OR Apache-2.0 | 第一者ネイティブモジュールのコンパイルと検査 |
| [Maturin](https://github.com/PyO3/maturin) | 1.14.1 | MIT OR Apache-2.0 | Python wheel のビルドと検証 |
| [PyO3](https://github.com/PyO3/pyo3) | 0.29.2 | MIT OR Apache-2.0 | Rust／Python 境界のビルド時バインディング |
| [Rayon](https://github.com/rayon-rs/rayon) | 1.12.0 | MIT OR Apache-2.0 | 第一者ネイティブモジュールへコンパイルされ、RGBA が 262,144 pixels 以上かつ実行環境に複数のワーカースレッドがある場合に条件付きで並列処理を有効化 |
| [BiRefNet HR Matting](https://huggingface.co/ZhengPeng7/BiRefNet_HR-matting) | `5d6b6f8adcb5b417c871b1d84ceaae9871355b7f` | MIT | ローカルのアート制作工程における高解像度人物切り抜き専用。モデル重み、推論環境、キャッシュは墨寒のランタイム構成要素ではなく、インストーラーにも同梱しません |
| [InstantMesh（TencentARC 公式実装）](https://github.com/TencentARC/InstantMesh) | `08822c52fdc399b93ea00e4fa9e596344ed52ccc` | Apache-2.0 | ソースはライセンスと来歴の証拠としてのみ保持します。完全な推論パイプラインは無効で、重み、推論環境、キャッシュを正式な 24／600 パイプライン、墨寒ランタイム、インストーラーへ含めません |

`native-wheels/` と `native-wheels-<id>/` はローカルまたは CI のビルド生成物と証拠だけを保存します。Git の対象外であり、Release アセットにも含めません。macOS／Linux は現在、中核 CI でモジュールをビルドし、等価性および性能テストを実行するだけで、Preview の同等パッケージ対応は表明しません。Rayon 1.12.0 の Rust serial／Rayon 境界テストと Python／native 実測により、結果の等価性と性能の証拠を得ています。PyO3 `PyBackedBytes` は入力を借用して追加の入力コピーを避けますが、出力では新しい Python `bytes` を生成するため、エンドツーエンドのゼロコピーは表明しません。SIMD の実装証拠はないため、SIMD は表明しません。

BiRefNet は公式の `ZhengPeng7/BiRefNet_HR-matting` ソースコードと重みを使用し、上記の不変 revision に固定しています。両方とも MIT ライセンスに基づいて使用します。完全なライセンス本文は `third_party_licenses/BiRefNet-LICENSE.txt` に保存し、ローカル美術ツールのインベントリは `sbom/local-art-tooling-components.toml` に記録しています。本プロジェクトは BRIA／RMBG-2.0 の重みを使用または再配布しません。

InstantMesh の TencentARC 公式ソースは上記の不変 commit に固定し、ライセンスと来歴の証拠としてのみ保持します。この版の上流には Apache 2.0 `LICENSE` がありますが、独立した `NOTICE` または名義付き copyright header はありません。そのため本一覧では著作権者を創作せず、完全なライセンス本文を `third_party_licenses/InstantMesh-LICENSE.txt` に原文のまま保存します。公式論文の帰属：*InstantMesh: Efficient 3D Mesh Generation from a Single Image with Sparse-view Large Reconstruction Models*、Jiale Xu、Weihao Cheng、Yiming Gao、Xintao Wang、Shenghua Gao、Ying Shan、arXiv:2404.07191（2024）。完全なパイプラインは永久禁止の `nvdiffrast` と、十分な重みライセンス証拠がない Zero123++ に依存するため、正式な 24／600 パイプライン向けに再ダウンロード、ビルド、ロード、使用してはなりません。

### v4.0.0 のローカル視覚モデル

### 同梱する Face Mesh、虹彩、音声活動モデル

Face Mesh、虹彩、Silero VAD は正式な Windows パッケージに同梱され、OpenCV 5 DNN を通じてローカルで読み込まれます。モデル、ライセンス、出典、サイズ、SHA-256 は `sbom/components.toml` と `docs/MULTIMODAL-MODEL-PROVENANCE.json` に記録されています。Windows 正式パッケージ化の契約では、ビルド前にモデルのハッシュを検証します。モデルまたは実行エンジンを利用できない場合、既存の視覚、音声、2.5D 機能は既存の経路へ安全にフォールバックします。

| モデルファイル | 用途 | 出典とライセンス | SHA-256 |
| --- | --- | --- | --- |
| `face_landmark_468.tflite` | 468 点の MediaPipe Face Mesh | [MediaPipe 公式アセット](https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite)；Apache-2.0 | `1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814` |
| `iris_landmark.tflite` | 両目それぞれ 5 点の虹彩推定 | [MediaPipe 公式アセット](https://storage.googleapis.com/mediapipe-assets/iris_landmark.tflite)；Apache-2.0 | `d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f` |
| `silero_vad_v4.0.onnx` | 16 kHz の音声活動検出 | [Silero VAD v4.0](https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx)；MIT | `a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28` |

次の ONNX モデルは `assets/vision-models/` にあり、利用者が明示的に有効化したローカル視覚機能だけで使用します。5 モデルすべてを表に示す不変 OpenCV Zoo commit の公式 Git LFS 実体から取得し、公式 LFS pointer、正確な byte size、ローカルファイル、SHA-256 を照合しました。各モデルディレクトリの公式 LICENSE／README も同一 commit で確認済みです。完全な機械可読証拠は `docs/VISION-MODEL-PROVENANCE.json` と `docs/HAND-MODEL-PROVENANCE.json` にあり、移動する `main` ブランチを取得元 revision として使用しません。

| モデルファイル | 用途 | 公式取得元 | モデル固有ライセンス | SHA-256 |
| --- | --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | YuNet 顔検出；232,589 bytes | [OpenCV Zoo commit `f12e12798e8314f7c074a6656816c048dcc95b7a`](https://github.com/opencv/opencv_zoo/tree/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet) | MIT；Copyright (c) 2020 Shiqi Yu | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `face_recognition_sface_2021dec.onnx` | SFace 顔特徴；38,696,353 bytes | [OpenCV Zoo commit `ba91a3b91d00d76e86540d4013f944bd6b514e39`](https://github.com/opencv/opencv_zoo/tree/ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface) | Apache-2.0 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| `object_detection_nanodet_2022nov.onnx` | NanoDet 一般物体検出；3,800,954 bytes | [OpenCV Zoo commit `510899a2a0adb8c25957915fd030d66dbd553919`](https://github.com/opencv/opencv_zoo/tree/510899a2a0adb8c25957915fd030d66dbd553919/models/object_detection_nanodet) | Apache-2.0 | `4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186` |
| `palm_detection_mediapipe_2023feb.onnx` | 手掌検出；3,905,734 bytes | [OpenCV Zoo commit `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5`](https://github.com/opencv/opencv_zoo/tree/8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5/models/palm_detection_mediapipe) | Apache-2.0 | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` |
| `handpose_estimation_mediapipe_2023feb.onnx` | 片手 21 点の手部姿勢推定；4,099,621 bytes | [OpenCV Zoo commit `56cef36ae45e5a6da7eba01a91631f6d7e955da1`](https://github.com/opencv/opencv_zoo/tree/56cef36ae45e5a6da7eba01a91631f6d7e955da1/models/handpose_estimation_mediapipe) | Apache-2.0 | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` |

5 つのモデルは `sbom/components.toml` の機械可読アセット一覧と CycloneDX SBOM 検証器で管理され、名称、バージョン、パッケージ内パス、byte size、SHA-256、不変の取得元、ライセンスの全項目を必須とします。`build.ps1` は `assets` ディレクトリ全体を Windows パッケージへ収録するため、検証済みの全 5 モデルは既存のパッケージ経路で製品と SBOM に含まれます。将来の theme／outfit pack に第三者素材が含まれる場合も、package manifest に同じ項目を記載して SBOM に含めます。取得元またはライセンスが不明な素材は正式パッケージへ入れません。

衣装パックには複数の衣装、配色、アクセサリーを含められますが、提供できる資産は `garment`、`accessory`、`occlusion` のみです。保護された公式 `core_body_skin` は承認済み ID と SHA-256 で参照します。identity、face、skin tone、body shape、または肌本体を提供・上書きしてはなりません。首、肩、腕などの露出肌は、公式本体を可視／遮蔽マスクで参照して表示します。現実の服装写真は `design-reference-only` として記録し、既定で再配布不可かつパッケージ非同梱とします。配布資産は再配布権を持つオリジナル派生デザインでなければなりません。

### Preview パッケージ作成ツール

Linux x86_64 の機能制限付き Preview は、公式の [AppImage `appimagetool`](https://github.com/AppImage/appimagetool) で組み立てられます。ビルドは上流の `continuous` x86_64 アセットをダウンロードしますが、その SHA-256 が `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` と一致する場合にのみ受け入れます。記録されている上流ソースの commit は `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`、GitHub アセット ID は `324406882` です。

`appimagetool` には、引き続き上流独自のライセンスが適用されます。

### パッケージに含まれるランタイムコンポーネント

Windows のワンディレクトリパッケージには、Python（PSF License）、Qt および Shiboken（LGPL／GPL／商用条件）、NumPy（BSD-3-Clause）、CFFI（MIT）、PortAudio（MIT）、OpenSSL（Apache-2.0）、SQLite（public domain）、ならびにそれらに必要なランタイムライブラリが含まれる場合があります。macOS および Linux の機能制限付き Preview パッケージには、`requirements-preview.txt` で宣言された小規模な Preview 依存セットだけが含まれます。

パッケージでは、動的リンクされる Qt／PySide ライブラリを `_internal` 配下の個別ファイルとして保持するため、受領者はこれらのライブラリを確認または置換できます。対応する Qt for Python のソース Release は、[Qt 公式ダウンロードアーカイブ](https://download.qt.io/official_releases/QtForPython/)から取得できます。

完全なライセンス本文とソースへのリンクは、各上流プロジェクトおよびインストール済みパッケージのメタデータで確認できます。配布者は、実際に出荷する正確な依存バージョンを確認し、上流の著作権表示とライセンス表示をすべて保持してください。

### Windows インストーラーの言語ファイル

同梱の `installer/languages/ChineseTraditional.isl` は、[Inno Setup ソースリポジトリ](https://github.com/jrsoftware/issrc)による公式の繁体字中国語メッセージ翻訳であり、ソース commit `0c0b463621963243e430420b6c633039e562e1e3`（blob `8eb13d2c45e9d434aa5435a2877234418186ad87`）に固定されています。このファイルは [Inno Setup ライセンス](https://jrsoftware.org/files/is/license.txt)に基づいて配布され、ファイルヘッダーにある上流翻訳者のクレジットを保持します。

### サービスと商標

OpenAI、Microsoft、Google、GitHub、Home Assistant、LINE、およびその他のサービス名は、それぞれの権利者の商標です。API アクセス、クラウド生成音声、OAuth の使用、サービス利用枠には、各プロバイダー独自の規約が適用されます。

OpenAI Responses API は Python 標準ライブラリの `urllib.request` から HTTPS で直接アクセスします。墨寒に `openai` Python SDK の実行時依存はありません。OpenAI は利用者が自ら許可する外部サービスであり、インストーラーで配布するコンポーネントではないため、CycloneDX コンポーネント一覧に SDK のバージョンやライセンスを架空登録しません。`sbom/components.toml` は、別の機械可読な外部サービスポリシーとしてこの境界を記録します。
