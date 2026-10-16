# 素體輪廓與髮絲淡出／素体轮廓与发丝淡出／Body outlines and hair feathering／素体輪郭と髪のぼかし

## 繁體中文

新素體可在骨架的 `*_base.png` 旁提供 `*_body_outline.png`。檔案必須是同畫布、具有 Alpha 的非空圖片，來源固定為同一核可素體的完整外輪廓，並由核心素體提供。省略時維持舊版淡出；載入器只接受完整、尺寸正確且含內容的輪廓。

執行期使用逐列輪廓跨度填補拆層的內部空洞，以區分皮膚與桌面背景。髮絲的既有淡出範圍限定於人物內部，輪廓外保持原有透明度；五官核心及其 8 像素擴張持續受到覆蓋保護，6 像素淡出參數維持原值。輪廓隨素體發布，更新後重建渲染器快取。

## 简体中文

新素体可在骨架的 `*_base.png` 旁提供 `*_body_outline.png`。文件必须是同画布、具有 Alpha 的非空图片，来源固定为同一核可素体的完整外轮廓，并由核心素体提供。省略时维持旧版淡出；加载器只接受完整、尺寸正确且包含内容的轮廓。

运行时使用逐行轮廓跨度填补拆层的内部空洞，以区分皮肤与桌面背景。发丝仅在人物内部保留既有淡出，轮廓外保持原有透明度；五官核心及其 8 像素扩张持续受到覆盖保护，6 像素淡出参数维持原值。轮廓随素体发布，更新后重建渲染器缓存。

## English

A rebuilt rig may provide `*_body_outline.png` beside `*_base.png`. It must be a nonempty alpha image with the same canvas, derived from the complete outline of the same approved body and supplied by the core body. Omission retains legacy feathering; the loader accepts complete, correctly sized outlines with content.

Runtime fills internal rig cutout holes with per-row outline spans to distinguish skin from desktop background. Existing feathering remains inside the body; hair outside retains its original alpha. The feature core and its 8-pixel dilation remain protected from coverage, and the 6-pixel feather parameter retains its established value. Ship the outline with the body and rebuild renderer caches after updates.

## 日本語

新しい素体リグは `*_base.png` の隣に `*_body_outline.png` を配置できます。同じキャンバスでアルファを持つ空でない画像とし、同一の承認済み素体の完全な外輪郭から作成し、コア素体から提供します。省略時は従来のぼかしを維持し、ローダーは完全で寸法が正しく内容を持つ輪郭を受け入れます。

実行時は行ごとの輪郭範囲でリグ内部の切り抜き穴を埋め、肌とデスクトップ背景を区別します。人物内部では既存のぼかしを維持し、輪郭外の髪は元のアルファを保持します。五官の中心と8ピクセルの拡張範囲は引き続き保護され、6ピクセルのぼかし値も従来値を維持します。輪郭は素体と共に配布し、更新後は描画キャッシュを再構築します。
