# 墨寒架構／墨寒架构／MoHan Architecture／墨寒アーキテクチャ

## 繁體中文

本文件是人類貢獻者與 Codex 共同遵守的維護契約。

### 長期賈維斯式個人助理願景與模組邊界

- 「賈維斯式」只描述一個能長期理解情境、協調裝置與適時協助使用者的個人助理方向；墨寒不承諾、也不得企圖模仿任何影視、文學或其他作品的角色、人格、聲音、外觀或受保護表現。
- 專案不以程式行數、模組數量或功能清單長度衡量成果。每項能力必須以實際使用價值、正確性、安全、隱私、可維護性、可觀測性與不破壞既有功能的證據驗收。
- 視覺、語音、記憶、主動互動、外觀與自動化各自擁有明確且低耦合的公開邊界。每項能力都必須能獨立啟閉、替換供應器或實作、在相依項目不可用時安全降級，且不得迫使其他能力一併啟用或失效。
- 攝影機、麥克風、顯示器、輸入裝置、智慧家庭及未來裝置只能透過型別化裝置介面提供能力與健康狀態；對話、在席、排程、提醒、手勢、感知與外部服務結果只能透過型別化事件進入系統。領域模組不得直接搶占裝置或彼此呼叫私有實作。
- 所有裝置狀態與事件候選必須先交由單一、可測試、可稽核的仲裁邊界協調，再產生最多一個原子決策。仲裁器負責優先序、互斥、冷卻、取消、過期 generation、專注保護、權限與安全政策，避免多個能力同時說話、動作或控制同一裝置。
- 涉及醫療、健康、安全、金錢、法律、身分、隱私、不可逆裝置控制或其他高風險資訊時，輸出必須攜帶可追溯來源、觀測或資料時間、不確定性與適用限制。執行或形成高風險結論前必須取得清楚的使用者確認；缺少來源、資料過期、互相矛盾或信心不足時，系統應明確降級為建議、詢問或拒絕執行。
- 這是長期架構方向與未來功能的准入門檻，不是 v4 已完成、已封裝、已通過實機驗收或已發布的宣稱。每個版本仍須以當次程式、測試、裝置驗收、SBOM、封裝及發布證據為準。

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
- 可攜式設定檔規則只有一個真實來源：`profile_transfer.py`。機器權限、本機裝置狀態與原始本機路徑永不攜帶；機密預設排除，只有使用者明確勾選並提供強密碼時，才能依 `portable_secrets.py` 的固定型別格式寫入獨立且通過完整性驗證的 `sensitive.enc`。機密絕不儲存於 SQLite、明文攜帶檔、日誌或錯誤訊息。
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

### 視覺感知的授權與資料邊界

- 公開版的攝影機與遠端影像語意分析預設關閉。使用者在控制台明確啟用並全域保存後，即建立持續授權，直到使用者主動關閉。系統不會逐幀詢問；授權狀態必須始終可見，並提供配額、成本上限與立即撤銷控制。
- OpenCV 在本機執行持續、低成本的感知。GPT-5.6 僅接收低頻或事件觸發的一張暫時影像作語意分析，不得把持續影像串流直接交給遠端服務。
- 原始影像不得落地，Base64 不得寫入資料庫、設定、攜帶檔、日誌、遙測或錯誤訊息。視覺模組不自行開啟網路；只有已保存的使用者授權、已設定的服務與尚未用盡的配額同時成立時，才可提出遠端請求。
- 使用者可設定用量與成本上限，並可隨時關閉或取消尚未完成的分析。關閉後的延遲結果必須失效；攝影機、模型、SDK、網路、額度或取消失敗不影響本機感知及任何既有功能。
- 發行清冊必須鎖定 OpenCV 版本及經核實授權。OpenAI Responses API 路徑使用 Python 標準庫 `urllib.request` 經 HTTPS 直接呼叫；專案沒有、不得加入或虛構 `openai` Python SDK 執行期相依。OpenAI 是外部服務而非封裝元件，SBOM 的機器可讀外部服務政策必須明確記錄此邊界。若 OpenCV 清冊缺漏、出現 SDK 相依或政策漂移，v4 發行必須失敗關閉。

#### 手勢與視覺融合管線

- 本機管線以最高 10 Hz 處理手部 21 點骨架，並以最高 1 Hz 取得短時嘴部區域證據。兩者先轉換至一致的 selfie 座標系，再由具時間戳的融合層配對；任何融合證據最長 1.5 秒後失效，不得以過期嘴部或手部資料推定新手勢。
- 原始影像、嘴部裁切與一般骨架證據只存在於處理中的短時記憶體，不得寫入資料庫、一般攜帶檔、日誌或遙測。只有使用者明確錄製的自訂 21 點骨架樣本可以持久化，且必須進入受保護的加密儲存；一般設定與一般攜帶檔只保存開關、名稱及動作映射等非敏感中繼資料。
- 權限未授予、攝影機或模型不可用、時間戳失序、座標無法一致化、追蹤中斷或信心不足時，融合結果必須故障封閉為未知或不派送，且不得影響既有聊天、語音及 2.5D 功能。
- 控制器只管理生命週期、權限與 generation；辨識器只把正規化證據轉為候選意圖；路由器只依使用者映射與安全政策產生動作決策；派送器只把已核准決策交給既有安全命令邊界。各層以不可變型別與窄介面連接，不得直接讀取彼此的儲存、UI、攝影機或外部服務。
- 本節描述開發中的架構契約，不代表完整回歸、封裝、Windows EXE 真攝影機實機驗證或正式發布已完成。

### 零技術債與前瞻相容門檻

