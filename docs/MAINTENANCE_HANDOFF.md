# MoHan 專案交接／MoHan 项目交接／MoHan Project Handoff／MoHan プロジェクト引継ぎ

## 繁體中文

本檔是可攜、受版本控制的專案交接點；不得記錄憑證、密碼、API 金鑰、原始對話內容或不必要的私人本機路徑。程式碼、文件、發行證據與本檔均以 [Flameblade Studio 組織儲存庫](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant) 為跨電腦基準；目前 v4.4.2 候選修復位於 `fix/release-please-release-trigger`，已發布穩定版本為 v4.4.1。

- v4.4.2 修復半身／全身分層說話破圖、無聲與嘴型停止，並限制渲染快取以排除「記憶體已滿」。
- 鏡頭活動與自然揮手會觸發四語主動回應；全身路徑已接入手勢節拍、手部狀態與安全的小幅身體動勢。
- GPT Image 2 雲端製衣、官方 DLC、使用者 DLC 可並存；使用者手動換裝預設鎖定 6 小時，可調 0–720 小時，▲／▼ 於邊界皆可用。
- 發版前必須確認完整回歸、Windows CI、三平台預覽、跨平台核心、安全、相依、CodeQL 與四語治理皆為綠燈。

實機驗收須確認半身／全身說話均無破圖且有聲有嘴型、沒有第二個角色、文字對話可用、鏡頭活動／揮手得到明顯回應、自主選裝與手動鎖定能共存，且鎖定時數的 ▲／▼ 在最小值與最大值都可操作。若有差異，建立 GitHub issue 或後續 PR，而不只記在本機聊天。

1. 在其他電腦取得 main 與最新開放 PR，閱讀本檔及 PR 說明。
2. 依 GitHub Actions 的實際工作日誌確認失敗原因，進行最小直接修復並推送。
3. 所有必要檢查通過後合併 PR，驗證 main、標籤與發行版本的對應關係。
4. 將合併 SHA、驗證結果、未完成實機項目與下一步寫回本檔後提交。
5. 聽到「儲存進度」時，盤點狀態、更新交接、適度驗證、提交推送，並提供可貼回雲端 ChatGPT 專案的摘要。

## 简体中文

本文件是可携带、受版本控制的项目交接点；不得记录凭据、密码、API 密钥、原始对话内容或不必要的私人本机路径。代码、文档、发布证据与本文件均以 [Flameblade Studio 组织仓库](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant) 为跨电脑基准；当前 v4.4.2 候选修复位于 `fix/release-please-release-trigger`，已发布稳定版本为 v4.4.1。

- v4.4.2 修复半身／全身分层说话破图、无声与嘴型停止，并限制渲染缓存以排除“内存已满”。
- 镜头活动与自然挥手会触发四语主动回应；全身路径已接入手势节拍、手部状态与安全的小幅身体动势。
- GPT Image 2 云端制衣、官方 DLC、用户 DLC 可以共存；手动换装默认锁定 6 小时，可调 0–720 小时，▲／▼ 在边界均可用。
- 发布前必须确认完整回归、Windows CI、三平台预览、跨平台核心、安全、依赖、CodeQL 与四语治理皆为绿灯。

实机验收须确认半身／全身说话均无破图且有声有嘴型、没有第二个角色、文字对话可用、镜头活动／挥手得到明显回应、自主选装与手动锁定能共存，且锁定时数的 ▲／▼ 在最小值与最大值都可操作。若有差异，建立 GitHub issue 或后续 PR，而不只记在本机聊天。

1. 在其他电脑取得 main 与最新开放 PR，阅读本文件及 PR 说明。
2. 依 GitHub Actions 的实际工作日志确认失败原因，进行最小直接修复并推送。
3. 所有必要检查通过后合并 PR，验证 main、标签与发布版本的对应关系。
4. 将合并 SHA、验证结果、未完成实机项目与下一步写回本文件后提交。
5. 听到「储存进度」时，盘点状态、更新交接、适度验证、提交推送，并提供可贴回云端 ChatGPT 项目的摘要。

