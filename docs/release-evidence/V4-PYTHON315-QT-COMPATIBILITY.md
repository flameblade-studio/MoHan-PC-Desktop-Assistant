# v4.0.0 Python 3.15 Qt 相容層證據／v4.0.0 Python 3.15 Qt 兼容层证据／v4.0.0 Python 3.15 Qt Compatibility-Layer Evidence／v4.0.0 Python 3.15 Qt 互換レイヤー証拠

## 繁體中文

### 目前作法

- v4.0.0 的 Python 3.15 Qt 相容層不是把本機自行編譯的原始碼冒充成官方套件。它以固定版本的官方 PyPI wheel 為二進位來源，只在本機重建 wheel metadata、相依版本與雜湊目錄，讓正常 pip resolver 能在 Python 3.15 下明確解析。
- 目前已在乾淨 Windows Python 3.15.0rc1 環境，以 `6.11.1+mohan.py315.1`、`cp310-abi3` wheel、未使用 `--ignore-requires-python` 的方式安裝 PySide6、Addons、Essentials、shiboken6，並通過 `pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test 匯入及離屏 QWidget smoke。
- `tools/build_python315_qt_compat.py` 會從官方 PyPI JSON 取得上游 URL 與 SHA-256，保留編譯二進位內容，只重寫必要 metadata，並產生可稽核 manifest。上游仍不宣稱官方已支援 Python 3.15。

### 原始碼建置備援

- `tools/qt315/build-config.toml` 與本機 PySide source-build wheel 是 Windows 備援證據，不是目前跨平台 Release 的主要相容層，也沒有被當成 macOS/Linux 實機驗證。
- 如果未來官方 wheel 的 abi3 二進位在特定平台無法載入，才會依固定 source-build 規格另行建立該平台的 wheel；失敗時回報並維持 Preview 邊界，不使用忽略相依條件的捷徑。

### 發行政策

- 官方 PySide6 metadata 是否已宣告 Python 3.15，不再是 v4.0.0 的硬閘門；相容層必須以正常 resolver、固定雜湊、`pip check` 與實際 Qt smoke 證明可用。
- Windows 是正式支援平台。macOS 與 Linux 維持功能受限 Preview；CI 原生 runner 的建置與 smoke 是可重現性證據，不等於開發者本人完成該平台實機認證，也不宣稱 Windows 功能同等。
- 安全、秘密隔離、完整回歸、套件內容、SBOM、SHA-256 與可回退行為仍是不可取消的必要閘門。

## 简体中文

### 当前做法

- v4.0.0 的 Python 3.15 Qt 兼容层不是把本地自行编译的源码冒充成官方软件包。它以固定版本的官方 PyPI wheel 作为二进制来源，只在本地重建 wheel metadata、依赖版本与哈希目录，使正常 pip resolver 能在 Python 3.15 下明确解析。
- 当前已在干净 Windows Python 3.15.0rc1 环境，以 `6.11.1+mohan.py315.1`、`cp310-abi3` wheel、未使用 `--ignore-requires-python` 的方式安装 PySide6、Addons、Essentials、shiboken6，并通过 `pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test 导入及离屏 QWidget smoke。
- `tools/build_python315_qt_compat.py` 会从官方 PyPI JSON 获取上游 URL 与 SHA-256，保留编译二进制内容，只重写必要 metadata，并生成可审计 manifest。这里不声称上游已经正式支持 Python 3.15。

### 源码构建备援

- `tools/qt315/build-config.toml` 与本地 PySide source-build wheel 是 Windows 备援证据，不是当前跨平台 Release 的主要兼容层，也没有被当成 macOS/Linux 实机验证。
- 如果未来官方 wheel 的 abi3 二进制在特定平台无法加载，才会按照固定 source-build 规格另行构建该平台的 wheel；失败时报告并维持 Preview 边界，不使用忽略依赖条件的捷径。

### 发布政策

- 官方 PySide6 metadata 是否已经声明 Python 3.15，不再是 v4.0.0 的硬关卡；兼容层必须以正常 resolver、固定哈希、`pip check` 与实际 Qt smoke 证明可用。
- Windows 是正式支持平台。macOS 与 Linux 保持功能受限 Preview；CI 原生 runner 的构建与 smoke 是可复现性证据，不等于开发者本人完成该平台实机认证，也不声明 Windows 功能同等。
- 安全、秘密隔离、完整回归、软件包内容、SBOM、SHA-256 与可回退行为仍是不可取消的必要关卡。

