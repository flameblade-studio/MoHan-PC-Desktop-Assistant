# 墨寒架構／墨寒架构／MoHan Architecture／墨寒アーキテクチャ

## 繁體中文

### 仙俠控制中心與外觀分頁

`wardrobe_layout.py` 在窄視窗將人物與控制區改為上下排列並提供整頁捲動。場景與人物共用 `SCENE_GROUND_RATIO`；預覽以可見 Alpha 範圍的底邊定位，透明留白與提示列不影響腳底位置。高對比模式隱藏裝飾背景，保留純色面板與操作元件。

`presentation/dashboard_artwork.py` 擁有可縮放金玉框與場景；裝飾子元件不取得輸入焦點，也不重染人物。`dashboard_theme_materials.py` 將內建色板與既有 v2 佈景語意值接到同一材質介面，`Dashboard._apply_theme_resolution` 維持主題交易入口。雲裳閣以可捲動分頁提供衣裝、髮型、髮飾、妝容與自主選裝；`application/wardrobe_appearance_service.py` 負責獨立髮型／髮飾選擇，原子儲存仍歸 `domain.outfit_pack`。`wardrobe_turntable.py` 只切換既有 24 個角度；預覽繼續使用正式全身合成器。相關驗證包含 `test_wardrobe_ui.py`、`test_wardrobe_preview_composite.py`、`test_wardrobe_appearance_service.py` 與主題交易測試。

可拆卸粉底契約記載於 `docs/makeup-foundation-contract.md`。`domain/outfit_pack_makeup.py` 驗證各狀態的肌膚與眼部開口遮罩；`WardrobeService.active_makeup_slots` 提供所選變體的實際槽位。`ActiveOutfitOverlay` 在臉部動態之後套用妝容並保留原生 Alpha；預覽建置器會將標準遮罩目錄連同安全區文件與封存套件納入。

可選的 `occludes_makeup` 宣告由 `domain/outfit_pack.py` 解析，`domain/outfit_pack_assets.py` 維持幾何與 `PNG` Alpha 的 `fail-closed` 檢查。`infrastructure/appearance_layer_stack.py` 的 `AppearanceLayerStack` 記錄 `makeup_occluder_indices`；`infrastructure/active_outfit_overlay.py` 在 `apply_animated` 使用 `split_makeup_depth`，將明確選擇的衣裝延後到動作與妝容之後，而 `apply` 保留靜態 z-order。省略 `occludes_makeup` 仍等同 `false`；非零 `RGBA` Alpha（含部分透明）參與遮擋。這個欄位只改變 paint depth，不放寬 protected identity 或手部安全界線；衣裝仍須通過既有 Alpha、遮罩與幾何驗證。`tests/test_garment_makeup_occlusion.py` 覆蓋宣告邊界，技術檢查與擁有者的美術外觀核可分開記錄。

本文件是人類貢獻者與 Codex 共同遵守的維護契約。

### 長期賈維斯式個人助理願景與模組邊界

- 「賈維斯式」只描述一個能長期理解情境、協調裝置與適時協助使用者的個人助理方向；墨寒的創作範圍限於自有角色、人格、聲音與外觀，並尊重其他影視、文學及作品的受保護表現。
- 專案不以程式行數、模組數量或功能清單長度衡量成果。每項能力必須以實際使用價值、正確性、安全、隱私、可維護性、可觀測性與不破壞既有功能的證據驗收。
- 視覺、語音、記憶、主動互動、外觀與自動化各自擁有明確且低耦合的公開邊界。每項能力都必須能獨立啟閉、替換供應器或實作、在相依項目暫時無法使用時安全降級，並將啟用狀態與影響限定於自身能力。
- 攝影機、麥克風、顯示器、輸入裝置、智慧家庭及未來裝置只能透過型別化裝置介面提供能力與健康狀態；對話、在席、排程、提醒、手勢、感知與外部服務結果只能透過型別化事件進入系統。領域模組只透過公開裝置介面與公開領域契約協作。
- 所有裝置狀態與事件候選必須先交由單一、可測試、可稽核的仲裁邊界協調，再產生最多一個原子決策。仲裁器負責優先序、互斥、冷卻、取消、過期 generation、專注保護、權限與安全政策，避免多個能力同時說話、動作或控制同一裝置。
- 涉及醫療、健康、安全、金錢、法律、身分、隱私、不可逆裝置控制或其他高風險資訊時，輸出必須攜帶可追溯來源、觀測或資料時間、不確定性與適用限制。執行或形成高風險結論前必須取得清楚的使用者確認；系統只在來源完整、資料有效、內容一致且信心充足時執行；其餘結果明確轉為建議或詢問。
- 這是長期架構方向與未來功能的准入門檻，不是 v4 已完成、已封裝、已通過實機驗收或已發布的宣稱。每個版本仍須以當次程式、測試、裝置驗收、SBOM、封裝及發布證據為準。

### 依賴方向

依賴只能向下指向：

1. `app.py` 是 Windows 角色外殼；`service_container.py` 是明確的執行期組裝根。`preview_app.py` 則是獨立且刻意受限的 macOS／Linux 預覽封裝外殼；它可以顯示平台狀態與在地化內容，其功能範圍限於平台狀態與在地化內容；Windows `app.py`、雲端／語音／工具服務及機密輸入欄位位於此預覽範圍之外。
2. UI 模組（`flagship_ui.py`、`profile_transfer_ui.py`）可以呼叫服務的公開 API。
3. 服務（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）可以使用領域與儲存模組。
4. 領域與儲存模組（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）匯入範圍限於領域與儲存層契約。

本機模組相依須形成有向無環圖，並由 `tests/test_architecture_contracts.py` 強制檢查。

### 功能邊界

- 儀表板分頁透過 `DashboardFeatureRegistry` 掛載。新增分頁只應變更組裝清單，變更範圍限於組裝清單及新增分頁。
- 跨視窗呼叫必須使用公開方法或 Qt signal。`CompanionWindow` 只呼叫 Dashboard 的公開方法或 Qt signal。
- 可替換的語音、Realtime、機密儲存與監聽器依賴，由 `contracts.py` 內小型的 `typing.Protocol` 連接埠描述，並透過 `CompanionServices` 注入 `CompanionWindow`。
- 桌面作業系統行為必須透過 `PlatformServicePort`，以及明確的 `platform_windows.py`、`platform_macos.py`、`platform_linux.py` 介接器進入。`winreg`、`winsound`、`ctypes.windll` 與 `os.startfile` 只由對應平台介接器按平台條件匯入。
- 桌面依賴注入以建構式為基礎。FastAPI 的 `Depends` 只屬於未來的 HTTP 邊界；FastAPI 匯入範圍限於未來 HTTP 邊界。
- OpenAI／Windows 語音時序只有一個真實來源：`lip_sync.py`。
- 參數化分層 2.5D 臉部只有一條資料流：`lip_sync.py` 產生嘴型狀態，`face_motion.py` 合成不可變的臉部參數，`face_renderer.py` 繪製三種姿態；`app.py` 只組裝與顯示。`face_assets.py` 是三姿態素材、尺寸與錨點的權威清冊，現有相容渲染路徑只作為明確回退。
- 可替換的文字轉語音引擎透過 `speech_providers.py` 註冊。供應器可以合成音訊，供應器的擁有範圍限於音訊合成；嘴型同步、表情狀態、UI、權限與備援政策由各自權威模組擁有；經 Windows 驗證的女性本機語音是權威離線備援。
- 持久化的本機語音選擇使用平台中立的 `system-local` 供應器 ID。舊字面 ID `windows-local` 與在地化標籤只可作為遷移輸入，只作為遷移輸入並正規化成 `system-local`。
- 語言政策、回覆語言指示及內建提醒遷移只有一個真實來源：`language_support.py`。英文、簡體中文顯示字串及穩定的內部值至顯示值對應存放於 `ui_localization.py`；在地化標籤只用於顯示，持久化仍使用穩定內部設定值。簡體中文對話路徑使用簡體中文輸出正規化器。
- 回覆前等待表情政策只有一個真實來源：`expression_system.plan_wait_expressions`。畫面上的「思考中」狀態僅供資訊顯示，只顯示 `expression_system.plan_wait_expressions` 選定的角色表情。
- 可攜式設定檔規則只有一個真實來源：`profile_transfer.py`。可攜內容範圍是跨機器共用進度；機器權限、本機裝置狀態、原始本機路徑與一般機密留在來源裝置，只有使用者明確勾選並提供強密碼時，才能依 `portable_secrets.py` 的固定型別格式寫入獨立且通過完整性驗證的 `sensitive.enc`。機密只儲存於核准的安全儲存或明確選擇的加密 `sensitive.enc`。
- 受限的預覽封裝完整維持前述規則。預覽 UI 的金鑰、OAuth、token 欄位與相關功能服務在原生安全儲存完成實作並經真實裝置驗證後啟用。

### 封裝邊界

- Windows ZIP、EXE 與 MSI 仍是唯一完整產品封裝。
- 分開提供的 macOS Apple Silicon（arm64）、Intel（x86_64）DMG，以及 Linux x86_64 AppImage，內含 `preview_app.py`，而非 Windows 的 `app.py` 外殼。其用途是驗證原生封裝、啟動、在地化、路徑與安全邊界。
- Pull Request 可在封裝層級 smoke test 通過後上傳短期 artifact，且輸出範圍限於短期 artifact；GitHub Release 由有效 tag 工作流程建立。
- 只有符合 `vN.N.N` 或 `vN.N.N-rc.N` 規則且已存在的不可變 tag 可以發布多平台版本；正式 tag 建立 Stable Release，RC tag 建立 Pre-release。唯讀中繼資料工作負責收集全部平台輸出並建立 SBOM、中繼資料與 checksum；另一個最小權限工作則重新檢查完全相同的 artifact 與 tag commit、產生證明，並發布單一 Release。
- 發布證據把可觀測性與供應鏈資料視為門檻，而非裝飾。Tachyon 證據必須完成淨化、JIT 驗證、取樣品質檢查，且可由單一二進位資料流重現；原始資料流僅能暫存。CycloneDX 1.7 清冊必須符合鎖定的執行期需求、包含完整根依賴邊、PURL 與宣告的 SPDX 授權，通過官方 schema 與隱私門檻，並分開追蹤僅建置使用的工具。
- 每一個 Windows 與預覽二進位發行包，都必須在終端使用者可閱讀的位置攜帶 MIT 授權與第三方聲明。
- 只有當 AppImage 建置工具的官方來源 commit、資產身分與 SHA-256 均符合已審查常數時，才可接受該工具。GitHub Actions 必須固定至完整 commit SHA。

