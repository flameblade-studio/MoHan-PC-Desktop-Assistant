# 手部模型來源與發布門檻／手部模型来源与发布门槛／Hand-model provenance and release gates／手モデルの出典と公開ゲート

## 繁體中文

本文件固定墨寒手部關鍵點功能所採用的兩個 OpenCV Zoo FP32 ONNX 模型來源。來源紀錄通過的證據範圍是檔名、上游版本、Git LFS 物件、大小與授權證據完整；模型下載、載入、推論及 Windows EXE 實機驗證各自保留獨立門檻。

### 固定來源

| 模型 | OpenCV Zoo 固定 commit | Git LFS／實際檔 SHA-256 | 精確大小 |
|---|---|---|---:|
| `palm_detection_mediapipe_2023feb.onnx` | `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5` | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` | 3,905,734 bytes |
| `handpose_estimation_mediapipe_2023feb.onnx` | `56cef36ae45e5a6da7eba01a91631f6d7e955da1` | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` | 4,099,621 bytes |

Git LFS 指標中的 `oid sha256` 是實際大檔物件內容的 SHA-256，對應實際大檔物件內容，並與小型 pointer 檔雜湊分開。取得資產後，發布門檻必須重新計算實際 ONNX 檔的 SHA-256 與位元組大小；兩者完全相符才可封裝。

### 授權證據

兩個模型各自的 OpenCV Zoo 模型目錄 README 均明確表示該目錄全部檔案採 Apache License 2.0，且各目錄都附有完整 Apache-2.0 `LICENSE`。重新散布時必須保留授權與必要歸屬；本文件不是法律意見。

### 分離門檻

1. **來源契約門檻：** 文件中的 commit、路徑、LFS SHA-256、大小、授權 URL 必須完整且不可變。
2. **實際資產門檻：** `assets/vision-models/` 中兩個實際 ONNX 必須存在，必須是實際 ONNX 二進位檔，且大小與 SHA-256 必須完全符合。
3. **執行門檻：** 接著以兩個真實 ONNX 驗證 OpenCV 載入、真實影像推論、左右手、鏡像、21 點輸出及封裝後執行。執行通過證明由本門檻的實測結果成立。

### 規範機器可讀證據

固定欄位的唯一權威機器來源是 [手部模型來源 JSON](HAND-MODEL-PROVENANCE.json)。自動化、SBOM 稽核與封裝門檻統一讀取該 JSON，Markdown 表格維持人類可讀翻譯，機器資料維持單一來源。

本 Markdown 是 JSON 內容與門檻意義的完整繁體中文人類可讀翻譯，其角色是人類可讀翻譯。測試必須持續核對翻譯所呈現的模型、commit、SHA-256、大小與授權關係，避免人類文件與唯一 JSON 證據產生漂移；發生差異時以 JSON 為機器判定依據，並修正文案。

## 简体中文

本文档固定墨寒手部关键点功能所采用的两个 OpenCV Zoo FP32 ONNX 模型来源。来源记录通过的证据范围是文件名、上游版本、Git LFS 对象、大小和许可证据完整；模型下载、加载、推理及 Windows EXE 真机验证各自保留独立关卡。

### 固定来源

| 模型 | OpenCV Zoo 固定 commit | Git LFS／实际文件 SHA-256 | 精确大小 |
|---|---|---|---:|
| `palm_detection_mediapipe_2023feb.onnx` | `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5` | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` | 3,905,734 bytes |
| `handpose_estimation_mediapipe_2023feb.onnx` | `56cef36ae45e5a6da7eba01a91631f6d7e955da1` | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` | 4,099,621 bytes |

Git LFS 指针中的 `oid sha256` 是实际大文件对象内容的 SHA-256，对应实际大文件对象内容，并与小型 pointer 文件哈希分开。取得资源后，发布门槛必须重新计算实际 ONNX 文件的 SHA-256 和字节大小；两者完全相符才可打包。

### 许可依据

两个模型各自的 OpenCV Zoo 模型目录 README 都明确说明该目录全部文件采用 Apache License 2.0，而且各目录都附有完整 Apache-2.0 `LICENSE`。重新分发时必须保留许可证和必要归属；本文档不是法律意见。

### 分离门槛

1. **来源契约门槛：** 文档中的 commit、路径、LFS SHA-256、大小和许可 URL 必须完整且不可变。
2. **实际资源门槛：** `assets/vision-models/` 中两个实际 ONNX 必须存在，必须是实际 ONNX 二进制文件，而且大小和 SHA-256 必须完全符合。
3. **运行门槛：** 仍须使用两个真实 ONNX 验证 OpenCV 加载、真实图像推理、左右手、镜像、21 点输出及打包后运行。本文档和来源测试不构成运行通过证明。

### 规范机器可读证据

固定字段的唯一权威机器来源是 [手部模型来源 JSON](HAND-MODEL-PROVENANCE.json)。自动化、SBOM 审计与打包关卡统一读取该 JSON；Markdown 表格保持人类可读翻译，机器数据保持单一来源。

本 Markdown 是 JSON 内容与关卡含义的完整简体中文人类可读翻译，其角色是人类可读翻译。测试必须持续核对翻译所呈现的模型、commit、SHA-256、大小与许可关系，避免人类文档与唯一 JSON 证据发生偏移；出现差异时以 JSON 作为机器判断依据，并修正文案。

