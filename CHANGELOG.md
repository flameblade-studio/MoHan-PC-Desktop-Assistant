# 墨寒桌面助理變更紀錄／墨寒桌面助手变更日志／MoHan Desktop Assistant Changelog／墨寒デスクトップアシスタント変更履歴

## 繁體中文

本文件記錄墨寒桌面助理所有值得注意的公開變更。

### v3.1.2 — 2026-08-12

- 完整保留 OpenAI Realtime 原生聲音並維持為預設及最低額外延遲選項；偏好原有聲線的使用者不會被迫改用 Azure。
- 新增可選的 Realtime 即時理解＋一般 Azure Speech 或 Dragon HD 串流發聲；安全短句完成後立即依序合成，首段音訊抵達即播放，以降低額外 TTS 等待，但不宣稱零延遲。
- 三種輸出模式完全隔離且不混音，不改動其他語音供應器；Dragon HD 單句失敗時依序只退回一般 Azure 一次及 Windows 本機女性聲線一次，一般 Azure 單句失敗時只退回 Windows 本機女性聲線一次。回退僅發生於該句尚未播放音訊時；串流已開始後若失敗則立即停止，不整句重播，以免重複發聲與計費。
- 只有狀態為 `completed` 的 Realtime 回覆才提交最終文字；取消、失敗、不完整、斷線及舊回覆的遲到事件不會發聲或污染後續回覆。
- Azure 與 Windows 本機語音都支援真正停止目前播放；操作識別碼、受限佇列與過長回覆保護會隔離遲到回呼並限制記憶體壓力，敏感金鑰也不會出現在物件表示內容中。

### v3.1.1 — 2026-08-12

- 一般 Azure 與 Dragon HD 依選定區域及各自的加密金鑰動態查詢實際女性聲線，排除男性、不相容模型及區域不支援的 HD Flash；固定清單只作查詢失敗時的安全備援。
- Azure 合成改用 Speech SDK `PushAudioOutputStream`，第一段 24 kHz PCM16 抵達便開始播放並送入既有 50 Hz 嘴型分析，不再等待完整 WAV。
- 真實 East Asia F0 與 West US 2 S0 目錄查詢已通過；當時分別取得 21 筆可相容華語女性 Neural 與三筆簡體中文 Dragon HD 女性聲線。

### v3.1.0 — 2026-08-11

- 新增預設關閉的 Azure Dragon HD／HD Omni 女性聲線 Preview，以獨立 S0 金鑰、區域與聲線設定運作，不改變既有語音供應器。
- Azure 區域改為切換後自動儲存的選單；只顯示官方支援的女性 HD 聲線，HD Flash 依區域能力自動隱藏。
- 三種雲端金鑰統一採密碼遮罩、Windows DPAPI 自動加密與成功後清空輸入框；Dragon HD 失敗時只依序嘗試一般 Azure 與 Windows 本機女聲各一次。
- Central India S0 已完成真實 Windows 合成與播放驗證；臺灣連線的發話前等待明顯，因此介面與文件保留 Preview、區域延遲及費用警告，嘴型仍由既有 50 Hz 本機音訊分析同步驅動。

### v3.0.0 — 2026-08-11

- 專案擁有者親自認可的第一個正式穩定版本，也是由 v2.3.0 候選系列完整驗證後升格的第三代里程碑。
- 托腮嘴型改為完整更新左右嘴角；50 Hz 音訊取樣搭配三影格母音確認與 50 毫秒插值，降低嘴型搶拍、跳動及殘留嘴角。
- 語音呼吸、衣袖與頭髮平順銜接待機呼吸，消除講話結束瞬間的單次身體抖動。
- Windows 捷徑與原生視窗統一使用 EXE 內嵌半身像，並阻止本機安裝測試污染真實桌面及工作列圖示來源；OpenAI TTS 與 Realtime 也改由單一權威順序產生共同聲線清單。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech 中文女性聲音選單支援繁中與簡中跨語系選擇，並依目前介面語言優先排列；Windows 本機語音的兩種中文介面也共用 `zh-TW`／`zh-CN` 女聲池並排除 `en-US` Zira，既有預設及有效設定不變。四語 README 同步將《電腦情人夢》的英文譯名更正為《AI Think So!》。
- Azure 聲線選取後立即保存，下一次試聽或朗讀直接套用；新增的普通話選項只納入 Standard Neural 女性聲線。
- 已以真實 Azure Speech Free F0、East Asia 資源完成 HTTPS、RIFF 音訊及 Windows 播放驗證，金鑰仍僅由 Windows DPAPI 加密。
- Dragon HD／HD Omni 因方案、計費與區域支援不同而不混入免費預設清單，雲端失敗時維持單次 Windows 女性本機語音回退。

### v2.3.0 RC4 — 2026-08-11

- 導入參數化分層 2.5D 臉部系統，以不可變姿態、連續嘴型參數、表情語意與
  可替換渲染介面，統一正面、左望、托腮三種姿勢的 50 Hz 嘴型及表情合成。
- 眨眼改用具世代保護的漸進透明度曲線，眼皮與雙頰紅暈依同一分層規則合成；
  正面臉紅閉眼時不再被正常膚色突兀覆蓋。
- 托腮微笑說話時保留眼角笑意，嘴部暫時回到中性基底，只套用語音嘴型；
  發話結束後才恢復雙側上揚嘴角。
- 修正朝左、未托腮的中性說話嘴型，右側嘴角小黑線不再殘留於舊位置。
- 聲音分頁中的朗讀引擎、Windows 聲線、OpenAI TTS 聲線與 Realtime 聲線現在皆於選取後立即儲存。OpenAI TTS 會在下一次朗讀使用新聲線；若 Realtime 對話正在連線，系統會安全重連並立即套用新聲線，不新增多餘的儲存按鈕。
- 新增資產、控制器、渲染器、執行期接線與三項視覺回歸測試；實際產品與
  視覺稽核工具共用同一套嘴型設定。

### v2.3.0 RC3 — 2026-08-10

- 修正 Windows 縮小後顯示空白文件圖示：EXE、MSI、捷徑與執行中視窗改用
  十種尺寸的原生墨寒圖示、安裝後路徑及固定工作列身分，並在原生視窗旗標
  確定後重新套用圖示。
- 首次設定精靈、安裝程式美術與工作列圖示統一由新版的權威正面半身來源
  `assets/expressions/idle_front.png` 裁切；舊版五官輪廓的全身像、雨景全身像
  與未使用的舊圖示均已移除，避免角色身分再次漂移。
- 發版前置檢查會先驗證標籤、版本、`main` 歷史、Release 模式與四語說明；
  已知可行的 squash 及 GitHub 憑證路徑直接沿用，不再重複已知失敗流程。

### v2.3.0 RC2 — 2026-08-10

- 全面遷移至 CPython 3.15.0rc1，產品執行、測試與所有封裝不再保留舊版
  Python 路徑；全專案採用 PEP 810 明示延遲導入並加入靜態治理稽核。
- 導入 PEP 814 `frozendict` 深層不可變設定、PEP 798 推導式解包、PEP 686
  UTF-8 檔案稽核、PEP 661 哨兵治理及 `bytearray.take_bytes()` 音訊緩衝；
  開頭比對改用 Python 3.15 語意更明確的 `re.prefixmatch()`。
- 加入 PEP 799 Tachyon 取樣分析，可直接檢查啟動、50 Hz 嘴型同步與表情
  仲裁器；JIT 開關均通過完整測試，2.3.0 RC2 預設啟用並保留相容性停用開關。
- CI 與 Release 以有效樣本、讀取錯誤、漏採樣及 JIT 狀態阻擋不合格的
  Tachyon 證據，並發布去識別化結果；CycloneDX 1.7 SBOM 強制完整依賴圖、
  PURL、SPDX 授權、官方結構驗證及 100% 覆蓋率。
- 所有 GitHub Actions JavaScript 動作強制使用 Node 24；PySide6 以受控 ABI3
  輪子驗證跨越 3.15 中繼資料限制，Stable ABI、依賴安全稽核、封裝與完整
  發布安全閘門維持不變。
