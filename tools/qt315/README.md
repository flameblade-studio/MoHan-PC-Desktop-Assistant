# Python 3.15 Qt 建置規格／Python 3.15 Qt 构建规范／Python 3.15 Qt Build Specification／Python 3.15 Qt ビルド仕様

## 繁體中文

這個目錄固定墨寒在官方 PySide6 metadata 尚未允許 Python 3.15 時的原始碼建置規格。它只描述可重現的輸入與補丁，不包含本機輪子、Qt SDK、編譯器、金鑰或使用者資料，也不代表 Qt 官方已正式支援 Python 3.15。

目前固定輸入如下：PySide 原始碼提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test，以及 Designer 外掛的 MSVC 嵌入式 Python 連結補丁。完整值位於 `build-config.toml`，補丁位於 `patches/pyside-designer-python-embed.patch`。

建置流程必須在全新環境中套用固定提交與補丁，產生 `6.11.1+mohan.py315.1` 的 cp310-abi3 輪子，使用一般 pip resolver 的本地 wheelhouse 安裝，並禁止 `--ignore-requires-python`。本機 Windows smoke 已通過；三平台 CI、所有輸入雜湊、正式工作流程接入、包內載入、SBOM 與完整回歸仍是發布前門檻。

在上述證據完成前，官方 PyPI metadata 阻擋仍然有效，不能把本機建置結果宣稱為 v4.0.0 已可發布。

## 简体中文

此目录固定墨寒在官方 PySide6 metadata 尚未允许 Python 3.15 时的源码构建规范。它只描述可复现的输入与补丁，不包含本地轮子、Qt SDK、编译器、密钥或用户数据，也不代表 Qt 官方已经正式支持 Python 3.15。

当前固定输入如下：PySide 源码提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test，以及 Designer 插件的 MSVC 嵌入式 Python 链接补丁。完整值位于 `build-config.toml`，补丁位于 `patches/pyside-designer-python-embed.patch`。

构建流程必须在全新环境中应用固定提交与补丁，生成 `6.11.1+mohan.py315.1` 的 cp310-abi3 轮子，使用普通 pip resolver 的本地 wheelhouse 安装，并禁止 `--ignore-requires-python`。本地 Windows smoke 已通过；三平台 CI、全部输入哈希、正式工作流接入、包内加载、SBOM 与完整回归仍是发布前关卡。

在上述证据完成前，官方 PyPI metadata 阻挡仍然有效，不能把本地构建结果宣称为 v4.0.0 已可发布。

## English

This directory fixes MoHan's source-build specification for the period in which official PySide6 metadata does not permit Python 3.15. It describes reproducible inputs and patches only. It does not contain local wheels, the Qt SDK, compilers, secrets, or user data, and it does not claim official Qt support for Python 3.15.

The fixed inputs are the PySide source commit `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`, Qt SDK 6.11.1, Python `>=3.15,<3.16`, Core／Gui／Widgets／Network／Multimedia／Svg／Test, and the MSVC embedded-Python link patch for the Designer plugin. The complete values are in `build-config.toml`; the patch is in `patches/pyside-designer-python-embed.patch`.

The build must apply the pinned source and patch in a clean environment, produce `6.11.1+mohan.py315.1` cp310-abi3 wheels, install them from a local wheelhouse through the normal pip resolver, and never use `--ignore-requires-python`. The local Windows smoke check passes. Three-platform CI, hashes for every input, formal workflow integration, packaged loading, SBOM, and full regression remain release gates.

Until that evidence is complete, the official PyPI metadata blocker remains active, and the local build must not be described as making v4.0.0 releasable.

## 日本語

このディレクトリは、PySide6 の公式 metadata が Python 3.15 を許可していない期間における、墨寒のソースビルド仕様を固定します。再現可能な入力とパッチだけを記録し、ローカル wheel、Qt SDK、コンパイラ、secret、ユーザーデータは含みません。Qt が Python 3.15 を公式対応したという意味でもありません。

固定する入力は、PySide ソースコミット `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test、Designer プラグイン用 MSVC embedded-Python link patch です。完全な値は `build-config.toml` に、パッチは `patches/pyside-designer-python-embed.patch` にあります。

ビルドはクリーンな環境で固定ソースとパッチを適用し、`6.11.1+mohan.py315.1` の cp310-abi3 wheel を作成し、通常の pip resolver によるローカル wheelhouse から導入しなければなりません。`--ignore-requires-python` は禁止です。Windows ローカル smoke は合格していますが、三プラットフォーム CI、全入力の hash、正式 workflow への接続、パッケージ内 load、SBOM、全回帰は公開前のゲートとして残っています。

これらの証拠が揃うまで、PyPI 公式 metadata の阻害は有効であり、ローカルビルドを v4.0.0 公開可能の根拠として扱ってはいけません。