### 資料所有權

- `db.py`：對話、記憶、任務、靈感、工作紀錄與設定。
- `secret_store.py`：可注入的 `PlatformSecretStoreFactory` 邊界。Windows 使用與使用者綁定的 DPAPI 儲存；未驗證平台使用安全失敗儲存，安全儲存是功能區域唯一的持久化路徑。
- `platform_contracts.py`：平台能力、每位使用者的路徑及桌面服務協定。在尚無經驗證原生安全儲存的平台上，機密只在經驗證的原生安全儲存可用時持久化；其餘情況保持於持久化範圍之外。
- `profile_transfer.py`：可攜的共用進度；排除機器權限與機密。每一個套件都有 snapshot ID；重複匯入相同 snapshot 會被阻擋，較舊 snapshot 則會收到覆寫警告。
- `backup_manager.py`：經驗證的本機變更前備份與每日備份。

### 新增功能的方法

1. 將領域邏輯放入名稱精確的新模組。
2. 定義小型公開 API；只透過其他類別的公開 API 存取。
3. UI 若不只是小型控制項，請放入獨立的 `<feature>_ui.py` 模組。
4. 在組裝點註冊其分頁或面板。
5. 為該功能單獨加入一項契約測試，並加入一項整合 smoke test。
6. 執行 `test_architecture_contracts.py` 與完整回歸測試套件。

若某項行為已有權威擁有者，應擴充該擁有者的公開 API，維持單一設定、計時器與 signal。

### 視覺感知的授權與資料邊界

- 公開版的攝影機與遠端影像語意分析由使用者明確啟用。使用者在控制台明確啟用並全域保存後，即建立持續授權，直到使用者主動關閉。持續授權適用於後續影格；授權狀態必須始終可見，並提供配額、成本上限與立即撤銷控制。
- OpenCV 在本機執行持續、低成本的感知。GPT-5.6 僅接收低頻或事件觸發的一張暫時影像作語意分析，遠端服務的影像輸入限於低頻或事件觸發的單張暫時影像。
- 原始影像保持於短時記憶體並於處理後釋放；資料庫、設定、攜帶檔、日誌、遙測與錯誤訊息只接收已移除 Base64 的內容。網路由已保存的使用者設定啟用；只有已保存的使用者授權、已設定的服務與尚未用盡的配額同時成立時，才可提出遠端請求。
- 使用者可設定用量與成本上限，並可隨時關閉或取消尚未完成的分析。關閉後的延遲結果必須失效；攝影機、模型、SDK、網路、額度或取消失敗不影響本機感知及任何既有功能。
- 發行清冊必須鎖定 OpenCV 版本及經核實授權。OpenAI Responses API 路徑使用 Python 標準庫 `urllib.request` 經 HTTPS 直接呼叫；專案執行期相依範圍採用 Python 標準函式庫 HTTPS 路徑。OpenAI 是外部服務而非封裝元件，SBOM 的機器可讀外部服務政策必須明確記錄此邊界。v4 發行只在 OpenCV 清冊完整、執行期相依符合標準函式庫路徑且政策一致時通過。

#### 手勢與視覺融合管線

- 本機管線以最高 10 Hz 處理手部 21 點骨架，並以最高 1 Hz 取得短時嘴部區域證據。兩者先轉換至一致的 selfie 座標系，再由具時間戳的融合層配對；任何融合證據最長 1.5 秒後失效，新手勢只使用有效期內的嘴部與手部資料推定。
- 原始影像、嘴部裁切與一般骨架證據只存在於處理中的短時記憶體，並於處理後釋放；資料庫、一般攜帶檔、日誌與遙測只接收非敏感中繼資料。只有使用者明確錄製的自訂 21 點骨架樣本可以持久化，且必須進入受保護的加密儲存；一般設定與一般攜帶檔只保存開關、名稱及動作映射等非敏感中繼資料。
- 融合結果只在權限、攝影機、模型、時間戳、座標、追蹤與信心檢查全數通過時派送；其餘結果統一為未知，既有聊天、語音及 2.5D 功能維持運作。
- 控制器只管理生命週期、權限與 generation；辨識器只把正規化證據轉為候選意圖；路由器只依使用者映射與安全政策產生動作決策；派送器只把已核准決策交給既有安全命令邊界。各層以不可變型別與窄介面連接，只透過各層窄介面取得資料與服務。
- 本節描述開發中的架構契約，不代表完整回歸、封裝、Windows EXE 真攝影機實機驗證或正式發布已完成。

### 零技術債與前瞻相容門檻

- 新功能第一次實作就必須涵蓋完整生命週期：建立／安裝、驗證、預覽、保存、取消、停用、刪除、遷移、缺失回退、可觀測性及回歸測試。初次實作即採用可持續維護並涵蓋完整生命週期的路徑。
- 每次設計都要主動評估當下最新且已能可靠採用的語言、標準庫、平台 API、封裝格式與安全機制；在能提升清楚度、效能、安全或維護性且完整回歸不退步時，優先採用新的做法，不因慣性保留舊路徑。
- 只有上游、作業系統、硬體或相依套件尚未真正支援時，才可暫緩。暫緩必須記錄限制原因、隔離邊界、安全替代、未來啟用條件、移除舊路徑的責任與測試，每項暫緩都須明列 owner 與完成條件。
- 任何新增功能若損害既有聊天、語音、表情、記憶、工具、設定、四語、隱私、安全、跨平台或封裝行為，則保持開發中狀態；封裝、合併與發布只接受完整保留既有行為的變更。
- 角色外觀與 2.5D 視覺變更必須把未來逐像素修補轉成自動門檻：固定畫布與錨點、分層深度、透明邊緣、臉／手／髮／衣領遮擋、核心身份區零變動，以及全部表情與姿態逐張接觸表稽核。任一姿態穿模、漂移或露回舊素材即整包拒絕。

### Codex 導向維護規則

- 優先採用明確匯入、建構式與 signal 連線，不採用探索魔法或反射。
- 外部引擎與工具優先使用鴨子型別的 `Protocol` 邊界；若完整 API 就是預期不變量，具體領域物件可以維持具體型別。
- 新功能的服務、UI 與測試應使用一致且可搜尋的名稱。
- `app.py` 的內容限於組裝邏輯；它是組裝外殼。
- 功能只能透過有文件的公開方法、signal 或服務 API 使用其他功能。
- 若變更需要碰觸無關模組，必須先新增或改善缺少的公開邊界。
- 新依賴須在完整維持架構測試的條件下通過。

### 桌面應用分層契約

架構閘門分別報告實體五層套件模組、根相容入口與 `legacy-root` 數量，完成分層須有實體 owner；空 `__init__.py` 只代表套件標記。每個根產品名稱都必須有機器可讀的目標層與維護 owner；`legacy-root` 必須為零，相容性根檔只能是 `compatibility-root` 薄轉接，實作只能存在於 `presentation`、`application`、`domain`、`integrations` 或 `infrastructure` 的單一真正 owner。根 `app.py` 是不超過五十行的正式組合入口，直接使用 `application.application_bootstrap`；其他根相容入口與正式套件的相依方向保持指向正式 owner。Domain 與 application 清冊中的全部模組已由實體套件承接，層內依賴必須直接使用 `domain.*` 或 `application.*` 正式路徑，直接使用正式 owner 路徑；其餘層若缺實體 owner 或仍使用根 facade，發行閘門維持失敗。

`presentation` 現已實體承接 Companion 與 Dashboard 視窗組裝、各自的 UI mixin、對話框、首次設定精靈、攜帶檔面板、主題面板／繪製、更新面板及顯示層在地化目錄。根目錄同名模組只保留可搜尋的薄相容轉接，既有外部匯入仍可使用，但 presentation 內部必須直接指向 `presentation.*` 的真正 owner；`flagship_ui.py` 仍留待獨立遷移，本階段明確標示為待獨立遷移。

`integrations` 與 `infrastructure` 現已實體承接已盤點的外部服務、語音供應器、持久化、資產、平台及安全儲存實作。同名根模組僅為薄相容別名；產品內部、測試與工具必須直接匯入正式套件 owner，兩個實體層皆直接依賴正式套件 owner。相容入口與正式 owner 必須解析為同一 module 物件，避免 patch、型別 identity 或 lazy import callable 漂移。

- `presentation` 只負責 Qt 視窗、控制項、顯示模型與使用者事件轉接；外部服務、資料庫與金鑰只由對應 application／infrastructure 邊界提供。
- `application` 協調使用案例、交易、取消與連接埠，只依賴 `domain`；相依範圍限於 `domain` 契約。
- `domain` 保存純政策、不可變值與不變條件，維持零專案分層相依。
- `integrations` 實作雲端、語音及第三方服務介接器；`infrastructure` 實作資料庫、檔案、作業系統及安全儲存介接器。兩者只能透過 application/domain 契約接入，UI 所有權固定於 presentation。
- 依賴方向為 `presentation → application → domain`；`integrations` 與 `infrastructure` 是由組裝根注入的外圍介接器。跨層只能使用公開、型別化的連接埠。
- API Key、OAuth secret、token 與臉部識別資料只經核准的作業系統安全儲存連接埠使用；`config.py`、`app.py`、原始碼常數、日誌與錯誤訊息的內容範圍限於已移除機密的資料。
- 遷移完成後，`app.py` 必須是最多 50 個實體行的唯一 composition root，只保留明確匯入、單一無參數 `main()` 委派與單一 `__main__` 啟動保護。此限制是完成分層遷移後的發布門檻，不是要求尚未搬移的模組假裝已完成。

