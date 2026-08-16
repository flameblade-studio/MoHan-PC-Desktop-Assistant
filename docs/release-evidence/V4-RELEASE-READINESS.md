# v4.0.0 發版就緒總表／v4.0.0 发布就绪总表／v4.0.0 Release Readiness／v4.0.0 公開準備状況

## 繁體中文

> **RELEASE-READY／可發布。** 本文件記錄 2026-08-14 的可重現發版路徑；GitHub Release 仍須由鎖定的 tag、必要 CI、完整回歸與實際封裝證據共同產生。

### 目前判定

- **Windows 正式路徑：READY。** Python 3.15.0rc1、Rust／PyO3 原生模組、Windows 安裝包、完整回歸、SBOM、SHA-256 與發版前置檢查由 workflow 驗證。
- **Qt 相容層：READY。** 官方 PyPI wheel 的二進位內容經固定雜湊取得，metadata 以 `6.11.1+mohan.py315.1` 相容層重建；正常 pip resolver、`pip check`、Qt 匯入與離屏 smoke 已在 Windows 通過。
- **macOS／Linux：Preview。** CI 原生 runner 可提供建置與 smoke 證據，但開發者沒有該平台實機；本文件不宣稱實機認證或 Windows 功能同等。
- **PoseAtlas：未納入 v4.0.0。** 候選素材仍缺完整來源授權與正式 sidecar，正式稽核工具維持 fail-closed；Release 只記錄 `optional-not-included`，不把候選素材放入套件。
- **必要安全線仍保留。** 秘密隔離、完整回歸、封裝內容、SBOM、SHA-256、artifact 完整性、可回退與四語文件不能取消。

### 可重現證據

- `tools/check_python315_qt_compatibility.py` 通過；`V4-PYTHON315-QT-COMPATIBILITY.md` 記錄官方 wheel 來源、metadata 相容層、source-build 備援與平台邊界。
- `tests/run_all.py` 在 Python 3.15.0rc1、`PYTHON_JIT=1` 下動態隔離執行 268 個測試腳本，結果為 `ALL_268_TESTS_OK`；本次發版仍須在 tagged CI 重新取得同等證據。
- Rust `1.97.1`、Maturin `1.14.1`、PyO3 `0.29.2`、Rayon `1.12.0` 的 PCM16、嘴型分析與 RGBA 等價性證據已納入測試與包內驗證流程；`PyBackedBytes` 的輸入借用與未實作 SIMD 均如實記錄。
- Windows 安裝器、ZIP、Tachyon 摘要、SBOM、SHA-256 與 attestation 必須由同一個已驗證 commit 產生；任何檔案集合或雜湊不一致都必須讓發布失敗。

### 政策邊界

- 官方 PySide6 是否已在上游 metadata 宣告 Python 3.15，不再是本專案 v4.0.0 的硬閘門；本專案只接受可重現、可稽核且不使用 `--ignore-requires-python` 的相容層。
- macOS/Linux 實機驗證不是發布硬閘門；它們只能以功能受限 Preview 發布，並在說明中清楚標示未經開發者實機驗證。
- 如果必要安全、回歸、秘密、包內驗證或 tag 不變性失敗，不能以這項政策繞過；應先修復或與使用者討論。

## 简体中文

> **RELEASE-READY／可发布。** 本文记录 2026-08-14 的可复现发布路径；GitHub Release 仍须由锁定的 tag、必要 CI、完整回归与实际打包证据共同产生。

### 当前判定

