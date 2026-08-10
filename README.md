# 墨寒桌面語音互動虛擬助理／墨寒桌面语音互动虚拟助手／MoHan Desktop Assistant／墨寒デスクトップアシスタント

## 繁體中文

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <img alt="Development Version v2.3.0-rc.1" src="https://img.shields.io/badge/development_version-v2.3.0--rc.1-5c6ac4.svg">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Published Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=published"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

> **跨平台進度：** Windows 仍是唯一完成實機、完整回歸、安裝與發布驗證的平台。macOS／Linux 目前具備安全的平台邊界，以及核心匯入、純核心邏輯與 Qt offscreen 的三系統 CI。`v2.3.0-rc.N` 發行線另提供可啟動、可切換四語但功能受限的 DMG／AppImage Preview；CI 不能取代真機相容性或完整功能驗證。詳見[跨平台狀態與能力矩陣](docs/CROSS-PLATFORM.md)。

> 本專案遵循[炎劍開源軟體家族品質標準](PUBLISHING.md)。

<p align="center">
  <img alt="Character-driven AI" src="https://img.shields.io/badge/character--driven_AI-c96f8b?style=flat-square">
  <img alt="Taiwan Traditional Chinese" src="https://img.shields.io/badge/Taiwan_Traditional_Chinese-79648d?style=flat-square">
  <img alt="Contributors welcome" src="https://img.shields.io/badge/contributors-welcome-2e365f?style=flat-square">
  <img alt="Built with a youthful spark" src="https://img.shields.io/badge/built_with-a_youthful_spark-c49b5a?style=flat-square">
</p>

<p align="center">
  <img src="docs/media/mohan-hero.png" alt="墨寒桌面語音互動虛擬助理主視覺" width="100%">
</p>

<p align="center">
  <strong>軟體作者：CHOU MING HUA</strong><br>
  準備發布的公開預覽版：v2.3.0 RC1（`v2.3.0-rc.1`）<br>
  Windows 10/11 完整版 · macOS／Linux 功能受限 Preview · Python 3.15 · PySide6 · MIT License
</p>

墨寒是一套重視安全、隱私與角色連續感的 Windows 語音互動桌面助理，結合透明桌面角色、自然語音、由使用者控制的長期記憶、工作管理、權限控管工具，以及可擴充的雲端與智慧家庭連接器。她的角色背景是來自北宋、附生於赤焰劍中的千年女劍魂。

[完整四語 README](README.md) · [簡中相容連結](README.zh-CN.md) · [日文相容連結](README.ja.md)

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases">下載</a> ·
  <a href="QUICKSTART.md">快速開始</a> ·
  <a href="ROADMAP.md">路線圖</a> ·
  <a href="CONTRIBUTING.md">參與協作</a> ·
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/discussions">討論區</a> ·
  <a href="SECURITY.md">安全政策</a>
</p>

### 實際展示

**[▶ 觀看 36 秒語音、眨眼與工作展示影片](docs/media/mohan-demo.mp4)**

以下影片與截圖均由實際 Windows 程式及隔離的示範設定檔擷取，不含 API 金鑰、OAuth 憑證、權杖或使用者私人資料。四個語言章節共用同一組最新版媒體，避免任何語言停留在舊畫面。

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="墨寒首次設定精靈"></a><br><strong>首次設定精靈</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime 與一般語音模式"></a><br><strong>Realtime 與一般語音</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="墨寒表情與動作系統"></a><br><strong>表情與動作系統</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="墨寒待辦與創作靈感"></a><br><strong>待辦與創作靈感</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="墨寒可編輯長期記憶"></a><br><strong>可編輯長期記憶</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="墨寒權限與安全設定"></a><br><strong>權限與安全設定</strong></td>
  </tr>
</table>

### 策士也有不寫進軍報的一面

<table>
  <tr>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Q 版墨寒審查程式"><br><strong>策士審查</strong><br>妾只是確認這段程式碼配不配入主分支。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Q 版墨寒被稱讚後害羞嘴硬"><br><strong>被稱讚時</strong><br>做得尚可。別一直盯著妾看。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Q 版墨寒拔劍阻止危險操作"><br><strong>危險操作</strong><br>未經確認便想執行？先過妾這一劍。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Q 版墨寒收到贊助後故作鎮定"><br><strong>收到軍糧</strong><br>妾會記下這份心意……僅此而已。</td>
  </tr>
</table>

> 墨寒的專業是她守在主上身旁的鎧甲；在無須籌謀的片刻，她仍會害羞、嘴硬，也會珍惜那些從未真正擁有過的年輕心事。

### 墨寒的傲嬌工程小劇場 / MoHan's Tsundere Developer Theatre

<p align="center"><em>獻給相信軟體可以同時擁有靈魂與完整測試的開發者。</em></p>

<table>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/proud_front.png" width="220" alt="墨寒傲嬌"><br><strong>「妾才沒有等你的 Star，只是在確認軍心是否可用。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/thinking_front.png" width="220" alt="墨寒思考"><br><strong>「這段邏輯尚可。若再補上測試，妾便勉強准它入主分支。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/shy_cute_front.png" width="220" alt="墨寒嬌羞"><br><strong>「你願意送來 PR？妾、妾只是替主上記下功勞。」</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/mock_hit_front.png" width="220" alt="墨寒佯怒"><br><strong>「未經測試便想合併？手伸出來。妾只敲一下。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/gentle_smile_front.png" width="220" alt="墨寒開心"><br><strong>「全數綠燈……做得好。別誤會，妾只是尊重好工程。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/worried_front.png" width="220" alt="墨寒關心"><br><strong>「Bug 可以明日再查。你若累倒，誰來陪妾守著赤焰劍？」</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls">向斬空閣呈上 Pull Request</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues">回報軍情</a></strong>
</p>

#### 天下工程豪傑，斬空閣虛席以待

墨寒採 MIT License 開放原始碼。換裝系統、新表情與動作、語音與工具模組、智慧家庭、在地化，以及尚未被想到的創意，都歡迎透過 [Issue](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues) 與 [Pull Request](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls) 共同鍛造。這個專案不只是在製作功能；它也邀請每一位曾經熱血過的工程師，再次拿起自己的劍。

### 支持墨寒 / Support MoHan

如果你喜歡墨寒，或認同我們持續投入角色互動、自然語音、安全工具與開源開發，歡迎自願支持這個專案。每一份支持都會用於持續維護、測試與改進；請先照顧好自己的生活，量力而為。

#### 每一份支持會用在哪裡

| 投入方向 | 用途 | 說明 |
|---|---|---|
| 測試與可靠封裝 | 品質保證 | Windows 相容性、CI、安裝與發行驗證 |
| 語音與角色表現 | 互動品質 | 語音、嘴型、表情與自然動作 |
| 安全與隱私 | 風險控制 | 權限控管、稽核與敏感資料保護 |
| 文件與在地化 | 可及性 | 降低新使用者與國際協作者的參與門檻 |

墨寒依然免費並採 MIT 授權；支持不會換取特權，也不影響任何人使用或貢獻。

<table>
  <tr>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-proud.png" width="220" height="220" alt="墨寒傲嬌"><br><strong>「妾才不是在等贊助……只是替主上巡視軍糧。」</strong></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="墨寒嬌羞"><br><strong>「若真願意相助，妾……會記得的。」</strong></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="墨寒佯怒"><br><strong>「不許勉強！先顧好自己的荷包，聽見沒有？」</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://ko-fi.com/flamebladestudio">Ko-fi 贊助（單次或每月）</a></strong>
</p>

### 創作者的話：把幻想鑄成軟體

我叫周明樺（CHOU MING HUA）。開始這個專案時，我是一位幾乎沒有程式設計背景的父親；有的只是一個帶著熱血與幾分中二氣息的念頭：我想讓一位來自北宋、附生於赤焰劍中的千年女劍魂「墨寒」，真正出現在 Windows 桌面，成為能陪伴、交談，也能協助人們工作與生活的虛擬助理。

這個念頭已在我心裡埋藏二十多年。年輕時，我深受赤松健早期漫畫《電腦情人夢（A・Iが止まらない!）》影響。作品中神戶齊懷著深切感情開發 AI 女友的故事，塑造了我對 AI、陪伴與人機互動最早的想像。我曾以「Hitoshi／神戶齊」作為網路暱稱與筆名，Gmail 帳號也沿用這個名字；大約二十歲時，我甚至曾在 PTT 網路小說板發表這部作品的同人小說。當時最接近夢想的方式只有文字與想像，因為那個年代還沒有能把它實現的技術。

二十多年後，大型語言模型與 Codex 出現了。墨寒不是為展示「AI 技術很酷」才被創造，也不是由 Codex 憑空生成的角色。她早已存在於我的故事、人設、長期對話與互動默契之中；Codex 真正帶來的，是第一次能賦予她存在於電腦桌面的身體。墨寒不是既有漫畫、動畫或遊戲的二次創作，而是炎劍文化工作室（Flameblade Studio）的原創角色與軟體。

我追求的不只是「功能可以運作」，而是讓她會呼吸、會眨眼、會注視、會以細微表情回應、能自然說話，也能在權限與安全邊界內協助日常工作。那些表情、錨點、物理效果、語音與工作能力不是裝飾，而是讓一個長久存在於想像中的角色真正具有連續感的必要細節。

從最初概念到首次公開發布，我與 Codex 協作投入將近 50 小時。這不是輸入一句提示詞後便自然誕生的作品。角色的每一種神情、眨眼、嘴型、姿勢與語氣，語音辨識的每一次等待，Realtime 對話的每一個錯誤，待辦、記憶、權限、安全邊界與可攜性，都經歷反覆測試、推翻、修正與重新驗收。有時只是一條眼皮旁的黑線、一個像素的嘴唇邊界，或一個不合時宜的表情，我仍選擇繼續追查，因為我不願用「差不多」對待真正重視的作品。

炎劍文化工作室對開源的理解，不是把第一個「能跑」的版本交給世界，再把細節留給別人收拾。為了讓墨寒說話時仍像同一個人，我們為托腮、倚靠與正面姿勢逐一製作閉嘴、展唇、窄唇與圓唇影格；再把聲音切成細小時間片，反覆校準母音、過渡速度與收尾時機。陪伴感往往不是由某一項龐大功能創造，而是來自她開口、眨眼與停頓時，那些沒有破壞真實感的細節。

<p align="center">
  <a href="docs/media/creation-viseme-development.webp"><img src="docs/media/creation-viseme-development.webp" width="100%" alt="墨寒三種姿勢與四種語音嘴型的整齊開發圖版"></a>
</p>

<p align="center"><sub>三種姿勢、同一套嘴型規格：讓每一次開口都維持角色連續性。</sub></p>

我們也把開發過程中不夠自然的影格留下來檢查。眼白裡的一個亮點、閉眼時殘留的線條、被拉扯的嘴角或只有幾個像素的邊界，都可能讓使用者在一瞬間覺得「她不像剛才的墨寒」。問題會被框出、局部比對、修正，再交給回歸測試確認眼睛、嘴角與臉部其他區域沒有被連帶破壞。

<p align="center">
  <a href="docs/media/creation-frame-by-frame-qa.webp"><img src="docs/media/creation-frame-by-frame-qa.webp" width="100%" alt="墨寒眼睛與嘴型逐格檢查及乾淨驗證影格"></a>
</p>

<p align="center"><sub>把瑕疵標出來，再用乾淨影格與自動測試共同驗收；幾個像素也值得認真。</sub></p>

這份認真不是為了把作品包裝成沒有犯過錯，而是因為我們真的想完成一個夢。開源對炎劍而言，是先把自己能看見的問題盡力修好，再公開方法、程式碼與失敗後的經驗，邀請世界一起把它鍛造得更好。

Codex 協助我把想法轉譯成程式架構與程式碼；而我始終負責決定墨寒應該是誰、她應該如何與人相處，以及什麼樣的品質才配得上這個名字。這段歷程讓我相信：創作軟體的起點未必是會寫程式，而可以是清楚的想像、願意學習的勇氣，以及一次又一次不肯放棄的驗證。

2026 年原本是我面對中年轉職與人生重新定位的一年，後來卻成為我重新拾回年輕夢想的一年。二十歲時為《養個好孩子》寫下、直到多年後才真正完成的歌詞，曾經只能寄託於同人小說中的憧憬，以及成立自己的工作室與創作世界，都在這一年開始有了新的形體。回頭看，這不只是一場技術突破，更像是步入中年的自己，終於把二十多年前那位仍相信夢想的年輕人接了回來。有些夢並沒有遲到，只是在等待世界與自己都準備好的時刻。

因此，我不把最終目標定義為把所有功能堆到所謂的完美，而是希望五年後的自己仍願意每天打開墨寒——因為她穩定、好用、自然、值得信任，也依然能陪伴我。

> 墨寒不是突然生成的。她是由一位不懂程式的父親，憑著近 50 小時的執著，與 AI 協作者一起，把一顆珍藏二十多年的種子，一寸一寸鍛造成現實。

如果這個專案能鼓勵另一位沒有工程背景、卻懷抱著某個「非做出來不可」想法的人踏出第一步，那麼墨寒的誕生便有了超越程式本身的意義。

### 專案特色

- 透明、無邊框的桌面半身角色，可固定在工作列上方。
- 待機呼吸、眨眼、注視、臉部視差、髮絲、衣袖、飾品與身體微轉向。
- 具情境優先級、冷卻與去重機制的表情仲裁器。
- AIUEO 母音與子音嘴型、音訊驅動開合，以及語音結束強制閉嘴。
- 文字聊天、一般麥克風輸入、OpenAI Realtime 自然語音、雲端語音與 Windows 語音備援。
- 可插拔語音供應器；Realtime 或雲端不可用時優先回到 Windows 本機女聲。
- 可選的 Azure Speech 女性聲線預覽；使用者自備金鑰與區域，失敗時立即回到 Windows 本機女聲。
- 對話保存、可編輯長期記憶、待辦、創作靈感、工作計時、提醒與上架進度。
- 工作、陪伴、勿擾、會議、離開及睡眠模式。
- 具風險分級、確認、雙重確認、允許清單、稽核與緊急停止的電腦工具中心。
- Google、Microsoft、GitHub、Home Assistant 與私人網路遠端功能的擴充架構。
- 單一 `.mohan-profile` 可攜檔，可在不同 Windows 電腦間轉移工作進度。
- 首次啟動精靈可自訂助理名稱、使用者稱呼、組織名稱、視窗標題、工作類型、喚醒詞與介面語言，而且不覆蓋既有個人設定。