- 新功能第一次實作就必須涵蓋完整生命週期：建立／安裝、驗證、預覽、保存、取消、停用、刪除、遷移、缺失回退、可觀測性及回歸測試。不得以日後必須推翻的一次性捷徑換取眼前完成。
- 每次設計都要主動評估當下最新且已能可靠採用的語言、標準庫、平台 API、封裝格式與安全機制；在能提升清楚度、效能、安全或維護性且完整回歸不退步時，優先採用新的做法，不因慣性保留舊路徑。
- 只有上游、作業系統、硬體或相依套件尚未真正支援時，才可暫緩。暫緩必須記錄限制原因、隔離邊界、安全替代、未來啟用條件、移除舊路徑的責任與測試，不得形成無主技術債。
- 任何新增功能若損害既有聊天、語音、表情、記憶、工具、設定、四語、隱私、安全、跨平台或封裝行為，即視為未完成，禁止封裝、合併與發布。
- 角色外觀與 2.5D 視覺變更必須把未來逐像素修補轉成自動門檻：固定畫布與錨點、分層深度、透明邊緣、臉／手／髮／衣領遮擋、核心身份區零變動，以及全部表情與姿態逐張接觸表稽核。任一姿態穿模、漂移或露回舊素材即整包拒絕。

### Codex 導向維護規則

- 優先採用明確匯入、建構式與 signal 連線，不採用探索魔法或反射。
- 外部引擎與工具優先使用鴨子型別的 `Protocol` 邊界；若完整 API 就是預期不變量，具體領域物件可以維持具體型別。
- 新功能的服務、UI 與測試應使用一致且可搜尋的名稱。
- 不得將大量功能邏輯加入 `app.py`；它是組裝外殼。
- 功能只能透過有文件的公開方法、signal 或服務 API 使用其他功能。
- 若變更需要碰觸無關模組，必須先新增或改善缺少的公開邊界。
- 絕不得只為讓新依賴通過而削弱架構測試。

### 桌面應用分層契約

架構閘門分別報告實體五層套件模組、根相容入口與 `legacy-root` 數量，只有空 `__init__.py` 絕不能代表完成分層。每個根產品名稱都必須有機器可讀的目標層與維護 owner；`legacy-root` 必須為零，相容性根檔只能是 `compatibility-root` 薄轉接，實作只能存在於 `presentation`、`application`、`domain`、`integrations` 或 `infrastructure` 的單一真正 owner。根 `app.py` 是不超過五十行的正式組合入口，直接使用 `application.application_bootstrap`；其他根相容入口與正式套件均不得反向依賴它。Domain 與 application 清冊中的全部模組已由實體套件承接，層內依賴必須直接使用 `domain.*` 或 `application.*` 正式路徑，不得繞回根相容入口；其餘層若缺實體 owner 或仍使用根 facade，發行閘門維持失敗。

`presentation` 現已實體承接 Companion 與 Dashboard 視窗組裝、各自的 UI mixin、對話框、首次設定精靈、攜帶檔面板、主題面板／繪製、更新面板及顯示層在地化目錄。根目錄同名模組只保留可搜尋的薄相容轉接，既有外部匯入仍可使用，但 presentation 內部必須直接指向 `presentation.*` 的真正 owner；`flagship_ui.py` 仍留待獨立遷移，不得在本階段假稱完成。

`integrations` 與 `infrastructure` 現已實體承接已盤點的外部服務、語音供應器、持久化、資產、平台及安全儲存實作。同名根模組僅為薄相容別名；產品內部、測試與工具必須直接匯入正式套件 owner，兩個實體層也不得反向經過任何根相容入口。相容入口與正式 owner 必須解析為同一 module 物件，避免 patch、型別 identity 或 lazy import callable 漂移。

- `presentation` 只負責 Qt 視窗、控制項、顯示模型與使用者事件轉接；不得直接建立外部服務、讀寫資料庫或讀取金鑰。
- `application` 協調使用案例、交易、取消與連接埠，只依賴 `domain`；不得依賴 Qt、供應器實作或作業系統細節。
- `domain` 保存純政策、不可變值與不變條件，不得依賴其他專案分層。
- `integrations` 實作雲端、語音及第三方服務介接器；`infrastructure` 實作資料庫、檔案、作業系統及安全儲存介接器。兩者只能透過 application/domain 契約接入，不得反向擁有 UI。
- 依賴方向為 `presentation → application → domain`；`integrations` 與 `infrastructure` 是由組裝根注入的外圍介接器。跨層只能使用公開、型別化的連接埠。
- API Key、OAuth secret、token 與臉部識別資料不得放入 `config.py`、`app.py`、原始碼常數、日誌或錯誤訊息；只能經核准的作業系統安全儲存連接埠使用。
- 遷移完成後，`app.py` 必須是最多 50 個實體行的唯一 composition root，只保留明確匯入、單一無參數 `main()` 委派與單一 `__main__` 啟動保護。此限制是完成分層遷移後的發布門檻，不是要求尚未搬移的模組假裝已完成。

### v4.0.0 平台與 Qt 相容層政策

- 官方 PySide6 metadata 是否宣告 Python 3.15，不再是硬閘門；以固定雜湊官方 wheel 二進位、`6.11.1+mohan.py315.1` metadata、正常 resolver、`pip check` 與 Qt smoke 驗證。
- Windows 是正式支援平台；macOS／Linux 是功能受限 Preview。CI runner 證據不等於開發者本人實機認證，也不宣稱 Windows 功能同等。
- 安全、秘密、回歸、包內內容、SBOM、SHA-256、artifact 完整性與回退行為仍是不可取消的必要門檻。

## 简体中文

本文档是人类贡献者与 Codex 共同遵守的维护契约。

### 长期贾维斯式个人助理愿景与模块边界

