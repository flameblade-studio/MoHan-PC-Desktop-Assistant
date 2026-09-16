# 墨寒原生加速器／墨寒原生加速器／MoHan Native Accelerator／墨寒ネイティブアクセラレーター

## 繁體中文

### 邊界

`_mohan_accel` 是墨寒第一方、MIT 授權的 Rust＋PyO3 原生模組。它承接可由確定性測試核對的 CPU 熱路徑：PCM16 縮放、立體聲混音、取樣率轉換、音訊強度與母音分析，以及 RGBA alpha 合成、交叉淡化與受遮罩區域合成。Python 參考實作仍是行為規格；當模組載入狀態或單次運算狀態需要 Python 路徑時，產品層會留下可觀測診斷並自動採用 Python。此模組的存取範圍固定在這些 CPU 熱路徑，Qt、網路、資料庫與金鑰位於範圍之外。

### RGBA 契約分界與慢路徑觀測

RGBA 的 `ValueError` 代表呼叫端需依契約調整，例如可見像素越界、遮罩非二值或尺寸不符；這類錯誤原樣交給呼叫端，`operation_failures` 維持原值，原生運算維持可用。模組載入狀態採用 Python 時，`available` 為 `False` 並使用 Python；單次運算發生後端故障時，該運算進入停用、計數並只警告一次。以 `accelerator.status()` 檢查：某運算出現在 `disabled_operations`，或其 `operation_failures` 有計數，即表示該運算走 Python 慢路徑。

呼叫端若持有 `bytearray`／`memoryview`，在跨入 PyO3 前先以 `bytes(buffer)` 建立不可變快照；底層 `_mohan_accel` 的契約固定使用不可變 `bytes`。512×512、5 輪實測中位數［全距］為原生 3.007 ms［1.819–4.560］、Python 路徑 397.365 ms［389.295–415.565］，原生處理速度約為 Python 的 132 倍。

### 固定版本建置與驗證

使用 CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2 與 Rayon 1.12.0。`Cargo.lock`、`rust-toolchain.toml` 與 `--locked` 固定建置輸入；正式流程先執行 rustfmt、Clippy 與 Rust 測試，再建置並安裝包含 `abi3t` 標籤的 wheel，最後執行 Python／Rust 等價及效能測試。RGBA 達 262,144 pixels 且有多個工作執行緒時才條件式使用 Rayon；Rust serial／Rayon 邊界與 Python／native 實測提供等價及效能證據。`PyBackedBytes` 可借用不可變的 Python `bytes`；可變 `bytearray` 會先複製到 Rust 擁有的記憶體，以維持資料隔離。輸出仍建立新的 Python `bytes`，因此端到端處理採用複製策略，SIMD 範圍維持目前實作。重採樣在 Python 與 Rust 邊界共同限制固定寬度整數與每次最多 4,194,304 個輸出樣本，先以固定上限檢查請求再配置記憶體。手動／CI 證據可寫入 `native-wheels/`；`build.ps1` 每次使用新的 `native-wheels-<id>/`，讓後續建置維持穩定。兩者皆納入 Git 忽略規則，也不列為 Release 資產。Windows 正式套件必須包含並實際載入 `_mohan_accel`，且通過 PCM 與 RGBA 核心運算；macOS／Linux 在核心 CI 建置驗證，Preview 能力以目前核心驗證範圍為準。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## 简体中文

### 边界

`_mohan_accel` 是墨寒第一方、采用 MIT 许可的 Rust＋PyO3 原生模块。它承接能由确定性测试核对的 CPU 热路径：PCM16 缩放、立体声混音、采样率转换、音频强度与元音分析，以及 RGBA alpha 合成、交叉淡化与受遮罩区域合成。Python 参考实现仍是行为规范；当模块加载状态或单次运算状态需要 Python 路径时，产品层会留下可观察诊断并自动采用 Python。此模块的访问范围固定在这些 CPU 热路径，Qt、网络、数据库与密钥位于范围之外。

### RGBA 契约分界与慢路径观测