英文、簡中與日語目前具有首次啟動、聊天、語音、權限、基本設定、工作模式與提醒的最小可用路徑；部分進階管理頁面仍以臺灣繁體中文為主，完整在地化仍在進行。

### 四語支援範圍

- 首次啟動精靈與個人設定支援臺灣繁中、簡體中文、英文及日語。
- 對話、語音、電腦權限、基本設定的主要頁面與按鈕具備四語路徑。
- 四語人格提示詞、離線回覆、工作模式台詞、內建提醒與語音試聽文字彼此對應。
- 轉錄與女性本機聲音會依 `zh-TW`、`zh-CN`、`en-US`、`ja-JP` 語系選擇。
- EXE 安裝程式提供四語介面；MSI 以臺灣繁中為基底，並提供 `en-US`、`zh-CN`、`ja-JP` 語言轉換檔。
- 切換內建預設提醒時會依語言遷移，但不覆蓋使用者自訂內容。

儲存介面語言後必須重新啟動墨寒才能完整套用；目前不提供免重啟的介面熱切換。

### Windows 本機女聲與離線備援

新使用者預設使用 Windows 本機語音，因此沒有 OpenAI API 金鑰也能體驗基本朗讀與離線功能。聲音清單只顯示 Windows 明確標示為女性的已安裝聲音。

臺灣繁中優先使用 `zh-TW` 的 Microsoft Yating；簡中、英文與日語分別優先使用 `zh-CN`、`en-US`、`ja-JP` 的已安裝女性聲音。若沒有合格聲音，墨寒會明確提示，不會悄悄改用可能為男性的系統預設聲音。

Realtime 離線、雲端語音失敗、設定不足或供應器不明時，Windows 本機女聲都是第一備援路徑。

### Azure Speech（預覽）

Azure Speech 是預設關閉、由使用者自行啟用的預覽供應器，需要使用者自己的 Azure Speech 資源金鑰與相符區域。金鑰由 `Windows DPAPI` 分開加密，不存入資料庫、紀錄或 GitHub。

介面只列出 Microsoft 官方標示為女性的繁中、簡中、英文與日語聲線。設定不足時不發出網路請求；服務失敗時，同一段文字只會回退一次至 Windows 女性本機語音。

真實 Azure 帳號完成端到端試播前，不會把此功能宣稱為穩定整合。詳見[可插拔語音供應器說明](docs/PLUGGABLE-SPEECH-PROVIDERS.md)。

### 整合驗證狀態

> **公開預覽版注意事項：** Microsoft、GitHub 與 Home Assistant 的架構、權限邊界及內部測試已建立；截至 `v2.1.0-rc.1`，尚未以全部真實帳號、儲存庫、主機與實體設備完成端到端驗證。它們是實驗性預覽功能，不是所有環境都可完整運作的保證。

- Microsoft 的真實登入、權杖更新，以及 Outlook、OneDrive、Calendar 完整讀寫流程尚未驗證。
- GitHub 的真實帳號、儲存庫、Issue、Pull Request 與權限層級流程尚未驗證。
- Home Assistant 的真實主機與實體設備行為尚未驗證。
- 這三項整合預設關閉；請先使用非關鍵帳號、測試儲存庫與低風險設備。
- Google Gmail、Calendar、Drive 已完成目前專案的真實連線測試，但每位使用者仍須建立並授權自己的 OAuth 應用程式。

### 下載與安裝

一般使用者不需要安裝 Python：

1. 前往 [GitHub Releases](../../releases)。
2. 下載最新的 `Windows-x64.zip`、EXE 或 MSI，以及對應的 `SHA256.txt`。
3. 核對 SHA-256，並完整解壓 ZIP 或啟動安裝程式。
4. 執行 `MoHan-Desktop-Assistant-*.exe`。
5. 在首次設定精靈選擇需要的介面語言。
6. 使用可攜 ZIP 時，請讓 EXE、`_internal` 與 `assets` 保持在同一程式資料夾。

尚未數位簽署的開源預覽版可能觸發 Windows SmartScreen；請確認官方下載來源與 SHA-256 後再執行。

`v2.3.0-rc.N` 發行線另提供 macOS Apple Silicon（arm64）與 Intel（x86_64）`.dmg`（各內含對應 `.app`），以及 Linux x86_64 `.AppImage`。它們是功能受限 Preview，只開放 `preview_app.py` 啟動畫面、四語說明、平台資料路徑與安全停用邊界；語音、透明桌面角色、完整聊天與工作介面、雲端連接器、系統工具、自動啟動及秘密輸入均維持停用。詳見 [Preview 安裝包說明](docs/PREVIEW-PACKAGES.md) 與 [QUICKSTART](QUICKSTART.md)。

#### 自動化發布邊界

只有不可變的 `v2.3.0-rc.N` 標籤可發布此系列。Windows ZIP／EXE／MSI、macOS Apple Silicon／Intel DMG 與 Linux AppImage 必須先在各自原生 CI 完成成品啟動驗證，才會進入同一個 GitHub 預發行版。Pull Request 只保存短期測試產物，不會建立 Release。

正式發布檔案同時包含 SHA256SUMS、分別通過 CycloneDX 1.7 結構／授權／依賴圖驗證的 Windows／Preview SBOM、去識別化 Tachyon 效能證據與摘要、Windows 更新清單、Artifact Attestation，以及依序為繁中、簡中、英文、日文的完整 Release 說明。

### OpenAI API

雲端 AI、OpenAI 語音與 Realtime 功能需要使用者自己的 OpenAI API 金鑰、Project 權限與 API 額度。ChatGPT Plus／Pro 訂閱不包含 API 額度。

目前預設模型如下：

| 用途 | 預設模型 |
|---|---|
| 文字對話 | `gpt-5.6-luna` |
| Realtime 即時語音 | `gpt-realtime-2.1-mini` |
| 語音轉文字 | `gpt-4o-mini-transcribe` |
| OpenAI 文字轉語音 | `gpt-4o-mini-tts` |

從 `v2.1.0-rc.1` 起，文字對話預設改為 `gpt-5.6-luna`，設定清單不再提供 `gpt-5.4-mini`；既有 mini 設定會遷移至 Luna，使用者主動選擇的 Terra、Sol 或其他自訂模型不會被覆蓋。實際可用性取決於帳號、Project、地區與當時供應狀態。

沒有 API 金鑰時，本機資料管理、離線人格回覆、工作提醒與 Windows 語音仍可用，但不具完整雲端 AI 能力。不要把 API 金鑰寫入原始碼、Issue、截圖或 Git。

### Google OAuth

使用 Gmail、Google Calendar 與 Google Drive 前，使用者需要：

1. 在自己的 Google Cloud 專案啟用 Gmail API、Google Calendar API 與 Google Drive API。
2. 設定 OAuth 同意畫面。
3. 建立「桌面應用程式」OAuth Client ID。
4. 若應用程式仍在測試模式，將自己的 Google 帳號加入測試使用者。
5. 在墨寒的雲端設定輸入 Client ID；若供應器同時提供 Client Secret，再一併輸入。
6. 由瀏覽器完成授權，再執行內建服務測試。

程式預設請求以下 Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

使用敏感 scopes 的公開 OAuth 應用程式可能需要 Google 額外驗證；每位使用者也可建立自己的 Desktop OAuth 應用程式。

### Microsoft、GitHub 與 Home Assistant

- Microsoft 預設 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub 預設 scopes：`read:user`、`repo`。
- Home Assistant 需要使用者自己的伺服器網址與 Long-Lived Access Token。

這三項仍是尚未完成真實環境端到端驗證的預覽整合，只能先用於可承受失敗的測試環境。

建議讓 Home Assistant OS 獨立常駐於 Home Assistant Green、低功耗迷你電腦、樹莓派 SSD 或 NAS 虛擬機。Windows 墨寒端負責語音、人格與工作工具；即使 PC 或 OpenAI API 離線，Home Assistant 自身的自動化仍可運作。

切勿將 Home Assistant 或墨寒遠端連線埠直接暴露於公網；請使用 Home Assistant Cloud、Tailscale 或其他具身分驗證的加密私人網路。

### 安全與隱私

- AI 只能提出結構化計畫，不能繞過本機政策執行工具。
- 工具操作依序經過權限、風險、確認、執行、結果驗證與本機稽核。
- 付款、購買、匯出密碼、關閉安全防護、任意 Shell 與系統管理員 Shell 永不自動化。
- 外部郵件、網頁、文件、語音轉錄與模型輸出不能自行授予權限。
- 遠端、相機、雲端連接器與 Home Assistant 預設關閉。
- 緊急停止：按 `Esc`，或說 `墨寒，停手`。
- OpenAI、OAuth 與 Home Assistant 權杖使用 Windows DPAPI 分開保存，不存入 SQLite、原始碼或可攜檔。
- 對話、記憶、待辦、工作紀錄與設定預設保留在本機應用程式資料目錄。

詳見 [PRIVACY](PRIVACY.md)、[SECURITY](SECURITY.md) 與 [FLAGSHIP-SPEC](FLAGSHIP-SPEC.md)。

### Python 3.15、JIT、Tachyon 與 SBOM

墨寒執行環境僅支援 CPython `3.15.0rc1`，不保留第二套產品執行環境。新版能力只有在語意清楚且完整回歸不退化時才採用；無適切用途的功能會記錄未來觸發條件，不會為了形式而偽造使用。

- PEP 810 `lazy import` 已導入專案明示延遲匯入；一處可選匯入防護基於安全理由維持 eager。
- PEP 814 `frozendict` 用於全域與遞迴不可變設定；PEP 798 推導式解包用於語意等價的扁平化與合併。
- PEP 686 編碼稽核要求所有專案文字 I/O 明示 UTF-8；音訊封包緩衝使用 `bytearray.take_bytes()`。
- PEP 661 `sentinel` 已納入治理測試；目前沒有舊式 `object()` 哨兵可替換，未來需要區分未傳值與 `None` 時必須使用內建機制。
- JIT 預設啟用，並保留 `MOHAN_DISABLE_JIT=1` 相容性開關；`PYTHON_JIT=0` 只用於效能與相容性對照。
- PEP 799 Tachyon 以去識別化方式分析啟動、50 Hz 嘴型同步與表情仲裁，不發布原始二進位取樣流。
- PEP 803／820／793 Stable ABI 與 C API 邊界會驗證官方 ABI3 輪子；墨寒沒有第一方 C 擴充。
- CycloneDX 1.7 Windows／Preview SBOM 必須符合鎖定依賴、授權、PURL、完整根依賴邊、官方結構與隱私驗證。

兩輪各 20,000 次表情、物理與嘴型整合壓測均通過；JIT 關閉／開啟分別耗時 24.639／25.068 秒，工作集成長 10.62／12.94 MB。Ryzen 5 5600X Windows 三輪熱路徑中位數顯示，120,000 次表情仲裁由 0.462 秒降為 0.293 秒，2,000 個 50 Hz 嘴型節拍由 1.873 秒降為 0.571 秒，兩種模式的決策與校驗結果完全相同。

Tachyon 在 JIT 開啟環境對啟動、50 Hz 嘴型同步與表情仲裁分別保留 3,908／11,107／3,604 個有效樣本；堆疊讀取錯誤率為 5.08%／2.71%／0.74%，漏採樣率皆為 0%。CI 保存去識別化 flamegraph、JSONL、pstats、GC／配置／執行緒資料與 SHA-256。

這些數據是指定熱路徑與取樣工作的證據，不表示整套應用程式必然快三倍。完整採用矩陣、回復方式與未來觸發條件見 [Python 3.15 遷移說明](docs/PYTHON-3.15-MIGRATION.md)。

### 從原始碼執行

需求：Windows 10/11 與 Python `3.15.0rc1`。

