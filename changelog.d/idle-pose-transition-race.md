### 待機姿勢切換競爭／待机姿势切换竞争／Idle pose transition race／待機ポーズ切替の競合

- 自動待機換姿勢會等目前切換完成，避免計時器在淡入途中取代目標姿勢；語音打斷與過期回呼檢查仍保留。所有測試結果都會完成視窗與資料庫清理，並保留原始錯誤。／自动待机换姿势会等当前切换完成，避免计时器在淡入途中替换目标姿势；保留语音中断与过期回调检查。所有测试结果都会完成窗口与数据库清理，并保留原始错误。／Automatic idle pose changes defer while a pose transition is active, preventing timer requests from replacing its target mid-fade. Speech interruption and stale-callback checks remain; all test outcomes close the window and database while preserving the original error.／待機ポーズの自動変更は進行中の切替が終わるまで延期し、フェード途中のタイマーによる切替先の上書きを防ぎます。音声割り込みと古いコールバックの検証は維持し、すべてのテスト結果でウィンドウとデータベースを閉じ、元のエラーを保持します。
