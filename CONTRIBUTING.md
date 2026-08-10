# 參與貢獻／参与贡献／Contributing／コントリビューション

## 繁體中文

### 開始之前

感謝你協助改善墨寒。開始重大變更前，請先閱讀[路線圖](ROADMAP.md)、[治理模式](GOVERNANCE.md)、[架構契約](ARCHITECTURE.md)及[安全政策](SECURITY.md)。大型功能應先提出 Feature Request 或 Discussion，以便在實作前議定權限邊界與相容性。

### 貢獻要求

1. 建立範圍集中的分支。
2. 不得將使用者資料、API 金鑰、錄音或生成的資料庫加入 commit。
3. 維持既有 SQLite 資料庫的向後相容性。
4. 每個新的行為預設值都必須提供使用者覆寫方式，或記錄不提供的理由。
5. 全新安裝不得預設加入特定職業專用的平台。
6. 行為變更必須新增或更新自動化測試。
7. 執行核心、UI、動畫、語音狀態及封裝後遷移測試。
8. 在 Pull Request 說明使用者可見變更及隱私／安全影響。
9. 解決所有審查對話，並等待全部必要的 GitHub 檢查通過。
10. 絕不繞過受保護的 `main`、對其強制推送，或重複使用已發布的標籤。

### 翻譯與持久資料

翻譯必須保留所有 placeholder，且不得僅為翻譯顯示文字而變更已持久化的資料庫值。

### 安全漏洞

不得在公開 Issue 或 Pull Request 揭露金鑰、權杖、私人對話、錄音、個人資料庫、未遮蔽截圖或尚未修補的漏洞。安全問題請依 [SECURITY.md](SECURITY.md) 私下回報。

## 简体中文

### 开始之前

感谢你帮助改进墨寒。开始重大变更前，请先阅读[路线图](ROADMAP.md)、[治理模式](GOVERNANCE.md)、[架构契约](ARCHITECTURE.md)及[安全政策](SECURITY.md)。大型功能应先提出 Feature Request 或 Discussion，以便在实现前议定权限边界与兼容性。

### 贡献要求

1. 创建范围集中的分支。
2. 不得将用户数据、API 密钥、录音或生成的数据库加入 commit。
3. 维持现有 SQLite 数据库的向后兼容性。
4. 每个新的行为默认值都必须提供用户覆盖方式，或记录不提供的理由。
5. 全新安装不得默认加入特定职业专用的平台。
6. 行为变更必须新增或更新自动化测试。
7. 执行核心、UI、动画、语音状态及封装后迁移测试。
8. 在 Pull Request 说明用户可见变更及隐私／安全影响。
9. 解决所有审查对话，并等待全部必要的 GitHub 检查通过。
10. 绝不绕过受保护的 `main`、对其强制推送，或重复使用已发布的标签。

### 翻译与持久数据

翻译必须保留所有 placeholder，且不得仅为翻译显示文字而变更已持久化的数据库值。

### 安全漏洞

不得在公开 Issue 或 Pull Request 泄露密钥、令牌、私人对话、录音、个人数据库、未遮蔽截图或尚未修补的漏洞。安全问题请依 [SECURITY.md](SECURITY.md) 私下报告。

## English

### Before you begin

Thank you for improving MoHan. Before starting a substantial change, read the [roadmap](ROADMAP.md), [governance model](GOVERNANCE.md), [architecture contract](ARCHITECTURE.md), and [security policy](SECURITY.md). Large features should begin with a Feature Request or Discussion so that permission boundaries and compatibility can be agreed before implementation.

### Contribution requirements

1. Create a focused branch.
2. Keep user data, API keys, recordings, and generated databases out of commits.
3. Preserve backward compatibility for existing SQLite databases.
4. Every new behavioral default must have a user override or a documented reason for not providing one.
5. Do not add profession-specific platforms to a fresh installation by default.
6. Add or update automated tests for behavior changes.
7. Run the core, UI, animation, speech-state, and packaged migration tests.
8. Describe user-visible changes and privacy or security effects in the Pull Request.
9. Resolve every review conversation and wait for all required GitHub checks to pass.
10. Never bypass protected `main`, force-push it, or reuse a published tag.

### Translation and persisted data

Translations must preserve every placeholder and must not change persisted database values merely to translate display text.

### Security vulnerabilities

Do not disclose keys, tokens, private conversations, recordings, personal databases, unredacted screenshots, or unpatched vulnerabilities in a public Issue or Pull Request. Report security concerns privately according to [SECURITY.md](SECURITY.md).

## 日本語

### 作業を始める前に

墨寒の改善にご協力いただき、ありがとうございます。大きな変更を始める前に、[ロードマップ](ROADMAP.md)、[ガバナンスモデル](GOVERNANCE.md)、[アーキテクチャ契約](ARCHITECTURE.md)、[セキュリティポリシー](SECURITY.md)をお読みください。大規模な機能は、実装前に権限境界と互換性について合意できるよう、Feature Request または Discussion から始めてください。

### コントリビューション要件

1. 対象を絞ったブランチを作成してください。
2. ユーザーデータ、API キー、録音、生成されたデータベースを commit に含めないでください。
3. 既存の SQLite データベースとの後方互換性を維持してください。
4. 新しい動作既定値には、ユーザーが上書きする方法、またはそれを提供しない理由の文書化が必要です。
5. 新規インストールへ特定職業向けプラットフォームを既定で追加しないでください。
6. 動作の変更には、自動テストを追加または更新してください。
7. コア、UI、アニメーション、音声状態、パッケージ後の移行テストを実行してください。
8. Pull Request に、ユーザーから見える変更とプライバシーまたはセキュリティへの影響を記載してください。
9. すべてのレビュー会話を解決し、必須の GitHub チェックがすべて成功するまで待ってください。
10. 保護された `main` を迂回したり、そこへ force-push したり、公開済みのタグを再利用したりしないでください。

### 翻訳と永続化データ

翻訳ではすべての placeholder を保持し、表示テキストを翻訳するためだけに永続化済みデータベース値を変更してはなりません。

### セキュリティ脆弱性

公開 Issue または Pull Request で、キー、トークン、非公開の会話、録音、個人データベース、未加工のスクリーンショット、未修正の脆弱性を開示しないでください。セキュリティ上の懸念は [SECURITY.md](SECURITY.md) に従って非公開で報告してください。