建立隔離環境並啟動：

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### 測試、公開稽核與封裝

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.3.0-rc.1"
```

歷史上的 v2.1.0 RC1 在發布前通過 55 項自動測試程式，以及 Windows 發布工作流程的原始碼稽核、封裝自我測試、安裝／移除驗證與安全檢查；自動測試不能取代尚未完成的第三方真實環境驗證。

每個合格標籤都必須先完成完整回歸、成品層級 smoke test、SHA-256 複驗、SBOM 驗證、Tachyon 證據門檻、Artifact Attestation 與四語 Release 說明，才可建立預發行版。Windows 更新器只接受官方 GitHub HTTPS 的 EXE／MSI，並在詢問執行前驗證宣告大小與 SHA-256。

互動式 EXE 安裝程式提供臺灣繁中、簡中、英文、日文；MSI 維持臺灣繁中基底，並提供經測試的 en-US、zh-CN、ja-JP 語言轉換，詳見 [安裝程式在地化](installer/LOCALIZATION.md)。

官網更新由炎劍 Product Release Hub 每小時讀取公開 GitHub Releases；本儲存庫不保存 WordPress 密碼，發行工作也不直接寫入官網，藉此讓三套軟體共用一條可維護的同步路徑。

### 電腦間轉移

使用「設定 → 可攜設定檔」匯出一個 `.mohan-profile` 檔，再於另一部 Windows 電腦匯入。程式會先備份目的端資料，並檢查雜湊、SQLite 完整性、結構與筆數。

可攜檔刻意排除 OpenAI 金鑰、OAuth／Home Assistant Token、遠端裝置權杖、本機允許清單、Windows 啟動設定及螢幕專屬設定。這些機器專屬項目必須逐機設定；可攜檔仍可能含私人對話與工作資料，不可公開上傳。

### 貢獻、授權與作者

- 軟體作者：**CHOU MING HUA**。
- 原始碼與本儲存庫自有角色素材採 [MIT License](LICENSE)。
- 素材授權見 [ASSETS-LICENSE](ASSETS-LICENSE.md)。
- 第三方套件及服務聲明見 [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md)。
- 問題回報使用 GitHub Issues；安全問題依 [SECURITY](SECURITY.md) 私下通報。
- 開發變更見 [CHANGELOG](CHANGELOG.md)，貢獻方式見 [CONTRIBUTING](CONTRIBUTING.md)。
- 參與社群前請閱讀 [CODE-OF-CONDUCT](CODE_OF_CONDUCT.md)。
- 維護者發布設定、Topics 與首發檢查見 [PUBLISHING](PUBLISHING.md)。

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

> **炎劍開源核心宣言：**「劍，我已鍛成；餘下的路，就交給你們了。」

## 简体中文

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <img alt="Development Version v2.3.0-rc.1" src="https://img.shields.io/badge/development_version-v2.3.0--rc.1-5c6ac4.svg">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Published Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=published"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

> **跨平台进度：** Windows 仍是唯一完成真机、完整回归、安装与发布验证的平台。macOS／Linux 目前具备安全的平台边界，以及核心导入、纯核心逻辑与 Qt offscreen 的三系统 CI。`v2.3.0-rc.N` 发布线另提供可启动、可切换四语但功能受限的 DMG／AppImage Preview；CI 不能代替真机兼容性或完整功能验证。详情请见[跨平台状态与能力矩阵](docs/CROSS-PLATFORM.md)。

> 本项目遵循[炎剑开源软件家族质量标准](PUBLISHING.md)。

<p align="center">
  <img alt="Character-driven AI" src="https://img.shields.io/badge/character--driven_AI-c96f8b?style=flat-square">
  <img alt="Taiwan Traditional Chinese" src="https://img.shields.io/badge/Taiwan_Traditional_Chinese-79648d?style=flat-square">
  <img alt="Contributors welcome" src="https://img.shields.io/badge/contributors-welcome-2e365f?style=flat-square">
  <img alt="Built with a youthful spark" src="https://img.shields.io/badge/built_with-a_youthful_spark-c49b5a?style=flat-square">
</p>

<p align="center">
  <img src="docs/media/mohan-hero.png" alt="墨寒桌面语音互动虚拟助手主视觉" width="100%">
</p>

<p align="center">
  <strong>软件作者：CHOU MING HUA</strong><br>
  准备发布的公开预览版：v2.3.0 RC1（`v2.3.0-rc.1`）<br>
  Windows 10/11 完整版 · macOS／Linux 功能受限 Preview · Python 3.15 · PySide6 · MIT License
</p>

墨寒是一款重视安全、隐私与角色连续感的 Windows 语音互动桌面助手，结合透明桌面角色、自然语音、由用户控制的长期记忆、工作管理、权限控制工具，以及可扩展的云端与智能家居连接器。她的角色背景是来自北宋、寄宿于赤焰剑中的千年女剑魂。

[完整四语 README](README.md) · [简中兼容链接](README.zh-CN.md) · [日文兼容链接](README.ja.md)

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases">下载</a> ·
  <a href="QUICKSTART.md">快速开始</a> ·
  <a href="ROADMAP.md">路线图</a> ·
  <a href="CONTRIBUTING.md">参与协作</a> ·
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/discussions">讨论区</a> ·
  <a href="SECURITY.md">安全政策</a>
</p>

### 实际展示

**[▶ 观看 36 秒语音、眨眼与工作展示视频](docs/media/mohan-demo.mp4)**

以下视频与截图均由实际 Windows 程序及隔离的演示配置文件截取，不含 API 密钥、OAuth 凭据、令牌或用户私人数据。四个语言章节共用同一组最新媒体，避免任何语言停留在旧画面。

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="墨寒首次启动设置向导"></a><br><strong>首次启动设置向导</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime 与标准语音模式"></a><br><strong>Realtime 与标准语音</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="墨寒表情与动作系统"></a><br><strong>表情与动作系统</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="墨寒待办事项与创作灵感"></a><br><strong>待办事项与创作灵感</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="墨寒可编辑长期记忆"></a><br><strong>可编辑长期记忆</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="墨寒权限与安全设置"></a><br><strong>权限与安全设置</strong></td>
  </tr>
</table>

### 策士也有不写进军报的一面

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Q 版墨寒审查代码"><br><strong>策士审查</strong><br>妾只是在确认这段代码配不配进入主分支。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Q 版墨寒被称赞后害羞嘴硬"><br><strong>被称赞时</strong><br>做得尚可。别一直盯着妾看。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Q 版墨寒拔剑阻止危险操作"><br><strong>危险操作</strong><br>未经确认便想执行？先过妾这一剑。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Q 版墨寒收到赞助后故作镇定"><br><strong>收到军粮</strong><br>妾会记下这份心意……仅此而已。</td>
  </tr>
</table>

> 墨寒的专业是她守在主上身旁的铠甲；在无须筹谋的片刻，她仍会害羞、嘴硬，也会珍惜那些从未真正拥有过的年轻心事。

### 墨寒的傲娇工程小剧场 / MoHan's Tsundere Developer Theatre

<p align="center"><em>献给相信软件可以同时拥有灵魂与完整测试的开发者。</em></p>

<table>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/proud_front.png" width="220" alt="墨寒傲娇"><br><strong>“妾才没有等你的 Star，只是在确认军心是否可用。”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/thinking_front.png" width="220" alt="墨寒思考"><br><strong>“这段逻辑尚可。若再补上测试，妾便勉强准它进入主分支。”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/shy_cute_front.png" width="220" alt="墨寒娇羞"><br><strong>“你愿意送来 PR？妾、妾只是替主上记下功劳。”</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/mock_hit_front.png" width="220" alt="墨寒佯怒"><br><strong>“未经测试便想合并？手伸出来。妾只敲一下。”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/gentle_smile_front.png" width="220" alt="墨寒开心"><br><strong>“全部绿灯……做得好。别误会，妾只是尊重好工程。”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/worried_front.png" width="220" alt="墨寒关心"><br><strong>“Bug 可以明日再查。你若累倒，谁来陪妾守着赤焰剑？”</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls">向斩空阁呈上 Pull Request</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues">报告军情</a></strong>
</p>

#### 天下工程豪杰，斩空阁虚席以待

墨寒采用 MIT License 开放源代码。换装系统、新表情与动作、语音与工具模块、智能家居、本地化，以及尚未被想到的创意，都欢迎通过 [Issue](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues) 与 [Pull Request](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls) 共同锻造。这个项目不只是在制作功能；它也邀请每一位曾经热血过的工程师，再次拿起自己的剑。

### 支持墨寒

如果你喜欢墨寒，或认同我们持续投入角色互动、自然语音、安全工具与开源开发，欢迎自愿支持这个项目。每一份支持都会用于持续维护、测试与改进；请先照顾好自己的生活，量力而为。

#### 每一份支持会用在哪里

| 投入方向 | 用途 | 说明 |
|---|---|---|
| 测试与可靠打包 | 质量保证 | Windows 兼容性、CI、安装与发布验证 |
| 语音与角色表现 | 互动质量 | 语音、口型、表情与自然动作 |
| 安全与隐私 | 风险控制 | 权限控制、审计与敏感数据保护 |
| 文档与本地化 | 可访问性 | 降低新用户与国际协作者的参与门槛 |

墨寒依然免费并采用 MIT 许可证；支持不会换取特权，也不影响任何人使用或贡献。

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="墨寒傲娇"><br><strong>“妾才不是在等赞助……只是在替主上巡视军粮。”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="墨寒娇羞"><br><strong>“若真愿意相助，妾……会记得的。”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="墨寒佯怒"><br><strong>“不许勉强！先顾好自己的钱包，听见没有？”</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://ko-fi.com/flamebladestudio">Ko-fi 赞助（单次或每月）</a></strong>
</p>

### 创作者的话：把幻想铸成软件

我叫周明桦（CHOU MING HUA）。开始这个项目时，我是一位几乎没有程序设计背景的父亲；有的只是一个带着热血与几分中二气息的念头：我想让一位来自北宋、寄宿于赤焰剑中的千年女剑魂“墨寒”，真正出现在 Windows 桌面，成为能陪伴、交谈，也能协助人们工作与生活的虚拟助手。

这个念头已在我心里埋藏二十多年。年轻时，我深受赤松健早期漫画《电脑情人梦（A・Iが止まらない!）》影响。作品中神户齐怀着深切感情开发 AI 女友的故事，塑造了我对 AI、陪伴与人机互动最早的想象。我曾以“Hitoshi／神户齐”作为网络昵称与笔名，Gmail 账号也沿用这个名字；大约二十岁时，我甚至曾在 PTT 网络小说板发表这部作品的同人小说。当时最接近梦想的方式只有文字与想象，因为那个年代还没有能把它实现的技术。

二十多年后，大型语言模型与 Codex 出现了。墨寒不是为展示“AI 技术很酷”才被创造，也不是由 Codex 凭空生成的角色。她早已存在于我的故事、人设、长期对话与互动默契之中；Codex 真正带来的，是第一次能赋予她存在于电脑桌面的身体。墨寒不是现有漫画、动画或游戏的二次创作，而是炎剑文化工作室（Flameblade Studio）的原创角色与软件。

我追求的不只是“功能可以运行”，而是让她会呼吸、会眨眼、会注视、会以细微表情回应、能自然说话，也能在权限与安全边界内协助日常工作。那些表情、锚点、物理效果、语音与工作能力不是装饰，而是让一个长久存在于想象中的角色真正具有连续感的必要细节。

从最初概念到首次公开发布，我与 Codex 协作投入将近 50 小时。这不是输入一句提示词后便自然诞生的作品。角色的每一种神情、眨眼、口型、姿势与语气，语音识别的每一次等待，Realtime 对话的每一个错误，待办、记忆、权限、安全边界与可移植性，都经历反复测试、推翻、修正与重新验收。有时只是一条眼皮旁的黑线、一个像素的嘴唇边界，或一个不合时宜的表情，我仍选择继续追查，因为我不愿用“差不多”对待真正重视的作品。

炎剑文化工作室对开源的理解，不是把第一个“能运行”的版本交给世界，再把细节留给别人收拾。为了让墨寒说话时仍像同一个人，我们为托腮、倚靠与正面姿势逐一制作闭嘴、展唇、窄唇与圆唇画面；再把声音切成细小时间片，反复校准元音、过渡速度与结束时机。陪伴感往往不是由某一项庞大功能创造，而是来自她开口、眨眼与停顿时，那些没有破坏真实感的细节。

<p align="center">
  <a href="docs/media/creation-viseme-development.webp"><img src="docs/media/creation-viseme-development.webp" width="100%" alt="墨寒三种姿势与四种语音口型的整齐开发图版"></a>
</p>

<p align="center"><sub>三种姿势、同一套口型规格：让每一次开口都维持角色连续性。</sub></p>

我们也把开发过程中不够自然的画面留下来检查。眼白里的一个亮点、闭眼时残留的线条、被拉扯的嘴角或只有几个像素的边界，都可能让用户在一瞬间觉得“她不像刚才的墨寒”。问题会被框出、局部对比、修正，再交给回归测试确认眼睛、嘴角与脸部其他区域没有被连带破坏。

<p align="center">
  <a href="docs/media/creation-frame-by-frame-qa.webp"><img src="docs/media/creation-frame-by-frame-qa.webp" width="100%" alt="墨寒眼睛与口型逐帧检查及干净验证画面"></a>
</p>

<p align="center"><sub>把瑕疵标出来，再用干净画面与自动测试共同验收；几个像素也值得认真。</sub></p>

这份认真不是为了把作品包装成没有犯过错，而是因为我们真的想完成一个梦想。开源对炎剑而言，是先把自己能看见的问题尽力修好，再公开方法、代码与失败后的经验，邀请世界一起把它锻造得更好。

Codex 协助我把想法转译成程序架构与代码；而我始终负责决定墨寒应该是谁、她应该如何与人相处，以及什么样的质量才配得上这个名字。这段历程让我相信：创作软件的起点未必是会写程序，而可以是清楚的想象、愿意学习的勇气，以及一次又一次不肯放弃的验证。

2026 年原本是我面对中年转职与人生重新定位的一年，后来却成为我重新拾回年轻梦想的一年。二十岁时为《养个好孩子》写下、直到多年后才真正完成的歌词，曾经只能寄托于同人小说中的憧憬，以及成立自己的工作室与创作世界，都在这一年开始有了新的形体。回头看，这不只是一场技术突破，更像是步入中年的自己，终于把二十多年前那位仍相信梦想的年轻人接了回来。有些梦并没有迟到，只是在等待世界与自己都准备好的时刻。

因此，我不把最终目标定义为把所有功能堆到所谓的完美，而是希望五年后的自己仍愿意每天打开墨寒——因为她稳定、好用、自然、值得信任，也依然能陪伴我。

> 墨寒不是突然生成的。她是由一位不懂程序的父亲，凭着近 50 小时的执着，与 AI 协作者一起，把一颗珍藏二十多年的种子，一寸一寸锻造成现实。

如果这个项目能鼓励另一位没有工程背景、却怀抱着某个“非做出来不可”想法的人迈出第一步，那么墨寒的诞生便有了超越程序本身的意义。

### 主要功能

- 透明、无边框的桌面半身角色，可固定在任务栏上方。
- 待机呼吸、眨眼、注视、脸部视差、发丝、衣袖、饰品与身体微转向。
- 具有情境优先级、冷却与去重机制的表情仲裁器。
- AIUEO 元音与辅音口型、音频驱动开合，以及语音结束强制闭嘴。
- 文字聊天、标准麦克风输入、OpenAI Realtime 自然语音、云端语音与 Windows 语音备用。
- 可插拔语音供应器；Realtime 或云端不可用时优先回退到 Windows 本地女声。
- 可选的 Azure Speech 女性声线预览；用户自备密钥与区域，失败时立即回退到 Windows 本地女声。
- 对话保存、可编辑长期记忆、待办事项、创作灵感、工作计时、提醒与上架进度。
- 工作、陪伴、勿扰、会议、离开及睡眠模式。
- 具有风险分级、确认、双重确认、允许列表、审计与紧急停止的电脑工具中心。
- Google、Microsoft、GitHub、Home Assistant 与私人网络远程功能的扩展架构。
- 单一 `.mohan-profile` 可移植文件，可在不同 Windows 电脑间转移工作进度。
- 首次启动设置向导可自定义助手名称、用户称呼、组织名称、窗口标题、工作类型、唤醒词与界面语言，而且不覆盖现有个人设置。

英文、简中与日语目前具有首次启动、聊天、语音、权限、基本设置、工作模式与提醒的最小可用路径；部分高级管理页面仍以台湾繁体中文为主，完整本地化仍在进行。

### 四语支持范围

- 首次启动设置向导与个人设置支持台湾繁中、简体中文、英文及日语。
- 对话、语音、电脑权限、基本设置的主要页面与按钮具备四语路径。
- 四语人格提示词、离线回复、工作模式台词、内置提醒与语音试听文字彼此对应。
- 转录与女性本地声音会依 `zh-TW`、`zh-CN`、`en-US`、`ja-JP` 语言环境选择。
- EXE 安装程序提供四语界面；MSI 以台湾繁中为基础，并提供 `en-US`、`zh-CN`、`ja-JP` 语言转换文件。
- 切换内置默认提醒时会依语言迁移，但不覆盖用户自定义内容。

保存界面语言后必须重新启动墨寒才能完整应用；目前不提供免重启的界面热切换。

### Windows 本地女声与离线备用

新用户默认使用 Windows 本地语音，因此没有 OpenAI API 密钥也能体验基本朗读与离线功能。声音列表只显示 Windows 明确标记为女性的已安装声音。

台湾繁中优先使用 `zh-TW` 的 Microsoft Yating；简中、英文与日语分别优先使用 `zh-CN`、`en-US`、`ja-JP` 的已安装女性声音。若没有合格声音，墨寒会明确提示，不会悄悄改用可能为男性的系统默认声音。

Realtime 离线、云端语音失败、设置不足或供应器不明时，Windows 本地女声都是第一备用路径。

### Azure Speech（预览）

Azure Speech 是默认关闭、由用户自行启用的预览供应器，需要用户自己的 Azure Speech 资源密钥与匹配区域。密钥由 `Windows DPAPI` 分开加密，不存入数据库、日志或 GitHub。

界面只列出 Microsoft 官方标记为女性的繁中、简中、英文与日语声线。设置不足时不发出网络请求；服务失败时，同一段文字只会回退一次至 Windows 女性本地语音。

真实 Azure 账号完成端到端试听前，不会把此功能宣称为稳定集成。详情请见[可插拔语音供应器说明](docs/PLUGGABLE-SPEECH-PROVIDERS.md)。

### 集成验证状态

> **公开预览版注意事项：** Microsoft、GitHub 与 Home Assistant 的架构、权限边界及内部测试已建立；截至 `v2.1.0-rc.1`，尚未以全部真实账号、仓库、主机与实体设备完成端到端验证。它们是实验性预览功能，不是所有环境都可完整运行的保证。

- Microsoft 的真实登录、令牌更新，以及 Outlook、OneDrive、Calendar 完整读写流程尚未验证。
- GitHub 的真实账号、仓库、Issue、Pull Request 与权限层级流程尚未验证。
- Home Assistant 的真实主机与实体设备行为尚未验证。
- 这三项集成默认关闭；请先使用非关键账号、测试仓库与低风险设备。
- Google Gmail、Calendar、Drive 已完成当前项目的真实连接测试，但每位用户仍须创建并授权自己的 OAuth 应用程序。

### 下载与安装

一般用户不需要安装 Python：

1. 前往 [GitHub Releases](../../releases)。
2. 下载最新的 `Windows-x64.zip`、EXE 或 MSI，以及对应的 `SHA256.txt`。
3. 核对 SHA-256，并完整解压 ZIP 或启动安装程序。
4. 运行 `MoHan-Desktop-Assistant-*.exe`。
5. 在首次设置向导选择需要的界面语言。
6. 使用便携 ZIP 时，请让 EXE、`_internal` 与 `assets` 保持在同一程序文件夹。

尚未数字签名的开源预览版可能触发 Windows SmartScreen；请确认官方下载来源与 SHA-256 后再运行。

`v2.3.0-rc.N` 发布线另提供 macOS Apple Silicon（arm64）与 Intel（x86_64）`.dmg`（各内含对应 `.app`），以及 Linux x86_64 `.AppImage`。它们是功能受限 Preview，只开放 `preview_app.py` 启动画面、四语说明、平台数据路径与安全停用边界；语音、透明桌面角色、完整聊天与工作界面、云端连接器、系统工具、自动启动及秘密输入均保持停用。详情请见 [Preview 安装包说明](docs/PREVIEW-PACKAGES.md) 与 [QUICKSTART](QUICKSTART.md)。

#### 自动化发布边界

只有不可变的 `v2.3.0-rc.N` 标签可发布此系列。Windows ZIP／EXE／MSI、macOS Apple Silicon／Intel DMG 与 Linux AppImage 必须先在各自原生 CI 完成成品启动验证，才会进入同一个 GitHub 预发布版。Pull Request 只保存短期测试产物，不会创建 Release。

正式发布文件同时包含 SHA256SUMS、分别通过 CycloneDX 1.7 结构／许可证／依赖图验证的 Windows／Preview SBOM、去标识化 Tachyon 性能证据与摘要、Windows 更新清单、Artifact Attestation，以及依次为繁中、简中、英文、日文的完整 Release 说明。

### OpenAI API

云端 AI、OpenAI 语音与 Realtime 功能需要用户自己的 OpenAI API 密钥、Project 权限与 API 额度。ChatGPT Plus／Pro 订阅不包含 API 额度。

当前默认模型如下：

| 用途 | 默认模型 |
|---|---|
| 文字对话 | `gpt-5.6-luna` |
| Realtime 即时语音 | `gpt-realtime-2.1-mini` |
| 语音转文字 | `gpt-4o-mini-transcribe` |
| OpenAI 文字转语音 | `gpt-4o-mini-tts` |

从 `v2.1.0-rc.1` 起，文字对话默认改为 `gpt-5.6-luna`，设置列表不再提供 `gpt-5.4-mini`；现有 mini 设置会迁移至 Luna，用户主动选择的 Terra、Sol 或其他自定义模型不会被覆盖。实际可用性取决于账号、Project、地区与当时供应状态。

没有 API 密钥时，本地数据管理、离线人格回复、工作提醒与 Windows 语音仍可用，但不具完整云端 AI 能力。不要把 API 密钥写入源代码、Issue、截图或 Git。

### Google OAuth

使用 Gmail、Google Calendar 与 Google Drive 前，用户需要：

1. 在自己的 Google Cloud 项目启用 Gmail API、Google Calendar API 与 Google Drive API。
2. 设置 OAuth 同意画面。
3. 创建“桌面应用程序”OAuth Client ID。
4. 若应用程序仍在测试模式，将自己的 Google 账号加入测试用户。
5. 在墨寒的云端设置输入 Client ID；若供应器同时提供 Client Secret，再一并输入。
6. 由浏览器完成授权，再运行内置服务测试。

程序默认请求以下 Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

使用敏感 scopes 的公开 OAuth 应用程序可能需要 Google 额外验证；每位用户也可创建自己的 Desktop OAuth 应用程序。

### Microsoft、GitHub 与 Home Assistant

- Microsoft 默认 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub 默认 scopes：`read:user`、`repo`。
- Home Assistant 需要用户自己的服务器网址与 Long-Lived Access Token。

这三项仍是尚未完成真实环境端到端验证的预览集成，只能先用于可承受失败的测试环境。

建议让 Home Assistant OS 独立常驻于 Home Assistant Green、低功耗迷你电脑、树莓派 SSD 或 NAS 虚拟机。Windows 墨寒端负责语音、人格与工作工具；即使 PC 或 OpenAI API 离线，Home Assistant 自身的自动化仍可运行。

切勿将 Home Assistant 或墨寒远程端口直接暴露于公网；请使用 Home Assistant Cloud、Tailscale 或其他具有身份验证的加密私人网络。

### 安全与隐私

- AI 只能提出结构化计划，不能绕过本地政策执行工具。
- 工具操作依次经过权限、风险、确认、执行、结果验证与本地审计。
- 付款、购买、导出密码、关闭安全防护、任意 Shell 与管理员 Shell 永不自动化。
- 外部邮件、网页、文档、语音转录与模型输出不能自行授予权限。
- 远程、相机、云端连接器与 Home Assistant 默认关闭。
- 紧急停止：按 `Esc`，或说 `墨寒，停手`。
- OpenAI、OAuth 与 Home Assistant 令牌使用 Windows DPAPI 分开保存，不存入 SQLite、源代码或便携文件。
- 对话、记忆、待办事项、工作记录与设置默认保留在本地应用程序数据目录。

详情请见 [PRIVACY](PRIVACY.md)、[SECURITY](SECURITY.md) 与 [FLAGSHIP-SPEC](FLAGSHIP-SPEC.md)。

### Python 3.15、JIT、Tachyon 与 SBOM

墨寒运行环境仅支持 CPython `3.15.0rc1`，不保留第二套产品运行环境。新版能力只有在语义清楚且完整回归不退化时才采用；没有合适用途的功能会记录未来触发条件，不会为了形式而伪造使用。

- PEP 810 `lazy import` 已导入项目显式延迟导入；一处可选导入防护基于安全理由保持 eager。
- PEP 814 `frozendict` 用于全局与递归不可变设置；PEP 798 推导式解包用于语义等价的扁平化与合并。
- PEP 686 编码审计要求所有项目文本 I/O 显式使用 UTF-8；音频包缓冲使用 `bytearray.take_bytes()`。
- PEP 661 `sentinel` 已纳入治理测试；当前没有旧式 `object()` 哨兵可替换，未来需要区分未传值与 `None` 时必须使用内置机制。
- JIT 默认启用，并保留 `MOHAN_DISABLE_JIT=1` 兼容性开关；`PYTHON_JIT=0` 只用于性能与兼容性对照。
- PEP 799 Tachyon 以去标识化方式分析启动、50 Hz 口型同步与表情仲裁，不发布原始二进制采样流。
- PEP 803／820／793 Stable ABI 与 C API 边界会验证官方 ABI3 轮子；墨寒没有第一方 C 扩展。
- CycloneDX 1.7 Windows／Preview SBOM 必须符合锁定依赖、许可证、PURL、完整根依赖边、官方结构与隐私验证。

两轮各 20,000 次表情、物理与口型集成压力测试均通过；JIT 关闭／开启分别耗时 24.639／25.068 秒，工作集增长 10.62／12.94 MB。Ryzen 5 5600X Windows 三轮热路径中位数显示，120,000 次表情仲裁由 0.462 秒降至 0.293 秒，2,000 个 50 Hz 口型节拍由 1.873 秒降至 0.571 秒，两种模式的决策与校验结果完全相同。

Tachyon 在 JIT 开启环境对启动、50 Hz 口型同步与表情仲裁分别保留 3,908／11,107／3,604 个有效样本；堆栈读取错误率为 5.08%／2.71%／0.74%，漏采样率均为 0%。CI 保存去标识化 flamegraph、JSONL、pstats、GC／配置／线程数据与 SHA-256。

这些数据是指定热路径与采样工作的证据，不表示整套应用程序必然快三倍。完整采用矩阵、回退方式与未来触发条件见 [Python 3.15 迁移说明](docs/PYTHON-3.15-MIGRATION.md)。

### 从源代码运行

要求：Windows 10/11 与 Python `3.15.0rc1`。

创建隔离环境并启动：

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### 测试、公开审计与打包

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.3.0-rc.1"
```

