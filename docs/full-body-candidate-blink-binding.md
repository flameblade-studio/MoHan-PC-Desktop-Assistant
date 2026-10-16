# 全身候選眨眼來源綁定／全身候选眨眼来源绑定／Full-body candidate blink source binding／全身候補まばたきソースのバインディング

## 繁體中文

這份契約適用範圍限定為明確指定 `LayeredFullBodyRenderer(authority_root=...)` 的 candidate authority 路徑。當某個 `LayeredFullBodyView` 的 `blink_frames` 非空時，authority_root 下必須有：

```text
<authority_root>/<view_id>.blink-binding.json
```

新 receipt 使用 `mohan.candidate-blink-binding.v2`、整數 `version: 2`，列出同一個 view 的 authority source、`half` 與 `closed` 三個 PNG。三個 `path` 都以 `authority_root.parent` 為基準，採用正斜線的相對路徑，例如 `v5-base/<view_id>.png` 與 `v5-base-layered/<view_id>_blink_half.png`。路徑須維持在該 atlas 根目錄內；磁碟代號、反斜線、`..` 與非標準化路徑均會被拒絕。解析後的來源必須等於 `<authority_root>/<view_id>.png`，兩個眨眼來源必須各自等於 `view.blink_frames` 指定的檔案。SHA256 仍以 PNG 原始位元組計算。既有 `mohan.candidate-blink-binding.v1`／整數 `version: 1` 保留原本的絕對路徑契約；schema 與 version 必須配對。遷移只更新 receipt 的 schema、version 與路徑，保留三個 PNG 及其雜湊，並在新位置重新驗證綁定。

三個檔案的寬高必須完全等於 receipt 的 `canvas`。source 必須能解碼為 8-bit RGB 或 RGBA PNG；兩個 blink overlay 必須是 8-bit RGBA，並且至少含一個完全透明像素。Renderer 建構只接受 receipt 與 pair 完整、schema/version/view/path/SHA 正確、檔案可用、解碼成功、畫布一致且透明格式正確的組合；explicit candidate 以這份 binding 為唯一眨眼來源。

建構 renderer 時會各讀取、雜湊並解碼三個 PNG 一次，將通過驗證的 bytes 綁在當次 renderer。現有 renderer 持續使用建構時綁定的 bytes；QPixmap cache 淘汰時同樣從已綁定的記憶體 bytes 解碼。若 candidate source、blink 檔或 receipt 更新，必須重建 renderer，讓新 binding 在下一次建構重新驗證。

正式／legacy default renderer 在省略 `authority_root` 時沿用既有 manifest v1 的檔名解析、缺 pair 行為與 authored blink fallback，歷史 receipt 要求維持關閉。Explicit view 在省略 `blink_frames` 時同樣沿用既有流程；提供 blink 時以完整 pair 作為載入條件。

SHA/path、格式與畫布驗證證明這三個 bytes 檔案在建構當下可追溯且互相配對。人物身分、臉型、神韻、髮飾、美術品質、來源授權與 owner 視覺核准仍各自需要正式驗收；候選經這些驗收後才可升為正式素材。

完整格式見 [JSON 範例](examples/full-body-blink-binding.json)；路徑與雜湊均為示意。省略預先傳入的 manifest 時，驗證會在首次載入 manifest、繪製前完成。

省略眨眼影格的明確指定視角，仍會在載入 manifest 時讀取並固定原圖 PNG 位元組，且載入條件要求原圖存在並可完整解碼。此時眨眼 receipt 要求維持關閉；身分與美術驗收仍須另行完成。

## 简体中文

本契约的适用范围限定为明确指定 `LayeredFullBodyRenderer(authority_root=...)` 的 candidate authority 路径。当某个 `LayeredFullBodyView` 的 `blink_frames` 非空时，authority_root 下必须存在：

```text
<authority_root>/<view_id>.blink-binding.json
```

