# MoHan Desktop Assistant / 墨寒桌面語音互動虛擬助理

<p align="center">
  <img src="assets/mohan.png" alt="MoHan character" width="320">
</p>

<p align="center">
  <strong>Author / 軟體作者：CHOU MING HUA</strong><br>
  Current public preview / 目前公開預覽版：v2.0.14 RC<br>
  Windows 10/11 · Python 3.12 · PySide6 · MIT License
</p>

> 墨寒是一套重視安全、隱私與角色連續感的 Windows 語音互動桌面助理，
> 結合透明桌面角色、自然語音、長期記憶、工作管理、權限控管工具，以及
> 可擴充的雲端與智慧家庭連接器。

> MoHan is a safety-first, voice-interactive Windows desktop companion combining
> an animated character, natural voice, user-controlled long-term memory,
> productivity workflows, permission-gated tools, and extensible cloud and
> smart-home connectors.

- [繁體中文](#繁體中文)
- [English](#english)

---

# 繁體中文

## 專案特色

- 透明、無邊框的桌面半身角色，可固定在工具列上方。
- 待機呼吸、眨眼、注視、臉部視差、髮絲、衣袖、飾品與身體微轉向。
- 具表情仲裁器的情緒系統，避免待機時出現不合情境的表情。
- AIUEO 母音嘴型、子音嘴型、音訊驅動開合與語音結束強制閉嘴。
- 文字聊天、一般麥克風輸入、OpenAI Realtime 自然語音與 Windows 語音備援。
- 對話保存、可編輯長期記憶、待辦、創作靈感、工作計時、提醒與上架進度。
- 工作、陪伴、勿擾、會議、離開及睡眠模式。
- 具風險分級、確認、雙重確認、允許清單、稽核與緊急停止的電腦工具中心。
- Google、Microsoft、GitHub、Home Assistant 與私人網路遠端功能的擴充架構。
- 單一 `.mohan-profile` 可攜檔，可在不同 Windows 電腦間轉移工作進度。
- 首次啟動精靈可自訂助理名稱、使用者稱呼、組織名稱、視窗標題、工作類型與
  喚醒詞；現有個人安裝的設定不會被公開版預設覆蓋。

目前程式操作介面以臺灣繁體中文為主，英文介面尚未完成。

## 整合驗證狀態

> **公開預覽版注意事項：** Microsoft 套件、GitHub 與 Home Assistant 的
> 程式架構、權限邊界及內部測試已建置，但截至 v2.0.14 RC，尚未使用真實
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
| 文字對話 | `gpt-5.4-mini` |
| Realtime 即時語音 | `gpt-realtime-2.1-mini` |
| 語音轉文字 | `gpt-4o-mini-transcribe` |
| OpenAI 文字轉語音 | `gpt-4o-mini-tts` |

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

需求：Windows 10/11、Python 3.12+。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## 測試、公開稽核與封裝

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.0.14-RC"
```

v2.0.14 RC 在封裝前通過 38 項自動測試，以及 25,000 次表情、姿勢、語音、
注視與物理混合壓力測試。測試不能取代尚未完成的第三方真實環境驗證。

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
- 維護者發布設定、Topics 與首發檢查見 [PUBLISHING.md](PUBLISHING.md)。

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.

---

# English

## Overview

MoHan Desktop Assistant is a configurable Windows companion and
permission-gated productivity assistant built with Python and PySide6.

Key capabilities:

- Transparent half-body desktop character positioned above the taskbar.
- Breathing, blinking, gaze, face parallax, hair, sleeve, ornament, and body
  micro-turn animation.
- Context-controlled expression arbitration and AIUEO viseme lip synchronization.
- Text chat, microphone input, OpenAI Realtime voice, cloud TTS, and Windows TTS
  fallback.
- Persistent conversations, editable long-term memory, tasks, ideas, work
  sessions, reminders, and customizable progress trackers.
- Work, companion, do-not-disturb, meeting, away, and sleep modes.
- Permission-gated tools with risk levels, allowlists, confirmation, double
  confirmation, result verification, audit logs, and emergency stop.
- Portable one-file profile handoff between Windows computers.
- A first-run wizard for assistant name, user title, organization, window title,
  work type, UI language, and wake word.

The current application interface is primarily Taiwan Traditional Chinese.
Complete English UI localization is not yet available.

## Integration verification status

> **Public preview notice:** Microsoft, GitHub, and Home Assistant connector
> architecture, permission boundaries, and internal tests are implemented.
> As of v2.0.14 RC, they have **not** completed end-to-end validation with a
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
| Text conversation | `gpt-5.4-mini` |
| Realtime voice | `gpt-realtime-2.1-mini` |
| Speech-to-text | `gpt-4o-mini-transcribe` |
| OpenAI text-to-speech | `gpt-4o-mini-tts` |

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

Requirements: Windows 10/11 and Python 3.12+.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Audit, test, and build

```powershell
python tools\audit_public_release.py
python tests\run_all.py
.\build.ps1 -Version "2.0.14-RC"
```

Before packaging, v2.0.14 RC passed 38 automated test programs and a
25,000-step mixed expression, pose, speech, gaze, and physics stress test.
Automated tests do not replace uncompleted third-party live verification.

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
- Maintainer publication settings and Topics: [PUBLISHING.md](PUBLISHING.md)

Copyright © 2026 **CHOU MING HUA** and MoHan Desktop Assistant contributors.
