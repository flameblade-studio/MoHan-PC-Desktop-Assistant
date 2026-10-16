# AI 協作入口／AI 协作入口／AI Workflow Router／AI 共同作業の入口

## 繁體中文

自有文件、提示詞、介面訊息與程式說明採用肯定句，直接寫明應採取的動作、必要條件與實際狀態。改寫時保留原有授權、驗證門檻、數值及完整因果；錯誤提示提供準確原因與可執行的下一步。機器識別碼、判斷用字串、模型條件資料、法律原文及封存輸出依原契約保存；以原句為鍵的翻譯目錄須與全部呼叫點同步更新並驗證。

本文件指向現有規則與目前工作，產品進度統一保存於所指向的權威紀錄。Playbook 的唯一版本宣告在 [AGENTS.md](../AGENTS.md)；使用者已核定開始採用。先確認目前工作樹、分支與變更，再讀該版本的 CHAT_INIT.md 和本次需要的章節。

- 程式與架構：讀 [ARCHITECTURE.md](../ARCHITECTURE.md)、相關模組及 tests，依既有驗證政策執行。
- 二代素體與外觀：讀 [分區產線契約](../tools/art_pipeline/REVIEWED_PARTITIONS.md) 與 [漢服原型設計依據](hanfu-design-authority.md)，再讀工作樹內 `scratchpad/v4-identity-rebuild-20260905/software-audit-20260907/body-v2-root-checkpoint.json` 的目前指派及相關工作欄位。該檔待補齊時，將狀態標為待確認，並以當前素材與證據建立進度依據。
- 發行與跨專案規則：讀工作區根目錄的 AGENTS.md、CODEX_PROJECT_HANDOFF.md，以及 [PUBLISHING.md](../PUBLISHING.md) 的既存政策。專案內舊發行交接紀錄作為歷史參照，目前產品狀態以當次證據確認。

派工與交接只保留：目標、必要輸入、已授權範圍、排除項目、唯一寫入負責者、完成條件、必要檢查、證據位置、待涵蓋項目、下一個已授權動作。依 2026-09-24 工作區政策，主代理預設使用 `gpt-6-sol`／max，子代理預設使用 `gpt-6-luna`／max；依獨立工作需要派 0–3 名子代理（上限不含主代理），不為填滿名額派工，子代理不得遞迴派工。保留 `astra-flash-orchestrator` skill 與 DeepSeek 路由作參考，暫停使用，直到擁有者另行恢復。主代理規劃工作包、明確範圍與排除項、指定唯一檔案寫入者、保留 dirty worktree、執行必要檢查並批次驗收。單純小修由主代理直接完成。

候選產生、外觀檢查、技術驗證、正式接入與發布分別記錄。主線直接核對代理的檔案與測試證據；每個 PASS 只代表實際覆蓋的範圍。外觀判定依擁有者目前授權與實際視覺審閱作成。已核准的下一步沿用現有許可，持續完成。

只選讀當前任務需要的 Playbook 章節：交接與閱讀成本看 AI_CONTEXT.md、SESSION_HANDOFF_TEMPLATE.md；驗收與重試看 DEBUG_VALIDATION.md。外部章節均使用 AGENTS.md 固定版本，已核對且維持原版的內容可在同一工作階段重用。代理依目前擁有者派工政策執行；`astra-flash-orchestrator` skill 與 DeepSeek 路由暫停使用，產品品質門檻沿用專案規範。

## 简体中文

自有文档、提示词、界面消息与代码说明采用肯定句，直接写明应采取的动作、必要条件与实际状态。改写时保留原有授权、验证门槛、数值及完整因果；错误提示提供准确原因与可执行的下一步。机器标识、判断用字符串、模型条件数据、法律原文及封存输出按原契约保存；以原句为键的翻译目录须与全部调用点同步更新并验证。

本文件指向现有规则与当前工作，产品进度统一保存在所指向的权威记录中。Playbook 的唯一版本声明在 [AGENTS.md](../AGENTS.md)；用户已批准开始采用。先确认当前工作树、分支与变更，再读该版本的 CHAT_INIT.md 和本次需要的章节。

