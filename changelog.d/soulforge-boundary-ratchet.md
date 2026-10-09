### 建立鑄魂引擎邊界棘輪／建立铸魂引擎边界棘轮／Establish the Soulforge engine boundary ratchet／Soulforge エンジン境界ラチェットを確立

- 新增逐模組邊界清冊與匯入棘輪，既有產品殼依賴只准減少且新增違規會使測試失敗／新增逐模块边界清单与导入棘轮，现有产品壳依赖只准减少且新增违规会使测试失败／Add a per-module boundary inventory and import ratchet so existing product-shell dependencies may only decrease and new violations fail tests／モジュール単位の境界台帳とインポートラチェットを追加し、既存の製品シェル依存は減少のみを許可して新規違反をテスト失敗にします
- 分離角色中立通用常數並將 companion 服務型別邊界改為窄介面，維持既有公開介面、資料位置與執行行為／分离角色中立通用常数并将 companion 服务类型边界改为窄接口，保持现有公开接口、数据位置与运行行为／Separate character-neutral constants and replace the companion service type dependency with a narrow interface while preserving public interfaces, data locations, and runtime behavior／キャラクター中立の共通定数を分離し、companion サービスの型依存を狭いインターフェースへ置き換え、既存の公開インターフェース、データ位置、実行動作を維持します
