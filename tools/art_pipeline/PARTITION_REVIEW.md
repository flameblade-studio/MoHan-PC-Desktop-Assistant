# 單一原圖分層預覽／单一原图分层预览／Single-source layer review／単一原画のレイヤーレビュー

## 繁體中文

`partition_layers` 從同一張核可原圖與同尺寸的分區圖，產生頭髮、髮飾、露出皮膚及衣服四個可見表面圖層。所有顏色與透明度來自原圖的既有去背流程，分區圖只決定像素歸屬。它不混合不同重繪階段，不貼回另一張圖的五官，也不依衣服顏色判定髮型。

分區圖使用黑色背景、紅色頭髮、綠色髮飾、藍色皮膚與黃色衣服。抗鋸齒混色邊緣以鄰近純色種子分配；原圖輪廓只容許最多 3 像素的分區漏邊，超過即拒絕。工具拒絕覆寫輸出目錄，並記錄輸入與輸出 SHA-256、像素數及重組差異。

**這是外觀檢視工具，不是可直接安裝的外觀包。** 可見表面分割不會補出頭飾後的頭髮、髮束後的衣服或其他遮住的區域。單張重組一致也不能證明圖層可獨立替換、符合現行素體身分或適用表情動畫。須先讓擁有者確認外觀，再處理遮擋、執行期接線與回歸測試；不得用預覽結果宣稱正式包已修復。

```powershell
python -m tools.art_pipeline.partition_layers approved.png semantic-mask.png review-output
```

## 简体中文

`partition_layers` 从同一张核可原图与同尺寸的分区图，生成头发、发饰、露出皮肤及衣服四个可见表面图层。所有颜色与透明度来自原图的既有去背景流程，分区图只决定像素归属。它不混合不同重绘阶段，不贴回另一张图的五官，也不依衣服颜色判定发型。

分区图使用黑色背景、红色头发、绿色发饰、蓝色皮肤与黄色衣服。抗锯齿混色边缘以邻近纯色种子分配；原图轮廓只允许最多 3 像素的分区漏边，超过即拒绝。工具拒绝覆盖输出目录，并记录输入与输出 SHA-256、像素数及重组差异。

**这是外观检查工具，不是可直接安装的外观包。** 可见表面分割不会补出头饰后的头发、发束后的衣服或其他遮住的区域。单张重组一致也不能证明图层可独立替换、符合现行素体身份或适用表情动画。须先让拥有者确认外观，再处理遮挡、运行时接线与回归测试；不得用预览结果宣称正式包已修复。

```powershell
python -m tools.art_pipeline.partition_layers approved.png semantic-mask.png review-output
```

## English

`partition_layers` uses one approved source and a same-sized semantic map to produce four visible-surface layers: hair, headwear, exposed skin, and garment. All colors and alpha come from the existing source keying procedure; the map assigns ownership only. It does not mix redraw stages, paste facial features from another image, or identify hair from garment colors.

The map uses black background, red hair, green headwear, blue skin, and yellow garment. Antialiased mixed boundaries inherit nearby pure-color seeds. Missing source silhouette edges may extend at most 3 pixels; larger omissions are rejected. The tool refuses to overwrite its output directory and records input/output SHA-256, pixel counts, and reconstruction differences.

**This is a visual review tool, not an installable outfit pack.** Visible-surface partitioning does not recover hair behind ornaments, garment behind hair, or other occluded surfaces. Exact single-image reconstruction does not establish independent layer replacement, compatibility with the current body identity, or expression animation support. Obtain the owner's visual approval before occlusion work, runtime integration, and regression tests. Never describe this preview as a repaired production pack.

```powershell
python -m tools.art_pipeline.partition_layers approved.png semantic-mask.png review-output
```

## 日本語

`partition_layers` は承認済みの単一原画と同寸法の領域マップから、髪、髪飾り、露出した肌、衣服の可視表面を4つのレイヤーに分割します。色と透明度は既存の背景除去処理による原画から取得し、マップは画素の所属だけを決めます。異なる描き直し段階の混合、別画像からの顔の貼り戻し、衣服の色による髪の判定は行いません。

マップは背景を黒、髪を赤、髪飾りを緑、肌を青、衣服を黄で示します。アンチエイリアスの混色境界は近傍の純色を継承します。原画輪郭の領域欠落は最大3画素までとし、それを超える場合は拒否します。出力先の上書きを拒否し、入出力のSHA-256、画素数、再構成差分を記録します。

**これは外観確認用のツールであり、インストール可能な外観パックではありません。** 可視表面の分割では、飾りの後ろの髪、髪の後ろの衣服などの隠れた部分は復元されません。単一画像の完全一致だけでは、独立したレイヤー交換、現行素体の同一性との互換性、表情アニメーションへの対応を証明できません。所有者の外観承認後に遮蔽処理、実行時の統合、回帰テストを進めてください。このプレビューを正式パックの修復完了として報告してはいけません。

```powershell
python -m tools.art_pipeline.partition_layers approved.png semantic-mask.png review-output
```