RGBA 的 `ValueError` 表示调用方需要按契约调整，例如可见像素越界、遮罩非二值或尺寸不符；这类错误原样交给调用方，`operation_failures` 保持原值，原生运算保持可用。模块加载状态采用 Python 时，`available` 为 `False` 并使用 Python；单次运算发生后端故障时，该运算进入停用、计数并只警告一次。用 `accelerator.status()` 检查：某运算出现在 `disabled_operations`，或其 `operation_failures` 有计数，即表示该运算走 Python 慢路径。

调用方若持有 `bytearray`／`memoryview`，在跨入 PyO3 前先用 `bytes(buffer)` 建立不可变快照；底层 `_mohan_accel` 的契约固定使用不可变 `bytes`。512×512、5 轮实测中位数［全距］为原生 3.007 ms［1.819–4.560］、Python 路径 397.365 ms［389.295–415.565］，原生处理速度约为 Python 的 132 倍。

### 固定版本构建与验证

使用 CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2 与 Rayon 1.12.0。`Cargo.lock`、`rust-toolchain.toml` 与 `--locked` 固定构建输入；正式流程先运行 rustfmt、Clippy 与 Rust 测试，再构建并安装包含 `abi3t` 标签的 wheel，最后运行 Python／Rust 等价和性能测试。RGBA 达到 262,144 pixels 且有多个工作线程时才条件式使用 Rayon；Rust serial／Rayon 边界与 Python／native 实测提供等价和性能证据。`PyBackedBytes` 可借用不可变的 Python `bytes`；可变 `bytearray` 会先复制到 Rust 拥有的内存，以保持数据隔离。输出仍创建新的 Python `bytes`，因此端到端处理采用复制策略，SIMD 范围保持当前实现。重采样在 Python 与 Rust 边界共同限制固定宽度整数与每次最多 4,194,304 个输出样本，在分配内存前以固定上限检查请求。手动／CI 证据可写入 `native-wheels/`；`build.ps1` 每次使用新的 `native-wheels-<id>/`，让后续构建保持稳定。两者均纳入 Git 忽略规则，也不列为 Release 资产。Windows 正式软件包必须包含并实际加载 `_mohan_accel`，且通过 PCM 与 RGBA 核心运算；macOS／Linux 在核心 CI 构建验证，Preview 能力以当前核心验证范围为准。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## English

### Boundary

`_mohan_accel` is MoHan's first-party, MIT-licensed Rust and PyO3 native module. It handles CPU hot paths that deterministic tests can compare: PCM16 scaling, stereo mixing, sample-rate conversion, audio-level and vowel analysis, plus RGBA alpha-over, crossfade, and masked regional composition. The Python reference implementations remain the behavioral specification. When module loading or an individual operation routes through Python, the product layer records observable diagnostics and automatically uses Python. The module's access scope covers these CPU hot paths, with Qt, networking, databases, and secrets outside that scope.

### RGBA contract boundary and slow-path observability

An RGBA `ValueError` identifies an input that needs a contract adjustment, such as a visible pixel outside the canvas, a non-binary mask, or a size mismatch. It is re-raised to the caller while `operation_failures` and native execution retain their current state. When module loading routes through Python, `available` is `False` and Python is used; when one operation reports a backend fault, that operation enters the disabled state, increments its count, and emits one warning. Check `accelerator.status()`: an operation in `disabled_operations`, or with a count in `operation_failures`, means that operation is using the Python slow path.

If a caller holds `bytearray` or `memoryview`, it snapshots the buffer with `bytes(buffer)` before crossing the PyO3 boundary; the low-level `_mohan_accel` contract uses immutable `bytes`. In the 512×512, five-round measurement, the native median [range] was 3.007 ms [1.819–4.560] and the Python path was 397.365 ms [389.295–415.565]; native processing was roughly 132× faster.

### Pinned build and verification

