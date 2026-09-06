# 專案規範索引／项目规范索引／Project Rules Index／プロジェクト規範索引

## 繁體中文

### 範圍與效力

墨寒是個人開發的業餘中大型專案，制度與交付品質比照大型商業軟體；以興趣專案節奏持續維護，不因人力或進度降低既定門檻。符合商業或外部稽核要求的宣稱，必須有對應證據。

本索引涵蓋整個墨寒專案，供修改前查閱；它不取代原始契約，不表示所有規則已通過驗證，也不將歷史測試或發版紀錄視為目前狀態。擁有者後續明確裁決優先於較早的同範圍要求；不同範圍的規則不能互相取消，尤其開發授權不會取消產品內的安全確認。

### 制度與查核入口

美術判斷以正常解剖、自然姿態與物理合理性為基本要求，包括透視、重心、接觸、遮擋及光影一致。五指五趾是解剖要求，不是要求每根都露出；不可為了數清楚而刻意張開、改變核可姿態或犧牲美感。自然遮擋不構成單獨重繪的理由。

- 協作與品質：先讀工作區交接及 [代理規則](../AGENTS.md)，檢查實際工作樹與正式產物；保留既有變更，跨專案隔離，不破壞舊功能，不以計數、候選圖或部分測試冒充驗收。依 [治理](../GOVERNANCE.md) 維持可追溯審查。
- 架構：依 [架構契約](../ARCHITECTURE.md) 維持五層單一責任、公開型別化介面、依賴注入及單一仲裁來源；禁止循環、反向依賴、重複政策、計時器或私有介面跨功能呼叫。新模組行數與既有只降不升棘輪由既有測試約束，不新增豁免。
- 語言與工程：依 [語言遷移](PYTHON-3.15-MIGRATION.md) 與 [靜態設定](../ruff.toml) 使用專案指定的 Python、明示延遲匯入及可適用的新語法；函式內不用延遲匯入。所有工程與工作流程遵守 Python 之禪，保留相容性、可觀測失敗與可執行退路。
- 四語：依 [發布規則](../PUBLISHING.md) 維持繁中、簡中、英文、日文的內容與結構平行，包括對外文件、標題、PR 內文、發布說明及介面；內部穩定設定值不得使用翻譯標籤。新增變更使用 [片段目錄](../changelog.d/)，不直接重寫發布歷史。
- 測試：依 [測試策略](TESTING.md) 使用開發快速套、提交前完整套及必要隔夜套；快速套無法對應時接受完整回退。測試具直接入口與成功標記，失敗不可刪斷言或放寬門檻；自動化、實機、封裝、發布分別取證。
- 防護有效性：依 [變異稽核](release-evidence/gate-mutation-audit-2026-09-04.md) 確認失效的防護會使測試失敗；依 [吞錯裁決](release-evidence/swallowed-error-audit-2026-09-04.md) 對使用者資料問題提示，工具失敗明確回傳失敗，不把清理錯誤蓋過原始錯誤。
- 效能：依 [合成預算](PERFORMANCE-BUDGET.md) 記錄真實環境與獨立樣本；少於三筆只記錄並說明原因，足量才依既定公式擋門。效能宣稱限實測路徑；原生加速、JIT、取樣品質與 Python 對照證據不能互相代替。
- 權限：依 [安全政策](../SECURITY.md) 由本機政策而非模型授權；產品黃色操作須確認、紅色雙確認，永久禁止的操作保持禁止。緊急停止、具名取消隔離、允許清單及智慧家庭高風險分類都須保留。
- 秘密與資料：依 [旗艦規格](../FLAGSHIP-SPEC.md) 與安全政策保存個人設定、對話及遷移相容性；秘密走核准的作業系統儲存，不進原始碼、資料庫、紀錄、截圖或發行包。更新簽章私鑰由擁有者管理，本工作不得讀取。
- 攜帶與備份：依架構契約排除機器權限、裝置狀態及本機路徑；敏感內容只在明確選擇與強密碼加密後攜帶，驗證失敗不套用。保留快照重複匯入防護、舊快照警告、變更前及每日備份。
- 記憶：依 [記憶規則](MEMORY-RETRIEVAL-AND-PRUNING.md) 本機索引、內容指紋失效及可還原封存；容量剪枝只處理符合條件的低重要度對話，不刪手動、重要或人物資料。
- 感知與手勢：依 [手勢規格](GESTURE-INTERACTION.md) 與架構契約預設關閉、保存授權、配額及撤銷；原始影像不落地，骨架敏感樣本獨立加密。過期、低信心或缺模型不猜測、不派送，保留其他功能。
- 背景工作：依 [背景工作者](BACKGROUND-MANAGER-WORKERS.md) 保持唯讀觀察、主線仲裁、冷卻及專注保護；背景工作者不能直接控制語音、表情、工具或權限。
- 語音：依 [供應器契約](PLUGGABLE-SPEECH-PROVIDERS.md) 保留單一嘴型與播放生命週期、女性本機備援及供應器隔離；播放開始後失敗不得整句重播。擁有者指定的本機墨寒語音使用 Yating、OneCore 與正常語速。
- 授權：依 [白名單](LICENSE-PURITY.md)、[黑名單](LICENSE-BLACKLIST.md) 與 [角色授權](../ASSETS-LICENSE.md) 分別檢查程式、權重及角色資產。三項既有例外為 PySide6、PyInstaller、Azure Speech SDK；不得擴張成其他例外。字型 OFL 原文不可修改，角色美術不因程式採 MIT 而成為 MIT。
- 角色身份與分層：依 [半身](../DLC_ART_ASSET_SPEC.md)、[身體](../DLC_ART_ASSET_SPEC_BODY.md)、[全身](../DLC_ART_ASSET_SPEC_FULLBODY.md) 及外觀包契約維持權威身份、畫布、錨點、深度與透明邊緣。頭髮、衣裝、髮飾、妝容與手部可拆，不能用拼貼、烘焙或錯位遮掩缺陷。
- 解剖與美術：每手五指、每腳五趾是既有 [製圖條件](../tools/second_gen_body/chroma_mass_produce_v9.py)，並有 [手部稽核](../domain/hand_asset_audit.py) 與 [證據契約](../domain/hand_asset_evidence.py)。骨架點數不等於實際指數已驗收；遮擋須有證據，不能掩蓋增指、缺指、黏連或接縫。
- 外觀 DLC：依 [外觀包](OUTFIT-PACKS.md) 保留完整三十一視角、各槽混搭、原子安裝、保存與取消、不可刪官方包、來源授權及執行期世代拒絕。妝容三槽、安全區、虹膜與口腔排除、持久濃淡與同一路徑預覽都須成立。
- 自主換裝：沿用外觀包的手動鎖定、冷卻、天氣與場合政策；生成和趨勢搜尋分開授權，成本與容量有界。隔離候選通過全部稽核才可安裝，滿額不能自刪使用者套件，展示待辦須說完才完成。
- 姿態與主題：依 [姿態包](POSE-PACKS.md) 和 [主題包](THEME-PACKS.md) 使用自含宣告式包、來源雜湊、尺寸與壓縮限制；拒絕執行碼、危險路徑及外部引用，維持預覽、啟用與刪除保護。主題只控制語意樣式，不接管 UI 結構；對比至少符合既有門檻。
- 媒體：依 [媒體世代](MEDIA-PROVENANCE.md) 及 [介面素材來源](UI-ASSET-PROVENANCE.md) 保存實檔雜湊與生成來源；預覽與桌面用同一合成路徑，影片走正常語速 OneCore，不拿舊世代截圖代表新素材。
- 平台：依 [跨平台](CROSS-PLATFORM.md) 與 [預覽包](PREVIEW-PACKAGES.md) 維持 Windows 完整功能與其他平台明確限制；CI 不等於作者真機驗收，不以明文儲存或停用系統防護繞過限制。
- 合併與發版：依發布規則及擁有者裁決，所有修改經 PR、必要檢查全綠、對話解決、鎖定 head；每個合併須擁有者明確點名並使用四語 squash 標題。發布另行授權，標籤不可移動，需精確產物、SBOM、雜湊、來源證明、簽章及安裝生命週期證據。

