# v4.0.0 Python 3.15 與 Qt 發版阻擋證據／v4.0.0 Python 3.15 与 Qt 发布阻挡证据／v4.0.0 Python 3.15 and Qt Release Blocker Evidence／v4.0.0 Python 3.15 と Qt 公開阻害証拠

## 繁體中文

### 結論

截至 2026-08-13，v4.0.0 發版仍被阻擋。墨寒要求 CPython 3.15.0rc1，並固定 PySide6 6.11.1；但 Qt 官方在 PyPI 發布的 PySide6、PySide6_Addons、PySide6_Essentials 與 shiboken6 6.11.1 metadata 均宣告 `Requires-Python: >=3.10,<3.15`。標準 pip resolver 因此必須拒絕 Python 3.15.0rc1。

### 本機原始碼建置證據（尚不足以解除正式門檻）

2026-08-14 已以 PySide 原始碼提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK 與 Python 3.15.0rc1，在 Windows 本機建出版本 `6.11.1+mohan.py315.1` 的 Core、Gui、Widgets、Network、Multimedia、Svg、Test 組件與 Designer 外掛。乾淨 smoke 環境已確認 Qt 版本、離屏 QWidget 與上述模組載入，過程沒有使用 `--ignore-requires-python`。這只代表本機建置可行；原始碼固定、Qt SDK 與補丁雜湊、三平台 CI 重現、正式依賴安裝流程、包內載入與完整回歸仍未完成，因此官方 metadata 阻擋仍然有效。

### 可重現證據與現況

- 官方來源：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。四者皆由 PyPI 的 Qt 組織維護，且皆排除 Python 3.15。
- `pyproject.toml` 要求 `>=3.15,<3.16`，但五份 requirements 檔只固定版本，沒有可證明官方支援 3.15 的鎖定解法。
- 舊安裝工具曾用 `--ignore-requires-python` 安裝 cp310-abi3 wheel。本機可以匯入，不等於上游正式支援，也不能作為正式發版 clean-install 證據。
- 舊安裝工具還會在安裝前先匯入 PySide6，乾淨 Runner 可能先發生 `ModuleNotFoundError`。目前工具已改為先檢查官方 metadata，通過後才以一般 resolver 安裝，最後才載入 Qt 驗證。
- `app.py` 已精簡為 13 個實體行且 composition-root gate 已通過；正式事件迴圈、Python 3.15 JIT、8 組嘴型／表情回歸，以及由 `tests/run_all.py` 動態發現並隔離執行的 268 個 `test_*.py` 測試腳本均已通過。這些進展不會解除 Qt 官方 metadata 的獨立阻擋；自建 Qt 的包內載入、三平台 clean install、正式封裝與實機驗收仍未完成。
- 所有 CI／Release 安裝流程皆共用該工具，因此現在會在長時間測試與封裝前安全停止，不會默認繞過上游條件。

### 解除阻擋條件

Qt 官方必須發布一組完整且互相一致、metadata 明確允許 Python 3.15 的 PySide6、Addons、Essentials 與 shiboken6。專案之後須同步更新精確版本，並在不使用 `--ignore-requires-python` 的全新 Windows、macOS、Linux 環境完成解析、安裝、Qt 載入、完整回歸、SBOM 與封裝驗證。以上全部完成前，不得宣稱 v4.0.0 可發布。

## 简体中文

### 结论

截至 2026-08-13，v4.0.0 发布仍被阻挡。墨寒要求 CPython 3.15.0rc1，并固定 PySide6 6.11.1；但 Qt 官方在 PyPI 发布的 PySide6、PySide6_Addons、PySide6_Essentials 与 shiboken6 6.11.1 metadata 均声明 `Requires-Python: >=3.10,<3.15`。标准 pip resolver 因此必须拒绝 Python 3.15.0rc1。

### 本地源码构建证据（尚不足以解除正式关卡）

