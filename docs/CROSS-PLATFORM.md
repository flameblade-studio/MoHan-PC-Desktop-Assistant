# MoHan cross-platform status / 墨寒跨平台狀態

## 繁體中文

這一階段建立的是「可安全延伸的跨平台核心」，不是宣稱 macOS 或 Linux 已經
達到 Windows 正式版的完整功能。Windows 仍是目前唯一具備實機使用、完整回歸、
安裝程式與發行驗證的主要平台。

| 能力 | Windows | macOS | Linux |
|---|---|---|---|
| 核心模組匯入、純核心測試、Qt offscreen | CI 守門 | CI 守門 | CI 守門 |
| 完整桌面角色與設定介面 | 已實作、持續實測 | 尚待真機驗證 | 尚待真機驗證 |
| 系統本機女聲與離線辨識 | 已支援；zh-TW 優先 Yating | 尚未接入 | 尚未接入 |
| 安全金鑰保存 | Windows DPAPI | Keychain 尚待實作／實測 | Secret Service 尚待實作／實測 |
| 自動啟動、原生視窗工具 | 已支援 | 尚未接入 | 尚未接入 |
| 公開安裝包 | ZIP、EXE、MSI（完整功能） | Apple Silicon arm64／Intel x86_64 DMG（功能受限 Preview） | x86_64 AppImage（功能受限 Preview） |

- 新的語音供應器識別為平台中性的 `system-local`。既有資料庫中的
  `windows-local` 與四語舊標籤會自動遷移，不會刪除使用者選擇。
- Windows 資料位置保持 `%LOCALAPPDATA%\YanJianStudio\MoHan`，避免升級後
  看似遺失既有對話、記憶與設定。
- macOS 使用 `~/Library/Application Support/YanJianStudio/MoHan`；Linux
  遵循 `XDG_DATA_HOME`、`XDG_CONFIG_HOME`、`XDG_CACHE_HOME`。
- macOS／Linux 尚未有原生安全金鑰保存前，程式會拒絕退回明文保存。
- 設定頁與旗艦控制中心共用同一個可注入的金鑰邊界；未驗證平台會停用
  金鑰、OAuth 與 Home Assistant 權杖輸入，且不顯示 Windows 專用語音選項。
- GitHub Actions 的三系統測試只證明原始碼可匯入、核心邏輯與無畫面 Qt
  守門通過，不等同真實麥克風、喇叭或完整桌面環境驗證。
- `v2.3.0-rc.N` 另在原生 runner 產生兩種 macOS 架構的 DMG 與 Linux
  AppImage，並從完成的安裝包執行
  啟動與四語畫面 smoke test。預覽殼層不提供秘密輸入、語音、完整桌面角色、
  雲端連接器與系統工具；這是刻意的 fail-closed 邊界，不是功能遺失。
- 作者目前沒有實體 Mac／Linux 電腦可做手動驗收。CI 封裝與 smoke test 通過
  後仍須清楚標示「未經作者真機驗證」。詳見 [Preview 安裝包說明](PREVIEW-PACKAGES.md)。

## 简体中文

此阶段建立的是“可安全扩展的跨平台核心”，并不表示 macOS 或 Linux 已达到
Windows 正式版本的完整功能。Windows 仍是目前唯一经过真机使用、完整回归、
安装程序与发布验证的主要平台。

| 能力 | Windows | macOS | Linux |
|---|---|---|---|
| 核心模块导入、纯核心测试、Qt offscreen | CI 守门 | CI 守门 | CI 守门 |
| 完整桌面角色与设置界面 | 已实现并持续实测 | 等待真机验证 | 等待真机验证 |
| 系统本地女性语音与离线识别 | 已支持；zh-TW 优先 Yating | 尚未接入 | 尚未接入 |
| 安全密钥保存 | Windows DPAPI | Keychain 待实现／实测 | Secret Service 待实现／实测 |
| 自动启动与原生窗口工具 | 已支持 | 尚未接入 | 尚未接入 |
| 公开安装包 | ZIP、EXE、MSI（完整功能） | Apple Silicon arm64／Intel x86_64 DMG（功能受限 Preview） | x86_64 AppImage（功能受限 Preview） |

- 新语音供应器 ID 为平台中性的 `system-local`。数据库中的
  `windows-local` 与四语旧标签会自动迁移，不会删除用户选择。
- Windows 数据目录继续使用 `%LOCALAPPDATA%\YanJianStudio\MoHan`。
- macOS 使用 `~/Library/Application Support/YanJianStudio/MoHan`；Linux
  遵循 XDG 数据、设置与缓存目录。
- 在 macOS／Linux 原生安全密钥保存完成前，程序会拒绝以明文保存密钥。
- 设置页与旗舰控制中心共用同一个可注入密钥边界；未验证平台会停用密钥、
  OAuth 与 Home Assistant 权杖输入，也不会显示 Windows 专用语音选项。
- 三系统 CI 不等同真实麦克风、扬声器或完整桌面环境验证。
- `v2.3.0-rc.N` 会在原生 runner 生成两种 macOS 架构的 DMG 与 Linux
  AppImage，并从完成的安装包执行
  启动与四语界面 smoke test。预览外壳不提供秘密输入、语音、完整桌面角色、
  云端连接器或系统工具，这是刻意的 fail-closed 边界。
