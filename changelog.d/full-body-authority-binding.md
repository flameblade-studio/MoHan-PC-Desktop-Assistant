### 全身母圖來源綁定／全身母图来源绑定／Full-body authority binding／全身原画像の関連付け

- 相對母圖路徑在建立渲染器時固定，切換工作目錄後仍使用同一份參考圖。／相对母图路径在创建渲染器时固定，切换工作目录后仍使用同一份参考图。／Relative authority paths are resolved at renderer construction, keeping the same reference through later working-directory changes.／相対原画像パスを描画器の作成時に確定し、作業ディレクトリ変更後も同じ参照画像を使用します。

- 全身渲染可明確指定母圖目錄，讓補縫與臉部還原使用同一套素材；不同渲染器的母圖快取相互獨立。／全身渲染可明确指定母图目录，让补缝与脸部还原使用同一套素材；不同渲染器的母图缓存相互独立。／Full-body rendering accepts an explicit authority directory for both seam repair and face restoration, with independent caches per renderer.／全身描画では継ぎ目の補修と顔の復元に使用する原画像ディレクトリを明示でき、キャッシュは描画器ごとに独立します。
- 明確指定的母圖須具備可讀取的檔案、可解碼內容與相符尺寸；任一條件需要修正時直接報錯，來源持續綁定指定母圖。省略目錄參數時沿用既有預設行為。／明确指定的母图须具备可读取的文件、可解码内容与相符尺寸；任一条件需要修正时直接报错，来源持续绑定指定母图。省略目录参数时沿用现有默认行为。／Explicit authority images require readable files, decodable content, and matching dimensions. Any correction required raises an error while the source stays bound to that authority. Omitted directories preserve existing defaults.／明示した原画像には読み取り可能なファイル、デコード可能な内容、正しい寸法を必須とします。修正が必要な条件はエラーとして報告し、参照元は指定画像に固定します。ディレクトリ引数を省略した場合は既存の既定動作を維持します。
