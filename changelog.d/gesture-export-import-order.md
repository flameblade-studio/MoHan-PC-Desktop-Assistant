### 修正手勢匯出的載入順序／修正手势导出的加载顺序／Fix gesture export import order／ジェスチャー公開項目の読み込み順序を修正

- 手勢設定儲存介面的公開型別與匯入匯出函式保持為實際物件，避免先建立主程式服務後暴露未解析的延遲匯入。／手势设置存储接口的公开类型与导入导出函数保持为实际对象，避免先建立主程序服务后暴露未解析的延迟导入。／Keep the gesture store's public types and import/export functions concrete after the presentation composition root loads them.／メインサービスを先に構築した場合も、ジェスチャー設定ストアの公開型と入出力関数を実際のオブジェクトとして保持します。
