### 本機與 CI 鎖定相同 Qt wheel／本地与 CI 锁定相同 Qt wheel／Lock identical Qt wheels locally and in CI／ローカルと CI で同一 Qt wheel を固定

- 新增可重跑的同 CI 建置入口、wheel 雜湊與型別檔一致性閘門，並在 cargo-audit 缺少時提供固定版本安裝指令且維持失敗／新增可重复运行的同 CI 构建入口、wheel 哈希与类型文件一致性门禁，并在 cargo-audit 缺失时提供固定版本安装命令且保持失败／Add a repeatable CI-equivalent build entry point, wheel hash and typing-file parity gate, and a pinned cargo-audit install command while preserving failure when absent／再実行可能な CI 同等ビルド入口、wheel hash と型ファイルの一致ゲートを追加し、cargo-audit がない場合は固定版の導入コマンドを示して失敗を維持
