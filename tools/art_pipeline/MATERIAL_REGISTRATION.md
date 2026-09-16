# 局部外觀對位／局部外观对位／Local appearance registration／局所外観位置合わせ

## 繁體中文

`material_registration.control_map(source, target, shape, boundary_width=24)`
產生反向座標映射；`shape` 是高度與寬度，控制點採 XY 座標。
`boundary_width` 預設為 0，保留既有行為。正值使整圈邊界的位移歸零，
並在指定寬度內平滑銜接。移動控制點須超過這段邊界距離；最終映射須通過折疊檢查。
以預乘 Alpha 重採樣外觀層，確認邊界及範圍外 RGBA 與來源一致，再目視審閱。
記錄來源雜湊、控制點、邊界寬度、裁切座標及任何透明補邊；原生身體保持原座標。

## 简体中文

`material_registration.control_map(source, target, shape, boundary_width=24)`
生成反向坐标映射；`shape` 是高度与宽度，控制点采用 XY 坐标。
`boundary_width` 默认为 0，保留既有行为。正值使整圈边界的位移归零，
并在指定宽度内平滑衔接。移动控制点须超过这段边界距离；最终映射须通过折叠检查。
以预乘 Alpha 重采样外观层，确认边界及范围外 RGBA 与来源一致，再进行视觉审阅。
记录来源哈希、控制点、边界宽度、裁切坐标及任何透明补边；原生身体保持原坐标。

## English

`material_registration.control_map(source, target, shape, boundary_width=24)`
returns inverse coordinate maps. `shape` is height and width; controls use XY coordinates.
The default `boundary_width` of zero preserves existing behavior. A positive value smoothly
reduces displacement to zero at every edge pixel. Moving controls must lie beyond this
transition band, and the final map must pass the fold check. Resample appearance layers
with premultiplied alpha, verify source RGBA at the boundary and outside the patch, then
review visually. Record source hashes, controls, boundary width, crop coordinates, and
any transparent padding. Keep the native body in its original coordinates.

## 日本語

`material_registration.control_map(source, target, shape, boundary_width=24)`
は逆座標マップを返します。`shape` は高さと幅、制御点は XY 座標です。
`boundary_width` の既定値 0 は既存の動作を維持します。正の値では指定幅で変位を滑らかに減らし、
境界の全画素でゼロにします。移動する制御点は遷移帯より内側に配置し、最終マップの
折り返し検証を通過させます。乗算済み Alpha で外観を再標本化し、境界と領域外の
RGBA が元画像と一致することを確認してから目視確認します。元画像のハッシュ、制御点、
境界幅、切り出し座標、透明余白を記録し、元の身体の座標を維持します。