- “贾维斯式”只描述一个能够长期理解情境、协调设备并适时协助用户的个人助理方向；墨寒不承诺、也不得试图模仿任何影视、文学或其他作品的角色、人格、声音、外观或受保护表现。
- 项目不以代码行数、模块数量或功能清单长度衡量成果。每项能力必须以实际使用价值、正确性、安全、隐私、可维护性、可观测性与不破坏现有功能的证据验收。
- 视觉、语音、记忆、主动交互、外观与自动化分别拥有明确且低耦合的公开边界。每项能力都必须能够独立启停、替换供应商或实现、在依赖项不可用时安全降级，而且不得迫使其他能力一并启用或失效。
- 摄像头、麦克风、显示器、输入设备、智能家居及未来设备只能通过强类型设备接口提供能力与健康状态；对话、在场、日程、提醒、手势、感知与外部服务结果只能通过强类型事件进入系统。领域模块不得直接抢占设备或相互调用私有实现。
- 所有设备状态与事件候选必须先交由单一、可测试、可审计的仲裁边界协调，再产生至多一个原子决策。仲裁器负责优先级、互斥、冷却、取消、过期 generation、专注保护、权限与安全策略，避免多个能力同时说话、动作或控制同一设备。
- 涉及医疗、健康、安全、金钱、法律、身份、隐私、不可逆设备控制或其他高风险信息时，输出必须携带可追溯来源、观测或数据时间、不确定性与适用限制。执行或形成高风险结论前必须取得清楚的用户确认；缺少来源、数据过期、相互矛盾或置信度不足时，系统应明确降级为建议、询问或拒绝执行。
- 这是长期架构方向与未来功能的准入关卡，不是 v4 已完成、已打包、已通过真机验收或已发布的声明。每个版本仍须以当次代码、测试、设备验收、SBOM、打包及发布证据为准。

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
- 可移植配置文件规则只有一个真实来源：`profile_transfer.py`。机器权限、本地设备状态与原始本地路径永不携带；机密默认排除，只有用户明确勾选并提供强密码时，才能依照 `portable_secrets.py` 的固定类型格式写入独立且通过完整性验证的 `sensitive.enc`。机密绝不存储于 SQLite、明文携带文件、日志或错误信息。
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

### 视觉感知的授权与数据边界

- 公开版的摄像头与远程图像语义分析默认关闭。用户在控制台明确启用并全局保存后，即建立持续授权，直到用户主动关闭。系统不会逐帧询问；授权状态必须始终可见，并提供配额、成本上限与立即撤销控制。
- OpenCV 在本地执行持续、低成本的感知。GPT-5.6 仅接收低频或事件触发的一张临时图像进行语义分析，不得将持续图像流直接交给远程服务。
- 原始图像不保存到磁盘，Base64 不得写入数据库、设置、可移植文件、日志、遥测或错误信息。视觉模块不会自行开启网络；只有已保存的用户授权、已设置的服务与尚未用尽的配额同时成立时，才可发出远程请求。
- 用户可设置用量与成本上限，并可随时关闭或取消尚未完成的分析。关闭后的延迟结果必须失效；摄像头、模型、SDK、网络、额度或取消失败不影响本地感知及任何现有功能。
- 发布清单必须锁定 OpenCV 版本及经核实的许可证。OpenAI Responses API 路径使用 Python 标准库 `urllib.request` 通过 HTTPS 直接调用；项目没有、不得加入或虚构 `openai` Python SDK 运行时依赖。OpenAI 是外部服务而不是打包组件，SBOM 的机器可读外部服务策略必须明确记录此边界。若 OpenCV 清单缺失、出现 SDK 依赖或策略漂移，v4 发布必须安全失败。

#### 手势与视觉融合管线

- 本地管线以最高 10 Hz 处理手部 21 点骨架，并以最高 1 Hz 获取短时嘴部区域证据。两者先转换到一致的 selfie 坐标系，再由带时间戳的融合层配对；任何融合证据最长 1.5 秒后失效，不得用过期嘴部或手部数据推断新手势。
- 原始图像、嘴部裁剪与普通骨架证据只存在于处理中的短时内存，不得写入数据库、普通可移植文件、日志或遥测。只有用户明确录制的自定义 21 点骨架样本可以持久化，且必须进入受保护的加密存储；普通设置与普通可移植文件只保存开关、名称及动作映射等非敏感元数据。
- 权限未授予、摄像头或模型不可用、时间戳乱序、坐标无法统一、跟踪中断或置信度不足时，融合结果必须故障关闭为未知或不派发，且不得影响现有聊天、语音及 2.5D 功能。
- 控制器只管理生命周期、权限与 generation；识别器只将归一化证据转换为候选意图；路由器只依据用户映射与安全策略生成动作决策；派发器只将已批准决策交给现有安全命令边界。各层通过不可变类型与窄接口连接，不得直接读取彼此的存储、UI、摄像头或外部服务。
- 本节描述开发中的架构契约，不代表完整回归、打包、Windows EXE 真摄像头实机验证或正式发布已经完成。

### 零技术债与前瞻兼容门槛

- 新功能第一次实现就必须涵盖完整生命周期：创建／安装、验证、预览、保存、取消、停用、删除、迁移、缺失回退、可观测性及回归测试。不得以日后必须推翻的一次性捷径换取眼前完成。
- 每次设计都要主动评估当下最新且已能可靠采用的语言、标准库、平台 API、封装格式与安全机制；在能提升清晰度、性能、安全或维护性且完整回归不退步时，优先采用新的做法，不因惯性保留旧路径。
- 只有上游、操作系统、硬件或依赖包尚未真正支持时，才可暂缓。暂缓必须记录限制原因、隔离边界、安全替代、未来启用条件、移除旧路径的责任与测试，不得形成无人负责的技术债。
- 任何新增功能若损害现有聊天、语音、表情、记忆、工具、设置、四语、隐私、安全、跨平台或封装行为，即视为未完成，禁止封装、合并与发布。
- 角色外观与 2.5D 视觉变更必须把未来逐像素修补转成自动门槛：固定画布与锚点、分层深度、透明边缘、脸／手／头发／衣领遮挡、核心身份区零变动，以及全部表情与姿态逐张接触表审核。任一姿态穿模、漂移或露回旧素材即整包拒绝。

