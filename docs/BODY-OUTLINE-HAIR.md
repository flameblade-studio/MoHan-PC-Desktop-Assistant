# 素體輪廓與髮絲淡出／素体轮廓与发丝淡出／Body outlines and hair feathering／素体輪郭と髪のぼかし

## 繁體中文

新素體可在骨架的 `*_base.png` 旁提供 `*_body_outline.png`。檔案必須是同畫布、具有 Alpha 的非空圖片，取自同一核可素體的完整外輪廓，不可從服裝或 DLC 提供。缺少時維持舊版淡出；損壞、錯誤尺寸或空輪廓會硬性失敗。

執行期使用逐列輪廓跨度填補拆層的內部空洞，以區分皮膚與桌面背景。髮絲僅在人物內部保留既有淡出，輪廓外保持原有透明度；五官核心及其 8 像素擴張仍禁止覆蓋，6 像素淡出參數不變。輪廓隨素體發布，更新後重建渲染器快取。

## 简体中文

新素体可在骨架的 `*_base.png` 旁提供 `*_body_outline.png`。文件必须是同画布、具有 Alpha 的非空图片，取自同一核可素体的完整外轮廓，不可从服装或 DLC 提供。缺少时维持旧版淡出；损坏、错误尺寸或空轮廓会硬性失败。

运行时使用逐行轮廓跨度填补拆层的内部空洞，以区分皮肤与桌面背景。发丝仅在人物内部保留既有淡出，轮廓外保持原有透明度；五官核心及其 8 像素扩张仍禁止覆盖，6 像素淡出参数不变。轮廓随素体发布，更新后重建渲染器缓存。

## English

A rebuilt rig may provide `*_body_outline.png` beside `*_base.png`. It must be a nonempty alpha image with the same canvas, derived from the complete outline of the same approved body. Clothing and DLC must not supply it. Absence retains legacy feathering; corrupt images, wrong dimensions and empty outlines fail closed.

Runtime fills internal rig cutout holes with per-row outline spans to distinguish skin from desktop background. Existing feathering remains inside the body; hair outside retains its original alpha. The feature core and its 8-pixel dilation remain forbidden, and the 6-pixel feather parameter is unchanged. Ship the outline with the body and rebuild renderer caches after updates.

## 日本語

新しい素体リグは `*_base.png` の隣に `*_body_outline.png` を配置できます。同じキャンバスでアルファを持つ空でない画像とし、同一の承認済み素体の完全な外輪郭から作成します。衣装や DLC から提供してはいけません。省略時は従来のぼかしを維持し、破損、寸法違い、空の輪郭は失敗として扱います。

実行時は行ごとの輪郭範囲でリグ内部の切り抜き穴を埋め、肌とデスクトップ背景を区別します。人物内部では既存のぼかしを維持し、輪郭外の髪は元のアルファを保持します。五官の中心と8ピクセルの拡張範囲は引き続き保護され、6ピクセルのぼかし値も変更しません。輪郭は素体と共に配布し、更新後は描画キャッシュを再構築します。
