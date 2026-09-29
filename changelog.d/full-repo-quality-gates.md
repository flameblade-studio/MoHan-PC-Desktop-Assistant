### 啟用全庫品質閘門／启用全库质量闸门／Enable full-repository quality gates／全リポジトリ品質ゲートを有効化

- 新增單一正式入口，依序執行語法、靜態分析、型別、相依、授權、架構、死碼、文件、安全與完整測試檢查／新增单一正式入口，依次执行语法、静态分析、类型、依赖、许可证、架构、死代码、文档、安全与完整测试检查／Add one formal entry point for ordered syntax, static analysis, typing, dependency, license, architecture, dead-code, documentation, security, and full-test checks／構文、静的解析、型、依存関係、ライセンス、アーキテクチャ、デッドコード、文書、安全性、全テストを順番に実行する単一の正式入口を追加
- 測試執行器新增跑完後彙總失敗的模式，既有預設仍在第一個失敗時安全停止／测试执行器新增运行完毕后汇总失败的模式，现有默认仍在首个失败时安全停止／Add an aggregate-failure test mode while preserving the existing fail-fast default／既存の早期失敗終了を維持しつつ、全実行後に失敗を集計するテストモードを追加
