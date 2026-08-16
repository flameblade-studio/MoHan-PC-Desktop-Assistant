# v4.0.0 Python 3.15 與 Qt 相容供應鏈證據／v4.0.0 Python 3.15 与 Qt 兼容供应链证据／v4.0.0 Python 3.15 and Qt Compatibility Supply-Chain Evidence／v4.0.0 Python 3.15 と Qt 互換サプライチェーン証拠

## 繁體中文

### 結論

截至 2026-08-16，PySide6 6.11.1 的官方預編譯 metadata 仍宣告 `Requires-Python: >=3.10,<3.15`，但那只描述上游預編譯發行範圍，**不再是墨寒 v4.0.0 的發版阻擋條件**。本專案採用炎劍文化工作室核准的 Python 3.15 相容供應鏈：固定官方 PyPI 輸入與雜湊的相容 wheelhouse，以及固定 PySide 原始碼與 Qt SDK 的本機 source-build 規格。

### 已核准的本機原始碼建置證據

2026-08-14 已以 PySide 原始碼提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK 與 Python 3.15.0rc1，在 Windows 本機建出版本 `6.11.1+mohan.py315.1` 的 Core、Gui、Widgets、Network、Multimedia、Svg、Test 組件與 Designer 外掛。乾淨 smoke 環境已確認 Qt 版本、離屏 QWidget 與上述模組載入，過程沒有使用 `--ignore-requires-python`。此成果是已核准的相容基礎；原始碼、Qt SDK、補丁與產物雜湊、各平台重現、包內載入、完整回歸與 SBOM 仍須作為獨立發行證據驗證，而非將上游 metadata 當作阻擋。

### 可重現證據與現況

- 官方來源：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。四者皆由 PyPI 的 Qt 組織維護，且皆排除 Python 3.15。
- `pyproject.toml` 要求 `>=3.15,<3.16`，但五份 requirements 檔只固定版本，沒有可證明官方支援 3.15 的鎖定解法。
- 舊安裝工具曾用 `--ignore-requires-python` 安裝 cp310-abi3 wheel。本機可以匯入，不等於上游正式支援，也不能作為正式發版 clean-install 證據。
- 舊安裝工具還會在安裝前先匯入 PySide6，乾淨 Runner 可能先發生 `ModuleNotFoundError`。目前工具已改為先檢查官方 metadata，通過後才以一般 resolver 安裝，最後才載入 Qt 驗證。
- `app.py` 已精簡為 13 個實體行且 composition-root gate 已通過；正式事件迴圈、Python 3.15 JIT、8 組嘴型／表情回歸，以及由 `tests/run_all.py` 動態發現並隔離執行的 268 個 `test_*.py` 測試腳本均已通過。自建 Qt 的包內載入、三平台 clean install、正式封裝與實機驗收仍未完成，但這些是獨立證據，不是 Qt 官方 metadata 的阻擋。
- 所有 CI／Release 安裝流程皆共用該工具，因此現在會在長時間測試與封裝前安全停止，不會默認繞過上游條件。

### 發行前仍需的獨立證據

專案須以固定輸入在對應目標重現所選 wheelhouse／source-build 路徑，並在不使用 `--ignore-requires-python` 的全新 Windows、macOS、Linux 環境完成正常 resolver 安裝、Qt 載入、完整回歸、SBOM、雜湊與封裝驗證。Windows 為正式支援；macOS 與 Linux 維持 Preview 邊界。以上證據尚未齊備前，不得宣稱 v4.0.0 可發布，但官方預編譯 metadata 本身不是阻擋。

## 简体中文

### 结论

截至 2026-08-16，PySide6 6.11.1 的官方预编译 metadata 仍声明 `Requires-Python: >=3.10,<3.15`，但这只描述上游预编译发行范围，**不再是墨寒 v4.0.0 的发布阻挡条件**。本项目采用炎剑文化工作室批准的 Python 3.15 兼容供应链：固定官方 PyPI 输入与哈希的兼容 wheelhouse，以及固定 PySide 源码与 Qt SDK 的本地 source-build 规格。

### 已批准的本地源码构建证据