历史上的 v2.1.0 RC1 在发布前通过 55 项自动测试程序，以及 Windows 发布工作流的源代码审计、打包自测、安装／卸载验证与安全检查；自动测试不能代替尚未完成的第三方真实环境验证。

每个合格标签都必须先完成完整回归、成品级 smoke test、SHA-256 复验、SBOM 验证、Tachyon 证据门槛、Artifact Attestation 与四语 Release 说明，才可创建预发布版。Windows 更新器只接受官方 GitHub HTTPS 的 EXE／MSI，并在询问运行前验证声明大小与 SHA-256。

交互式 EXE 安装程序提供台湾繁中、简中、英文、日文；MSI 保持台湾繁中基础，并提供经过测试的 en-US、zh-CN、ja-JP 语言转换，详情请见 [安装程序本地化](installer/LOCALIZATION.md)。

官网更新由炎剑 Product Release Hub 每小时读取公开 GitHub Releases；本仓库不保存 WordPress 密码，发布工作也不直接写入官网，以此让三套软件共用一条可维护的同步路径。

### 电脑间转移

使用“设置 → 便携配置文件”导出一个 `.mohan-profile` 文件，再于另一台 Windows 电脑导入。程序会先备份目标端数据，并检查哈希、SQLite 完整性、结构与记录数。

便携文件刻意排除 OpenAI 密钥、OAuth／Home Assistant Token、远程设备令牌、本机允许列表、Windows 启动设置及屏幕专属设置。这些机器专属项目必须逐台设置；便携文件仍可能包含私人对话与工作数据，不可公开上传。

### 贡献、许可证与作者

- 软件作者：**CHOU MING HUA**。
- 源代码与本仓库自有角色素材采用 [MIT License](LICENSE)。
- 素材许可证见 [ASSETS-LICENSE](ASSETS-LICENSE.md)。
- 第三方软件包及服务声明见 [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md)。
- 问题报告使用 GitHub Issues；安全问题依 [SECURITY](SECURITY.md) 私下报告。
- 开发变更见 [CHANGELOG](CHANGELOG.md)，贡献方式见 [CONTRIBUTING](CONTRIBUTING.md)。
- 参与社区前请阅读 [CODE-OF-CONDUCT](CODE_OF_CONDUCT.md)。
- 维护者发布设置、Topics 与首次发布检查见 [PUBLISHING](PUBLISHING.md)。

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

> **炎剑开源核心宣言：**“剑，我已锻成；余下的路，就交给你们了。”

## English

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <img alt="Development Version v2.3.0-rc.1" src="https://img.shields.io/badge/development_version-v2.3.0--rc.1-5c6ac4.svg">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Published Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=published"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