### v4.0.0 平台與 Qt 相容層政策

- 官方 PySide6 metadata 是否宣告 Python 3.15，由相容層證據取代單一 metadata 宣告作為閘門；以固定雜湊官方 wheel 二進位、`6.11.1+mohan.py315.1` metadata、正常 resolver、`pip check` 與 Qt smoke 驗證。
- Windows 是正式支援平台；macOS／Linux 是功能受限 Preview。CI runner 證據不等於開發者本人實機認證，也不宣稱 Windows 功能同等。
- 安全、秘密、回歸、包內內容、SBOM、SHA-256、artifact 完整性與回退行為仍是永久適用的必要門檻。

## 简体中文

### 仙侠控制中心与外观分页

`wardrobe_layout.py` 在窄窗口将人物与控制区改为上下排列并提供整页滚动。场景与人物共用 `SCENE_GROUND_RATIO`；预览以可见 Alpha 范围的底边定位，透明留白与提示行不影响脚底位置。高对比度模式隐藏装饰背景，保留纯色面板与操作组件。

`presentation/dashboard_artwork.py` 负责可缩放金玉边框与场景；装饰子组件不获取输入焦点，也不对人物调色。`dashboard_theme_materials.py` 将内置色板与既有 v2 主题语义值接入同一材质接口，`Dashboard._apply_theme_resolution` 保留主题事务入口。云裳阁通过可滚动分页提供衣装、发型、发饰、妆容与自主换装；`application/wardrobe_appearance_service.py` 负责独立发型／发饰选择，原子保存仍由 `domain.outfit_pack` 负责。`wardrobe_turntable.py` 仅切换既有的 24 个角度，预览继续使用正式全身合成器。相关验证包括 `test_wardrobe_ui.py`、`test_wardrobe_preview_composite.py`、`test_wardrobe_appearance_service.py` 和主题事务测试。

可拆卸粉底契约记录在 `docs/makeup-foundation-contract.md` 中。`domain/outfit_pack_makeup.py` 验证各状态的皮肤与眼部开口遮罩；`WardrobeService.active_makeup_slots` 提供所选变体的实际槽位。`ActiveOutfitOverlay` 在面部动态之后套用妆容并保留原生 Alpha；预览构建器会将标准遮罩目录连同安全区文档与封存套件纳入。

可选的 `occludes_makeup` 声明由 `domain/outfit_pack.py` 解析，`domain/outfit_pack_assets.py` 保持几何与 `PNG` Alpha 的 `fail-closed` 检查。`infrastructure/appearance_layer_stack.py` 的 `AppearanceLayerStack` 记录 `makeup_occluder_indices`；`infrastructure/active_outfit_overlay.py` 在 `apply_animated` 使用 `split_makeup_depth`，将明确选择的衣装延后到动作与妆容之后，而 `apply` 保留静态 z-order。省略 `occludes_makeup` 仍等同 `false`；非零 `RGBA` Alpha（含部分透明）参与遮挡。该字段只改变 paint depth，不放宽 protected identity 或手部安全边界；衣装仍须通过既有 Alpha、遮罩与几何验证。`tests/test_garment_makeup_occlusion.py` 覆盖声明边界，技术检查与拥有者的美术外观核可分开记录。

本文档是人类贡献者与 Codex 共同遵守的维护契约。

### 长期贾维斯式个人助理愿景与模块边界

- “贾维斯式”只描述一个能够长期理解情境、协调设备并适时协助用户的个人助理方向；墨寒的创作范围限于自有角色、人格、声音与外观，并尊重其他影视、文学及作品的受保护表现。
- 项目不以代码行数、模块数量或功能清单长度衡量成果。每项能力必须以实际使用价值、正确性、安全、隐私、可维护性、可观测性与不破坏现有功能的证据验收。
- 视觉、语音、记忆、主动交互、外观与自动化分别拥有明确且低耦合的公开边界。每项能力都必须能够独立启停、替换供应商或实现、在依赖项暂时无法使用时安全降级，并将启用状态与影响限定在自身能力。
- 摄像头、麦克风、显示器、输入设备、智能家居及未来设备只能通过强类型设备接口提供能力与健康状态；对话、在场、日程、提醒、手势、感知与外部服务结果只能通过强类型事件进入系统。领域模块只通过公开设备接口与公开领域契约协作。
- 所有设备状态与事件候选必须先交由单一、可测试、可审计的仲裁边界协调，再产生至多一个原子决策。仲裁器负责优先级、互斥、冷却、取消、过期 generation、专注保护、权限与安全策略，避免多个能力同时说话、动作或控制同一设备。
- 涉及医疗、健康、安全、金钱、法律、身份、隐私、不可逆设备控制或其他高风险信息时，输出必须携带可追溯来源、观测或数据时间、不确定性与适用限制。执行或形成高风险结论前必须取得清楚的用户确认；系统只在来源完整、数据有效、内容一致且置信度充足时执行；其余结果明确转为建议或询问。
- 这是长期架构方向与未来功能的准入关卡，不是 v4 已完成、已打包、已通过真机验收或已发布的声明。每个版本仍须以当次代码、测试、设备验收、SBOM、打包及发布证据为准。

### 依赖方向

依赖只能向下指向：

1. `app.py` 是 Windows 角色外壳；`service_container.py` 是明确的运行时装配根。`preview_app.py` 则是独立且刻意受限的 macOS／Linux 预览封装外壳；它可以显示平台状态与本地化内容，其功能范围限于平台状态与本地化内容；Windows `app.py`、云端／语音／工具服务及机密输入字段位于此预览范围之外。
2. UI 模块（`flagship_ui.py`、`profile_transfer_ui.py`）可以调用服务的公开 API。
3. 服务（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）可以使用领域与存储模块。
4. 领域与存储模块（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）的导入范围限于领域与存储层契约。

本地模块依赖须形成有向无环图，并由 `tests/test_architecture_contracts.py` 强制检查。

### 功能边界

- 仪表板分页通过 `DashboardFeatureRegistry` 挂载。新增分页只应变更装配清单，变更范围限于装配清单与新增分页。
- 跨窗口调用必须使用公开方法或 Qt signal。`CompanionWindow` 只调用 Dashboard 的公开方法或 Qt signal。
- 可替换的语音、Realtime、机密存储与监听器依赖，由 `contracts.py` 内小型的 `typing.Protocol` 端口描述，并通过 `CompanionServices` 注入 `CompanionWindow`。
- 桌面操作系统行为必须通过 `PlatformServicePort`，以及明确的 `platform_windows.py`、`platform_macos.py`、`platform_linux.py` 适配器进入。核心模块只通过平台适配器按平台条件导入 `winreg`、`winsound`、`ctypes.windll` 或 `os.startfile`。
- 桌面依赖注入以构造函数为基础。FastAPI 的 `Depends` 只属于未来的 HTTP 边界；FastAPI 导入范围限于未来 HTTP 边界。
- OpenAI／Windows 语音时序只有一个真实来源：`lip_sync.py`。
- 参数化分层 2.5D 脸部只有一条数据流：`lip_sync.py` 生成嘴型状态，`face_motion.py` 合成不可变的脸部参数，`face_renderer.py` 绘制三种姿态；`app.py` 只负责装配与显示。`face_assets.py` 是三姿态素材、尺寸与锚点的权威清单，现有兼容渲染路径只作为明确回退。
- 可替换的文字转语音引擎通过 `speech_providers.py` 注册。提供程序可以合成音频，提供程序的所有权范围限于音频合成；嘴型同步、表情状态、UI、权限与回退策略由各自权威模块拥有；经 Windows 验证的女性本地语音是权威离线回退。
- 持久化的本地语音选择使用平台中立的 `system-local` 提供程序 ID。旧字面 ID `windows-local` 与本地化标签只可作为迁移输入，只作为迁移输入并规范化为 `system-local`。
- 语言策略、回复语言指示及内置提醒迁移只有一个真实来源：`language_support.py`。英文、简体中文显示字符串及稳定的内部值至显示值映射存放于 `ui_localization.py`；本地化标签只用于显示，持久化仍使用稳定内部设置值。简体中文对话路径使用简体中文输出规范化器。
- 回复前等待表情策略只有一个真实来源：`expression_system.plan_wait_expressions`。界面上的“思考中”状态仅供信息显示，只显示 `expression_system.plan_wait_expressions` 选定的角色表情。
- 可移植配置文件规则只有一个真实来源：`profile_transfer.py`。可移植内容范围是跨机器共享进度；机器权限、本地设备状态、原始本地路径与普通机密保留在源设备，只有用户明确勾选并提供强密码时，才能依照 `portable_secrets.py` 的固定类型格式写入独立且通过完整性验证的 `sensitive.enc`。机密只存储在核准的安全存储或明确选择的加密 `sensitive.enc`。
- 受限的预览封装完整维持上述规则。预览 UI 的密钥、OAuth、token 字段与相关功能服务在原生安全存储完成实现并经真实设备验证后启用。

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
- `platform_contracts.py`：平台能力、每位用户的路径及桌面服务协议。在尚无经验证原生安全存储的平台上，机密只在经验证的原生安全存储可用时持久化；其余情况保持在持久化范围之外。
- `profile_transfer.py`：可移植的共享进度；排除机器权限与机密。每一个包都有 snapshot ID；重复导入相同 snapshot 会被阻止，较旧 snapshot 则会收到覆盖警告。
- `backup_manager.py`：经验证的本地变更前备份与每日备份。

### 新增功能的方法

1. 将领域逻辑放入名称精确的新模块。
2. 定义小型公开 API；只通过其他类的公开 API 访问。
3. UI 若不只是小型控件，请放入独立的 `<feature>_ui.py` 模块。
4. 在装配点注册其分页或面板。
5. 为该功能单独加入一项契约测试，并加入一项集成 smoke test。
6. 执行 `test_architecture_contracts.py` 与完整回归测试套件。

若某项行为已有权威拥有者，应扩展该拥有者的公开 API，维持单一设置、计时器与 signal。