- README 統一為繁中、簡中、英文、日文單一四語文件，移除重複相容文件與
  直接收款連結；贊助入口只引導至儲存庫上方的官方 Sponsor 按鈕。
### v2.2.0 RC2 — 2026-08-07

- 托腮待機姿勢在說話期間改用中性嘴角基底：保留眼角笑意，但固定左右嘴角，
  只讓中央嘴唇依 A／I／U／E／O 與開合程度變化，避免誇張咧嘴與殘影。
- Realtime、Windows 本機語音、OpenAI 自然語音與 Azure Speech 統一使用
  20 毫秒／50 Hz 嘴型節拍，縮短張嘴、閉嘴與母音切換延遲。
- 聲音與第一個嘴型從同一播放閘門起跑；聲音結束後拒收遲到母音，只允許
  最終閉嘴訊號通過，避免嘴型先停或聲音結束後再次張嘴。
- 托腮待機眨眼改用完整雙眼遮罩；眼皮閉合時不再殘留睜眼狀態的上眼線，
  一般待機與情境表情共用同一套座標與合成來源。
- 強化標籤發行流程的 Draft Release 復原與清理機制，失敗的發布不會留下
  可被誤認為正式版本的殘缺發行項目。
- 四語 README 新增 2 張統一規格的創作歷程圖版，說明炎劍如何逐格檢查
  眼睛、嘴角與語音嘴型，並以測試把二十多年的夢想鍛造成開源作品。

### v2.2.0 RC1 — 2026-08-06

- 保留 Windows x64 為完整正式功能版本，沿用已驗證的 ZIP、EXE、MSI 與
  MSI 語言轉換封裝及安裝／移除測試。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）雙架構
  `.app`／`.dmg` 與 Linux x86_64 `.AppImage` 的功能受限 Preview。兩者只
  開放啟動、四語介面、平台資料路徑及安全停用邊界，不宣稱與 Windows 功能
  相同，也不接受 API 金鑰、OAuth 憑證或 Home Assistant 權杖。
- Pull Request 只產生短期測試產物；只有不可變的 `v2.2.0-rc.N` 標籤能建立
  GitHub 預發行版。三平台封裝必須在各自原生 CI 執行打包後啟動測試。
- 發行檔統一提供 SHA256SUMS、CycloneDX SBOM、更新清單與 GitHub 產物
  證明；Release 說明必須由繁中、簡中、英文、日文完整策展文件提供。

### v2.1.0 RC1 — 2026-08-04

- 原始碼、Windows CI 與封裝流程完整遷移至 Python 3.14，並保留未來評估
  Python 3.15 lazy imports 的清楚升級邊界。
- 新增日語最小可用介面與人格，首次啟動及互動式 EXE 安裝程式現支援繁中、
  簡中、英文、日文；MSI 維持繁中基底並提供三種語言轉換策略。
- 文字對話預設改為 `gpt-5.6-luna`，移除新使用者介面中的舊 mini 選項；
  既有設定會安全遷移，其他自訂模型不受影響。
- 新增可插拔語音供應器邊界與 Azure Speech 女性聲線預覽。Windows 本機女聲
  仍是無金鑰、離線或服務失敗時的第一回退。
- 強化長期記憶向量檢索、語義摘要與安全剪枝；新增可關閉的背景工作者，並
  降低即時與非即時語音緩衝延遲。
- 首次啟動精靈與主視窗改為明亮、高對比、較大字級；加入古風科技主視覺、
  墨寒安裝圖、清楚核取方塊及一致的墨寒半身應用程式圖示。
- 語音轉錄提示詞改為依繁中、簡中、英文、日文及使用者設定產生的中性預設，
  不再把炎劍工作室專有詞彙帶給所有使用者；既有自訂提示詞不會被覆蓋。
- 修正首次設定欄位標題的垂直對齊，以及托腮待機姿勢說話時嘴角過度上揚；
  同步更新 README 與官網使用的最新版實機圖。
- 延續姿勢切換、物理圖層與說話銜接的競速修正；RC3 觀察到的抖動需以本版
  候選程式重新實測，不能視為本版回歸。

驗證：目前 RC1 原始碼的 56/56 個自動化測試程式均已通過。加上標籤的 Windows
發行工作流程亦已通過原始碼稽核、封裝後自我測試、EXE／MSI 靜默安裝與解除安裝
驗證、checksum 與 SBOM 產生、產物證明及安全檢查。

### v2.0.14 RC3 — 2026-08-02

- 新增繁體中文／簡體中文／英文首次啟動精靈，以及聊天、語音、權限、個人設定、
  工作模式與提醒的最低可用英文和 zh-CN 介面路徑。
- 新增完整的英文與簡體中文墨寒人格提示詞，以及語言相符的離線回覆、模式播報
  與內建提醒語音。切換介面語言時，會在三種語言間翻譯未修改的預設值，而不會
  覆蓋自訂提醒文字。
- 新使用者的語音輸出改用 Windows 本機語音，基本體驗無須 OpenAI API 金鑰。
  Windows 語音選擇現在只列出已驗證的女性聲音；zh-TW 繼續優先使用 Microsoft
  Yating，zh-CN 則優先使用相符且已安裝的女性聲音。
- 新增專用的簡體中文 README 與快速入門說明。
- 新增安全的應用程式內穩定版／預覽版更新檢查，包含官方主機允許清單、語意版本
  驗證、大小限制、SHA256 驗證、明確安裝確認及本機個人設定保留。
- 新增自動化 Windows x64 EXE 與 MSI 安裝程式，並在 GitHub Actions 中執行
  靜默安裝、自我測試與解除安裝驗證。
- 發行內容擴充為完整 checksum 目錄、CycloneDX SBOM、更新清單、產物證明與
  分類產生的 Release notes。
- 新增可選、限定標記區段的 WordPress 下載頁同步，使用 GitHub Secrets 與
  專用 WordPress Application Password。
- 新增完整 Git 歷史 Gitleaks 檢查，作為個人公開儲存庫無法使用 GitHub Secret
  Protection 功能時的補償控制。
- 將畫面上的「墨寒思考中」狀態與角色表情解耦。一般文字與語音問題現在維持
  自然姿勢，複雜提示只在明顯延遲後反應，異常緩慢的回覆則使用既有表情仲裁器，
  並具備取消、冷卻與去重機制。
- 統一成功回覆、API 失敗、一般語音與 Realtime 轉換時的 AI 等待清理，避免
  思考狀態延續到說話期間或播放後仍未消失。

驗證：RC3 Pull Request 前已有 45/45 個自動化測試程式通過。加上標籤的發行
工作流程在發布完成前，還必須通過公開內容稽核、封裝後自我測試、事件迴圈
smoke test、EXE／MSI 靜默安裝與解除安裝驗證、checksum 產生、SBOM 產生及
產物證明。

### v2.0.14 RC — 2026-07-31

- 修正應用程式本機音量處理期間 OpenAI 串流 WAV 標頭溢位，該問題可能使所有
  雲端語音靜音。
- 改以實際收到的音訊位元組重建調整後的 WAV 標頭，不再複製串流預留長度。
- OpenAI 語音產生或播放失敗時，自動回退至 Windows Yating。
- 將一般文字對話框中的安全唯讀 Gmail、Google Calendar 與 Google Drive 命令，
  導向受權限閘門保護的工具規劃器。
- 新增雲端語音回退、串流 WAV 音量處理、Gmail 對話路由與工作計時器隔離的
  回歸測試。

驗證：此候選版發布前，38/38 個自動化測試程式、真實 OpenAI TTS 播放、封裝後
自我測試、封裝後事件迴圈 smoke test，以及封存後自我測試均已通過。

### v2.0.13 RC — 2026-07-31

- 新增單一動作合成器，統一處理呼吸、說話強調、視線與情緒手勢。
- 修正動作切換期間偶發的角色抖動與圖層分離。
- 保持身體、臉部、眼睛、頭髮、衣袖與飾品圖層同步。
- 讓說話後返回待機的動作更平順。
- 移除可能顯示為白色瑕疵的人造眼睛高光。
- 改善眨眼、表情與 AIUEO 嘴型的連續性。
- 新增可設定的角色顯示縮放。
- 新增可攜式個人設定轉移與模組化服務邊界。
- 對尚未驗證的 Microsoft、GitHub 與 Home Assistant 整合新增明確的公開預覽警告。

