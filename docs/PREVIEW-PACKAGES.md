# macOS 與 Linux 功能受限預覽包／macOS 与 Linux 功能受限预览包／Limited macOS and Linux Preview packages／macOS・Linux 機能限定 Preview パッケージ

## 繁體中文

### 這些安裝檔是什麼

`v2.3.0-rc.N` 發行線會分別在 GitHub 原生 Apple Silicon（arm64）與 Intel
（x86_64）macOS runner 製作 `.dmg`，其中包含相符架構的 `.app`；Linux
x86_64 runner 則製作 `.AppImage`。三個流程都會先建立封裝，
再從成品執行無畫面啟動測試，確認四語畫面與安全邊界能載入。Pull Request
只保存短期測試產物；只有已存在且符合 `v2.3.0-rc.N` 的標籤才會發布到
GitHub Releases。

### 目前可以驗證的範圍

- 原生格式安裝檔能由 CI 建立並啟動。
- 介面可切換臺灣繁中、簡體中文、英文、日文。
- macOS 與 Linux 使用各自正確的使用者資料路徑。
- API 金鑰、OAuth、Home Assistant 權杖、系統工具、語音與自動啟動等尚未
  實機驗證的能力不會出現在輸入介面，也不會退回不安全的明文保存。

### 目前不能代表的事

CI 不是作者持有真實 Mac 或 Linux 桌面電腦的證明。此 Preview 不是完整墨寒，
也不承諾與 Windows 版功能相同。透明桌面角色、完整聊天與工作介面、麥克風、
喇叭、系統本機女聲、雲端連接器、原生安全金鑰保存及系統整合，必須由實機
使用者回報並通過後續驗證，才會逐項開放。

目前沒有 Apple Developer ID 簽署或公證。macOS 若阻擋首次開啟，請只在確認
檔案來自本專案 GitHub Release、SHA256 與 Artifact Attestation 均正確後，
使用 Finder 的「打開」明確核准；不要停用整體 Gatekeeper。

### 供應鏈與驗證

- Python、PySide6 與 PyInstaller 版本固定於需求檔。
- GitHub Actions 一律固定到完整提交 SHA。
- macOS 使用 runner 內建的 `sips`、`iconutil`、`hdiutil`。
- Linux 使用 AppImage 官方倉庫的 `appimagetool`；來源提交、資產 ID 與
  SHA-256 同時固定，雜湊不符便停止封裝。
- Release 同時產生 SHA256SUMS、Windows／Preview CycloneDX SBOM 與 GitHub Artifact
  Attestation。
- DMG 根目錄、app 資源與 AppImage 文件目錄都包含 MIT `LICENSE` 與第三方
  套件聲明；成品 smoke test 會檢查這些文件可讀。

## 简体中文

### 这些安装文件是什么

`v2.3.0-rc.N` 发布线会分别在 GitHub 原生 Apple Silicon（arm64）与 Intel
（x86_64）macOS runner 生成 `.dmg`（内含对应架构的 `.app`），并在 Linux
x86_64 runner 生成 `.AppImage`。三个流程都会从完成的
安装包执行无画面启动测试，检查四语界面与安全边界。Pull Request 仅保存短期
测试产物；只有已经存在并符合 `v2.3.0-rc.N` 的标签才能发布到 Releases。

### 当前验证范围

- CI 能生成并启动原生格式安装包。
- 界面可切换繁中、简中、英文、日文。
- macOS 与 Linux 使用各自正确的用户数据路径。
- API 密钥、OAuth、Home Assistant 令牌、系统工具、语音与自动启动等未经
  真机验证的能力不会出现输入框，也不会退回不安全的明文保存。

### 当前不能代表的内容

CI 并不表示作者已经拥有并实测真实 Mac 或 Linux 桌面电脑。此 Preview 不是
完整墨寒，也不承诺与 Windows 版本功能相同。透明桌面角色、完整聊天与工作
界面、麦克风、扬声器、本机女性语音、云端连接器、安全密钥保存与系统集成，
必须经过真实设备回报及后续验证后才会逐项开放。

目前尚无 Apple Developer ID 签名或公证。若 macOS 阻止首次打开，请只在确认
文件来自本项目 GitHub Release，且 SHA256 与 Artifact Attestation 均正确后，
通过 Finder 的“打开”明确批准；不要关闭系统整体 Gatekeeper。

### 供应链与验证

- 固定 Python、PySide6 与 PyInstaller 版本。
- GitHub Actions 固定到完整提交 SHA。
- macOS 只使用 runner 内置的 `sips`、`iconutil`、`hdiutil`。
- Linux 的官方 `appimagetool` 同时固定来源提交、资产 ID 与 SHA-256。
- Release 生成 SHA256SUMS、Windows／Preview CycloneDX SBOM 与 Artifact Attestation。
- DMG 根目录、app 资源与 AppImage 文档目录均包含 MIT `LICENSE` 和第三方
  组件声明；成品 smoke test 会检查这些文件可读。

