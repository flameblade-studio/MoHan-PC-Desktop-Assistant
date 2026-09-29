# Python 3.15 Qt 建置規格／Python 3.15 Qt 构建规范／Python 3.15 Qt Build Specification／Python 3.15 Qt ビルド仕様

## 繁體中文

這個目錄固定墨寒在官方 PySide6 metadata 尚未允許 Python 3.15 時的原始碼建置規格。它只描述可重現的輸入與補丁，不包含本機輪子、Qt SDK、編譯器、金鑰或使用者資料，也不代表 Qt 官方已正式支援 Python 3.15。

目前固定輸入如下：PySide 原始碼提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test，以及 Designer 外掛的 MSVC 嵌入式 Python 連結補丁。完整值位於 `build-config.toml`，補丁位於 `patches/pyside-designer-python-embed.patch`。

建置流程必須在全新環境中套用固定提交與補丁，產生 `6.11.1+mohan.py315.1` 的 cp310-abi3 輪子，使用一般 pip resolver 的本地 wheelhouse 安裝，並禁止 `--ignore-requires-python`。本機 Windows smoke 已通過；三平台 CI、所有輸入雜湊、正式工作流程接入、包內載入、SBOM 與完整回歸仍是發布前門檻。

2026-09-29 實測顯示，舊的 `shared/qt315-wheelhouse` 已不存在；現存 `shared/qt315-compat-full` 與 CI 都使用 `tools/build_python315_qt_compat.py` 對官方 6.11.1 wheel 做可重現 metadata repack。四顆現存 wheel 均為 `6.11.1+mohan.py315.1`，分別含 60、60、60、1 個 `.pyi`，且各含一個 `py.typed`。工單所述缺少型別 stub 的本機 wheel 是先前候選，不能再作為依賴來源。正式 SHA-256 與型別檔計數固定在 `wheel-hashes.json`。

Windows 本機與 CI 的單一入口是 `python tools/install_python315_dependencies.py --like-ci`。本機預設在專案外的 `shared/qt315-ci-parity/win_amd64` 建置或重用 wheel；CI 明確指定工作目錄內的暫存 wheelhouse。兩者都必須在安裝前通過同一份雜湊清單，品質閘門另有獨立的 wheel 一致性階段。若本機要指定位置，設定 `MOHAN_QT315_WHEELHOUSE`。`cargo-audit` 固定使用 0.22.2，安裝指令是 `cargo install cargo-audit --version 0.22.2 --locked`；缺少工具時品質閘門維持失敗。

在上述證據完成前，官方 PyPI metadata 阻擋仍然有效，不能把本機建置結果宣稱為 v4.0.0 已可發布。

## 简体中文

此目录固定墨寒在官方 PySide6 metadata 尚未允许 Python 3.15 时的源码构建规范。它只描述可复现的输入与补丁，不包含本地轮子、Qt SDK、编译器、密钥或用户数据，也不代表 Qt 官方已经正式支持 Python 3.15。

当前固定输入如下：PySide 源码提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test，以及 Designer 插件的 MSVC 嵌入式 Python 链接补丁。完整值位于 `build-config.toml`，补丁位于 `patches/pyside-designer-python-embed.patch`。

构建流程必须在全新环境中应用固定提交与补丁，生成 `6.11.1+mohan.py315.1` 的 cp310-abi3 轮子，使用普通 pip resolver 的本地 wheelhouse 安装，并禁止 `--ignore-requires-python`。本地 Windows smoke 已通过；三平台 CI、全部输入哈希、正式工作流接入、包内加载、SBOM 与完整回归仍是发布前关卡。

2026-09-29 实测显示，旧的 `shared/qt315-wheelhouse` 已不存在；现有 `shared/qt315-compat-full` 与 CI 都使用 `tools/build_python315_qt_compat.py` 对官方 6.11.1 wheel 执行可重现 metadata repack。四个现有 wheel 均为 `6.11.1+mohan.py315.1`，分别包含 60、60、60、1 个 `.pyi`，且各包含一个 `py.typed`。工单所述缺少类型 stub 的本地 wheel 是先前候选，不再作为依赖来源。正式 SHA-256 与类型文件计数固定在 `wheel-hashes.json`。

Windows 本地与 CI 的单一入口是 `python tools/install_python315_dependencies.py --like-ci`。本地默认在项目外的 `shared/qt315-ci-parity/win_amd64` 构建或复用 wheel；CI 明确指定工作目录内的临时 wheelhouse。两者都必须在安装前通过同一份哈希清单，质量门禁另有独立的 wheel 一致性阶段。如需在本地指定位置，请设置 `MOHAN_QT315_WHEELHOUSE`。`cargo-audit` 固定使用 0.22.2，安装命令是 `cargo install cargo-audit --version 0.22.2 --locked`；工具缺失时质量门禁保持失败。

在上述证据完成前，官方 PyPI metadata 阻挡仍然有效，不能把本地构建结果宣称为 v4.0.0 已可发布。

