# Python 3.15 migration / Python 3.15 遷移 / Python 3.15 迁移 / Python 3.15 移行

Runtime baseline: **CPython 3.15.0rc1 only**. MoHan does not keep a second
Python runtime after this migration. The complete upstream checklist is the
official [What’s New in Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html);
every item in that document, including library changes, removals and
deprecations, remains in scope for future MoHan features.

## 繁體中文

墨寒採用「新版能力可安全適用時，不沿用舊寫法」原則。已導入：PEP 810
全專案明示延遲導入、PEP 814 `frozendict` 與遞迴不可變設定、PEP 798
推導式解包、PEP 686 UTF-8 稽核、`bytearray.take_bytes()` 音訊封包緩衝、
PEP 799 Tachyon 取樣工具，以及 PEP 803／820／793 Stable ABI 依賴驗證。
PEP 661 `sentinel` 已加入治理測試；目前沒有舊式 `object()` 哨兵可替換，未來
一旦出現「未傳值」與 `None` 必須區分的 API，就必須使用內建 `sentinel`。

2.3.0 RC1 封裝使用固定在 CPython 提交
`37e98da7c19a9e5892ee756d6dee08225422cd49` 的官方原始碼，以
`--experimental-jit`／`--enable-experimental-jit=yes` 建置 JIT 預設啟用
執行環境；未修改 PyInstaller 的隔離邊界。`PYTHON_JIT=0` 僅用於效能與相容性
對照。PEP 831 Frame Pointer、Windows tail-calling interpreter、
PEP 782／788 與其他 C API 項目屬 CPython／原生擴充建置層，透過 runtime
report、官方輪子與 CI 驗證，不在 Python 業務程式偽造使用。PEP 829、PEP
728、PEP 747、PEP 800 及標準庫新增 API，當前沒有等價且有價值的使用點，
保留在本清單；未來功能一旦符合用途就必須重新評估並採用。

實測兩輪各 20,000 次表情、物理與嘴型整合壓測皆通過；JIT 關閉／開啟分別
耗時 24.639／25.068 秒，工作集成長 10.62／12.94 MB。JIT 在此工作負載沒有
可靠優勢；依產品採用新版能力的政策，2.3.0 RC1 仍預設啟用 JIT，並保留
`MOHAN_DISABLE_JIT=1` 相容性逃生開關。Tachyon 已以 JIT 開啟的正式執行環境
真實分析啟動、50 Hz 嘴型同步與表情仲裁器；本機嚴格閘門分別保留 3,908／
11,107／3,604 個有效樣本，堆疊讀取錯誤率為 5.08%／2.71%／0.74%，三者
漏採樣率皆為 0%。CI 會保存去識別化的 flamegraph、JSONL、pstats、執行期
GC／配置區塊／執行緒數據與 SHA-256 證據，不保存原始二進位取樣流。
`pip-audit` 2.10.1 與 CycloneDX 7.3.0 的產生器相依套件目前尚不能完整支援
3.15，故只有這兩項隔離的稽核工具使用 3.14.7；墨寒程式、測試、SBOM
語意驗證與所有封裝仍只有 3.15.0rc1。

Ryzen 5 5600X Windows 實機的三輪熱路徑中位數顯示：120,000 次表情仲裁由
JIT 關閉的 0.462 秒降為開啟的 0.293 秒（1.57 倍）；2,000 個 50 Hz
嘴型分析節拍由 1.873 秒降為 0.571 秒（3.28 倍）。兩模式的決策、強度校驗和
與 A/I/U/E/O 結果完全相同。這是 CPU 熱路徑微基準，不宣稱整體程式快三倍。

## 简体中文

墨寒遵循“新版能力能够安全适用时，不沿用旧写法”的原则。已导入 PEP 810
全项目显式延迟导入、PEP 814 不可变配置、PEP 798 推导式解包、PEP 686
UTF-8 审计、音频缓冲新 API、PEP 799 Tachyon，以及 Stable ABI 依赖验证。
当前没有旧式 `object()` 哨兵；治理测试会阻止它重新出现，未来需要区分
“未传值”和 `None` 时必须使用 PEP 661 内建 `sentinel`。JIT、Frame Pointer、
C API 与暂时没有实际使用点的类型／启动配置功能持续保留在升级清单，新增功能
出现适用场景时必须重新评估，不得因沿用旧代码而放弃。

两轮各 20,000 次整合压力测试均通过；JIT 在此负载没有可靠优势，所以 2.3.0 RC1
仍按产品政策默认启用 JIT，并保留 `MOHAN_DISABLE_JIT=1` 兼容性开关。
Tachyon 已在 JIT 开启的正式运行环境中分析启动、50 Hz 嘴型同步和表情
仲裁器，分别保留 3,908／11,107／3,604 个有效样本，堆栈读取错误率为
5.08%／2.71%／0.74%，漏采样率均为 0%。CI 保存去识别化 flamegraph、
JSONL、pstats、GC／内存／线程运行数据及 SHA-256，不保存原始二进制采样流。
Windows 实机热路径中，表情仲裁与 50 Hz 嘴型分析分别约为关闭 JIT 时的
1.57 倍与 3.28 倍，且功能校验结果完全一致；这不代表整个程序快三倍。
仅 `pip-audit` 2.10.1 与 CycloneDX 7.3.0 生成器的隔离工具使用 3.14.7；
墨寒程序、测试、SBOM 语义验证与所有封装仍只使用 3.15.0rc1。

## English

