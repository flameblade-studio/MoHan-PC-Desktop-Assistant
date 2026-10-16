### 產線匯入契約／产线导入契约／Pipeline import contract／パイプラインのインポート契約

- 分層、授權檢查及新增回歸測試遵循 Python 3.15 延遲匯入規則；外觀包既有例外型別的相容匯出保持直接匯入，內部驗證函式分開載入。／分层、授权检查及新增回归测试遵循 Python 3.15 延迟导入规则；外观包既有异常类型的兼容导出保持直接导入，内部验证函数分开加载。／Partition tools, license checks, and added regression tests follow Python 3.15 lazy imports. Existing outfit exception re-exports remain eager, with internal validation functions imported separately.／分割ツール、ライセンス検査、追加回帰テストに Python 3.15 の遅延インポート規則を適用します。既存の衣装例外型の再エクスポートは即時読み込みを維持し、内部検証関数を分離します。