### Codex 导向维护规则

- 优先采用明确导入、构造函数与 signal 连接，不采用发现魔法或反射。
- 外部引擎与工具优先使用鸭子类型的 `Protocol` 边界；若完整 API 就是预期不变量，具体领域对象可以保持具体类型。
- 新功能的服务、UI 与测试应使用一致且可搜索的名称。
- 不得将大量功能逻辑加入 `app.py`；它是装配外壳。
- 功能只能通过有文档的公开方法、signal 或服务 API 使用其他功能。
- 若变更需要触及无关模块，必须先新增或改善缺少的公开边界。
- 绝不得只为让新依赖通过而削弱架构测试。

### 桌面应用分层契约

架构门禁分别报告实体五层包模块、根兼容入口与 `legacy-root` 数量，只有空 `__init__.py` 绝不能代表完成分层。每个根产品名称都必须有机器可读的目标层与维护 owner；`legacy-root` 必须为零，兼容性根文件只能是 `compatibility-root` 薄转接，实作只能存在于 `presentation`、`application`、`domain`、`integrations` 或 `infrastructure` 的单一真正 owner。根 `app.py` 是不超过五十行的正式组合入口，直接使用 `application.application_bootstrap`；其他根兼容入口与正式包均不得反向依赖它。Domain 与 application 清册中的全部模块已由实体包承接，层内依赖必须直接使用 `domain.*` 或 `application.*` 正式路径，不得绕回根兼容入口；其余层若缺实体 owner 或仍使用根 facade，发行门禁维持失败。

`presentation` 现已实体承接 Companion 与 Dashboard 窗口装配、各自的 UI mixin、对话框、首次设置向导、便携档案面板、主题面板／绘制、更新面板及显示层本地化目录。根目录同名模块只保留可搜索的薄兼容转接，既有外部导入仍可使用，但 presentation 内部必须直接指向 `presentation.*` 的真正 owner；`flagship_ui.py` 仍留待独立迁移，不得在本阶段宣称已经完成。

`integrations` 与 `infrastructure` 现已实体承接已盘点的外部服务、语音供应商、持久化、资产、平台及安全存储实现。同名根模块仅为薄兼容别名；产品内部、测试与工具必须直接导入正式包 owner，这两个实体层也不得反向经过任何根兼容入口。兼容入口与正式 owner 必须解析为同一 module 对象，避免 patch、类型 identity 或 lazy import callable 漂移。

- `presentation` 只负责 Qt 窗口、控件、显示模型与用户事件转接；不得直接创建外部服务、读写数据库或读取密钥。
- `application` 协调用例、事务、取消与端口，只依赖 `domain`；不得依赖 Qt、供应商实现或操作系统细节。
- `domain` 保存纯策略、不可变值与不变量，不得依赖其他项目分层。
- `integrations` 实现云端、语音及第三方服务适配器；`infrastructure` 实现数据库、文件、操作系统及安全存储适配器。两者只能通过 application/domain 契约接入，不得反向拥有 UI。
- 依赖方向为 `presentation → application → domain`；`integrations` 与 `infrastructure` 是由装配根注入的外围适配器。跨层只能使用公开、强类型端口。
- API Key、OAuth secret、token 与人脸识别数据不得放入 `config.py`、`app.py`、源代码常量、日志或错误信息；只能通过核准的操作系统安全存储端口使用。
- 迁移完成后，`app.py` 必须是最多 50 个物理行的唯一 composition root，只保留明确导入、单一无参数 `main()` 委派与单一 `__main__` 启动保护。此限制是完成分层迁移后的发布门槛，不要求尚未迁移的模块假装已经完成。

### v4.0.0 平台与 Qt 兼容层政策

- 官方 PySide6 metadata 是否声明 Python 3.15，不再是硬关卡；使用固定哈希官方 wheel 二进制、`6.11.1+mohan.py315.1` metadata、正常 resolver、`pip check` 与 Qt smoke 验证。
- Windows 是正式支持平台；macOS／Linux 是功能受限 Preview。CI runner 证据不等于开发者本人实机认证，也不声明 Windows 功能同等。
- 安全、秘密、回归、包内内容、SBOM、SHA-256、artifact 完整性与回退行为仍是不可取消的必要门槛。

## English

This file is the maintenance contract shared by human contributors and Codex.

### Long-term JARVIS-style personal-assistant vision and module boundaries