### 差異與待核實項目

JIT 的歷史預設已由 [PR #109](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/pull/109) 因實機穩定性問題改為關閉；現行 [啟動器](../tools/jit_launcher.py) 只有在 `MOHAN_ENABLE_JIT=1` 時開啟。較早遷移文件中的預設開啟敘述不能作為目前行為依據。

原始文件中舊版本號、測試數量與「尚未發布」屬歷史狀態；舊 Qt 官方 metadata 阻擋已由架構契約中的相容層政策取代。舊美術限定代理不可寫程式、保留舊臉及上衣款式，已由本次擁有者整合授權、V4 外觀標準及細肩帶短版運動素體裁決取代。一般自主作業不需逐步詢問；重大事項與美術正式接入仍保留確認。

Tachyon 存在待核實差異：本次交接稱讀取錯誤率門檻為百分之一，但本工作樹 CI 與 Release 明示百分之十五，命令列預設百分之八十。這是規則與設定落差，不能宣稱一致，也不能在本索引內自行放寬或改寫門檻。舊語音文件稱不安裝 Azure SDK，但目前需求清單包含 SDK；需區分各供應器實作與歷史描述。已讀文件不等於目前全專案合規。

## 简体中文

### 范围与效力

墨寒是个人开发的业余中大型项目，制度与交付质量比照大型商业软件；按兴趣项目节奏持续维护，不因人力或进度降低既定门槛。符合商业或外部审计要求的声明，必须有对应证据。

本索引覆盖整个墨寒项目，供修改前查阅；它不替代原始契约，不表示所有规则已通过验证，也不将历史测试或发布记录视为当前状态。所有者后续明确裁决优先于较早的同范围要求；不同范围的规则不能互相取消，尤其开发授权不会取消产品内的安全确认。

### 制度与检查入口

美术判断以正常解剖、自然姿态与物理合理性为基本要求，包括透视、重心、接触、遮挡及光影一致。五指五趾是解剖要求，不是要求每根都露出；不可为了数清楚而刻意张开、改变核准姿态或牺牲美感。自然遮挡不构成单独重绘的理由。

- 协作与质量：先读工作区交接及 [代理规则](../AGENTS.md)，检查实际工作树与正式产物；保留现有更改，隔离不同项目，不破坏旧功能，不以计数、候选图或部分测试冒充验收。依 [治理](../GOVERNANCE.md) 保持可追溯审查。
- 架构：依 [架构契约](../ARCHITECTURE.md) 保持五层单一职责、公开类型化接口、依赖注入及单一仲裁来源；禁止循环、反向依赖、重复策略、计时器或跨功能调用私有接口。新模块行数与现有只降不升基线由既有测试约束，不新增豁免。
- 语言与工程：依 [语言迁移](PYTHON-3.15-MIGRATION.md) 与 [静态配置](../ruff.toml) 使用项目指定的 Python、显式延迟导入及适用的新语法；函数内不用延迟导入。所有工程与工作流程遵守 Python 之禅，保留兼容性、可观测失败与可执行退路。
- 四语：依 [发布规则](../PUBLISHING.md) 保持繁中、简中、英文、日文内容与结构平行，包括对外文档、标题、PR 正文、发布说明及界面；内部稳定配置值不得使用翻译标签。新增更改使用 [片段目录](../changelog.d/)，不直接重写发布历史。
- 测试：依 [测试策略](TESTING.md) 使用开发快速套、提交前完整套及必要夜间套；快速套无法匹配时接受完整回退。测试有直接入口与成功标记，失败不可删除断言或放宽门槛；自动化、实机、打包、发布分别取证。
- 防护有效性：依 [变异审计](release-evidence/gate-mutation-audit-2026-09-04.md) 确认失效防护会使测试失败；依 [吞错裁决](release-evidence/swallowed-error-audit-2026-09-04.md) 提示用户数据问题，工具失败明确返回失败，不用清理错误覆盖原始错误。
- 性能：依 [合成预算](PERFORMANCE-BUDGET.md) 记录真实环境与独立样本；少于三笔仅记录并说明原因，足量才按既定公式设门槛。性能声明限实测路径；原生加速、JIT、采样质量与 Python 对照证据不能互相替代。
- 权限：依 [安全政策](../SECURITY.md) 由本地政策而非模型授权；产品黄色操作须确认、红色双确认，永久禁止的操作保持禁止。紧急停止、具名取消隔离、允许列表及智能家居高风险分类都须保留。
- 秘密与数据：依 [旗舰规格](../FLAGSHIP-SPEC.md) 与安全政策保留个人配置、对话及迁移兼容性；秘密通过批准的操作系统存储，不进入源代码、数据库、日志、截图或发布包。更新签名私钥由所有者管理，本工作不得读取。
- 携带与备份：依架构契约排除机器权限、设备状态及本地路径；敏感内容仅在明确选择与强密码加密后携带，验证失败不应用。保留快照重复导入防护、旧快照警告、更改前及每日备份。
- 记忆：依 [记忆规则](MEMORY-RETRIEVAL-AND-PRUNING.md) 使用本地索引、内容指纹失效及可恢复归档；容量剪枝仅处理符合条件的低重要度对话，不删手动、重要或人物数据。
- 感知与手势：依 [手势规格](GESTURE-INTERACTION.md) 与架构契约默认关闭、保存授权、配额及撤销；原始图像不落地，骨架敏感样本独立加密。过期、低置信或缺模型不猜测、不派发，保留其他功能。
- 后台工作：依 [后台工作者](BACKGROUND-MANAGER-WORKERS.md) 保持只读观察、主线程仲裁、冷却及专注保护；后台工作者不能直接控制语音、表情、工具或权限。
- 语音：依 [提供商契约](PLUGGABLE-SPEECH-PROVIDERS.md) 保留单一口型与播放生命周期、女性本地备用语音及提供商隔离；播放开始后失败不得整句重播。所有者指定的本地墨寒语音使用 Yating、OneCore 与正常语速。
- 授权：依 [白名单](LICENSE-PURITY.md)、[黑名单](LICENSE-BLACKLIST.md) 与 [角色授权](../ASSETS-LICENSE.md) 分别检查程序、权重及角色资产。三项既有例外为 PySide6、PyInstaller、Azure Speech SDK；不得扩展为其他例外。字体 OFL 原文不可修改，角色美术不因程序采用 MIT 而成为 MIT。
- 角色身份与分层：依 [半身](../DLC_ART_ASSET_SPEC.md)、[身体](../DLC_ART_ASSET_SPEC_BODY.md)、[全身](../DLC_ART_ASSET_SPEC_FULLBODY.md) 及外观包契约保持权威身份、画布、锚点、深度与透明边缘。头发、服装、头饰、妆容与手部可拆，不能以拼贴、烘焙或错位掩盖缺陷。
- 解剖与美术：每手五指、每脚五趾是既有 [制图条件](../tools/second_gen_body/chroma_mass_produce_v9.py)，并有 [手部审计](../domain/hand_asset_audit.py) 与 [证据契约](../domain/hand_asset_evidence.py)。骨架点数不等于实际指数已验收；遮挡须有证据，不能掩盖增指、缺指、粘连或接缝。
- 外观 DLC：依 [外观包](OUTFIT-PACKS.md) 保留完整三十一视角、各槽混搭、原子安装、保存与取消、不可删官方包、来源授权及执行期世代拒绝。妆容三槽、安全区、虹膜与口腔排除、持久浓淡与同一路径预览都须成立。
- 自主换装：沿用外观包的手动锁定、冷却、天气与场合政策；生成与趋势搜索分别授权，成本与容量有界。隔离候选通过全部审计才可安装，满额不能自删用户包，展示待办须说完才完成。
- 姿态与主题：依 [姿态包](POSE-PACKS.md) 和 [主题包](THEME-PACKS.md) 使用自含声明式包、来源哈希、尺寸与压缩限制；拒绝执行代码、危险路径及外部引用，保持预览、启用与删除保护。主题仅控制语义样式，不接管 UI 结构；对比至少符合既有门槛。
- 媒体：依 [媒体世代](MEDIA-PROVENANCE.md) 及 [界面素材来源](UI-ASSET-PROVENANCE.md) 保存实文件哈希与生成来源；预览与桌面用同一合成路径，视频走正常语速 OneCore，不以旧世代截图代表新素材。
- 平台：依 [跨平台](CROSS-PLATFORM.md) 与 [预览包](PREVIEW-PACKAGES.md) 保持 Windows 完整功能与其他平台明确限制；CI 不等于作者实机验收，不以明文存储或停用系统防护绕过限制。
- 合并与发布：依发布规则及所有者裁决，全部更改经 PR、必要检查全绿、对话解决、锁定 head；每个合并须所有者明确点名并使用四语 squash 标题。发布另行授权，标签不可移动，需要精确产物、SBOM、哈希、来源证明、签名及安装生命周期证据。

### 差异与待核实项目

JIT 的历史默认值已由 [PR #109](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/pull/109) 因实机稳定性问题改为关闭；现行 [启动器](../tools/jit_launcher.py) 仅在 `MOHAN_ENABLE_JIT=1` 时开启。较早迁移文档中默认开启的描述不能作为当前行为依据。

原始文档的旧版本号、测试数量及“尚未发布”属于历史状态；旧 Qt 官方 metadata 阻挡已由架构契约的兼容层政策取代。旧美术限定代理不可写程序、保留旧脸及上衣款式，已由本次所有者整合授权、V4 外观标准及细肩带短版运动素体裁决取代。一般自主工作不需逐步询问；重大事项与美术正式接入仍保留确认。

Tachyon 存在待核实差异：本次交接称读取错误率门槛为百分之一，但本工作树 CI 与 Release 明示百分之十五，命令行默认为百分之八十。这是规则与配置落差，不能声称一致，也不能在本索引内自行放宽或改写门槛。旧语音文档称不安装 Azure SDK，但当前需求清单包含 SDK；需区分各提供商实现与历史描述。已读文档不等于当前全项目合规。

## English

### Scope and authority

MoHan is a medium-to-large personal hobby project whose governance and delivery quality follow large commercial software standards. Maintenance follows a sustainable hobby pace without lowering established gates for staffing or deadlines. Commercial or external audit readiness claims require corresponding evidence.

This index covers the entire MoHan project for pre-change review. It does not replace original contracts, certify compliance, or treat historical test and release records as current status. Later explicit owner decisions supersede earlier requirements of the same scope. Rules of different scopes do not cancel each other; development authorization does not remove product safety confirmations.

### Rules and verification entry points

Art must respect normal anatomy, natural poses and physical plausibility, including perspective, balance, contact, occlusion and consistent lighting. Five fingers and five toes are anatomical requirements, not a requirement to expose every digit. Do not spread digits, alter approved poses or sacrifice aesthetics merely to make counting easier. Natural occlusion alone is not a reason to redraw.

- Collaboration and quality: read the workspace handoff and [agent rules](../AGENTS.md), inspect the actual worktree and formal outputs, preserve existing changes, isolate projects, and protect existing behavior. Counts, candidates, and partial tests are not acceptance. Follow [governance](../GOVERNANCE.md) for traceable review.
- Architecture: follow the [architecture contract](../ARCHITECTURE.md) for five-layer ownership, public typed interfaces, dependency injection, and single arbitration authorities. Reject cycles, reverse dependencies, duplicate policies or timers, and cross-feature private calls. Existing tests enforce new-module limits and downward-only line baselines without new exemptions.
- Language and engineering: follow [runtime migration](PYTHON-3.15-MIGRATION.md) and [static configuration](../ruff.toml) for the specified Python, explicit lazy imports, and applicable modern syntax; no lazy imports inside functions. Apply the Zen of Python to engineering and workflows, retaining compatibility, observable failures, and executable fallback paths.
- Four languages: follow [publication rules](../PUBLISHING.md) for parallel Traditional Chinese, Simplified Chinese, English, and Japanese content and structure, including public documents, titles, PR bodies, release notes, and UI. Stable stored values must not use translated labels. Use the [fragment directory](../changelog.d/) rather than rewriting release history.
- Testing: follow the [test strategy](TESTING.md) for development fast suites, complete pre-commit suites, and applicable nightly suites. Accept complete fallback when impact mapping fails. Tests need direct entry points and success markers; never delete assertions or loosen gates to pass. Automation, device acceptance, packaging, and release require separate evidence.
- Effective guards: follow the [mutation audit](release-evidence/gate-mutation-audit-2026-09-04.md) to establish that broken guards fail tests. Follow the [error-handling decision](release-evidence/swallowed-error-audit-2026-09-04.md) to surface user-data failures and fail tools explicitly, without masking original errors with cleanup failures.
- Performance: follow the [compositing budget](PERFORMANCE-BUDGET.md) using real environments and independent samples. Fewer than three samples remain observational with a reason; sufficient samples enable the established formula. Claims apply only to measured paths; native acceleration, JIT, sampling quality, and Python equivalence evidence are distinct.
- Permissions: follow [security policy](../SECURITY.md); local policy, not the model, grants authority. Product yellow actions need confirmation, red actions need two, and prohibited actions remain prohibited. Preserve emergency stop, named-cancellation isolation, allowlists, and smart-home risk classification.
- Secrets and data: follow the [flagship specification](../FLAGSHIP-SPEC.md) and security policy to preserve profiles, conversations, and migrations. Secrets use approved operating-system storage and never enter code, databases, logs, screenshots, or distributions. The owner manages the update-signing private key; this work must not read it.
- Transfer and backup: follow architecture contracts to exclude machine permissions, device state, and local paths. Sensitive transfer requires explicit selection and strong-password encryption; failed verification applies nothing. Preserve duplicate-snapshot protection, older-snapshot warnings, pre-change backups, and daily backups.
- Memory: follow [memory rules](MEMORY-RETRIEVAL-AND-PRUNING.md) for local indexing, content-fingerprint invalidation, and restorable archives. Capacity pruning only affects eligible low-importance conversational records, never manual, important, or person records.
- Perception and gestures: follow the [gesture specification](GESTURE-INTERACTION.md) and architecture for default-off operation, persisted consent, quotas, and revocation. Raw images are not stored; sensitive skeleton samples are separately encrypted. Expired, uncertain, or model-less observations neither guess nor dispatch and preserve other features.
- Background work: follow [worker rules](BACKGROUND-MANAGER-WORKERS.md) for read-only observations, main-thread arbitration, cooldowns, and focus protection. Workers cannot directly control speech, expressions, tools, or permissions.
- Speech: follow [provider contracts](PLUGGABLE-SPEECH-PROVIDERS.md) for one lip-sync and playback lifecycle, female local fallback, and provider isolation. Failure after playback begins must not replay the entire sentence. The owner-selected local MoHan voice uses Yating, OneCore, and normal speed.
- Licensing: consult the [allowlist](LICENSE-PURITY.md), [denylist](LICENSE-BLACKLIST.md), and [character license](../ASSETS-LICENSE.md) separately for code, weights, and character assets. Existing exceptions are PySide6, PyInstaller, and Azure Speech SDK; do not generalize them. Preserve original font OFL text; MIT code does not make character art MIT.
- Identity and layers: follow [half-body](../DLC_ART_ASSET_SPEC.md), [body](../DLC_ART_ASSET_SPEC_BODY.md), [full-body](../DLC_ART_ASSET_SPEC_FULLBODY.md), and appearance contracts for authoritative identity, canvases, anchors, depth, and alpha edges. Hair, clothes, ornaments, makeup, and hands remain detachable; collages, baking, and misalignment cannot conceal defects.
- Anatomy and art: five fingers per hand and five toes per foot are existing [generation requirements](../tools/second_gen_body/chroma_mass_produce_v9.py), supported by [hand auditing](../domain/hand_asset_audit.py) and [evidence contracts](../domain/hand_asset_evidence.py). Landmark counts do not prove digit acceptance. Occlusion needs evidence and cannot conceal extra, missing, fused digits or seams.
- Appearance DLC: follow [appearance packs](OUTFIT-PACKS.md) for all thirty-one views, independent mixed slots, atomic installation, Save/Cancel, protected official packs, provenance, and runtime generation rejection. Preserve three makeup slots, safe regions, iris and oral exclusions, persistent intensity, and the shared runtime preview path.
- Autonomous wardrobe: retain manual locks, cooldowns, weather, and occasion policies. Generation and trend search require separate consent and bounded cost and storage. Quarantined candidates pass all audits before installation; limits never trigger deletion of user packs, and presentation tasks finish only after speech completes.
- Poses and themes: follow [pose packs](POSE-PACKS.md) and [theme packs](THEME-PACKS.md) for self-contained declarative archives, provenance hashes, dimensions, and compression limits. Reject executable code, unsafe paths, and external references; retain preview, activation, and deletion protection. Themes control semantic styling, not UI structure, and retain established contrast gates.
- Media: follow [media generation](MEDIA-PROVENANCE.md) and [UI provenance](UI-ASSET-PROVENANCE.md) for actual file hashes and generation sources. Preview and desktop share the compositor; videos use normal-speed OneCore, and old-generation screenshots cannot represent new assets.
- Platforms: follow [cross-platform contracts](CROSS-PLATFORM.md) and [preview packages](PREVIEW-PACKAGES.md) for full Windows functionality and explicit limits elsewhere. CI is not owner device acceptance; plaintext storage and disabled system protections cannot bypass restrictions.
- Merge and release: publication rules and owner decisions require PRs, green required checks, resolved discussions, and a locked head. Each merge needs explicit owner identification and a four-language squash title. Release needs separate authorization, immutable tags, exact assets, SBOM, hashes, attestations, signatures, and installer lifecycle evidence.

### Differences requiring reconciliation

[PR #109](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/pull/109) changed the historical JIT default to off after stability failures on a user machine. The current [launcher](../tools/jit_launcher.py) enables it only with `MOHAN_ENABLE_JIT=1`. Earlier migration documentation describing an enabled default does not establish current behavior.

Old version numbers, test counts, and unreleased statements in source documents are historical status. The old Qt metadata blocker was replaced by the architecture compatibility-layer policy. Earlier art-only delegation, old-face preservation, and top design were superseded by the current integration authorization, V4 appearance standard, and thin-strap cropped sports base. Routine autonomous work does not require stepwise questions; major matters and formal artwork integration retain confirmation.

Tachyon has an unresolved discrepancy: the supplied handoff states a one-percent read-error threshold, while this worktree explicitly passes fifteen percent in CI and Release and defaults to eighty percent in the CLI. These are inconsistent rules and settings, not verified equivalence; this index neither loosens nor rewrites thresholds. Older speech documentation says no Azure SDK installation, while current requirements include it; provider implementation and historical description must be distinguished. Reading documents does not certify current project-wide compliance.

## 日本語

### 範囲と効力

墨寒は個人開発の中大規模な趣味プロジェクトであり、制度と納品品質は大規模な商用ソフトウェアの基準に従う。持続可能な趣味のペースで保守し、人員や納期を理由に既定の基準を下げない。商用化や外部監査への対応を主張する際は、対応する証拠を必要とする。

本索引は変更前に確認する墨寒プロジェクト全体の規範を対象とする。原契約の代替でも、全規則への適合証明でもなく、過去のテストや公開記録を現在の状態とは扱わない。同じ範囲ではオーナーの後の明示的裁定を優先する。異なる範囲の規則は相互に解除できず、開発の許可によって製品内の安全確認は解除されない。

### 制度と検証の参照先

美術は正常な解剖、自然な姿勢、物理的な妥当性を基本とし、透視、重心、接触、遮蔽、光と影の整合性を保つ。手足の五指は解剖上の要件であり、すべての指を見せる要件ではない。数えやすさのために指を広げたり、承認済みの姿勢を変えたり、美しさを損なってはならない。自然な遮蔽だけを理由に描き直さない。

- 協働と品質：作業領域の引継ぎと [エージェント規則](../AGENTS.md) を読み、実際の作業ツリーと正式成果物を確認する。既存変更を保護し、プロジェクトを分離し、既存機能を維持する。件数、候補画像、一部テストを検収の代用にせず、[ガバナンス](../GOVERNANCE.md) に従い追跡可能に審査する。
- アーキテクチャ：[構造契約](../ARCHITECTURE.md) に従い五層の単一責任、公開された型付きインターフェース、依存注入、単一の調停主体を維持する。循環、逆依存、重複した政策やタイマー、機能間の非公開呼出しは禁止する。新モジュールの行数と下方限定の既存基準は従来テストで守り、免除を追加しない。
- 言語と開発：[言語移行](PYTHON-3.15-MIGRATION.md) と [静的設定](../ruff.toml) に従い指定 Python、明示的遅延インポート、適用可能な新構文を使う。関数内では遅延インポートしない。開発と作業手順に Python の禅を適用し、互換性、観測可能な失敗、実行可能な退避経路を保つ。
- 四言語：[公開規則](../PUBLISHING.md) に従い繁体字、簡体字、英語、日本語の内容と構造を揃える。公開文書、題名、PR 本文、公開説明、UI を含む。保存する安定値に翻訳ラベルを使わない。変更は [断片ディレクトリ](../changelog.d/) に追加し、公開履歴を直接書き換えない。
- テスト：[試験方針](TESTING.md) に従い開発時の高速試験、コミット前の全試験、必要な夜間試験を使う。影響対応が不明なら全試験への移行を受け入れる。直接実行入口と成功表示を備え、失敗を通すためにアサーションや基準を弱めない。自動試験、実機、梱包、公開は別々に立証する。
- 防護の実効性：[変異監査](release-evidence/gate-mutation-audit-2026-09-04.md) に従い壊れた防護で試験が失敗することを確認する。[エラー裁定](release-evidence/swallowed-error-audit-2026-09-04.md) に従い利用者データの問題を通知し、ツールは明示的に失敗させ、後処理の失敗で元のエラーを隠さない。
- 性能：[合成予算](PERFORMANCE-BUDGET.md) に従い実環境と独立標本を記録する。三件未満は理由付き記録のみとし、十分な標本で既定式を適用する。性能の主張は実測経路に限定し、ネイティブ高速化、JIT、標本品質、Python 等価性の証拠を混同しない。
- 権限：[安全政策](../SECURITY.md) に従いモデルではなくローカル政策が許可する。製品の黄色操作は確認、赤色は二重確認とし、恒久禁止操作は禁止を維持する。緊急停止、名前付き取消しの分離、許可リスト、スマートホームの高リスク分類を保つ。
- 機密とデータ：[旗艦仕様](../FLAGSHIP-SPEC.md) と安全政策に従い個人設定、会話、移行互換性を保つ。機密は承認済み OS 保存先だけを使い、コード、データベース、ログ、画像、配布物に入れない。更新署名秘密鍵はオーナーが管理し、本作業では読まない。
- 移行とバックアップ：構造契約に従い機械権限、装置状態、ローカルパスを除外する。機密移行は明示選択と強いパスワード暗号化を要し、検証失敗時は適用しない。重複スナップショット防止、旧版警告、変更前と日次のバックアップを維持する。
- 記憶：[記憶規則](MEMORY-RETRIEVAL-AND-PRUNING.md) に従いローカル索引、内容指紋による失効、復元可能な保存を行う。容量整理は条件に合う低重要度の会話のみとし、手動保存、重要記録、人物情報は削除しない。
- 感知とジェスチャー：[ジェスチャー仕様](GESTURE-INTERACTION.md) と構造契約に従い既定無効、保存された同意、上限、取消しを保つ。生画像は保存せず、機密骨格標本は別途暗号化する。期限切れ、低信頼、モデル不在では推測や送出をせず、他機能を維持する。
- 背景処理：[ワーカー規則](BACKGROUND-MANAGER-WORKERS.md) に従い読取専用観察、主スレッド調停、冷却、集中保護を維持する。ワーカーは音声、表情、ツール、権限を直接制御しない。
- 音声：[供給元契約](PLUGGABLE-SPEECH-PROVIDERS.md) に従い単一の口形同期と再生周期、女性ローカル代替、供給元分離を保つ。再生開始後の失敗で文全体を再生し直さない。オーナー指定のローカル音声は Yating、OneCore、通常速度を使う。
- ライセンス：[許可リスト](LICENSE-PURITY.md)、[禁止リスト](LICENSE-BLACKLIST.md)、[キャラクター権利](../ASSETS-LICENSE.md) を用いコード、重み、キャラクター資産を別々に確認する。既存例外は PySide6、PyInstaller、Azure Speech SDK の三件であり拡張しない。フォント OFL 原文を保持し、コードの MIT は美術を MIT にしない。
- 同一性とレイヤー：[半身](../DLC_ART_ASSET_SPEC.md)、[身体](../DLC_ART_ASSET_SPEC_BODY.md)、[全身](../DLC_ART_ASSET_SPEC_FULLBODY.md) と外観契約に従い権威ある同一性、画布、基準点、深度、透明縁を保つ。髪、衣装、飾り、化粧、手を分離可能にし、貼り合わせや焼込み、位置ずれで欠陥を隠さない。
- 解剖と美術：各手五指、各足五趾は既存の [生成条件](../tools/second_gen_body/chroma_mass_produce_v9.py) であり、[手の監査](../domain/hand_asset_audit.py) と [証拠契約](../domain/hand_asset_evidence.py) がある。骨格点数は指の検収証明ではない。遮蔽には証拠が必要で、増指、欠指、融合、継ぎ目を隠してはならない。
- 外観 DLC：[外観パック](OUTFIT-PACKS.md) に従い全三十一視点、独立スロット混用、原子的導入、保存と取消し、公式パック保護、由来、実行時世代拒否を保つ。化粧三スロット、安全領域、虹彩と口腔の除外、濃度保存、同一実行経路のプレビューを維持する。
- 自主着替え：手動ロック、冷却、天候と場面政策を維持する。生成と流行検索は別々の同意と費用・容量制限を要する。隔離候補は全監査後に導入し、上限到達で利用者パックを消さず、披露の発話が終わるまで完了としない。
- 姿勢とテーマ：[姿勢パック](POSE-PACKS.md) と [テーマパック](THEME-PACKS.md) に従い自己完結する宣言形式、由来ハッシュ、寸法、圧縮制限を使う。実行コード、危険パス、外部参照を拒否し、プレビュー、有効化、削除保護を保つ。テーマは意味的様式のみを扱い UI 構造を支配せず、既定コントラスト基準を満たす。
- メディア：[メディア世代](MEDIA-PROVENANCE.md) と [UI 素材由来](UI-ASSET-PROVENANCE.md) に従い実ファイルのハッシュと生成元を保存する。プレビューとデスクトップは同じ合成経路を使い、動画は通常速度 OneCore とし、旧世代画像で新素材を表さない。
- プラットフォーム：[クロスプラットフォーム](CROSS-PLATFORM.md) と [Preview パック](PREVIEW-PACKAGES.md) に従い Windows の全機能と他 OS の明示的制限を維持する。CI は作者の実機検収ではなく、平文保存やシステム保護無効化で制限を回避しない。
- マージと公開：公開規則とオーナー裁定に従い全変更を PR、必須検査成功、対話解決、head 固定の対象とする。各マージはオーナーの明示指定と四言語 squash 題名を要する。公開には別の許可、不変タグ、厳密な成果物、SBOM、ハッシュ、由来証明、署名、インストール周期の証拠を要する。

### 差異と未確認事項

実機の安定性問題を受け、[PR #109](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/pull/109) は JIT の既定値を無効に変更した。現行の [起動ツール](../tools/jit_launcher.py) は `MOHAN_ENABLE_JIT=1` の場合のみ有効化する。以前の移行文書にある既定で有効という記述は、現行動作の根拠にしない。

原文書の旧版番号、試験件数、未公開記述は過去の状態である。旧 Qt metadata 阻害条件は構造契約の互換層政策に置き換わった。旧来の美術専任制限、旧顔維持、上着形状は今回の統合許可、V4 外観基準、細肩紐の短丈スポーツ素体裁定に置き換わった。通常の自律作業で逐次質問は不要だが、重大事項と美術の正式接続は確認を維持する。

Tachyon には未解決の差異がある。引継ぎの読取エラー上限は一パーセントだが、この作業ツリーの CI と Release は十五パーセント、CLI 既定値は八十パーセントである。規則と設定の不一致であり、一致と主張せず、本索引で上限を緩和・変更しない。旧音声文書は Azure SDK 不要とするが、現在の依存一覧には SDK がある。供給元実装と歴史記述を区別する必要がある。文書を読むことは現在の全プロジェクト適合証明ではない。