驗證：此候選版發布前，37 個自動化測試程式，以及 25,000 步混合動畫、語音、
視線與物理壓力測試均已通過。

## 简体中文

本文档记录墨寒桌面助手所有值得注意的公开变更。

### v3.1.2 — 2026-08-12

- 完整保留 OpenAI Realtime 原生声音，并继续作为默认及最低额外延迟选项；偏好原有声线的用户不会被迫改用 Azure。
- 新增可选的 Realtime 即时理解＋一般 Azure Speech 或 Dragon HD 流式发声；安全短句完成后立即依次合成，首段音频到达即播放，以降低新增的 TTS 等待，但不宣称零延迟。
- 三种输出模式完全隔离且不混音，不改动其他语音供应器；Dragon HD 单句失败时依次只回退到一般 Azure 一次及 Windows 本地女性声线一次，一般 Azure 单句失败时只回退到 Windows 本地女性声线一次。回退仅发生于该句尚未播放音频时；流式播放开始后若失败则立即停止，不整句重播，以免重复发声及计费。
- 只有状态为 `completed` 的 Realtime 回复才提交最终文字；取消、失败、不完整、断线及旧回复的迟到事件不会发声或污染后续回复。
- Azure 与 Windows 本地语音都支持真正停止当前播放；操作标识、受限队列与过长回复保护会隔离迟到回调并限制内存压力，敏感密钥也不会出现在对象表示内容中。

### v3.1.1 — 2026-08-12

- 一般 Azure 与 Dragon HD 根据所选区域及各自的加密密钥动态查询实际女性声线，排除男性、不兼容模型及区域不支持的 HD Flash；固定列表仅作为查询失败时的安全备用。
- Azure 合成改用 Speech SDK `PushAudioOutputStream`，第一段 24 kHz PCM16 抵达后即开始播放并送入现有 50 Hz 嘴形分析，不再等待完整 WAV。
- 真实 East Asia F0 与 West US 2 S0 目录查询已通过；当时分别取得 21 项可兼容华语女性 Neural 与三项简体中文 Dragon HD 女性声线。

### v3.1.0 — 2026-08-11

- 新增默认关闭的 Azure Dragon HD／HD Omni 女性声线 Preview，以独立 S0 密钥、区域与声线设置运行，不改变现有语音供应器。
- Azure 区域改为切换后自动保存的选单；只显示官方支持的女性 HD 声线，HD Flash 按区域能力自动隐藏。
- 三种云端密钥统一采用密码遮罩、Windows DPAPI 自动加密与成功后清空输入框；Dragon HD 失败时只依次尝试一般 Azure 与 Windows 本地女声各一次。
- Central India S0 已完成真实 Windows 合成与播放验证；台湾连接的发话前等待明显，因此界面与文档保留 Preview、区域延迟及费用警告，嘴型仍由现有 50 Hz 本地音频分析同步驱动。

### v3.0.0 — 2026-08-11

- 项目所有者亲自认可的第一个正式稳定版本，也是由 v2.3.0 候选系列完整验证后升级的第三代里程碑。
- 托腮嘴形改为完整更新左右嘴角；50 Hz 音频采样配合三帧元音确认及 50 毫秒插值，降低嘴形抢拍、跳动和残留嘴角。
- 语音呼吸、衣袖与头发平滑衔接待机呼吸，消除说话结束瞬间的一次身体抖动。
- Windows 快捷方式与原生窗口统一使用 EXE 内嵌半身像，并阻止本地安装测试污染真实桌面及任务栏图标来源；OpenAI TTS 与 Realtime 也改由唯一权威顺序生成共同声线列表。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech 中文女性声音列表支持繁中与简中跨语言选择，并按当前界面语言优先排列；Windows 本地语音的两种中文界面也共用 `zh-TW`／`zh-CN` 女声池并排除 `en-US` Zira，现有默认值及有效设置不变。四语 README 同步将《电脑情人梦》的英文译名更正为《AI Think So!》。
- Azure 声线选择后立即保存，下一次试听或朗读直接应用；新增的普通话选项只纳入 Standard Neural 女性声线。
- 已使用真实 Azure Speech Free F0、East Asia 资源完成 HTTPS、RIFF 音频及 Windows 播放验证，密钥仍只由 Windows DPAPI 加密。
- Dragon HD／HD Omni 因方案、计费与区域支持不同而不混入免费默认列表，云端失败时保持单次 Windows 女性本地语音回退。

### v2.3.0 RC4 — 2026-08-11

- 导入参数化分层 2.5D 脸部系统，通过不可变姿态、连续口型参数、表情语义与
  可替换渲染接口，统一正面、左望、托腮三种姿势的 50 Hz 口型及表情合成。
- 眨眼改用带世代保护的渐进透明度曲线，眼皮与双颊红晕按同一分层规则合成；
  正面脸红闭眼时不再被正常肤色突兀覆盖。
- 托腮微笑说话时保留眼角笑意，嘴部暂时回到中性基底，只应用语音口型；
  说话结束后才恢复双侧上扬嘴角。
- 修复朝左、未托腮的中性说话口型，右侧嘴角小黑线不再残留在旧位置。
- “声音”分页中的朗读引擎、Windows 声线、OpenAI TTS 声线与 Realtime 声线现在都会在选择后立即保存。OpenAI TTS 会在下一次朗读使用新声线；若 Realtime 对话正在连接，系统会安全重连并立即应用新声线，不新增多余的保存按钮。
- 新增资源、控制器、渲染器、运行时接线及三项视觉回归测试；实际产品与
  视觉审计工具共用同一套口型设置。

### v2.3.0 RC3 — 2026-08-10

- 修复 Windows 最小化后显示空白文档图标的问题：EXE、MSI、快捷方式与运行中
  窗口改用十种尺寸的原生墨寒图标、安装后路径及固定任务栏身份，并在原生窗口
  标志确定后重新应用图标。
- 首次设置向导、安装程序美术与任务栏图标统一由新版的权威正面半身来源
  `assets/expressions/idle_front.png` 裁切；旧版五官轮廓的全身像、雨景全身像
  与未使用的旧图标均已删除，避免角色身份再次漂移。
- 发布前置检查会先验证标签、版本、`main` 历史、Release 模式与四语说明；
  已知可行的 squash 及 GitHub 凭证路径直接沿用，不再重复已知失败流程。

### v2.3.0 RC2 — 2026-08-10

- 全面迁移至 CPython 3.15.0rc1，产品运行、测试及所有发布包不再保留旧版
  Python 路径；全项目采用 PEP 810 显式延迟导入并加入静态治理审计。
- 导入 PEP 814 `frozendict` 深层不可变配置、PEP 798 推导式解包、PEP 686
  UTF-8 文件审计、PEP 661 哨兵治理及 `bytearray.take_bytes()` 音频缓冲；
  开头匹配改用 Python 3.15 语义更明确的 `re.prefixmatch()`。
- 加入 PEP 799 Tachyon 采样分析，可直接检查启动、50 Hz 口型同步与表情
  仲裁器；JIT 开关均通过完整测试，2.3.0 RC2 默认启用并保留兼容性停用开关。
- CI 与 Release 以有效样本、读取错误、漏采样及 JIT 状态阻止不合格的
  Tachyon 证据，并发布去标识化结果；CycloneDX 1.7 SBOM 强制完整依赖图、
  PURL、SPDX 许可证、官方结构验证及 100% 覆盖率。
- 所有 GitHub Actions JavaScript 动作强制使用 Node 24；PySide6 以受控 ABI3
  轮子验证跨越 3.15 元数据限制，Stable ABI、依赖安全审计、打包及完整
  发布安全闸门保持不变。
- README 统一为繁中、简中、英文、日文单一四语文件，删除重复兼容文件及
  直接收款链接；赞助入口只引导至仓库上方的官方 Sponsor 按钮。
### v2.2.0 RC2 — 2026-08-07