- “JARVIS-style” describes only the direction of a personal assistant that can understand context over time, coordinate devices, and help the user at appropriate moments. MoHan does not promise, and must not attempt, to imitate any character, personality, voice, appearance, or protected expression from film, literature, or any other work.
- The project does not measure achievement by lines of code, module count, or feature-list length. Every capability must be accepted through evidence of practical user value, correctness, safety, privacy, maintainability, observability, and preservation of established behavior.
- Vision, speech, memory, proactive interaction, appearance, and automation each have an explicit, loosely coupled public boundary. Every capability must support independent enablement and disablement, replacement of its provider or implementation, and safe degradation when a dependency is unavailable, without forcing another capability to become enabled or fail.
- Cameras, microphones, displays, input devices, smart-home systems, and future devices expose capabilities and health only through typed device interfaces. Conversation, presence, schedules, reminders, gestures, perception, and external-service results enter only as typed events. Domain modules must not seize devices directly or call one another's private implementations.
- Every device state and event candidate must pass through one testable and auditable arbitration boundary before the system emits at most one atomic decision. The arbitrator owns priority, mutual exclusion, cooldowns, cancellation, stale generations, focus protection, permissions, and safety policy so multiple capabilities cannot speak, perform, or control the same device at once.
- For medical, wellbeing, safety, financial, legal, identity, privacy, irreversible device-control, or other high-risk information, output must carry a traceable source, observation or data time, uncertainty, and applicability limits. Clear user confirmation is required before execution or formation of a high-risk conclusion. Missing sources, stale data, contradictions, or insufficient confidence must explicitly degrade to advice, a question, or refusal to act.
- This is a long-term architecture direction and an admission gate for future capabilities, not a claim that v4 is complete, packaged, accepted on real devices, or released. Each version remains governed by its own source, test, device-acceptance, SBOM, packaging, and release evidence.

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
- Portable-profile rules have one source of truth: `profile_transfer.py`. Machine permissions, local device state, and raw local paths never travel. Secrets are excluded by default and may enter only a separate, integrity-checked `sensitive.enc` when the user explicitly opts in and supplies a strong password, using the fixed typed schema in `portable_secrets.py`. Secrets never enter SQLite, plaintext bundles, logs, or error messages.
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

### Vision authorization and data boundary

- Camera access and remote image semantics are off by default in public builds. Explicitly enabling and globally saving the feature in the control center establishes continuous authorization until the user turns it off. The system does not ask for consent frame by frame; authorization status must remain visible, with quota and cost limits and immediate revocation controls.
- OpenCV performs continuous, low-cost perception locally. GPT-5.6 receives only one transient image at a low frequency or on an event trigger for semantic analysis; a continuous camera stream must never be sent directly to a remote service.
- Vision does not retain raw images. Base64 must not enter databases, settings, portable profiles, logs, telemetry, or error messages. Vision does not enable networking by itself; a remote request requires saved user authorization, a configured service, and remaining quota at the same time.
- Users can set usage and cost limits and can turn off the feature or cancel unfinished analysis at any time. Late results after shutdown must become invalid. Camera, model, SDK, network, quota, or cancellation failure is isolated without harming local perception or any established feature.
- The release inventory must pin OpenCV and its verified license. The OpenAI Responses API path calls HTTPS directly through Python's standard-library `urllib.request`; the project has no `openai` Python SDK runtime dependency and must neither add nor invent one. OpenAI is an external service, not a packaged component, and the SBOM's machine-readable external-service policy must record that boundary. A missing OpenCV inventory, any SDK dependency, or policy drift fails the v4 release closed.

#### Gesture and vision fusion pipeline

- The local pipeline processes 21-point hand skeletons at up to 10 Hz and obtains short-lived mouth-region evidence at up to 1 Hz. Both inputs are normalized into one selfie coordinate system before a timestamped fusion layer pairs them. Every fused observation expires after at most 1.5 seconds; stale mouth or hand evidence must never support a new gesture decision.
- Raw images, mouth crops, and ordinary skeleton evidence exist only in short-lived processing memory and must not enter databases, ordinary portable profiles, logs, or telemetry. Only custom 21-point skeleton samples that the user explicitly records may persist, and they must enter protected encrypted storage. Ordinary settings and portable profiles retain only non-sensitive metadata such as switches, names, and action mappings.
- Missing permission, unavailable cameras or models, non-monotonic timestamps, coordinate-normalization failure, lost tracking, or insufficient confidence makes fusion fail closed to unknown or no dispatch without harming established chat, speech, or 2.5D behavior.
- The controller owns lifecycle, authorization, and generation only. The recognizer converts normalized evidence into candidate intents only. The router applies user mappings and safety policy to produce action decisions only. The dispatcher forwards approved decisions to the established safe-command boundary only. Immutable types and narrow interfaces connect these layers; no layer may directly reach into another layer's storage, UI, camera, or external service.
- This section defines an architecture contract under development. It does not claim that full regression testing, packaging, real-camera validation in the Windows EXE, or release is complete.

### Zero-technical-debt and forward-compatibility gate

- A feature's first implementation covers its whole lifecycle: creation or installation, validation, preview, save, cancel, disable, removal, migration, missing-content fallback, observability, and regression tests. A shortcut that must later be replaced is not an acceptable definition of done.
- Every design proactively evaluates the newest language, standard-library, platform API, package format, and security mechanism that is currently reliable. Adopt the newer approach when it improves clarity, performance, security, or maintainability without a full-regression loss; do not preserve a legacy path merely through inertia.
- Deferral is allowed only when an upstream, operating system, hardware platform, or dependency does not genuinely support the capability yet. Record the constraint, isolation boundary, safe alternative, future activation trigger, owner of legacy-path removal, and tests so the deferral cannot become unowned debt.
- A new feature that harms established chat, speech, expression, memory, tool, settings, four-language, privacy, security, portability, or packaging behavior is incomplete and cannot be packaged, merged, or released.
- Character-appearance and 2.5D visual work converts future pixel-by-pixel repair into automated gates: fixed canvases and anchors, layer depth, transparent edges, face/hand/hair/collar occlusion, zero change in core identity regions, and per-frame contact-sheet review across every expression and silhouette. Any clipping, drift, or exposure of an old asset rejects the complete pack.

### Codex-oriented maintenance rules

