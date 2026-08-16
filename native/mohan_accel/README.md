# 墨寒原生加速器／墨寒原生加速器／MoHan Native Accelerator／墨寒ネイティブアクセラレーター

## 繁體中文

### 邊界

`_mohan_accel` 是墨寒第一方、MIT 授權的 Rust＋PyO3 原生模組。它只承接可由確定性測試核對的 CPU 熱路徑：PCM16 縮放、立體聲混音、取樣率轉換、音訊強度與母音分析，以及 RGBA alpha 合成、交叉淡化與受遮罩區域合成。Python 參考實作仍是行為規格；原生模組無法載入或單次運算失敗時，產品層會留下可觀測診斷並自動回退 Python。此模組沒有 Qt、網路、資料庫或金鑰存取權。

### 固定版本建置與驗證

使用 CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2 與 Rayon 1.12.0。`Cargo.lock`、`rust-toolchain.toml` 與 `--locked` 固定建置輸入；正式流程先執行 rustfmt、Clippy 與 Rust 測試，再建置並安裝包含 `abi3t` 標籤的 wheel，最後執行 Python／Rust 等價及效能測試。RGBA 達 262,144 pixels 且有多個工作執行緒時才條件式使用 Rayon；Rust serial／Rayon 邊界與 Python／native 實測提供等價及效能證據。`PyBackedBytes` 可借用不可變的 Python `bytes`；為避免資料競爭，可變 `bytearray` 會先複製到 Rust 擁有的記憶體。輸出仍建立新的 Python `bytes`，故不宣稱端到端零複製，也不宣稱未實作的 SIMD。重採樣在 Python 與 Rust 邊界共同限制固定寬度整數與每次最多 4,194,304 個輸出樣本，先拒絕異常放大請求再配置記憶體。手動／CI 證據可寫入 `native-wheels/`；`build.ps1` 每次使用新的 `native-wheels-<id>/`，所以既有同名但內容不同的 wheel 不會造成後續建置失敗。兩者皆由 Git 忽略且不會成為 Release 資產。Windows 正式套件必須包含並實際載入 `_mohan_accel`，且通過 PCM 與 RGBA 核心運算；macOS／Linux 僅在核心 CI 建置驗證，不宣稱 Preview 已封裝同等能力。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## 简体中文

### 边界

`_mohan_accel` 是墨寒第一方、采用 MIT 许可的 Rust＋PyO3 原生模块。它只承接能由确定性测试核对的 CPU 热路径：PCM16 缩放、立体声混音、采样率转换、音频强度与元音分析，以及 RGBA alpha 合成、交叉淡化与受遮罩区域合成。Python 参考实现仍是行为规范；原生模块无法加载或单次运算失败时，产品层会留下可观察诊断并自动回退 Python。此模块没有 Qt、网络、数据库或密钥访问权。

### 固定版本构建与验证

使用 CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2 与 Rayon 1.12.0。`Cargo.lock`、`rust-toolchain.toml` 与 `--locked` 固定构建输入；正式流程先运行 rustfmt、Clippy 与 Rust 测试，再构建并安装包含 `abi3t` 标签的 wheel，最后运行 Python／Rust 等价和性能测试。RGBA 达到 262,144 pixels 且有多个工作线程时才条件式使用 Rayon；Rust serial／Rayon 边界与 Python／native 实测提供等价和性能证据。`PyBackedBytes` 可借用不可变的 Python `bytes`；为避免数据竞争，可变 `bytearray` 会先复制到 Rust 拥有的内存。输出仍创建新的 Python `bytes`，因此不声明端到端零复制，也不声明尚未实现的 SIMD。重采样在 Python 与 Rust 边界共同限制固定宽度整数与每次最多 4,194,304 个输出样本，在分配内存前拒绝异常放大请求。手动／CI 证据可写入 `native-wheels/`；`build.ps1` 每次使用新的 `native-wheels-<id>/`，因此已有同名但内容不同的 wheel 不会导致后续构建失败。两者均被 Git 忽略且不会成为 Release 资产。Windows 正式软件包必须包含并实际加载 `_mohan_accel`，且通过 PCM 与 RGBA 核心运算；macOS／Linux 仅在核心 CI 构建验证，不声明 Preview 已打包同等能力。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## English

### Boundary

