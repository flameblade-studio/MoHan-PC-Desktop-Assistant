# 墨寒架構／墨寒架构／MoHan Architecture／墨寒アーキテクチャ

## 繁體中文

本文件是人類貢獻者與 Codex 共同遵守的維護契約。

### 依賴方向

依賴只能向下指向：

1. `app.py` 是 Windows 角色外殼；`service_container.py` 是明確的執行期組裝根。`preview_app.py` 則是獨立且刻意受限的 macOS／Linux 預覽封裝外殼；它可以顯示平台狀態與在地化內容，但不得匯入 `app.py`、建立雲端／語音／工具服務，或顯示機密輸入欄位。
2. UI 模組（`flagship_ui.py`、`profile_transfer_ui.py`）可以呼叫服務的公開 API。
3. 服務（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）可以使用領域與儲存模組。
4. 領域與儲存模組（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）絕不匯入 UI 或 `app.py`。

禁止本機模組循環匯入，並由 `tests/test_architecture_contracts.py` 強制檢查。

### 功能邊界

- 儀表板分頁透過 `DashboardFeatureRegistry` 掛載。新增分頁只應變更組裝清單，不得變更無關分頁。
- 跨視窗呼叫必須使用公開方法或 Qt signal。`CompanionWindow` 絕不得呼叫私有的 `Dashboard._method`。
- 可替換的語音、Realtime、機密儲存與監聽器依賴，由 `contracts.py` 內小型的 `typing.Protocol` 連接埠描述，並透過 `CompanionServices` 注入 `CompanionWindow`。
- 桌面作業系統行為必須透過 `PlatformServicePort`，以及明確的 `platform_windows.py`、`platform_macos.py`、`platform_linux.py` 介接器進入。核心模組不得無條件匯入 `winreg`、`winsound`、`ctypes.windll` 或 `os.startfile`。
- 桌面依賴注入以建構式為基礎。FastAPI 的 `Depends` 只屬於未來的 HTTP 邊界；禁止將 FastAPI 匯入 PySide 桌面核心。
- OpenAI／Windows 語音時序只有一個真實來源：`lip_sync.py`。
- 參數化分層 2.5D 臉部只有一條資料流：`lip_sync.py` 產生嘴型狀態，`face_motion.py` 合成不可變的臉部參數，`face_renderer.py` 繪製三種姿態；`app.py` 只組裝與顯示。`face_assets.py` 是三姿態素材、尺寸與錨點的權威清冊，現有相容渲染路徑只作為明確回退。
- 可替換的文字轉語音引擎透過 `speech_providers.py` 註冊。供應器可以合成音訊，但不得擁有嘴型同步、表情狀態、UI、權限或備援政策；經 Windows 驗證的女性本機語音是權威離線備援。
- 持久化的本機語音選擇使用平台中立的 `system-local` 供應器 ID。舊字面 ID `windows-local` 與在地化標籤只可作為遷移輸入，絕不得成為第二個供應器。
- 語言政策、回覆語言指示及內建提醒遷移只有一個真實來源：`language_support.py`。英文、簡體中文顯示字串及穩定的內部值至顯示值對應存放於 `ui_localization.py`；在地化標籤絕不得取代持久化的內部設定值。簡體中文對話路徑不得通過台灣繁體中文輸出正規化器。
- 回覆前等待表情政策只有一個真實來源：`expression_system.plan_wait_expressions`。畫面上的「思考中」狀態僅供資訊顯示，絕不得自行選擇角色表情。
- 可攜式設定檔規則只有一個真實來源：`profile_transfer.py`。
- 機密絕不儲存於 SQLite，也絕不進入可攜式設定檔。
- 受限的預覽封裝不得削弱前述規則。在原生安全儲存完成實作並經真實裝置驗證前，預覽 UI 不顯示金鑰、OAuth 或 token 欄位，也不得建立可能持久化這些資料的功能服務。

### 封裝邊界