## English

### Current approach

- The v4.0.0 Python 3.15 Qt compatibility layer does not present locally compiled source as an official package. It uses fixed-version official PyPI wheels as the binary source, rebuilds only the wheel metadata, dependency versions, and digest inventory locally, and lets the normal pip resolver resolve the set explicitly on Python 3.15.
- A clean Windows Python 3.15.0rc1 environment installed PySide6, Addons, Essentials, and shiboken6 as `6.11.1+mohan.py315.1` `cp310-abi3` wheels without `--ignore-requires-python`. `pip check`, Core／Gui／Widgets／Network／Multimedia／Svg／Test imports, and an offscreen QWidget smoke test passed.
- `tools/build_python315_qt_compat.py` obtains upstream URLs and SHA-256 values from official PyPI JSON, preserves compiled binary contents, rewrites only necessary metadata, and emits an auditable manifest. It does not claim that upstream has formally enabled Python 3.15.

### Source-build fallback

- `tools/qt315/build-config.toml` and the local PySide source-build wheels are Windows fallback evidence, not the primary cross-platform Release compatibility layer, and they are not treated as macOS/Linux physical-device certification.
- If an official abi3 binary cannot load on a specific platform in the future, a wheel may be built for that platform from the pinned source-build specification; a failure must be reported and the Preview boundary retained rather than bypassing dependency constraints.

### Release policy

- Whether official PySide6 metadata declares Python 3.15 is no longer a v4.0.0 hard gate. The compatibility layer must be proven with the normal resolver, pinned digests, `pip check`, and an actual Qt smoke test.
- Windows is the formally supported platform. macOS and Linux remain limited Previews; native-runner builds and smoke tests are reproducibility evidence, not the developer's physical-device certification and not a Windows feature-parity claim.
- Security, secret isolation, full regression, package contents, SBOM, SHA-256, and rollback behavior remain mandatory non-waivable gates.

## 日本語

### 現在の方式

- v4.0.0 の Python 3.15 Qt 互換レイヤーは、ローカルでコンパイルしたソースを公式パッケージとして扱いません。固定版の公式 PyPI wheel をバイナリの出所とし、ローカルでは wheel metadata、依存版、ダイジェスト台帳だけを再構成して、通常の pip resolver が Python 3.15 で明示的に解決できるようにします。
- クリーンな Windows Python 3.15.0rc1 環境で、`6.11.1+mohan.py315.1`、`cp310-abi3` wheel、`--ignore-requires-python` なしで PySide6、Addons、Essentials、shiboken6 を導入しました。`pip check`、Core／Gui／Widgets／Network／Multimedia／Svg／Test の import、offscreen QWidget smoke は合格しています。
- `tools/build_python315_qt_compat.py` は公式 PyPI JSON から上流 URL と SHA-256 を取得し、コンパイル済みバイナリを保持して必要な metadata だけを書き換え、監査可能な manifest を生成します。上流が Python 3.15 を正式対応したとは表明しません。

### ソースビルドの代替経路

- `tools/qt315/build-config.toml` とローカル PySide source-build wheel は Windows の代替証拠であり、現在のクロスプラットフォーム Release の主要な互換レイヤーではありません。macOS/Linux の実機認証としても扱いません。
- 将来、公式 abi3 バイナリが特定プラットフォームで読み込めない場合だけ、固定した source-build 仕様からそのプラットフォーム用 wheel を別途作成します。失敗時は報告して Preview 境界を維持し、依存条件を無視する近道は使いません。

### 公開ポリシー

- 公式 PySide6 metadata が Python 3.15 を宣言しているかどうかは、v4.0.0 の硬いゲートではありません。互換レイヤーは通常 resolver、固定ダイジェスト、`pip check`、実際の Qt smoke で証明しなければなりません。
- Windows を正式対応プラットフォームとします。macOS と Linux は機能限定 Preview のままです。ネイティブ runner のビルドと smoke は再現性の証拠であり、開発者本人の実機認証でも Windows との機能同等性の表明でもありません。
- セキュリティ、秘密分離、完全回帰、パッケージ内容、SBOM、SHA-256、ロールバック動作は、免除できない必須ゲートとして残ります。