- 代码与架构：读 [ARCHITECTURE.md](../ARCHITECTURE.md)、相关模块及 tests，按现有验证政策执行。
- 二代素体与外观：读 [分区产线契约](../tools/art_pipeline/REVIEWED_PARTITIONS.md) 与 [汉服原型设计依据](hanfu-design-authority.md)，再读工作树内 `scratchpad/v4-identity-rebuild-20260905/software-audit-20260907/body-v2-root-checkpoint.json` 的当前分工及相关工作字段。该文件待补齐时，将状态标为待确认，并以当前素材与证据建立进度依据。
- 发布与跨项目规则：读工作区根目录的 AGENTS.md、CODEX_PROJECT_HANDOFF.md，以及 [PUBLISHING.md](../PUBLISHING.md) 的现有政策。项目内旧发布交接记录作为历史参考，当前产品状态以本次证据确认。

分工与交接只保留：目标、必要输入、已授权范围、排除项、唯一写入负责人、完成条件、必要检查、证据位置、待覆盖项、下一个已授权动作。按 2026-09-24 工作区政策，主代理默认使用 `gpt-6-sol`／max，子代理默认使用 `gpt-6-luna`／max；按独立工作需要派 0–3 名子代理（上限不含主代理），不为填满名额派工，子代理不得递归分工。保留 `astra-flash-orchestrator` skill 和 DeepSeek 路由供参考，暂停使用，直到所有者另行恢复。主代理规划工作包、明确范围与排除项、指定唯一文件写入者、保留 dirty worktree、执行必要检查并批量验收。简单小修由主代理直接完成。

候选生成、外观检查、技术验证、正式接入与发布分别记录。主线直接核对代理的文件与测试证据；每个 PASS 只代表实际覆盖的范围。外观判断依所有者当前授权与实际视觉审查作出。已批准的下一步沿用现有许可，持续完成。

只选读当前任务需要的 Playbook 章节：交接与阅读成本看 AI_CONTEXT.md、SESSION_HANDOFF_TEMPLATE.md；验收与重试看 DEBUG_VALIDATION.md。外部章节均使用 AGENTS.md 固定版本，已核对且保持原版的内容可在同一工作阶段复用。代理按当前所有者分工政策执行；`astra-flash-orchestrator` skill 与 DeepSeek 路由暂停使用，产品质量门槛沿用项目规范。

## English

Use affirmative wording in authored documentation, prompts, UI messages, and code explanations. State the action, required conditions, and actual status directly. Preserve authorization, validation thresholds, numbers, and complete causal meaning; error messages provide an accurate reason and an actionable next step. Preserve machine identifiers, matching strings, model-conditioning data, legal originals, and archived output under their contracts. Update sentence-keyed translation catalogs together with every call site and verify their consistency.

This router points to existing rules and current work, with product status maintained in the linked authoritative records. [AGENTS.md](../AGENTS.md) owns the sole Playbook baseline; the owner has authorized adoption. Confirm the current worktree, branch and changes, then read that revision's CHAT_INIT.md and the sections needed for the task.

- Code and architecture: read [ARCHITECTURE.md](../ARCHITECTURE.md), relevant modules and tests, and follow the existing validation policy.
- Second-generation body and appearance: read the [partition pipeline contract](../tools/art_pipeline/REVIEWED_PARTITIONS.md) and [hanfu prototype design authority](hanfu-design-authority.md), then the current assignments and relevant work fields in the worktree's `scratchpad/v4-identity-rebuild-20260905/software-audit-20260907/body-v2-root-checkpoint.json`. While the file awaits restoration, mark status as awaiting confirmation and establish progress from current assets and evidence.
- Release and cross-project rules: read the workspace-root AGENTS.md and CODEX_PROJECT_HANDOFF.md, plus the persisted policies in [PUBLISHING.md](../PUBLISHING.md). Use old repository release handoffs as historical references and establish current product status from present evidence.

Delegation and handoff retain the goal, necessary inputs, authorized scope, exclusions, exclusive file writer, completion criteria, necessary checks, evidence pointers, areas awaiting coverage, and next authorized action. Follow the 2026-09-24 workspace policy: default to `gpt-6-sol` / max for the main coordinator and `gpt-6-luna` / max for child agents; assign zero to three children according to independent work needs, with the limit excluding the main coordinator, and never fill slots for their own sake. Children cannot delegate recursively. Keep the `astra-flash-orchestrator` skill and DeepSeek route as references, with use paused until the owner restores them. The main coordinator plans bounded work packages, states scope and exclusions, assigns one exclusive file writer, preserves dirty worktrees, runs necessary checks, and reviews evidence in a batch. The root handles trivial fixes directly.