## English

This document is the portable, version-controlled project handoff; never record credentials, passwords, API keys, raw conversation content, or unnecessary private local paths. The [Flameblade Studio organization repository](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant) is the cross-computer baseline. The v4.4.2 candidate is on `fix/release-please-release-trigger`; the published stable release is v4.4.1.

- v4.4.2 repairs torn half/full-body layered speech, silent playback and stopped mouth motion, and bounds render caches to prevent “memory full”.
- Camera activity and natural waves receive proactive four-language responses; hand state, gesture beats, and conservative visible body motion reach full-body rendering.
- GPT Image 2 cloud outfits coexist with official and user DLC. Manual selection locks autonomous changes for a configurable 0–720 hours (default 6); ▲ and ▼ remain usable at both boundaries.
- Before publication, the full regression, Windows CI, three-platform preview, cross-platform core, security, dependencies, CodeQL, and four-language governance must all be green.

For device acceptance, confirm both framings speak without corruption and with audio/lip motion, no second character appears, text chat works, camera activity/waving receives visible responses, autonomous and manual wardrobes coexist, and both lock-duration arrows work at minimum and maximum. If a discrepancy remains, open a GitHub issue or follow-up PR rather than recording it only in a local chat.

1. On another computer, obtain main and the newest open PR, then read this document and the PR description.
2. Use the exact GitHub Actions job log to identify a failure, make the smallest direct repair, and push it.
3. When all required checks pass, merge the PR and verify the relationship among main, tag, and published release.
4. Write the merge SHA, verification results, unfinished device items, and next step back into this document, then commit it.
5. When the owner says "儲存進度", inspect the state, update this handoff, verify proportionately, commit and push, then provide a summary suitable for the cloud ChatGPT project.

## 日本語

この文書は持ち運び可能でバージョン管理されたプロジェクト引継ぎです。認証情報、パスワード、API キー、生の会話内容、不要な私的ローカルパスは記録しません。[Flameblade Studio 組織リポジトリ](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant) がクロスコンピュータ基準です。v4.4.2 候補は `fix/release-please-release-trigger` にあり、公開済み安定版は v4.4.1 です。

- v4.4.2 は半身／全身レイヤー発話の崩れ、無音、口パク停止を修正し、「メモリ不足」を防ぐため描画キャッシュを制限します。
- カメラ上の活動と自然な手振りへ四言語で能動的に反応し、手状態、ジェスチャービート、安全な小幅身体動勢を全身描画へ接続します。
- GPT Image 2 クラウド衣装、公式 DLC、ユーザー DLC は共存します。手動変更ロックは既定 6 時間、0–720 時間で、▲／▼ は上下限でも使用できます。
- 公開前に完全回帰、Windows CI、三プラットフォーム Preview、クロスプラットフォームコア、セキュリティ、依存関係、CodeQL、四言語ガバナンスがすべて緑でなければなりません。

実機受け入れでは半身／全身発話に崩れがなく音声と口パクが動き、二人目のキャラクターがなく、文字会話が動き、カメラ活動／手振りへ明確に反応し、自主選装と手動ロックが共存し、ロック時間の ▲／▼ が最小・最大でも操作できることを確認します。差異が残る場合は、ローカルチャットだけに記録せず GitHub issue または後続 PR を作成します。

1. 別のコンピュータでは main と最新のオープン PR を取得し、この文書と PR 説明を読みます。
2. 正確な GitHub Actions ジョブログで失敗を確認し、最小の直接修正を行ってプッシュします。
3. 必要なチェックがすべて通ったら PR をマージし、main、タグ、公開版の対応を確認します。
4. マージ SHA、検証結果、未完了の実機項目、次の手順をこの文書へ戻してコミットします。
5. 所有者が「儲存進度」と言ったら、状態を確認し、この引継ぎを更新し、適切に検証してコミットとプッシュを行い、クラウド ChatGPT プロジェクト向けの要約を提供します。