- Prefer explicit imports, constructors, and signal connections over discovery magic or reflection.
- Prefer duck-typed `Protocol` boundaries for external engines and tools. Concrete domain objects may remain concrete when their full API is the intended invariant.
- Keep a new feature's service, UI, and tests under matching searchable names.
- Do not add substantial feature logic to `app.py`; it is a composition shell.
- A feature may use another feature only through a documented public method, signal, or service API.
- If a change requires touching unrelated modules, first add or improve the missing public boundary.
- Never weaken an architecture test merely to make a new dependency pass.

### Desktop application layering contract

The architecture gate reports physical five-layer package modules, root compatibility entries, and the `legacy-root` count separately; empty `__init__.py` files can never represent completed layering. Every root product name requires a machine-readable target layer and maintenance owner. `legacy-root` must remain zero, and a retained root file may only be a thin `compatibility-root` entry while implementation exists under exactly one true owner in `presentation`, `application`, `domain`, `integrations`, or `infrastructure`. Root `app.py` is the formal composition entrypoint, remains at most fifty lines, and imports `application.application_bootstrap` directly; neither compatibility roots nor package modules may reverse-depend on it. Every domain and application inventory module now has a physical package owner, and internal dependencies must use canonical `domain.*` or `application.*` paths instead of detouring through root compatibility entries. A missing physical owner or root-facade dependency in another layer keeps the release gate red.

`presentation` now physically owns the Companion and Dashboard window compositions, their UI mixins, dialogs, first-run wizard, portable-profile panel, theme panel/rendering, update panel, and presentation-localization catalogs. Same-named root modules remain only as searchable thin compatibility facades, so existing external imports continue to work, while internal presentation imports must target the true `presentation.*` owners directly. `flagship_ui.py` remains intentionally deferred and must not be represented as migrated in this phase.

`integrations` and `infrastructure` now physically own the inventoried external-service, speech-provider, persistence, asset, platform, and secure-storage implementations. Same-named root modules are thin compatibility aliases only. Product internals, tests, and tools must import canonical package owners directly, and neither physical layer may route back through any root compatibility facade. A compatibility entrypoint and its canonical owner must resolve to the same module object so patching, type identity, and lazy-import callability cannot drift.

- `presentation` owns only Qt windows, controls, view models, and user-event adaptation; it must not construct external services, access databases, or read secrets directly.
- `application` coordinates use cases, transactions, cancellation, and ports and depends only on `domain`; it must not depend on Qt, provider implementations, or operating-system details.
- `domain` owns pure policy, immutable values, and invariants and must not depend on another project layer.
- `integrations` implements cloud, speech, and third-party adapters; `infrastructure` implements database, file, operating-system, and secure-storage adapters. Both enter through application/domain contracts and must never own the UI.
- Dependencies point `presentation → application → domain`; `integrations` and `infrastructure` are outer adapters injected by the composition root. Cross-layer access uses only public typed ports.
- API keys, OAuth secrets, tokens, and face-identity data must never appear in `config.py`, `app.py`, source constants, logs, or error messages; only approved operating-system secure-storage ports may provide them.
- After migration, `app.py` must be the single composition root with at most 50 physical lines, containing only explicit imports, one argument-free `main()` delegation, and one `__main__` guard. This is a release gate after layered migration, not a demand to pretend unmoved modules have already migrated.

### v4.0.0 platform and Qt compatibility-layer policy

- Whether official PySide6 metadata declares Python 3.15 is no longer a hard gate; verify the layer with fixed-digest official wheel binaries, `6.11.1+mohan.py315.1` metadata, the normal resolver, `pip check`, and Qt smoke.
- Windows is formal support; macOS/Linux are limited Previews. CI-runner evidence is not the developer's physical-device certification and does not claim Windows feature parity.
- Security, secrets, regression, packaged contents, SBOM, SHA-256, artifact integrity, and fallback behavior remain mandatory non-waivable gates.

## 日本語

本書は、人間のコントリビューターと Codex が共同で従う保守契約です。

### 長期的な JARVIS 型パーソナルアシスタント構想とモジュール境界

- 「JARVIS 型」は、長期的に状況を理解し、機器を協調させ、適切な時機に利用者を支援できるパーソナルアシスタントの方向性だけを表します。墨寒は、映画、文学、その他の作品に登場する人物、人格、声、外観、保護された表現の模倣を約束せず、試みてもなりません。
- 本プロジェクトは、コード行数、モジュール数、機能一覧の長さを成果の尺度にしません。各機能は、実際の利用価値、正確性、安全性、プライバシー、保守性、可観測性、既存動作を損なわない証拠によって受入判定します。
- 視覚、音声、記憶、自発的対話、外観、自動化は、それぞれ明確で疎結合な公開境界を持ちます。各機能は独立して有効化／無効化でき、プロバイダーまたは実装を交換でき、依存先が利用不能な場合に安全に縮退できなければなりません。他の機能を同時に有効化したり、巻き添えで停止させたりしてはなりません。
- カメラ、マイク、ディスプレイ、入力機器、スマートホーム、将来の機器は、型付けされた機器インターフェースだけを通じて能力と健全性を提供します。会話、在席、予定、通知、ジェスチャー、知覚、外部サービスの結果は、型付けされたイベントとしてだけシステムへ入ります。ドメインモジュールが機器を直接占有したり、相互の非公開実装を呼び出したりしてはなりません。
- すべての機器状態とイベント候補は、一つのテスト可能で監査可能な仲裁境界で調整した後、最大一つの原子的決定として出力します。仲裁器は優先順位、排他、クールダウン、取消、古い generation、集中保護、権限、安全方針を担当し、複数機能が同時に発話、演出、または同一機器の制御を行うことを防ぎます。
- 医療、健康、安全、金銭、法律、本人性、プライバシー、不可逆な機器制御、その他の高リスク情報では、出力に追跡可能な情報源、観測時刻またはデータ時刻、不確実性、適用限界を含めます。実行または高リスクな結論の形成前に、明確な利用者確認が必要です。情報源の欠落、古いデータ、矛盾、信頼度不足がある場合は、助言、質問、または実行拒否へ明示的に縮退します。
- これは長期的なアーキテクチャ方針と将来機能の受入ゲートであり、v4 の完成、パッケージ化、実機受入合格、公開を示すものではありません。各バージョンは、その時点のソース、テスト、機器受入、SBOM、パッケージ化、公開証拠に基づいて判定します。

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
- ポータブルプロファイル規則には、`profile_transfer.py` という唯一の信頼できる情報源があります。マシン権限、ローカル機器状態、生のローカルパスは携帯しません。機密情報は既定で除外し、利用者が明示的に選択して強いパスワードを指定した場合だけ、`portable_secrets.py` の固定型スキーマに従い、整合性検証済みの独立した `sensitive.enc` へ格納できます。機密情報を SQLite、平文の携帯ファイル、ログ、エラーメッセージへ含めてはいけません。
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