- Windows ZIP、EXE 與 MSI 仍是唯一完整產品封裝。
- 分開提供的 macOS Apple Silicon（arm64）、Intel（x86_64）DMG，以及 Linux x86_64 AppImage，內含 `preview_app.py`，而非 Windows 的 `app.py` 外殼。其用途是驗證原生封裝、啟動、在地化、路徑與安全邊界。
- Pull Request 可在封裝層級 smoke test 通過後上傳短期 artifact，但絕不建立 GitHub Release。
- 只有符合 `vN.N.N` 或 `vN.N.N-rc.N` 規則且已存在的不可變 tag 可以發布多平台版本；正式 tag 建立 Stable Release，RC tag 建立 Pre-release。唯讀中繼資料工作負責收集全部平台輸出並建立 SBOM、中繼資料與 checksum；另一個最小權限工作則重新檢查完全相同的 artifact 與 tag commit、產生證明，並發布單一 Release。
- 發布證據把可觀測性與供應鏈資料視為門檻，而非裝飾。Tachyon 證據必須完成淨化、JIT 驗證、取樣品質檢查，且可由單一二進位資料流重現；原始資料流僅能暫存。CycloneDX 1.7 清冊必須符合鎖定的執行期需求、包含完整根依賴邊、PURL 與宣告的 SPDX 授權，通過官方 schema 與隱私門檻，並分開追蹤僅建置使用的工具。
- 每一個 Windows 與預覽二進位發行包，都必須在終端使用者可閱讀的位置攜帶 MIT 授權與第三方聲明。
- 只有當 AppImage 建置工具的官方來源 commit、資產身分與 SHA-256 均符合已審查常數時，才可接受該工具。GitHub Actions 必須固定至完整 commit SHA。

### 資料所有權

- `db.py`：對話、記憶、任務、靈感、工作紀錄與設定。
- `secret_store.py`：可注入的 `PlatformSecretStoreFactory` 邊界。Windows 使用與使用者綁定的 DPAPI 儲存；未驗證平台使用安全失敗儲存，絕不使用功能區域內的明文備援。
- `platform_contracts.py`：平台能力、每位使用者的路徑及桌面服務協定。在尚無經驗證原生安全儲存的平台上，機密持久化必須安全失敗，不得寫入明文。
- `profile_transfer.py`：可攜的共用進度；排除機器權限與機密。每一個套件都有 snapshot ID；重複匯入相同 snapshot 會被阻擋，較舊 snapshot 則會收到覆寫警告。
- `backup_manager.py`：經驗證的本機變更前備份與每日備份。

### 新增功能的方法

1. 將領域邏輯放入名稱精確的新模組。
2. 定義小型公開 API；不得直接存取其他類別的私有狀態。
3. UI 若不只是小型控制項，請放入獨立的 `<feature>_ui.py` 模組。
4. 在組裝點註冊其分頁或面板。
5. 為該功能單獨加入一項契約測試，並加入一項整合 smoke test。
6. 執行 `test_architecture_contracts.py` 與完整回歸測試套件。

若某項行為已有權威擁有者，不得新增第二份設定、計時器或 signal；應擴充該擁有者的公開 API。

### Codex 導向維護規則

- 優先採用明確匯入、建構式與 signal 連線，不採用探索魔法或反射。
- 外部引擎與工具優先使用鴨子型別的 `Protocol` 邊界；若完整 API 就是預期不變量，具體領域物件可以維持具體型別。
- 新功能的服務、UI 與測試應使用一致且可搜尋的名稱。
- 不得將大量功能邏輯加入 `app.py`；它是組裝外殼。
- 功能只能透過有文件的公開方法、signal 或服務 API 使用其他功能。
- 若變更需要碰觸無關模組，必須先新增或改善缺少的公開邊界。
- 絕不得只為讓新依賴通過而削弱架構測試。

## 简体中文

本文档是人类贡献者与 Codex 共同遵守的维护契约。

### 依赖方向

依赖只能向下指向：

1. `app.py` 是 Windows 角色外壳；`service_container.py` 是明确的运行时装配根。`preview_app.py` 则是独立且刻意受限的 macOS／Linux 预览封装外壳；它可以显示平台状态与本地化内容，但不得导入 `app.py`、创建云端／语音／工具服务，或显示机密输入字段。
2. UI 模块（`flagship_ui.py`、`profile_transfer_ui.py`）可以调用服务的公开 API。
3. 服务（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）可以使用领域与存储模块。
4. 领域与存储模块（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）绝不导入 UI 或 `app.py`。

禁止本地模块循环导入，并由 `tests/test_architecture_contracts.py` 强制检查。

### 功能边界