## English

This directory fixes MoHan's source-build specification for the period in which official PySide6 metadata does not permit Python 3.15. It describes reproducible inputs and patches only. It does not contain local wheels, the Qt SDK, compilers, secrets, or user data, and it does not claim official Qt support for Python 3.15.

The fixed inputs are the PySide source commit `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`, Qt SDK 6.11.1, Python `>=3.15,<3.16`, Core／Gui／Widgets／Network／Multimedia／Svg／Test, and the MSVC embedded-Python link patch for the Designer plugin. The complete values are in `build-config.toml`; the patch is in `patches/pyside-designer-python-embed.patch`.

The build must apply the pinned source and patch in a clean environment, produce `6.11.1+mohan.py315.1` cp310-abi3 wheels, install them from a local wheelhouse through the normal pip resolver, and never use `--ignore-requires-python`. The local Windows smoke check passes. Three-platform CI, hashes for every input, formal workflow integration, packaged loading, SBOM, and full regression remain release gates.

The 2026-09-29 measurement found that the old `shared/qt315-wheelhouse` no longer exists. The current `shared/qt315-compat-full` and CI both use `tools/build_python315_qt_compat.py` to reproducibly repack the official 6.11.1 wheels' metadata. All four current wheels have version `6.11.1+mohan.py315.1`, contain 60, 60, 60, and 1 `.pyi` files respectively, and each contains one `py.typed`. The local wheel without typing stubs described by the ticket was an earlier candidate and is no longer a valid dependency source. `wheel-hashes.json` locks the authoritative SHA-256 values and typing-file counts.

The single Windows local and CI entry point is `python tools/install_python315_dependencies.py --like-ci`. Local runs build or reuse wheels outside the project at `shared/qt315-ci-parity/win_amd64`; CI explicitly selects a temporary wheelhouse in its workspace. Both must pass the same hash list before installation, and the quality gate has a separate wheel-parity stage. Set `MOHAN_QT315_WHEELHOUSE` to select a local location explicitly. `cargo-audit` is pinned to 0.22.2 and installs with `cargo install cargo-audit --version 0.22.2 --locked`; the quality gate remains failed when the tool is absent.

Until that evidence is complete, the official PyPI metadata blocker remains active, and the local build must not be described as making v4.0.0 releasable.

## 日本語

このディレクトリは、PySide6 の公式 metadata が Python 3.15 を許可していない期間における、墨寒のソースビルド仕様を固定します。再現可能な入力とパッチだけを記録し、ローカル wheel、Qt SDK、コンパイラ、secret、ユーザーデータは含みません。Qt が Python 3.15 を公式対応したという意味でもありません。

固定する入力は、PySide ソースコミット `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt SDK 6.11.1、Python `>=3.15,<3.16`、Core／Gui／Widgets／Network／Multimedia／Svg／Test、Designer プラグイン用 MSVC embedded-Python link patch です。完全な値は `build-config.toml` に、パッチは `patches/pyside-designer-python-embed.patch` にあります。

ビルドはクリーンな環境で固定ソースとパッチを適用し、`6.11.1+mohan.py315.1` の cp310-abi3 wheel を作成し、通常の pip resolver によるローカル wheelhouse から導入しなければなりません。`--ignore-requires-python` は禁止です。Windows ローカル smoke は合格していますが、三プラットフォーム CI、全入力の hash、正式 workflow への接続、パッケージ内 load、SBOM、全回帰は公開前のゲートとして残っています。

2026-09-29 の実測では、旧 `shared/qt315-wheelhouse` は存在せず、現在の `shared/qt315-compat-full` と CI はどちらも `tools/build_python315_qt_compat.py` で公式 6.11.1 wheel の metadata を再現可能に再パックしています。現在の四つの wheel はすべて `6.11.1+mohan.py315.1` で、`.pyi` をそれぞれ 60、60、60、1 個含み、各 wheel に `py.typed` が一つあります。工單に記載された型 stub のないローカル wheel は以前の候補であり、今後の依存元にはできません。正式な SHA-256 と型ファイル数は `wheel-hashes.json` に固定します。

Windows のローカルと CI は `python tools/install_python315_dependencies.py --like-ci` を単一入口として使います。ローカルではプロジェクト外の `shared/qt315-ci-parity/win_amd64` に wheel を生成または再利用し、CI は作業領域内の一時 wheelhouse を明示します。両方とも導入前に同じ hash 一覧へ合格し、品質ゲートにも独立した wheel 一致性段階があります。ローカル位置を明示する場合は `MOHAN_QT315_WHEELHOUSE` を設定します。`cargo-audit` は 0.22.2 に固定し、`cargo install cargo-audit --version 0.22.2 --locked` で導入します。ツールがない場合、品質ゲートは失敗を維持します。

これらの証拠が揃うまで、PyPI 公式 metadata の阻害は有効であり、ローカルビルドを v4.0.0 公開可能の根拠として扱ってはいけません。
