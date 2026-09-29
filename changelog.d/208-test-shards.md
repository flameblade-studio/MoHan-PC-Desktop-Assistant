### 平衡分片完整測試並保留既有必過檢查／均衡分片完整测试并保留现有必需检查／Balance full-test shards while preserving required checks／必須チェックを維持して完全テストを均衡分割

- Windows CI 將靜態閘門執行一次，再依歷史耗時平行執行八個完整測試分片，最後由原名 test 的工作彙總結果／Windows CI 只运行一次静态关卡，再按历史耗时并行运行八个完整测试分片，最后由原名 test 的作业汇总结果／Windows CI runs the static gate once, executes eight duration-balanced full-test shards in parallel, and aggregates them in the existing test job／Windows CI は静的ゲートを一度実行し、履歴時間で均衡化した八つの完全テスト分片を並列実行して、既存名の test ジョブで集約します
- 本機品質閘門可分開執行靜態與測試階段，測試執行器可列出分片並更新版控耗時表／本地质量关卡可分别运行静态与测试阶段，测试运行器可列出分片并更新版本控制内的耗时表／The local quality gate can run static and test stages separately, while the test runner can list shards and refresh the versioned timing table／ローカル品質ゲートは静的段階とテスト段階を分けて実行でき、テストランナーは分片一覧と版管理された時間表の更新に対応します