- 仪表板分页通过 `DashboardFeatureRegistry` 挂载。新增分页只应变更装配清单，不得变更无关分页。
- 跨窗口调用必须使用公开方法或 Qt signal。`CompanionWindow` 绝不得调用私有的 `Dashboard._method`。
- 可替换的语音、Realtime、机密存储与监听器依赖，由 `contracts.py` 内小型的 `typing.Protocol` 端口描述，并通过 `CompanionServices` 注入 `CompanionWindow`。
- 桌面操作系统行为必须通过 `PlatformServicePort`，以及明确的 `platform_windows.py`、`platform_macos.py`、`platform_linux.py` 适配器进入。核心模块不得无条件导入 `winreg`、`winsound`、`ctypes.windll` 或 `os.startfile`。
- 桌面依赖注入以构造函数为基础。FastAPI 的 `Depends` 只属于未来的 HTTP 边界；禁止将 FastAPI 导入 PySide 桌面核心。
- OpenAI／Windows 语音时序只有一个真实来源：`lip_sync.py`。
- 参数化分层 2.5D 脸部只有一条数据流：`lip_sync.py` 生成嘴型状态，`face_motion.py` 合成不可变的脸部参数，`face_renderer.py` 绘制三种姿态；`app.py` 只负责装配与显示。`face_assets.py` 是三姿态素材、尺寸与锚点的权威清单，现有兼容渲染路径只作为明确回退。
- 可替换的文字转语音引擎通过 `speech_providers.py` 注册。提供程序可以合成音频，但不得拥有嘴型同步、表情状态、UI、权限或回退策略；经 Windows 验证的女性本地语音是权威离线回退。
- 持久化的本地语音选择使用平台中立的 `system-local` 提供程序 ID。旧字面 ID `windows-local` 与本地化标签只可作为迁移输入，绝不得成为第二个提供程序。
- 语言策略、回复语言指示及内置提醒迁移只有一个真实来源：`language_support.py`。英文、简体中文显示字符串及稳定的内部值至显示值映射存放于 `ui_localization.py`；本地化标签绝不得取代持久化的内部设置值。简体中文对话路径不得通过台湾繁体中文输出规范化器。
- 回复前等待表情策略只有一个真实来源：`expression_system.plan_wait_expressions`。界面上的“思考中”状态仅供信息显示，绝不得自行选择角色表情。
- 可移植配置文件规则只有一个真实来源：`profile_transfer.py`。
- 机密绝不存储于 SQLite，也绝不进入可移植配置文件。
- 受限的预览封装不得削弱上述规则。在原生安全存储完成实现并经真实设备验证前，预览 UI 不显示密钥、OAuth 或 token 字段，也不得创建可能持久化这些数据的功能服务。

### 封装边界

- Windows ZIP、EXE 与 MSI 仍是唯一完整产品封装。
- 分别提供的 macOS Apple Silicon（arm64）、Intel（x86_64）DMG，以及 Linux x86_64 AppImage，内含 `preview_app.py`，而非 Windows 的 `app.py` 外壳。其用途是验证原生封装、启动、本地化、路径与安全边界。
- Pull Request 可在封装层级 smoke test 通过后上传短期 artifact，但绝不创建 GitHub Release。
- 只有符合 `vN.N.N` 或 `vN.N.N-rc.N` 规则且已存在的不可变 tag 可以发布多平台版本；正式 tag 创建 Stable Release，RC tag 创建 Pre-release。只读元数据作业负责收集全部平台输出并创建 SBOM、元数据与 checksum；另一个最小权限作业则重新检查完全相同的 artifact 与 tag commit、生成证明，并发布单一 Release。
- 发布证据把可观测性与供应链数据视为门槛，而非装饰。Tachyon 证据必须完成净化、JIT 验证、采样质量检查，且可由单一二进制数据流重现；原始数据流只能暂存。CycloneDX 1.7 清单必须符合锁定的运行时需求、包含完整根依赖边、PURL 与声明的 SPDX 许可证，通过官方 schema 与隐私门槛，并分别追踪仅构建使用的工具。
- 每一个 Windows 与预览二进制发行包，都必须在最终用户可阅读的位置携带 MIT 许可证与第三方声明。
- 只有当 AppImage 构建工具的官方源 commit、资产身份与 SHA-256 均符合已审查常量时，才可接受该工具。GitHub Actions 必须固定至完整 commit SHA。

### 数据所有权