- **Windows 正式路径：READY。** Python 3.15.0rc1、Rust／PyO3 原生模块、Windows 安装包、完整回归、SBOM、SHA-256 与发布前置检查由 workflow 验证。
- **Qt 兼容层：READY。** 官方 PyPI wheel 的二进制内容通过固定哈希取得，metadata 以 `6.11.1+mohan.py315.1` 兼容层重建；正常 pip resolver、`pip check`、Qt 导入与离屏 smoke 已在 Windows 通过。
- **macOS／Linux：Preview。** CI 原生 runner 可提供构建与 smoke 证据，但开发者没有这些平台实机；本文不声明实机认证或 Windows 功能同等。
- **PoseAtlas：未纳入 v4.0.0。** 候选素材仍缺完整来源授权与正式 sidecar，正式审计工具维持 fail-closed；Release 只记录 `optional-not-included`，不把候选素材放入软件包。
- **必要安全线仍保留。** 秘密隔离、完整回归、打包内容、SBOM、SHA-256、artifact 完整性、可回退与四语文档不能取消。

### 可复现证据

- `tools/check_python315_qt_compatibility.py` 已通过；`V4-PYTHON315-QT-COMPATIBILITY.md` 记录官方 wheel 来源、metadata 兼容层、source-build 备援与平台边界。
- `tests/run_all.py` 在 Python 3.15.0rc1、`PYTHON_JIT=1` 下动态隔离执行 268 个测试脚本，结果为 `ALL_268_TESTS_OK`；本次发布仍须在 tagged CI 重新取得同等证据。
- Rust `1.97.1`、Maturin `1.14.1`、PyO3 `0.29.2`、Rayon `1.12.0` 的 PCM16、口型分析与 RGBA 等价性证据已纳入测试与包内验证流程；`PyBackedBytes` 的输入借用与未实现 SIMD 均如实记录。
- Windows 安装器、ZIP、Tachyon 摘要、SBOM、SHA-256 与 attestation 必须由同一个已验证 commit 产生；任何文件集合或哈希不一致都必须让发布失败。

### 政策边界

- 官方 PySide6 是否已经在上游 metadata 声明 Python 3.15，不再是本项目 v4.0.0 的硬关卡；本项目只接受可复现、可审计且不使用 `--ignore-requires-python` 的兼容层。
- macOS/Linux 实机验证不是发布硬关卡；它们只能以功能受限 Preview 发布，并在说明中明确标示未经开发者实机验证。
- 如果必要安全、回归、秘密、包内验证或 tag 不变性失败，不能用这项政策绕过；应先修复或与用户讨论。

## English

> **RELEASE-READY.** This document records the reproducible path as of 2026-08-14. A GitHub Release still requires the immutable tag, required CI, full regression, and actual packaging evidence together.

### Current decision

- **Windows formal path: READY.** Python 3.15.0rc1, the Rust／PyO3 native module, Windows installers, full regression, SBOM, SHA-256, and release preflight are verified by the workflow.
- **Qt compatibility layer: READY.** Binary contents come from official PyPI wheels verified by fixed digests, while metadata is rebuilt as the `6.11.1+mohan.py315.1` compatibility layer; the normal pip resolver, `pip check`, Qt imports, and an offscreen smoke test passed on Windows.
- **macOS／Linux: Preview.** Native CI runners can provide build and smoke evidence, but the developer does not have those physical platforms; this document does not claim physical certification or Windows feature parity.
- **PoseAtlas: excluded from v4.0.0.** Candidate assets still lack complete provenance authorization and formal sidecars. The formal audit tool remains fail-closed; the Release records `optional-not-included` and does not package the candidates.
- **The necessary safety line remains.** Secret isolation, full regression, package contents, SBOM, SHA-256, artifact integrity, fallback behavior, and four-language documentation cannot be removed.

### Reproducible evidence

- `tools/check_python315_qt_compatibility.py` passes; `V4-PYTHON315-QT-COMPATIBILITY.md` records the official wheel sources, metadata compatibility layer, source-build fallback, and platform boundaries.
- `tests/run_all.py` isolated 268 test scripts under Python 3.15.0rc1 with `PYTHON_JIT=1` and produced `ALL_268_TESTS_OK`; tagged CI must obtain equivalent evidence again for this release.
- Rust `1.97.1`, Maturin `1.14.1`, PyO3 `0.29.2`, and Rayon `1.12.0` PCM16, lip-sync, and RGBA equivalence evidence is part of testing and packaged verification; `PyBackedBytes` input borrowing and unimplemented SIMD are stated accurately.
- Windows installers, ZIP, Tachyon summary, SBOM, SHA-256, and attestation must come from the same verified commit; any artifact-set or digest mismatch must fail publication.