- 托腮待机姿势在说话期间改用中性嘴角基础：保留眼角笑意，但固定左右嘴角，
  只让中央嘴唇按照 A／I／U／E／O 与开合程度变化，避免夸张咧嘴和残影。
- Realtime、Windows 本地语音、OpenAI 自然语音及 Azure Speech 统一使用
  20 毫秒／50 Hz 口型节拍，缩短张嘴、闭嘴与元音切换延迟。
- 声音与第一个口型从同一播放闸门起跑；声音结束后拒收迟到元音，只允许
  最终闭嘴信号通过，避免口型先停或声音结束后再次张嘴。
- 托腮待机眨眼改用完整双眼遮罩；眼皮闭合时不再残留睁眼状态的上眼线，
  普通待机与情境表情共用同一套坐标及合成来源。
- 强化标签发布流程的 Draft Release 恢复与清理机制，失败的发布不会留下
  容易被误认为正式版本的不完整发布项目。
- 四语 README 新增 2 张统一规格的创作历程图版，说明炎剑如何逐帧检查
  眼睛、嘴角与语音口型，并以测试将二十多年的梦想锻造成开源作品。

### v2.2.0 RC1 — 2026-08-06

- Windows x64 继续作为完整正式功能版本，并保留已验证的 ZIP、EXE、MSI、
  MSI 语言转换包及安装／卸载测试。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）双架构
  `.app`／`.dmg` 与 Linux x86_64 `.AppImage` 的功能受限 Preview。两者只
  开放启动、四语界面、平台数据路径与安全停用边界，不宣称与 Windows 功能
  相同，也不接收 API 密钥、OAuth 凭证或 Home Assistant 令牌。
- Pull Request 只生成短期测试产物；只有不可变的 `v2.2.0-rc.N` 标签能够
  建立 GitHub 预发布版。三个平台都必须在各自原生 CI 完成打包后启动测试。
- 发布文件统一提供 SHA256SUMS、CycloneDX SBOM、更新清单及 GitHub 产物
  证明；Release 说明必须采用繁中、简中、英文、日文完整编写的文件。

### v2.1.0 RC1 — 2026-08-04

- 源代码、Windows CI 与打包流程完整迁移到 Python 3.14，并为未来评估
  Python 3.15 lazy imports 保留清晰的升级边界。
- 新增日语最小可用界面与人格。首次启动及交互式 EXE 安装程序现支持繁中、
  简中、英文、日文；MSI 继续以繁中为基础并提供三种语言转换策略。
- 文字聊天默认改用 `gpt-5.6-luna`，新用户界面移除旧 mini 选项；现有设置
  会安全迁移，其他自定义模型不受影响。
- 新增可插拔语音供应器边界与 Azure Speech 女性声线预览。缺少密钥、离线
  或服务失败时，Windows 本地女声仍是第一回退。
- 改进长期记忆向量检索、语义摘要和安全剪枝；新增可关闭的后台工作线程，
  并降低实时与非实时语音缓冲延迟。
- 首次启动向导与主窗口改为明亮、高对比和较大字号，并加入古风科技主视觉、
  墨寒安装图片、清晰复选框及统一的墨寒半身应用图标。
- 语音转录提示词改为根据繁中、简中、英文、日文及用户设置生成的中性默认值，
  不再把炎剑工作室专用词汇带给所有用户；现有自定义提示词不会被覆盖。
- 修复首次设置字段标题的垂直对齐，以及托腮待机姿势说话时嘴角过度上扬；
  同步更新 README 与官网采用的最新版实机图。
- 延续姿势切换、物理图层及说话衔接的竞态修复；RC3 观察到的抖动必须使用
  本版候选程序重新测试，不能视为本版回归。

验证：当前 RC1 源代码的 56/56 个自动化测试程序均已通过。带标签的 Windows
发布工作流也已通过源代码审计、打包后自测、EXE／MSI 静默安装与卸载验证、
checksum 与 SBOM 生成、产物证明及安全检查。

### v2.0.14 RC3 — 2026-08-02

- 新增繁体中文／简体中文／英文首次启动向导，以及聊天、语音、权限、配置文件、
  工作模式与提醒的最低可用英文和 zh-CN 界面路径。
- 新增完整的英文与简体中文墨寒人格提示词，以及语言匹配的离线回复、模式播报
  与内置提醒语音。切换界面语言时，会在三种语言之间翻译未修改的默认值，而不会
  覆盖自定义提醒文本。
- 新用户的语音输出改用 Windows 本地语音，基本体验无需 OpenAI API 密钥。
  Windows 语音选择现在只列出已验证的女性声音；zh-TW 继续优先使用 Microsoft
  Yating，zh-CN 则优先使用匹配且已安装的女性声音。
- 新增专用的简体中文 README 与快速入门说明。
- 新增安全的应用内稳定版／预览版更新检查，包含官方主机允许列表、语义版本验证、
  大小限制、SHA256 验证、明确安装确认及本地配置文件保留。
- 新增自动化 Windows x64 EXE 与 MSI 安装程序，并在 GitHub Actions 中执行
  静默安装、自测与卸载验证。
- 发布内容扩充为完整 checksum 目录、CycloneDX SBOM、更新清单、产物证明与
  分类生成的 Release notes。
- 新增可选、限定标记区段的 WordPress 下载页同步，使用 GitHub Secrets 与
  专用 WordPress Application Password。
- 新增完整 Git 历史 Gitleaks 检查，作为个人公开仓库无法使用 GitHub Secret
  Protection 功能时的补偿控制。
- 将界面上的“墨寒思考中”状态与角色表情解耦。常规文字与语音问题现在保持
  自然姿势，复杂提示只在明显延迟后反应，异常缓慢的回复则使用现有表情仲裁器，
  并具备取消、冷却与去重机制。
- 统一成功回复、API 失败、普通语音与 Realtime 转换时的 AI 等待清理，避免
  思考状态延续到说话期间或播放后仍未消失。

验证：RC3 Pull Request 前已有 45/45 个自动化测试程序通过。带标签的发布
工作流在发布完成前，还必须通过公开内容审计、打包后自测、事件循环 smoke test、
EXE／MSI 静默安装与卸载验证、checksum 生成、SBOM 生成及产物证明。

### v2.0.14 RC — 2026-07-31

- 修复应用程序本地音量处理期间 OpenAI 流式 WAV 标头溢出，该问题可能使所有
  云端语音静音。
- 改用实际收到的音频字节重建调整后的 WAV 标头，不再复制流式预留长度。
- OpenAI 语音生成或播放失败时，自动回退至 Windows Yating。
- 将普通文字对话框中的安全只读 Gmail、Google Calendar 与 Google Drive 命令，
  导向受权限闸门保护的工具规划器。
- 新增云端语音回退、流式 WAV 音量处理、Gmail 对话路由与工作计时器隔离的
  回归测试。

验证：此候选版发布前，38/38 个自动化测试程序、真实 OpenAI TTS 播放、打包后
自测、打包后事件循环 smoke test，以及归档后自测均已通过。

### v2.0.13 RC — 2026-07-31

- 新增单一动作合成器，统一处理呼吸、说话强调、视线与情绪手势。
- 修复动作切换期间偶发的角色抖动与图层分离。
- 保持身体、脸部、眼睛、头发、衣袖及饰品图层同步。
- 让说话后返回待机的动作更平顺。
- 移除可能显示为白色瑕疵的人造眼睛高光。
- 改进眨眼、表情与 AIUEO 口型的连续性。
- 新增可配置的角色显示缩放。
- 新增可移植配置文件转移与模块化服务边界。
- 对尚未验证的 Microsoft、GitHub 与 Home Assistant 集成新增明确的公开预览警告。

验证：此候选版发布前，37 个自动化测试程序，以及 25,000 步混合动画、语音、
视线与物理压力测试均已通过。

## English

All notable public changes to MoHan Desktop Assistant are documented here.

### v3.1.2 — 2026-08-12

