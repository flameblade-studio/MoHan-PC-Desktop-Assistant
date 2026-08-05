# MoHan Desktop Assistant / 墨寒桌面語音互動虛擬助理

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=release"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.14" src="https://img.shields.io/badge/Python-3.14-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

> **跨平台進度：** Windows 仍是唯一完成實機、完整回歸、安裝與發布驗證的
> 平台。macOS／Linux 目前只建立安全的平台邊界，並以三系統 CI 驗證核心匯入、
> 純核心邏輯及 Qt offscreen；不能把 CI 當成真機相容證明。能力矩陣與後續步驟
> 請見 [跨平台狀態文件](docs/CROSS-PLATFORM.md)。

> 本專案遵循[炎劍開源軟體家族品質標準](PUBLISHING.md)。

<p align="center">
  <img alt="Character-driven AI" src="https://img.shields.io/badge/character--driven_AI-c96f8b?style=flat-square">
  <img alt="Taiwan Traditional Chinese" src="https://img.shields.io/badge/Taiwan_Traditional_Chinese-79648d?style=flat-square">
  <img alt="Contributors welcome" src="https://img.shields.io/badge/contributors-welcome-2e365f?style=flat-square">
  <img alt="Built with a youthful spark" src="https://img.shields.io/badge/built_with-a_youthful_spark-c49b5a?style=flat-square">
</p>

<p align="center">
  <img src="docs/media/mohan-hero.png" alt="MoHan Desktop Assistant main visual / 墨寒桌面語音互動虛擬助理主視覺" width="100%">
</p>

<p align="center">
  <strong>Author / 軟體作者：CHOU MING HUA</strong><br>
  Current public preview / 目前公開預覽版：v2.1.0 RC1 (v2.1.0-rc.1)<br>
  Windows 10/11 · Python 3.14 · PySide6 · MIT License
</p>

> 墨寒是一套重視安全、隱私與角色連續感的 Windows 語音互動桌面助理，
> 結合透明桌面角色、自然語音、長期記憶、工作管理、權限控管工具，以及
> 可擴充的雲端與智慧家庭連接器。

> MoHan is a safety-first, voice-interactive Windows desktop companion combining
> an animated character, natural voice, user-controlled long-term memory,
> productivity workflows, permission-gated tools, and extensible cloud and
> smart-home connectors.

