# 安裝器在地化政策／安装程序本地化策略／Installer Localization Policy／インストーラーのローカライズ方針

## 繁體中文

墨寒提供兩種安裝器格式，兩者刻意採用不同的在地化契約。

### 互動式 EXE 安裝器

Inno Setup EXE 是一般互動式安裝器。它會偵測 Windows 使用者語言，並在安裝前提供以下四個選項：

- 台灣繁體中文（`zh-TW`，LCID 1028）
- 簡體中文（`zh-CN`，LCID 2052）
- 英文（`en-US`，LCID 1033）
- 日文（`ja-JP`，LCID 1041）

選定語言只影響安裝器與解除安裝器介面。墨寒本身的首次啟動精靈仍是應用程式 UI 語言的權威來源。

EXE 與 MSI 捷徑必須指向安裝完成後的執行檔，並使用該執行檔內嵌的墨寒半身圖示，不得保留建置機器或 GitHub runner 的絕對路徑。兩種捷徑與執行中視窗都使用 `FlamebladeStudio.MoHanDesktopAssistant` 工作列身分。Windows CI 必須讀回兩種捷徑的目標與圖示位置，並在解除安裝後確認捷徑已移除。

### MSI 封裝

MSI 維持為台灣繁體中文基礎封裝（`Language=1028`）。它主要供靜默安裝與受管理部署使用，因此不顯示自訂語言選擇器。維持單一穩定基礎 MSI，也能避免發布多個可能被 Windows Installer 視為不同產品的封裝。

建置程序會以相同 payload 與產品身分建立三個語言 transform：

- `MoHan-Desktop-Assistant-<tag>-en-US.mst`（`1033`）
- `MoHan-Desktop-Assistant-<tag>-zh-CN.mst`（`2052`）
- `MoHan-Desktop-Assistant-<tag>-ja-JP.mst`（`1041`）

Transform 必須保留基礎 MSI 的產品身分、component GUID、安裝位置、upgrade code 與 payload。管理員可使用標準 Windows Installer 命令套用其中一個 transform，例如：

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-vX.Y.Z-ja-JP.mst /qn
```

MSI 與 transform 使用 WiX Toolset 7.0.0 建置。WiX v7 維護中的 `Files` 元素會遞迴收集已封裝應用程式；已移除的 Heat／Candle／Light／Torch v3 工具鏈不再使用。每一項 WiX 建置、驗證及 transform 命令，都必須提供擁有者已授權的 `-acceptEula wix7` 參數。ICE 驗證保持啟用；ICE38 與 ICE64 保留歷史上的每使用者封裝豁免，而 ICE91 因其警告只針對假設性的每機器用途而排除，本 `Scope="perUser"` 封裝並不支援該用途。

Windows CI 會安裝基礎 MSI 與每一個 transform、執行封裝後自我測試，再將其解除安裝。任一變體失敗時，絕不得發布 transform。Transform 只影響 Windows Installer 訊息；墨寒首次啟動精靈仍控制應用程式的繁體中文、簡體中文、英文或日文介面與回覆語言。

## 简体中文

墨寒提供两种安装程序格式，两者刻意采用不同的本地化契约。

### 交互式 EXE 安装程序

Inno Setup EXE 是常规交互式安装程序。它会检测 Windows 用户语言，并在安装前提供以下四个选项：

- 台湾繁体中文（`zh-TW`，LCID 1028）
- 简体中文（`zh-CN`，LCID 2052）
- 英文（`en-US`，LCID 1033）
- 日文（`ja-JP`，LCID 1041）

所选语言只影响安装程序与卸载程序界面。墨寒本身的首次运行向导仍是应用程序 UI 语言的权威来源。

EXE 与 MSI 快捷方式必须指向安装完成后的可执行文件，并使用该可执行文件内嵌的墨寒半身图标，不得保留构建计算机或 GitHub runner 的绝对路径。两种快捷方式与运行中的窗口都使用 `FlamebladeStudio.MoHanDesktopAssistant` 任务栏身份。Windows CI 必须读回两种快捷方式的目标与图标位置，并在卸载后确认快捷方式已删除。

### MSI 封装

MSI 保持为台湾繁体中文基础封装（`Language=1028`）。它主要供静默安装与托管部署使用，因此不显示自定义语言选择器。保持单一稳定基础 MSI，也能避免发布多个可能被 Windows Installer 视为不同产品的封装。

构建流程会以相同 payload 与产品身份创建三个语言 transform：

- `MoHan-Desktop-Assistant-<tag>-en-US.mst`（`1033`）
- `MoHan-Desktop-Assistant-<tag>-zh-CN.mst`（`2052`）
- `MoHan-Desktop-Assistant-<tag>-ja-JP.mst`（`1041`）

Transform 必须保留基础 MSI 的产品身份、component GUID、安装位置、upgrade code 与 payload。管理员可使用标准 Windows Installer 命令应用其中一个 transform，例如：

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-vX.Y.Z-ja-JP.mst /qn
```