新 receipt 使用 `mohan.candidate-blink-binding.v2`、整数 `version: 2`，列出同一个 view 的 authority source、`half` 与 `closed` 三个 PNG。三个 `path` 都以 `authority_root.parent` 为基准，采用正斜线的相对路径，例如 `v5-base/<view_id>.png` 与 `v5-base-layered/<view_id>_blink_half.png`。路径须保持在该 atlas 根目录内；盘符、反斜线、`..` 与非规范化路径均会被拒绝。解析后的来源必须等于 `<authority_root>/<view_id>.png`，两个眨眼来源必须各自等于 `view.blink_frames` 指定的文件。SHA256 仍以 PNG 原始字节计算。现有 `mohan.candidate-blink-binding.v1`／整数 `version: 1` 保留原本的绝对路径契约；schema 与 version 必须配对。迁移只更新 receipt 的 schema、version 与路径，保留三个 PNG 及其哈希，并在新位置重新验证绑定。

三个文件的宽高必须完全等于 receipt 的 `canvas`。source 必须能解码为 8-bit RGB 或 RGBA PNG；两个 blink overlay 必须是 8-bit RGBA，并且至少包含一个完全透明像素。Renderer 构建只接受 receipt 与 pair 完整、schema/version/view/path/SHA 正确、文件可用、解码成功、画布一致且透明格式正确的组合；explicit candidate 以这份 binding 为唯一眨眼来源。

构建 renderer 时会各读取、哈希并解码三个 PNG 一次，将通过验证的 bytes 绑定到当前 renderer。现有 renderer 持续使用构建时绑定的 bytes；QPixmap cache 淘汰时同样从已绑定的内存 bytes 解码。candidate source、blink 文件或 receipt 更新后，必须重建 renderer，让新 binding 在下一次构建重新验证。

正式／legacy default renderer 在省略 `authority_root` 时沿用现有 manifest v1 的文件名解析、缺 pair 行为与 authored blink fallback，历史 receipt 要求维持关闭。Explicit view 在省略 `blink_frames` 时同样沿用现有流程；提供 blink 时以完整 pair 作为加载条件。

SHA/path、格式与画布验证证明这三个 bytes 文件在构建当下可追溯并且互相配对。人物身份、脸型、神韵、发饰、美术质量、来源授权与 owner 视觉批准仍各自需要正式验收；候选通过这些验收后才可升为正式素材。

完整格式见 [JSON 示例](examples/full-body-blink-binding.json)；路径与哈希均为示意。省略预先传入的 manifest 时，验证会在首次加载 manifest、绘制前完成。

省略眨眼帧的明确指定视角，仍会在加载 manifest 时读取并固定原图 PNG 字节，且加载条件要求原图存在并可完整解码。此时眨眼 receipt 要求维持关闭；身份与美术验收仍须另行完成。

## English

This contract's scope is the candidate-authority path that explicitly selects `LayeredFullBodyRenderer(authority_root=...)`. When a `LayeredFullBodyView` has non-empty `blink_frames`, the authority root must contain:

```text
<authority_root>/<view_id>.blink-binding.json
```

New receipts use `mohan.candidate-blink-binding.v2` with integer `version: 2` and name the authority source, `half`, and `closed` PNGs for one view. Each `path` is relative to `authority_root.parent`, uses forward slashes, and stays within that atlas root; examples are `v5-base/<view_id>.png` and `v5-base-layered/<view_id>_blink_half.png`. Drive prefixes, backslashes, `..`, and noncanonical paths are rejected. The resolved source must equal `<authority_root>/<view_id>.png`, and each blink path must equal its corresponding `view.blink_frames` entry. SHA256 continues to cover original PNG bytes. Existing `mohan.candidate-blink-binding.v1` with integer `version: 1` retains its absolute-path contract; schema and version must match. Migration changes only the receipt schema, version, and paths, preserving all three PNGs and their hashes, then validates the binding at its new location.

All three files must have the exact dimensions declared by `canvas`. The source must decode as an 8-bit RGB or RGBA PNG. Both blink overlays must be 8-bit RGBA and contain at least one fully transparent pixel. Renderer construction accepts a complete receipt and pair with valid schema/version/view/path/SHA, available and decodable files, matching canvases, and valid transparency. The binding is the explicit candidate's sole blink source.

Renderer construction reads, hashes, and decodes each of the three PNGs once, then binds the verified bytes to that renderer instance. The existing renderer continues using the bytes bound at construction. An evicted QPixmap cache entry is likewise decoded from those bound in-memory bytes. When candidate source, blink files, or the receipt changes, rebuild the renderer so the next construction verifies the new binding.