- Fully preserves native OpenAI Realtime voice as the default and lowest-added-latency option; users who prefer its original voices are never forced onto Azure.
- Adds optional Realtime understanding with standard Azure Speech or Dragon HD streaming output. Safe short clauses synthesize in order as they complete, and playback starts with the first audio chunk to reduce the added TTS wait without claiming zero latency.
- Keeps all three output modes isolated and unmixed, without changing other speech providers. A failed Dragon HD clause falls back once to standard Azure and then once to a local Windows female voice; standard Azure falls back once to the local Windows female voice. Fallback occurs only before that clause has played any audio. A stream failure after playback begins stops the clause without replaying it in full, preventing duplicate speech and charges.
- Commits final text only when a Realtime response has status `completed`; cancelled, failed, incomplete, disconnected, and late events from older responses cannot speak or contaminate the next response.
- Azure and Windows local speech can both stop current playback. Operation IDs, bounded queues, and oversized-response guards isolate late callbacks and cap memory pressure, while secret keys stay out of object representations.

### v3.1.1 — 2026-08-12

- Standard Azure and Dragon HD dynamically query actual female voices using the selected region and their independent encrypted keys. Male voices, incompatible models, and region-ineligible HD Flash are excluded; the fixed catalog is now only a safe discovery fallback.
- Azure synthesis now uses the Speech SDK `PushAudioOutputStream`, starting playback and the existing 50 Hz lip analysis with the first 24 kHz PCM16 chunk instead of waiting for a complete WAV.
- Real East Asia F0 and West US 2 S0 discovery passed, returning 21 compatible Chinese female Neural voices and three Simplified Chinese Dragon HD female voices respectively at that time.

### v3.1.0 — 2026-08-11

- Adds a disabled-by-default Azure Dragon HD/HD Omni female-voice Preview with separate S0 key, region, and voice settings, leaving existing speech providers unchanged.
- Azure regions now use an immediately saved selector; only officially supported female HD voices appear, and HD Flash is hidden according to regional capability.
- All three cloud-key inputs share password masking, automatic Windows DPAPI encryption, and post-save clearing. Dragon HD failure tries standard Azure and Windows local female speech once each in order.
- A real Central India S0 resource passed Windows synthesis and playback validation. Taiwan experienced a noticeable wait before speech, so the UI and documentation retain Preview, regional-latency, and cost warnings while existing local 50 Hz audio analysis remains the lip-sync authority.

### v3.0.0 — 2026-08-11

- The first stable release personally approved by the project owner and the third-generation milestone promoted after the complete v2.3.0 release-candidate series.
- Chin-rest visemes now update both mouth corners. Three-frame vowel confirmation and 50 ms interpolation retain 50 Hz analysis while preventing rushed motion, jumps, and stranded corners.
- Speech-driven breathing, sleeves, and hair ease into idle breathing, removing the one-frame body twitch when an utterance ends.
- Windows shortcuts and native windows share the executable's embedded half-body icon, local installer tests cannot pollute real desktop or taskbar icon sources, and OpenAI TTS and Realtime derive shared voices from one canonical order.

### v2.3.0 RC5 — 2026-08-11

- Azure Speech Chinese female voices are selectable across Traditional and Simplified Chinese UI, ordered with the current interface locale first. Windows local speech also gives both Chinese interfaces a shared `zh-TW`/`zh-CN` female-voice pool and excludes `en-US` Zira; existing defaults and valid settings remain unchanged. The four-language README also corrects the English rendering of *電腦情人夢* to *AI Think So!*.
- Azure voice selections now save immediately and apply to the next preview or utterance; the added Mandarin options include only Standard Neural female voices.
- A real Azure Speech Free F0 resource in East Asia completed HTTPS, RIFF audio, and Windows playback validation, while its key remains encrypted only through Windows DPAPI.
- Dragon HD and HD Omni stay out of the free default list because tier, billing, and regional support differ; cloud failure retains the one-time Windows local female fallback.

### v2.3.0 RC4 — 2026-08-11

- Introduces a parametric layered 2.5D face system. Immutable poses, continuous
  viseme parameters, expression semantics, and a replaceable renderer unify
  50 Hz composition across front-facing, left-facing, and chin-rest poses.
- Blinking now uses a generation-safe progressive opacity curve. Eyelids and
  cheek blush follow one layer policy, preventing normal skin from abruptly
  covering blushed cheeks when the front-facing eyes close.
- Happy chin-rest speech keeps smiling eyes but temporarily uses a neutral mouth
  base with only the active viseme; both raised corners return after speech.
- Fixes left-facing neutral speech so the small dark line at the right mouth
  corner no longer remains at its previous position.
- The speech provider, Windows voice, OpenAI TTS voice, and Realtime voice now save immediately when selected. OpenAI TTS uses the new voice on the next utterance; an active Realtime conversation reconnects safely to apply its new voice immediately, without adding a redundant save button.
- Adds asset, controller, renderer, runtime-wiring, and three visual regression
  test groups. Production and visual auditing share one viseme setup path.

### v2.3.0 RC3 — 2026-08-10

- Fixes the blank-document icon shown after minimizing on Windows. EXE, MSI,
  shortcuts, and running windows now use ten native MoHan icon sizes, installed
  paths, and one stable taskbar identity, with the icon reapplied after native
  window flags are final.
- Makes `assets/expressions/idle_front.png` the sole canonical front-facing
  half-body source for the first-run wizard, installer artwork, and taskbar
  icons. The obsolete full-body identity, rain-scene full-body image, and
  unused old icon are removed to prevent future character-identity drift.
- Moves tag, version, `main` ancestry, Release-mode, and four-language-note
  validation into preflight. Known-working squash and GitHub credential paths
  are reused directly instead of repeating known-failing flows.

### v2.3.0 RC2 — 2026-08-10

- Moves the product, tests, and every package exclusively to CPython
  3.15.0rc1, with project-wide explicit PEP 810 lazy imports and static
  governance auditing; no legacy Python path remains.
- Adds deeply immutable PEP 814 `frozendict` configuration, PEP 798 unpacking
  comprehensions, PEP 686 UTF-8 file auditing, PEP 661 sentinel governance,
  the new `bytearray.take_bytes()` audio-buffer API, and Python 3.15's more
  explicit `re.prefixmatch()` for prefix matching.
- Adds PEP 799 Tachyon profiling for startup, 50 Hz lip sync, and expression
  arbitration. Both JIT modes pass the complete suite; 2.3.0 RC2 defaults JIT
  on while retaining a compatibility disable switch.
- Gates sanitized Tachyon evidence on valid samples, stack-read errors, missed
  samples, and JIT state. CycloneDX 1.7 SBOMs require complete dependency
  graphs, PURLs, SPDX licenses, official schema validation, and 100% coverage.
- Forces Node 24 for every GitHub Actions JavaScript action. PySide6 crosses
  the 3.15 metadata limit through a controlled ABI3 wheel validation, while
  Stable ABI, dependency-audit, packaging, and complete release safety gates
  remain unchanged.
- Consolidates the README into one Traditional Chinese, Simplified Chinese,
  English, and Japanese document, removes duplicate compatibility files and
  direct payment links, and points support only to GitHub's official Sponsor button.
### v2.2.0 RC2 — 2026-08-07

- Gives the chin-rest pose a neutral speech-mouth base: the smiling eyes remain,
  both corners stay fixed, and only the central lips follow A/I/U/E/O and jaw
  aperture, eliminating the exaggerated grin and corner ghosting.
- Moves Realtime, Windows local speech, OpenAI natural speech, and Azure Speech
  onto one 20 ms / 50 Hz viseme clock with shorter open, close, and vowel-change
  transitions.
- Releases audio and the first viseme through the same playback gate, rejects
  late vowels after playback ends, and permits only the final closed-mouth cue,
  preventing visemes from stopping early or the mouth from reopening afterward.
- Replaces the complete bilateral eye area during chin-rest idle blinks, so
  open-eye eyeliner cannot remain above closed eyelids; idle and contextual
  expressions now share one authoritative mask definition.
- Makes tagged Draft Release publication recoverable and cleans up failed
  attempts so incomplete assets cannot resemble a finished public release.
- Adds 2 aligned creation-history panels to all four README languages,
  documenting the frame-by-frame care behind MoHan's eyes, mouth corners, and
  lip sync—and the more-than-twenty-year dream Flameblade is turning into
  open-source software through testing.

