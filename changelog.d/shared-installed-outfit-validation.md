### 共用已安裝外觀包驗證／共用已安装外观包验证／Shared installed outfit validation／インストール済み外観パック検証の共有

- 新增同一顯示實例暖切換兩個已安裝封包的整合測試，確認目前選擇與來源像素更新，封包內容保持不變。／新增同一显示实例暖切换两个已安装封包的集成测试，确认当前选择与来源像素更新，封包内容保持不变。／A warm-switch integration test verifies that one overlay changes its selection and rendered pixels between two installed packs while preserving both archives.／同じ表示インスタンスで二つのインストール済みパックを切り替え、選択と描画ピクセルの更新、および両アーカイブの不変性を検証します。

- 外觀選單與顯示端共用既有封包驗證快取，切換姿勢時降低重複解碼；封包時間或大小變動仍觸發驗證，完整且相容的封包才進入使用流程。／外观菜单与显示端共用现有封包验证缓存，切换姿势时降低重复解码；封包时间或大小变化时仍触发验证，完整且兼容的封包才进入使用流程。／Appearance selection and rendering share the existing validated archive cache to reduce duplicate decoding during pose changes. Timestamp or size changes still trigger validation, and only intact compatible archives enter use.／外観選択と描画で既存の検証済みアーカイブキャッシュを共有し、ポーズ変更時の重複デコードを削減します。更新時刻やサイズの変更時は再検証し、完全で互換性のあるパックだけを使用します。

- 全身眨眼測試直接從定義模組載入圖層順序，修正首次執行時讀到未解析延後載入物件的錯誤。／全身眨眼测试直接从定义模块加载图层顺序，修复首次执行时读取到未解析延迟加载对象的问题。／The full-body blink test imports layer order from its defining module, fixing unresolved lazy-import access on its first execution.／全身瞬きテストはレイヤー順序を定義元から直接インポートし、初回実行時の未解決遅延インポート参照を修正します。