MSI 与 transform 使用 WiX Toolset 7.0.0 构建。WiX v7 维护中的 `Files` 元素会递归收集已封装应用程序；已移除的 Heat／Candle／Light／Torch v3 工具链不再使用。每一项 WiX 构建、验证及 transform 命令，都必须提供所有者已授权的 `-acceptEula wix7` 参数。ICE 验证保持启用；ICE38 与 ICE64 保留历史上的每用户封装豁免，而 ICE91 因其警告只针对假设性的每机器用途而排除，本 `Scope="perUser"` 封装并不支持该用途。

Windows CI 会安装基础 MSI 与每一个 transform、执行封装后自检，再将其卸载。任一变体失败时，绝不得发布 transform。Transform 只影响 Windows Installer 消息；墨寒首次运行向导仍控制应用程序的繁体中文、简体中文、英文或日文界面与回复语言。

## English

MoHan ships two installer formats with deliberately different localization contracts.

### Interactive EXE installer

The Inno Setup EXE is the normal interactive installer. It detects the Windows user language and offers these four choices before installation:

- Taiwan Traditional Chinese (`zh-TW`, LCID 1028)
- Simplified Chinese (`zh-CN`, LCID 2052)
- English (`en-US`, LCID 1033)
- Japanese (`ja-JP`, LCID 1041)

The selected language affects only the installer and uninstaller interface. MoHan's own first-run wizard remains the authority for the application UI language.

EXE and MSI shortcuts must target the installed executable and use the MoHan half-body icon embedded in that executable; they must never retain an absolute build-machine or GitHub runner path. Both shortcut formats and the running window use the `FlamebladeStudio.MoHanDesktopAssistant` taskbar identity. Windows CI must read back both shortcut targets and icon locations and confirm that uninstall removes each shortcut.

### MSI package

The MSI remains a Taiwan Traditional Chinese base package (`Language=1028`). It is intended primarily for silent installation and managed deployment, so it does not display a custom language picker. Keeping one stable base MSI also avoids publishing several packages that Windows Installer could treat as different products.

The build creates three language transforms from the same payload and product identity:

- `MoHan-Desktop-Assistant-<tag>-en-US.mst` (`1033`)
- `MoHan-Desktop-Assistant-<tag>-zh-CN.mst` (`2052`)
- `MoHan-Desktop-Assistant-<tag>-ja-JP.mst` (`1041`)