- `db.py`：对话、记忆、任务、灵感、工作记录与设置。
- `secret_store.py`：可注入的 `PlatformSecretStoreFactory` 边界。Windows 使用与用户绑定的 DPAPI 存储；未验证平台使用安全失败存储，绝不使用功能局部的明文回退。
- `platform_contracts.py`：平台能力、每位用户的路径及桌面服务协议。在尚无经验证原生安全存储的平台上，机密持久化必须安全失败，不得写入明文。
- `profile_transfer.py`：可移植的共享进度；排除机器权限与机密。每一个包都有 snapshot ID；重复导入相同 snapshot 会被阻止，较旧 snapshot 则会收到覆盖警告。
- `backup_manager.py`：经验证的本地变更前备份与每日备份。

### 新增功能的方法

1. 将领域逻辑放入名称精确的新模块。
2. 定义小型公开 API；不得直接访问其他类的私有状态。
3. UI 若不只是小型控件，请放入独立的 `<feature>_ui.py` 模块。
4. 在装配点注册其分页或面板。
5. 为该功能单独加入一项契约测试，并加入一项集成 smoke test。
6. 执行 `test_architecture_contracts.py` 与完整回归测试套件。

若某项行为已有权威拥有者，不得新增第二份设置、计时器或 signal；应扩展该拥有者的公开 API。

### Codex 导向维护规则

- 优先采用明确导入、构造函数与 signal 连接，不采用发现魔法或反射。
- 外部引擎与工具优先使用鸭子类型的 `Protocol` 边界；若完整 API 就是预期不变量，具体领域对象可以保持具体类型。
- 新功能的服务、UI 与测试应使用一致且可搜索的名称。
- 不得将大量功能逻辑加入 `app.py`；它是装配外壳。
- 功能只能通过有文档的公开方法、signal 或服务 API 使用其他功能。
- 若变更需要触及无关模块，必须先新增或改善缺少的公开边界。
- 绝不得只为让新依赖通过而削弱架构测试。

## English

This file is the maintenance contract shared by human contributors and Codex.

### Dependency direction

Dependencies point downward only:

1. `app.py` is the Windows character shell; `service_container.py` is the explicit runtime composition root. `preview_app.py` is a separate, deliberately limited macOS/Linux Preview package shell; it may display platform status and localization, but it must not import `app.py`, create cloud/voice/tool services, or expose secret inputs.
2. UI modules (`flagship_ui.py`, `profile_transfer_ui.py`) may call public service APIs.
3. Services (`profile_transfer.py`, `speech.py`, `realtime_voice.py`, `ai_client.py`, `cloud_connectors.py`, `home_assistant.py`, `remote_control.py`) may use domain and storage modules.
4. Domain and storage modules (`db.py`, `flagship_core.py`, `expression_system.py`, `lip_sync.py`, `face_rig.py`, `face_motion.py`, `face_assets.py`, `face_renderer.py`, `workflow_engine.py`) never import UI or `app.py`.

Circular local imports are prohibited and enforced by `tests/test_architecture_contracts.py`.

### Feature boundaries

- Dashboard tabs are mounted through `DashboardFeatureRegistry`. Adding a tab changes the composition list, not unrelated tabs.
- Cross-window calls use public methods or Qt signals. `CompanionWindow` must never call a private `Dashboard._method`.
- Replaceable speech, Realtime, secret-store, and listener dependencies are described by small `typing.Protocol` ports in `contracts.py` and enter `CompanionWindow` through `CompanionServices`.
- Desktop operating-system behavior enters through `PlatformServicePort` and the explicit `platform_windows.py`, `platform_macos.py`, and `platform_linux.py` adapters. Core modules must not import `winreg`, `winsound`, `ctypes.windll`, or `os.startfile` unconditionally.
- Desktop dependency injection is constructor-based. FastAPI `Depends` belongs only in a future HTTP boundary; importing FastAPI into the PySide desktop core is prohibited.
- OpenAI/Windows speech timing has one source of truth: `lip_sync.py`.
- The parametric layered 2.5D face has one data flow: `lip_sync.py` produces articulation state, `face_motion.py` combines immutable face parameters, and `face_renderer.py` draws all three poses; `app.py` only composes and displays them. `face_assets.py` is the authoritative manifest for three-pose assets, dimensions, and anchors, while the compatible renderer is an explicit rollback path only.
- Replaceable text-to-speech engines register through `speech_providers.py`. Providers may synthesize audio but must not own lip sync, expression state, UI, permissions, or fallback policy; Windows verified-female local speech is the authoritative offline fallback.
- Persisted local-speech selection uses the platform-neutral `system-local` provider ID. The literal legacy ID `windows-local` and localized labels are migration inputs only; they must never become a second provider.
- Language policy, response-language instructions, and built-in reminder migration have one source of truth in `language_support.py`. English and Simplified Chinese display strings and stable internal-to-display mappings live in `ui_localization.py`; localized labels must never replace persisted internal setting values. Simplified Chinese conversation paths must not pass through the Taiwan Traditional Chinese output normalizer.
- Pre-reply wait-expression policy has one source of truth in `expression_system.plan_wait_expressions`. The visible “thinking” status is informational and must never select a character expression by itself.
- Portable profile rules have one source of truth: `profile_transfer.py`.
- Secrets are never stored in SQLite and never enter portable profile files.
- A limited Preview package does not weaken these rules. Until a native secure store is implemented and device-validated, the Preview UI exposes no key, OAuth, or token fields and does not construct a feature service that could persist them.