`_mohan_accel` is MoHan's first-party, MIT-licensed Rust and PyO3 native module. It handles only CPU hot paths that deterministic tests can compare: PCM16 scaling, stereo mixing, sample-rate conversion, audio-level and vowel analysis, plus RGBA alpha-over, crossfade, and masked regional composition. The Python reference implementations remain the behavioral specification. If the module cannot load or an individual operation fails, the product layer records observable diagnostics and automatically falls back to Python. The module has no access to Qt, networking, databases, or secrets.

### Pinned build and verification

The toolchain is CPython 3.15, Rust 1.97.1, Maturin 1.14.1, PyO3 0.29.2, and Rayon 1.12.0. `Cargo.lock`, `rust-toolchain.toml`, and `--locked` fix the build inputs. The formal path runs rustfmt, Clippy, and Rust tests, builds and installs a wheel carrying an `abi3t` tag, and then runs Python／Rust equivalence and performance tests. RGBA conditionally uses Rayon only at 262,144 pixels or more when multiple worker threads are available; Rust serial／Rayon boundary and Python／native measurements provide equivalence and performance evidence. `PyBackedBytes` can borrow immutable Python `bytes`; mutable `bytearray` input is first copied into Rust-owned memory to prevent data races. Outputs still allocate new Python `bytes`, so end-to-end zero-copy and unimplemented SIMD are not claimed. Python and Rust jointly enforce fixed-width resampling integers and a maximum of 4,194,304 output samples per call, rejecting abnormal amplification before allocation. Manual and CI evidence may use `native-wheels/`; every `build.ps1` invocation uses a fresh `native-wheels-<id>/`, so an existing wheel with the same name but different contents cannot break a later build. Git ignores both locations, and neither is a Release asset. Formal Windows packages must contain and directly load `_mohan_accel`, then pass core PCM and RGBA operations. macOS／Linux build it only in core CI and do not claim equivalent Preview packaging.

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```

## 日本語

### 境界

`_mohan_accel` は墨寒の第一者 MIT ライセンス Rust＋PyO3 ネイティブモジュールです。決定的テストで照合できる CPU ホットパスだけを担当します。対象は PCM16 の倍率変換、ステレオ混合、サンプルレート変換、音声レベルと母音解析、および RGBA の alpha-over、クロスフェード、マスク付き領域合成です。Python 参照実装を動作仕様として維持し、モジュールを読み込めない場合または個別処理に失敗した場合、製品層は観測可能な診断を記録して Python へ自動的にフォールバックします。このモジュールは Qt、ネットワーク、データベース、機密情報へアクセスしません。

### 固定バージョンのビルドと検証

ツールチェーンは CPython 3.15、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2、Rayon 1.12.0 です。`Cargo.lock`、`rust-toolchain.toml`、`--locked` でビルド入力を固定します。正式手順では rustfmt、Clippy、Rust テストを実行し、`abi3t` タグを含む wheel をビルドしてインストールした後、Python／Rust の等価性および性能テストを実行します。RGBA は 262,144 pixels 以上かつ複数のワーカースレッドが利用できる場合だけ条件付きで Rayon を使用し、Rust serial／Rayon 境界と Python／native 実測により等価性と性能の証拠を得ています。`PyBackedBytes` は不変の Python `bytes` を借用できます。データ競合を避けるため、可変の `bytearray` は Rust 所有メモリへ先にコピーします。出力では新しい Python `bytes` を生成するため、エンドツーエンドのゼロコピーと未実装の SIMD は表明しません。リサンプリングでは Python／Rust 境界が固定幅整数と一回あたり最大 4,194,304 出力サンプルを共同で制限し、異常な増幅要求をメモリ割り当て前に拒否します。手動／CI 証拠は `native-wheels/` を使用できます。`build.ps1` は実行ごとに新しい `native-wheels-<id>/` を使用するため、同名で内容が異なる既存 wheel が後続ビルドを失敗させることはありません。どちらも Git の対象外であり、Release アセットにも含めません。Windows 正式パッケージは `_mohan_accel` を同梱して直接読み込み、PCM と RGBA の中核処理に合格する必要があります。macOS／Linux は中核 CI でのみビルド検証し、Preview の同等パッケージ対応を表明しません。

```powershell
python -m pip install --only-binary=:all: maturin==1.14.1
python tools/build_native_acceleration.py --output-dir native-wheels --evidence native-wheels/build-evidence.json --install
python -m pytest tests/test_native_equivalence.py tests/test_native_rgba_equivalence.py -q
```