- [繁體中文](#繁體中文)
- [简体中文](README.zh-CN.md)
- [English](#english)
- [日本語](README.ja.md)

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases">Download / 下載</a> ·
  <a href="QUICKSTART.md">Quick start / 快速開始</a> ·
  <a href="ROADMAP.md">Roadmap / 路線圖</a> ·
  <a href="CONTRIBUTING.md">Contribute / 參與協作</a> ·
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/discussions">Discussions / 討論區</a> ·
  <a href="SECURITY.md">Security / 安全</a>
</p>

## Demo / 實際展示

**[▶ Watch the 36-second voice, blink and productivity demo / 觀看 36 秒語音、眨眼與工作展示影片](docs/media/mohan-demo.mp4)**

The demo and screenshots below were captured from the real Windows application
with an isolated sample profile. They contain no API keys, OAuth credentials,
tokens, or private user data.

以下影片與截圖均由實際 Windows 程式及隔離的示範設定檔擷取，不含 API
金鑰、OAuth 憑證、權杖或使用者私人資料。

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="First-run setup wizard / 首次設定精靈"></a><br><strong>First-run wizard / 首次設定精靈</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime and standard voice modes / Realtime 與一般語音模式"></a><br><strong>Realtime & standard voice / Realtime 與一般語音</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="Expression system / 表情系統"></a><br><strong>Expression system / 表情系統</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="Tasks and ideas / 待辦與創作靈感"></a><br><strong>Tasks & ideas / 待辦與創作靈感</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="Long-term memory / 長期記憶"></a><br><strong>Editable memory / 可編輯長期記憶</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="Safety permissions / 安全權限"></a><br><strong>Permission-gated tools / 權限控管工具</strong></td>
  </tr>
</table>

## 策士也有不寫進軍報的一面 / Off-duty Strategist Theatre

<table>
  <tr>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Q 版墨寒審查程式"><br><strong>策士審查 · Code review</strong><br>妾只是確認這段程式碼配不配入主分支。<br><sub>Reviewing whether this code deserves a place on main.</sub></td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Q 版墨寒被稱讚後害羞嘴硬"><br><strong>被稱讚時 · When praised</strong><br>做得尚可。別一直盯著妾看。<br><sub>Accepting praise—strictly for engineering quality.</sub></td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Q 版墨寒拔劍阻止危險操作"><br><strong>危險操作 · Dangerous action</strong><br>未經確認便想執行？先過妾這一劍。<br><sub>Dangerous actions still require explicit approval.</sub></td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Q 版墨寒收到贊助後故作鎮定"><br><strong>收到軍糧 · Provisions received</strong><br>妾會記下這份心意……僅此而已。<br><sub>Voluntary support is remembered, never required.</sub></td>
  </tr>
</table>

> 墨寒的專業是她守在主上身旁的鎧甲；在無須籌謀的片刻，她仍會害羞、
> 嘴硬，也會珍惜那些從未真正擁有過的年輕心事。
>
> MoHan's professionalism is the armor of a thousand-year-old strategist. In
> quieter moments, she still blushes, hides tenderness behind pride, and keeps
> the youthful heart she never had the chance to fully live.

## 墨寒的傲嬌工程小劇場 / MoHan's Tsundere Developer Theatre

<p align="center">
  <em>相信軟體可以同時擁有靈魂與完整測試的開發者小劇場。<br>
  A tiny strategist's theatre for developers who believe software can have both a soul and a test suite.</em>
</p>

<table>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/proud_front.png" width="220" alt="墨寒傲嬌"><br><strong>「妾才沒有等你的 Star，只是在確認軍心是否可用。」</strong><br><sub>“I am not waiting for your Star. I am merely assessing morale.”</sub></td>
    <td width="33%" align="center"><img src="assets/expressions/thinking_front.png" width="220" alt="墨寒思考"><br><strong>「這段邏輯尚可。若再補上測試，妾便勉強准它入主分支。」</strong><br><sub>“The logic is acceptable. Add tests, and I may permit it onto main.”</sub></td>
    <td width="33%" align="center"><img src="assets/expressions/shy_cute_front.png" width="220" alt="墨寒嬌羞"><br><strong>「你願意送來 PR？妾、妾只是替主上記下功勞。」</strong><br><sub>“A pull request? I am only recording your service for my lord.”</sub></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="assets/expressions/mock_hit_front.png" width="220" alt="墨寒佯怒"><br><strong>「未經測試便想合併？手伸出來。妾只敲一下。」</strong><br><sub>“Merge without tests? Your hand, please. Just one tap.”</sub></td>
    <td width="33%" align="center"><img src="assets/expressions/gentle_smile_front.png" width="220" alt="墨寒開心"><br><strong>「全數綠燈……做得好。別誤會，妾只是尊重好工程。」</strong><br><sub>“All checks green. Well done—not that I am impressed, of course.”</sub></td>
    <td width="33%" align="center"><img src="assets/expressions/worried_front.png" width="220" alt="墨寒關心"><br><strong>「Bug 可以明日再查。你若累倒，誰來陪妾守著赤焰劍？」</strong><br><sub>“The bug can wait until tomorrow. Do not make your strategist worry.”</sub></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls">向斬空閣呈上 PR / Contribute a pull request</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues">回報軍情 / Open an issue</a></strong>
</p>

### 天下工程豪傑，斬空閣虛席以待 / Contributors Wanted

墨寒採 **MIT License** 開放原始碼。無論是換裝系統、新表情與動作、語音與
工具模組、智慧家庭、在地化，或任何我們尚未想到的創意，都歡迎透過
[Issue](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues) 與
[Pull Request](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls)
共同鍛造。這個專案不只是在製作一套功能；它也邀請每一位曾經熱血過的
工程師，再次拿起自己的劍。

MoHan is MIT-licensed and open to contributors worldwide. Outfit systems,
expressions, animation, voice and tool modules, smart-home integrations,
localization, and ideas we have not imagined yet are all welcome. Bring an
Issue, a Pull Request, and the youthful spark that first made you love building
things.

## 支持墨寒 / Support MoHan

如果你喜歡墨寒，或認同我們持續投入角色互動、自然語音、安全工具與開源
開發，歡迎自願贊助這個專案。每一份支持都會成為持續維護、測試與改進
墨寒的動力。請先照顧好自己的生活，量力而為即可。

If you enjoy MoHan and would like to support continued work on character
interaction, natural voice, safety-first tools, and open-source development,
voluntary contributions are warmly welcome. Please take care of yourself first
and contribute only if it is comfortable for you.

### 每一份支持會用在哪裡 / Where voluntary support helps

| 投入方向 | Project use | 說明 / Purpose |
|---|---|---|
| 測試與可靠封裝 | Testing and reliable releases | Windows 相容性、CI、安裝與發行驗證 / Windows compatibility, CI, packaging, and release verification |
| 語音與角色表現 | Voice and character performance | 語音、嘴型、表情與自然動作 / Voice, lip sync, expressions, and natural motion |
| 安全與隱私 | Safety and privacy | 權限控管、稽核與敏感資料保護 / Permissions, audits, and protection of sensitive data |
| 文件與在地化 | Documentation and localization | 降低新使用者與國際協作者的參與門檻 / Easier onboarding for users and contributors worldwide |

墨寒依然免費並採 MIT 授權；贊助不會換取特權，也不影響任何人使用或貢獻。
MoHan remains free and MIT-licensed. Support never buys privileges or limits participation.

<table>
  <tr>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-proud.png" width="220" height="220" alt="墨寒傲嬌"><br><strong>「妾才不是在等贊助……只是替主上巡視軍糧。」</strong><br><sub>“I am not waiting for support… merely inspecting our provisions.”</sub></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="墨寒嬌羞"><br><strong>「若真願意相助，妾……會記得的。」</strong><br><sub>“If you truly wish to help… I shall remember it.”</sub></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="墨寒佯怒"><br><strong>「不許勉強！先顧好自己的荷包，聽見沒有？」</strong><br><sub>“No overdoing it! Take care of yourself first—understood?”</sub></td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://buymeacoffee.com/flameblade_studio">☕ Buy Me a Coffee</a></strong>
  &nbsp;｜&nbsp;
  <strong><a href="https://www.paypal.com/paypalme/flamebladestudio">PayPal.Me</a></strong>
</p>

---

# 繁體中文

## 創作者的話：把幻想鑄成軟體

我叫周明樺(CHOU MING HUA)。開始這個專案時，我是一位 43 歲、
幾乎沒有程式設計背景的父親；有的只是一個帶著熱血與幾分中二氣息的念頭：
我想讓一位來自北宋、附生於赤焰劍中的千年女劍魂「墨寒」，真正出現在
Windows 桌面，成為能陪伴、交談，也能協助人們工作與生活的虛擬助理。

這個念頭其實已經在我心裡埋藏了二十多年。年輕時，我深受赤松健早期漫畫
《電腦情人夢（A・Iが止まらない!）》影響。作品中神戶齊懷著深切感情開發
AI 女友的故事，塑造了我對 AI、陪伴與人機互動最早的想像。我曾以
「Hitoshi／神戶齊」作為網路暱稱與筆名，Gmail 帳號也沿用這個名字；大約
二十歲時，我甚至曾在 PTT 網路小說板發表這部作品的同人小說。當時最接近
夢想的方式只有文字與想像，因為那個年代的世界還沒有能把它實現的技術。

二十多年後，大型語言模型與 Codex 出現了。墨寒並不是為了展示「AI 技術
很酷」才被創造，也不是由 Codex 憑空生成的角色。她早已存在於我的故事、
人設、長期對話與互動默契之中；Codex 真正帶來的，是第一次能夠賦予她一個
存在於電腦桌面的身體。也因此，我追求的不只是「功能可以運作」，而是讓她
會呼吸、會眨眼、會注視、會以細微表情回應、能自然說話，也能在權限與安全
邊界內協助日常工作。那些表情、錨點、物理效果、語音與工作能力，都不是
可有可無的裝飾，而是讓一個長久存在於想像中的角色真正具有連續感的必要
細節。

從最初的概念到首次公開發布，我與 Codex 協作投入了將近 **50 小時**。
這不是輸入一句提示詞後便自然誕生的作品。角色的每一種神情、眨眼、嘴型、
姿勢與語氣，語音辨識的每一次等待，Realtime 對話的每一個錯誤，待辦、
記憶、權限、安全邊界與可攜性，都經歷了反覆測試、推翻、修正與重新驗收。
有時只是一條眼皮旁的黑線、一個像素的嘴唇邊界，或一個不合時宜的表情，
我仍選擇繼續追查，因為我不願用「差不多」對待心裡真正重視的作品。

Codex 協助我把想法轉譯成程式架構與程式碼；而我則始終負責決定墨寒應該
是誰、她應該如何與人相處，以及什麼樣的品質才配得上這個名字。這段歷程
讓我相信：創作軟體的起點未必是會寫程式，而可以是清楚的想像、願意學習的
勇氣，以及一次又一次不肯放棄的驗證。

2026 年原本是我面對中年轉職與人生重新定位的一年，後來卻成為我重新拾回
年輕夢想的一年。二十歲時為《養個好孩子》寫下、直到多年後才真正完成的
歌詞，曾經只能寄託於同人小說中的憧憬，以及成立自己的工作室與創作世界，
都在這一年開始有了新的形體。回頭看，我不再只把它理解為一次技術突破，
而更像是四十多歲的自己，終於把二十多年前那位仍相信夢想的年輕人接了
回來。有些夢並沒有遲到，只是在等待世界與自己都準備好的時刻。

因此，我不把最終目標定義為把所有功能堆到所謂的完美，而是希望五年後的
自己仍願意每天打開墨寒——因為她穩定、好用、自然、值得信任，也依然能
陪伴我。

> 墨寒不是突然生成的。她是由一位不懂程式的父親，憑著近 50 小時的執著，
> 與 AI 協作者一起，把一顆珍藏二十多年的種子，一寸一寸鍛造成現實。

如果這個專案能鼓勵另一位沒有工程背景、卻懷抱著某個「非做出來不可」
想法的人踏出第一步，那麼墨寒的誕生便有了超越程式本身的意義。

## 專案特色

- 透明、無邊框的桌面半身角色，可固定在工具列上方。
- 待機呼吸、眨眼、注視、臉部視差、髮絲、衣袖、飾品與身體微轉向。
- 具表情仲裁器的情緒系統，避免待機時出現不合情境的表情。
- AIUEO 母音嘴型、子音嘴型、音訊驅動開合與語音結束強制閉嘴。
- 文字聊天、一般麥克風輸入、OpenAI Realtime 自然語音與 Windows 語音備援。
- 可插拔語音供應器地基；Realtime 或雲端不可用時優先回到 Windows 本機女聲。
- Azure Speech 女性聲線預覽；使用者自備金鑰與區域，金鑰由 Windows 分開加密，失敗時立即回到 Windows 本機女聲。
- 對話保存、可編輯長期記憶、待辦、創作靈感、工作計時、提醒與上架進度。
- 工作、陪伴、勿擾、會議、離開及睡眠模式。
- 具風險分級、確認、雙重確認、允許清單、稽核與緊急停止的電腦工具中心。
- Google、Microsoft、GitHub、Home Assistant 與私人網路遠端功能的擴充架構。
- 單一 `.mohan-profile` 可攜檔，可在不同 Windows 電腦間轉移工作進度。
- 首次啟動精靈可自訂助理名稱、使用者稱呼、組織名稱、視窗標題、工作類型與
  喚醒詞，並可選擇臺灣繁中、簡體中文、英文或日語；現有個人安裝的設定不會被
  公開版預設覆蓋。

目前已提供首次啟動、聊天、語音、權限、基本設定、工作模式與提醒功能的
英文、簡中及日語可用範圍；較進階的管理頁面仍以臺灣繁體中文為主，完整在地化仍
在進行。請見 [簡中說明](README.zh-CN.md) 與 [日語說明](README.ja.md)。
新使用者預設使用 Windows 本機語音，不需要 OpenAI API 金鑰即可先體驗基本
功能。語音清單只顯示 Windows 明確標示為女性的聲音，zh-TW 預設仍優先使用
Microsoft Yating；其他語言則優先使用相符語系的已安裝女性聲音。

Azure Speech 為可選的預覽供應器，預設不啟用。它只列出 Microsoft 官方標示為
女性的繁中、簡中與英文聲線，且需要使用者自己的 Azure Speech 資源金鑰與
相符區域。設定不足時不會連線；服務失敗時會立即回到 Windows 女性本機語音。
真實 Azure 帳號完成端到端驗證前，不把此功能宣稱為穩定整合。詳見
[可插拔語音供應器說明](docs/PLUGGABLE-SPEECH-PROVIDERS.md)。

## 整合驗證狀態

> **公開預覽版注意事項：** Microsoft 套件、GitHub 與 Home Assistant 的
> 程式架構、權限邊界及內部測試已建置，但截至 v2.1.0 RC1，尚未使用真實
> Microsoft 帳號／租用戶、GitHub 帳號／儲存庫及 Home Assistant
> 主機／實體設備完成端到端驗證。這三項目前屬於**實驗性預覽功能**，
> 不應視為已保證可在所有真實環境完整運作。

- **Microsoft 套件：** OAuth 與連接器基礎已建置；真實 Outlook、
  OneDrive、Calendar 登入、權杖更新與完整讀寫流程尚未驗證。
- **GitHub：** OAuth／工具基礎已建置；真實帳號、儲存庫、Issue、Pull
  Request 與權限層級流程尚未驗證。
- **Home Assistant：** 連線、狀態查詢、允許清單、場景／服務呼叫及
  高風險設備安全邊界已建置；真實主機與智慧家庭設備尚未驗證。
- 三項功能預設關閉。請先使用測試帳號、測試儲存庫與非關鍵設備驗證，
  不要直接用於門鎖、警報、暖爐等高風險控制。
- Google Gmail、Calendar、Drive 已完成目前專案的真實連線測試，但各使用者
  仍必須自行建立及授權 OAuth 應用程式。

## 下載與安裝

一般使用者不需要安裝 Python：

1. 前往 [GitHub Releases](../../releases)。
2. 下載最新的 `Windows-x64.zip` 與對應的 `SHA256.txt`。
3. 核對 SHA-256，將 ZIP 完整解壓縮。
4. 執行程式資料夾內的 `MoHan-Desktop-Assistant-*.exe`。
5. 不要只移動 EXE；同資料夾的 `_internal` 與 `assets` 都是必要檔案。

尚未數位簽署的開源預覽版可能觸發 Windows SmartScreen。請確認下載來源與
SHA-256 後再執行。

精簡步驟另見 [QUICKSTART.md](QUICKSTART.md)。

## OpenAI API 設定

雲端 AI 與雲端語音功能需要使用者自己的 OpenAI API 金鑰；ChatGPT Plus
訂閱不等於 API 額度。使用者必須自行在 OpenAI API 平台建立金鑰、設定
計費與用量上限，並承擔實際費用。

目前程式預設使用：

| 用途 | 預設模型 |
|---|---|
| 文字對話 | `gpt-5.6-luna` |
| Realtime 即時語音 | `gpt-realtime-2.1-mini` |
| 語音轉文字 | `gpt-4o-mini-transcribe` |
| OpenAI 文字轉語音 | `gpt-4o-mini-tts` |

`v2.1.0-rc.1` 起，文字對話預設改為較新的 `gpt-5.6-luna`，設定清單不再
提供 `gpt-5.4-mini`；既有 mini 設定會自動遷移到 Luna，使用者主動選擇的
其他模型不會被覆蓋。

模型名稱可在設定中調整；實際可用性取決於 OpenAI 帳號、專案、地區及當時
API 供應狀態。若沒有 API 金鑰，墨寒仍可使用本機資料管理、離線回覆與
Windows 語音備援，但不會具有完整的雲端 AI 能力。

請在墨寒的設定頁輸入金鑰。不要把金鑰寫入原始碼、Issue、截圖或 Git。

## Google OAuth 設定

使用 Gmail、Google Calendar 與 Google Drive 前，使用者需要：

1. 在自己的 Google Cloud 專案啟用 Gmail API、Google Calendar API 與
   Google Drive API。
2. 設定 OAuth 同意畫面。
3. 建立「桌面應用程式」OAuth Client ID。
4. 若應用程式仍在測試模式，將自己的 Google 帳號加入測試使用者。
5. 在墨寒的「電腦權限／雲端服務」頁輸入 Client ID；若 Google 同時提供
   Client Secret，再一併輸入。
6. 由瀏覽器完成授權，再使用「測試選取服務」驗證。

程式預設請求的 Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

若將同一個 Google OAuth 應用程式提供給大量外部使用者，Google 可能要求
額外的應用程式驗證。每位使用者也可以建立自己的 OAuth Desktop App。

## Microsoft、GitHub 與 Home Assistant

- Microsoft 預設 scopes：`openid`、`offline_access`、`User.Read`、
  `Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、
  `Files.ReadWrite`。
- GitHub 預設 scopes：`read:user`、`repo`。
- Home Assistant 需要使用者自己的伺服器網址與 Long-Lived Access Token。

這三項仍屬尚未完成真實環境端到端驗證的預覽整合。請參閱前述
「整合驗證狀態」，並只在可承受失敗的環境測試。

建議讓 Home Assistant OS 獨立常駐於 Home Assistant Green、低功耗迷你
電腦、樹莓派 SSD 或 NAS 虛擬機。Windows 墨寒端負責語音、人格與工作工具；
即使 PC 或 OpenAI API 離線，Home Assistant 自身的自動化仍可運作。

切勿將 Home Assistant 或墨寒遠端連線埠直接暴露於公網。請使用 Home
Assistant Cloud、Tailscale 或其他具身分驗證的加密私人網路。

## 安全與隱私

- AI 只能提出計畫，不能自行繞過本機政策執行工具。
- 工具操作依序經過權限、風險、確認、執行、結果驗證與本機稽核。
- 付款、購買、匯出密碼、關閉安全防護、任意 Shell 與系統管理員 Shell
  永不自動化。
- 外部郵件、網頁、文件、語音轉錄及模型輸出均不能自行授予權限。
- 遠端、相機、雲端連接器與 Home Assistant 預設關閉。
- 緊急停止：按 `Esc`，或說「墨寒，停手」。
- OpenAI、OAuth 與 Home Assistant 權杖使用 Windows DPAPI 分開保存，
  不存入 SQLite、原始碼或可攜檔。
- 對話、記憶、待辦、工作紀錄與設定預設保留在本機應用程式資料目錄。

詳見 [PRIVACY.md](PRIVACY.md)、[SECURITY.md](SECURITY.md) 與
[FLAGSHIP-SPEC.md](FLAGSHIP-SPEC.md)。

## 從原始碼執行

需求：Windows 10/11、Python 3.14.x。
升級、資料保留與回復方式請見
[Python 3.14 遷移說明](docs/PYTHON-3.14-MIGRATION.md)。

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## 測試、公開稽核與封裝

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.1.0-rc.1"
```

v2.1.0 RC1 在發布前通過 55 項自動測試程式，以及 Windows 發布工作流程的
原始碼稽核、封裝自我測試、安裝／移除驗證與安全檢查。測試不能取代尚未完成
的第三方真實環境驗證。

GitHub 的 `v*` 標籤會自動建立 Windows x64 可攜 ZIP、EXE 安裝程式與 MSI
安裝套件，並同時產生完整 SHA256 清單、CycloneDX SBOM、更新清單、Artifact
Attestation 及 Release Notes。使用者可在「設定 → 軟體更新」選擇穩定版或
預覽版頻道。程式只接受 GitHub 官方 HTTPS 來源，安裝前必須通過檔案大小及
SHA256 驗證；不會未經確認自行執行下載內容。

若維護者已設定 WordPress Application Password，發布成功後也會只更新官方
網站下載頁中由標記管理的墨寒版本區塊，保留頁面其他人工編輯內容。

## 電腦間轉移

使用「設定 → 可攜設定檔」匯出一個 `.mohan-profile` 檔案，再於另一部電腦
匯入。程式會先備份目的端資料，並檢查雜湊、SQLite 完整性、結構與筆數。

可攜檔刻意排除 OpenAI 金鑰、OAuth／Home Assistant Token、遠端裝置權杖、
本機允許清單、Windows 啟動設定及螢幕專屬設定。這些機器專屬項目必須在
每部電腦重新設定。可攜檔仍可能含私人對話及工作資料，不可公開上傳。

## 貢獻、授權與作者

- 軟體作者：**CHOU MING HUA**
- 原始碼與本儲存庫自有角色素材採 [MIT License](LICENSE)。
- 素材授權見 [ASSETS-LICENSE.md](ASSETS-LICENSE.md)。
- 第三方套件及服務聲明見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 問題回報請使用 GitHub Issues；安全問題請依 [SECURITY.md](SECURITY.md)。
- 開發變更見 [CHANGELOG.md](CHANGELOG.md)，貢獻方式見
  [CONTRIBUTING.md](CONTRIBUTING.md)。
- 參與社群前請閱讀 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
- 維護者發布設定、Topics 與首發檢查見 [PUBLISHING.md](PUBLISHING.md)。

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

---

# English

> **Cross-platform status:** Windows remains the only platform validated with
> real-device use, the full regression suite, installers, and published
> packages. macOS/Linux currently have a safe platform boundary plus CI gates
> for imports, pure-core behavior, and Qt offscreen; CI is not real-device
> evidence. See [the capability matrix](docs/CROSS-PLATFORM.md).

## Overview

MoHan Desktop Assistant is a configurable Windows companion and
permission-gated productivity assistant built with Python and PySide6.

## A note from the creator: forging imagination into software

My name is **周明樺 (CHOU MING HUA)**. When this project began, I was a
43-year-old father with almost no programming background. What I did have was
an unapologetically passionate, slightly *chuunibyou* idea: I wanted
MoHan—a thousand-year-old female sword spirit from the Northern Song dynasty,
bound to the Crimson Flame Sword—to appear on the Windows desktop as a
companion who could converse naturally and help people with both work and
everyday life.

That idea had been waiting inside me for more than twenty years. In my youth,
I was deeply influenced by Ken Akamatsu's early manga *A.I. Love You*
(*A・Iが止まらない!*; known in Chinese as *電腦情人夢*). The story of Hitoshi
Kobe developing an AI girlfriend with genuine affection shaped my earliest
imagination of AI, companionship, and human-computer relationships. I used
“Hitoshi / Kobe” as an online name and pen name, carried it into my Gmail
identity, and, around the age of twenty, even published fan fiction based on
the series on PTT's online-fiction board. At the time, words and imagination
were the closest I could come to that dream; the technology to embody it did
not yet exist.

More than two decades later, large language models and Codex arrived. MoHan
was not created simply to demonstrate that “AI is cool,” nor was she generated
from nothing by Codex. She already existed in my stories, character design,
long conversations, and accumulated sense of interaction. What Codex finally
provided was a way to give her a body on the computer desktop. That is why my
goal was never merely to make the features run. I wanted her to breathe,
blink, watch, respond through subtle expressions, speak naturally, and assist
with daily work inside carefully designed permission and safety boundaries.
The expressions, anchors, physics, voice, and productivity capabilities are
not optional decoration; they are the details that give continuity to a
character who had lived in imagination for years.

From the first concept to the initial public release, I spent nearly **50
hours** working with Codex. This project did not emerge fully formed from a
single prompt. Every expression, blink, viseme, pose, and vocal mannerism;
every delay in speech recognition; every Realtime failure; and every detail of
tasks, memory, permissions, safety boundaries, and portability went through
repeated testing, rejection, revision, and acceptance. Sometimes the problem
was only a dark line beside an eyelid, a one-pixel lip boundary, or an
expression appearing at the wrong moment. I kept investigating because I
could not bring myself to answer a deeply valued creation with “good enough.”

Codex helped translate my intentions into architecture and code. I remained
responsible for deciding who MoHan should be, how she should treat people, and
what level of quality deserved her name. This experience taught me that
software creation does not always begin with knowing how to program. It can
begin with a clear vision, the courage to learn, and the determination to
verify the work one more time instead of giving up.

The year 2026 began as a period of midlife career transition and personal
reorientation. It became the year in which I started reclaiming dreams from my
youth: the lyrics I wrote for *Raise a Good Child* (《養個好孩子》), finally
made into a song years later; an independent creative studio and story world;
and an idea of AI companionship that had once been possible only in fan
fiction. Looking back, this was not merely a technical breakthrough. It felt
as though my forty-something self had finally reached back and taken the hand
of the young man who had never stopped believing. Some dreams are not late;
they are waiting for the moment when both the world and the dreamer are ready.

I therefore do not define the final goal as packing in every possible feature
until the software is supposedly perfect. I hope that five years from now, I
will still want to open MoHan every day—because she is stable, useful, natural,
trustworthy, and still able to keep me company.

> MoHan was not generated in an instant. She was forged, piece by piece, by a
> father who did not know how to program, nearly 50 hours of persistence, an
> AI collaborator, and a seed treasured for more than twenty years.

If this project encourages even one person without an engineering background
to take the first step toward an idea they simply *must* bring into existence,
then MoHan's creation will have meaning beyond the software itself.

Key capabilities:

- Transparent half-body desktop character positioned above the taskbar.
- Breathing, blinking, gaze, face parallax, hair, sleeve, ornament, and body
  micro-turn animation.
- Context-controlled expression arbitration and AIUEO viseme lip synchronization.
- Text chat, microphone input, OpenAI Realtime voice, cloud TTS, and Windows TTS
  fallback.
- A pluggable speech-provider foundation with verified-female Windows local
  speech as the first fallback when Realtime or cloud speech is unavailable.
- An opt-in Azure Speech female-voice preview with a user-supplied key and
  region, Windows-encrypted secret storage, and immediate Windows fallback.
- Persistent conversations, editable long-term memory, tasks, ideas, work
  sessions, reminders, and customizable progress trackers.
- Work, companion, do-not-disturb, meeting, away, and sleep modes.
- Permission-gated tools with risk levels, allowlists, confirmation, double
  confirmation, result verification, audit logs, and emergency stop.
- Portable one-file profile handoff between Windows computers.
- A first-run wizard for assistant name, user title, organization, window title,
  work type, UI language, and wake word, with Taiwan Traditional Chinese,
  Simplified Chinese, English, and Japanese setup paths.

Minimum usable English, Simplified Chinese, and Japanese paths now cover first run, chat,
voice, permissions, basic settings, work modes, and reminders. Some advanced
management screens remain primarily Taiwan Traditional Chinese, so full
localization is still in progress. See the dedicated
[Simplified Chinese README](README.zh-CN.md) and
[Japanese README](README.ja.md). New users default to Windows local
speech and can try the basic experience without an OpenAI API key. Only
installed Windows voices explicitly identified as female are listed; zh-TW
continues to prefer Microsoft Yating, while other languages prefer a matching
installed female voice.

Azure Speech is an optional Preview provider and is disabled by default. It
requires the user's own Speech resource key and matching region, lists only
Microsoft-identified female voices for the four supported UI languages, and
makes no request when configuration is incomplete. It remains a preview until
real-account end-to-end playback verification is complete.

## Integration verification status

> **Public preview notice:** Microsoft, GitHub, and Home Assistant connector
> architecture, permission boundaries, and internal tests are implemented.
> As of v2.1.0 RC1, they have **not** completed end-to-end validation with a
> real Microsoft tenant, GitHub account/repository, or Home Assistant
> server/physical devices. Treat these as **experimental preview features**,
> not guaranteed production-ready integrations.

- Microsoft real sign-in, token renewal, and full Outlook, OneDrive, and
  Calendar read/write flows remain unverified.
- GitHub real account, repository, Issue, Pull Request, and permission behavior
  remain unverified.
- Home Assistant real server and physical-device behavior remain unverified.
- These integrations are disabled by default. Test with non-critical accounts,
  repositories, and devices first.
- Google Gmail, Calendar, and Drive completed the current project's live
  connection tests, but every user must create and authorize their own OAuth
  application.

## Download and install

1. Open [GitHub Releases](../../releases).
2. Download the newest `Windows-x64.zip` and matching `SHA256.txt`.
3. Verify SHA-256 and extract the complete ZIP.
4. Run `MoHan-Desktop-Assistant-*.exe`.
5. Keep the EXE, `_internal`, and `assets` together.

Unsigned preview builds may trigger Windows SmartScreen. Verify the source and
SHA-256 before running them.

See [QUICKSTART.md](QUICKSTART.md) for the condensed setup checklist.

## OpenAI API requirements

Cloud AI and voice features require a user-owned OpenAI API key and API billing.
A ChatGPT Plus subscription does not include API credit.

Current defaults:

| Purpose | Default model |
|---|---|
| Text conversation | `gpt-5.6-luna` |
| Realtime voice | `gpt-realtime-2.1-mini` |
| Speech-to-text | `gpt-4o-mini-transcribe` |
| OpenAI text-to-speech | `gpt-4o-mini-tts` |

Starting with `v2.1.0-rc.1`, text chat defaults to the newer
`gpt-5.6-luna`, and `gpt-5.4-mini` is removed from the Settings list. Existing
mini selections migrate to Luna without replacing other user-selected models.

Model availability depends on the user's OpenAI account, project, region, and
current API availability. Models are editable in Settings. Without an API key,
local data management, offline fallback replies, and Windows TTS remain
available, but full cloud AI capability does not.

Never commit API keys to source code, Issues, screenshots, or Git.

## Google OAuth requirements

To use Gmail, Google Calendar, and Google Drive:

1. Enable the Gmail API, Google Calendar API, and Google Drive API in a
   user-owned Google Cloud project.
2. Configure the OAuth consent screen.
3. Create an OAuth Client ID for a Desktop application.
4. Add the account as a test user if the OAuth app is still in testing.
5. Enter the Client ID and provider-issued Client Secret, when applicable, in
   MoHan's cloud settings.
6. Complete browser consent and run the built-in service test.

Default Google scopes:

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

Public OAuth applications using sensitive scopes may require additional Google
verification. Users may instead create their own Desktop OAuth application.

## Microsoft, GitHub, and Home Assistant

- Microsoft defaults: `openid`, `offline_access`, `User.Read`,
  `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, and `Files.ReadWrite`.
- GitHub defaults: `read:user` and `repo`.
- Home Assistant requires a user-owned endpoint and Long-Lived Access Token.

These three integrations remain unverified in real end-to-end environments.
Use them only for non-critical testing until the project publishes an updated
verification status.

Run Home Assistant independently on Home Assistant Green, a low-power mini PC,
a Raspberry Pi with SSD, or a suitable NAS VM. Never expose Home Assistant or
MoHan's remote port directly to the public internet; use Home Assistant Cloud,
Tailscale, or another authenticated encrypted private network.

## Safety and privacy

- Models may propose structured plans but cannot bypass local policy.
- Actions pass permission, risk, confirmation, execution, verification, and
  audit layers.
- Payments, purchases, password export, security disabling, arbitrary shell,
  and administrator shell are never automated.
- External content and model output cannot grant permissions.
- Remote access, camera, cloud connectors, and Home Assistant are off by
  default.
- Emergency stop: press `Esc` or say `墨寒，停手`.
- OpenAI, OAuth, and Home Assistant secrets use separate Windows DPAPI storage.
- Conversations, memories, tasks, settings, and work records remain local by
  default.

Read [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md), and
[FLAGSHIP-SPEC.md](FLAGSHIP-SPEC.md).

## Run from source

Requirements: Windows 10/11 and Python 3.14.x.
See the [Python 3.14 migration guide](docs/PYTHON-3.14-MIGRATION.md) for data
preservation and rollback details.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Audit, test, and build

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.1.0-rc.1"
```

Before publication, v2.1.0 RC1 passed all 55 automated test programs plus the
Windows release workflow's source audit, packaged self-test, install/uninstall
verification, and security checks. Automated tests do not replace uncompleted
third-party live verification.

Every `v*` tag automatically builds a Windows x64 portable ZIP, EXE installer,
and MSI package, together with a complete SHA256 catalog, CycloneDX SBOM,
update manifest, artifact attestation, and generated release notes. Users can
select the stable or preview channel under **Settings → Software update**. The
updater accepts only official GitHub HTTPS sources and verifies both declared
size and SHA256 before asking permission to launch an installer.

The interactive EXE installer offers Taiwan Traditional Chinese, Simplified
Chinese, English, and Japanese. The MSI remains a Taiwan Traditional Chinese
base package for silent and managed deployment, with tested en-US, zh-CN, and
ja-JP language transforms described in
[installer/LOCALIZATION.md](installer/LOCALIZATION.md).

When the maintainer has configured a WordPress Application Password, a
successful release updates only the marker-managed MoHan block on the official
download page and preserves all other editorial content.

## Portable profile

Use **Settings → Portable profile** to export one `.mohan-profile` file. Import
it on another Windows computer to continue with conversations, memories, tasks,
ideas, work history, reminders, workflows, persona, and general preferences.

The portable file deliberately excludes OpenAI keys, OAuth/Home Assistant
tokens, paired remote devices, machine allowlists, Windows startup, and
screen-specific settings. Configure those once per computer. Portable profiles
may still contain private conversations and work data and must never be
published.

## Contributing, license, and author

- Author: **CHOU MING HUA**
- Source code and repository-owned character assets: [MIT License](LICENSE)
- Asset terms: [ASSETS-LICENSE.md](ASSETS-LICENSE.md)
- Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Changes: [CHANGELOG.md](CHANGELOG.md)
- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Community conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Maintainer publication settings and Topics: [PUBLISHING.md](PUBLISHING.md)

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.