2026-08-14 已使用 PySide 源码提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK 与 Python 3.15.0rc1，在 Windows 本机构建出版本 `6.11.1+mohan.py315.1` 的 Core、Gui、Widgets、Network、Multimedia、Svg、Test 组件与 Designer 插件。干净 smoke 环境已确认 Qt 版本、离屏 QWidget 与上述模块加载，过程中没有使用 `--ignore-requires-python`。该成果是已批准的兼容基础；源码、Qt SDK、补丁与产物哈希、各平台重现、包内加载、完整回归与 SBOM 仍须作为独立发布证据验证，而不是把上游 metadata 当作阻挡。

### 可复现证据与现状

- 官方来源：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。四者均由 PyPI 的 Qt 组织维护，并且都排除 Python 3.15。
- `pyproject.toml` 要求 `>=3.15,<3.16`，但五份 requirements 文件只固定版本，没有能够证明官方支持 3.15 的锁定解法。
- 旧安装工具曾使用 `--ignore-requires-python` 安装 cp310-abi3 wheel。本机可以导入，不等于上游正式支持，也不能作为正式发布的 clean-install 证据。
- 旧安装工具还会在安装前先导入 PySide6，干净 Runner 可能先发生 `ModuleNotFoundError`。当前工具已改为先检查官方 metadata，通过后才使用一般 resolver 安装，最后才载入 Qt 验证。
- `app.py` 已精简为 13 个实体行且 composition-root gate 已通过；正式事件循环、Python 3.15 JIT、8 组嘴型／表情回归，以及由 `tests/run_all.py` 动态发现并隔离执行的 268 个 `test_*.py` 测试脚本均已通过。自建 Qt 的包内加载、三平台 clean install、正式打包与实机验收仍未完成，但这些是独立证据，不是 Qt 官方 metadata 的阻挡。
- 所有 CI／Release 安装流程均共用该工具，因此现在会在长时间测试与打包前安全停止，不会默认绕过上游条件。

### 发布前仍需的独立证据

项目须以固定输入在对应目标重现所选 wheelhouse／source-build 路径，并在不使用 `--ignore-requires-python` 的全新 Windows、macOS、Linux 环境完成普通 resolver 安装、Qt 加载、完整回归、SBOM、哈希与打包验证。Windows 为正式支持；macOS 与 Linux 保持 Preview 边界。以上证据尚未齐备前，不得声明 v4.0.0 可以发布，但官方预编译 metadata 本身不是阻挡。

## English

### Conclusion

As of 2026-08-16, PySide6 6.11.1 official prebuilt metadata still says `Requires-Python: >=3.10,<3.15`. That describes the upstream prebuilt release range only and is **not a MoHan v4.0.0 release blocker**. The project uses the Flameblade Studio-approved Python 3.15 compatibility supply chain: a fixed-digest official-PyPI compatibility wheelhouse and a pinned local PySide-source/Qt-SDK source-build specification.

### Approved local source-build evidence

On 2026-08-14, a local Windows build used PySide source commit `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`, the Qt 6.11.1 SDK, and CPython 3.15.0rc1 to build version `6.11.1+mohan.py315.1` with Core, Gui, Widgets, Network, Multimedia, Svg, Test, and the Designer plugin. A clean smoke environment confirmed the Qt version, an offscreen QWidget, and imports for those modules without using `--ignore-requires-python`. This is approved compatibility groundwork. Source, SDK, patch, and artifact hashes; target-platform reproduction; packaged loading; full regression; and SBOM remain independent release evidence, rather than treating upstream metadata as a blocker.

### Reproducible evidence and current state

