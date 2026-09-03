# PoseAtlas v5-base 分層暫存素材／PoseAtlas v5-base 分层暂存素材／PoseAtlas v5-base layered assets, staged／PoseAtlas v5-base レイヤー分割の暫定素材

## 繁體中文

`assets/pose-atlas/v5-base-layered/` 收錄以 `v5-base` 為權威、由 golden 建置器切出的 24 視角 × 25 層共 600 個圖層：袖層依素體無袖宣告為空、像素交還身體層，背面視角的臉部層依契約留空。`layer_manifest.json` 與 `mouth_authority_manifest.json` 由同一組稽核工具在這個路徑重算；整組語意稽核 0 問題，layer-pack 只有每視角一個已知的 C 級 `neutral_teeth_empty`，臉部層不對稱 0。2026-09-02 起執行期、封裝與稽核工具預設皆載入本目錄（目錄名只在 `domain/constants.py` 的 `POSE_ATLAS_LAYERED_ROOT_NAME` 定義一次），渲染器的權威回貼也同步改讀 `v5-base`。袖層依無袖素體刻意近乎全空，因此 `sleeve_left`／`sleeve_right` 的袖口抬升動作在畫面上等於沒有動作。

## 简体中文

`assets/pose-atlas/v5-base-layered/` 收录以 `v5-base` 为权威、由 golden 构建器切出的 24 视角 × 25 层共 600 个图层：袖层依素体无袖声明为空、像素交还身体层，背面视角的脸部层依契约留空。`layer_manifest.json` 与 `mouth_authority_manifest.json` 由同一组审计工具在这个路径重算；整组语义审计 0 问题，layer-pack 只有每视角一个已知的 C 级 `neutral_teeth_empty`，脸部层不对称 0。2026-09-02 起运行时、封装与审计工具默认皆加载本目录（目录名只在 `domain/constants.py` 的 `POSE_ATLAS_LAYERED_ROOT_NAME` 定义一次），渲染器的权威回贴也同步改读 `v5-base`。袖层依无袖素体刻意近乎全空，因此 `sleeve_left`／`sleeve_right` 的袖口抬升动作在画面上等于没有动作。

## English

`assets/pose-atlas/v5-base-layered/` holds the 600 layers (24 views × 25 layers) cut by the golden builder with `v5-base` as the authority: the sleeve layers are declared empty because the body is sleeveless and their pixels return to the body layer, and the face layers of rear views stay empty by contract. `layer_manifest.json` and `mouth_authority_manifest.json` were recomputed at this path by the same audit tools; the whole set has 0 semantic issues, the layer-pack audit reports only the one known class-C `neutral_teeth_empty` per view, and face-layer asymmetry is 0. Since 2026-09-02 the runtime, packaging, and the audit-tool defaults all load this directory (its name is defined once, as `POSE_ATLAS_LAYERED_ROOT_NAME` in `domain/constants.py`), and the renderer's authority repaint reads `v5-base` in step. The sleeve layers are intentionally near-empty for the sleeveless body, so the `sleeve_left` / `sleeve_right` cuff-lift motion is a visual no-op.

## 日本語

`assets/pose-atlas/v5-base-layered/` には `v5-base` を権威として golden ビルダーで切り出した 24 視角 × 25 層、計 600 のレイヤーを収録します。袖レイヤーは素体が袖なしであるため空と宣言され、その画素は身体レイヤーへ戻り、背面視角の顔レイヤーは契約どおり空のままです。`layer_manifest.json` と `mouth_authority_manifest.json` は同じ監査ツール群でこのパスに対して再計算しました。全体で意味論監査は 0 件、layer-pack 監査は各視角に既知のクラス C `neutral_teeth_empty` が一つあるだけで、顔レイヤーの非対称は 0 件です。2026-09-02 以降、実行時・パッケージング・監査ツールの既定はすべて本ディレクトリを読み込み（ディレクトリ名は `domain/constants.py` の `POSE_ATLAS_LAYERED_ROOT_NAME` で一度だけ定義）、レンダラーの権威再描画も同時に `v5-base` を参照します。袖レイヤーは袖なし素体のため意図的にほぼ空であり、`sleeve_left`／`sleeve_right` の袖口リフト動作は画面上では何も動きません。