A formal or legacy default renderer that omits `authority_root` retains existing manifest v1 filename resolution, missing-pair behavior, and authored-blink fallback, with the historical-receipt requirement disabled. An explicit view that omits `blink_frames` follows the same established path; when blink frames are provided, a complete pair is the loading condition.

SHA/path, format, and canvas checks prove that these three byte files were traceable and paired at construction time. Identity, facial likeness, expression, hair ornaments, artistic quality, licensing, and owner visual approval each remain subject to formal acceptance; a candidate becomes a formal asset after those gates pass.

See the [JSON example](examples/full-body-blink-binding.json) for the complete format; paths and hashes are illustrative. When the caller omits a supplied manifest, verification occurs when the manifest is first loaded, before drawing.

Explicit views that omit blink frames still read and freeze the source PNG bytes when the manifest loads; loading requires an available, decodable source. The blink-receipt requirement remains disabled in this case, while identity and art acceptance remain separate required gates.

## 日本語

この契約の適用範囲は、候補の authority を使うために `LayeredFullBodyRenderer(authority_root=...)` を明示的に指定した経路です。`LayeredFullBodyView` の `blink_frames` が空でない場合、authority root には次の receipt が必要です。

```text
<authority_root>/<view_id>.blink-binding.json
```

新しい receipt は `mohan.candidate-blink-binding.v2` と整数の `version: 2` を使用し、同じ view の authority source、`half`、`closed` の PNG を列挙します。各 `path` は `authority_root.parent` を基準とするスラッシュ区切りの相対パスで、atlas ルート内に収めます。例は `v5-base/<view_id>.png` と `v5-base-layered/<view_id>_blink_half.png` です。ドライブ指定、バックスラッシュ、`..`、非正規化パスは拒否します。解決後のソースは `<authority_root>/<view_id>.png`、各まばたきパスは対応する `view.blink_frames` のファイルと一致する必要があります。SHA256 は PNG の元のバイト列から計算します。既存の `mohan.candidate-blink-binding.v1` と整数の `version: 1` は絶対パス契約を維持し、schema と version の組み合わせを検証します。移行では receipt の schema、version、パスだけを更新し、3 つの PNG とハッシュを維持したうえで、移動先のバインディングを再検証します。

3 ファイルの幅と高さは receipt の `canvas` と完全に一致しなければなりません。source は 8-bit RGB または RGBA PNG としてデコードできる必要があります。2 つの blink overlay は 8-bit RGBA で、少なくとも 1 ピクセルが完全透明でなければなりません。Renderer 構築が受け入れるのは、receipt と pair が揃い、schema/version/view/path/SHA が正しく、ファイルを利用・デコードでき、キャンバスと透明形式が一致する組み合わせです。この binding が明示的な候補の唯一のまばたきソースです。

Renderer の構築時に 3 つの PNG をそれぞれ一度だけ読み取り、ハッシュし、デコードして、その bytes を当該 renderer に固定します。既存 renderer は構築時に固定した bytes を継続して使用します。QPixmap cache が破棄された場合も、固定済みのメモリ bytes からデコードします。candidate source、blink ファイル、または receipt を更新した場合は renderer を再構築し、次の構築時に新しい binding を検証します。

`authority_root` を省略した formal／legacy default renderer は、既存の manifest v1 のファイル名解決、pair 欠落時の動作、authored blink fallback を維持し、過去の receipt 要件を無効のまま保ちます。`blink_frames` を省略した explicit view も既存経路を使い、blink を指定する場合は完全な pair を読み込み条件とします。

SHA/path、形式、キャンバスの検証は、構築時点で 3 つの byte ファイルを追跡でき、相互に対応していることを証明します。人物の同一性、顔立ち、表情、髪飾り、芸術的品質、ライセンス、owner の視覚承認は、それぞれ正式な承認対象です。候補はこれらの関門を通過した後に正式素材へ昇格できます。

完全な形式は [JSON の例](examples/full-body-blink-binding.json) を参照してください。パスとハッシュは説明用です。manifest を省略した場合は、初回の manifest 読み込み時に、描画前の検証を行います。

まばたきフレームを省略した明示的な視点でも、manifest の読み込み時に元の PNG バイト列を読み取り、固定し、利用可能で正常にデコードできる元画像を読み込み条件とします。この場合、まばたき receipt の要件は無効のままです。人物の同一性と美術的な承認は別の必須関門として残ります。