### 视觉感知的授权与数据边界

- 公开版的摄像头与远程图像语义分析默认关闭。用户在控制台明确启用并全局保存后，即建立持续授权，直到用户主动关闭。系统不会逐帧询问；授权状态必须始终可见，并提供配额、成本上限与立即撤销控制。
- OpenCV 在本地执行持续、低成本的感知。GPT-5.6 仅接收低频或事件触发的一张临时图像进行语义分析，远程服务的图像输入限于低频或事件触发的单张临时图像。
- 原始图像保持在短时内存并在处理后释放；数据库、设置、可移植文件、日志、遥测与错误信息只接收已移除 Base64 的内容。网络由已保存的用户设置启用；只有已保存的用户授权、已设置的服务与尚未用尽的配额同时成立时，才可发出远程请求。
- 用户可设置用量与成本上限，并可随时关闭或取消尚未完成的分析。关闭后的延迟结果必须失效；摄像头、模型、SDK、网络、额度或取消失败不影响本地感知及任何现有功能。
- 发布清单必须锁定 OpenCV 版本及经核实的许可证。OpenAI Responses API 路径使用 Python 标准库 `urllib.request` 通过 HTTPS 直接调用；项目运行时依赖范围采用 Python 标准库 HTTPS 路径。OpenAI 是外部服务而不是打包组件，SBOM 的机器可读外部服务策略必须明确记录此边界。v4 发布只在 OpenCV 清单完整、运行时依赖符合标准库路径且策略一致时通过。

#### 手势与视觉融合管线

- 本地管线以最高 10 Hz 处理手部 21 点骨架，并以最高 1 Hz 获取短时嘴部区域证据。两者先转换到一致的 selfie 坐标系，再由带时间戳的融合层配对；任何融合证据最长 1.5 秒后失效，新手势只使用有效期内的嘴部与手部数据推断。
- 原始图像、嘴部裁剪与普通骨架证据只存在于处理中的短时内存，并在处理后释放；数据库、普通可移植文件、日志与遥测只接收非敏感元数据。只有用户明确录制的自定义 21 点骨架样本可以持久化，且必须进入受保护的加密存储；普通设置与普通可移植文件只保存开关、名称及动作映射等非敏感元数据。
- 融合结果只在权限、摄像头、模型、时间戳、坐标、跟踪与置信度检查全部通过时派发；其余结果统一为未知，现有聊天、语音及 2.5D 功能维持运行。
- 控制器只管理生命周期、权限与 generation；识别器只将归一化证据转换为候选意图；路由器只依据用户映射与安全策略生成动作决策；派发器只将已批准决策交给现有安全命令边界。各层通过不可变类型与窄接口连接，只通过各层窄接口取得数据与服务。
- 本节描述开发中的架构契约，不代表完整回归、打包、Windows EXE 真摄像头实机验证或正式发布已经完成。

### 零技术债与前瞻兼容门槛

- 新功能第一次实现就必须涵盖完整生命周期：创建／安装、验证、预览、保存、取消、停用、删除、迁移、缺失回退、可观测性及回归测试。初次实现即采用可持续维护并覆盖完整生命周期的路径。
- 每次设计都要主动评估当下最新且已能可靠采用的语言、标准库、平台 API、封装格式与安全机制；在能提升清晰度、性能、安全或维护性且完整回归不退步时，优先采用新的做法，不因惯性保留旧路径。
- 只有上游、操作系统、硬件或依赖包尚未真正支持时，才可暂缓。暂缓必须记录限制原因、隔离边界、安全替代、未来启用条件、移除旧路径的责任与测试，每项暂缓都须明确 owner 与完成条件。
- 任何新增功能若损害现有聊天、语音、表情、记忆、工具、设置、四语、隐私、安全、跨平台或封装行为，则保持开发中状态；封装、合并与发布只接受完整保留现有行为的变更。
- 角色外观与 2.5D 视觉变更必须把未来逐像素修补转成自动门槛：固定画布与锚点、分层深度、透明边缘、脸／手／头发／衣领遮挡、核心身份区零变动，以及全部表情与姿态逐张接触表审核。任一姿态穿模、漂移或露回旧素材即整包拒绝。

### Codex 导向维护规则

- 优先采用明确导入、构造函数与 signal 连接，不采用发现魔法或反射。
- 外部引擎与工具优先使用鸭子类型的 `Protocol` 边界；若完整 API 就是预期不变量，具体领域对象可以保持具体类型。
- 新功能的服务、UI 与测试应使用一致且可搜索的名称。
- `app.py` 的内容限于装配逻辑；它是装配外壳。
- 功能只能通过有文档的公开方法、signal 或服务 API 使用其他功能。
- 若变更需要触及无关模块，必须先新增或改善缺少的公开边界。
- 新依赖须在完整维持架构测试的条件下通过。

### 桌面应用分层契约

架构门禁分别报告实体五层包模块、根兼容入口与 `legacy-root` 数量，完成分层须有实体 owner；空 `__init__.py` 只代表包标记。每个根产品名称都必须有机器可读的目标层与维护 owner；`legacy-root` 必须为零，兼容性根文件只能是 `compatibility-root` 薄转接，实作只能存在于 `presentation`、`application`、`domain`、`integrations` 或 `infrastructure` 的单一真正 owner。根 `app.py` 是不超过五十行的正式组合入口，直接使用 `application.application_bootstrap`；其他根兼容入口与正式包的依赖方向保持指向正式 owner。Domain 与 application 清册中的全部模块已由实体包承接，层内依赖必须直接使用 `domain.*` 或 `application.*` 正式路径，直接使用正式 owner 路径；其余层若缺实体 owner 或仍使用根 facade，发行门禁维持失败。

`presentation` 现已实体承接 Companion 与 Dashboard 窗口装配、各自的 UI mixin、对话框、首次设置向导、便携档案面板、主题面板／绘制、更新面板及显示层本地化目录。根目录同名模块只保留可搜索的薄兼容转接，既有外部导入仍可使用，但 presentation 内部必须直接指向 `presentation.*` 的真正 owner；`flagship_ui.py` 仍留待独立迁移，本阶段明确标示为待独立迁移。

`integrations` 与 `infrastructure` 现已实体承接已盘点的外部服务、语音供应商、持久化、资产、平台及安全存储实现。同名根模块仅为薄兼容别名；产品内部、测试与工具必须直接导入正式包 owner，这两个实体层均直接依赖正式包 owner。兼容入口与正式 owner 必须解析为同一 module 对象，避免 patch、类型 identity 或 lazy import callable 漂移。

- `presentation` 只负责 Qt 窗口、控件、显示模型与用户事件转接；外部服务、数据库与密钥只由对应 application／infrastructure 边界提供。
- `application` 协调用例、事务、取消与端口，只依赖 `domain`；依赖范围限于 `domain` 契约。
- `domain` 保存纯策略、不可变值与不变量，保持零项目分层依赖。
- `integrations` 实现云端、语音及第三方服务适配器；`infrastructure` 实现数据库、文件、操作系统及安全存储适配器。两者只能通过 application/domain 契约接入，UI 所有权固定在 presentation。
- 依赖方向为 `presentation → application → domain`；`integrations` 与 `infrastructure` 是由装配根注入的外围适配器。跨层只能使用公开、强类型端口。
- API Key、OAuth secret、token 与人脸识别数据只通过核准的操作系统安全存储端口使用；`config.py`、`app.py`、源代码常量、日志和错误信息的内容范围限于已移除机密的数据。
- 迁移完成后，`app.py` 必须是最多 50 个物理行的唯一 composition root，只保留明确导入、单一无参数 `main()` 委派与单一 `__main__` 启动保护。此限制是完成分层迁移后的发布门槛，尚待迁移的模块保持明确标记。

### v4.0.0 平台与 Qt 兼容层政策

- 官方 PySide6 metadata 是否声明 Python 3.15，由兼容层证据取代单一 metadata 声明作为关卡；使用固定哈希官方 wheel 二进制、`6.11.1+mohan.py315.1` metadata、正常 resolver、`pip check` 与 Qt smoke 验证。
- Windows 是正式支持平台；macOS／Linux 是功能受限 Preview。CI runner 证据不等于开发者本人实机认证，也不声明 Windows 功能同等。
- 安全、秘密、回归、包内内容、SBOM、SHA-256、artifact 完整性与回退行为仍是永久适用的必要门槛。

## English

### Celestial dashboard and appearance categories

`wardrobe_layout.py` stacks the character and controls in narrow windows and scrolls the full page. The scene and character share `SCENE_GROUND_RATIO`; the preview anchors the bottom of the visible alpha bounds anchoring the feet independently of transparent padding and status rows. High-contrast mode hides decorative backgrounds while retaining solid panels and controls.

`presentation/dashboard_artwork.py` owns resizable gold/jade frames and scenery. Decorative children neither capture input nor recolor the character. `dashboard_theme_materials.py` maps built-in palettes and existing v2 theme tokens to one material interface; `Dashboard._apply_theme_resolution` remains the theme transaction entry point. Scrollable wardrobe categories expose outfits, hair, headwear, makeup, and autonomy. `application/wardrobe_appearance_service.py` handles independent hair/headwear choices while `domain.outfit_pack` retains atomic persistence. `wardrobe_turntable.py` selects only the existing 24 angles, using the production full-body compositor. Relevant coverage includes `test_wardrobe_ui.py`, `test_wardrobe_preview_composite.py`, `test_wardrobe_appearance_service.py`, and theme transaction tests.

The detachable foundation contract is documented in `docs/makeup-foundation-contract.md`.
`domain/outfit_pack_makeup.py` validates state-specific skin and eye-aperture masks;
`WardrobeService.active_makeup_slots` exposes the selected variant's actual slots.
`ActiveOutfitOverlay` applies makeup with SourceAtop after facial motion, retaining
native alpha. The preview builder includes the canonical mask directories with
the safe-region document and sealed packs.