### v2.2.0 RC1 — 2026-08-06

- Windows x64 remains the complete product surface with the verified ZIP,
  EXE, MSI, MSI language transforms, and installer lifecycle tests.
- Adds native macOS Apple Silicon (arm64) and Intel (x86_64) `.app`/`.dmg`
  packages plus a Linux x86_64 `.AppImage` limited Preview. They expose only
  launch, four-language UI, platform paths, and fail-closed boundaries; they
  claim no Windows feature parity and accept no API keys, OAuth credentials,
  or Home Assistant tokens.
- Pull requests produce short-lived test artifacts only. Only immutable
  `v2.2.0-rc.N` tags can create a GitHub pre-release, after every platform has
  built and executed its package on a native CI runner.
- Releases provide SHA256SUMS, CycloneDX SBOMs, an update manifest, and GitHub
  artifact attestations, with curated Traditional Chinese, Simplified Chinese,
  English, and Japanese release notes.

### v2.1.0 RC1 — 2026-08-04

- Migrated source, Windows CI, and packaging to Python 3.14 while preserving
  an explicit boundary for a future Python 3.15 lazy-import evaluation.
- Added a minimum usable Japanese UI and persona. First run and the interactive
  EXE installer now support Traditional Chinese, Simplified Chinese, English,
  and Japanese; the MSI keeps its Traditional Chinese base plus transforms.
- Made `gpt-5.6-luna` the text-chat default and removed the old mini choice
  from the new-user picker without overwriting custom model settings.
- Added a pluggable speech-provider boundary and an opt-in Azure Speech female-
  voice preview. Windows female local speech remains the first offline and
  failure fallback.
- Improved vector memory retrieval, semantic summarization, safe pruning,
  optional background workers, and Realtime/non-Realtime audio buffering.
- Redesigned first run and the main UI with a bright, high-contrast, larger-
  type theme, an ink-and-technology hero, MoHan installer artwork, visible
  checkboxes, and one consistent MoHan half-body application icon.
- Replaced the author-specific transcription default with neutral localized
  prompts generated from each user's language and profile while preserving
  every existing custom prompt.
- Corrected first-run label alignment and the over-wide smile while the
  chin-rest pose speaks, then refreshed the README and website screenshots.
- Continues the race-condition fixes for pose transitions, physical layers,
  and speech handoffs. Jitter observed in RC3 must be retested with this
  candidate and cannot be treated as a regression in this version.

Verification: 56/56 automated test programs passed for the current RC1 source. The
tagged Windows release workflow also passed source auditing, packaged self-test,
silent EXE/MSI install and uninstall verification, checksum and SBOM generation,
artifact attestation, and security checks.

### v2.0.14 RC3 — 2026-08-02

- Added a Traditional Chinese / Simplified Chinese / English first-run wizard
  and minimum usable English and zh-CN UI paths for chat, voice, permissions,
  profile, work modes, and reminders.
- Added complete English and Simplified Chinese MoHan persona prompts plus
  language-matched offline replies, mode announcements, and built-in reminder
  speech. Switching the UI language translates untouched defaults between all
  three languages without overwriting custom reminder text.
- Changed new-user speech output to Windows local voice so the basic experience
  works without an OpenAI API key. Windows voice selection now lists only
  voices verified as female; zh-TW continues to prefer Microsoft Yating while
  zh-CN prefers a matching installed female voice.
- Added a dedicated Simplified Chinese README and quick-start instructions.
- Added secure in-app stable/preview update checks with official-host
  allowlisting, semantic-version validation, size limits, SHA256 verification,
  explicit install confirmation, and preserved local profiles.
- Added automated Windows x64 EXE and MSI installers with silent
  install/self-test/uninstall verification in GitHub Actions.
- Expanded releases with a complete checksum catalog, CycloneDX SBOM, update
  manifest, artifact attestations, and categorized generated release notes.
- Added optional marker-scoped WordPress download-page synchronization using
  GitHub Secrets and a dedicated WordPress Application Password.
- Added full-history Gitleaks checks as a compensating control for GitHub
  Secret Protection features unavailable to personal public repositories.
- Decoupled the visible “墨寒思考中” status from character expressions.
  Routine text and voice questions now keep a natural pose, complex prompts
  react only after a noticeable delay, and unusually slow responses use the
  existing expression arbiter with cancellation, cooldown, and deduplication.
- Unified AI wait cleanup across successful replies, API failures, standard
  voice, and Realtime transitions so thinking cannot linger into speech or
  remain after playback.

Verification: 45/45 automated test programs passed before the RC3 pull
request. The tagged release workflow must additionally pass public-content
audit, packaged self-test, event-loop smoke test, silent EXE/MSI install and
uninstall verification, checksum generation, SBOM generation, and artifact
attestation before publication completes.

### v2.0.14 RC — 2026-07-31

- Fixed OpenAI streaming WAV headers overflowing during application-local
  volume processing, which could make all cloud speech silent.
- Rebuilt adjusted WAV headers from the audio bytes actually received instead
  of copying streaming placeholder lengths.
- Added automatic Windows Yating fallback when OpenAI speech generation or
  playback fails.
- Routed safe read-only Gmail, Google Calendar, and Google Drive commands from
  the normal text conversation box into the permission-gated tool planner.
- Added regression coverage for cloud-speech fallback, streaming WAV volume
  processing, Gmail chat routing, and work-timer isolation.

Verification: 38/38 automated test programs, real OpenAI TTS playback,
packaged self-test, packaged event-loop smoke test, and post-archive self-test
passed before this release candidate.

### v2.0.13 RC — 2026-07-31

- Added a single motion compositor for breathing, speech emphasis, gaze, and
  emotional gestures.
- Fixed occasional character twitching and layer separation during action
  changes.
- Preserved synchronized body, face, eye, hair, sleeve, and ornament layers.
- Smoothed return-to-idle motion after speech.
- Removed synthetic eye highlights that could appear as white artifacts.
- Improved blink, expression, and AIUEO viseme continuity.
- Added configurable character display scaling.
- Added portable profile transfer and modular service boundaries.
- Added explicit public-preview notices for unverified Microsoft, GitHub, and
  Home Assistant integrations.

Verification: 37 automated test programs and a 25,000-step mixed animation,
speech, gaze, and physics stress test passed before this release candidate.

## 日本語

本書には、墨寒デスクトップアシスタントの主な公開変更をすべて記録します。

### v3.1.2 — 2026-08-12

- OpenAI Realtime のネイティブ音声を完全に維持し、既定かつ追加遅延が最も少ない選択肢とします。従来の音声を好む利用者へ Azure を強制しません。
- Realtime による即時理解と、通常 Azure Speech または Dragon HD のストリーミング発話を組み合わせる任意モードを追加します。安全な短い句が完成するたび順番に合成し、最初の音声断片から再生して TTS の追加待ち時間を抑えますが、ゼロ遅延はうたいません。
- 三つの出力モードを完全に分離して混音せず、他の音声供給元も変更しません。Dragon HD が一つの句で失敗した場合は通常 Azure へ一度、続いて Windows 本機女性音声へ一度だけ代替し、通常 Azure が失敗した場合は Windows 本機女性音声へ一度だけ代替します。代替するのは、その句の音声がまだ再生されていない場合だけです。再生開始後のストリーム障害では句を直ちに停止し、全体を再生し直さないことで重複発話と重複課金を防ぎます。
- Realtime 応答の状態が `completed` の場合だけ最終テキストを確定します。取消、失敗、未完了、切断、過去の応答から遅れて届いたイベントは発話せず、次の応答も汚染しません。
- Azure と Windows 本機音声は、どちらも現在の再生を実際に停止できます。操作 ID、上限付きキュー、長すぎる応答の保護により遅延コールバックを隔離してメモリ負荷を制限し、秘密キーをオブジェクト表現へ出しません。

### v3.1.1 — 2026-08-12