### Package boundaries

- Windows ZIP, EXE, and MSI remain the only complete product packages.
- Separate macOS Apple Silicon (arm64) and Intel (x86_64) DMGs plus the Linux x86_64 AppImage contain `preview_app.py`, not the Windows `app.py` shell. Their purpose is native packaging, startup, localization, path, and safety-boundary validation.
- Pull requests may upload short-lived package artifacts after a package-level smoke test. They never create a GitHub Release.
- Only an existing immutable tag matching `vN.N.N` or `vN.N.N-rc.N` may publish multi-platform packages; stable tags create Stable Releases and RC tags create Pre-releases. A read-only metadata job gathers all platform outputs and creates SBOMs, metadata, and checksums; a separate minimal privileged job rechecks the exact artifacts and tag commit, attests them, and publishes one Release.
- Release evidence treats observability and supply-chain data as gates, not decoration. Tachyon evidence must be sanitized, JIT-verified, sample-quality checked, and reproducible from one binary stream; raw streams are temporary. CycloneDX 1.7 inventories must match pinned runtime requirements, include complete root dependency edges, PURLs and declared SPDX licenses, pass the official schema and privacy gates, and track build-only tools separately.
- Every Windows and Preview binary distribution carries the MIT license and third-party notices in an end-user-readable location.
- The AppImage build tool is accepted only when its official source commit, asset identity, and SHA-256 match the reviewed constants. GitHub Actions are pinned to complete commit SHAs.

### Data ownership

- `db.py`: conversations, memories, tasks, ideas, work history, and settings.
- `secret_store.py`: the injectable `PlatformSecretStoreFactory` boundary. Windows receives user-bound DPAPI stores; an unverified platform receives a fail-closed store, never a feature-local plaintext fallback.
- `platform_contracts.py`: platform capabilities, per-user paths, and the desktop service protocol. On a platform without verified native secure storage, secret persistence fails closed instead of writing plaintext.
- `profile_transfer.py`: portable shared progress; machine permissions and secrets are excluded. Every bundle has a snapshot ID; importing the same snapshot twice is blocked, and older snapshots receive an overwrite warning.
- `backup_manager.py`: verified local pre-change and daily backups.

### How to add a feature

1. Put domain logic in a new, narrowly named module.
2. Define a small public API; do not reach into another class's private state.
3. Put UI in a separate `<feature>_ui.py` module when it is more than a small control.
4. Register its tab or panel at the composition point.
5. Add a contract test for the feature alone and one integration smoke test.
6. Run `test_architecture_contracts.py` and the full regression suite.

Do not add a second setting, timer, or signal for behavior that already has a canonical owner. Extend the owner's public API instead.

### Codex-oriented maintenance rules

- Prefer explicit imports, constructors, and signal connections over discovery magic or reflection.
- Prefer duck-typed `Protocol` boundaries for external engines and tools. Concrete domain objects may remain concrete when their full API is the intended invariant.
- Keep a new feature's service, UI, and tests under matching searchable names.
- Do not add substantial feature logic to `app.py`; it is a composition shell.
- A feature may use another feature only through a documented public method, signal, or service API.
- If a change requires touching unrelated modules, first add or improve the missing public boundary.
- Never weaken an architecture test merely to make a new dependency pass.

