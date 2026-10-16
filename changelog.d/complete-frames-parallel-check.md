### 完整幀並行檢查／完整帧并行检查／Parallel complete-frame checks／完全フレームの並列検査

- 完整幀的畫布與透明度檢查改由可釋放 GIL 的 Pillow 並行執行，300 張幀的首次載入由約 9.5 秒降至約 2 秒；檢查內容不變。／完整帧的画布与透明度检查改由可释放 GIL 的 Pillow 并行执行，300 张帧的首次加载由约 9.5 秒降至约 2 秒；检查内容不变。／Complete-frame canvas and transparency checks now run in parallel with Pillow, which releases the GIL, cutting the first load of 300 frames from about 9.5 s to about 2 s with unchanged checks.／完全フレームのキャンバスと透明度の検査を GIL を解放する Pillow で並列実行し、300 枚の初回読み込みを約 9.5 秒から約 2 秒に短縮しました。検査内容は変わりません。
