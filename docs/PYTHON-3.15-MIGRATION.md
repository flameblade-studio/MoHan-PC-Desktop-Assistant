# Python 3.15 遷移／Python 3.15 迁移／Python 3.15 migration／Python 3.15 移行

## 繁體中文

執行環境基準：**僅限 CPython 3.15.0rc1**。完成遷移後，墨寒不保留第二套
Python 執行環境。完整上游檢查清單以官方
[Python 3.15 新功能](https://docs.python.org/3.15/whatsnew/3.15.html)為準；
其中每一項標準庫變更、移除與棄用，未來只要適用於墨寒功能，皆持續納入評估。

墨寒採用「新版能力可安全適用時，不沿用舊寫法」原則。已導入 PEP 810
全專案明示延遲導入、PEP 814 `frozendict` 與遞迴不可變設定、PEP 798
推導式解包、PEP 686 UTF-8 稽核、`bytearray.take_bytes()` 音訊封包緩衝、
PEP 799 Tachyon，以及 PEP 803／820／793 Stable ABI 依賴驗證。PEP 661
`sentinel` 已加入治理測試；目前沒有舊式 `object()` 哨兵可替換，未來一旦
「未傳值」與 `None` 必須區分，就必須使用內建 `sentinel`。
開頭比對已改用語意明確的 `re.prefixmatch()`，並由稽核阻止軟性棄用的
`re.match()` 回流。

2.3.0 RC2 封裝使用固定在 CPython 提交
`37e98da7c19a9e5892ee756d6dee08225422cd49` 的官方原始碼，以
`--experimental-jit`／`--enable-experimental-jit=yes` 建置 JIT 預設啟用
執行環境；未修改 PyInstaller 的隔離邊界。`PYTHON_JIT=0` 僅用於效能與
相容性對照。PEP 831 Frame Pointer、Windows tail-calling interpreter、
PEP 782／788 與其他 C API 項目由 runtime report、官方輪子與 CI 驗證，
不在 Python 業務程式偽造使用。PEP 829、728、747、800 與標準庫新增 API
目前沒有等價且有價值的使用點；未來功能符合用途時必須重新評估並採用。

兩輪各 20,000 次表情、物理與嘴型整合壓測均通過；JIT 關閉／開啟分別耗時
24.639／25.068 秒，工作集成長 10.62／12.94 MB。JIT 在此負載沒有可靠優勢，
但依產品政策仍預設啟用，並保留 `MOHAN_DISABLE_JIT=1` 相容性開關。Tachyon
在 JIT 開啟的正式環境分析啟動、50 Hz 嘴型同步與表情仲裁器，分別保留
4,553／11,482／3,475 個有效樣本；堆疊讀取錯誤率為
6.20%／2.23%／0.57%，漏採樣率為 0.02%／0%／0%。CI 保存去識別化 flamegraph、
JSONL、pstats、GC／配置／執行緒資料與 SHA-256，不發布原始二進位取樣流。
只有隔離的 `pip-audit` 2.10.1 與 CycloneDX 7.3.0 產生器使用 3.14.7；
墨寒程式、測試、SBOM 語意驗證與所有封裝仍只使用 3.15.0rc1。

同一部 Ryzen 5 5600X Windows 實機以目前的 3.15.0rc1 環境獨立執行三輪
熱路徑比較。JIT 開啟相對關閉時，120,000 次表情仲裁的速度比為
0.86–0.98 倍（中位數 0.97 倍，未證實加速）；2,000 個 50 Hz 嘴型分析節拍
為 1.45–1.65 倍（中位數 1.48 倍）。每一輪的決策、強度校驗和與
A／I／U／E／O 結果完全相同。結果顯示 JIT 效益取決於熱路徑，只證實受測
嘴型分析路徑加速，不宣稱表情仲裁或整體程式會得到一致加速。

### 持續維護的採用矩陣

| Python 3.15 領域 | 墨寒狀態 | 永久觸發條件 |
|---|---|---|
| PEP 810 延遲導入 | 已全專案導入；一處可選匯入防護刻意維持 eager | 新模組必須通過延遲導入稽核 |
| PEP 814 `frozendict` | 已用於全域與巢狀設定 | 新增靜態映射必須不可變 |
| PEP 661 `sentinel` | 執行期已驗證；目前沒有舊式哨兵候選 | 未傳值與明確 `None` 不同時使用 |
| PEP 798 解包 | 已用於語意等價的扁平化與合併 | 稽核新的巢狀扁平化寫法 |
| PEP 686 UTF-8 | 所有專案文字 I/O 都明示 UTF-8 | 編碼稽核必須維持零缺漏 |
| PEP 799 分析 | 去識別化 flamegraph、JSONL、pstats、runtime／GC 與 SHA-256；Release 檢查樣本、讀取錯誤、漏採樣與 JIT | 分析啟動、語音、50 Hz 嘴型與表情仲裁 |
| PEP 831 Frame Pointer | runtime／build 報告與 CI 平台驗證 | 在支援的 Unix runner 使用系統分析器 |
| JIT 與 Windows tail-calling interpreter | 封裝使用固定官方 CPython 提交並預設 JIT；PyInstaller 隔離不變，開關測試皆通過 | 保留停用開關並重跑完整回歸與效能檢查 |
| PEP 803／820／793 Stable ABI 與 C API 現代化 | 已驗證 Qt ABI3 輪子；沒有第一方 C 擴充 | 2.3.0 RC2 拒絕原始碼建置或非 ABI3 Qt 輪子 |
| PEP 782 與 PEP 788 C API | 不適用：墨寒沒有自有 C 擴充 | 加入原生程式碼前重新評估 |
| PEP 829 啟動設定 | 目前封裝的桌面入口不需要 | 墨寒成為可安裝套件或外掛主機時重新評估 |
| PEP 728／747／800 型別功能 | 目前沒有等價的正式模型 | 引入型別化外掛負載或 type-form API 時採用 |
| 分代式 GC 恢復 | 必須執行壓力與記憶體耐久驗證 | 長時間工作階段與前一版基準比較 |
| 標準庫新增／移除／棄用 API | 靜態稽核加 warnings-as-errors | 上游 What’s New 更新時擴充稽核 |

此矩陣刻意保持開放。Python 3.15 預發行文件仍會更新；2.3.0 RC2 在建立標籤前
必須立即重跑官方清單，之後每一個 Python 版本也重複相同流程。

## 简体中文

运行环境基准：**仅限 CPython 3.15.0rc1**。完成迁移后，墨寒不保留第二套
Python 运行环境。完整上游检查清单以官方
[Python 3.15 新功能](https://docs.python.org/3.15/whatsnew/3.15.html)为准；
其中每一项标准库变更、移除与弃用，未来只要适用于墨寒功能，均持续纳入评估。

墨寒遵循“新版能力能够安全适用时，不沿用旧写法”的原则。已导入 PEP 810
全项目显式延迟导入、PEP 814 `frozendict` 与递归不可变配置、PEP 798
推导式解包、PEP 686 UTF-8 审计、`bytearray.take_bytes()` 音频包缓冲、
PEP 799 Tachyon，以及 PEP 803／820／793 Stable ABI 依赖验证。PEP 661
`sentinel` 已加入治理测试；目前没有旧式 `object()` 哨兵可替换，未来一旦
“未传值”与 `None` 必须区分，就必须使用内建 `sentinel`。
开头匹配已改用语义明确的 `re.prefixmatch()`，并由审计阻止软性弃用的
`re.match()` 回流。

2.3.0 RC2 打包使用固定在 CPython 提交
`37e98da7c19a9e5892ee756d6dee08225422cd49` 的官方源代码，以
`--experimental-jit`／`--enable-experimental-jit=yes` 构建默认启用 JIT 的
运行环境；不修改 PyInstaller 隔离边界。`PYTHON_JIT=0` 仅用于性能与兼容性
对照。PEP 831 Frame Pointer、Windows tail-calling interpreter、PEP 782／788
及其他 C API 项目由 runtime report、官方轮子与 CI 验证，不在 Python 业务
代码中伪造使用。PEP 829、728、747、800 与标准库新增 API 目前没有等价且
有价值的使用点；未来功能符合用途时必须重新评估并采用。

两轮各 20,000 次表情、物理与口型整合压力测试均通过；JIT 关闭／开启分别耗时
24.639／25.068 秒，工作集增长 10.62／12.94 MB。JIT 在此负载没有可靠优势，
但依产品政策仍默认启用，并保留 `MOHAN_DISABLE_JIT=1` 兼容性开关。Tachyon
在 JIT 开启的正式环境分析启动、50 Hz 口型同步与表情仲裁器，分别保留
4,553／11,482／3,475 个有效样本；堆栈读取错误率为
6.20%／2.23%／0.57%，漏采样率为 0.02%／0%／0%。CI 保存去标识化 flamegraph、
JSONL、pstats、GC／配置／线程数据与 SHA-256，不发布原始二进制采样流。
只有隔离的 `pip-audit` 2.10.1 与 CycloneDX 7.3.0 生成器使用 3.14.7；
墨寒程序、测试、SBOM 语义验证与所有打包仍只使用 3.15.0rc1。

同一台 Ryzen 5 5600X Windows 真机以当前的 3.15.0rc1 环境独立执行三轮
热路径比较。JIT 开启相对关闭时，120,000 次表情仲裁的速度比为
0.86–0.98 倍（中位数 0.97 倍，未证实加速）；2,000 个 50 Hz 口型分析节拍
为 1.45–1.65 倍（中位数 1.48 倍）。每一轮的决策、强度校验和与
A／I／U／E／O 结果完全相同。结果显示 JIT 收益取决于热路径，只证实受测
口型分析路径加速，不宣称表情仲裁或整个程序会获得一致加速。

### 持续维护的采用矩阵

| Python 3.15 领域 | 墨寒状态 | 永久触发条件 |
|---|---|---|
| PEP 810 延迟导入 | 已在全项目导入；一处可选导入防护刻意保持 eager | 新模块必须通过延迟导入审计 |
| PEP 814 `frozendict` | 已用于全局与嵌套配置 | 新增静态映射必须不可变 |
| PEP 661 `sentinel` | 运行时已验证；目前没有旧式哨兵候选 | 未传值与明确 `None` 不同时使用 |
| PEP 798 解包 | 已用于语义等价的扁平化与合并 | 审计新的嵌套扁平化写法 |
| PEP 686 UTF-8 | 所有项目文本 I/O 都显式使用 UTF-8 | 编码审计必须保持零缺漏 |
| PEP 799 分析 | 去标识化 flamegraph、JSONL、pstats、runtime／GC 与 SHA-256；Release 检查样本、读取错误、漏采样与 JIT | 分析启动、语音、50 Hz 口型与表情仲裁 |
| PEP 831 Frame Pointer | runtime／build 报告与 CI 平台验证 | 在支持的 Unix runner 使用系统分析器 |
| JIT 与 Windows tail-calling interpreter | 打包使用固定官方 CPython 提交并默认启用 JIT；PyInstaller 隔离不变，开关测试均通过 | 保留停用开关并重跑完整回归与性能检查 |
| PEP 803／820／793 Stable ABI 与 C API 现代化 | 已验证 Qt ABI3 轮子；没有第一方 C 扩展 | 2.3.0 RC2 拒绝源代码构建或非 ABI3 Qt 轮子 |
| PEP 782 与 PEP 788 C API | 不适用：墨寒没有自有 C 扩展 | 添加原生代码前重新评估 |
| PEP 829 启动配置 | 当前打包的桌面入口不需要 | 墨寒成为可安装包或插件主机时重新评估 |
| PEP 728／747／800 类型功能 | 当前没有等价的正式模型 | 引入类型化插件负载或 type-form API 时采用 |
| 分代式 GC 恢复 | 必须执行压力与内存耐久验证 | 长时间工作阶段与上一版基准比较 |
| 标准库新增／移除／弃用 API | 静态审计加 warnings-as-errors | 上游 What’s New 更新时扩充审计 |

此矩阵刻意保持开放。Python 3.15 预发布文档仍会更新；2.3.0 RC2 在建立标签前
必须立即重跑官方清单，之后每一个 Python 版本也重复相同流程。

## English

Runtime baseline: **CPython 3.15.0rc1 only**. MoHan does not keep a second
Python runtime after this migration. The complete upstream checklist is the
official [What’s New in Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html);
every library change, removal, and deprecation remains in scope whenever a
future MoHan feature can use it safely.

MoHan follows the rule “do not retain an older idiom when a new capability is
safe and applicable.” Integrated work includes project-wide explicit PEP 810
imports, recursive immutable PEP 814 `frozendict` configuration, PEP 798
unpacking comprehensions, PEP 686 UTF-8 auditing, the
`bytearray.take_bytes()` audio-packet buffer, PEP 799 Tachyon, and PEP
803/820/793 Stable ABI dependency validation. PEP 661 `sentinel` is governed
by CI; no legacy `object()` sentinel exists today, and a future API that must
distinguish omission from `None` must use the built-in `sentinel`.
Prefix matching now uses the explicit `re.prefixmatch()` API, and the audit
prevents the soft-deprecated `re.match()` spelling from returning.

The 2.3.0 RC2 packages use official CPython sources pinned to commit
`37e98da7c19a9e5892ee756d6dee08225422cd49`, built with
`--experimental-jit` and `--enable-experimental-jit=yes` so JIT is enabled by
default without weakening PyInstaller isolation. `PYTHON_JIT=0` is used only
for performance and compatibility comparisons. PEP 831 frame pointers, the
Windows tail-calling interpreter, PEP 782/788, and other C API work are verified
through runtime reports, official wheels, and CI rather than simulated in
application code. PEP 829, 728, 747, 800, and new standard-library APIs have
no equivalent valuable use today and must be reassessed when a feature fits.

Two 20,000-iteration expression, physics, and lip-sync integration soaks pass.
JIT off/on takes 24.639/25.068 seconds with 10.62/12.94 MB working-set growth.
This workload shows no reliable JIT advantage, but product policy keeps JIT on
by default with `MOHAN_DISABLE_JIT=1` as a compatibility switch. With JIT on,
Tachyon retains 4,553/11,482/3,475 valid samples for startup, 50 Hz lip sync,
and expression arbitration; stack-read error is 6.20%/2.23%/0.57%, with
0.02%/0%/0% missed samples. CI stores sanitized flamegraph, JSONL, pstats, GC,
allocation,
thread, and SHA-256 evidence, never the raw binary stream. Only the isolated
`pip-audit` 2.10.1 and CycloneDX 7.3.0 generators use 3.14.7; MoHan code,
tests, SBOM semantic validation, and every package remain on 3.15.0rc1 only.

Three independent hot-path comparisons ran on the same Ryzen 5 5600X Windows
host in the current 3.15.0rc1 environment. With JIT on relative to off,
120,000 expression-arbitration iterations measured 0.86–0.98x speed
(0.97x median, with no demonstrated speedup), while 2,000 50 Hz
viseme-analysis ticks measured 1.45–1.65x (1.48x median). Decisions, intensity
checksums, and A/I/U/E/O results were identical in every run. The benefit is
hot-path dependent: these results demonstrate acceleration only for the
measured viseme path, not uniform acceleration of expression arbitration or
the complete application.

### Maintained adoption matrix

| Python 3.15 area | MoHan status | Permanent trigger |
|---|---|---|
| PEP 810 lazy imports | Integrated across the project; one optional-import guard intentionally remains eager | New modules must pass the lazy-import audit |
| PEP 814 `frozendict` | Integrated for global and nested configuration | New static mappings must be immutable |
| PEP 661 `sentinel` | Runtime verified; no legacy sentinel candidate exists | Use when omission and explicit `None` differ |
| PEP 798 unpacking | Integrated where flattening or merging is equivalent | Audit new nested-flattening idioms |
| PEP 686 UTF-8 | All project text I/O explicitly uses UTF-8 | Encoding audit must remain at zero omissions |
| PEP 799 profiling | Sanitized flamegraph, JSONL, pstats, runtime/GC, and SHA-256; Release gates samples, read errors, missed samples, and JIT | Profile startup, speech, 50 Hz visemes, and expression arbitration |
| PEP 831 frame pointers | Runtime/build report and CI platform validation | Use system profilers on supported Unix runners |
| JIT and Windows tail-calling interpreter | Packages use a pinned official CPython commit with JIT on by default; PyInstaller isolation remains intact and on/off tests pass | Keep the disable switch and repeat full regression/performance checks |
| PEP 803/820/793 Stable ABI and C API modernization | Qt ABI3 wheels verified; no first-party C extension | Reject source builds or non-ABI3 Qt wheels in 2.3.0 RC2 |
| PEP 782 and PEP 788 C APIs | Not applicable: MoHan owns no C extension | Reassess before adding native code |
| PEP 829 startup configuration | Not needed by the packaged desktop entry point | Reassess if MoHan becomes an installable package or plugin host |
| PEP 728/747/800 typing features | No equivalent production model yet | Adopt with typed plugin payloads or type-form APIs |
| Generational GC restoration | Stress and memory-soak validation required | Compare long sessions with the previous release baseline |
| New, removed, or deprecated standard-library APIs | Static audit plus warnings-as-errors | Extend the audit whenever upstream What’s New changes |

This matrix is intentionally open. Python 3.15 prerelease documentation still
changes upstream; 2.3.0 RC2 must rerun the official checklist immediately
before tagging, and every later Python release repeats the same process.

## 日本語

実行環境の基準は **CPython 3.15.0rc1 のみ**です。移行後の墨寒は、二つ目の
Python 実行環境を保持しません。アップストリームの完全な確認項目は、公式の
[Python 3.15 の新機能](https://docs.python.org/3.15/whatsnew/3.15.html)を
基準とします。標準ライブラリの変更、削除、非推奨化を含む全項目は、将来の
墨寒機能に安全に適用できる場合、継続して採用を評価します。

墨寒は「新機能を安全に適用できる場合、旧方式を残さない」方針です。PEP 810
の明示的遅延インポート、PEP 814 `frozendict` の再帰的不変設定、PEP 798、
PEP 686 UTF-8 監査、`bytearray.take_bytes()` 音声パケットバッファー、
PEP 799 Tachyon、PEP 803／820／793 Stable ABI 検証を導入しました。PEP 661
`sentinel` は CI で管理しています。現在は旧式の `object()` センチネルがなく、
将来「未指定」と `None` を区別する API では組み込み `sentinel` を使います。
先頭一致には明示的な `re.prefixmatch()` を使用し、監査によってソフト非推奨の
`re.match()` が戻ることを防ぎます。

2.3.0 RC2 は、公式 CPython のコミット
`37e98da7c19a9e5892ee756d6dee08225422cd49` に固定したソースを
`--experimental-jit` と `--enable-experimental-jit=yes` でビルドし、
PyInstaller の隔離を弱めず JIT を既定で有効にします。`PYTHON_JIT=0` は
性能・互換性比較だけに使用します。PEP 831 Frame Pointer、Windows
tail-calling interpreter、PEP 782／788 などの C API は runtime report、
公式 wheel、CI で確認し、アプリコードで擬似的に使用しません。PEP 829、728、
747、800 と標準ライブラリの新 API は、価値ある用途が生じた時点で再評価します。

表情、物理、口形の 20,000 回統合耐久試験を二回通過しました。JIT 無効／有効は
24.639／25.068 秒、作業セット増加は 10.62／12.94 MB で、この負荷では確実な
優位性がありません。ただし製品方針により既定で有効にし、互換性用に
`MOHAN_DISABLE_JIT=1` を残します。Tachyon は JIT 有効環境で起動、50 Hz
リップシンク、表情調停を解析し、4,553／11,482／3,475 有効サンプル、
6.20%／2.23%／0.57% 読取エラー、漏れ 0.02%／0%／0% を確認しました。CI は匿名化済み
flamegraph、JSONL、pstats、GC、割当、スレッド、SHA-256 証拠を保存し、生の
バイナリストリームは公開しません。隔離された `pip-audit` 2.10.1 と
CycloneDX 7.3.0 生成器だけが 3.14.7 を使い、墨寒本体、テスト、SBOM 意味
検証、全パッケージは 3.15.0rc1 のみです。

同じ Ryzen 5 5600X Windows 実機の現在の 3.15.0rc1 環境で、ホットパスを
三回独立して比較しました。JIT 無効時に対する有効時の速度比は、120,000 回の
表情調停で 0.86～0.98 倍（中央値 0.97 倍、加速は確認できず）、2,000 回の
50 Hz 口形解析で 1.45～1.65 倍（中央値 1.48 倍）でした。各回の判断、強度
チェックサム、A／I／U／E／O の結果は完全に一致しました。JIT の効果は
ホットパスに依存し、今回の結果が示す加速は測定した口形解析経路だけです。
表情調停やアプリ全体が一様に高速化するとは主張しません。

### 継続管理する採用マトリクス

| Python 3.15 領域 | 墨寒の状態 | 恒久的な再評価条件 |
|---|---|---|
| PEP 810 遅延インポート | 全体へ導入済み。一つの任意インポート防護だけ意図的に eager | 新規モジュールは遅延インポート監査に合格すること |
| PEP 814 `frozendict` | グローバル・入れ子設定へ導入済み | 新しい静的マッピングは不変にすること |
| PEP 661 `sentinel` | 実行時検証済み。旧式候補は存在しない | 未指定と明示的な `None` が異なる場合に使用 |
| PEP 798 アンパック | 同等な平坦化・結合へ導入済み | 新しい入れ子平坦化構文を監査 |
| PEP 686 UTF-8 | 全テキスト I/O で UTF-8 を明示 | エンコーディング監査の漏れを常にゼロにする |
| PEP 799 解析 | 匿名化 flamegraph、JSONL、pstats、runtime／GC、SHA-256。Release はサンプル、読取エラー、漏れ、JIT を検査 | 起動、音声、50 Hz 口形、表情調停を解析 |
| PEP 831 Frame Pointer | runtime／build 報告と CI プラットフォーム検証 | 対応 Unix runner でシステム分析器を使用 |
| JIT と Windows tail-calling interpreter | 固定した公式 CPython コミットで JIT を既定有効化。PyInstaller 隔離を維持し、オン／オフ試験に合格 | 無効化設定を保ち、全回帰・性能検査を反復 |
| PEP 803／820／793 Stable ABI と C API 現代化 | Qt ABI3 wheel を検証済み。自製 C 拡張はない | 2.3.0 RC2 ではソースビルドや非 ABI3 Qt wheel を拒否 |
| PEP 782 と PEP 788 C API | 非該当：墨寒に自製 C 拡張はない | ネイティブコード追加前に再評価 |
| PEP 829 起動設定 | 現在のデスクトップ入口には不要 | インストール可能パッケージ／プラグインホスト化時に再評価 |
| PEP 728／747／800 型機能 | 同等の本番モデルはまだない | 型付きプラグイン負荷や type-form API 導入時に採用 |
| 世代別 GC の復帰 | 負荷・メモリ耐久検証が必要 | 長時間セッションを前版基準と比較 |
| 標準ライブラリの追加／削除／非推奨 API | 静的監査と warnings-as-errors | 上流 What’s New 更新時に監査を拡張 |

このマトリクスは意図的に開いたままです。Python 3.15 のプレリリース文書は
更新され続けます。2.3.0 RC2 はタグ作成直前に公式一覧を再確認し、以後の
Python リリースでも同じ手順を繰り返します。