- 作者目前没有实体 Mac／Linux 电脑进行手动验收；即使 CI 通过，也会明确标示
  “未经作者真机验证”。详情见 [Preview 安装包说明](PREVIEW-PACKAGES.md)。

## English

This phase establishes a safe cross-platform core; it does **not** claim that
the macOS or Linux application has feature parity with the Windows release.
Windows remains the only platform with real-device use, the full regression
suite, installer testing, and published packages.

| Capability | Windows | macOS | Linux |
|---|---|---|---|
| Core imports, pure-core tests, Qt offscreen | CI gate | CI gate | CI gate |
| Full character shell and settings UI | Implemented and exercised | Real-device validation pending | Real-device validation pending |
| System-local female speech and offline recognition | Supported; zh-TW prefers Yating | Not connected yet | Not connected yet |
| Secure secret storage | Windows DPAPI | Keychain pending | Secret Service pending |
| Autostart and native window tools | Supported | Not connected yet | Not connected yet |
| Published packages | ZIP, EXE, MSI (complete build) | Apple Silicon arm64 / Intel x86_64 DMGs (limited Preview) | x86_64 AppImage (limited Preview) |

- `system-local` is the platform-neutral speech-provider ID. Existing
  `windows-local` values and older localized labels migrate without discarding
  the user's selection.
- The Windows data directory remains
  `%LOCALAPPDATA%\YanJianStudio\MoHan`, preserving all existing profiles.
- macOS uses `~/Library/Application Support/YanJianStudio/MoHan`; Linux follows
  `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME`.
- Until native secure storage is implemented and validated on macOS/Linux,
  MoHan fails closed instead of writing secrets in plaintext.
- Settings and the flagship control center share one injectable secret-store
  boundary. Unverified platforms disable key, OAuth, and Home Assistant token
  inputs and do not advertise Windows-only speech controls.
- A green matrix proves imports, pure-core behavior, and headless Qt only. It is
  not evidence of real microphones, speakers, or a complete desktop session.
- The `v2.3.0-rc.N` line also builds both macOS architecture DMGs and the Linux
  AppImage on native runners
  and smoke-tests startup and all four UI languages from the finished package.
  The Preview shell exposes no secret entry, voice, complete character UI,
  cloud connector, or system tool. This is a deliberate fail-closed boundary.
- The maintainer currently has no physical Mac/Linux device for manual signoff.
  Passing package CI remains labelled as not maintainer-device validated. See
  [the Preview package guide](PREVIEW-PACKAGES.md).

## 日本語

この段階で整備するのは、安全に拡張できるクロスプラットフォーム中核です。
macOS／Linux が Windows 版と同等に完成したという意味ではありません。
実機利用、全回帰テスト、インストーラー、公開パッケージまで確認済みの主要
プラットフォームは、現在も Windows のみです。

| 機能 | Windows | macOS | Linux |
|---|---|---|---|
| 中核モジュール、純粋な中核テスト、Qt offscreen | CI 検査 | CI 検査 | CI 検査 |
| 完全なデスクトップキャラクターと設定画面 | 実装・継続実機確認済み | 実機確認待ち | 実機確認待ち |
| システム本機女性音声・オフライン認識 | 対応済み；zh-TW は Yating 優先 | 未接続 | 未接続 |
| 安全なキー保存 | Windows DPAPI | Keychain 実装／実機確認待ち | Secret Service 実装／実機確認待ち |
| 自動起動・ネイティブウィンドウ操作 | 対応済み | 未接続 | 未接続 |
| 公開パッケージ | ZIP、EXE、MSI（完全版） | Apple Silicon arm64／Intel x86_64 DMG（機能限定 Preview） | x86_64 AppImage（機能限定 Preview） |

- 音声プロバイダーの新しい共通 ID は `system-local` です。既存の
  `windows-local` と旧四言語ラベルは、利用者の選択を失わず移行します。
- Windows の保存先 `%LOCALAPPDATA%\YanJianStudio\MoHan` は変更しません。
- macOS は `~/Library/Application Support/YanJianStudio/MoHan`、Linux は
  XDG のデータ・設定・キャッシュ各ディレクトリに従います。
- macOS／Linux の安全なネイティブ保存が完成するまで、キーを平文で保存せず
  安全側で停止します。
- 設定画面とフラッグシップ制御画面は、同じ注入可能なキー保存境界を使用します。
  未検証の環境ではキー、OAuth、Home Assistant トークン入力を無効にし、
  Windows 専用音声も表示しません。
- 三 OS の CI 合格は、実機のマイク、スピーカー、デスクトップ環境、
  完全なデスクトップ利用の検証を意味しません。
- `v2.3.0-rc.N` 系列では、ネイティブ runner で macOS 両アーキテクチャの
  DMG と Linux AppImage を作成し、
  完成した配布物から起動と四言語画面の smoke test を実行します。Preview
  シェルには秘密情報入力、音声、完全なキャラクター画面、クラウド連携、
  システム操作を設けません。これは意図した fail-closed 境界です。
- 作者は現在、実機 Mac／Linux で手動確認できません。CI 合格後も作者実機
  未確認と明記します。[Preview 配布物の説明](PREVIEW-PACKAGES.md)もご覧ください。