## 日本語

本書は、人間のコントリビューターと Codex が共同で従う保守契約です。

### 依存関係の方向

依存関係は下位方向にだけ向けます。

1. `app.py` は Windows のキャラクターシェルであり、`service_container.py` は明示的な実行時コンポジションルートです。`preview_app.py` は独立した、意図的に制限された macOS／Linux Preview パッケージシェルです。プラットフォーム状態とローカライズ内容は表示できますが、`app.py` のインポート、クラウド／音声／ツールサービスの生成、機密入力欄の公開は禁止します。
2. UI モジュール（`flagship_ui.py`、`profile_transfer_ui.py`）は、サービスの公開 API を呼び出せます。
3. サービス（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）は、ドメインおよびストレージモジュールを利用できます。
4. ドメインおよびストレージモジュール（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）は、UI または `app.py` を決してインポートしません。

ローカルモジュール間の循環インポートは禁止し、`tests/test_architecture_contracts.py` で強制検査します。

### 機能境界

- ダッシュボードのタブは `DashboardFeatureRegistry` を通じてマウントします。タブを追加するときはコンポジション一覧だけを変更し、無関係なタブを変更してはいけません。
- ウィンドウ間の呼び出しには公開メソッドまたは Qt signal を使用します。`CompanionWindow` は非公開の `Dashboard._method` を決して呼び出してはいけません。
- 交換可能な音声、Realtime、機密ストア、リスナーの依存関係は、`contracts.py` にある小さな `typing.Protocol` ポートで記述し、`CompanionServices` を通じて `CompanionWindow` に注入します。
- デスクトップ OS の動作は、`PlatformServicePort` と明示的な `platform_windows.py`、`platform_macos.py`、`platform_linux.py` アダプターを通じて導入します。コアモジュールは `winreg`、`winsound`、`ctypes.windll`、`os.startfile` を無条件にインポートしてはいけません。
- デスクトップの依存性注入はコンストラクター方式とします。FastAPI の `Depends` は将来の HTTP 境界だけに属し、PySide デスクトップコアへの FastAPI のインポートは禁止します。
- OpenAI／Windows の音声タイミングには、`lip_sync.py` という唯一の信頼できる情報源があります。
- パラメトリック多層 2.5D フェイスのデータフローは一つだけです。`lip_sync.py` が口形状態を生成し、`face_motion.py` が不変の顔パラメーターを統合し、`face_renderer.py` が三姿勢を描画します。`app.py` は構成と表示だけを担当します。`face_assets.py` は三姿勢の素材、寸法、アンカーの権威あるマニフェストであり、現行互換レンダラーは明示的なロールバック経路としてのみ残します。
- 交換可能なテキスト読み上げエンジンは `speech_providers.py` を通じて登録します。プロバイダーは音声を合成できますが、リップシンク、表情状態、UI、権限、フォールバック方針を所有してはいけません。Windows で検証済みの女性ローカル音声を正式なオフラインフォールバックとします。
- 永続化するローカル音声の選択には、プラットフォーム中立の `system-local` プロバイダー ID を使用します。旧リテラル ID `windows-local` とローカライズ済みラベルは移行入力に限り、第二のプロバイダーにしてはいけません。
- 言語方針、応答言語の指示、組み込みリマインダーの移行には、`language_support.py` という唯一の信頼できる情報源があります。英語および簡体字中国語の表示文字列と、安定した内部値から表示値への対応は `ui_localization.py` に置きます。ローカライズ済みラベルで永続化された内部設定値を置き換えてはいけません。簡体字中国語の会話経路を台湾繁体字中国語の出力正規化処理に通してはいけません。
- 応答前の待機表情方針には、`expression_system.plan_wait_expressions` という唯一の信頼できる情報源があります。画面上の「思考中」状態は情報表示だけに使用し、それ自体でキャラクター表情を選択してはいけません。
- ポータブルプロファイル規則には、`profile_transfer.py` という唯一の信頼できる情報源があります。
- 機密情報を SQLite に保存したり、ポータブルプロファイルへ含めたりしてはいけません。
- 制限付き Preview パッケージでも、これらの規則を弱めてはいけません。ネイティブ安全ストアの実装と実機検証が完了するまで、Preview UI はキー、OAuth、token の入力欄を公開せず、それらを永続化し得る機能サービスも生成しません。

### パッケージ境界