### 視覚感知の許可とデータ境界

- 公開版では、カメラと遠隔画像意味解析を既定で無効にします。利用者がコントロールセンターで明示的に有効化して全体設定を保存すると、自ら無効にするまで継続的な許可となります。フレームごとに許可を求めることはありません。許可状態を常に表示し、利用枠と費用の上限、および直ちに取り消せる操作を提供しなければなりません。
- OpenCV は端末内で継続的かつ低コストの感知を行います。GPT-5.6 が意味解析のために受け取るのは、低頻度またはイベント発生時の一時的な画像一枚だけです。継続的なカメラストリームを遠隔サービスへ直接送ってはいけません。
- 元画像をディスクへ保存してはいけません。Base64 をデータベース、設定、可搬プロファイル、ログ、テレメトリー、エラーメッセージへ含めてはいけません。視覚機能が自らネットワークを有効にしてはならず、保存済みの利用者許可、設定済みサービス、残り利用枠が同時に成立した場合だけ遠隔要求を行えます。
- 利用者は使用量と費用の上限を設定でき、いつでも無効化または未完了の解析を取り消せます。停止後に届いた結果は無効にしなければなりません。カメラ、モデル、SDK、ネットワーク、利用枠、取消処理の失敗は端末内感知や既存機能に影響しません。
- 発行インベントリでは OpenCV のバージョンと検証済みライセンスを固定します。OpenAI Responses API 経路は Python 標準ライブラリの `urllib.request` から HTTPS で直接呼び出します。プロジェクトに `openai` Python SDK の実行時依存は存在せず、追加または架空登録も禁止します。OpenAI は同梱コンポーネントではなく外部サービスであり、SBOM の機械可読な外部サービスポリシーにこの境界を明記します。OpenCV インベントリの欠落、SDK 依存の混入、またはポリシーのずれがあれば、v4 の発行は安全側で失敗させます。

#### ジェスチャーと視覚の融合パイプライン

- ローカルパイプラインは 21 点の手骨格を最大 10 Hz で処理し、短時間だけ有効な口元領域の証拠を最大 1 Hz で取得します。両入力を同一の selfie 座標系へ正規化した後、タイムスタンプ付き融合層で対応付けます。融合証拠は最長 1.5 秒で失効し、古い口元または手の証拠を新しいジェスチャー判断に使用しません。
- 元画像、口元の切り抜き、通常の骨格証拠は処理中の短期メモリだけに存在し、データベース、通常の可搬プロファイル、ログ、テレメトリーへ書き込みません。利用者が明示的に記録したカスタム 21 点骨格サンプルだけを永続化でき、保護された暗号化ストレージへ保存します。通常設定と通常の可搬プロファイルには、有効状態、名前、動作割り当てなどの非機密メタデータだけを保存します。
- 権限未付与、カメラまたはモデルの利用不能、タイムスタンプの逆行、座標正規化の失敗、追跡喪失、信頼度不足の場合、融合結果は不明または派遣なしとして安全側で停止し、既存の会話、音声、2.5D 機能へ影響させません。
- コントローラーはライフサイクル、権限、generation だけを管理します。認識器は正規化済み証拠を候補意図へ変換するだけです。ルーターは利用者の割り当てと安全方針から動作決定を作るだけです。ディスパッチャーは承認済み決定を既存の安全なコマンド境界へ渡すだけです。各層は不変型と狭いインターフェースで接続し、他層のストレージ、UI、カメラ、外部サービスへ直接アクセスしません。
- 本節は開発中のアーキテクチャ契約を示すもので、完全な回帰テスト、パッケージ化、Windows EXE による実カメラ実機検証、正式公開の完了を主張しません。

### 技術的負債ゼロと将来互換性のゲート

- 新機能は最初の実装から、作成／インストール、検証、プレビュー、保存、キャンセル、無効化、削除、移行、不足時のフォールバック、可観測性、回帰テストまでの全ライフサイクルを備えます。後で作り直すことが前提の一時的な近道を完成とは見なしません。
- 設計時には、その時点で信頼して採用できる最新の言語機能、標準ライブラリ、プラットフォーム API、パッケージ形式、安全機構を必ず先回りして評価します。明確さ、性能、安全性、保守性を改善し、完全回帰を損なわない場合は新しい方法を優先し、惰性だけで旧経路を残しません。
- 上流、OS、ハードウェア、依存パッケージが実際には未対応の場合に限り延期できます。延期時は、制約理由、隔離境界、安全な代替、将来の有効化条件、旧経路を削除する責任者、テストを記録し、所有者のない負債にしません。
- 新機能が既存のチャット、音声、表情、記憶、ツール、設定、四言語、プライバシー、安全、クロスプラットフォーム、パッケージ動作を損なう場合は未完成であり、パッケージ化、マージ、公開を禁止します。
- キャラクター外観と 2.5D 視覚変更では、将来のピクセル単位修正を自動ゲートへ置き換えます。固定キャンバスとアンカー、レイヤー深度、透明境界、顔／手／髪／襟の遮蔽、コア同一性領域の変化ゼロ、全表情・全シルエットのフレーム別コンタクトシート監査を必須とします。一つでも突き抜け、ずれ、旧素材の露出があればパック全体を拒否します。

