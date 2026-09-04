# 墨寒桌面語音互動虛擬助理／墨寒桌面语音互动虚拟助手／MoHan Desktop Assistant／墨寒デスクトップアシスタント

## 繁體中文

[繁體中文](#繁體中文) · [簡體中文](#简体中文) · [English](#english) · [日本語](#日本語)

<p align="center"><img src="docs/media/mohan-hero.png" alt="墨寒桌面助理主視覺" width="100%"></p>

<p align="center"><strong>墨寒是重視安全、隱私與角色連續感的 Windows 語音互動桌面助理。</strong></p>

<p align="center">[下載 Windows 安裝程式](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) · [快速開始](QUICKSTART.md) · [跨平台能力矩陣](docs/CROSS-PLATFORM.md)</p>

> **軟體作者：CHOU MING HUA** · Windows 10/11 完整版 · macOS／Linux 功能受限 Preview<br>**最新正式版本：** `v4.6.0`（2026-08-29）。實際產物仍須通過本版最終發布門檻；最新公開版本以動態徽章與 [Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) 為準。<!-- x-release-please-version-date -->

### 這是什麼

墨寒是重視安全、隱私與角色連續感的 Windows 語音互動桌面助理。她以透明 2.5D 角色、自然語音、由使用者控制的本機長期記憶、待辦與工作工具陪伴日常；角色設定是來自北宋、附生於赤焰劍中的千年女劍魂。

<p align="center">
  <img alt="Windows CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Latest Published Release" src="https://img.shields.io/github/v/release/flameblade-studio/MoHan-PC-Desktop-Assistant?include_prereleases&label=published">
</p>

<details>
<summary>其他 CI、資安、Python 與四語徽章</summary>

<p align="center">
  <img alt="Cross-platform core CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg">
  <img alt="CodeQL" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg">
  <img alt="Python Security Audit" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg">
  <img alt="Extended Secret Defense / Gitleaks" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg">
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>
</details>

### 畫面與功能一覽

[觀看 36 秒實際展示](docs/media/mohan-demo.mp4)。設定與主要畫面：[首次設定](docs/media/first-run-wizard.png)、[語音模式](docs/media/voice-modes.png)、[表情](docs/media/expressions.png)、[待辦與靈感](docs/media/tasks-and-ideas.png)、[長期記憶](docs/media/long-term-memory.png)、[安全權限](docs/media/security-permissions.png)。

- 透明桌面角色、眨眼、表情、動作與 50 Hz 嘴型同步。
- 文字、Realtime、Windows 本機女聲、OpenAI TTS 與 Azure Speech 選用路徑。
- 對話、可編輯記憶、待辦、靈感、工作計時、提醒與可攜設定檔。
- 工具執行需經權限、風險分級、確認、稽核與緊急停止。
- Google 已完成實連線驗證；Microsoft、GitHub、Home Assistant 仍是實驗性 Preview。
- 多感官視覺、手勢、遠端存取與雲端連接器預設關閉並可個別撤銷。

#### 四語支援範圍

繁體中文、簡體中文、英文與日文均提供首次設定、對話、語音、權限、基本設定、工作模式與提醒。進階頁面仍可能留有繁體中文；Azure Speech（預覽）的實際語音、區域、額度與費用以使用者自己的服務帳號為準。

### 墨寒的傲嬌工程小劇場 / MoHan's Tsundere Developer Theatre

六張半身表情皆為二代素體、官方藍白漢服與內建原妝經正式執行期路徑合成的固定素材。

<table>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/proud_front.png" width="220" alt="墨寒傲嬌"><br><strong>「妾才沒有等你的 Star，只是在確認軍心是否可用。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/thinking_front.png" width="220" alt="墨寒思考"><br><strong>「這段邏輯尚可。若再補上測試，妾便勉強准它入主分支。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/shy_cute_front.png" width="220" alt="墨寒嬌羞"><br><strong>「你願意送來 PR？妾、妾只是替主上記下功勞。」</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/mock_hit_front.png" width="220" alt="墨寒佯怒"><br><strong>「未經測試便想合併？手伸出來。妾只敲一下。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/gentle_smile_front.png" width="220" alt="墨寒微笑"><br><strong>「全數綠燈……做得好。別誤會，妾只是尊重好工程。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/worried_front.png" width="220" alt="墨寒關心"><br><strong>「Bug 可以明日再查。你若累倒，誰來陪妾守著赤焰劍？」</strong></td>
  </tr>
</table>

<table>
  <tr>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Q 版墨寒審查程式"><br><strong>策士審查</strong><br>確認程式是否配得上主分支。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Q 版墨寒被稱讚"><br><strong>被稱讚時</strong><br>做得尚可，別一直盯著妾看。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Q 版墨寒阻止危險操作"><br><strong>危險操作</strong><br>未經確認，先過妾這一劍。</td>
    <td width="25%" align="center" valign="top"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Q 版墨寒收到贊助"><br><strong>收到軍糧</strong><br>妾會記下這份心意。</td>
  </tr>
</table>

### 安裝與更新

1. 從 [GitHub Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) 下載以 `Windows-x64-Setup.exe` 結尾的安裝程式；進階使用者也可選完整的 `Windows-x64.zip` 或 MSI。
2. 安裝前核對 `SHA256SUMS` 與 GitHub Artifact Attestation。來源、檔名或雜湊不符就停止，不要關閉整體安全防護。
3. 啟動安裝程式，或完整解壓 ZIP 並保持 EXE、內部資料夾與 assets 在同一目錄；更新不會刪除本機個人資料。
4. 內建更新器先用內嵌公鑰驗證更新清單的 Ed25519 分離 `.sig` 簽章，再核對宣告大小與 SHA-256；簽章、大小或雜湊失敗即拒絕啟動下載檔。

macOS／Linux Preview 尚未等同 Windows 完整版，且可能沒有平台商店簽章或公證；只從本專案 Release 取得並完成上述來源驗證。詳見 [Preview 套件說明](docs/PREVIEW-PACKAGES.md)。

### 第一次使用要做的三件事

1. 在首次設定精靈確認介面語言、助理名稱、主上稱呼、組織、工作類型與喚醒詞；既有設定不會被覆寫。
2. 先試 Windows 本機女聲；需要雲端 AI 時，再到設定輸入自己持有的 OpenAI API 金鑰。ChatGPT 訂閱不包含 API 額度。
3. 檢查麥克風、通知與工具權限，只開啟真正需要的連接器；先記住緊急停止鍵 Esc 與「墨寒，停手」。

### 雲端連接器設定

#### Google OAuth

使用 Gmail、Google Calendar 與 Google Drive 前，請先完成：

1. 在自己的 Google Cloud 專案啟用 Gmail API、Google Calendar API 與 Google Drive API。
2. 設定 OAuth 同意畫面；若應用程式仍在測試模式，將自己的 Google 帳號加入測試使用者。
3. 建立「桌面應用程式」OAuth Client ID。
4. 開啟墨寒「設定」頁的「旗艦控制中心」→「雲端連接器」，選擇 Google（Gmail／Calendar／Drive），填入「OAuth Client ID」；只有供應商提供「OAuth Client Secret」時才填入。
5. 在「授權範圍」保留以下預設 scopes，按「開啟瀏覽器安全連線」完成瀏覽器授權，再按「測試選取服務」。

程式預設請求以下 Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

公開 OAuth 應用程式若使用敏感 scopes，可能需要 Google 額外驗證；每位使用者也可建立自己的 Desktop OAuth 應用程式。

#### Microsoft、GitHub 與 Home Assistant

- Microsoft 預設 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub 預設 scopes：`read:user`、`repo`。
- Home Assistant：先在自己的 Home Assistant 個人檔案建立 Long-Lived Access Token；在墨寒「設定」頁的「旗艦控制中心」→「智慧家庭」勾選「啟用 Home Assistant 整合」，填入「Home Assistant 位址」與「長期存取權杖」，確認「驗證 HTTPS 憑證」後按「保存設定」，再用「測試連線」或「讀取裝置」確認。

這三項仍是尚未完成真實環境端到端驗證的實驗性 Preview 整合，請先使用可承受失敗的測試帳號與設備；不要將 Home Assistant 或墨寒遠端連線埠直接暴露於公網，請使用 Home Assistant Cloud、Tailscale 或其他具身分驗證的加密私人網路。

### 隱私與本機優先

- Windows 的對話、記憶、待辦、設定、工作紀錄、權限與稽核預設存於 `%LOCALAPPDATA%\YanJianStudio\MoHan`；備份位於其 backups 子目錄，可攜資料使用單一 `.mohan-profile`。
- 只有使用者啟用相關功能時，完成該次要求所需的文字、音訊或工具規劃才會送往 OpenAI；OAuth 服務只收到使用者同意的 API 要求，Home Assistant 收到本機裝置要求。
- API 金鑰與 OAuth／Home Assistant Token 以 Windows DPAPI 分離保存，不進 SQLite、原始碼、日誌或一般可攜檔；墨寒也不會自動取得 ChatGPT 帳號歷史。
- 相機、遠端存取與雲端連接器預設關閉；原始相機影格不保存，權限或服務失敗只會停用受影響路徑。

多感官視覺預設關閉。使用者在控制中心明確啟用並保存全體設定後，該選擇構成持續授權，直到主動關閉；不會逐幀詢問。畫面持續顯示授權狀態，可立即撤銷，並可設成本上限與取消未完成分析。本機 OpenCV 負責持續偵測，只有低頻或事件觸發才將暫時影像送往 GPT-5.6；原圖不儲存、Base64 不進日誌，系統不自行開啟網路。缺少相機、模型、網路、額度或辨識時只停用該路徑，不影響其他功能。完整邊界見 [隱私說明](PRIVACY.md) 與 [安全政策](SECURITY.md)。

### DLC 與外觀自訂

`.mohan-outfit` 是角色外觀容器，可含衣裝、髮型、頭飾、妝容與配件；妝容專用包仍是同一格式。`.mohan-theme` 只改控制台色彩、字型、圓角與可選背景，不改角色外觀。兩者都是單一、自包含、免解壓檔案，安裝前會完整驗證且不執行其中的程式碼。

#### 安裝、選用外觀與妝容

1. 下載 `.mohan-outfit`，不要改副檔名或解壓縮。
2. 開啟控制中心「雲裳閣」，按「匯入服裝套件」並選檔；衣裝包與妝容包共用此入口、驗證、清單與移除流程。
3. 從套件或完整造型清單選取後按「套用選取服裝」；妝容則在妝容選單挑選原妝、淡雅、素顏或已安裝款式，再用 0–100% 滑桿調整濃度。
4. 要撤銷自訂外觀，按「還原內建服裝」；妝容改選內建原妝或素顏。內建藍白漢服與內建妝容不可移除或被同 id 套件覆蓋。

#### 安裝與還原主題

1. 下載 `.mohan-theme`，不要解壓縮。
2. 在「設定」→「控制台佈景主題」按「上傳單一檔案」，選取主題後從清單預覽。
3. 按右下「保存設定」才正式套用；取消會回到原主題。「還原主題」可預覽內建主題，再保存完成還原。

#### 容量、數量與相容性

- 單一外觀包最多 1 GiB，解壓後總量最多 2 GiB、最多 2,048 個成員；每個成員最多 128 MiB，圖片任一邊最多 4,096 px。
- 單一主題檔及解壓總量最多 16 MiB，每個成員最多 12 MiB，背景任一邊最多 4,096 px。
- 雲端自創服裝預設保留 16 包、總容量 6 GiB、修復待審隔離 5 件；前兩項可各調為 1–64。到達上限即停止生成，不會自動刪除使用者匯入包。
- 現行二代骨架只接受 `mohan-body-v2`。為 `mohan-body-v1` 三姿勢製作的一代包缺少二代 31 個輪廓、錨點與遮蔽契約，因此匯入與執行期都拒絕；請以 `tools/build_outfit_pack.py` 對二代範本重建，或用「一鍵製衣」重新生成。
- 安裝採完整驗證後原子寫入；絕對路徑、跨目錄路徑、可執行程式、腳本、符號連結、加密成員、解壓炸彈與未宣告素材一律拒絕。

完整作者規格見 [外觀包文件](docs/OUTFIT-PACKS.md)。

> #### ❤️⚔️ 支持墨寒：Ko-fi 贊助＆裝飾 DLC 下載
>
> 贊助者依 Ko-fi 謝禮指引取得外觀、妝容與主題等純裝飾 DLC；目前採單次贊助與每月贊助雙軌，沒有功能特權。下載位置與檔名以 Ko-fi 該項謝禮指引為準。

### 支持墨寒 / Support MoHan：贊助與授權

請使用儲存庫上方由 GitHub 顯示的 Sponsor 按鈕，或直接前往 [Ko-fi](https://ko-fi.com/flamebladestudio)；目前正式收款選項為 Ko-fi，可選單次或每月贊助。完整功能永遠免費，贊助只提供純裝飾 DLC 謝禮。

<table>
  <tr>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-proud.png" width="220" height="220" alt="墨寒傲嬌"><br><strong>「妾才不是在等贊助……只是巡視軍糧。」</strong></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="墨寒嬌羞"><br><strong>「若真願意相助，妾會記得的。」</strong></td>
    <td width="33%" align="center" valign="top"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="墨寒提醒量力而為"><br><strong>「不許勉強，先顧好自己的荷包。」</strong></td>
  </tr>
</table>

- 作者：**CHOU MING HUA**。
- 原始碼採 [MIT License](LICENSE)；「墨寒」角色美術、人設、名稱與肖像保留一切權利，不在 MIT 授權範圍。
- 素材生產工具與權重只接受 MIT、Apache 2.0、CC0、CC BY（及同級 BSD）白名單；字型是唯一例外：自 2026-09-02 起允許 SIL OFL 1.1，但僅限字型，不延伸至其他素材；角色美術仍是權利人的專有財產，詳見 [授權純淨承諾](docs/LICENSE-PURITY.md)。
- 素材與第三方條款分別見 [ASSETS-LICENSE](ASSETS-LICENSE.md) 與 [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md)。

本專案遵循[炎劍開源軟體家族品質標準](PUBLISHING.md)。

### 疑難排解

- Windows SmartScreen 或平台警告：先確認 GitHub Release 來源、`SHA256SUMS` 與 Artifact Attestation；不要停用整體保護。
- 無法對話：確認自己的 OpenAI API 金鑰、Project 權限、額度與網路；ChatGPT 訂閱不能代替 API 額度。
- 沒有聲音：先切回 Windows 本機女聲；Azure Speech 需使用者自己的金鑰與相符區域。
- DLC 被拒絕：確認檔案完整、大小、安全 manifest、四語名稱與 `mohan-body-v2` 相容性；一代包必須重建。
- Preview 整合失敗：先用非重要帳號、測試儲存庫與低風險設備；Microsoft、GitHub、Home Assistant 尚未完成所有真實環境驗證。

一般問題請到 [Issues](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues)，使用討論請到 [Discussions](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/discussions)，安全問題依 [SECURITY](SECURITY.md) 私下回報；規劃見 [ROADMAP](ROADMAP.md)。

### 開發者入口

先讀 [架構](ARCHITECTURE.md)、[測試說明](docs/TESTING.md)、[貢獻指南](CONTRIBUTING.md)、[外觀包規格](docs/OUTFIT-PACKS.md) 與 [發布政策](PUBLISHING.md)。Windows 安裝封裝版使用工作室維護的 Python 3.15 執行環境；原始碼與 CI 採 PEP 810 惰性匯入，文件維持四語同構。

```powershell
py -3.15 -m ruff check .
py -3.15 tools/audit_python315_idioms.py
py -3.15 tools/check_four_language_docs.py
$env:QT_QPA_PLATFORM = "offscreen"
py -3.15 tests/run_all.py
```

Windows 正式封裝規格以 Rust 1.97.1、Maturin 1.14.1 與 PyO3 0.29.2 建置第一方原生模組；Rayon 1.12.0 只在至少 262,144 pixels 且有多執行緒時平行合成 RGBA。PyBackedBytes 避免額外輸入複製，但輸出仍建立新 bytes，不宣稱端到端零複製或未實作的 SIMD。OpenAI Responses API 直接使用標準函式庫 HTTPS；墨寒沒有 `openai` Python SDK 執行期相依。

## 简体中文

[繁體中文](#繁體中文) · [簡體中文](#简体中文) · [English](#english) · [日本語](#日本語)

<p align="center"><img src="docs/media/mohan-hero.png" alt="墨寒桌面助手主视觉" width="100%"></p>

<p align="center"><strong>墨寒是一款重视安全、隐私与角色连续感的 Windows 语音交互桌面助手。</strong></p>

<p align="center">[下载 Windows 安装程序](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) · [快速开始](QUICKSTART.md) · [跨平台能力矩阵](docs/CROSS-PLATFORM.md)</p>

> **软件作者：CHOU MING HUA** · Windows 10/11 完整版 · macOS／Linux 功能受限 Preview<br>**最新正式版本：** `v4.6.0`（2026-08-29）。实际产物仍须通过本版本最终发布关卡；最新公开版本以动态徽章与 [Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) 为准。<!-- x-release-please-version-date -->

### 这是什么

墨寒是一款重视安全、隐私与角色连续感的 Windows 语音交互桌面助手。她通过透明 2.5D 角色、自然语音、由用户控制的本地长期记忆、待办事项与工作工具陪伴日常；角色设定是来自北宋、寄居在赤焰剑中的千年女剑魂。

<p align="center">
  <img alt="Windows CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Latest Published Release" src="https://img.shields.io/github/v/release/flameblade-studio/MoHan-PC-Desktop-Assistant?include_prereleases&label=published">
</p>

<details>
<summary>其他 CI、安全、Python 与四语徽章</summary>

<p align="center">
  <img alt="Cross-platform core CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg">
  <img alt="CodeQL" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg">
  <img alt="Python Security Audit" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg">
  <img alt="Extended Secret Defense / Gitleaks" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg">
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>
</details>

### 界面与功能一览

[观看 36 秒实际演示](docs/media/mohan-demo.mp4)。设置与主要界面：[首次设置](docs/media/first-run-wizard.png)、[语音模式](docs/media/voice-modes.png)、[表情](docs/media/expressions.png)、[待办与灵感](docs/media/tasks-and-ideas.png)、[长期记忆](docs/media/long-term-memory.png)、[安全权限](docs/media/security-permissions.png)。

- 透明桌面角色、眨眼、表情、动作与 50 Hz 口型同步。
- 文本、Realtime、Windows 本地女声、OpenAI TTS 与 Azure Speech 可选路径。
- 对话、可编辑记忆、待办事项、灵感、工作计时、提醒与便携配置文件。
- 工具执行必须经过权限、风险分级、确认、审计与紧急停止。
- Google 已完成真实连接验证；Microsoft、GitHub、Home Assistant 仍为实验性 Preview。
- 多感官视觉、手势、远程访问与云端连接器默认关闭并可单独撤销。

#### 四语支持范围

繁体中文、简体中文、英文与日文均提供首次设置、对话、语音、权限、基本设置、工作模式与提醒。高级页面仍可能保留繁体中文；Azure Speech（预览）的实际语音、区域、配额与费用以用户自己的服务账号为准。

### 墨寒的傲娇工程小剧场

六张半身表情均为二代素体、官方蓝白汉服与内置原妆经正式运行时路径合成的固定素材。

<table>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/proud_front.png" width="220" alt="墨寒傲娇"><br><strong>“妾才没有等你的 Star，只是在确认军心是否可用。”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/thinking_front.png" width="220" alt="墨寒思考"><br><strong>“这段逻辑尚可。若再补上测试，妾便勉强准它进入主分支。”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/shy_cute_front.png" width="220" alt="墨寒娇羞"><br><strong>“你愿意提交 PR？妾、妾只是替主上记下功劳。”</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/mock_hit_front.png" width="220" alt="墨寒佯怒"><br><strong>“未经测试便想合并？手伸出来。妾只敲一下。”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/gentle_smile_front.png" width="220" alt="墨寒微笑"><br><strong>“全部绿灯……做得好。别误会，妾只是尊重好工程。”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/worried_front.png" width="220" alt="墨寒关心"><br><strong>“Bug 可以明天再查。你若累倒，谁来陪妾守着赤焰剑？”</strong></td>
  </tr>
</table>

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Q 版墨寒审查程序"><br><strong>谋士审查</strong><br>确认程序是否配得上主分支。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Q 版墨寒被称赞"><br><strong>被称赞时</strong><br>做得尚可，别一直盯着妾看。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Q 版墨寒阻止危险操作"><br><strong>危险操作</strong><br>未经确认，先过妾这一剑。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Q 版墨寒收到赞助"><br><strong>收到军粮</strong><br>妾会记下这份心意。</td>
  </tr>
</table>

### 安装与更新

1. 从 [GitHub Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) 下载以 `Windows-x64-Setup.exe` 结尾的安装程序；高级用户也可选择完整的 `Windows-x64.zip` 或 MSI。
2. 安装前核对 `SHA256SUMS` 与 GitHub Artifact Attestation。来源、文件名或哈希不符就停止，不要关闭整体安全防护。
3. 启动安装程序，或完整解压 ZIP 并保持 EXE、内部文件夹与 assets 在同一目录；更新不会删除本地个人数据。
4. 内置更新器先用内嵌公钥验证更新清单的 Ed25519 分离 `.sig` 签名，再核对声明大小与 SHA-256；签名、大小或哈希失败即拒绝启动下载文件。

macOS／Linux Preview 尚不等同于 Windows 完整版，且可能没有平台商店签名或公证；只从本项目 Release 获取并完成上述来源验证。详见 [Preview 软件包说明](docs/PREVIEW-PACKAGES.md)。

### 第一次使用要做的三件事

1. 在首次设置向导确认界面语言、助手名称、对用户的称呼、组织、工作类型与唤醒词；现有设置不会被覆盖。
2. 先试听 Windows 本地女声；需要云端 AI 时，再到设置中输入自己持有的 OpenAI API 密钥。ChatGPT 订阅不包含 API 配额。
3. 检查麦克风、通知与工具权限，只开启真正需要的连接器；先记住紧急停止键 Esc 与“墨寒，停手”。

### 云端连接器设置

#### Google OAuth

使用 Gmail、Google Calendar 与 Google Drive 前，请先完成：

1. 在自己的 Google Cloud 项目启用 Gmail API、Google Calendar API 与 Google Drive API。
2. 设置 OAuth 同意屏幕；若应用程序仍处于测试模式，将自己的 Google 账号加入测试用户。
3. 创建“桌面应用程序”OAuth Client ID。
4. 打开墨寒“设置”页的“旗舰控制中心”→“云端连接器”，选择 Google（Gmail／Calendar／Drive），填写“OAuth Client ID”；仅在供应商提供“OAuth Client Secret”时填写。
5. 在“授权范围”保留以下默认 scopes，点击“打开浏览器安全连接”完成浏览器授权，再点击“测试选中服务”。

程序默认请求以下 Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

公开 OAuth 应用程序若使用敏感 scopes，可能需要 Google 额外验证；每位用户也可以创建自己的 Desktop OAuth 应用程序。

#### Microsoft、GitHub 与 Home Assistant

- Microsoft 默认 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub 默认 scopes：`read:user`、`repo`。
- Home Assistant：先在自己的 Home Assistant 个人资料中创建 Long-Lived Access Token；在墨寒“设置”页的“旗舰控制中心”→“智能家居”勾选“启用 Home Assistant 集成”，填写“Home Assistant 地址”和“长期访问令牌”，确认“验证 HTTPS 证书”后点击“保存设置”，再用“测试连接”或“读取设备”确认。

这三项仍是尚未完成真实环境端到端验证的实验性 Preview 集成，请先使用可承受失败的测试账号与设备；不要将 Home Assistant 或墨寒远程端口直接暴露于公网，请使用 Home Assistant Cloud、Tailscale 或其他具有身份验证的加密私人网络。

### 隐私与本地优先

- Windows 的对话、记忆、待办事项、设置、工作记录、权限与审计默认存储在 `%LOCALAPPDATA%\YanJianStudio\MoHan`；备份位于其 backups 子目录，便携数据使用单一 `.mohan-profile`。
- 只有用户启用相关功能时，完成该次请求所需的文本、音频或工具规划才会发送到 OpenAI；OAuth 服务只收到用户同意的 API 请求，Home Assistant 收到本地设备请求。
- API 密钥与 OAuth／Home Assistant 令牌通过 Windows DPAPI 分开保存，不进入 SQLite、源代码、日志或普通便携文件；墨寒也不会自动获取 ChatGPT 账号历史。
- 摄像头、远程访问与云端连接器默认关闭；原始摄像头帧不保存，权限或服务失败只会停用受影响的路径。

多感官视觉默认关闭。用户在控制中心明确启用并全局保存后，该选择构成持续授权，直到用户主动关闭；不会逐帧询问。界面持续显示授权状态，可立即撤销，并可设置成本上限与取消未完成的分析。本地 OpenCV 负责持续检测，只有低频或事件触发才将临时图像发送到 GPT-5.6；原图不保存、Base64 不进入日志，系统不会自行开启网络。缺少摄像头、模型、网络、配额或识别时只会停用该路径，不影响其他功能。完整边界见 [隐私说明](PRIVACY.md) 与 [安全政策](SECURITY.md)。

### DLC 与外观自定义

`.mohan-outfit` 是角色外观容器，可包含服装、发型、头饰、妆容与配件；妆容专用包仍使用同一格式。`.mohan-theme` 只修改控制台色彩、字体、圆角与可选背景，不修改角色外观。两者都是单一、自包含、无需解压的文件，安装前会完整验证且不执行其中的代码。

#### 安装、选用外观与妆容

1. 下载 `.mohan-outfit`，不要修改扩展名或解压。
2. 打开控制中心“云裳阁”，点击“导入服装套件”并选择文件；服装包与妆容包共用该入口、验证、列表与删除流程。
3. 从套件或完整造型列表选取后点击“应用所选服装”；妆容则在妆容菜单选择原妆、淡雅、素颜或已安装样式，再使用 0–100% 滑块调整浓度。
4. 要撤销自定义外观，点击“恢复内置服装”；妆容改选内置原妆或素颜。内置蓝白汉服与内置妆容不可删除，也不可被同 id 套件覆盖。

#### 安装与恢复主题

1. 下载 `.mohan-theme`，不要解压。
2. 在“设置”→“控制台主题”点击“上传单个文件”，选取主题后从列表预览。
3. 点击右下角“保存设置”才正式应用；取消会恢复原主题。“恢复主题”可预览内置主题，再保存以完成恢复。

#### 容量、数量与兼容性

- 单个外观包最大 1 GiB，解压后总量最大 2 GiB、最多 2,048 个成员；每个成员最大 128 MiB，图片任一边最大 4,096 px。
- 单个主题文件及解压总量最大 16 MiB，每个成员最大 12 MiB，背景任一边最大 4,096 px。
- 云端自创服装默认保留 16 包、总容量 6 GiB、修复待审隔离 5 个；前两项可分别调整为 1–64。达到上限即停止生成，不会自动删除用户导入包。
- 当前二代骨架只接受 `mohan-body-v2`。为 `mohan-body-v1` 三姿势制作的一代包缺少二代 31 个轮廓、锚点与遮挡契约，因此导入与运行时均会拒绝；请使用 `tools/build_outfit_pack.py` 按二代模板重建，或使用“一键制衣”重新生成。
- 安装在完整验证后进行原子写入；绝对路径、跨目录路径、可执行程序、脚本、符号链接、加密成员、解压炸弹与未声明素材一律拒绝。

完整作者规范见 [外观包文档](docs/OUTFIT-PACKS.md)。

> #### ❤️⚔️ 支持墨寒：Ko-fi 赞助＆装饰 DLC 下载
>
> 赞助者根据 Ko-fi 谢礼说明获取外观、妆容与主题等纯装饰 DLC；目前采用单次赞助与每月赞助双轨，不提供功能特权。下载位置与文件名以 Ko-fi 对应谢礼说明为准。

### 支持墨寒：赞助与许可证

请使用仓库上方由 GitHub 显示的 Sponsor 按钮，或直接前往 [Ko-fi](https://ko-fi.com/flamebladestudio)；当前正式收款选项为 Ko-fi，可选择单次或每月赞助。完整功能始终免费，赞助仅提供纯装饰 DLC 谢礼。

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="墨寒傲娇"><br><strong>“妾才不是在等赞助……只是在巡视军粮。”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="墨寒娇羞"><br><strong>“若真愿意相助，妾会记得的。”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="墨寒提醒量力而行"><br><strong>“不许勉强，先照顾好自己的钱包。”</strong></td>
  </tr>
</table>

- 作者：**CHOU MING HUA**。
- 源代码采用 [MIT License](LICENSE)；“墨寒”角色美术、人设、名称与肖像保留所有权利，不在 MIT 许可证范围内。
- 素材生产工具与权重只接受 MIT、Apache 2.0、CC0、CC BY（及同等级 BSD）白名单；字体是唯一例外：自 2026-09-02 起允许 SIL OFL 1.1，但仅限字体，不延伸至其他素材；角色美术仍是权利人的专有财产，详见 [许可证纯净承诺](docs/LICENSE-PURITY.md)。
- 素材与第三方条款分别见 [ASSETS-LICENSE](ASSETS-LICENSE.md) 与 [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md)。

本项目遵循[炎剑开源软件家族质量标准](PUBLISHING.md)。

### 疑难解答

- Windows SmartScreen 或平台警告：先确认 GitHub Release 来源、`SHA256SUMS` 与 Artifact Attestation；不要关闭整体保护。
- 无法对话：确认自己的 OpenAI API 密钥、Project 权限、配额与网络；ChatGPT 订阅不能替代 API 配额。
- 没有声音：先切回 Windows 本地女声；Azure Speech 需要用户自己的密钥与匹配区域。
- DLC 被拒绝：确认文件完整、大小、安全 manifest、四语名称与 `mohan-body-v2` 兼容性；一代包必须重建。
- Preview 集成失败：先使用非重要账号、测试仓库与低风险设备；Microsoft、GitHub、Home Assistant 尚未完成所有真实环境验证。

一般问题请到 [Issues](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues)，使用讨论请到 [Discussions](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/discussions)，安全问题按 [SECURITY](SECURITY.md) 私下报告；规划见 [ROADMAP](ROADMAP.md)。

### 开发者入口

请先阅读 [架构](ARCHITECTURE.md)、[测试说明](docs/TESTING.md)、[贡献指南](CONTRIBUTING.md)、[外观包规范](docs/OUTFIT-PACKS.md) 与 [发布政策](PUBLISHING.md)。Windows 安装包使用工作室维护的 Python 3.15 运行环境；源代码与 CI 采用 PEP 810 延迟导入，文档保持四语同构。

```powershell
py -3.15 -m ruff check .
py -3.15 tools/audit_python315_idioms.py
py -3.15 tools/check_four_language_docs.py
$env:QT_QPA_PLATFORM = "offscreen"
py -3.15 tests/run_all.py
```

Windows 正式打包规范使用 Rust 1.97.1、Maturin 1.14.1 与 PyO3 0.29.2 构建第一方原生模块；Rayon 1.12.0 仅在至少 262,144 pixels 且有多线程时并行合成 RGBA。PyBackedBytes 避免额外输入复制，但输出仍创建新 bytes，不声称端到端零复制或尚未实现的 SIMD。OpenAI Responses API 直接使用标准库 HTTPS；墨寒没有 `openai` Python SDK 运行时依赖。

## English

[繁體中文](#繁體中文) · [簡體中文](#简体中文) · [English](#english) · [日本語](#日本語)

<p align="center"><img src="docs/media/mohan-hero.png" alt="MoHan Desktop Assistant hero image" width="100%"></p>

<p align="center"><strong>MoHan is a Windows voice-interactive desktop assistant built around safety, privacy, and character continuity.</strong></p>

<p align="center">[Download Windows installer](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) · [Quick Start](QUICKSTART.md) · [Cross-platform capability matrix](docs/CROSS-PLATFORM.md)</p>

> **Author: CHOU MING HUA** · Windows 10/11 complete build · macOS/Linux limited Preview<br>**Latest formal release:** `v4.6.0` (August 29, 2026). The actual artifacts must still pass this release's final publication gates; the dynamic badge and [Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) remain authoritative.<!-- x-release-please-version-date -->

### What this is

MoHan is a Windows voice-interactive desktop assistant built around safety, privacy, and character continuity. She combines a transparent 2.5D character, natural speech, user-controlled local long-term memory, tasks, and work tools; in her story, she is a thousand-year-old sword spirit from the Northern Song dynasty who dwells within the Crimson Flame Sword.

<p align="center">
  <img alt="Windows CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Latest Published Release" src="https://img.shields.io/github/v/release/flameblade-studio/MoHan-PC-Desktop-Assistant?include_prereleases&label=published">
</p>

<details>
<summary>Other CI, security, Python, and four-language badges</summary>

<p align="center">
  <img alt="Cross-platform core CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg">
  <img alt="CodeQL" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg">
  <img alt="Python Security Audit" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg">
  <img alt="Extended Secret Defense / Gitleaks" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg">
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>
</details>

### Screens and capabilities

[Watch the 36-second live demonstration](docs/media/mohan-demo.mp4). Setup and main screens: [first run](docs/media/first-run-wizard.png), [voice modes](docs/media/voice-modes.png), [expressions](docs/media/expressions.png), [tasks and ideas](docs/media/tasks-and-ideas.png), [long-term memory](docs/media/long-term-memory.png), and [security permissions](docs/media/security-permissions.png).

- Transparent desktop character, blinking, expressions, motion, and 50 Hz lip sync.
- Text, Realtime, Windows local female speech, OpenAI TTS, and optional Azure Speech paths.
- Conversations, editable memory, tasks, ideas, work timers, reminders, and a portable profile.
- Tool execution passes through permissions, risk levels, confirmation, auditing, and emergency stop.
- Google has completed live connection verification; Microsoft, GitHub, and Home Assistant remain experimental Preview integrations.
- Multisensory vision, gestures, remote access, and cloud connectors are off by default and separately revocable.

#### Four-language support scope

Traditional Chinese, Simplified Chinese, English, and Japanese cover first run, chat, voice, permissions, basic settings, work modes, and reminders. Some advanced pages may still contain Traditional Chinese; actual voices, regions, quotas, and costs for Azure Speech (Preview) depend on the user's own service account.

### MoHan's Tsundere Developer Theatre

These six half-body expressions are fixed assets composed through the formal runtime path from the generation-2 body, official Blue-and-White Hanfu, and built-in classic makeup.

<table>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/proud_front.png" width="220" alt="Proud MoHan"><br><strong>“I was not waiting for your Star. I was merely checking morale.”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/thinking_front.png" width="220" alt="Thinking MoHan"><br><strong>“The logic is acceptable. Add tests, and I may permit it onto main.”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/shy_cute_front.png" width="220" alt="Shy MoHan"><br><strong>“You brought a PR? I-I am only recording your contribution.”</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/mock_hit_front.png" width="220" alt="Mock-angry MoHan"><br><strong>“Merge without tests? Hold out your hand. One tap.”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/gentle_smile_front.png" width="220" alt="Smiling MoHan"><br><strong>“All green... well done. I merely respect sound engineering.”</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/worried_front.png" width="220" alt="Concerned MoHan"><br><strong>“The bug can wait until tomorrow. Who guards the sword if you collapse?”</strong></td>
  </tr>
</table>

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="Chibi MoHan reviewing code"><br><strong>Strategist review</strong><br>Checking whether the code deserves main.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="Chibi MoHan receiving praise"><br><strong>When praised</strong><br>Acceptable. Stop staring.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="Chibi MoHan blocking a dangerous action"><br><strong>Dangerous action</strong><br>No confirmation? First pass my blade.</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="Chibi MoHan receiving support"><br><strong>Provisions received</strong><br>I shall remember this kindness.</td>
  </tr>
</table>

### Install and update

1. Download the installer ending in `Windows-x64-Setup.exe` from [GitHub Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases); advanced users may choose the complete `Windows-x64.zip` or MSI.
2. Before installation, verify `SHA256SUMS` and the GitHub Artifact Attestation. Stop if the source, filename, or digest differs; do not disable system-wide protection.
3. Start the installer, or fully extract the ZIP and keep the EXE, internal folders, and assets together. Updating does not delete local personal data.
4. The built-in updater first verifies the update manifest's detached Ed25519 `.sig` signature with its pinned public key, then checks declared size and SHA-256. A signature, size, or digest failure prevents the downloaded file from starting.

The macOS/Linux Preview is not equivalent to the complete Windows build and may lack platform-store signing or notarization. Obtain it only from this project's Release and complete the source checks above. See [Preview packages](docs/PREVIEW-PACKAGES.md).

### Three things to do first

1. In the first-run wizard, review interface language, assistant name, the user's title, organization, work type, and wake word; existing settings are not overwritten.
2. Try a Windows local female voice first. When cloud AI is needed, enter a user-owned OpenAI API key in Settings. A ChatGPT subscription does not include API quota.
3. Review microphone, notification, and tool permissions and enable only the connectors you need. First learn the Esc emergency stop and the phrase “mohan stop.”

### Cloud connector setup

#### Google OAuth

Before using Gmail, Google Calendar, and Google Drive, complete these steps:

1. In a user-owned Google Cloud project, enable the Gmail API, Google Calendar API, and Google Drive API.
2. Configure the OAuth consent screen; while the application is in testing, add the user's Google account as a test user.
3. Create an OAuth Client ID for a Desktop application.
4. Open MoHan Settings → Flagship control center → Cloud Connectors, select Google（Gmail／Calendar／Drive）, and enter the OAuth Client ID; enter the OAuth Client Secret only if the provider supplies one.
5. Keep the default scopes below in OAuth scopes, press Open secure browser connection, complete browser authorization, and then press Test selected service.

The application requests these Google scopes by default:

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

A public OAuth application using sensitive scopes may require additional Google verification; each user may instead create a personal Desktop OAuth application.

#### Microsoft, GitHub, and Home Assistant

- Microsoft defaults: `openid`, `offline_access`, `User.Read`, `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, and `Files.ReadWrite`.
- GitHub defaults: `read:user` and `repo`.
- Home Assistant: first create a Long-Lived Access Token in the user's own Home Assistant profile; in MoHan Settings → Flagship control center → Smart Home, check Enable Home Assistant integration, enter the Home Assistant address and Long-lived access token, confirm Verify HTTPS certificate, press Save settings, then use Test connection or Load devices to confirm.

These three remain experimental Preview integrations without completed real-environment end-to-end validation. Begin with failure-tolerant test accounts and devices; never expose the Home Assistant or MoHan remote port directly to the public internet, and use Home Assistant Cloud, Tailscale, or another authenticated encrypted private network.

### Privacy and local-first behavior

- On Windows, conversations, memories, tasks, settings, work records, permissions, and audits stay by default in `%LOCALAPPDATA%\YanJianStudio\MoHan`; backups are in its backups subfolder, and portable data uses one `.mohan-profile`.
- Only when the user enables a relevant feature does the text, audio, or tool-planning context needed for that request go to OpenAI. OAuth services receive only user-consented API requests; Home Assistant receives local device requests.
- API keys and OAuth/Home Assistant tokens are stored separately with Windows DPAPI and never enter SQLite, source code, logs, or ordinary portable files. MoHan does not automatically gain access to ChatGPT account history.
- Camera, remote access, and cloud connectors are off by default. Raw camera frames are not retained, and permission or service failure disables only the affected path.

Multisensory vision is off by default. After the user explicitly enables it and confirms it by globally saving the settings, that choice is continuous authorization until the user turns it off; the app does not ask for consent frame by frame. The authorization status stays visible, with immediate revocation, cost limits, and a way to cancel unfinished analysis. Local OpenCV handles ongoing sensing; only at low frequency or on an event trigger is a temporary image sent to GPT-5.6. The app does not retain originals or log Base64, and it does not enable network access by itself. Missing camera, model, network, quota, or recognition disables only that path without harming other features. Read [Privacy](PRIVACY.md) and [Security](SECURITY.md) for the complete boundary.

### DLC and appearance customization

`.mohan-outfit` is the character-appearance container and may include garments, hairstyles, headwear, makeup, and accessories; a makeup-only pack uses the same format. `.mohan-theme` changes only control-panel colors, font, corner radius, and an optional background, not the character's appearance. Both are single, self-contained files that need no unpacking, are fully validated before installation, and cannot execute packaged code.

#### Install and select outfits or makeup

1. Download the `.mohan-outfit`; do not rename or unpack it.
2. Open the control center's Wardrobe Pavilion, press “Import outfit package,” and choose the file. Outfit and makeup packs share this entry point, validation, catalog, and removal flow.
3. Choose a package or complete look and press “Apply selected outfit.” For makeup, select classic, light, bare face, or an installed style in the makeup menu, then adjust intensity with the 0–100% slider.
4. To undo appearance customization, press “Restore built-in outfit”; choose built-in classic makeup or bare face for makeup. The built-in Blue-and-White Hanfu and makeup cannot be removed or shadowed by a package with the same id.

#### Install and restore themes

1. Download the `.mohan-theme`; do not unpack it.
2. In Settings → Dashboard theme, press “Upload one file,” choose the theme, and preview it from the list.
3. It takes effect only after “Save settings” at the lower right; cancel restores the previous theme. “Restore theme” previews the built-in theme, which is restored after saving.

#### Capacity, count, and compatibility

- One appearance pack is limited to 1 GiB, 2 GiB expanded, and 2,048 members; each member is limited to 128 MiB and each image edge to 4,096 px.
- One theme and its expanded contents are limited to 16 MiB; each member is limited to 12 MiB and each background edge to 4,096 px.
- Cloud-created outfits retain 16 packs, 6 GiB total, and 5 repair-review quarantine entries by default; the first two settings each allow 1–64. Generation stops at the limit and never auto-deletes user-imported packs.
- The current generation-2 rig accepts only `mohan-body-v2`. A generation-1 pack for the three-pose `mohan-body-v1` lacks the 31 silhouettes, anchors, and occlusion contract, so import and runtime both reject it. Rebuild against the generation-2 template with `tools/build_outfit_pack.py`, or regenerate it through one-click outfit creation.
- Installation is atomic after full validation. Absolute or traversing paths, executables, scripts, symlinks, encrypted members, decompression bombs, and undeclared assets are rejected.

See the [outfit-pack documentation](docs/OUTFIT-PACKS.md) for the complete authoring contract.

> #### ❤️⚔️ Support MoHan: Ko-fi sponsorship & cosmetic DLC downloads
>
> Sponsors obtain purely cosmetic appearance, makeup, and theme DLC by following the Ko-fi reward instructions. The current dual track is one-time or monthly support; neither grants functional privileges. Follow the relevant Ko-fi reward instructions for the download location and filename.

### Support MoHan: sponsorship and licensing

Use the Sponsor button displayed by GitHub above this repository, or visit [Ko-fi](https://ko-fi.com/flamebladestudio) directly. Ko-fi is the current official funding option and supports one-time or monthly contributions. Every feature remains free; support provides cosmetic DLC thank-you rewards only.

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="Proud MoHan"><br><strong>“I am not waiting for support... merely inspecting provisions.”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="Shy MoHan"><br><strong>“If you truly wish to help, I shall remember.”</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="MoHan says to give responsibly"><br><strong>“Do not overextend yourself. Care for your own purse first.”</strong></td>
  </tr>
</table>

- Author: **CHOU MING HUA**.
- Source code uses the [MIT License](LICENSE); the MoHan character artwork, persona, name, and likeness are All Rights Reserved and outside the MIT grant.
- Asset-production tools and weights admit only the MIT, Apache 2.0, CC0, CC BY (and equivalent BSD-class) allowlist. Fonts are the sole exception: since 2026-09-02, SIL OFL 1.1 is allowed for fonts only and does not extend to other materials. Character art remains the rights holder's proprietary property; see the [License Purity Commitment](docs/LICENSE-PURITY.md).
- Asset and third-party terms are in [ASSETS-LICENSE](ASSETS-LICENSE.md) and [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md).

This project follows the [Flameblade Open Source Software Family Quality Standard](PUBLISHING.md).

### Troubleshooting

- Windows SmartScreen or a platform warning: verify the GitHub Release source, `SHA256SUMS`, and Artifact Attestation first; do not disable system-wide protection.
- No conversation response: check your OpenAI API key, Project permission, quota, and network. A ChatGPT subscription cannot replace API quota.
- No sound: switch to a Windows local female voice first. Azure Speech requires the user's own key and matching region.
- DLC rejected: check file integrity, size, safe manifest, four-language names, and `mohan-body-v2` compatibility. A generation-1 pack must be rebuilt.
- Preview integration failure: begin with a non-critical account, test repository, or low-risk device. Microsoft, GitHub, and Home Assistant have not completed validation in every real environment.

Use [Issues](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues) for ordinary problems, [Discussions](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/discussions) for usage, and [SECURITY](SECURITY.md) for private security reports; plans are in the [ROADMAP](ROADMAP.md).

### Developer entry points

Start with [Architecture](ARCHITECTURE.md), [Testing](docs/TESTING.md), [Contributing](CONTRIBUTING.md), the [outfit-pack specification](docs/OUTFIT-PACKS.md), and [Publishing policy](PUBLISHING.md). The Windows installer uses the studio-maintained Python 3.15 runtime; source and CI use PEP 810 lazy imports, and documentation stays structurally complete in all four languages.

```powershell
py -3.15 -m ruff check .
py -3.15 tools/audit_python315_idioms.py
py -3.15 tools/check_four_language_docs.py
$env:QT_QPA_PLATFORM = "offscreen"
py -3.15 tests/run_all.py
```

The formal Windows packaging contract builds its first-party native module with Rust 1.97.1, Maturin 1.14.1, and PyO3 0.29.2. Rayon 1.12.0 parallelizes RGBA composition only at 262,144 pixels or above with multiple workers. PyBackedBytes avoids an extra input copy, but output still creates new bytes; no end-to-end zero-copy or unimplemented SIMD claim is made. The OpenAI Responses API uses standard-library HTTPS directly; MoHan has no `openai` Python SDK runtime dependency.

## 日本語

[繁體中文](#繁體中文) · [簡體中文](#简体中文) · [English](#english) · [日本語](#日本語)

<p align="center"><img src="docs/media/mohan-hero.png" alt="墨寒デスクトップアシスタントのメインビジュアル" width="100%"></p>

<p align="center"><strong>墨寒は、安全性、プライバシー、キャラクターの連続性を重視する Windows 音声対話型デスクトップアシスタントです。</strong></p>

<p align="center">[Windows インストーラーをダウンロード](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) · [クイックスタート](QUICKSTART.md) · [クロスプラットフォーム機能表](docs/CROSS-PLATFORM.md)</p>

> **作者：CHOU MING HUA** · Windows 10/11 完全版 · macOS／Linux 機能限定 Preview<br>**最新正式リリース：** `v4.6.0`（2026 年 8 月 29 日）。実際の成果物は本版の最終公開ゲートに合格する必要があります。最新の公開版は動的バッジと [Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) を基準とします。<!-- x-release-please-version-date -->

### これは何か

墨寒は、安全性、プライバシー、キャラクターの連続性を重視する Windows 音声対話型デスクトップアシスタントです。透明な 2.5D キャラクター、自然な音声、利用者が管理するローカル長期記憶、タスク、作業ツールを統合しています。物語上は北宋から来た、赤焰剣に宿る千年の女剣魂です。

<p align="center">
  <img alt="Windows CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Latest Published Release" src="https://img.shields.io/github/v/release/flameblade-studio/MoHan-PC-Desktop-Assistant?include_prereleases&label=published">
</p>

<details>
<summary>その他の CI・セキュリティ・Python・4言語バッジ</summary>

<p align="center">
  <img alt="Cross-platform core CI" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg">
  <img alt="CodeQL" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg">
  <img alt="Python Security Audit" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg">
  <img alt="Extended Secret Defense / Gitleaks" src="https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg">
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>
</details>

### 画面と機能の一覧

[36 秒の実機デモを見る](docs/media/mohan-demo.mp4)。設定と主な画面：[初回設定](docs/media/first-run-wizard.png)、[音声モード](docs/media/voice-modes.png)、[表情](docs/media/expressions.png)、[タスクとアイデア](docs/media/tasks-and-ideas.png)、[長期記憶](docs/media/long-term-memory.png)、[安全権限](docs/media/security-permissions.png)。

- 透明デスクトップキャラクター、まばたき、表情、動作、50 Hz リップシンク。
- テキスト、Realtime、Windows 本機女性音声、OpenAI TTS、任意の Azure Speech 経路。
- 会話、編集可能な記憶、タスク、アイデア、作業タイマー、リマインダー、可搬プロファイル。
- ツール実行は権限、危険度、確認、監査、緊急停止を通過します。
- Google は実接続検証済みです。Microsoft、GitHub、Home Assistant は実験的 Preview のままです。
- マルチセンサー視覚、ジェスチャー、遠隔アクセス、クラウド連携は既定で無効で、個別に取り消せます。

#### 日本語の対応範囲

繁体字中国語、簡体字中国語、英語、日本語は、初回設定、会話、音声、権限、基本設定、作業モード、リマインダーに対応します。高度な画面には繁体字中国語が残る場合があります。Azure Speech（プレビュー）の実際の音声、リージョン、割り当て、費用は、利用者自身のサービスアカウントに依存します。

### 墨寒のツンデレ開発小劇場

六枚の半身表情は、第二世代素体、公式の藍白漢服、内蔵の基本メイクを正式な実行時経路で合成した固定素材です。

<table>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/proud_front.png" width="220" alt="誇らしげな墨寒"><br><strong>「Star を待っていたのではありません。士気を確認していただけです。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/thinking_front.png" width="220" alt="考える墨寒"><br><strong>「このロジックは悪くありません。テストを足せば main 入りを許しましょう。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/shy_cute_front.png" width="220" alt="照れる墨寒"><br><strong>「PR を送るのですか？　功績を記録するだけです。」</strong></td>
  </tr>
  <tr>
    <td width="33%" align="center"><img src="docs/media/portraits/mock_hit_front.png" width="220" alt="怒ったふりをする墨寒"><br><strong>「テストなしでマージ？　手を出しなさい。一度だけです。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/gentle_smile_front.png" width="220" alt="微笑む墨寒"><br><strong>「すべて緑……よくできました。良い設計を尊重しただけです。」</strong></td>
    <td width="33%" align="center"><img src="docs/media/portraits/worried_front.png" width="220" alt="心配する墨寒"><br><strong>「Bug は明日でも直せます。倒れたら誰が剣を守るのですか？」</strong></td>
  </tr>
</table>

<table>
  <tr>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-code-review.png" width="100%" alt="コードを審査するちび墨寒"><br><strong>策士の審査</strong><br>main に入れる品質か確認します。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-praised.png" width="100%" alt="褒められたちび墨寒"><br><strong>褒められた時</strong><br>悪くありません。見つめないで。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-dangerous-action.png" width="100%" alt="危険操作を止めるちび墨寒"><br><strong>危険操作</strong><br>未確認なら、この剣を越えてから。</td>
    <td align="center" valign="top" width="25%"><img src="docs/media/mohan-chibi-provisions.png" width="100%" alt="支援を受け取るちび墨寒"><br><strong>兵糧を受領</strong><br>この気持ちは覚えておきます。</td>
  </tr>
</table>

### インストールと更新

1. [GitHub Releases](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases) から、末尾が `Windows-x64-Setup.exe` のインストーラーを取得します。上級者は完全な `Windows-x64.zip` または MSI も選べます。
2. インストール前に `SHA256SUMS` と GitHub Artifact Attestation を検証します。配布元、ファイル名、ハッシュが異なる場合は停止し、システム全体の保護を無効にしないでください。
3. インストーラーを起動するか、ZIP を完全展開して EXE、内部フォルダー、assets を同じ場所に保ちます。更新でローカル個人データは削除されません。
4. 内蔵アップデーターは、埋め込み公開鍵で更新マニフェストの Ed25519 分離 `.sig` 署名を検証し、次に宣言サイズと SHA-256 を照合します。署名、サイズ、ハッシュのいずれかが失敗すると、ダウンロードしたファイルを起動しません。

macOS／Linux Preview は Windows 完全版と同等ではなく、プラットフォームストア署名や公証がない場合があります。本プロジェクトの Release だけから取得し、上記の配布元検証を完了してください。[Preview パッケージ説明](docs/PREVIEW-PACKAGES.md)も参照してください。

### 最初に行う三つのこと

1. 初回設定で、画面言語、アシスタント名、利用者の呼び名、組織、作業内容、ウェイクワードを確認します。既存設定は上書きしません。
2. まず Windows 本機女性音声を試します。クラウド AI が必要な場合だけ、利用者自身の OpenAI API キーを設定に入力します。ChatGPT の契約に API 割り当ては含まれません。
3. マイク、通知、ツール権限を確認し、必要な連携だけを有効にします。先に Esc の緊急停止と「墨寒、止まって」を覚えてください。

### クラウド連携の設定

#### Google OAuth

Gmail、Google Calendar、Google Drive を利用する前に、次を完了してください。

1. 利用者自身の Google Cloud プロジェクトで Gmail API、Google Calendar API、Google Drive API を有効にします。
2. OAuth 同意画面を設定します。アプリケーションがテスト中の間は、自分の Google アカウントをテストユーザーに追加します。
3. Desktop アプリケーション用の OAuth Client ID を作成します。
4. 墨寒の「設定」→「フラッグシップ操作センター」→「クラウド接続」を開き、Google（Gmail／Calendar／Drive）を選んで OAuth Client ID を入力します。OAuth Client Secret は、サービスから発行された場合だけ入力します。
5. 「認可スコープ」に以下の既定値を残し、「ブラウザーで安全に接続」を押してブラウザー認可を完了し、「選択したサービスをテスト」を押します。

アプリケーションが既定で要求する Google scopes：

```text
openid
email
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
```

機密 scopes を使う公開 OAuth アプリケーションは、Google の追加検証が必要になる場合があります。各利用者が個人用 Desktop OAuth アプリケーションを作ることもできます。

#### Microsoft、GitHub、Home Assistant

- Microsoft の既定 scopes：`openid`、`offline_access`、`User.Read`、`Mail.ReadWrite`、`Mail.Send`、`Calendars.ReadWrite`、`Files.ReadWrite`。
- GitHub の既定 scopes：`read:user`、`repo`。
- Home Assistant：まず自分の Home Assistant プロフィールで Long-Lived Access Token を作成します。墨寒の「設定」→「フラッグシップ操作センター」→「スマートホーム」で「Home Assistant 連携を有効化」をチェックし、「Home Assistant アドレス」と「長期アクセストークン」を入力します。「HTTPS 証明書を検証」を確認して「設定を保存」を押し、「接続をテスト」または「機器を読み取る」で確認します。

この三つは実環境での完全なエンドツーエンド検証が未完了の実験的 Preview 連携です。失敗を許容できるテスト用アカウントと機器から始め、Home Assistant や墨寒のリモートポートを公衆インターネットへ直接公開しないでください。Home Assistant Cloud、Tailscale、または認証付き暗号化プライベートネットワークを利用してください。

### プライバシーとローカル優先

- Windows では、会話、記憶、タスク、設定、作業記録、権限、監査を既定で `%LOCALAPPDATA%\YanJianStudio\MoHan` に保存します。バックアップは backups サブフォルダーにあり、可搬データには単一の `.mohan-profile` を使います。
- 利用者が関連機能を有効にした場合だけ、その要求に必要なテキスト、音声、ツール計画を OpenAI へ送ります。OAuth サービスは利用者が同意した API 要求だけを受け取り、Home Assistant はローカル機器要求を受け取ります。
- API キーと OAuth／Home Assistant トークンは Windows DPAPI で分離保存し、SQLite、ソースコード、ログ、通常の可搬ファイルには入りません。墨寒が ChatGPT アカウント履歴を自動取得することもありません。
- カメラ、遠隔アクセス、クラウド連携は既定で無効です。元のカメラフレームは保存せず、権限やサービスの失敗は該当経路だけを停止します。

マルチセンサー視覚は既定で無効です。利用者がコントロールセンターで明示的に有効化して全体設定を保存すると、自ら無効にするまで継続的な許可となり、フレームごとに許可を求めることはありません。許可状態は常に表示し、直ちに取り消せるほか、費用の上限を設定して未完了の解析を取り消せます。端末内の OpenCV が継続検知を担当し、低頻度またはイベント発生時だけ一時画像を GPT-5.6 へ送ります。元画像を保存せず、Base64 をログへ残さず、システムが自らネットワークを有効にしません。カメラ、モデル、ネットワーク、割り当て、認識が不足する場合は該当経路だけを停止し、他の機能へ影響しません。完全な境界は [プライバシー](PRIVACY.md) と [セキュリティ](SECURITY.md) を参照してください。

### DLC と外観のカスタマイズ

`.mohan-outfit` はキャラクター外観のコンテナーで、衣装、髪型、髪飾り、メイク、アクセサリーを収録できます。メイク専用パックも同じ形式です。`.mohan-theme` はコントロールパネルの色、フォント、角丸、任意の背景だけを変更し、キャラクター外観は変えません。どちらも単一で自己完結し、解凍不要です。導入前に全体を検証し、同梱コードを実行しません。

#### 衣装とメイクの導入・選択

1. `.mohan-outfit` をダウンロードし、拡張子を変えたり解凍したりしないでください。
2. コントロールセンターの「雲裳閣」を開き、「衣装パッケージをインポート」でファイルを選びます。衣装とメイクは同じ入口、検証、一覧、削除経路を使います。
3. パッケージまたは一式を選び、「選択した衣装を適用」を押します。メイクは基本、淡め、すっぴん、導入済みスタイルから選び、0–100% スライダーで濃さを調整します。
4. カスタム外観を取り消すには「内蔵衣装に戻す」を押し、メイクは内蔵の基本メイクまたはすっぴんを選びます。内蔵の藍白漢服とメイクは削除できず、同じ id のパッケージで置き換えられません。

#### テーマの導入と復元

1. `.mohan-theme` をダウンロードし、解凍しないでください。
2. 「設定」→「コントロールセンターのテーマ」で「ファイルを1つアップロード」を押し、テーマを選んで一覧からプレビューします。
3. 右下の「設定を保存」を押した時だけ反映され、取り消すと元のテーマへ戻ります。「テーマを元に戻す」で内蔵テーマをプレビューし、保存すると復元が完了します。

#### 容量・数量・互換性

- 外観パック一件は最大 1 GiB、展開後最大 2 GiB、最大 2,048 メンバーです。各メンバーは最大 128 MiB、画像の各辺は最大 4,096 px です。
- テーマ一件と展開後の合計は最大 16 MiB、各メンバーは最大 12 MiB、背景の各辺は最大 4,096 px です。
- クラウド自作衣装は既定で 16 パック、合計 6 GiB、修復審査用隔離 5 件を保持します。前二項はそれぞれ 1–64 に設定できます。上限では生成を停止し、利用者がインポートしたパックを自動削除しません。
- 現行の第二世代 rig は `mohan-body-v2` だけを受理します。三姿勢の `mohan-body-v1` 用第一世代パックには 31 silhouette、anchor、occlusion 契約がないため、インポート時と実行時に拒否します。`tools/build_outfit_pack.py` で第二世代テンプレートに対して再構築するか、「ワンクリック衣装生成」で作り直してください。
- 導入は完全検証後にアトミックに行います。絶対／横断パス、実行ファイル、スクリプト、シンボリックリンク、暗号化メンバー、解凍爆弾、未宣言素材は拒否します。

完全な制作契約は [外観パック文書](docs/OUTFIT-PACKS.md) を参照してください。

> #### ❤️⚔️ 墨寒を支援：Ko-fi スポンサー＆装飾 DLC ダウンロード
>
> 支援者は Ko-fi の謝礼案内に従い、外観、メイク、テーマなど純装飾 DLC を取得できます。現在は単発支援と毎月支援の二本立てで、機能上の特権はありません。ダウンロード先とファイル名は、該当する Ko-fi の謝礼案内に従ってください。

### 墨寒を支援：支援とライセンス

このリポジトリ上部に GitHub が表示する Sponsor ボタンをご利用いただくか、[Ko-fi](https://ko-fi.com/flamebladestudio) へ直接お越しください。現在の正式な支援先は Ko-fi で、単発または毎月の支援を選べます。全機能は常に無料で、支援の謝礼は純装飾 DLC だけです。

<table>
  <tr>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-proud.png" width="220" height="220" alt="誇らしげな墨寒"><br><strong>「支援を待ってなどいません。兵糧を巡回しているだけです。」</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-shy-aligned.png" width="220" height="220" alt="照れる墨寒"><br><strong>「本当に助けてくださるなら、覚えておきます。」</strong></td>
    <td align="center" valign="top" width="33%"><img src="docs/media/support-mock-hit.png" width="220" height="220" alt="無理な支援を止める墨寒"><br><strong>「無理は禁止です。まず自分のお財布を守りなさい。」</strong></td>
  </tr>
</table>

- 作者：**CHOU MING HUA**。
- ソースコードは [MIT License](LICENSE) です。「墨寒」のキャラクター美術、人物設定、名称、肖像はすべての権利を留保し、MIT の許諾範囲外です。
- 素材生成の道具と重みは MIT、Apache 2.0、CC0、CC BY（および同等の BSD 系）ホワイトリストだけを受理します。フォントが唯一の例外で、2026-09-02 以降は SIL OFL 1.1 をフォントに限って認め、他の素材には拡張しません。キャラクター美術は権利者の専有財産です。詳しくは [ライセンス純浄性の約束](docs/LICENSE-PURITY.md) を参照してください。
- 素材と第三者条項は [ASSETS-LICENSE](ASSETS-LICENSE.md) と [THIRD-PARTY-NOTICES](THIRD_PARTY_NOTICES.md) に記載しています。

本プロジェクトは [炎剣オープンソース・ソフトウェア・ファミリー品質基準](PUBLISHING.md) に従います。

### トラブルシューティング

- Windows SmartScreen またはプラットフォーム警告：GitHub Release の配布元、`SHA256SUMS`、Artifact Attestation を先に確認し、システム全体の保護を無効にしないでください。
- 会話が返らない：利用者自身の OpenAI API キー、Project 権限、割り当て、ネットワークを確認してください。ChatGPT 契約は API 割り当ての代わりになりません。
- 音が出ない：まず Windows 本機女性音声へ戻してください。Azure Speech には利用者自身のキーと対応リージョンが必要です。
- DLC が拒否される：ファイルの完全性、容量、安全な manifest、四言語名、`mohan-body-v2` 互換性を確認してください。第一世代パックは再構築が必要です。
- Preview 連携が失敗する：重要でないアカウント、テスト用リポジトリ、低リスク機器から始めてください。Microsoft、GitHub、Home Assistant は全実環境での検証を完了していません。

一般的な問題は [Issues](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues)、利用相談は [Discussions](https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/discussions)、セキュリティ問題は [SECURITY](SECURITY.md) から非公開で報告してください。計画は [ROADMAP](ROADMAP.md) にあります。

### 開発者向け入口

最初に [アーキテクチャ](ARCHITECTURE.md)、[テスト説明](docs/TESTING.md)、[貢献ガイド](CONTRIBUTING.md)、[外観パック仕様](docs/OUTFIT-PACKS.md)、[公開方針](PUBLISHING.md) をお読みください。Windows インストーラーは、スタジオ管理の Python 3.15 実行環境を使用します。ソースと CI は PEP 810 遅延インポートを採用し、文書は四言語で同じ構造を維持します。

```powershell
py -3.15 -m ruff check .
py -3.15 tools/audit_python315_idioms.py
py -3.15 tools/check_four_language_docs.py
$env:QT_QPA_PLATFORM = "offscreen"
py -3.15 tests/run_all.py
```

Windows 正式パッケージ化の契約では、Rust 1.97.1、Maturin 1.14.1、PyO3 0.29.2 で第一者ネイティブモジュールを構築します。Rayon 1.12.0 は 262,144 pixels 以上かつ複数ワーカーがある場合だけ RGBA 合成を並列化します。PyBackedBytes は余分な入力コピーを避けますが、出力は新しい bytes を生成するため、エンドツーエンドのゼロコピーや未実装の SIMD を主張しません。OpenAI Responses API は標準ライブラリ HTTPS を直接使い、墨寒には `openai` Python SDK の実行時依存がありません。