Record candidate generation, visual review, technical validation, formal integration and release separately. The root checks agent files and test evidence directly; each PASS proves only its actual coverage. Visual decisions follow the owner's current authorization and actual visual review. Complete already approved next steps under the existing permission.

Read only task-relevant Playbook sections: AI_CONTEXT.md and SESSION_HANDOFF_TEMPLATE.md for handoff and retrieval cost; DEBUG_VALIDATION.md for acceptance and retries. All external sections use the revision pinned in AGENTS.md; verified content retained at the same revision can be reused within the session. Agent execution follows the current owner delegation policy; use of the `astra-flash-orchestrator` skill and DeepSeek route is paused. Product quality gates follow project rules.

## 日本語

自作の文書、プロンプト、画面メッセージ、コード説明は肯定形で、行動、必要条件、実際の状態を明示します。既存の承認範囲、検証基準、数値、因果関係を保持し、エラーには正確な原因と実行可能な次の手順を示します。機械識別子、照合文字列、モデル条件データ、法律原文、保存済み出力は各契約に従って保持します。原文をキーとする翻訳辞書は、すべての呼び出し箇所と同時に更新し、整合性を検証します。

本書は既存の規則と現在の作業への入口です。製品の進捗は参照先の正式記録で一元管理します。Playbook の唯一の基準版は [AGENTS.md](../AGENTS.md) に記載し、所有者は採用を承認済みです。現在の作業ツリー、ブランチ、変更を確認してから、その版の CHAT_INIT.md と必要な章だけを読みます。

- コードと設計：[ARCHITECTURE.md](../ARCHITECTURE.md)、関連モジュールと tests を読み、既存の検証方針に従います。
- 二代目素体と外観：[領域分割の契約](../tools/art_pipeline/REVIEWED_PARTITIONS.md) と [漢服の原型デザイン基準](hanfu-design-authority.md)、作業ツリーの `scratchpad/v4-identity-rebuild-20260905/software-audit-20260907/body-v2-root-checkpoint.json` にある現在の担当と対象作業を読みます。ファイルの復元待ちでは状態を確認待ちとし、現在の素材と証拠から進捗の根拠を整えます。
- リリースとプロジェクト横断規則：ワークスペース直下の AGENTS.md、CODEX_PROJECT_HANDOFF.md、および [PUBLISHING.md](../PUBLISHING.md) の既存方針を読みます。過去のリリース引き継ぎは履歴として参照し、現在の製品状態は今回の証拠で確認します。

委任と引き継ぎには、目標、必要な入力、承認済み範囲、対象外、排他的なファイル書き込み担当、完了条件、必要な確認、証拠の場所、検証待ちの範囲、次の承認済み操作を記載します。2026-09-24 のワークスペース方針に従い、主担当は既定で `gpt-6-sol`／max、子代理は既定で `gpt-6-luna`／max とします。独立した作業の必要に応じて子代理を 0～3 名割り当てます（上限に主担当を含みません）。枠を埋めるために割り当てず、子代理は再帰的に委任しません。`astra-flash-orchestrator` skill と DeepSeek 経路は参照用に保持し、所有者が再開するまで使用を停止します。主担当は作業単位を計画し、範囲と除外事項を明示し、ファイル書き込み担当を一名に限定し、dirty worktree を保持し、必要な確認を実行して証拠を一括で受け入れます。単純な修正は主担当が直接行います。

候補生成、外観確認、技術検証、正式統合、公開を分けて記録します。主担当は代理のファイルと試験証拠を直接確認し、各 PASS は実際の検証範囲だけを示します。外観の判断は所有者の現在の承認と実際の視覚確認に従います。承認済みの次の作業は既存の許可に基づいて完了します。

必要な Playbook の章だけを読みます。引き継ぎと読み取りコストは AI_CONTEXT.md と SESSION_HANDOFF_TEMPLATE.md、受け入れと再試行は DEBUG_VALIDATION.md を参照します。外部の章には AGENTS.md の固定版を使用し、検証済みで同じ版を維持した内容は同じ作業段階で再利用できます。代理の実行は現行の所有者方針に従い、`astra-flash-orchestrator` skill と DeepSeek 経路の使用は停止中です。製品品質の条件はプロジェクト規範に従います。