## English

This document pins the two OpenCV Zoo FP32 ONNX models used by MoHan hand landmarks. Passing the provenance record establishes complete filenames, upstream revisions, Git LFS objects, sizes, and license evidence. Model download, loading, inference, and a real Windows EXE test retain separate gates.

### Immutable sources

| Model | Immutable OpenCV Zoo commit | Git LFS / actual-file SHA-256 | Exact size |
|---|---|---|---:|
| `palm_detection_mediapipe_2023feb.onnx` | `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5` | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` | 3,905,734 bytes |
| `handpose_estimation_mediapipe_2023feb.onnx` | `56cef36ae45e5a6da7eba01a91631f6d7e955da1` | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` | 4,099,621 bytes |

The `oid sha256` in a Git LFS pointer is the SHA-256 of the actual large-file object, not the hash of the small pointer file. After acquiring an asset, the release gate must recompute the real ONNX file SHA-256 and byte size. Packaging is permitted only when both values match exactly.

### License evidence

The README in each OpenCV Zoo model directory expressly states that every file in that directory is licensed under Apache License 2.0, and each directory contains the complete Apache-2.0 `LICENSE`. Redistribution must preserve the license and required attribution. This document is not legal advice.

### Separate gates

1. **Provenance-contract gate:** every commit, path, LFS SHA-256, size, and license URL in this document must be complete and immutable.
2. **Actual-asset gate:** both real ONNX files must exist under `assets/vision-models/`, must be actual ONNX binaries, and must exactly match the recorded sizes and SHA-256 values.
3. **Runtime gate:** both real ONNX files must still pass OpenCV loading, real-image inference, left/right hand, mirroring, 21-landmark output, and packaged execution tests. Neither this document nor the provenance tests prove runtime success.

### Canonical machine-readable evidence

The [hand-model provenance JSON](HAND-MODEL-PROVENANCE.json) is the sole authoritative machine source for immutable fields. Automation, SBOM audits, and packaging gates read that JSON uniformly; the Markdown tables remain human-readable translations and machine data keeps one authoritative source.

This Markdown is the complete human-readable English translation of the JSON content and the meaning of its gates, serves as the human-readable translation. Tests must continue checking the models, commits, SHA-256 values, sizes, and licensing relationships presented by the translation so the human document stays aligned with the sole JSON evidence. If a difference occurs, the JSON governs machine decisions and the prose must be corrected.

## 日本語

本書は、墨寒の手ランドマーク機能で使用する二つの OpenCV Zoo FP32 ONNX モデルの出典を固定します。出典記録の合格は、ファイル名、上流 revision、Git LFS オブジェクト、サイズ、ライセンス証拠の完全性を示します。モデルの取得、読み込み、推論精度、実際の Windows EXE 検証はそれぞれ独立したゲートです。

### 固定した出典

| モデル | OpenCV Zoo の固定 commit | Git LFS／実ファイル SHA-256 | 正確なサイズ |
|---|---|---|---:|
| `palm_detection_mediapipe_2023feb.onnx` | `8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5` | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` | 3,905,734 bytes |
| `handpose_estimation_mediapipe_2023feb.onnx` | `56cef36ae45e5a6da7eba01a91631f6d7e955da1` | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` | 4,099,621 bytes |

Git LFS pointer の `oid sha256` は、小さな pointer ファイルではなく実際の大容量オブジェクト内容の SHA-256 です。資産取得後、リリースゲートで実際の ONNX ファイルの SHA-256 とバイト数を再計算し、両方が完全一致した場合だけパッケージ化できます。

### ライセンス証拠

各 OpenCV Zoo モデルディレクトリの README は、そのディレクトリ内の全ファイルが Apache License 2.0 であることを明記し、各ディレクトリには完全な Apache-2.0 `LICENSE` があります。再配布時はライセンスと必要な帰属表示を保持しなければなりません。本書は法律上の助言ではありません。

### 分離したゲート

1. **出典契約ゲート：** 本書の commit、パス、LFS SHA-256、サイズ、ライセンス URL が完全かつ不変でなければなりません。
2. **実資産ゲート：** `assets/vision-models/` に実際の ONNX 二ファイルが存在し、実際の ONNX バイナリとしてサイズと SHA-256 が記録と完全一致することを求めます。
3. **実行ゲート：** 二つの実 ONNX を用いた OpenCV 読み込み、実画像推論、左右の手、鏡像、21 点出力、パッケージ後の実行検証を完了すると実行合格証拠が成立します。

### 標準機械可読証拠

固定フィールドに対する唯一の権威ある機械情報源は [手モデル出典 JSON](HAND-MODEL-PROVENANCE.json) です。自動処理、SBOM 監査、パッケージ化ゲートはこの JSON を統一して読み、Markdown 表は人間向け翻訳、機械データは単一の正規情報源として維持します。

この Markdown は JSON の内容と各ゲートの意味を完全に説明する日本語の人間向け翻訳であり、人間向け翻訳として機能します。翻訳に示すモデル、commit、SHA-256、サイズ、ライセンス関係をテストで継続的に照合し、人間向け文書と唯一の JSON 証拠とのずれを防ぎます。差異が生じた場合、機械判定には JSON を用い、文章を修正します。