- Primary sources: [PySide6](https://pypi.org/pypi/PySide6/6.11.1/json), [PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json), [PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json), and [shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json). All four are maintained by the Qt organization on PyPI and exclude Python 3.15.
- `pyproject.toml` requires `>=3.15,<3.16`, but the five requirements files provide exact version pins rather than a locked solution demonstrating official Python 3.15 support.
- The previous installer used `--ignore-requires-python` to install cp310-abi3 wheels. A successful local import is not upstream support and is not acceptable clean-install evidence for a formal release.
- The previous installer also imported PySide6 before installation, so a clean runner could fail first with `ModuleNotFoundError`. The current tool installs the verified project compatibility wheelhouse through the normal resolver and imports Qt only for post-install verification.
- `app.py` is now 13 physical lines and the composition-root gate passes. The formal event loop, Python 3.15 JIT, eight mouth／expression regression groups, and all 268 `test_*.py` scripts dynamically discovered and isolated by `tests/run_all.py` pass. Packaged loading with the source-built Qt, three-platform clean installation, formal packaging, and real-device acceptance remain incomplete independent evidence, not an official Qt metadata blocker.
- Every CI and Release dependency installation uses that tool. It now fails safely before long tests and packaging instead of silently bypassing upstream constraints.

### Independent evidence still required before release

The project must reproduce its selected wheelhouse/source-build path from pinned inputs on each target and complete normal-resolver installation, Qt loading, full regression, SBOM, digests, and package validation in fresh Windows, macOS, and Linux environments without `--ignore-requires-python`. Windows is supported; macOS and Linux retain their Preview boundary. v4.0.0 must not be described as releasable until that evidence is complete, but official prebuilt metadata itself is not the blocker.

## 日本語

### 結論

2026-08-16 時点で、PySide6 6.11.1 の公式 prebuilt metadata は `Requires-Python: >=3.10,<3.15` のままです。しかし、これは上流 prebuilt の公開範囲だけを示し、**墨寒 v4.0.0 の公開阻害条件ではありません**。本プロジェクトは、炎剣文化工作室が承認した Python 3.15 互換サプライチェーン、すなわち固定ダイジェストの公式 PyPI 互換 wheelhouse と固定 PySide ソース／Qt SDK のローカル source-build 仕様を使用します。

### 承認済みのローカルソースビルド証拠

2026-08-14、PySide のソースコミット `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK、CPython 3.15.0rc1 を使い、Windows ローカルでバージョン `6.11.1+mohan.py315.1` の Core、Gui、Widgets、Network、Multimedia、Svg、Test、Designer プラグインを構築しました。クリーンな smoke 環境で Qt version、offscreen QWidget、対象モジュールの import を確認し、`--ignore-requires-python` は使用していません。これは承認済みの互換基盤です。ソース、SDK、patch、成果物 hash、対象プラットフォームでの再現、パッケージ内 load、全回帰、SBOM は、上流 metadata を阻害と扱うのではなく独立した公開証拠として残ります。

### 再現可能な証拠と現状

- 公式一次資料：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。4 件とも PyPI 上の Qt 組織が管理し、Python 3.15 を除外しています。
- `pyproject.toml` は `>=3.15,<3.16` を要求していますが、5 件の requirements ファイルは版を固定するだけで、Python 3.15 の公式対応を証明するロック済み解決策ではありません。
- 以前のインストールツールは `--ignore-requires-python` で cp310-abi3 wheel を導入していました。ローカルで import できることは上流の正式対応を意味せず、正式リリースの clean-install 証拠にはできません。
- 以前のツールはインストール前に PySide6 を import していたため、クリーンな Runner では先に `ModuleNotFoundError` が起こり得ました。現在のツールは検証済みプロジェクト互換 wheelhouse を通常 resolver で導入し、最後に Qt を読み込んで検証します。
- `app.py` は物理 13 行となり、composition-root gate は合格しています。正式イベントループ、Python 3.15 JIT、8 組の口形／表情回帰、および `tests/run_all.py` が動的に検出して隔離実行する 268 個の `test_*.py` テストスクリプトはすべて合格しています。ソースビルド Qt のパッケージ内 load、三プラットフォームの clean install、正式パッケージ化、実機受入れは未完了の独立証拠であり、Qt 公式 metadata の阻害ではありません。
- すべての CI／Release 依存関係導入はこのツールを共有します。現在は上流条件を暗黙に迂回せず、長時間のテストやパッケージ作成より前に安全に停止します。

### 公開前に必要な独立証拠

プロジェクトは、固定入力から選択した wheelhouse/source-build 経路を各ターゲットで再現し、`--ignore-requires-python` を使わず、新規の Windows、macOS、Linux 環境で通常 resolver による導入、Qt 読み込み、全回帰、SBOM、digest、パッケージ検証を完了する必要があります。Windows は正式対応、macOS と Linux は Preview 境界を維持します。この証拠がそろうまで v4.0.0 を公開可能と表現してはいけませんが、公式 prebuilt metadata 自体は阻害ではありません。