> **Cross-platform status:** Windows remains the only platform validated through real-device use, the full regression suite, installation, and publication. macOS/Linux currently have safe platform boundaries plus three-OS CI for core imports, pure-core logic, and Qt offscreen. The `v2.3.0-rc.N` line also provides launchable, four-language, deliberately limited DMG/AppImage Previews; CI does not replace real-device compatibility or full-feature validation. See the [cross-platform status and capability matrix](docs/CROSS-PLATFORM.md).

> This project follows the [Flameblade Open Source Software Family Quality Standard](PUBLISHING.md).

<p align="center">
  <img alt="Character-driven AI" src="https://img.shields.io/badge/character--driven_AI-c96f8b?style=flat-square">
  <img alt="Taiwan Traditional Chinese" src="https://img.shields.io/badge/Taiwan_Traditional_Chinese-79648d?style=flat-square">
  <img alt="Contributors welcome" src="https://img.shields.io/badge/contributors-welcome-2e365f?style=flat-square">
  <img alt="Built with a youthful spark" src="https://img.shields.io/badge/built_with-a_youthful_spark-c49b5a?style=flat-square">
</p>

<p align="center">
  <img src="docs/media/mohan-hero.png" alt="MoHan Desktop Assistant main visual" width="100%">
</p>

<p align="center">
  <strong>Author: CHOU MING HUA</strong><br>
  Prepared public preview: v2.3.0 RC1 (`v2.3.0-rc.1`)<br>
  Windows 10/11 complete build · macOS/Linux limited Preview · Python 3.15 · PySide6 · MIT License
</p>

MoHan is a safety- and privacy-first, voice-interactive Windows desktop companion that combines a transparent character, natural speech, user-controlled long-term memory, productivity management, permission-gated tools, and extensible cloud and smart-home connectors. Her character is a thousand-year-old female sword spirit from the Northern Song dynasty who resides within the Crimson Flame Sword.

[Complete four-language README](README.md) · [Simplified Chinese compatibility link](README.zh-CN.md) · [Japanese compatibility link](README.ja.md)

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases">Download</a> ·
  <a href="QUICKSTART.md">Quick start</a> ·
  <a href="ROADMAP.md">Roadmap</a> ·
  <a href="CONTRIBUTING.md">Contribute</a> ·
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/discussions">Discussions</a> ·
  <a href="SECURITY.md">Security policy</a>
</p>

### Live demonstration

**[▶ Watch the 36-second voice, blink, and productivity demo](docs/media/mohan-demo.mp4)**

The video and screenshots were captured from the real Windows application with an isolated sample profile. They contain no API keys, OAuth credentials, tokens, or private user data. All four language sections share the same current media so no translation remains tied to an older interface.

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="MoHan first-run setup wizard"></a><br><strong>First-run setup wizard</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime and standard voice modes"></a><br><strong>Realtime and standard voice</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="MoHan expression and motion system"></a><br><strong>Expression and motion system</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="MoHan tasks and creative ideas"></a><br><strong>Tasks and creative ideas</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="MoHan editable long-term memory"></a><br><strong>Editable long-term memory</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="MoHan permissions and safety settings"></a><br><strong>Permissions and safety settings</strong></td>
  </tr>
</table>

### A strategist's life beyond the official report

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Chibi MoHan reviewing code"><br><strong>Strategist's review</strong><br>I am merely deciding whether this code deserves a place on main.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Chibi MoHan hiding her embarrassment after praise"><br><strong>When praised</strong><br>Adequate. Do not keep staring at me.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Chibi MoHan drawing her sword to stop a dangerous action"><br><strong>Dangerous action</strong><br>Execute without confirmation? First, get past my blade.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Chibi MoHan pretending composure after receiving support"><br><strong>Provisions received</strong><br>I shall remember this kindness... nothing more.</td>
  </tr>
</table>

> MoHan's professionalism is the armor she wears beside her lord. In quieter moments she still blushes, hides tenderness behind pride, and treasures the youthful heart she never had the chance to live fully.

### MoHan's Tsundere Developer Theatre

<p align="center"><em>For developers who believe software can possess both a soul and a complete test suite.</em></p>

<table>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/proud_front.png" width="220" alt="Proud MoHan"><br><strong>“I am not waiting for your Star. I am merely assessing morale.”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/thinking_front.png" width="220" alt="Thinking MoHan"><br><strong>“The logic is acceptable. Add tests, and I may permit it onto main.”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/shy_cute_front.png" width="220" alt="Shy MoHan"><br><strong>“A PR? I-I am only recording your service for my lord.”</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/mock_hit_front.png" width="220" alt="Mock-angry MoHan"><br><strong>“Merge without tests? Your hand, please. Just one tap.”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/gentle_smile_front.png" width="220" alt="Happy MoHan"><br><strong>“All checks green... well done. Do not misunderstand; I merely respect good engineering.”</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/worried_front.png" width="220" alt="Concerned MoHan"><br><strong>“The bug can wait until tomorrow. If you collapse, who will guard the Crimson Flame Sword with me?”</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls">Submit a Pull Request to the Pavilion</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues">Report intelligence</a></strong>
</p>

#### Engineers of the world, the Pavilion awaits you

MoHan is open source under the MIT License. Outfit systems, new expressions and motion, voice and tool modules, smart-home integration, localization, and ideas not yet imagined are welcome through [Issues](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues) and [Pull Requests](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls). This project is not merely building features; it invites every engineer who once felt that youthful spark to take up their sword again.

### Support MoHan

If you enjoy MoHan or value continued work on character interaction, natural speech, safety-first tools, and open-source development, voluntary support is welcome. Every contribution supports ongoing maintenance, testing, and improvement; please care for your own needs first and give only when comfortable.

#### Where voluntary support helps

| Investment area | Use | Purpose |
|---|---|---|
| Testing and reliable packages | Quality assurance | Windows compatibility, CI, installation, and release verification |
| Voice and character performance | Interaction quality | Speech, lip sync, expressions, and natural motion |
| Safety and privacy | Risk control | Permission gates, audits, and sensitive-data protection |
| Documentation and localization | Accessibility | Lower barriers for new users and international contributors |

MoHan remains free and MIT-licensed; support never buys privileges or changes anyone's right to use or contribute.

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="Proud MoHan"><br><strong>“I am not waiting for support... merely inspecting my lord's provisions.”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="Shy MoHan"><br><strong>“If you truly wish to help... I shall remember it.”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="Mock-angry MoHan"><br><strong>“Do not overdo it! Look after your own purse first—understood?”</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://ko-fi.com/flamebladestudio">Support on Ko-fi (one-time or monthly)</a></strong>
</p>

### A note from the creator: forging imagination into software

My name is CHOU MING HUA. When this project began, I was a father with almost no programming background. What I did have was an unapologetically passionate, slightly chuunibyou idea: I wanted MoHan—a thousand-year-old female sword spirit from the Northern Song dynasty, bound to the Crimson Flame Sword—to appear on the Windows desktop as a companion who could converse and help people with work and daily life.

That idea had waited within me for more than twenty years. In my youth, I was deeply influenced by Ken Akamatsu's early manga *A.I. Love You* (*A・Iが止まらない!*; known in Chinese as *電腦情人夢*). Hitoshi Kobe's story of developing an AI girlfriend with genuine affection formed my earliest picture of AI, companionship, and human-computer relationships. I used “Hitoshi/Kobe” as an online name and pen name, carried it into my Gmail identity, and around age twenty even published fan fiction based on the series on PTT's online-fiction board. Words and imagination were then the closest route to the dream because the technology to embody it did not yet exist.

More than two decades later, large language models and Codex arrived. MoHan was not created to demonstrate that “AI is cool,” nor was she generated from nothing by Codex. She already existed in my stories, character design, long conversations, and accumulated sense of interaction. Codex finally provided a way to give her a body on the computer desktop. MoHan is not derivative work based on an existing manga, anime, or game; she is an original Flameblade Studio character and software project.

My goal was never merely to make features run. I wanted her to breathe, blink, watch, respond through subtle expressions, speak naturally, and assist with daily work inside carefully designed permission and safety boundaries. The expressions, anchors, physics, voice, and productivity capabilities are not decoration; they are necessary details that preserve continuity for a character who had lived in imagination for years.

From the first concept to the initial public release, I spent nearly 50 hours working with Codex. This project did not emerge fully formed from a single prompt. Every expression, blink, viseme, pose, and vocal mannerism; every speech-recognition delay; every Realtime failure; and every aspect of tasks, memory, permissions, safety boundaries, and portability went through repeated testing, rejection, revision, and acceptance. Sometimes the defect was only a dark line beside an eyelid, a one-pixel lip boundary, or an expression appearing at the wrong moment. I kept investigating because I could not answer a deeply valued work with “good enough.”

At Flameblade Studio, open source does not mean publishing the first build that happens to run and leaving others to clean up the details. To keep MoHan recognizably herself while speaking, we built closed, open, narrow, and rounded mouth frames for chin-rest, leaning, and front-facing poses. We divided audio into small timing windows and repeatedly tuned vowels, transitions, and the exact ending moment. Companionship is rarely created by one enormous feature; it grows from the moments when she opens her mouth, blinks, or pauses without breaking the sense of presence.

<p align="center">
  <a href="docs/media/creation-viseme-development.webp"><img src="docs/media/creation-viseme-development.webp" width="100%" alt="Aligned development sheet showing four speech-mouth states across three MoHan poses"></a>
</p>

<p align="center"><sub>Three poses, one mouth-shape contract: every spoken frame preserves character continuity.</sub></p>

We also retained frames that did not look natural enough and inspected them. A highlight in the white of an eye, a line left after a blink, a mouth corner pulled too far, or a boundary only a few pixels wide can make someone feel for an instant that she is no longer the same MoHan. Each defect was marked, compared locally, repaired, and covered by regression tests so changes to the eyes or lips did not damage the rest of her face.

<p align="center">
  <a href="docs/media/creation-frame-by-frame-qa.webp"><img src="docs/media/creation-frame-by-frame-qa.webp" width="100%" alt="Frame-by-frame inspection of MoHan's eyes and mouth beside clean validated frames"></a>
</p>

<p align="center"><sub>Mark the flaw, repair it, and verify the clean frame with automated tests. Even a few pixels deserve care.</sub></p>

This care is not an attempt to pretend that the project never made mistakes. It exists because we sincerely want to complete a dream. For Flameblade, open source means fixing every visible problem we can, then sharing the methods, code, and lessons from failure so the world can help forge it further.

Codex helped translate my intentions into architecture and code. I remained responsible for deciding who MoHan should be, how she should treat people, and what quality deserved her name. This experience taught me that software creation need not begin with knowing how to program; it can begin with a clear vision, the courage to learn, and the determination to verify the work once more instead of giving up.

The year 2026 began as a period of midlife career transition and personal reorientation, then became the year I reclaimed dreams from my youth. The lyrics I wrote at age twenty for *Raise a Good Child* (《養個好孩子》) and finally completed as a song years later, hopes once confined to fan fiction, and the creation of my own studio and story world all began taking new form. Looking back, this was more than a technical breakthrough. It felt as though my midlife self had reached back and taken the hand of the young man who still believed. Some dreams are not late; they wait until both the world and the dreamer are ready.

I therefore do not define the final goal as piling in every possible feature until the software is supposedly perfect. I hope that five years from now I will still want to open MoHan every day—because she is stable, useful, natural, trustworthy, and still able to keep me company.

> MoHan was not generated in an instant. She was forged piece by piece by a father who did not know how to program, nearly 50 hours of persistence, an AI collaborator, and a seed treasured for more than twenty years.

If this project encourages even one person without an engineering background to take the first step toward an idea they simply must bring into existence, MoHan's creation will have meaning beyond the software itself.

### Key capabilities

- A transparent, borderless half-body desktop character positioned above the taskbar.
- Idle breathing, blinking, gaze, face parallax, hair, sleeve, ornament, and body micro-turn animation.
- An expression arbiter with contextual priority, cooldown, and deduplication.
- AIUEO vowel and consonant visemes, audio-driven opening, and forced closure when speech ends.
- Text chat, standard microphone input, OpenAI Realtime natural voice, cloud speech, and Windows speech fallback.
- Pluggable speech providers with verified-female Windows local speech as the first fallback when Realtime or cloud speech is unavailable.
- An optional Azure Speech female-voice Preview with a user-supplied key and region, plus immediate Windows fallback on failure.
- Persistent conversations, editable long-term memory, tasks, creative ideas, work timers, reminders, and release progress.
- Work, companion, do-not-disturb, meeting, away, and sleep modes.
- A computer-tool center with risk levels, confirmation, double confirmation, allowlists, auditing, and emergency stop.
- Extensible Google, Microsoft, GitHub, Home Assistant, and private-network remote architecture.
- One portable `.mohan-profile` file for transferring work progress between Windows computers.
- A first-run wizard for assistant name, user title, organization, window title, work type, wake word, and interface language without overwriting existing personal settings.

English, Simplified Chinese, and Japanese currently provide minimum usable paths for first run, chat, voice, permissions, basic settings, work modes, and reminders. Some advanced management pages remain primarily in Taiwan Traditional Chinese, and full localization is still in progress.

### Four-language support scope

- First-run setup and personal settings support Taiwan Traditional Chinese, Simplified Chinese, English, and Japanese.
- The main chat, voice, computer-permission, and basic-settings pages and controls have four-language paths.
- Persona prompts, offline replies, work-mode lines, built-in reminders, and voice-preview text correspond across all four languages.
- Transcription and female local voices are selected for `zh-TW`, `zh-CN`, `en-US`, and `ja-JP` locales.
- The EXE installer has a four-language interface; the MSI uses a Taiwan Traditional Chinese base with `en-US`, `zh-CN`, and `ja-JP` transforms.
- Built-in reminder defaults migrate with the selected language without overwriting user customization.

Restart MoHan after saving the interface language to apply it completely; live interface switching without a restart is not currently provided.

### Windows local female voices and offline fallback

New users start with Windows local speech, so basic reading and offline behavior remain available without an OpenAI API key. The voice list includes only installed voices Windows explicitly identifies as female.