The transforms must preserve the base MSI's product identity, component GUIDs, install location, upgrade code, and payload. Administrators can apply one with the standard Windows Installer command, for example:

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-vX.Y.Z-ja-JP.mst /qn
```

The MSI and transforms are built with WiX Toolset 7.0.0. WiX v7's maintained `Files` element recursively harvests the packaged application; the removed Heat/Candle/Light/Torch v3 toolchain is not used. Every WiX build, validation, and transform command supplies the owner-authorized `-acceptEula wix7` argument. ICE validation remains enabled; ICE38 and ICE64 retain the historic per-user package exemptions, while ICE91 is excluded because its warning concerns a hypothetical per-machine use that this `Scope="perUser"` package does not support.

Windows CI installs the base MSI and every transform, runs the packaged self-test, and uninstalls them. A transform must never be published if any variant fails. The transforms affect Windows Installer messages only; MoHan's first-run wizard still controls the application's Traditional Chinese, Simplified Chinese, English, or Japanese interface and reply language.

## 日本語

墨寒は、意図的に異なるローカライズ契約を持つ二つのインストーラー形式を提供します。

### 対話式 EXE インストーラー

Inno Setup EXE は通常の対話式インストーラーです。Windows のユーザー言語を検出し、インストール前に次の四つの選択肢を提示します。

- 台湾繁体字中国語（`zh-TW`、LCID 1028）
- 簡体字中国語（`zh-CN`、LCID 2052）
- 英語（`en-US`、LCID 1033）
- 日本語（`ja-JP`、LCID 1041）

選択した言語が影響するのは、インストーラーとアンインストーラーの画面だけです。アプリケーション UI 言語の正式な決定元は、引き続き墨寒本体の初回起動ウィザードです。

EXE と MSI のショートカットは、インストール済み実行ファイルを参照し、その実行ファイルに埋め込まれた墨寒半身アイコンを使用しなければなりません。ビルドマシンや GitHub runner の絶対パスを残してはなりません。両形式のショートカットと実行中ウィンドウは、`FlamebladeStudio.MoHanDesktopAssistant` のタスクバー ID を共有します。Windows CI は両形式のショートカットのリンク先とアイコン位置を読み戻し、アンインストール後に各ショートカットが削除されたことを確認します。

### MSI パッケージ

MSI は台湾繁体字中国語のベースパッケージ（`Language=1028`）を維持します。主な用途はサイレントインストールと管理下の展開であるため、独自の言語選択画面は表示しません。安定した単一のベース MSI を維持することで、Windows Installer が別製品として扱い得る複数パッケージの公開も防ぎます。

ビルドでは、同一の payload と製品 identity から三つの言語 transform を作成します。

- `MoHan-Desktop-Assistant-<tag>-en-US.mst`（`1033`）
- `MoHan-Desktop-Assistant-<tag>-zh-CN.mst`（`2052`）
- `MoHan-Desktop-Assistant-<tag>-ja-JP.mst`（`1041`）

Transform は、ベース MSI の製品 identity、component GUID、インストール先、upgrade code、payload を維持しなければなりません。管理者は、次の例のように標準の Windows Installer コマンドでいずれかの transform を適用できます。

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-vX.Y.Z-ja-JP.mst /qn
```

MSI と transform は WiX Toolset 7.0.0 でビルドします。WiX v7 で保守されている `Files` 要素が、パッケージ対象アプリケーションを再帰的に収集します。削除済みの Heat／Candle／Light／Torch v3 ツールチェーンは使用しません。WiX のすべてのビルド、検証、transform コマンドに、所有者が許可した `-acceptEula wix7` 引数を指定します。ICE 検証は有効なままとし、ICE38 と ICE64 には従来のユーザー単位パッケージ例外を維持します。ICE91 は、この `Scope="perUser"` パッケージが対応しない仮想的なマシン単位用途だけを警告するため除外します。

Windows CI は、ベース MSI と各 transform をインストールし、パッケージ済み自己テストを実行してからアンインストールします。いずれかの変種が失敗した場合、transform を決して公開してはいけません。Transform が影響するのは Windows Installer のメッセージだけです。アプリケーションの繁体字中国語、簡体字中国語、英語、日本語の画面および応答言語は、引き続き墨寒の初回起動ウィザードが制御します。