The optional `occludes_makeup` declaration is parsed by `domain/outfit_pack.py`, while `domain/outfit_pack_assets.py` keeps geometry and `PNG` alpha checks `fail-closed`. `infrastructure/appearance_layer_stack.py` records `makeup_occluder_indices` on `AppearanceLayerStack`; `infrastructure/active_outfit_overlay.py` uses `split_makeup_depth` in `apply_animated` to delay explicitly selected garments until after motion and makeup, while `apply` preserves static z-order. An omitted `occludes_makeup` remains `false`; nonzero `RGBA` alpha, including partial alpha, participates in occlusion. The field changes paint depth only; it fully preserves protected identity and hand-safety boundaries, and garments still pass the existing Alpha, mask, and geometry checks. `tests/test_garment_makeup_occlusion.py` covers the declaration boundary, and technical checks remain separate from the owner's visual approval.

This file is the maintenance contract shared by human contributors and Codex.

### Long-term JARVIS-style personal-assistant vision and module boundaries

- “JARVIS-style” describes only the direction of a personal assistant that can understand context over time, coordinate devices, and help the user at appropriate moments. MoHan's creative scope consists of its original character, personality, voice, and appearance, with protected expression from other film, literature, and works respected.
- The project measures achievement through practical user value, correctness, safety, privacy, maintainability, observability, and preservation of established behavior. Every capability must be accepted through evidence of practical user value, correctness, safety, privacy, maintainability, observability, and preservation of established behavior.
- Vision, speech, memory, proactive interaction, appearance, and automation each have an explicit, loosely coupled public boundary. Every capability must support independent enablement and disablement, replacement of its provider or implementation, and safe degradation when a dependency is unavailable, with enablement and impact contained to that capability.
- Cameras, microphones, displays, input devices, smart-home systems, and future devices expose capabilities and health only through typed device interfaces. Conversation, presence, schedules, reminders, gestures, perception, and external-service results enter only as typed events. Domain modules collaborate only through public device interfaces and public domain contracts.
- Every device state and event candidate must pass through one testable and auditable arbitration boundary before the system emits at most one atomic decision. The arbitrator owns priority, mutual exclusion, cooldowns, cancellation, stale generations, focus protection, permissions, and safety policy so at most one capability speaks, performs, or controls a device at a time.
- For medical, wellbeing, safety, financial, legal, identity, privacy, irreversible device-control, or other high-risk information, output must carry a traceable source, observation or data time, uncertainty, and applicability limits. Clear user confirmation is required before execution or formation of a high-risk conclusion. Missing sources, stale data, contradictions, or insufficient confidence must explicitly degrade to advice, a question, or refusal to act.
- This is a long-term architecture direction and an admission gate for future capabilities, while v4 completion, packaging, real-device acceptance, and release remain governed by their dedicated evidence. Each version remains governed by its own source, test, device-acceptance, SBOM, packaging, and release evidence.

### Dependency direction

Dependencies point downward only:

1. `app.py` is the Windows character shell; `service_container.py` is the explicit runtime composition root. `preview_app.py` is a separate, deliberately limited macOS/Linux Preview package shell; it may display platform status and localization, and its scope is limited to platform status and localization; Windows `app.py`, cloud/voice/tool services, and secret inputs remain outside that Preview scope.
2. UI modules (`flagship_ui.py`, `profile_transfer_ui.py`) may call public service APIs.
3. Services (`profile_transfer.py`, `speech.py`, `realtime_voice.py`, `ai_client.py`, `cloud_connectors.py`, `home_assistant.py`, `remote_control.py`) may use domain and storage modules.
4. Domain and storage modules (`db.py`, `flagship_core.py`, `expression_system.py`, `lip_sync.py`, `face_rig.py`, `face_motion.py`, `face_assets.py`, `face_renderer.py`, `workflow_engine.py`) import only domain and storage contracts.

Local-module dependencies form a directed acyclic graph and enforced by `tests/test_architecture_contracts.py`.

### Feature boundaries

- Dashboard tabs are mounted through `DashboardFeatureRegistry`. Adding a tab changes the composition list, while preserving unrelated tabs.
- Cross-window calls use public methods or Qt signals. `CompanionWindow` calls only Dashboard public methods or Qt signals.
- Replaceable speech, Realtime, secret-store, and listener dependencies are described by small `typing.Protocol` ports in `contracts.py` and enter `CompanionWindow` through `CompanionServices`.
- Desktop operating-system behavior enters through `PlatformServicePort` and the explicit `platform_windows.py`, `platform_macos.py`, and `platform_linux.py` adapters. Core modules import platform facilities only through their platform adapter: `winreg`, `winsound`, `ctypes.windll`, or `os.startfile` unconditionally.
- Desktop dependency injection is constructor-based. FastAPI `Depends` belongs only in a future HTTP boundary; FastAPI imports are limited to the future HTTP boundary.
- OpenAI/Windows speech timing has one source of truth: `lip_sync.py`.
- The parametric layered 2.5D face has one data flow: `lip_sync.py` produces articulation state, `face_motion.py` combines immutable face parameters, and `face_renderer.py` draws all three poses; `app.py` only composes and displays them. `face_assets.py` is the authoritative manifest for three-pose assets, dimensions, and anchors, while the compatible renderer is an explicit rollback path only.
- Replaceable text-to-speech engines register through `speech_providers.py`. Providers may synthesize audio and their ownership is limited to audio synthesis; the canonical modules own lip sync, expression state, UI, permissions, and fallback policy; Windows verified-female local speech is the authoritative offline fallback.
- Persisted local-speech selection uses the platform-neutral `system-local` provider ID. The literal legacy ID `windows-local` and localized labels are migration inputs only; they normalize to `system-local` during migration.
- Language policy, response-language instructions, and built-in reminder migration have one source of truth in `language_support.py`. English and Simplified Chinese display strings and stable internal-to-display mappings live in `ui_localization.py`; localized labels serve display only, while persistence keeps stable internal setting values. Simplified Chinese conversation paths use the Simplified Chinese output normalizer.
- Pre-reply wait-expression policy has one source of truth in `expression_system.plan_wait_expressions`. The visible “thinking” status is informational and displays only the character expression selected by `expression_system.plan_wait_expressions`.
- Portable-profile rules have one source of truth: `profile_transfer.py`. Portable content is limited to cross-machine shared progress; machine permissions, local device state, and raw local paths remain on the source device. Secrets are excluded by default and may enter only a separate, integrity-checked `sensitive.enc` when the user explicitly opts in and supplies a strong password, using the fixed typed schema in `portable_secrets.py`. Secrets remain exclusively in approved secure storage or the explicitly selected encrypted `sensitive.enc`.
- A limited Preview package fully preserves these rules. Until a native secure store is implemented and device-validated, key, OAuth, and token fields and their feature services become available after native secure storage is implemented and device-validated.

### Package boundaries

- Windows ZIP, EXE, and MSI remain the only complete product packages.
- Separate macOS Apple Silicon (arm64) and Intel (x86_64) DMGs plus the Linux x86_64 AppImage use `preview_app.py` as their dedicated shell, while Windows uses `app.py`. Their purpose is native packaging, startup, localization, path, and safety-boundary validation.
- Pull requests may upload short-lived package artifacts after a package-level smoke test. Their output is limited to short-lived artifacts; the valid-tag workflow creates the GitHub Release.
- Only an existing immutable tag matching `vN.N.N` or `vN.N.N-rc.N` may publish multi-platform packages; stable tags create Stable Releases and RC tags create Pre-releases. A read-only metadata job gathers all platform outputs and creates SBOMs, metadata, and checksums; a separate minimal privileged job rechecks the exact artifacts and tag commit, attests them, and publishes one Release.
- Release evidence treats observability and supply-chain data as release gates. Tachyon evidence must be sanitized, JIT-verified, sample-quality checked, and reproducible from one binary stream; raw streams are temporary. CycloneDX 1.7 inventories must match pinned runtime requirements, include complete root dependency edges, PURLs and declared SPDX licenses, pass the official schema and privacy gates, and track build-only tools separately.
- Every Windows and Preview binary distribution carries the MIT license and third-party notices in an end-user-readable location.
- The AppImage build tool is accepted only when its official source commit, asset identity, and SHA-256 match the reviewed constants. GitHub Actions are pinned to complete commit SHAs.

### Data ownership

- `db.py`: conversations, memories, tasks, ideas, work history, and settings.
- `secret_store.py`: the injectable `PlatformSecretStoreFactory` boundary. Windows receives user-bound DPAPI stores; an unverified platform receives a fail-closed store, with secure storage as the sole feature persistence path.
- `platform_contracts.py`: platform capabilities, per-user paths, and the desktop service protocol. On a platform without verified native secure storage, secret persistence fails closed instead of writing plaintext.
- `profile_transfer.py`: portable shared progress; machine permissions and secrets are excluded. Every bundle has a snapshot ID; importing the same snapshot twice is blocked, and older snapshots receive an overwrite warning.
- `backup_manager.py`: verified local pre-change and daily backups.

### How to add a feature

1. Put domain logic in a new, narrowly named module.
2. Define a small public API; use only the other class's public API.
3. Put UI in a separate `<feature>_ui.py` module when it is more than a small control.
4. Register its tab or panel at the composition point.
5. Add a contract test for the feature alone and one integration smoke test.
6. Run `test_architecture_contracts.py` and the full regression suite.

Extend the canonical owner's public API, preserving one setting, timer, and signal for the behavior.

### Vision authorization and data boundary

- Camera access and remote image semantics are enabled explicitly by the user in public builds. Explicitly enabling and globally saving the feature in the control center establishes continuous authorization until the user turns it off. Continuous authorization applies to subsequent frames; authorization status must remain visible, with quota and cost limits and immediate revocation controls.
- OpenCV performs continuous, low-cost perception locally. GPT-5.6 receives only one transient image at a low frequency or on an event trigger for semantic analysis; remote image input is limited to one transient image at low frequency or on an event trigger.
- Raw images remain in short-lived memory and are released after processing. Databases, settings, portable profiles, logs, telemetry, and error messages receive content from which Base64 has been removed. Saved user settings enable networking; a remote request requires saved user authorization, a configured service, and remaining quota at the same time.
- Users can set usage and cost limits and can turn off the feature or cancel unfinished analysis at any time. Late results after shutdown expire. The camera, model, SDK, network, quota, and cancellation boundaries isolate each unavailable path while local perception and established features remain operational.
- The release inventory must pin OpenCV and its verified license. The OpenAI Responses API path calls HTTPS directly through Python's standard-library `urllib.request`; the project runtime dependency scope uses the Python standard-library HTTPS path. OpenAI is an external service, not a packaged component, and the SBOM's machine-readable external-service policy must record that boundary. The v4 release passes only with a complete OpenCV inventory, the standard-library runtime path, and aligned policy.