- Windows ZIP、EXE、MSI は、引き続き唯一の完全な製品パッケージです。
- 個別に提供する macOS Apple Silicon（arm64）および Intel（x86_64）DMG と Linux x86_64 AppImage には、Windows の `app.py` シェルではなく `preview_app.py` を含めます。目的は、ネイティブパッケージング、起動、ローカライズ、パス、安全境界の検証です。
- Pull Request では、パッケージレベルの smoke test 後に短期 artifact をアップロードできますが、GitHub Release は決して作成しません。
- `vN.N.N` または `vN.N.N-rc.N` に一致する既存の不変 tag だけがマルチプラットフォームパッケージを公開できます。正式 tag は Stable Release、RC tag は Pre-release を作成します。読み取り専用メタデータジョブが全プラットフォームの出力を収集して SBOM、メタデータ、checksum を作成し、別の最小権限ジョブが同一の artifact と tag commit を再検査して証明を生成し、単一の Release を公開します。
- リリース証拠では、可観測性とサプライチェーンデータを装飾ではなくゲートとして扱います。Tachyon 証拠はサニタイズ、JIT 検証、サンプル品質検査を完了し、単一のバイナリストリームから再現できなければなりません。生ストリームは一時保存に限ります。CycloneDX 1.7 インベントリは、固定された実行時要件と一致し、完全なルート依存エッジ、PURL、宣言済み SPDX ライセンスを含み、公式 schema とプライバシーゲートに合格し、ビルド専用ツールを分離して追跡しなければなりません。
- すべての Windows および Preview バイナリ配布物には、エンドユーザーが読める場所に MIT ライセンスと第三者通知を収録します。
- AppImage ビルドツールは、公式ソース commit、asset identity、SHA-256 が審査済み定数と一致する場合にだけ受け入れます。GitHub Actions は完全な commit SHA に固定します。

### データ所有権

- `db.py`：会話、記憶、タスク、アイデア、作業履歴、設定。
- `secret_store.py`：注入可能な `PlatformSecretStoreFactory` 境界。Windows ではユーザーに紐づく DPAPI ストアを使用し、未検証のプラットフォームでは安全側に失敗するストアを使用します。機能内の平文フォールバックは決して使用しません。
- `platform_contracts.py`：プラットフォーム機能、ユーザーごとのパス、デスクトップサービスプロトコル。検証済みネイティブ安全ストレージがないプラットフォームでは、機密情報を平文で書き込まず、永続化を安全側に失敗させます。
- `profile_transfer.py`：ポータブルな共有進捗。マシン権限と機密情報は除外します。各 bundle は snapshot ID を持ち、同一 snapshot の二重インポートは阻止し、古い snapshot には上書き警告を表示します。
- `backup_manager.py`：検証済みのローカル変更前バックアップおよび日次バックアップ。

### 機能の追加方法

1. ドメインロジックを、目的が明確な名前の新しいモジュールへ配置します。
2. 小さな公開 API を定義し、別クラスの非公開状態へ直接アクセスしてはいけません。
3. UI が小さなコントロールを超える場合は、独立した `<feature>_ui.py` モジュールへ配置します。
4. コンポジションポイントでタブまたはパネルを登録します。
5. その機能単独の契約テストを一つと、統合 smoke test を一つ追加します。
6. `test_architecture_contracts.py` と完全な回帰テストスイートを実行します。

すでに正式な所有者がある動作に、第二の設定、タイマー、signal を追加してはいけません。代わりに、その所有者の公開 API を拡張します。

### Codex 指向の保守規則

- 探索マジックやリフレクションより、明示的なインポート、コンストラクター、signal 接続を優先します。
- 外部エンジンとツールには、ダックタイピングされた `Protocol` 境界を優先します。完全な API 自体が意図した不変条件である場合、具体的なドメインオブジェクトは具体型のままで構いません。
- 新機能のサービス、UI、テストには、一致して検索しやすい名前を付けます。
- `app.py` に大規模な機能ロジックを追加してはいけません。これはコンポジションシェルです。
- 機能が別の機能を利用できるのは、文書化された公開メソッド、signal、サービス API を通じる場合だけです。
- 変更に無関係なモジュールまで触れる必要がある場合は、まず不足している公開境界を追加または改善します。
- 新しい依存関係を通すためだけに、アーキテクチャテストを弱めてはいけません。