- 通常 Azure と Dragon HD は、選択したリージョンと各自の暗号化キーで実際の女性音声を動的に照会します。男性、非互換モデル、リージョン非対応の HD Flash を除外し、固定一覧は照会失敗時の安全な代替だけに使用します。
- Azure 合成は Speech SDK `PushAudioOutputStream` を使用し、完全 WAV を待たず、最初の 24 kHz PCM16 断片から再生と既存の 50 Hz 口形解析を開始します。
- 実際の East Asia F0 と West US 2 S0 の一覧照会に合格し、当時それぞれ互換性のある中国語女性 Neural 音声 21 件と簡体字中国語 Dragon HD 女性音声三件を取得しました。

### v3.1.0 — 2026-08-11

- 初期状態で無効な Azure Dragon HD／HD Omni 女性音声 Preview を追加し、独立した S0 キー、リージョン、音声設定で動作させ、既存の音声プロバイダーを変更しません。
- Azure リージョンは切替後すぐ保存する選択欄となり、公式対応の女性 HD 音声だけを表示し、HD Flash はリージョン機能に応じて自動的に隠します。
- 三種のクラウドキー入力は、パスワード表示、Windows DPAPI 自動暗号化、保存成功後の入力欄消去を共用します。Dragon HD 失敗時は通常の Azure と Windows 本機女性音声を順に各一回だけ試します。
- Central India S0 の実リソースで Windows の合成と再生を検証しました。台湾からは発話開始前の待ち時間が明確なため、画面と文書に Preview、リージョン遅延、料金の注意を残し、口形同期は従来の 50 Hz 本機音声解析を正規情報源として維持します。

### v3.0.0 — 2026-08-11

- プロジェクト所有者が自ら認定した初の正式安定版であり、v2.3.0 候補系列の完全検証後に昇格した第三世代の節目です。
- 頬杖姿勢の口形は左右の口角まで更新します。50 Hz 解析を保ちながら、母音の三フレーム確認と 50 ミリ秒補間で先走り、跳ね、残留口角を防ぎます。
- 発話連動の呼吸、袖、髪を待機呼吸へ滑らかにつなぎ、発話終了時の一フレームだけの身体揺れを解消しました。
- Windows ショートカットとネイティブウィンドウは EXE 内蔵の半身アイコンを共用し、本機インストーラーテストによる実デスクトップやタスクバーのアイコン参照元の汚染を禁止しました。OpenAI TTS と Realtime の共通音声も一つの正規順序から生成します。

### v2.3.0 RC5 — 2026-08-11

- Azure Speech の中国語女性音声を繁体字・簡体字画面から言語横断で選択でき、現在の画面言語を優先して並べます。Windows 本機音声でも両中国語画面が `zh-TW`／`zh-CN` 女性音声プールを共有し、`en-US` Zira を除外します。既定値と有効な保存済み設定は変更しません。四言語 README では『電腦情人夢』の英訳も『AI Think So!』へ訂正しました。
- Azure 音声は選択時に直ちに保存し、次の試聴または読み上げから適用します。追加する普通話選択肢には Standard Neural 女性音声だけを含めます。
- East Asia の実 Azure Speech Free F0 リソースで HTTPS、RIFF 音声、Windows 再生を検証し、キーは引き続き Windows DPAPI だけで暗号化します。
- Dragon HD／HD Omni はプラン、課金、対応リージョンが異なるため無料の既定一覧へ混在させず、クラウド障害時の Windows 本機女性音声への一度だけの代替を維持します。

### v2.3.0 RC4 — 2026-08-11

- パラメーター化された多層 2.5D 顔システムを導入し、不変の姿勢、連続的な
  口形パラメーター、表情の意味情報、交換可能なレンダラーにより、正面、
  左向き、頬杖の三姿勢で 50 Hz の口形と表情合成を統一しました。
- まばたきを世代保護付きの段階的な不透明度曲線へ変更しました。まぶたと頬の
  赤みを同じレイヤー規則で合成し、正面の赤面中に通常の肌色が頬を覆いません。
- 頬杖で微笑みながら話す間は目元の笑みを保ち、口を中立基底へ一時的に戻して
  発話口形だけを適用し、発話終了後に両側の上がった口角を復元します。
- 頬杖ではない左向きの中立発話で、右口角の小さな黒線が以前の位置に残る
  問題を修正しました。
- 「音声」タブの読み上げ方式、Windows 音声、OpenAI TTS 音声、Realtime 音声は、選択時に即座に保存されます。OpenAI TTS は次の読み上げから新しい音声を使用し、Realtime 会話が接続中の場合は安全に再接続して新しい音声を即時適用します。重複する保存ボタンは追加しません。
- 素材、制御器、レンダラー、実行時接続、三つの視覚回帰テストを追加し、
  製品と視覚監査ツールが同一の口形設定を共有するようにしました。

### v2.3.0 RC3 — 2026-08-10

- Windows で最小化した後に空白文書アイコンが表示される問題を修正しました。
  EXE、MSI、ショートカット、実行中ウィンドウは、十段階のネイティブ墨寒
  アイコン、インストール済みパス、固定タスクバー ID を使い、ネイティブ
  ウィンドウフラグ確定後にアイコンを再適用します。
- 初回設定ウィザード、インストーラー画像、タスクバーアイコンの正式な正面向き
  半身素材を `assets/expressions/idle_front.png` に統一しました。旧版の顔立ちを
  持つ全身像、雨景の全身像、未使用の旧アイコンを削除し、今後の人物同一性の
  ずれを防ぎます。
- タグ、バージョン、`main` 履歴、Release モード、四言語説明を事前検証へ移し、
  成功が既知の squash と GitHub 認証経路を直接再利用して、失敗が既知の処理を
  繰り返さないようにしました。

### v2.3.0 RC2 — 2026-08-10

- 製品、テスト、全パッケージを CPython 3.15.0rc1 のみに移行し、旧 Python
  経路を廃止しました。PEP 810 の明示的遅延インポートと静的ガバナンス監査を
  全プロジェクトへ導入しました。
- PEP 814 `frozendict` の深い不変設定、PEP 798 の内包表記アンパック、
  PEP 686 UTF-8 ファイル監査、PEP 661 センチネル管理、新しい
  `bytearray.take_bytes()` 音声バッファー API、先頭一致を明示する Python 3.15 の
  `re.prefixmatch()` を導入しました。
- PEP 799 Tachyon による起動、50 Hz 口形同期、表情調停のサンプリング解析を
  導入しました。JIT の有無は全テストに合格し、2.3.0 RC2 では既定で有効に
  しながら互換性用の無効化設定を残します。
- Tachyon 証拠は有効サンプル、読取エラー、漏れ、JIT 状態で判定し、匿名化して
  公開します。CycloneDX 1.7 SBOM は完全な依存関係、PURL、SPDX ライセンス、
  公式スキーマ検証、100% 網羅を必須とします。
- GitHub Actions の JavaScript 動作はすべて Node 24 を強制します。PySide6 は
  管理された ABI3 wheel 検証によって 3.15 のメタデータ制限に対応し、Stable
  ABI、依存関係の安全監査、パッケージング、完全なリリース安全ゲートを維持します。
- README を繁体字中国語、簡体字中国語、英語、日本語の一つの四言語文書へ統合し、
  重複する互換文書と直接決済リンクを削除しました。支援案内はリポジトリ上部の
  公式 Sponsor ボタンだけに統一します。
### v2.2.0 RC2 — 2026-08-07

- 頬杖姿勢の発話中は中立な口角ベースを使用します。目元の笑みを残しながら
  左右の口角を固定し、中央の唇だけを A／I／U／E／O と開口量に合わせて
  動かすことで、誇張された笑顔と残像を防ぎます。
- Realtime、Windows ローカル音声、OpenAI 自然音声、Azure Speech を
  共通の 20 ミリ秒／50 Hz 口形周期へ統一し、開口、閉口、母音切り替えの
  遅延を短縮します。
- 音声と最初の口形を同じ再生ゲートから開始し、再生終了後の遅延母音を拒否、
  最後の閉口信号だけを通すことで、口だけが先に止まる現象や音声終了後に
  再び口が開く現象を防ぎます。
- 頬杖の待機中のまばたきでは両目全体を覆う共通マスクを使用し、閉じた
  まぶたの上に開眼時のアイラインが残らないようにしました。待機表情と
  状況表情は同じ座標・合成定義を共有します。