#### Gesture and vision fusion pipeline

- The local pipeline processes 21-point hand skeletons at up to 10 Hz and obtains short-lived mouth-region evidence at up to 1 Hz. Both inputs are normalized into one selfie coordinate system before a timestamped fusion layer pairs them. Every fused observation expires after at most 1.5 seconds; new gesture decisions use only mouth and hand evidence within its validity window.
- Raw images, mouth crops, and ordinary skeleton evidence exist only in short-lived processing memory and is released after processing; databases, ordinary portable profiles, logs, and telemetry receive only non-sensitive metadata. Only custom 21-point skeleton samples that the user explicitly records may persist, and they must enter protected encrypted storage. Ordinary settings and portable profiles retain only non-sensitive metadata such as switches, names, and action mappings.
- Missing permission, unavailable cameras or models, non-monotonic timestamps, coordinate-normalization failure, lost tracking, or insufficient confidence makes fusion fail closed to unknown or no dispatch without harming established chat, speech, or 2.5D behavior.
- The controller owns lifecycle, authorization, and generation only. The recognizer converts normalized evidence into candidate intents only. The router applies user mappings and safety policy to produce action decisions only. The dispatcher forwards approved decisions to the established safe-command boundary only. Immutable types and narrow interfaces connect these layers; no layer may directly reach into another layer's storage, UI, camera, or external service.
- This section defines an architecture contract under development. Full regression testing, packaging, real-camera validation in the Windows EXE, and release each retain their dedicated completion evidence.

### Zero-technical-debt and forward-compatibility gate

- A feature's first implementation covers its whole lifecycle: creation or installation, validation, preview, save, cancel, disable, removal, migration, missing-content fallback, observability, and regression tests. The first implementation uses a maintainable path that covers the whole lifecycle.
- Every design proactively evaluates the newest language, standard-library, platform API, package format, and security mechanism that is currently reliable. Adopt the newer approach when it improves clarity, performance, security, or maintainability while preserving full regression; retain a legacy path only when its documented value supports it.
- Deferral is allowed only when the capability still awaits genuine support from an upstream, operating system, hardware platform, or dependency. Record the constraint, isolation boundary, safe alternative, future activation trigger, owner of legacy-path removal, and tests with an explicit owner and completion trigger for every deferral.
- A new feature that harms established chat, speech, expression, memory, tool, settings, four-language, privacy, security, portability, or packaging behavior remains in development; packaging, merging, and release accept only changes that fully preserve established behavior.
- Character-appearance and 2.5D visual work converts future pixel-by-pixel repair into automated gates: fixed canvases and anchors, layer depth, transparent edges, face/hand/hair/collar occlusion, zero change in core identity regions, and per-frame contact-sheet review across every expression and silhouette. Any clipping, drift, or exposure of an old asset rejects the complete pack.

### Codex-oriented maintenance rules

- Prefer explicit imports, constructors, and signal connections over discovery magic or reflection.
- Prefer duck-typed `Protocol` boundaries for external engines and tools. Concrete domain objects may remain concrete when their full API is the intended invariant.
- Keep a new feature's service, UI, and tests under matching searchable names.
- Keep `app.py` limited to composition logic; it is a composition shell.
- A feature may use another feature only through a documented public method, signal, or service API.
- If a change requires touching unrelated modules, first add or improve the missing public boundary.
- A new dependency passes while all architecture tests remain fully enforced.

### Desktop application layering contract

The architecture gate reports physical five-layer package modules, root compatibility entries, and the `legacy-root` count separately; empty `__init__.py` files represent package markers; completed layering requires a physical owner. Every root product name requires a machine-readable target layer and maintenance owner. `legacy-root` must remain zero, and a retained root file may only be a thin `compatibility-root` entry while implementation exists under exactly one true owner in `presentation`, `application`, `domain`, `integrations`, or `infrastructure`. Root `app.py` is the formal composition entrypoint, remains at most fifty lines, and imports `application.application_bootstrap` directly; compatibility roots and package modules keep their dependency direction toward canonical owners. Every domain and application inventory module now has a physical package owner, and internal dependencies must use canonical `domain.*` or `application.*` paths instead of detouring through root compatibility entries. A missing physical owner or root-facade dependency in another layer keeps the release gate red.

`presentation` now physically owns the Companion and Dashboard window compositions, their UI mixins, dialogs, first-run wizard, portable-profile panel, theme panel/rendering, update panel, and presentation-localization catalogs. Same-named root modules remain only as searchable thin compatibility facades, so existing external imports continue to work, while internal presentation imports must target the true `presentation.*` owners directly. `flagship_ui.py` remains intentionally deferred and is explicitly represented as pending its dedicated migration phase.

`integrations` and `infrastructure` now physically own the inventoried external-service, speech-provider, persistence, asset, platform, and secure-storage implementations. Same-named root modules are thin compatibility aliases only. Product internals, tests, and tools must import canonical package owners directly, and both physical layers route directly to canonical package owners. A compatibility entrypoint and its canonical owner must resolve to the same module object keeping patching, type identity, and lazy-import callability aligned.

- `presentation` owns only Qt windows, controls, view models, and user-event adaptation; external services, database access, and secrets enter only through the corresponding application/infrastructure boundaries.
- `application` coordinates use cases, transactions, cancellation, and ports and depends only on `domain`; its dependency scope is limited to `domain` contracts.
- `domain` owns pure policy, immutable values, and invariants and has zero dependencies on other project layers.
- `integrations` implements cloud, speech, and third-party adapters; `infrastructure` implements database, file, operating-system, and secure-storage adapters. Both enter through application/domain contracts and leave UI ownership exclusively in presentation.
- Dependencies point `presentation → application → domain`; `integrations` and `infrastructure` are outer adapters injected by the composition root. Cross-layer access uses only public typed ports.
- API keys, OAuth secrets, tokens, and face-identity data are provided only through approved operating-system secure-storage ports; `config.py`, `app.py`, source constants, logs, and error messages contain sanitized data.
- After migration, `app.py` must be the single composition root with at most 50 physical lines, containing only explicit imports, one argument-free `main()` delegation, and one `__main__` guard. This is a release gate after layered migration, while unmoved modules remain explicitly marked for migration.

### v4.0.0 platform and Qt compatibility-layer policy

- Whether official PySide6 metadata declares Python 3.15 is no longer a hard gate; verify the layer with fixed-digest official wheel binaries, `6.11.1+mohan.py315.1` metadata, the normal resolver, `pip check`, and Qt smoke.
- Windows is formal support; macOS/Linux are limited Previews. CI-runner evidence covers CI-runner validation; developer physical-device certification and Windows feature parity use their own evidence.
- Security, secrets, regression, packaged contents, SBOM, SHA-256, artifact integrity, and fallback behavior remain mandatory non-waivable gates.

## 日本語

### 仙侠ダッシュボードと外観カテゴリ

`wardrobe_layout.py` は狭いウィンドウで人物と操作部を縦に並べ、ページ全体をスクロールします。背景と人物は `SCENE_GROUND_RATIO` を共有し、可視アルファ領域の下端を基準に配置するため、透明な余白や状態表示によって足元がずれません。高コントラストモードでは装飾背景を非表示にし、単色パネルと操作部を維持します。

`presentation/dashboard_artwork.py` は伸縮可能な金・翡翠の枠と風景を担当します。装飾用の子部品は入力フォーカスを取らず、人物を着色しません。`dashboard_theme_materials.py` が組み込み色板と既存 v2 テーマを共通の材質インターフェースへ変換し、`Dashboard._apply_theme_resolution` がテーマ取引の入口を維持します。雲裳閣には衣装・髪型・髪飾り・メイク・自動着替えのスクロール可能なタブがあります。`application/wardrobe_appearance_service.py` が髪型と髪飾りの個別選択を担当し、原子的な保存は `domain.outfit_pack` に残します。`wardrobe_turntable.py` は既存の 24 方向だけを選択し、正式な全身合成器でプレビューします。関連する検証は `test_wardrobe_ui.py`、`test_wardrobe_preview_composite.py`、`test_wardrobe_appearance_service.py` およびテーマ取引テストです。

着脱式ファンデーション契約は `docs/makeup-foundation-contract.md` に記載します。`domain/outfit_pack_makeup.py` は状態別の肌と目の開口マスクを検証し、`WardrobeService.active_makeup_slots` は選択したバリアントの実際のスロットを公開します。`ActiveOutfitOverlay` は顔の動きの後にメイクを適用して元の Alpha を保持し、プレビュー・ビルダーは標準マスクのディレクトリを安全領域文書と封止済みパックとともに含めます。

任意指定の `occludes_makeup` は `domain/outfit_pack.py` で解析し、`domain/outfit_pack_assets.py` はジオメトリと `PNG` Alpha の `fail-closed` 検査を保持します。`infrastructure/appearance_layer_stack.py` の `AppearanceLayerStack` は `makeup_occluder_indices` を記録し、`infrastructure/active_outfit_overlay.py` は `apply_animated` で `split_makeup_depth` を使い、明示的に選択された衣装を動きとメイクの後へ遅らせます。`apply` は静的な z-order を維持します。`occludes_makeup` を省略した場合は `false` と同じで、部分透明を含む非ゼロ `RGBA` Alpha が遮蔽に参加します。この欄は paint depth だけを変え、protected identity や手部安全境界を緩和しません。衣装は従来の Alpha、マスク、ジオメトリ検査にも通過する必要があります。`tests/test_garment_makeup_occlusion.py` は宣言境界をカバーし、技術検査と所有者の外観承認は別に記録します。