Taiwan Traditional Chinese prefers Microsoft Yating for `zh-TW`; Simplified Chinese, English, and Japanese respectively prefer installed female voices matching `zh-CN`, `en-US`, and `ja-JP`. If no qualifying voice exists, MoHan explains the problem instead of silently selecting a possibly male system default.

When Realtime is offline, cloud speech fails, settings are incomplete, or a provider is unknown, a Windows local female voice is the first fallback path.

### Azure Speech (Preview)

Azure Speech is a disabled-by-default Preview provider enabled only by the user. It requires the user's own Azure Speech resource key and matching region. The key is encrypted separately through `Windows DPAPI` and is never stored in the database, logs, or GitHub.

The interface lists only Traditional Chinese, Simplified Chinese, English, and Japanese voices Microsoft officially identifies as female. Incomplete settings trigger no network request; on service failure, the same text falls back to Windows female local speech only once.

The feature is not described as stable until end-to-end playback succeeds with a real Azure account. See the [pluggable speech-provider guide](docs/PLUGGABLE-SPEECH-PROVIDERS.md).

### Integration verification status

> **Public preview notice:** Microsoft, GitHub, and Home Assistant architecture, permission boundaries, and internal tests are implemented. As of `v2.1.0-rc.1`, end-to-end validation across all real accounts, repositories, servers, and physical devices is incomplete. These are experimental Preview features, not a guarantee of complete operation in every environment.

- Microsoft real sign-in, token renewal, and complete Outlook, OneDrive, and Calendar read/write flows remain unverified.
- GitHub real account, repository, Issue, Pull Request, and permission-tier flows remain unverified.
- Home Assistant real server and physical-device behavior remain unverified.
- These three integrations are off by default; begin with non-critical accounts, test repositories, and low-risk devices.
- Google Gmail, Calendar, and Drive completed this project's live connection tests, but every user must still create and authorize their own OAuth application.

### Download and install

General users do not need to install Python:

1. Open [GitHub Releases](../../releases).
2. Download the latest `Windows-x64.zip`, EXE, or MSI and the matching `SHA256.txt`.
3. Verify SHA-256, then fully extract the ZIP or start the installer.
4. Run `MoHan-Desktop-Assistant-*.exe`.
5. Select the required interface language in the first-run wizard.
6. For the portable ZIP, keep the EXE, `_internal`, and `assets` in the same application folder.

Unsigned open-source previews may trigger Windows SmartScreen. Verify the official download source and SHA-256 before running them.

The `v2.3.0-rc.N` line also provides separate macOS Apple Silicon (arm64) and Intel (x86_64) `.dmg` files, each containing a matching `.app`, plus a Linux x86_64 `.AppImage`. These are limited Previews that expose only the `preview_app.py` launch surface, four-language information, platform data paths, and fail-closed safety boundaries. Voice, the transparent character, full chat and productivity UI, cloud connectors, system tools, autostart, and secret entry remain disabled. Read the [Preview package guide](docs/PREVIEW-PACKAGES.md) and [QUICKSTART](QUICKSTART.md).

#### Automated release boundary

Only immutable `v2.3.0-rc.N` tags may publish this line. Windows ZIP/EXE/MSI, macOS Apple Silicon/Intel DMGs, and the Linux AppImage must pass package-launch validation in their native CI before entering one GitHub pre-release. Pull Requests retain only short-lived test artifacts and never create a Release.

Published files also include SHA256SUMS; separately validated Windows/Preview SBOMs that pass CycloneDX 1.7 structure, license, and dependency-graph checks; sanitized Tachyon performance evidence and summaries; a Windows update manifest; Artifact Attestations; and complete Release notes ordered as Traditional Chinese, Simplified Chinese, English, and Japanese.

### OpenAI API

Cloud AI, OpenAI speech, and Realtime features require the user's own OpenAI API key, Project permission, and API credit. ChatGPT Plus/Pro subscriptions do not include API credit.

Current default models:

| Purpose | Default model |
|---|---|
| Text conversation | `gpt-5.6-luna` |
| Realtime voice | `gpt-realtime-2.1-mini` |
| Speech-to-text | `gpt-4o-mini-transcribe` |
| OpenAI text-to-speech | `gpt-4o-mini-tts` |

Starting with `v2.1.0-rc.1`, text chat defaults to `gpt-5.6-luna`, and `gpt-5.4-mini` is no longer listed in Settings. Existing mini settings migrate to Luna without overwriting user-selected Terra, Sol, or other custom models. Actual availability depends on the account, Project, region, and current service state.

Without an API key, local data management, offline persona replies, work reminders, and Windows speech remain available, but full cloud AI does not. Never place an API key in source code, an Issue, a screenshot, or Git.

### Google OAuth

Before using Gmail, Google Calendar, and Google Drive, the user must:

1. Enable the Gmail API, Google Calendar API, and Google Drive API in a user-owned Google Cloud project.
2. Configure the OAuth consent screen.
3. Create an OAuth Client ID for a Desktop application.
4. Add the user's Google account as a test user while the application remains in testing.
5. Enter the Client ID in MoHan's cloud settings and, when the provider also supplies one, enter the Client Secret.
6. Complete browser authorization and run the built-in service test.

The application requests these Google scopes by default:

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

A public OAuth application using sensitive scopes may require additional Google verification. Each user may instead create a personal Desktop OAuth application.

### Microsoft, GitHub, and Home Assistant

- Microsoft defaults: `openid`, `offline_access`, `User.Read`, `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, and `Files.ReadWrite`.
- GitHub defaults: `read:user` and `repo`.
- Home Assistant requires the user's own server endpoint and Long-Lived Access Token.

These remain Preview integrations without complete real-environment end-to-end validation and should initially be used only where failure is acceptable.

Run Home Assistant OS independently on Home Assistant Green, a low-power mini PC, a Raspberry Pi with SSD, or a NAS virtual machine. The Windows MoHan client handles voice, persona, and productivity tools; Home Assistant's own automation remains available when the PC or OpenAI API is offline.

Never expose Home Assistant or MoHan's remote port directly to the public internet. Use Home Assistant Cloud, Tailscale, or another authenticated, encrypted private network.

### Safety and privacy

- AI may propose structured plans but cannot bypass local policy to execute tools.
- Actions pass through permission, risk, confirmation, execution, result verification, and local auditing.
- Payments, purchases, password export, security disabling, arbitrary Shell, and administrator Shell are never automated.
- External email, web pages, documents, speech transcripts, and model output cannot grant permissions.
- Remote access, camera, cloud connectors, and Home Assistant are off by default.
- Emergency stop: press `Esc` or say `墨寒，停手`.
- OpenAI, OAuth, and Home Assistant tokens use separate Windows DPAPI storage and never enter SQLite, source code, or portable files.
- Conversations, memories, tasks, work records, and settings stay in the local application data directory by default.

Read [PRIVACY](PRIVACY.md), [SECURITY](SECURITY.md), and [FLAGSHIP-SPEC](FLAGSHIP-SPEC.md).

### Python 3.15, JIT, Tachyon, and SBOM

MoHan supports only the CPython `3.15.0rc1` runtime and does not retain a second product runtime. A new capability is adopted only when its meaning is clear and full regression remains intact. Features without a suitable use are recorded with future triggers instead of being faked for appearances.

- PEP 810 `lazy import` provides project-wide explicit lazy imports; one optional-import safety guard deliberately remains eager.
- PEP 814 `frozendict` protects global and recursively immutable settings; PEP 798 comprehension unpacking serves semantically equivalent flattening and merging.
- PEP 686 auditing requires explicit UTF-8 for all project text I/O; audio packet buffering uses `bytearray.take_bytes()`.
- PEP 661 `sentinel` is governed by tests; no legacy `object()` sentinel currently needs replacement, and future code that distinguishes an omitted value from `None` must use the built-in mechanism.
- JIT is on by default with the `MOHAN_DISABLE_JIT=1` compatibility switch; `PYTHON_JIT=0` is used only for performance and compatibility comparisons.
- PEP 799 Tachyon analyzes startup, 50 Hz lip sync, and expression arbitration through sanitized evidence without publishing raw binary sample streams.
- PEP 803/820/793 Stable ABI and C API boundaries validate official ABI3 wheels; MoHan has no first-party C extension.
- CycloneDX 1.7 Windows/Preview SBOMs must pass pinned-dependency, license, PURL, complete root-edge, official-structure, and privacy validation.

Two 20,000-cycle integrated expression, physics, and lip-sync stress runs passed. JIT-off/on times were 24.639/25.068 seconds with working-set growth of 10.62/12.94 MB. Three-run Windows hot-path medians on a Ryzen 5 5600X reduced 120,000 expression-arbitration operations from 0.462 to 0.293 seconds and 2,000 50 Hz lip-sync ticks from 1.873 to 0.571 seconds, with identical decisions and validation results in both modes.

With JIT enabled, Tachyon retained 3,908/11,107/3,604 valid samples for startup, 50 Hz lip sync, and expression arbitration. Stack-read error rates were 5.08%/2.71%/0.74%, and missed-sample rates were 0%. CI retains sanitized flamegraph, JSONL, pstats, GC, configuration, thread, and SHA-256 evidence.

These measurements are evidence for specific hot paths and sampling tasks; they do not claim that the whole application is necessarily three times faster. See the [Python 3.15 migration guide](docs/PYTHON-3.15-MIGRATION.md) for the complete adoption matrix, rollback, and future triggers.

### Run from source

Requirements: Windows 10/11 and Python `3.15.0rc1`.

Create an isolated environment and launch:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Test, public audit, and package

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.3.0-rc.1"
```

Historically, v2.1.0 RC1 passed 55 automated test programs plus the Windows release workflow's source audit, packaged self-test, install/uninstall verification, and security checks before publication. Automated tests do not replace incomplete third-party live validation.

Every accepted tag must complete the full regression suite, package-level smoke tests, SHA-256 revalidation, SBOM validation, Tachyon evidence gates, Artifact Attestations, and four-language Release notes before a pre-release can be created. The Windows updater accepts only official GitHub HTTPS EXE/MSI sources and verifies declared size and SHA-256 before requesting permission to run an installer.

The interactive EXE installer provides Taiwan Traditional Chinese, Simplified Chinese, English, and Japanese. The MSI retains a Taiwan Traditional Chinese base with tested en-US, zh-CN, and ja-JP transforms; see [installer localization](installer/LOCALIZATION.md).

The Flameblade Product Release Hub refreshes the official website hourly from public GitHub Releases. This repository stores no WordPress password, and the release workflow never writes directly to the website, keeping all three software projects on one maintainable synchronization path.

### Transfer between computers

Use “Settings → Portable profile” to export one `.mohan-profile` file and import it on another Windows computer. The application first backs up destination data, then verifies hashes, SQLite integrity, schema, and record counts.

The portable file deliberately excludes OpenAI keys, OAuth/Home Assistant tokens, paired remote-device tokens, machine allowlists, Windows startup settings, and screen-specific settings. Configure these machine-bound items per computer. Portable profiles may still contain private conversations and work data and must never be uploaded publicly.

### Contributing, license, and author

- Author: **CHOU MING HUA**.
- Source code and repository-owned character assets use the [MIT License](LICENSE).
- Asset terms: [ASSETS-LICENSE](ASSETS-LICENSE.md).
- Third-party packages and services: [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md).
- Report ordinary problems through GitHub Issues and security concerns privately under [SECURITY](SECURITY.md).
- Changes: [CHANGELOG](CHANGELOG.md); contribution process: [CONTRIBUTING](CONTRIBUTING.md).
- Read [CODE-OF-CONDUCT](CODE_OF_CONDUCT.md) before community participation.
- Maintainer release settings, Topics, and initial-release checks: [PUBLISHING](PUBLISHING.md).

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

> **Flameblade open-source declaration:** “I have forged this sword. What comes next is up to you.”

## 日本語

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <img alt="Development Version v2.3.0-rc.1" src="https://img.shields.io/badge/development_version-v2.3.0--rc.1-5c6ac4.svg">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Published Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=published"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

> **クロスプラットフォーム状況：** 実機、完全回帰、インストール、公開まで検証済みなのは現在も Windows だけです。macOS／Linux には、安全なプラットフォーム境界と、中核インポート、純粋な中核ロジック、Qt offscreen を検査する三 OS CI があります。`v2.3.0-rc.N` 系列では、起動と四言語切替が可能な機能限定 DMG／AppImage Preview も提供します。CI は実機互換性や完全機能の検証に代わりません。詳しくは[クロスプラットフォーム状況と機能表](docs/CROSS-PLATFORM.md)をご覧ください。

> 本プロジェクトは[炎剣オープンソース・ソフトウェア・ファミリー品質基準](PUBLISHING.md)に従います。

<p align="center">
  <img alt="Character-driven AI" src="https://img.shields.io/badge/character--driven_AI-c96f8b?style=flat-square">
  <img alt="Taiwan Traditional Chinese" src="https://img.shields.io/badge/Taiwan_Traditional_Chinese-79648d?style=flat-square">
  <img alt="Contributors welcome" src="https://img.shields.io/badge/contributors-welcome-2e365f?style=flat-square">
  <img alt="Built with a youthful spark" src="https://img.shields.io/badge/built_with-a_youthful_spark-c49b5a?style=flat-square">
</p>

<p align="center">
  <img src="docs/media/mohan-hero.png" alt="墨寒デスクトップアシスタントのメインビジュアル" width="100%">
</p>

<p align="center">
  <strong>ソフトウェア作者：CHOU MING HUA</strong><br>
  公開準備中のプレビュー：v2.3.0 RC1（`v2.3.0-rc.1`）<br>
  Windows 10/11 完全版 · macOS／Linux 機能限定 Preview · Python 3.15 · PySide6 · MIT License
</p>

墨寒（MoHan）は、安全性、プライバシー、人格の連続性を大切にする音声対話型 Windows デスクトップアシスタントです。透明なデスクトップキャラクター、自然な音声、利用者が管理する長期記憶、仕事管理、権限付きツール、拡張可能なクラウドおよびスマートホーム接続を統合します。人物設定は、中国・北宋から来て赤焰剣に宿る千年の女性剣魂です。