- タグ発行時の Draft Release を安全に復旧・整理できるようにし、失敗した
  発行が不完全な公開版として残らないようにしました。
- 四言語 README に統一規格の制作過程図を2枚追加し、目、口角、口形を
  フレーム単位で確認しながら、二十年以上の夢をテストによってオープンソース
  作品へ鍛える姿勢を伝えます。

### v2.2.0 RC1 — 2026-08-06

- Windows x64 を完全機能版として維持し、検証済みの ZIP、EXE、MSI、MSI
  言語変換、およびインストール／削除テストを継続します。
- macOS Apple Silicon（arm64）／Intel（x86_64）両方のネイティブ
  `.app`／`.dmg` と Linux x86_64 `.AppImage` の機能限定 Preview を追加します。
  起動、四言語画面、保存先、安全な無効化だけを提供し、Windows 版との同等性を
  主張せず、API キー、OAuth 認証情報、Home Assistant Token の入力も受け付けません。
- Pull Request は短期テスト用成果物だけを作成します。GitHub のプレリリースを
  作成できるのは変更しない `v2.2.0-rc.N` タグだけで、各 OS のネイティブ CI
  上で配布物を作成し、起動確認に合格する必要があります。
- SHA256SUMS、CycloneDX SBOM、更新マニフェスト、GitHub 成果物証明を提供し、
  Release 説明は繁体字中国語・簡体字中国語・英語・日本語で作成します。

### v2.1.0 RC1 — 2026-08-04

- ソースコード、Windows CI、配布物を Python 3.14 へ移行し、将来の
  Python 3.15 lazy imports 評価に備えた境界を残しました。
- 日本語の最小利用経路と人格を追加しました。初回設定と対話型 EXE
  インストーラーは、繁体字中国語、簡体字中国語、英語、日本語に対応します。
  MSI は繁体字中国語を基準とし、三つの言語変換を提供します。
- 文字会話の既定を `gpt-5.6-luna` に変更し、新規利用者向け一覧から旧 mini
  を削除しました。独自モデル設定は上書きしません。
- 交換可能な音声供給元と Azure Speech 女性音声プレビューを追加しました。
  キー不足、オフライン、障害時は Windows 本機女性音声へ最初に戻ります。
- 長期記憶のベクトル検索、意味要約、安全な整理、任意の背景ワーカー、音声
  バッファーを改善しました。
- 初回設定と本体画面を明るく高コントラストな大きめ文字へ刷新し、古風と
  技術を融合した背景、墨寒のインストール画像、見やすいチェック欄、統一した
  墨寒半身アイコンを追加しました。
- 音声文字起こしの既定文を、繁体字中国語、簡体字中国語、英語、日本語と
  利用者設定から作る中立的な内容へ変更しました。既存の独自文は上書きしません。
- 初回設定の項目名の縦位置と、頬杖姿勢で話す際の過度に広い笑顔を修正し、
  README と公式サイトの実機画像を最新版へ更新しました。
- 姿勢切り替え、物理レイヤー、発話の受け渡しに関する競合修正を継続します。
  RC3 で観察された揺れは本候補版で再検証する必要があり、本版の回帰とは
  見なせません。

検証：現在の RC1 ソースでは 56/56 個の自動テストプログラムが合格しました。
タグ付き Windows リリースワークフローも、ソース監査、パッケージ自己テスト、
EXE／MSI の無人インストールとアンインストール検証、checksum と SBOM の生成、
成果物証明、セキュリティ検査に合格しました。

### v2.0.14 RC3 — 2026-08-02

- 繁体字中国語／簡体字中国語／英語の初回設定ウィザードと、チャット、音声、
  権限、プロファイル、作業モード、リマインダー向けの最低限利用可能な英語および
  zh-CN UI 経路を追加しました。
- 完全な英語・簡体字中国語の墨寒人格プロンプトと、言語に合うオフライン応答、
  モード通知、組み込みリマインダー音声を追加しました。UI 言語を切り替えると、
  未変更の既定値を三言語間で翻訳し、独自のリマインダー文は上書きしません。
- 新規利用者の音声出力を Windows ローカル音声へ変更し、基本体験では OpenAI
  API キーを不要にしました。Windows の音声一覧には検証済みの女性音声だけを
  表示します。zh-TW は引き続き Microsoft Yating を優先し、zh-CN は一致する
  インストール済み女性音声を優先します。
- 簡体字中国語専用の README とクイックスタート手順を追加しました。
- 公式ホスト許可リスト、セマンティックバージョン検証、サイズ制限、SHA256 検証、
  明示的なインストール確認、ローカルプロファイル保持を備えた、安全なアプリ内
  安定版／プレビュー版更新確認を追加しました。
- Windows x64 EXE／MSI インストーラーを自動化し、GitHub Actions で無人
  インストール、自己テスト、アンインストールを検証します。
- 完全な checksum 一覧、CycloneDX SBOM、更新マニフェスト、成果物証明、分類済み
  自動生成 Release notes をリリースへ追加しました。
- GitHub Secrets と専用 WordPress Application Password を使う、任意の
  マーカー範囲限定 WordPress ダウンロードページ同期を追加しました。
- 個人公開リポジトリで利用できない GitHub Secret Protection 機能の補償統制として、
  Git 全履歴の Gitleaks 検査を追加しました。
- 表示される「墨寒思考中」状態をキャラクター表情から分離しました。通常の文字・
  音声質問では自然な姿勢を保ち、複雑なプロンプトには明確な遅延後だけ反応し、
  異常に遅い応答では取消、クールダウン、重複排除を備えた既存の表情調停器を使います。
- 成功応答、API 障害、通常音声、Realtime 遷移における AI 待機終了処理を統一し、
  思考状態が発話へ残ったり、再生後に消えなかったりすることを防ぎます。

検証：RC3 Pull Request 前に 45/45 個の自動テストプログラムが合格しました。
タグ付きリリースワークフローは公開完了前に、公開内容監査、パッケージ自己テスト、
イベントループ smoke test、EXE／MSI の無人インストールとアンインストール検証、
checksum 生成、SBOM 生成、成果物証明にも合格しなければなりません。

### v2.0.14 RC — 2026-07-31

- アプリ内音量処理中に OpenAI ストリーミング WAV ヘッダーがオーバーフローし、
  すべてのクラウド音声が無音になる可能性がある問題を修正しました。
- ストリーミング用プレースホルダー長をコピーせず、実際に受信した音声バイトから
  調整後の WAV ヘッダーを再構築しました。
- OpenAI 音声の生成または再生に失敗した場合、Windows Yating へ自動的に
  フォールバックするようにしました。
- 通常のテキスト会話欄に入力された安全な読み取り専用 Gmail、Google Calendar、
  Google Drive コマンドを、権限ゲート付きツールプランナーへ送るようにしました。
- クラウド音声フォールバック、ストリーミング WAV 音量処理、Gmail 会話ルーティング、
  作業タイマー分離の回帰テストを追加しました。

検証：このリリース候補の公開前に、38/38 個の自動テストプログラム、実際の OpenAI
TTS 再生、パッケージ自己テスト、パッケージイベントループ smoke test、アーカイブ後
自己テストが合格しました。

### v2.0.13 RC — 2026-07-31

- 呼吸、発話強調、視線、感情ジェスチャーを扱う単一モーションコンポジターを
  追加しました。
- 動作変更時にまれに発生するキャラクターの揺れとレイヤー分離を修正しました。
- 身体、顔、目、髪、袖、装飾レイヤーの同期を維持しました。
- 発話後に待機状態へ戻る動きを滑らかにしました。
- 白いアーティファクトとして現れる可能性がある人工的な目のハイライトを削除しました。
- まばたき、表情、AIUEO 口形の連続性を改善しました。
- 設定可能なキャラクター表示倍率を追加しました。
- ポータブルプロファイル移行とモジュール化されたサービス境界を追加しました。
- 未検証の Microsoft、GitHub、Home Assistant 連携に、明示的な公開プレビュー
  警告を追加しました。

検証：このリリース候補の公開前に、37 個の自動テストプログラムと、25,000 ステップの
アニメーション、音声、視線、物理を混合したストレステストが合格しました。