本書は、人間のコントリビューターと Codex が共同で従う保守契約です。

### 長期的な JARVIS 型パーソナルアシスタント構想とモジュール境界

- 「JARVIS 型」は、長期的に状況を理解し、機器を協調させ、適切な時機に利用者を支援できるパーソナルアシスタントの方向性だけを表します。墨寒は、映画、文学、その他の作品に登場する人物、人格、声、外観、保護された表現の模倣を約束せず、試みてもなりません。
- 本プロジェクトは、コード行数、モジュール数、機能一覧の長さを成果の尺度にしません。各機能は、実際の利用価値、正確性、安全性、プライバシー、保守性、可観測性、既存動作を損なわない証拠によって受入判定します。
- 視覚、音声、記憶、自発的対話、外観、自動化は、それぞれ明確で疎結合な公開境界を持ちます。各機能は独立して有効化／無効化でき、プロバイダーまたは実装を交換でき、依存先が一時的に利用可能範囲外の場合に安全に縮退できなければなりません。有効化状態と影響を各機能の内部に限定します。
- カメラ、マイク、ディスプレイ、入力機器、スマートホーム、将来の機器は、型付けされた機器インターフェースだけを通じて能力と健全性を提供します。会話、在席、予定、通知、ジェスチャー、知覚、外部サービスの結果は、型付けされたイベントとしてだけシステムへ入ります。ドメインモジュールが機器を直接占有したり、相互の非公開実装を呼び出したりしてはなりません。
- すべての機器状態とイベント候補は、一つのテスト可能で監査可能な仲裁境界で調整した後、最大一つの原子的決定として出力します。仲裁器は優先順位、排他、クールダウン、取消、古い generation、集中保護、権限、安全方針を担当し、複数機能が同時に発話、演出、または同一機器の制御を行うことを防ぎます。
- 医療、健康、安全、金銭、法律、本人性、プライバシー、不可逆な機器制御、その他の高リスク情報では、出力に追跡可能な情報源、観測時刻またはデータ時刻、不確実性、適用限界を含めます。実行または高リスクな結論の形成前に、明確な利用者確認が必要です。情報源の欠落、古いデータ、矛盾、信頼度不足がある場合は、実行条件が揃うまで助言または質問へ明示的に縮退します。
- これは長期的なアーキテクチャ方針と将来機能の受入ゲートであり、v4 の完成、パッケージ化、実機受入合格、公開はそれぞれ専用の証拠で判定します。各バージョンは、その時点のソース、テスト、機器受入、SBOM、パッケージ化、公開証拠に基づいて判定します。

### 依存関係の方向

依存関係は下位方向にだけ向けます。

1. `app.py` は Windows のキャラクターシェルであり、`service_container.py` は明示的な実行時コンポジションルートです。`preview_app.py` は独立した、意図的に制限された macOS／Linux Preview パッケージシェルです。プラットフォーム状態とローカライズ内容は表示できますが、機能範囲はプラットフォーム状態とローカライズ内容に限定し、Windows `app.py`、クラウド／音声／ツールサービス、機密入力欄は Preview 範囲外です。
2. UI モジュール（`flagship_ui.py`、`profile_transfer_ui.py`）は、サービスの公開 API を呼び出せます。
3. サービス（`profile_transfer.py`、`speech.py`、`realtime_voice.py`、`ai_client.py`、`cloud_connectors.py`、`home_assistant.py`、`remote_control.py`）は、ドメインおよびストレージモジュールを利用できます。
4. ドメインおよびストレージモジュール（`db.py`、`flagship_core.py`、`expression_system.py`、`lip_sync.py`、`face_rig.py`、`face_motion.py`、`face_assets.py`、`face_renderer.py`、`workflow_engine.py`）のインポート範囲はドメイン層とストレージ層の契約に限定します。

ローカルモジュールの依存関係を有向非巡回グラフとして維持し、`tests/test_architecture_contracts.py` で強制検査します。

### 機能境界

- ダッシュボードのタブは `DashboardFeatureRegistry` を通じてマウントします。タブを追加するときはコンポジション一覧だけを変更し、変更範囲を構成一覧と新規タブに限定します。
- ウィンドウ間の呼び出しには公開メソッドまたは Qt signal を使用します。`CompanionWindow` は Dashboard の公開メソッドまたは Qt signal だけを呼び出します。
- 交換可能な音声、Realtime、機密ストア、リスナーの依存関係は、`contracts.py` にある小さな `typing.Protocol` ポートで記述し、`CompanionServices` を通じて `CompanionWindow` に注入します。
- デスクトップ OS の動作は、`PlatformServicePort` と明示的な `platform_windows.py`、`platform_macos.py`、`platform_linux.py` アダプターを通じて導入します。コアモジュールは `winreg`、`winsound`、`ctypes.windll`、`os.startfile` は該当プラットフォームアダプターから条件付きでインポートします。
- デスクトップの依存性注入はコンストラクター方式とします。FastAPI の `Depends` は将来の HTTP 境界だけに属し、FastAPI のインポート範囲は将来の HTTP 境界に限定します。
- OpenAI／Windows の音声タイミングには、`lip_sync.py` という唯一の信頼できる情報源があります。
- パラメトリック多層 2.5D フェイスのデータフローは一つだけです。`lip_sync.py` が口形状態を生成し、`face_motion.py` が不変の顔パラメーターを統合し、`face_renderer.py` が三姿勢を描画します。`app.py` は構成と表示だけを担当します。`face_assets.py` は三姿勢の素材、寸法、アンカーの権威あるマニフェストであり、現行互換レンダラーは明示的なロールバック経路としてのみ残します。
- 交換可能なテキスト読み上げエンジンは `speech_providers.py` を通じて登録します。プロバイダーは音声を合成できますが、リップシンク、表情状態、UI、権限、フォールバック方針の所有権は各正式モジュールに置き、プロバイダーは音声合成だけを所有します。Windows で検証済みの女性ローカル音声を正式なオフラインフォールバックとします。
- 永続化するローカル音声の選択には、プラットフォーム中立の `system-local` プロバイダー ID を使用します。旧リテラル ID `windows-local` とローカライズ済みラベルは移行入力に限り、移行時に `system-local` へ正規化します。
- 言語方針、応答言語の指示、組み込みリマインダーの移行には、`language_support.py` という唯一の信頼できる情報源があります。英語および簡体字中国語の表示文字列と、安定した内部値から表示値への対応は `ui_localization.py` に置きます。ローカライズ済みラベルは表示だけに使い、永続化には安定した内部設定値を使います。簡体字中国語の会話経路は簡体字中国語の出力正規化処理を使います。
- 応答前の待機表情方針には、`expression_system.plan_wait_expressions` という唯一の信頼できる情報源があります。画面上の「思考中」状態は情報表示だけに使用し、`expression_system.plan_wait_expressions` が選択した表情だけを表示します。
- ポータブルプロファイル規則には、`profile_transfer.py` という唯一の信頼できる情報源があります。マシン権限、ローカル機器状態、生のローカルパスは携帯しません。機密情報は既定で除外し、利用者が明示的に選択して強いパスワードを指定した場合だけ、`portable_secrets.py` の固定型スキーマに従い、整合性検証済みの独立した `sensitive.enc` へ格納できます。機密情報は承認済みの安全ストレージまたは明示的に選択した暗号化 `sensitive.enc` だけに保存します。
- 制限付き Preview パッケージでも、これらの規則を弱めてはいけません。ネイティブ安全ストアの実装と実機検証が完了するまで、Preview UI はキー、OAuth、token の入力欄を公開せず、それらを永続化し得る機能サービスも生成しません。

### パッケージ境界

- Windows ZIP、EXE、MSI は、引き続き唯一の完全な製品パッケージです。
- 個別に提供する macOS Apple Silicon（arm64）および Intel（x86_64）DMG と Linux x86_64 AppImage には、専用シェルとして `preview_app.py` を含め、Windows は `app.py` を使用します。目的は、ネイティブパッケージング、起動、ローカライズ、パス、安全境界の検証です。
- Pull Request では、パッケージレベルの smoke test 後に短期 artifact をアップロードできますが、GitHub Release は決して作成しません。
- `vN.N.N` または `vN.N.N-rc.N` に一致する既存の不変 tag だけがマルチプラットフォームパッケージを公開できます。正式 tag は Stable Release、RC tag は Pre-release を作成します。読み取り専用メタデータジョブが全プラットフォームの出力を収集して SBOM、メタデータ、checksum を作成し、別の最小権限ジョブが同一の artifact と tag commit を再検査して証明を生成し、単一の Release を公開します。
- リリース証拠では、可観測性とサプライチェーンデータを正式なゲートとして扱います。Tachyon 証拠はサニタイズ、JIT 検証、サンプル品質検査を完了し、単一のバイナリストリームから再現できなければなりません。生ストリームは一時保存に限ります。CycloneDX 1.7 インベントリは、固定された実行時要件と一致し、完全なルート依存エッジ、PURL、宣言済み SPDX ライセンスを含み、公式 schema とプライバシーゲートに合格し、ビルド専用ツールを分離して追跡しなければなりません。
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
2. 小さな公開 API を定義し、別クラスの公開 API だけを使用します。
3. UI が小さなコントロールを超える場合は、独立した `<feature>_ui.py` モジュールへ配置します。
4. コンポジションポイントでタブまたはパネルを登録します。
5. その機能単独の契約テストを一つと、統合 smoke test を一つ追加します。
6. `test_architecture_contracts.py` と完全な回帰テストスイートを実行します。

すでに正式な所有者がある動作に、正式 owner の公開 API を拡張し、設定、タイマー、signal を一つに維持します。代わりに、その所有者の公開 API を拡張します。

### 視覚感知の許可とデータ境界