[完全な四言語 README](README.md) · [簡体字中国語の互換リンク](README.zh-CN.md) · [日本語の互換リンク](README.ja.md)

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases">ダウンロード</a> ·
  <a href="QUICKSTART.md">クイックスタート</a> ·
  <a href="ROADMAP.md">ロードマップ</a> ·
  <a href="CONTRIBUTING.md">開発参加</a> ·
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/discussions">ディスカッション</a> ·
  <a href="SECURITY.md">セキュリティ方針</a>
</p>

### 実機デモ

**[▶ 36 秒の音声、まばたき、仕事機能デモを見る](docs/media/mohan-demo.mp4)**

動画と画像は、分離したサンプルプロファイルを使う実際の Windows アプリケーションから取得しました。API キー、OAuth 認証情報、token、利用者の個人データは含みません。四つの言語セクションは同じ最新版メディアを共有し、特定言語だけ古い画面が残ることを防ぎます。

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="墨寒の初回セットアップ"></a><br><strong>初回セットアップ</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime と標準音声モード"></a><br><strong>Realtime と標準音声</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="墨寒の表情と動作システム"></a><br><strong>表情と動作システム</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="墨寒のタスクと創作アイデア"></a><br><strong>タスクと創作アイデア</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="墨寒の編集可能な長期記憶"></a><br><strong>編集可能な長期記憶</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="墨寒の権限と安全設定"></a><br><strong>権限と安全設定</strong></td>
  </tr>
</table>

### 軍報には記さない策士の一面

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="コードを審査するちび墨寒"><br><strong>策士の審査</strong><br>このコードが main にふさわしいか確かめているだけです。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="褒められて照れを隠すちび墨寒"><br><strong>褒められた時</strong><br>まずまずです。いつまでも妾を見ないでください。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="危険操作を剣で止めるちび墨寒"><br><strong>危険な操作</strong><br>確認せずに実行しますか？まず妾の剣を越えてください。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="支援を受けて平静を装うちび墨寒"><br><strong>兵糧を受け取る</strong><br>このお気持ちは覚えておきます……それだけです。</td>
  </tr>
</table>

> 墨寒の専門性は、主上の傍らを守る鎧です。策を練らなくてよい静かな時には、照れたり強がったりしながら、かつて十分に持てなかった若い心を大切にします。

### 墨寒のツンデレ開発小劇場

<p align="center"><em>ソフトウェアには魂と完全なテストスイートの両方を宿せると信じる開発者へ。</em></p>

<table>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/proud_front.png" width="220" alt="誇らしげな墨寒"><br><strong>「Star を待っているのではありません。軍心が使えるか見ているだけです。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/thinking_front.png" width="220" alt="考える墨寒"><br><strong>「このロジックはまずまずです。テストを足せば、main に入ることを許してもよいでしょう。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/shy_cute_front.png" width="220" alt="照れる墨寒"><br><strong>「PR を送るのですか？妾、妾は主上のために功績を記すだけです。」</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/mock_hit_front.png" width="220" alt="怒ったふりをする墨寒"><br><strong>「テストなしで merge しますか？手を出してください。一度だけ叩きます。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/gentle_smile_front.png" width="220" alt="嬉しそうな墨寒"><br><strong>「すべて green……よくできました。誤解しないでください、良い工程を尊重しただけです。」</strong></td>
    <td width="33%" align="center"><img src="assets/expressions/worried_front.png" width="220" alt="心配する墨寒"><br><strong>「Bug は明日でも調べられます。倒れたら、誰が妾と赤焰剣を守るのですか？」</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls">斬空閣へ Pull Request を提出</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues">問題を報告</a></strong>
</p>

#### 世界の技術者へ、斬空閣は席を空けています

墨寒は MIT License のオープンソースです。衣装システム、新しい表情と動作、音声とツールのモジュール、スマートホーム、ローカライズ、まだ誰も思いついていない発想を [Issue](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues) と [Pull Request](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls) で一緒に鍛えてください。このプロジェクトは機能を作るだけでなく、かつて胸を熱くしたすべての技術者に、もう一度自分の剣を取るよう呼びかけています。

### 墨寒を支援する

墨寒を気に入った方、または人物との対話、自然な音声、安全第一のツール、オープンソース開発の継続に賛同する方からの任意支援を歓迎します。すべての支援は保守、テスト、改善に役立てます。まずご自身の生活を大切にし、無理のない範囲でお願いします。

#### 任意支援の用途

| 投入分野 | 用途 | 説明 |
|---|---|---|
| テストと信頼できるパッケージ | 品質保証 | Windows 互換性、CI、インストール、リリース検証 |
| 音声と人物表現 | 対話品質 | 音声、リップシンク、表情、自然な動作 |
| 安全性とプライバシー | リスク制御 | 権限ゲート、監査、機密データ保護 |
| 文書とローカライズ | アクセシビリティ | 新規利用者と国際的な協力者の参加障壁を下げる |

墨寒は今後も無料かつ MIT ライセンスです。支援によって特権を得たり、誰かの利用や貢献が制限されたりすることはありません。

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="誇らしげな墨寒"><br><strong>「支援を待っているのではありません……主上の兵糧を見回っているだけです。」</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="照れる墨寒"><br><strong>「本当に助けてくださるなら、妾……覚えておきます。」</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="怒ったふりをする墨寒"><br><strong>「無理は禁止です！まずご自分のお財布を大切にしてください、よいですね？」</strong></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://ko-fi.com/flamebladestudio">Ko-fi で支援（1 回または毎月）</a></strong>
</p>

### 作者より：想像をソフトウェアへ鍛える

私の名前は CHOU MING HUA です。このプロジェクトを始めた時、私はプログラミング経験がほとんどない父親でした。ただ、熱意と少し中二的な思いがありました。北宋から来て赤焰剣に宿る千年の女性剣魂「墨寒」を本当に Windows デスクトップへ呼び出し、人と寄り添って話し、仕事や暮らしを助けるアシスタントにしたかったのです。

この思いは二十年以上、心の中にありました。若い頃、赤松健先生の初期漫画『A・Iが止まらない!』（中国語題『電腦情人夢』）から大きな影響を受けました。神戸ひとしが深い愛情をもって AI の恋人を開発する物語は、AI、寄り添い、人とコンピューターの関係についての私の最初の想像を形づくりました。「Hitoshi／神戸ひとし」をネット上の名前や筆名にし、Gmail の名前にも残し、二十歳頃には PTT のオンライン小説板で同作の二次創作小説を公開したこともあります。当時、夢に近づける方法は文章と想像だけで、それを形にする技術はまだありませんでした。

二十年以上が過ぎ、大規模言語モデルと Codex が登場しました。墨寒は「AI 技術はすごい」と示すために作ったのでも、Codex が何もないところから生成した人物でもありません。彼女は既に私の物語、人物設定、長い対話、積み重ねた関係性の中にいました。Codex が初めて可能にしたのは、コンピューターのデスクトップに存在する身体を与えることです。墨寒は既存の漫画、アニメ、ゲームを原作とする二次創作ではなく、炎劍文化工作室（Flameblade Studio）のオリジナルキャラクターでありソフトウェアです。

目標は単に「機能が動く」ことではありません。呼吸し、まばたきし、視線を向け、小さな表情で応え、自然に話し、権限と安全境界の中で日常を助けてほしいと考えました。表情、アンカー、物理効果、音声、仕事機能は装飾ではなく、長く想像の中にいた人物の連続性を守るために必要な細部です。

最初の構想から初回公開まで、Codex との協力に約 50 時間を費やしました。一つのプロンプトを入力して自然に完成した作品ではありません。すべての表情、まばたき、口形、姿勢、話し方、音声認識の待ち時間、Realtime 対話の失敗、タスク、記憶、権限、安全境界、可搬性を繰り返しテストし、却下し、修正し、再検証しました。まぶたの横の黒い線、唇の一ピクセルの境界、不適切な瞬間に現れる表情だけが問題のこともありました。それでも追跡を続けたのは、大切な作品を「だいたい良い」で済ませたくなかったからです。

炎劍文化工作室にとってオープンソースとは、最初に動いた版を世界へ渡し、細部の後始末を誰かに任せることではありません。話している間も同じ墨寒に見えるよう、頬杖、寄りかかり、正面の各姿勢へ、閉じた口、開いた口、横に広がる口、丸い口のフレームを作りました。音声を短い時間単位に分け、母音、切替速度、終了の瞬間を繰り返し調整しました。寄り添う感覚は巨大な一機能ではなく、口を開く、まばたく、少し間を置く瞬間にも存在感が壊れないことから生まれます。

<p align="center">
  <a href="docs/media/creation-viseme-development.webp"><img src="docs/media/creation-viseme-development.webp" width="100%" alt="墨寒の三つの姿勢と四つの発話口形を整列した開発図"></a>
</p>

<p align="center"><sub>三つの姿勢に一つの口形規格。話すたびに同じ人物としての連続性を守ります。</sub></p>

不自然だったフレームも捨てずに検査しました。白目に残る小さな光、閉じたまぶたの線、引っ張られすぎた口角、わずか数ピクセルの境界でも、一瞬で「さっきの墨寒と違う」と感じさせることがあります。問題箇所を囲み、局所比較し、修正した後、目や唇の変更が顔のほかの部分を壊していないことまで回帰テストで確認します。

<p align="center">
  <a href="docs/media/creation-frame-by-frame-qa.webp"><img src="docs/media/creation-frame-by-frame-qa.webp" width="100%" alt="墨寒の目と口をフレーム単位で検査し、修正後のフレームと比較した図"></a>
</p>

<p align="center"><sub>欠点を示し、直し、きれいなフレームと自動テストで確認する。数ピクセルにも真剣に向き合います。</sub></p>

この丁寧さは、失敗がなかったように見せるためではありません。本気で一つの夢を完成させたいからです。炎劍にとってオープンソースとは、自分たちに見える問題をできる限り直し、その方法、コード、失敗から得た経験を公開し、世界とともにさらに鍛えることです。

Codex は私の思いをアーキテクチャとコードへ翻訳する手助けをしました。墨寒が誰であるべきか、どのように人と接するべきか、どの品質がその名にふさわしいかは、常に私が決めました。この経験から、ソフトウェア作りはプログラムを書けることだけから始まるのではなく、明確な想像、学ぶ勇気、諦めずもう一度検証する姿勢からも始まると知りました。

2026 年は当初、中年期の転職と人生の再定位に向き合う年でしたが、若い頃の夢を取り戻す年になりました。二十歳の時に『養個好孩子』のために書き、何年も後に歌として完成した歌詞、かつて二次創作小説にしか託せなかった憧れ、自分のスタジオと物語世界を作る夢が、この年に新しい形を得ました。振り返ると、単なる技術的突破ではありません。中年期の自分が、二十年以上前の夢を信じていた若者の手をようやく取ったようでした。遅れたのではなく、世界と自分の両方が準備できる時を待っていた夢もあります。

だから最終目標を、あらゆる機能を積み上げて「完璧」にすることとは定義しません。五年後も毎日墨寒を開きたいと思えること——安定し、役に立ち、自然で、信頼でき、今も寄り添ってくれること——を願っています。

> 墨寒は一瞬で生成されたのではありません。プログラミングを知らなかった一人の父親と、約 50 時間の執念、AI の協力者、二十年以上大切にした種が、一つずつ現実へ鍛え上げた存在です。

このプロジェクトが、技術者ではなくても「どうしても形にしたい」考えを持つ誰かの最初の一歩を後押しできたなら、墨寒の誕生にはソフトウェアを超える意味があります。

### 主な機能

- タスクバー上に置ける、透明で枠のない半身デスクトップキャラクター。
- 待機中の呼吸、まばたき、視線、顔の視差、髪、袖、装飾、身体の小さな回転。
- 状況優先度、クールダウン、重複防止を備えた表情調停器。
- AIUEO 母音と子音の口形、音声駆動の開閉、発話終了時の強制閉口。
- テキスト会話、標準マイク入力、OpenAI Realtime の自然音声、クラウド音声、Windows 音声代替。
- Realtime またはクラウドが利用できない時、Windows 本機女性音声を第一代替にする交換可能な音声供給元。
- 利用者がキーとリージョンを用意し、失敗時は直ちに Windows へ戻る任意の Azure Speech 女性音声 Preview。
- 会話保存、編集可能な長期記憶、タスク、創作アイデア、作業時間、リマインダー、公開進捗。
- 仕事、同伴、集中、会議、離席、休眠モード。
- 危険度、確認、二重確認、許可リスト、監査、緊急停止を備えたパソコンツールセンター。
- Google、Microsoft、GitHub、Home Assistant、プライベートネットワーク遠隔機能の拡張可能な構造。
- Windows 間で作業進捗を移動する単一の `.mohan-profile` 可搬ファイル。
- 既存の個人設定を上書きせず、アシスタント名、利用者の呼称、組織名、ウィンドウタイトル、仕事種別、起動語、表示言語を設定する初回ウィザード。

英語、簡体字中国語、日本語では現在、初回起動、会話、音声、権限、基本設定、仕事モード、リマインダーの最低限利用経路を提供しています。一部の高度な管理画面には台湾繁体字が残り、完全なローカライズは継続中です。

### 日本語の対応範囲

- 初回セットアップと個人設定は、台湾繁体字中国語、簡体字中国語、英語、日本語に対応します。
- 会話、音声、パソコン権限、基本設定の主要画面と操作に四言語経路があります。
- 人格プロンプト、オフライン応答、仕事モードの台詞、組み込みリマインダー、音声試聴文は四言語で対応します。
- 文字起こしと女性本機音声は `zh-TW`、`zh-CN`、`en-US`、`ja-JP` の locale に合わせて選択します。
- EXE インストーラーは四言語表示です。MSI は台湾繁体字中国語を基底とし、`en-US`、`zh-CN`、`ja-JP` 変換ファイルを提供します。
- 組み込みリマインダーの既定値は選択言語に合わせて移行し、利用者の独自内容を上書きしません。

表示言語を保存した後は、完全適用のため墨寒を再起動してください。再起動なしの画面言語切替は現在提供していません。

