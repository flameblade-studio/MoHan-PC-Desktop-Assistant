### 語音關窗回呼生命週期修復／语音关窗回调生命周期修复／Fix speech callback lifetime during shutdown／音声コールバックの終了時ライフサイクルを修正

- 關閉墨寒視窗時使延遲語音完成回呼失效，讓資料庫關閉後晚到回呼維持無資料庫存取權。／关闭墨寒窗口时使延迟语音完成回调失效，让数据库关闭后迟到回调维持无数据库访问权。／Invalidate delayed speech completion callbacks when the MoHan window closes; late callbacks retain no database access after closure.／墨寒ウィンドウの終了時に遅延音声完了コールバックを無効化し、データベースの終了後も遅延コールバックにデータベースへのアクセス権を与えません。