- 公開版では、カメラと遠隔画像意味解析は利用者が明示的に有効化します。利用者がコントロールセンターで明示的に有効化して全体設定を保存すると、自ら無効にするまで継続的な許可となります。継続許可は後続フレームにも適用されます。許可状態を常に表示し、利用枠と費用の上限、および直ちに取り消せる操作を提供しなければなりません。
- OpenCV は端末内で継続的かつ低コストの感知を行います。GPT-5.6 が意味解析のために受け取るのは、低頻度またはイベント発生時の一時的な画像一枚だけです。継続的なカメラストリームを遠隔サービスへ直接送ってはいけません。
- 元画像は短期メモリで処理後に解放します。データベース、設定、可搬プロファイル、ログ、テレメトリー、エラーメッセージは Base64 を除去した内容に限定します。ネットワークは保存済みの利用者設定で有効化し、保存済みの利用者許可、設定済みサービス、残り利用枠が同時に成立した場合だけ遠隔要求を行えます。
- 利用者は使用量と費用の上限を設定でき、いつでも機能や進行中の解析を終了できます。終了後に届いた結果は期限切れとして扱います。カメラ、モデル、SDK、ネットワーク、利用枠、終了処理の各境界は利用可能範囲外の経路を分離し、端末内感知と既存機能は動作を続けます。
- 発行インベントリでは OpenCV のバージョンと検証済みライセンスを固定します。OpenAI Responses API 経路は Python 標準ライブラリの `urllib.request` から HTTPS で直接呼び出します。プロジェクトの実行時依存範囲は Python 標準ライブラリ HTTPS 経路に限定します。OpenAI は同梱コンポーネントではなく外部サービスであり、SBOM の機械可読な外部サービスポリシーにこの境界を明記します。v4 の発行は、OpenCV インベントリ、標準ライブラリ実行時経路、ポリシー整合性がすべて揃った場合だけ通過します。

#### ジェスチャーと視覚の融合パイプライン

- ローカルパイプラインは 21 点の手骨格を最大 10 Hz で処理し、短時間だけ有効な口元領域の証拠を最大 1 Hz で取得します。両入力を同一の selfie 座標系へ正規化した後、タイムスタンプ付き融合層で対応付けます。融合証拠は最長 1.5 秒で失効し、古い口元または手の証拠を新しいジェスチャー判断に使用しません。
- 元画像、口元の切り抜き、通常の骨格証拠は処理中の短期メモリだけに存在し、データベース、通常の可搬プロファイル、ログ、テレメトリーへ書き込みません。利用者が明示的に記録したカスタム 21 点骨格サンプルだけを永続化でき、保護された暗号化ストレージへ保存します。通常設定と通常の可搬プロファイルには、有効状態、名前、動作割り当てなどの非機密メタデータだけを保存します。
- 融合結果は、権限、カメラ、モデル、タイムスタンプ、座標、追跡、信頼度の検査をすべて通過した場合だけ派遣します。それ以外は不明として扱い、既存の会話、音声、2.5D 機能は動作を続けます。
- コントローラーはライフサイクル、権限、generation だけを管理します。認識器は正規化済み証拠を候補意図へ変換するだけです。ルーターは利用者の割り当てと安全方針から動作決定を作るだけです。ディスパッチャーは承認済み決定を既存の安全なコマンド境界へ渡すだけです。各層は不変型と狭いインターフェースで接続し、他層のストレージ、UI、カメラ、外部サービスへ直接アクセスしません。
- 本節は開発中のアーキテクチャ契約を示すもので、完全な回帰テスト、パッケージ化、Windows EXE による実カメラ実機検証、正式公開の完了を主張しません。

### 技術的負債ゼロと将来互換性のゲート

- 新機能は最初の実装から、作成／インストール、検証、プレビュー、保存、キャンセル、無効化、削除、移行、不足時のフォールバック、可観測性、回帰テストまでの全ライフサイクルを備えます。最初の実装から保守可能で全ライフサイクルを満たす経路を採用します。
- 設計時には、その時点で信頼して採用できる最新の言語機能、標準ライブラリ、プラットフォーム API、パッケージ形式、安全機構を必ず先回りして評価します。明確さ、性能、安全性、保守性を改善し、完全回帰を損なわない場合は新しい方法を優先し、惰性だけで旧経路を残しません。
- 上流、OS、ハードウェア、依存パッケージが実際には未対応の場合に限り延期できます。延期時は、制約理由、隔離境界、安全な代替、将来の有効化条件、旧経路を削除する責任者、テストを記録し、所有者のない負債にしません。
- 新機能が既存のチャット、音声、表情、記憶、ツール、設定、四言語、プライバシー、安全、クロスプラットフォーム、パッケージ動作を損なう場合は開発中として扱い、既存動作を完全に維持する変更だけをパッケージ化、マージ、公開します。
- キャラクター外観と 2.5D 視覚変更では、将来のピクセル単位修正を自動ゲートへ置き換えます。固定キャンバスとアンカー、レイヤー深度、透明境界、顔／手／髪／襟の遮蔽、コア同一性領域の変化ゼロ、全表情・全シルエットのフレーム別コンタクトシート監査を必須とします。一つでも突き抜け、ずれ、旧素材の露出があればパック全体を拒否します。

### Codex 指向の保守規則

- 探索マジックやリフレクションより、明示的なインポート、コンストラクター、signal 接続を優先します。
- 外部エンジンとツールには、ダックタイピングされた `Protocol` 境界を優先します。完全な API 自体が意図した不変条件である場合、具体的なドメインオブジェクトは具体型のままで構いません。
- 新機能のサービス、UI、テストには、一致して検索しやすい名前を付けます。
- `app.py` の内容をコンポジションロジックに限定します。これはコンポジションシェルです。
- 機能が別の機能を利用できるのは、文書化された公開メソッド、signal、サービス API を通じる場合だけです。
- 変更に無関係なモジュールまで触れる必要がある場合は、まず不足している公開境界を追加または改善します。
- 新しい依存関係を通すためだけに、アーキテクチャテストを弱めてはいけません。

### デスクトップアプリケーションのレイヤー契約

アーキテクチャゲートは、実体のある五層パッケージ、ルート互換入口、`legacy-root` 件数を分けて報告し、空の `__init__.py` だけで分層完了を示してはなりません。すべてのルート製品名には機械可読な移行先レイヤーと保守 owner が必要で、`legacy-root` はゼロでなければなりません。残すルートファイルは薄い `compatibility-root` に限定し、実装は `presentation`、`application`、`domain`、`integrations`、`infrastructure` のいずれか一つの真の owner にのみ置きます。ルート `app.py` は五十行以下の正式な構成入口として `application.application_bootstrap` を直接使用し、他の互換入口や正式パッケージから逆依存してはなりません。Domain と application の清冊にある全モジュールは実体パッケージへ移行済みで、内部依存はルート互換入口を経由せず、正式な `domain.*` または `application.*` パスを使用します。他層に実体 owner の欠落やルート facade 依存が残る限り、リリースゲートは失敗を維持します。

`presentation` は現在、Companion と Dashboard のウィンドウ構成、各 UI mixin、ダイアログ、初回設定ウィザード、ポータブルプロファイルパネル、テーマパネル／描画、更新パネル、表示層のローカライズカタログを実体として所有します。同名のルートモジュールは検索可能な薄い互換ファサードとしてのみ残し、既存の外部 import を維持します。一方、presentation 内部は真の owner である `presentation.*` を直接参照しなければなりません。`flagship_ui.py` は意図的に別工程へ残しており、この段階では専用移行待ちと明記します。

`integrations` と `infrastructure` は現在、棚卸し済みの外部サービス、音声プロバイダー、永続化、資産、プラットフォーム、安全ストレージの実装を実体として所有します。同名のルートモジュールは薄い互換 alias のみです。製品内部、テスト、ツールは正式なパッケージ owner を直接 import し、二つの実体レイヤーも正式パッケージ owner へ直接依存します。互換入口と正式 owner は同一 module オブジェクトへ解決し、patch、型 identity、lazy import の callable がずれないようにします。

- `presentation` は Qt ウィンドウ、コントロール、表示モデル、利用者イベントの変換だけを担当し、外部サービスの生成、データベース操作、機密情報の読み取りを直接行いません。
- `application` はユースケース、トランザクション、取消、ポートを調整し、`domain` だけに依存します。この依存範囲は `domain` 契約に限定します。Qt、プロバイダー実装、OS 詳細には依存しません。
- `domain` は純粋な方針、不変値、不変条件を所有し、他のプロジェクトレイヤーに依存しません。
- `integrations` はクラウド、音声、第三者サービスのアダプターを実装し、`infrastructure` はデータベース、ファイル、OS、安全ストレージのアダプターを実装します。両者は application/domain 契約を通じて接続し、UI を逆方向に所有しません。
- 依存方向は `presentation → application → domain` です。`integrations` と `infrastructure` はコンポジションルートから注入される外側のアダプターです。レイヤー間では公開された型付きポートだけを使用します。
- API Key、OAuth secret、token、顔識別データを `config.py`、`app.py`、ソース定数、ログ、エラーメッセージへ含めてはいけません。承認済みの OS 安全ストレージポートだけが提供できます。
- 移行完了後の `app.py` は、明示的インポート、引数なしの単一 `main()` 委譲、単一の `__main__` ガードだけを持つ、物理行 50 行以下の唯一の composition root とします。これは分層移行後のリリースゲートであり、未移動モジュールは移行待ちとして明示します。

### v4.0.0 プラットフォームと Qt 互換レイヤーのポリシー

- 単一 metadata 宣言に代えて、固定ダイジェストの wheel と互換性証拠をゲートにします。固定ダイジェストの公式 wheel バイナリ、`6.11.1+mohan.py315.1` metadata、通常 resolver、`pip check`、Qt smoke で検証します。
- Windows を正式対応とし、macOS/Linux は機能限定 Preview とします。CI runner の証拠はCI runner 検証を対象とし、開発者本人の実機認証と Windows 機能同等性は各専用証拠で判定します。
- セキュリティ、秘密、回帰、パッケージ内容、SBOM、SHA-256、artifact 整合性、フォールバック動作は恒久的に適用する必須ゲートです。
