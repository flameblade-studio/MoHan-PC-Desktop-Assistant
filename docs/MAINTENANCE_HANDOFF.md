# MoHan 專案交接／MoHan 项目交接／MoHan Project Handoff／MoHan プロジェクト引継ぎ

## 繁體中文

本檔是可攜、受版本控制的專案交接點；不得記錄憑證、密碼、API 金鑰、原始對話內容或不必要的私人本機路徑。程式碼、文件、發行證據與本檔均以 GitHub 為跨電腦的基準；目前修復工作位於 [PR #63](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/63)，分支為 fix/v4-readme-windows-ci，已發布的穩定版本為 v4.0.0。

- 此 PR 更新四語 README、Windows Qt 清理與發行後的互動修復。
- 控制台改為即時狀態卡，桌面墨寒是唯一可見、可拖移、可鍵盤對話的角色。
- 鏡頭在場、動作與揮手會觸發既有回應路徑；狀態卡不得阻斷主要互動。
- 合併前必須確認 Windows CI、三平台預覽、跨平台核心、安全、相依、CodeQL 與四語治理皆為綠燈。

實機驗收須確認沒有第二個角色、文字對話可用、保存只說一次、鏡頭在場／動作／揮手得到回應、休眠模式維持音色與順暢拖移，以及每個下拉選單皆可閱讀。若有差異，建立 GitHub issue 或後續 PR，而不只記在本機聊天。

1. 在其他電腦取得 main 與最新開放 PR，閱讀本檔及 PR 說明。
2. 依 GitHub Actions 的實際工作日誌確認失敗原因，進行最小直接修復並推送。
3. 所有必要檢查通過後合併 PR，驗證 main、標籤與發行版本的對應關係。
4. 將合併 SHA、驗證結果、未完成實機項目與下一步寫回本檔後提交。
5. 聽到「儲存進度」時，盤點狀態、更新交接、適度驗證、提交推送，並提供可貼回雲端 ChatGPT 專案的摘要。

## 简体中文

本文件是可携带、受版本控制的项目交接点；不得记录凭据、密码、API 密钥、原始对话内容或不必要的私人本机路径。代码、文档、发布证据与本文件均以 GitHub 为跨电脑的基准；当前修复工作位于 [PR #63](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/63)，分支为 fix/v4-readme-windows-ci，已发布的稳定版本为 v4.0.0。

- 此 PR 更新四语 README、Windows Qt 清理与发布后的互动修复。
- 控制台改为实时状态卡，桌面墨寒是唯一可见、可拖动、可键盘对话的角色。
- 镜头在场、动作与挥手会触发既有回应路径；状态卡不得阻断主要互动。
- 合并前必须确认 Windows CI、三平台预览、跨平台核心、安全、依赖、CodeQL 与四语治理皆为绿灯。

实机验收须确认没有第二个角色、文字对话可用、保存只说一次、镜头在场／动作／挥手得到回应、休眠模式维持音色与顺畅拖动，以及每个下拉菜单皆可阅读。若有差异，建立 GitHub issue 或后续 PR，而不只记在本机聊天。

1. 在其他电脑取得 main 与最新开放 PR，阅读本文件及 PR 说明。
2. 依 GitHub Actions 的实际工作日志确认失败原因，进行最小直接修复并推送。
3. 所有必要检查通过后合并 PR，验证 main、标签与发布版本的对应关系。
4. 将合并 SHA、验证结果、未完成实机项目与下一步写回本文件后提交。
5. 听到「储存进度」时，盘点状态、更新交接、适度验证、提交推送，并提供可贴回云端 ChatGPT 项目的摘要。

## English

This document is the portable, version-controlled project handoff; never record credentials, passwords, API keys, raw conversation content, or unnecessary private local paths. GitHub is the cross-computer baseline for code, documentation, release evidence, and this document; current repair work is in [PR #63](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/63) on fix/v4-readme-windows-ci, and the published stable release is v4.0.0.

- This PR refreshes four-language READMEs, Windows Qt cleanup, and post-release interaction repairs.
- The console is a live status card; desktop MoHan is the one visible, draggable, keyboard-chat companion.
- Camera presence, activity, and waving use the established response path; the status card must not block primary interaction.
- Before merge, Windows CI, three-platform preview, cross-platform core, security, dependencies, CodeQL, and four-language governance must all be green.

For device acceptance, confirm no second character, working text chat, one save acknowledgement, responses to camera presence/activity/waving, a consistent voice with smooth dragging in sleep mode, and readable dropdowns. If a discrepancy remains, open a GitHub issue or follow-up PR rather than recording it only in a local chat.

1. On another computer, obtain main and the newest open PR, then read this document and the PR description.
2. Use the exact GitHub Actions job log to identify a failure, make the smallest direct repair, and push it.
3. When all required checks pass, merge the PR and verify the relationship among main, tag, and published release.
4. Write the merge SHA, verification results, unfinished device items, and next step back into this document, then commit it.
5. When the owner says "儲存進度", inspect the state, update this handoff, verify proportionately, commit and push, then provide a summary suitable for the cloud ChatGPT project.

## 日本語

この文書は持ち運び可能でバージョン管理されたプロジェクト引継ぎです。認証情報、パスワード、API キー、生の会話内容、不要な私的ローカルパスは記録しません。コード、文書、公開証跡、この文書のクロスコンピュータ基準は GitHub です。現在の修正は [PR #63](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/63) の fix/v4-readme-windows-ci にあり、公開済み安定版は v4.0.0 です。

- この PR は四言語 README、Windows Qt のクリーンアップ、公開後の対話修正を更新します。
- コントロールセンターはライブ状態カードであり、デスクトップの墨寒だけが表示、ドラッグ、キーボード会話できる伴侶です。
- カメラの在席、動き、手を振る操作は既存の応答経路を使い、状態カードは主対話を妨げてはいけません。
- マージ前に Windows CI、三プラットフォームのプレビュー、クロスプラットフォームコア、セキュリティ、依存関係、CodeQL、四言語ガバナンスがすべて緑でなければなりません。

実機受け入れでは二人目のキャラクターがなく、文字会話が動き、保存時の発話が一度だけで、カメラの在席／動き／手振りに応答し、休眠モードで音色と滑らかなドラッグを保ち、すべてのドロップダウンが読めることを確認します。差異が残る場合は、ローカルチャットだけに記録せず GitHub issue または後続 PR を作成します。

1. 別のコンピュータでは main と最新のオープン PR を取得し、この文書と PR 説明を読みます。
2. 正確な GitHub Actions ジョブログで失敗を確認し、最小の直接修正を行ってプッシュします。
3. 必要なチェックがすべて通ったら PR をマージし、main、タグ、公開版の対応を確認します。
4. マージ SHA、検証結果、未完了の実機項目、次の手順をこの文書へ戻してコミットします。
5. 所有者が「儲存進度」と言ったら、状態を確認し、この引継ぎを更新し、適切に検証してコミットとプッシュを行い、クラウド ChatGPT プロジェクト向けの要約を提供します。