The toolchain is CPython 3.15, Rust 1.97.1, Maturin 1.14.1, PyO3 0.29.2, and Rayon 1.12.0. `Cargo.lock`, `rust-toolchain.toml`, and `--locked` fix the build inputs. The formal path runs rustfmt, Clippy, and Rust tests, builds and installs a wheel carrying an `abi3t` tag, and then runs Python／Rust equivalence and performance tests. RGBA conditionally uses Rayon at 262,144 pixels or more when multiple worker threads are available; Rust serial／Rayon boundary and Python／native measurements provide equivalence and performance evidence. `PyBackedBytes` can borrow immutable Python `bytes`; mutable `bytearray` input is first copied into Rust-owned memory to preserve data isolation. Outputs still allocate new Python `bytes`, so this path uses a copy strategy and keeps SIMD scope aligned with the current implementation. Python and Rust jointly enforce fixed-width resampling integers and a maximum of 4,194,304 output samples per call, checking the fixed limit before allocation. Manual and CI evidence may use `native-wheels/`; every `build.ps1` invocation uses a fresh `native-wheels-<id>/`, keeping later builds stable. Git ignores both locations, and neither is a Release asset. Formal Windows packages must contain and directly load `_mohan_accel`, then pass core PCM and RGBA operations. macOS／Linux build it in core CI, with Preview packaging scope following the current core evidence.

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## 日本語

### 境界

`_mohan_accel` は墨寒の第一者 MIT ライセンス Rust＋PyO3 ネイティブモジュールです。決定的テストで照合できる CPU ホットパスを担当します。対象は PCM16 の倍率変換、ステレオ混合、サンプルレート変換、音声レベルと母音解析、および RGBA の alpha-over、クロスフェード、マスク付き領域合成です。Python 参照実装を動作仕様として維持し、モジュール読み込みまたは個別処理が Python 経路へ切り替わる場合、製品層は観測可能な診断を記録して Python を自動的に使用します。このモジュールのアクセス範囲はこれらの CPU ホットパスに定め、Qt、ネットワーク、データベース、機密情報を範囲外に置きます。

### RGBA 契約の境界と低速経路の観測

RGBA の `ValueError` は、可視ピクセルのキャンバス外、二値でないマスク、サイズ不一致など、入力契約の調整が必要な状態を表します。この種のエラーはそのまま呼び出し側へ返し、`operation_failures` とネイティブ処理は現在の状態を保ちます。モジュール読み込みが Python 経路へ切り替わると `available` が `False` になり、Python を使用します。一つの処理がバックエンド障害を報告した場合、その処理を無効化し、計数し、警告を一度だけ出します。`accelerator.status()` で確認できます。処理名が `disabled_operations` にあるか、`operation_failures` に計数があれば、その処理は Python の低速経路です。

呼び出し側が `bytearray`／`memoryview` を持つ場合は、PyO3 境界を越える前に `bytes(buffer)` で不変スナップショットを作ります。低レベルの `_mohan_accel` は不変 `bytes` の契約を使用します。512×512、5 回の実測中央値［全域］はネイティブ 3.007 ms［1.819–4.560］、Python 経路 397.365 ms［389.295–415.565］で、ネイティブ処理は約 132 倍高速です。

### 固定バージョンのビルドと検証

ツールチェーンは CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2、Rayon 1.12.0 です。`Cargo.lock`、`rust-toolchain.toml`、`--locked` でビルド入力を固定します。正式手順では rustfmt、Clippy、Rust テストを実行し、`abi3t` タグを含む wheel をビルドしてインストールした後、Python／Rust の等価性および性能テストを実行します。RGBA は 262,144 pixels 以上かつ複数のワーカースレッドが利用できる場合だけ条件付きで Rayon を使用し、Rust serial／Rayon 境界と Python／native 実測により等価性と性能の証拠を得ています。`PyBackedBytes` は不変の Python `bytes` を借用できます。可変の `bytearray` は Rust 所有メモリへ先にコピーし、データを分離します。出力では新しい Python `bytes` を生成するため、この経路はコピー戦略を使用し、SIMD の範囲を現行実装に揃えます。リサンプリングでは Python／Rust 境界が固定幅整数と一回あたり最大 4,194,304 出力サンプルを共同で制限し、固定上限をメモリ割り当て前に確認します。手動／CI 証拠は `native-wheels/` を使用できます。`build.ps1` は実行ごとに新しい `native-wheels-<id>/` を使用するため、後続ビルドを安定して実行できます。どちらも Git の対象外であり、Release アセットにも含めません。Windows 正式パッケージは `_mohan_accel` を同梱して直接読み込み、PCM と RGBA の中核処理に合格する必要があります。macOS／Linux は中核 CI でビルド検証し、Preview のパッケージ対応範囲は現行の中核証拠に従います。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```