MoHan adopts every Python 3.15 capability that has a real project use and can
be proven regression-safe. Integrated items include explicit PEP 810 imports,
immutable PEP 814 configuration, PEP 798 unpacking comprehensions, PEP 686
encoding governance, the new audio-buffer bytearray API, PEP 799 Tachyon, and
Stable ABI validation. No legacy `object()` sentinel exists today; CI rejects
that pattern and requires PEP 661 when omission must differ from `None`.
Interpreter, operating-system, C API, typing, and package-startup features are
tracked even when they have no honest application-level use yet, and must be
reassessed whenever MoHan gains a relevant feature.

Both 20,000-iteration integration soaks passed. JIT showed no reliable gain
for this workload. Version 2.3.0 RC1 nevertheless enables it by default under the product's
new-capability policy, with `MOHAN_DISABLE_JIT=1` as a compatibility escape.
With JIT enabled, Tachyon sampled startup, the real 50 Hz lip-sync test, and
expression arbitration. The strict local gate retained 3,908, 11,107, and
3,604 valid samples with 5.08%, 2.71%, and 0.74% stack-read error and no
missed samples. CI retains sanitized flamegraph, JSONL, pstats, GC, allocation,
thread, and SHA-256 evidence; the raw binary sample stream is never published.
Only the isolated `pip-audit` 2.10.1 and CycloneDX 7.3.0 generator tools run on
3.14.7 while their dependencies cannot fully support 3.15. MoHan code, tests,
SBOM semantic validation, and every package remain exclusively on 3.15.0rc1.
On the Ryzen 5 5600X Windows host, median hot-path throughput improved by
1.57x for expression arbitration and 3.28x for 50 Hz viseme analysis, with
identical functional checksums. This is a microbenchmark, not a claim that the
whole application is three times faster.

## 日本語

墨寒では、実用途があり回帰がないと証明できる Python 3.15 の新機能を必ず
採用します。PEP 810、PEP 814、PEP 798、PEP 686、音声バッファーの新 API、
PEP 799 Tachyon、Stable ABI 検証を導入しました。現在は旧式の `object()`
センチネルが存在しないため、CI で再導入を禁止し、必要になった時点で PEP
661 の組み込み `sentinel` を使用します。JIT、Frame Pointer、C API、型機能、
起動設定など現時点で適用箇所がない項目も継続管理し、関連機能の追加時に必ず
再評価します。

20,000 回の統合耐久試験は JIT の有無の両方で合格しました。この負荷では
JIT の確実な利点はありませんが、製品方針に従って 2.3.0 RC1 では既定で有効にし、
互換性用の `MOHAN_DISABLE_JIT=1` を残します。JIT 有効環境で起動、実際の
50 Hz リップシンク、表情調停を Tachyon 解析し、3,908／11,107／3,604 の
有効サンプル、5.08%／2.71%／0.74% のスタック読取エラー、漏れ 0% を確認
しました。CI は匿名化済み flamegraph、JSONL、pstats、GC、割当、スレッド、
SHA-256 証拠を保存し、生のバイナリサンプルは公開しません。`pip-audit`
2.10.1 と CycloneDX 7.3.0 生成ツールだけを隔離された 3.14.7 で実行し、
墨寒本体、テスト、SBOM 意味検証、全パッケージは 3.15.0rc1 のみです。
Windows 実機のホットパス中央値では、表情調停が 1.57 倍、50 Hz リップ
シンク解析が 3.28 倍となり、機能チェックサムは完全に一致しました。これは
マイクロベンチマークであり、アプリ全体が 3 倍速いという意味ではありません。

## Maintained adoption matrix

| Python 3.15 area | MoHan status | Permanent trigger |
|---|---|---|
| PEP 810 lazy imports | Integrated across project; one optional-import guard remains intentionally eager | New modules must pass the lazy-import audit |
| PEP 814 `frozendict` | Integrated for global and nested configuration | New static mappings must be immutable |
| PEP 661 `sentinel` | Runtime verified; no legacy sentinel candidate exists | Use when omitted and explicit `None` differ |
| PEP 798 unpacking | Integrated where flattening/merging was equivalent | Audit new nested flattening idioms |
| PEP 686 UTF-8 | All project text I/O requires explicit UTF-8 | Encoding audit must remain at zero |
| PEP 799 profiling | Sanitized flamegraph, JSONL, pstats, runtime/GC and SHA-256 evidence; sample count, read-error, missed-sample and JIT release gates | Profile startup, speech, 50 Hz visemes and expression arbitration |
| PEP 831 frame pointers | Runtime/build report; CI platform verification | Use system profilers on supported Unix runners |
| JIT and Windows tail-calling interpreter | Packages use the exact official CPython commit built with JIT on by default; PyInstaller isolation remains intact; on/off tests pass | Keep the disable escape and repeat full regression/performance checks |
| PEP 803/820/793 Stable ABI and C API modernization | Qt ABI3 wheels verified; no first-party C extension | Reject source builds or non-ABI3 Qt wheels in 2.3.0 RC1 |
| PEP 782 and PEP 788 C APIs | Not applicable: MoHan owns no C extension | Reassess before adding native code |
| PEP 829 startup configuration | Not currently needed by the packaged desktop entry point | Reassess if MoHan becomes an installable package/plugin host |
| PEP 728/747/800 typing features | No equivalent production model yet | Adopt when typed plugin payloads/type-form APIs are introduced |
| GC generational restoration | Stress and memory-soak validation required | Compare long sessions with the prior release baseline |
| New/removed/deprecated standard-library APIs | Static audit plus warnings-as-errors | Extend the audit whenever upstream What’s New changes |

This matrix is intentionally not closed. Python 3.15 prerelease documentation
is still updated upstream; 2.3.0 RC1 must re-run the official checklist immediately
before tagging, and every later Python release repeats the same process.
