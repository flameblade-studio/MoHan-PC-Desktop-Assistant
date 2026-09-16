# 墨寒跨平台狀態／墨寒跨平台状态／MoHan cross-platform status／墨寒クロスプラットフォーム状況

## 繁體中文

這一階段建立「可安全延伸的跨平台核心」；macOS 與 Linux 的聲明範圍是目前已完成的 Preview 能力。Windows 仍是目前唯一具備實機使用、完整回歸、
安裝程式與發行驗證的主要平台。

| 能力 | Windows | macOS | Linux |
|---|---|---|---|
| 核心模組匯入、純核心測試、Qt offscreen | CI 守門 | CI 守門 | CI 守門 |
| 完整桌面角色與設定介面 | 已實作、持續實測 | 尚待真機驗證 | 尚待真機驗證 |
| 系統本機女聲與離線辨識 | 已支援；zh-TW 優先 Yating | 待接入 | 待接入 |
| 安全金鑰保存 | Windows DPAPI | Keychain 尚待實作／實測 | Secret Service 尚待實作／實測 |
| 自動啟動、原生視窗工具 | 已支援 | 待接入 | 待接入 |
| 公開安裝包 | ZIP、EXE、MSI（完整功能） | Apple Silicon arm64／Intel x86_64 DMG（功能受限 Preview） | x86_64 AppImage（功能受限 Preview） |

- 新的語音供應器識別為平台中性的 `system-local`。既有資料庫中的
  `windows-local` 與四語舊標籤會自動遷移，完整保留使用者選擇。
- Windows 資料位置保持 `%LOCALAPPDATA%\YanJianStudio\MoHan`，避免升級後
  看似遺失既有對話、記憶與設定。
- macOS 使用 `~/Library/Application Support/YanJianStudio/MoHan`；Linux
  遵循 `XDG_DATA_HOME`、`XDG_CONFIG_HOME`、`XDG_CACHE_HOME`。
- macOS／Linux 原生安全金鑰保存完成前，程式讓金鑰留在明文保存範圍之外。
- 設定頁與旗艦控制中心共用同一個可注入的金鑰邊界；平台通過驗證後才開放
  金鑰、OAuth、Home Assistant 權杖輸入與相應的原生語音選項。
- GitHub Actions 三系統測試的證據範圍是原始碼匯入、核心邏輯與無畫面 Qt
  守門；真實麥克風、喇叭與完整桌面環境各自保留實機驗證門檻。
- 符合 `vN.N.N` 或 `vN.N.N-rc.N` 的發布系列，另在原生 runner 產生兩種 macOS 架構的 DMG 與 Linux
  AppImage，並從完成的安裝包執行
  啟動與四語畫面 smoke test。預覽殼層的能力集合限定為已通過實機前門檻的項目，秘密輸入、語音、完整桌面角色、
  雲端連接器與系統工具於通過驗證後開放；這是刻意的 fail-closed 邊界。
- 作者的實體 Mac／Linux 手動驗收目前為待完成狀態。CI 封裝與 smoke test 通過
  後仍須清楚標示「未經作者真機驗證」。詳見 [Preview 安裝包說明](PREVIEW-PACKAGES.md)。

## 简体中文

此阶段建立的是“可安全扩展的跨平台核心”，；macOS 与 Linux 的声明范围是当前已完成的 Preview 能力。Windows 仍是目前唯一经过真机使用、完整回归、
安装程序与发布验证的主要平台。

| 能力 | Windows | macOS | Linux |
|---|---|---|---|
| 核心模块导入、纯核心测试、Qt offscreen | CI 守门 | CI 守门 | CI 守门 |
| 完整桌面角色与设置界面 | 已实现并持续实测 | 等待真机验证 | 等待真机验证 |
| 系统本地女性语音与离线识别 | 已支持；zh-TW 优先 Yating | 待接入 | 待接入 |
| 安全密钥保存 | Windows DPAPI | Keychain 待实现／实测 | Secret Service 待实现／实测 |
| 自动启动与原生窗口工具 | 已支持 | 待接入 | 待接入 |
| 公开安装包 | ZIP、EXE、MSI（完整功能） | Apple Silicon arm64／Intel x86_64 DMG（功能受限 Preview） | x86_64 AppImage（功能受限 Preview） |

- 新语音供应器 ID 为平台中性的 `system-local`。数据库中的
  `windows-local` 与四语旧标签会自动迁移，完整保留用户选择。
- Windows 数据目录继续使用 `%LOCALAPPDATA%\YanJianStudio\MoHan`。
- macOS 使用 `~/Library/Application Support/YanJianStudio/MoHan`；Linux
  遵循 `XDG_DATA_HOME`、`XDG_CONFIG_HOME`、`XDG_CACHE_HOME`。
- 在 macOS／Linux 原生安全密钥保存完成前，程序让密钥保持在明文保存范围之外。
- 设置页与旗舰控制中心共用同一个可注入密钥边界；平台通过验证后才开放密钥、
  OAuth、Home Assistant 权杖输入与相应的原生语音选项。
- 三系统 CI 的证据范围是源代码导入、核心逻辑与无画面 Qt；真实麦克风、扬声器与完整桌面环境各自保留真机验证关卡。
- 符合 `vN.N.N` 或 `vN.N.N-rc.N` 的发布系列会在原生 runner 生成两种 macOS 架构的 DMG 与 Linux
  AppImage，并从完成的安装包执行
  启动与四语界面 smoke test。预览外壳的能力集合限定为已通过真机前关卡的项目，秘密输入、语音、完整桌面角色、
  云端连接器与系统工具在通过验证后开放；这是刻意的 fail-closed 边界。
