# v4.0.0 Python 3.15 Qt 三平台封裝驗證／v4.0.0 Python 3.15 Qt 三平台打包验证／v4.0.0 Python 3.15 Qt Three-Platform Packaging Validation／v4.0.0 Python 3.15 Qt 三プラットフォームパッケージ検証

## 繁體中文

本紀錄對應同名 JSON，並以它作為機器可讀正本。2026-08-14 已在乾淨的 Python 3.15.0rc1 Windows x86_64 環境，以一般 pip resolver 從本機 source-built wheelhouse 安裝 `6.11.1+mohan.py315.1`。沒有使用 `--ignore-requires-python`。`pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test 模組載入，以及離屏 `QApplication`／`QWidget` smoke 均通過。

目前 wheelhouse 只有 `win_amd64`。因此 macOS arm64、macOS x86_64、Linux x86_64 沒有本機或原生 runner 證據，均標記為 `blocked_unverified`，不能宣稱三平台封裝完成。官方 PyPI 的 PySide6 6.11.1 metadata 仍排除 Python 3.15；這項官方門檻也維持阻擋。

正式發布前仍須在對應原生平台完成 source build 或取得明確支援的 wheel，使用乾淨 resolver 安裝，執行 Qt smoke、包內載入、SBOM、雜湊與完整回歸。這份紀錄不解除 v4.0.0 發布阻擋。

## 简体中文

本记录对应同名 JSON，并以它作为机器可读正本。2026-08-14 已在干净的 Python 3.15.0rc1 Windows x86_64 环境中，使用普通 pip resolver 从本地 source-built wheelhouse 安装 `6.11.1+mohan.py315.1`。没有使用 `--ignore-requires-python`。`pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test 模块加载，以及离屏 `QApplication`／`QWidget` smoke 均通过。

当前 wheelhouse 只有 `win_amd64`。因此 macOS arm64、macOS x86_64、Linux x86_64 没有本机或原生 runner 证据，均标记为 `blocked_unverified`，不能宣称三平台打包完成。官方 PyPI 的 PySide6 6.11.1 metadata 仍排除 Python 3.15；这个官方关卡也继续阻挡。

正式发布前仍须在对应原生平台完成 source build 或取得明确支持的 wheel，使用干净 resolver 安装，执行 Qt smoke、包内加载、SBOM、哈希与完整回归。本记录不会解除 v4.0.0 发布阻挡。

## English

This record corresponds to the same-named JSON, which is the machine-readable authority. On 2026-08-14, a clean Python 3.15.0rc1 Windows x86_64 environment installed `6.11.1+mohan.py315.1` from the local source-built wheelhouse through the normal pip resolver. No `--ignore-requires-python` was used. `pip check`, imports of Core, Gui, Widgets, Network, Multimedia, Svg, and Test, and an offscreen `QApplication`／`QWidget` smoke all passed.

The current wheelhouse contains only `win_amd64` artifacts. macOS arm64, macOS x86_64, and Linux x86_64 therefore have no native runner or wheel evidence in this record and are marked `blocked_unverified`; three-platform packaging must not be claimed. Official PyPI metadata for PySide6 6.11.1 still excludes Python 3.15, so that official gate remains blocked as well.

Before release, each native target still needs a source build or explicitly supported wheel, clean resolver installation, Qt smoke, packaged loading, SBOM, hashes, and full regression evidence. This record does not remove the v4.0.0 release blocker.

## 日本語

この記録は同名 JSON に対応し、JSON を機械可読な正本とします。2026-08-14、クリーンな Python 3.15.0rc1 Windows x86_64 環境で、ローカルの source-built wheelhouse から通常の pip resolver を使って `6.11.1+mohan.py315.1` を導入しました。`--ignore-requires-python` は使用していません。`pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test の読み込み、オフスクリーン `QApplication`／`QWidget` smoke はすべて合格しました。

現在の wheelhouse にあるのは `win_amd64` の成果物だけです。そのため macOS arm64、macOS x86_64、Linux x86_64 にはネイティブ runner または wheel の証拠がなく、`blocked_unverified` と記録します。三プラットフォームのパッケージ対応を完了したとは言えません。PySide6 6.11.1 の公式 PyPI metadata も Python 3.15 を引き続き除外しており、公式ゲートも阻害されたままです。

公開前に、各ネイティブターゲットで source build または明示的に対応した wheel、クリーンな resolver による導入、Qt smoke、パッケージ内読み込み、SBOM、ハッシュ、完全な回帰証拠を揃える必要があります。本記録は v4.0.0 の公開阻害を解除しません。