2026-08-14 已使用 PySide 源码提交 `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK 与 Python 3.15.0rc1，在 Windows 本机构建出版本 `6.11.1+mohan.py315.1` 的 Core、Gui、Widgets、Network、Multimedia、Svg、Test 组件与 Designer 插件。干净 smoke 环境已确认 Qt 版本、离屏 QWidget 与上述模块加载，过程中没有使用 `--ignore-requires-python`。这只代表本地构建可行；源码固定、Qt SDK 与补丁哈希、三平台 CI 重现、正式依赖安装流程、包内加载与完整回归仍未完成，因此官方 metadata 阻挡仍然有效。

### 可复现证据与现状

- 官方来源：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。四者均由 PyPI 的 Qt 组织维护，并且都排除 Python 3.15。
- `pyproject.toml` 要求 `>=3.15,<3.16`，但五份 requirements 文件只固定版本，没有能够证明官方支持 3.15 的锁定解法。
- 旧安装工具曾使用 `--ignore-requires-python` 安装 cp310-abi3 wheel。本机可以导入，不等于上游正式支持，也不能作为正式发布的 clean-install 证据。
- 旧安装工具还会在安装前先导入 PySide6，干净 Runner 可能先发生 `ModuleNotFoundError`。当前工具已改为先检查官方 metadata，通过后才使用一般 resolver 安装，最后才载入 Qt 验证。
- `app.py` 已精简为 13 个实体行且 composition-root gate 已通过；正式事件循环、Python 3.15 JIT、8 组嘴型／表情回归，以及由 `tests/run_all.py` 动态发现并隔离执行的 268 个 `test_*.py` 测试脚本均已通过。这些进展不会解除 Qt 官方 metadata 的独立阻挡；自建 Qt 的包内加载、三平台 clean install、正式打包与实机验收仍未完成。
- 所有 CI／Release 安装流程均共用该工具，因此现在会在长时间测试与打包前安全停止，不会默认绕过上游条件。

### 解除阻挡条件

Qt 官方必须发布一组完整且互相一致、metadata 明确允许 Python 3.15 的 PySide6、Addons、Essentials 与 shiboken6。项目之后须同步更新精确版本，并在不使用 `--ignore-requires-python` 的全新 Windows、macOS、Linux 环境完成解析、安装、Qt 载入、完整回归、SBOM 与打包验证。以上全部完成前，不得宣称 v4.0.0 可以发布。

## English

### Conclusion

As of 2026-08-13, the v4.0.0 release remains blocked. MoHan requires CPython 3.15.0rc1 and pins PySide6 6.11.1, while the official Qt publications for PySide6, PySide6_Addons, PySide6_Essentials, and shiboken6 6.11.1 on PyPI all declare `Requires-Python: >=3.10,<3.15`. A standard pip resolver must therefore reject Python 3.15.0rc1.

### Local source-build evidence (not sufficient to remove the formal gate)

On 2026-08-14, a local Windows build used PySide source commit `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`, the Qt 6.11.1 SDK, and CPython 3.15.0rc1 to build version `6.11.1+mohan.py315.1` with Core, Gui, Widgets, Network, Multimedia, Svg, Test, and the Designer plugin. A clean smoke environment confirmed the Qt version, an offscreen QWidget, and imports for those modules without using `--ignore-requires-python`. This proves local build feasibility only. Source pinning, Qt SDK and patch hashes, reproducible three-platform CI, the formal dependency installer, packaged loading, and full regression remain incomplete, so the official metadata blocker stays active.

### Reproducible evidence and current state

- Primary sources: [PySide6](https://pypi.org/pypi/PySide6/6.11.1/json), [PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json), [PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json), and [shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json). All four are maintained by the Qt organization on PyPI and exclude Python 3.15.
- `pyproject.toml` requires `>=3.15,<3.16`, but the five requirements files provide exact version pins rather than a locked solution demonstrating official Python 3.15 support.
- The previous installer used `--ignore-requires-python` to install cp310-abi3 wheels. A successful local import is not upstream support and is not acceptable clean-install evidence for a formal release.
- The previous installer also imported PySide6 before installation, so a clean runner could fail first with `ModuleNotFoundError`. The tool now checks official metadata first, invokes the normal resolver only after compatibility is proven, and imports Qt only for post-install verification.
- `app.py` is now 13 physical lines and the composition-root gate passes. The formal event loop, Python 3.15 JIT, eight mouth／expression regression groups, and all 268 `test_*.py` scripts dynamically discovered and isolated by `tests/run_all.py` pass. These advances do not remove the independent official Qt metadata blocker; packaged loading with the source-built Qt, three-platform clean installation, formal packaging, and real-device acceptance remain incomplete.
- Every CI and Release dependency installation uses that tool. It now fails safely before long tests and packaging instead of silently bypassing upstream constraints.

### Unblocking conditions

Qt must publish a complete, mutually consistent set of PySide6, Addons, Essentials, and shiboken6 artifacts whose metadata explicitly permits Python 3.15. The project must then pin that exact set and complete resolution, installation, Qt loading, full regression, SBOM, and packaging validation in fresh Windows, macOS, and Linux environments without `--ignore-requires-python`. v4.0.0 must not be described as releasable until every condition is met.

## 日本語

### 結論

2026-08-13 現在、v4.0.0 のリリースは引き続き阻害されています。墨寒は CPython 3.15.0rc1 を必須とし、PySide6 6.11.1 を固定しています。しかし、Qt が PyPI で公式公開している PySide6、PySide6_Addons、PySide6_Essentials、shiboken6 6.11.1 の metadata は、すべて `Requires-Python: >=3.10,<3.15` と宣言しています。そのため、標準の pip resolver は Python 3.15.0rc1 を拒否しなければなりません。

### ローカルソースビルドの証拠（正式ゲート解除には不十分）

2026-08-14、PySide のソースコミット `1e708e23e1b7a221e662bc2e5c51fae9e7a8764f`、Qt 6.11.1 SDK、CPython 3.15.0rc1 を使い、Windows ローカルでバージョン `6.11.1+mohan.py315.1` の Core、Gui、Widgets、Network、Multimedia、Svg、Test、Designer プラグインを構築しました。クリーンな smoke 環境で Qt version、offscreen QWidget、対象モジュールの import を確認し、`--ignore-requires-python` は使用していません。これはローカル構築の実現性だけを証明します。ソース固定、Qt SDK とパッチの hash、三プラットフォーム CI の再現、正式依存関係導入、パッケージ内 load、全回帰は未完了のため、公式 metadata の阻害は有効なままです。

### 再現可能な証拠と現状

- 公式一次資料：[PySide6](https://pypi.org/pypi/PySide6/6.11.1/json)、[PySide6_Addons](https://pypi.org/pypi/PySide6_Addons/6.11.1/json)、[PySide6_Essentials](https://pypi.org/pypi/PySide6_Essentials/6.11.1/json)、[shiboken6](https://pypi.org/pypi/shiboken6/6.11.1/json)。4 件とも PyPI 上の Qt 組織が管理し、Python 3.15 を除外しています。
- `pyproject.toml` は `>=3.15,<3.16` を要求していますが、5 件の requirements ファイルは版を固定するだけで、Python 3.15 の公式対応を証明するロック済み解決策ではありません。
- 以前のインストールツールは `--ignore-requires-python` で cp310-abi3 wheel を導入していました。ローカルで import できることは上流の正式対応を意味せず、正式リリースの clean-install 証拠にはできません。
- 以前のツールはインストール前に PySide6 を import していたため、クリーンな Runner では先に `ModuleNotFoundError` が起こり得ました。現在は公式 metadata を先に確認し、対応が証明された場合のみ通常の resolver で導入し、最後に Qt を読み込んで検証します。
- `app.py` は物理 13 行となり、composition-root gate は合格しています。正式イベントループ、Python 3.15 JIT、8 組の口形／表情回帰、および `tests/run_all.py` が動的に検出して隔離実行する 268 個の `test_*.py` テストスクリプトはすべて合格しています。これらの進展は Qt 公式 metadata の独立した阻害を解除せず、ソースビルド Qt のパッケージ内 load、三プラットフォームの clean install、正式パッケージ化、実機受入れは未完了です。
- すべての CI／Release 依存関係導入はこのツールを共有します。現在は上流条件を暗黙に迂回せず、長時間のテストやパッケージ作成より前に安全に停止します。

### 阻害解除の条件

Qt は Python 3.15 を metadata で明示的に許可する、完全かつ相互に整合した PySide6、Addons、Essentials、shiboken6 一式を公開する必要があります。その後、プロジェクトで正確な版を固定し、`--ignore-requires-python` を使わず、新規の Windows、macOS、Linux 環境で解決、導入、Qt 読み込み、全回帰、SBOM、パッケージ検証を完了しなければなりません。全条件を満たすまで v4.0.0 をリリース可能と表現してはなりません。