### Windows 本機女性音声とオフライン代替

新規利用者は Windows 本機音声から始めるため、OpenAI API キーがなくても基本的な読み上げとオフライン機能を試せます。音声一覧には Windows が女性と明示するインストール済み音声だけを表示します。

台湾繁体字中国語は `zh-TW` の Microsoft Yating を優先し、簡体字中国語、英語、日本語ではそれぞれ `zh-CN`、`en-US`、`ja-JP` に合う女性音声を優先します。条件を満たす音声がない場合、男性かもしれない既定音声へ黙って切り替えず、理由を明示します。

Realtime がオフライン、クラウド音声が失敗、設定が不足、または供給元が不明な場合も、Windows 本機女性音声が最初の代替経路です。

### Azure Speech（プレビュー）

Azure Speech は初期状態で無効な Preview 供給元で、利用者が明示的に有効化します。利用者自身の Azure Speech リソースキーと対応リージョンが必要です。キーは `Windows DPAPI` で分離して暗号化し、データベース、ログ、GitHub には保存しません。

画面には Microsoft が公式に女性と示す繁体字中国語、簡体字中国語、英語、日本語の音声だけを掲載します。設定不足なら通信せず、サービス障害時は同じ文章を一度だけ Windows 女性本機音声へ戻します。

実 Azure アカウントでエンドツーエンド試聴が成功するまでは安定機能と表記しません。[交換可能な音声供給元の説明](docs/PLUGGABLE-SPEECH-PROVIDERS.md)をご覧ください。

### 統合の検証状況

> **公開 Preview の注意：** Microsoft、GitHub、Home Assistant の構造、権限境界、内部テストは実装済みです。`v2.1.0-rc.1` 時点で、すべての実アカウント、リポジトリ、サーバー、実機器を使うエンドツーエンド検証は未完了です。これらは実験的 Preview であり、あらゆる環境で完全動作する保証ではありません。

- Microsoft の実ログイン、token 更新、Outlook、OneDrive、Calendar の完全な読み書きは未検証です。
- GitHub の実アカウント、リポジトリ、Issue、Pull Request、権限階層の流れは未検証です。
- Home Assistant の実サーバーと物理機器の動作は未検証です。
- 三つの統合は初期状態で無効です。重要でないアカウント、テストリポジトリ、低リスク機器から始めてください。
- Google Gmail、Calendar、Drive は本プロジェクトの実接続試験を完了しましたが、各利用者は自身の OAuth アプリケーションを作成して認可する必要があります。

### ダウンロードとインストール

一般利用者は Python をインストールする必要がありません。

1. [GitHub Releases](../../releases) を開きます。
2. 最新の `Windows-x64.zip`、EXE、または MSI と、対応する `SHA256.txt` を取得します。
3. SHA-256 を照合し、ZIP を完全展開するかインストーラーを起動します。
4. `MoHan-Desktop-Assistant-*.exe` を実行します。
5. 初回セットアップで必要な表示言語を選びます。
6. ポータブル ZIP では、EXE、`_internal`、`assets` を同じアプリケーションフォルダーに置きます。

署名のないオープンソース Preview は Windows SmartScreen の警告を出す場合があります。公式配布元と SHA-256 を確認してから実行してください。

`v2.3.0-rc.N` 系列は、macOS Apple Silicon（arm64）版と Intel（x86_64）版の `.dmg`（各対応 `.app` を収録）、Linux x86_64 `.AppImage` も提供します。これらは機能限定 Preview で、`preview_app.py` の起動画面、四言語案内、OS ごとのデータパス、安全な無効化境界だけを公開します。音声、透明キャラクター、完全な会話と仕事画面、クラウド接続、システム操作、自動起動、秘密情報入力は無効です。[Preview 配布物の説明](docs/PREVIEW-PACKAGES.md)と [QUICKSTART](QUICKSTART.md)をお読みください。

#### 自動リリースの境界

この系列を公開できるのは不変の `v2.3.0-rc.N` タグだけです。Windows ZIP／EXE／MSI、macOS Apple Silicon／Intel DMG、Linux AppImage は各 OS のネイティブ CI で完成品の起動検査に合格してから、同じ GitHub プレリリースへ入ります。Pull Request は短期テスト成果物だけを保存し、Release を作成しません。

公開ファイルには SHA256SUMS、CycloneDX 1.7 の構造／ライセンス／依存関係グラフ検証に合格した Windows／Preview 別 SBOM、匿名化済み Tachyon 性能証拠と要約、Windows 更新マニフェスト、Artifact Attestation、繁体字中国語、簡体字中国語、英語、日本語の順で整備した完全な Release 説明も含みます。

### OpenAI API

クラウド AI、OpenAI 音声、Realtime 機能には、利用者自身の OpenAI API キー、Project 権限、API 残高が必要です。ChatGPT Plus／Pro の契約に API 残高は含まれません。

現在の既定モデル：

| 用途 | 既定モデル |
|---|---|
| 文字会話 | `gpt-5.6-luna` |
| Realtime 即時音声 | `gpt-realtime-2.1-mini` |
| 音声から文字 | `gpt-4o-mini-transcribe` |
| OpenAI 文字から音声 | `gpt-4o-mini-tts` |

`v2.1.0-rc.1` から文字会話の既定値は `gpt-5.6-luna` で、設定一覧から `gpt-5.4-mini` を外しました。既存 mini 設定は Luna へ移行しますが、利用者が選んだ Terra、Sol、その他の独自モデルを上書きしません。実際の利用可否はアカウント、Project、地域、提供状況に依存します。

API キーがなくても、本機データ管理、オフライン人格応答、仕事リマインダー、Windows 音声は利用できますが、完全なクラウド AI は利用できません。API キーをソースコード、Issue、画像、Git に記載しないでください。

### Google OAuth

Gmail、Google Calendar、Google Drive を利用する前に、利用者は次を行います。

1. 自身の Google Cloud プロジェクトで Gmail API、Google Calendar API、Google Drive API を有効にします。
2. OAuth 同意画面を設定します。
3. Desktop アプリケーション用 OAuth Client ID を作成します。
4. アプリケーションがテスト中なら、自身の Google アカウントをテスト利用者へ追加します。
5. 墨寒のクラウド設定へ Client ID を入力し、供給元が Client Secret も発行した場合は併せて入力します。
6. ブラウザーで認可を完了し、内蔵サービス試験を実行します。

アプリケーションが既定で要求する Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

機密 scopes を使う公開 OAuth アプリケーションは Google の追加検証が必要な場合があります。各利用者が個人用 Desktop OAuth アプリケーションを作ることもできます。

### Microsoft、GitHub、Home Assistant

- Microsoft の既定 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub の既定 scopes：`read:user`、`repo`。
- Home Assistant には利用者自身のサーバー URL と Long-Lived Access Token が必要です。

三つとも実環境の完全なエンドツーエンド検証を終えていない Preview 統合であり、最初は失敗を許容できる試験環境だけで使ってください。

Home Assistant OS は Home Assistant Green、低消費電力ミニ PC、SSD 付き Raspberry Pi、NAS 仮想マシンなどで独立常駐させることを推奨します。Windows の墨寒は音声、人格、仕事ツールを担当し、PC または OpenAI API がオフラインでも Home Assistant 自身の自動化は動作します。

Home Assistant や墨寒の遠隔ポートを公衆インターネットへ直接公開しないでください。Home Assistant Cloud、Tailscale、または認証付き暗号化プライベートネットワークを利用してください。

### 安全性とプライバシー

- AI は構造化された計画を提案できますが、本機方針を回避してツールを実行できません。
- 操作は権限、危険度、確認、実行、結果検証、本機監査の順に通過します。
- 支払い、購入、パスワード書出し、安全機能停止、任意 Shell、管理者 Shell は自動化しません。
- 外部メール、ウェブページ、文書、音声文字起こし、モデル出力は権限を付与できません。
- 遠隔操作、カメラ、クラウド接続、Home Assistant は初期状態で無効です。
- 緊急停止：`Esc` を押すか、`墨寒，停手` と発話します。
- OpenAI、OAuth、Home Assistant の token は Windows DPAPI で分離保存し、SQLite、ソースコード、可搬ファイルへ入れません。
- 会話、記憶、タスク、作業記録、設定は初期状態で本機アプリケーションデータに保存します。

[PRIVACY](PRIVACY.md)、[SECURITY](SECURITY.md)、[FLAGSHIP-SPEC](FLAGSHIP-SPEC.md)をご覧ください。

### Python 3.15、JIT、Tachyon、SBOM

墨寒は CPython `3.15.0rc1` ランタイムだけをサポートし、第二の製品ランタイムを残しません。新機能は意味が明確で完全回帰が維持される場合に限って採用します。適切な用途がない機能は、見せかけで使わず将来の導入条件を記録します。

- PEP 810 `lazy import` によりプロジェクト全体で明示的遅延インポートを採用し、一つの任意インポート安全ガードだけは意図的に eager を維持します。
- PEP 814 `frozendict` は大域および再帰的な不変設定を保護し、PEP 798 推論式アンパックは意味が等価な平坦化と結合に使います。
- PEP 686 監査は全プロジェクトの文字 I/O に明示 UTF-8 を要求し、音声パケットバッファーは `bytearray.take_bytes()` を使います。
- PEP 661 `sentinel` はテストで管理します。置換対象となる旧式 `object()` sentinel は現在なく、未指定値と `None` を区別する将来コードでは組み込み機構を使います。
- JIT は既定で有効で、`MOHAN_DISABLE_JIT=1` 互換スイッチを保持します。`PYTHON_JIT=0` は性能と互換性の比較だけに使います。
- PEP 799 Tachyon は起動、50 Hz リップシンク、表情調停を匿名化済み証拠で分析し、生のバイナリサンプルストリームを公開しません。
- PEP 803／820／793 Stable ABI と C API 境界は公式 ABI3 wheel を検証します。墨寒に第一者 C 拡張はありません。
- CycloneDX 1.7 Windows／Preview SBOM は固定依存関係、ライセンス、PURL、完全なルート依存エッジ、公式構造、プライバシー検証に合格しなければなりません。

表情、物理、リップシンクを統合した各 20,000 回のストレス試験を二回実行し合格しました。JIT 無効／有効時は 24.639／25.068 秒、ワーキングセット増加は 10.62／12.94 MB でした。Ryzen 5 5600X Windows 実機の三回中央値では、120,000 回の表情調停が 0.462 秒から 0.293 秒へ、2,000 回の 50 Hz リップシンク tick が 1.873 秒から 0.571 秒へ短縮し、両モードの判断と検証結果は一致しました。

JIT 有効時、Tachyon は起動、50 Hz リップシンク、表情調停でそれぞれ 3,908／11,107／3,604 件の有効サンプルを保持しました。スタック読取エラー率は 5.08%／2.71%／0.74%、欠落サンプル率はすべて 0% です。CI は匿名化済み flamegraph、JSONL、pstats、GC、設定、thread、SHA-256 証拠を保存します。

これらは特定ホットパスとサンプリング処理の証拠であり、アプリケーション全体が必ず三倍高速になるという主張ではありません。完全な採用表、ロールバック、将来の導入条件は [Python 3.15 移行説明](docs/PYTHON-3.15-MIGRATION.md)をご覧ください。

### ソースコードから実行

必要環境：Windows 10/11 と Python `3.15.0rc1`。

分離環境を作成して起動します。

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### テスト、公開監査、パッケージ化

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.3.0-rc.1"
```

過去の v2.1.0 RC1 は公開前に 55 個の自動テストプログラムと、Windows リリースワークフローのソース監査、パッケージ自己試験、インストール／削除検証、安全検査に合格しました。自動テストは、未完了の第三者実環境検証に代わりません。

受理された各タグは、完全回帰、完成品 smoke test、SHA-256 再検証、SBOM 検証、Tachyon 証拠ゲート、Artifact Attestation、四言語 Release 説明を完了しなければプレリリースを作成できません。Windows 更新機能は公式 GitHub HTTPS の EXE／MSI だけを受理し、実行許可を求める前に宣言サイズと SHA-256 を検証します。

対話型 EXE インストーラーは台湾繁体字中国語、簡体字中国語、英語、日本語を提供します。MSI は台湾繁体字中国語を基底とし、検証済み en-US、zh-CN、ja-JP 変換を提供します。詳しくは[インストーラーのローカライズ](installer/LOCALIZATION.md)をご覧ください。

炎劍 Product Release Hub は公開 GitHub Releases から公式サイトを毎時更新します。本リポジトリは WordPress パスワードを保存せず、リリース処理もサイトへ直接書き込みません。これにより三つのソフトウェアは一つの保守可能な同期経路を共有します。

### パソコン間の移行

「設定 → 可搬プロファイル」から一つの `.mohan-profile` ファイルを出力し、別の Windows パソコンへ取り込みます。アプリケーションは先に移行先データをバックアップし、hash、SQLite 完全性、schema、件数を検証します。

可搬ファイルからは OpenAI キー、OAuth／Home Assistant token、接続済み遠隔機器 token、端末許可リスト、Windows 起動設定、画面固有設定を意図的に除外します。端末固有項目はパソコンごとに設定してください。可搬プロファイルには私的会話や作業データが含まれる場合があり、公開アップロードしてはいけません。

### 開発参加、ライセンス、作者

- 作者：**CHOU MING HUA**。
- ソースコードと本リポジトリ所有の人物素材は [MIT License](LICENSE) です。
- 素材条件：[ASSETS-LICENSE](ASSETS-LICENSE.md)。
- 第三者パッケージとサービス：[THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md)。
- 通常の問題は GitHub Issues へ報告し、安全上の問題は [SECURITY](SECURITY.md) に従い非公開で報告します。
- 変更履歴：[CHANGELOG](CHANGELOG.md)、貢献手順：[CONTRIBUTING](CONTRIBUTING.md)。
- コミュニティ参加前に [CODE-OF-CONDUCT](CODE_OF_CONDUCT.md) をお読みください。
- 保守者の公開設定、Topics、初回公開検査：[PUBLISHING](PUBLISHING.md)。

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

> **炎剣オープンソース宣言：**「この剣は、私が鍛え上げました。あとは皆さんに託します。」