### Policy boundaries

- Whether upstream PySide6 metadata declares Python 3.15 is no longer a v4.0.0 hard gate; the project accepts only a reproducible, auditable compatibility layer that does not use `--ignore-requires-python`.
- macOS/Linux physical-device verification is not a release hard gate; those targets may be published only as limited Previews and must clearly state that the developer has not physically certified them.
- If a required security, regression, secret, packaged-content, or tag-immutability check fails, this policy cannot bypass it; the issue must be fixed or discussed with the user first.

## 日本語

> **RELEASE-READY／公開準備完了。** 本文書は 2026-08-14 時点の再現可能な公開経路を記録します。GitHub Release には、不変 tag、必須 CI、完全回帰、実際のパッケージ証拠が引き続き必要です。

### 現在の判定

- **Windows 正式経路：READY。** Python 3.15.0rc1、Rust／PyO3 ネイティブモジュール、Windows インストーラー、完全回帰、SBOM、SHA-256、公開前検査を workflow で検証します。
- **Qt 互換レイヤー：READY。** バイナリ内容は固定ダイジェストで検証した公式 PyPI wheel から取得し、metadata は `6.11.1+mohan.py315.1` 互換レイヤーとして再構成します。通常の pip resolver、`pip check`、Qt import、offscreen smoke は Windows で合格しました。
- **macOS／Linux：Preview。** ネイティブ CI runner は build と smoke の証拠を提供できますが、開発者はこれらの実機を持ちません。本書は実機認証や Windows との機能同等性を表明しません。
- **PoseAtlas：v4.0.0 には含めません。** 候補素材には完全な出典許諾と正式 sidecar がまだありません。正式監査ツールは fail-closed のままとし、Release には `optional-not-included` を記録して候補を同梱しません。
- **必要な安全線は残ります。** 秘密分離、完全回帰、パッケージ内容、SBOM、SHA-256、フォールバック動作、四言語文書は削除できません。

### 再現可能な証拠

- `tools/check_python315_qt_compatibility.py` は合格しています。`V4-PYTHON315-QT-COMPATIBILITY.md` に公式 wheel の出所、metadata 互換レイヤー、source-build 代替、プラットフォーム境界を記録します。
- `tests/run_all.py` は Python 3.15.0rc1 と `PYTHON_JIT=1` の下で 268 個のテストスクリプトを隔離実行し、`ALL_268_TESTS_OK` を出力しました。本リリースでは tagged CI で同等の証拠を再取得します。
- Rust `1.97.1`、Maturin `1.14.1`、PyO3 `0.29.2`、Rayon `1.12.0` による PCM16、リップシンク、RGBA の等価性証拠をテストとパッケージ検証に含めます。`PyBackedBytes` の入力借用と未実装 SIMD は正確に記載します。
- Windows インストーラー、ZIP、Tachyon 概要、SBOM、SHA-256、attestation は同じ検証済み commit から生成し、成果物集合またはダイジェストに不一致があれば公開を失敗させます。

### ポリシー境界

- 上流の PySide6 metadata が Python 3.15 を宣言しているかどうかは、v4.0.0 の硬いゲートではありません。`--ignore-requires-python` を使わない、再現可能で監査可能な互換レイヤーだけを受け入れます。
- macOS/Linux の実機検証は公開の硬いゲートではありません。これらは機能限定 Preview としてのみ公開し、開発者が実機認証していないことを明記します。
- 必須のセキュリティ、回帰、秘密、パッケージ内容、tag 不変性の検査が失敗した場合、この方針で迂回してはなりません。先に修正するか、ユーザーと相談します。
