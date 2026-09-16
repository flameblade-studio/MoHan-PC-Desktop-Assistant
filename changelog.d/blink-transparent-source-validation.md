### 眨眼透明來源檢查／眨眼透明来源检查／Validate transparent blink sources／まばたき画像の透明度検証

- 全身眨眼素材載入時，解碼並要求 8 位元 RGBA 與透明背景，通過格式、透明度及解碼檢查後才進入角色合成。沿用既有 OpenCV 相依套件。／全身眨眼素材加载时，解码并要求 8 位 RGBA 与透明背景，通过格式、透明度及解码检查后才进入角色合成。沿用现有 OpenCV 依赖。／Decode full-body blink sources and require 8-bit RGBA with a transparent background. Admit frames to character composition only after format, transparency, and decoding checks pass. Uses the existing OpenCV dependency.／全身まばたき素材をデコードし、8 ビット RGBA と透明背景を必須とします。形式・透明度・デコードの検証に合格した画像だけをキャラクター合成へ渡します。既存の OpenCV 依存関係を使用します。