- 作者的实体 Mac／Linux 手动验收目前为待完成状态；即使 CI 通过，也会明确标示
  “未经作者真机验证”。详情见 [Preview 安装包说明](PREVIEW-PACKAGES.md)。

## English

This phase establishes a safe cross-platform core; the macOS and Linux claim scope is
the Preview capability completed so far.
Windows remains the only platform with real-device use, the full regression
suite, installer testing, and published packages.

| Capability | Windows | macOS | Linux |
|---|---|---|---|
| Core imports, pure-core tests, Qt offscreen | CI gate | CI gate | CI gate |
| Full character shell and settings UI | Implemented and exercised | Real-device validation pending | Real-device validation pending |
| System-local female speech and offline recognition | Supported; zh-TW prefers Yating | Connection pending | Connection pending |
| Secure secret storage | Windows DPAPI | Keychain pending | Secret Service pending |
| Autostart and native window tools | Supported | Connection pending | Connection pending |
| Published packages | ZIP, EXE, MSI (complete build) | Apple Silicon arm64 / Intel x86_64 DMGs (limited Preview) | x86_64 AppImage (limited Preview) |

- `system-local` is the platform-neutral speech-provider ID. Existing
  `windows-local` values and older localized labels migrate while preserving
  the user's selection.
- The Windows data directory remains
  `%LOCALAPPDATA%\YanJianStudio\MoHan`, preserving all existing profiles.
- macOS uses `~/Library/Application Support/YanJianStudio/MoHan`; Linux follows
  `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME`.
- Until native secure storage is implemented and validated on macOS/Linux,
  MoHan keeps secrets outside plaintext storage through its fail-closed state.
- Settings and the flagship control center share one injectable secret-store
  boundary. Platforms expose key, OAuth, Home Assistant token inputs, and corresponding native speech controls
  after their validation completes.
- A green matrix provides evidence for imports, pure-core behavior, and headless Qt.
  Real microphones, speakers, and a complete desktop session retain separate device gates.
- Release lines matching `vN.N.N` or `vN.N.N-rc.N` also build both macOS architecture DMGs and the Linux
  AppImage on native runners
  and smoke-tests startup and all four UI languages from the finished package.
  The Preview shell exposes the capability set that has passed pre-device gates; secret entry, voice, the complete character UI,
  cloud connectors, and system tools become available after validation. This is a deliberate fail-closed boundary.
- Maintainer signoff on physical Mac/Linux devices is currently pending.
  Passing package CI remains labelled as not maintainer-device validated. See
  [the Preview package guide](PREVIEW-PACKAGES.md).

## 日本語

この段階で整備するのは、安全に拡張できるクロスプラットフォーム中核です。
macOS／Linux の表明範囲は、現在までに完成した Preview 機能です。
実機利用、全回帰テスト、インストーラー、公開パッケージまで確認済みの主要
プラットフォームは、現在も Windows のみです。

| 機能 | Windows | macOS | Linux |
|---|---|---|---|
| 中核モジュール、純粋な中核テスト、Qt offscreen | CI 検査 | CI 検査 | CI 検査 |
| 完全なデスクトップキャラクターと設定画面 | 実装・継続実機確認済み | 実機確認待ち | 実機確認待ち |
| システム本機女性音声・オフライン認識 | 対応済み；zh-TW は Yating 優先 | 接続待ち | 接続待ち |
| 安全なキー保存 | Windows DPAPI | Keychain 実装／実機確認待ち | Secret Service 実装／実機確認待ち |
| 自動起動・ネイティブウィンドウ操作 | 対応済み | 接続待ち | 接続待ち |
| 公開パッケージ | ZIP、EXE、MSI（完全版） | Apple Silicon arm64／Intel x86_64 DMG（機能限定 Preview） | x86_64 AppImage（機能限定 Preview） |

- 音声プロバイダーの新しい共通 ID は `system-local` です。既存の
  `windows-local` と旧四言語ラベルは、利用者の選択を完全に保持して移行します。
- Windows の保存先は `%LOCALAPPDATA%\YanJianStudio\MoHan` を維持します。
- macOS は `~/Library/Application Support/YanJianStudio/MoHan`、Linux は
  `XDG_DATA_HOME`、`XDG_CONFIG_HOME`、`XDG_CACHE_HOME` に従います。
- macOS／Linux の安全なネイティブ保存が完成するまで、キーを平文保存の範囲外に維持し、
  安全側で停止します。
- 設定画面とフラッグシップ制御画面は、同じ注入可能なキー保存境界を使用します。
  環境の検証完了後にキー、OAuth、Home Assistant トークン入力と
  対応するネイティブ音声を開放します。
- 三 OS の CI 合格が示す証拠範囲は中核と headless Qt です。実機のマイク、スピーカー、デスクトップ環境、
  完全なデスクトップ利用は個別の実機ゲートを維持します。
- `vN.N.N` または `vN.N.N-rc.N` に一致するリリース系列では、ネイティブ runner で macOS 両アーキテクチャの
  DMG と Linux AppImage を作成し、
  完成した配布物から起動と四言語画面の smoke test を実行します。Preview
  シェルは実機前ゲートを通過した機能を提供し、秘密情報入力、音声、完全なキャラクター画面、クラウド連携、
  システム操作は検証後に開放します。これは意図した fail-closed 境界です。
- 作者による実機 Mac／Linux の手動確認は現在完了待ちです。CI 合格後も作者実機
  未確認と明記します。[Preview 配布物の説明](PREVIEW-PACKAGES.md)もご覧ください。
