### 完成炎劍鑄魂模組邊界歸零／完成炎剑铸魂模块边界归零／Complete the Soulforge module-boundary cleanup／炎剣鋳魂のモジュール境界整理を完了

- 消除最後 18 組引擎對墨寒產品殼依賴，並將 51 個待拆模組全部依實際責任分類／消除最后 18 组引擎对墨寒产品壳依赖，并将 51 个待拆模块全部按实际职责分类／Remove the final 18 engine-to-MoHan-shell dependencies and classify all 51 pending modules by actual responsibility／最後の 18 組のエンジンから墨寒製品シェルへの依存を解消し、分割待ち 51 モジュールを実際の責任で分類
- 角色資料改由活動角色來源供應，保留既有公開介面、畫面、行為與設定位置／角色数据改由活动角色来源提供，保留现有公开接口、画面、行为与设置位置／Serve character data from the active character source while preserving public interfaces, visuals, behavior, and settings locations／キャラクターデータをアクティブなキャラクターソースから提供し、公開インターフェース、表示、動作、設定位置を維持
- 獨立工具與 CI 入口會先明確啟用內建角色執行期，角色中立模組可在啟用前安全匯入／独立工具与 CI 入口会先明确启用内置角色运行时，角色中立模块可在启用前安全导入／Standalone tools and CI entry points explicitly activate the bundled character runtime, while character-neutral modules import safely before activation／独立ツールと CI エントリーポイントは同梱キャラクターランタイムを明示的に有効化し、キャラクター中立モジュールは有効化前でも安全にインポート可能