## English

### What these packages are

The `v2.3.0-rc.N` line builds separate `.dmg` files on native GitHub Apple
Silicon (arm64) and Intel (x86_64) macOS runners, each containing a matching
`.app`, plus an `.AppImage` on a Linux x86_64 runner. Each job executes a
headless smoke test from the finished package and checks all four UI languages
and fail-closed boundaries. Pull requests retain short-lived test artifacts;
only an existing tag matching `v2.3.0-rc.N` may publish a GitHub Release.

### What is verified now

- CI creates and launches the native-format package.
- The UI switches among Taiwan Traditional Chinese, Simplified Chinese,
  English, and Japanese.
- macOS and Linux select their correct per-user data paths.
- Unverified capabilities—including API-key entry, OAuth, Home Assistant
  tokens, system tools, voice, and autostart—are absent and cannot fall back to
  plaintext secret storage.

### What this does not prove

CI is not evidence that the maintainer owns or has tested a physical Mac or
Linux desktop. This Preview is not the complete MoHan application and does not
claim Windows feature parity. The transparent character, complete chat and
productivity UI, microphone, speakers, local female voices, cloud connectors,
native secure storage, and OS integrations remain disabled until real-device
reports and follow-up validation support enabling them.

The Preview is not signed or notarized with an Apple Developer ID. If macOS
blocks first launch, use Finder's explicit Open action only after verifying the
GitHub Release source, SHA256, and Artifact Attestation. Do not disable
Gatekeeper globally.

### Supply-chain controls

- Python, PySide6, and PyInstaller are version-pinned.
- Every GitHub Action is pinned to a complete commit SHA.
- macOS uses only runner-native `sips`, `iconutil`, and `hdiutil` tools.
- Linux `appimagetool` is tied to an official source commit, immutable asset ID,
  and expected SHA-256; a mismatch stops the build.
- Releases include SHA256SUMS, separate Windows/Preview CycloneDX SBOMs, and GitHub Artifact
  Attestations.
- The DMG root, app resources, and AppImage documentation path contain the MIT
  `LICENSE` and third-party notices; finished-package smoke tests require them.

## 日本語

### この配布物について

`v2.3.0-rc.N` 系列では、GitHub の Apple Silicon（arm64）版と Intel
（x86_64）版 macOS ネイティブ runner で、個別の `.dmg`（対応する `.app`
を同梱）を作成し、Linux x86_64 runner で `.AppImage` を作成します。完成した
配布物から headless 起動検査を実行し、四言語画面と安全な停止境界を確認します。
Pull Request の成果物は短期間の検査用です。Releases へ公開できるのは、既に
存在し `v2.3.0-rc.N` に一致するタグだけです。

### 現在確認する範囲

- CI がネイティブ形式の配布物を作成し、そこから起動できます。
- 繁体字中国語、簡体字中国語、英語、日本語を切り替えられます。
- macOS と Linux がそれぞれ正しい利用者別保存先を選びます。
- API キー、OAuth、Home Assistant Token、システム操作、音声、自動起動など
  実機未確認の機能は入力画面へ出さず、平文保存にも戻りません。

### 現在証明できないこと

CI 合格は、作者が実機の Mac や Linux デスクトップを所有して確認した証明では
ありません。この Preview は墨寒の完全版ではなく、Windows 版との機能同等を
主張しません。透明キャラクター、完全な会話・作業画面、マイク、スピーカー、
本機女性音声、クラウド連携、ネイティブ秘密情報保存、OS 統合は、実機報告と
追加検証を経てから段階的に有効化します。

現時点では Apple Developer ID の署名・公証を行っていません。macOS が初回
起動を止めた場合は、GitHub Release の配布元、SHA256、Artifact Attestation
を確認したうえで Finder の「開く」から明示的に許可してください。Gatekeeper
全体を無効にしないでください。

### サプライチェーン対策

- Python、PySide6、PyInstaller の版を固定します。
- GitHub Actions は完全なコミット SHA へ固定します。
- macOS は runner 標準の `sips`、`iconutil`、`hdiutil` だけを使用します。
- Linux の公式 `appimagetool` は、ソースコミット、資産 ID、SHA-256 を同時に
  固定し、不一致なら処理を停止します。
- Release には SHA256SUMS、Windows／Preview 別の CycloneDX SBOM、Artifact Attestation を含めます。
- DMG 直下、app のリソース、AppImage の文書ディレクトリに MIT `LICENSE` と
  第三者ソフトウェア通知を収録し、完成品 smoke test で読めることを確認します。