### Codex 指向の保守規則

- 探索マジックやリフレクションより、明示的なインポート、コンストラクター、signal 接続を優先します。
- 外部エンジンとツールには、ダックタイピングされた `Protocol` 境界を優先します。完全な API 自体が意図した不変条件である場合、具体的なドメインオブジェクトは具体型のままで構いません。
- 新機能のサービス、UI、テストには、一致して検索しやすい名前を付けます。
- `app.py` に大規模な機能ロジックを追加してはいけません。これはコンポジションシェルです。
- 機能が別の機能を利用できるのは、文書化された公開メソッド、signal、サービス API を通じる場合だけです。
- 変更に無関係なモジュールまで触れる必要がある場合は、まず不足している公開境界を追加または改善します。
- 新しい依存関係を通すためだけに、アーキテクチャテストを弱めてはいけません。

### デスクトップアプリケーションのレイヤー契約

アーキテクチャゲートは、実体のある五層パッケージ、ルート互換入口、`legacy-root` 件数を分けて報告し、空の `__init__.py` だけで分層完了を示してはなりません。すべてのルート製品名には機械可読な移行先レイヤーと保守 owner が必要で、`legacy-root` はゼロでなければなりません。残すルートファイルは薄い `compatibility-root` に限定し、実装は `presentation`、`application`、`domain`、`integrations`、`infrastructure` のいずれか一つの真の owner にのみ置きます。ルート `app.py` は五十行以下の正式な構成入口として `application.application_bootstrap` を直接使用し、他の互換入口や正式パッケージから逆依存してはなりません。Domain と application の清冊にある全モジュールは実体パッケージへ移行済みで、内部依存はルート互換入口を経由せず、正式な `domain.*` または `application.*` パスを使用します。他層に実体 owner の欠落やルート facade 依存が残る限り、リリースゲートは失敗を維持します。

`presentation` は現在、Companion と Dashboard のウィンドウ構成、各 UI mixin、ダイアログ、初回設定ウィザード、ポータブルプロファイルパネル、テーマパネル／描画、更新パネル、表示層のローカライズカタログを実体として所有します。同名のルートモジュールは検索可能な薄い互換ファサードとしてのみ残し、既存の外部 import を維持します。一方、presentation 内部は真の owner である `presentation.*` を直接参照しなければなりません。`flagship_ui.py` は意図的に別工程へ残しており、この段階で移行済みと表現してはいけません。

`integrations` と `infrastructure` は現在、棚卸し済みの外部サービス、音声プロバイダー、永続化、資産、プラットフォーム、安全ストレージの実装を実体として所有します。同名のルートモジュールは薄い互換 alias のみです。製品内部、テスト、ツールは正式なパッケージ owner を直接 import し、二つの実体レイヤーもルート互換入口を逆向きに経由してはいけません。互換入口と正式 owner は同一 module オブジェクトへ解決し、patch、型 identity、lazy import の callable がずれないようにします。

- `presentation` は Qt ウィンドウ、コントロール、表示モデル、利用者イベントの変換だけを担当し、外部サービスの生成、データベース操作、機密情報の読み取りを直接行いません。
- `application` はユースケース、トランザクション、取消、ポートを調整し、`domain` だけに依存します。Qt、プロバイダー実装、OS 詳細には依存しません。
- `domain` は純粋な方針、不変値、不変条件を所有し、他のプロジェクトレイヤーに依存しません。
- `integrations` はクラウド、音声、第三者サービスのアダプターを実装し、`infrastructure` はデータベース、ファイル、OS、安全ストレージのアダプターを実装します。両者は application/domain 契約を通じて接続し、UI を逆方向に所有しません。
- 依存方向は `presentation → application → domain` です。`integrations` と `infrastructure` はコンポジションルートから注入される外側のアダプターです。レイヤー間では公開された型付きポートだけを使用します。
- API Key、OAuth secret、token、顔識別データを `config.py`、`app.py`、ソース定数、ログ、エラーメッセージへ含めてはいけません。承認済みの OS 安全ストレージポートだけが提供できます。
- 移行完了後の `app.py` は、明示的インポート、引数なしの単一 `main()` 委譲、単一の `__main__` ガードだけを持つ、物理行 50 行以下の唯一の composition root とします。これは分層移行後のリリースゲートであり、未移動モジュールに移行済みを装わせる要求ではありません。

### v4.0.0 プラットフォームと Qt 互換レイヤーのポリシー

- 公式 PySide6 metadata が Python 3.15 を宣言しているかどうかは硬いゲートではありません。固定ダイジェストの公式 wheel バイナリ、`6.11.1+mohan.py315.1` metadata、通常 resolver、`pip check`、Qt smoke で検証します。
- Windows を正式対応とし、macOS/Linux は機能限定 Preview とします。CI runner の証拠は開発者本人の実機認証ではなく、Windows との機能同等性も表明しません。
- セキュリティ、秘密、回帰、パッケージ内容、SBOM、SHA-256、artifact 整合性、フォールバック動作は免除できない必須ゲートです。
