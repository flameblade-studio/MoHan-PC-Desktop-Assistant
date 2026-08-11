# GitHub 發布設定／GitHub 发布设置／GitHub Publication Settings／GitHub 公開設定

## 繁體中文

### 儲存庫說明

以安全為先、以 Windows 為主要平台的語音互動桌面伴侶，具備動畫表情、記憶、權限閘門工具，以及供社群驗證且限制清楚的 macOS／Linux Preview 套件。

### 儲存庫 Topics

GitHub 儲存庫應使用下列 Topics：

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
macos
linux
appimage
python
pyside6
openai-api
realtime-api
speech-recognition
text-to-speech
long-term-memory
lip-sync
animated-character
productivity
home-assistant
traditional-chinese
taiwan
open-source
```

### 已準備的公開預發行版

- 標籤：`v3.1.1`
- 標題：`MoHan Desktop Assistant v3.1.1`
- 發布條件：只有在所有必要 CI、套件 smoke、安全及發布政策檢查成功後才可發布。
- 內容包含 Windows x64 可攜式 ZIP、每位使用者安裝的 EXE 與 MSI、英文／簡體中文／日文 MSI 轉換檔、macOS Apple Silicon（arm64）與 Intel（x86_64）功能受限 Preview DMG、Linux x86_64 功能受限 Preview AppImage、SHA-256 清單、可重現的 CycloneDX 1.7 SBOM 與驗證報告、已去識別化的 Tachyon 證據與效能摘要、更新資訊清單及產物證明。

### 後續發行系列

- 可接受的發行標籤只能是不可變的 `vN.N.N` 正式版或 `vN.N.N-rc.N` 候選版，其中 RC 編號必須是正整數；其他標籤必須在封裝或發布前失敗。
- Windows 維持正式且完整的產品範圍，並保留已驗證的 x64 ZIP、EXE、MSI 及 MSI 語言轉換檔。
- macOS 分別提供原生 Apple Silicon（arm64）與 Intel（x86_64）`.dmg`，各自包含架構相符的 `.app`；Linux x86_64 提供 `.AppImage`。這些套件都必須明確標示為功能受限的 Preview：只驗證啟動、四語顯示、每位使用者路徑與安全失效關閉的平台邊界，不代表與 Windows 功能相同。
- Pull Request 只能為套件測試建立短期 CI 產物，不得建立 GitHub Release；只有既存且符合規則的正式版或候選版標籤能進入發布工作流程。
- Release 說明必須來自人工整理的四語檔案 `docs/releases/<tag>.md`，不能只使用自動產生的說明。

### 歷史首發版本

- 標籤：`v2.0.14-rc.1`
- 標題：`MoHan Desktop Assistant v2.0.14 RC — First Public Preview`
- 因 Microsoft、GitHub 與 Home Assistant 尚未完成真實環境端對端驗證，必須標示為預發行版。
- 必須附上 Windows x64 ZIP 與相符的 SHA-256 文字檔。

### 發布前必要檢查

```powershell
python tools\audit_public_release.py
python tests\run_all.py
git diff --check
```

絕對不得發布 `.env`、API 金鑰、OAuth 認證資料／權杖、Home Assistant 權杖、SQLite 資料庫、`.mohan-profile` 檔案、錄音、本機日誌或個人設定。

### 重建 README 媒體

媒體產生器會使用隔離的暫存設定檔啟動真實 Qt 介面、植入僅供示範的內容、擷取文件記載的頁面，並產生 36 秒的 H.264／AAC 示範影片；它絕不讀取維護者平常使用的墨寒設定檔。

```powershell
$env:QT_QPA_PLATFORM = "windows"
python tools\capture_readme_media.py --ffmpeg "C:\path\to\ffmpeg.exe"
```

若只要更新目前 UI 截圖而不重建示範影片，請使用：

```powershell
python tools\capture_readme_media.py --screenshots-only
```

提交重新產生的媒體前：

1. 以完整尺寸檢查每張 PNG，確認沒有文字遭裁切、字元圖形損壞或意外包含個人資料。
2. 確認 `docs/media/mohan-demo.mp4` 長度為 30–60 秒、解析度為 1280×720，且包含 H.264 視訊串流及非靜音 AAC 音訊串流。
3. 再次執行公開發行稽核及完整測試套件。

### 受保護 main 發布流程

儲存庫的所有變更都必須使用 Pull Request。不得將實作提交直接推送至 `main`、不得略過檢查、不得強制推送 `main`，也不得在必要檢查失敗或審查對話尚未解決時合併。必要的 Windows CI 檢查是 `Windows CI / test`；安全工作流程也必須完成，且不得留有尚未處理的高信心發現。

本儲存庫的既定合併政策只允許 squash。所有必要檢查成功、Pull Request 的 head SHA 未變且審查對話全部解決後，Codex 應直接使用 squash 合併；不得在每次發布時重新查詢這項已知政策，也不得先嘗試已知不允許的 merge commit 或 rebase。合併後必須讀回實際 merge commit，發布標籤只能建立在該 commit。只有擁有者明確變更設定，或 GitHub 實際拒絕 squash 而顯示政策可能漂移時，才重新查詢。

GitHub 自動化必須使用一條可預測的憑證路徑。Pull Request 的讀取與更新優先使用已連線的 GitHub 介面；本機 push 使用 Git 自身的憑證管理；`gh` 只保留給已連線介面尚未提供的 GitHub Actions 檢查與記錄。若 `gh auth status` 一次確認憑證失效，在外部狀態未改變前不得反覆重試、登出或重新登入；應直接改用已連線介面或已登入瀏覽器。只有必要操作沒有等價途徑且確實被阻擋時，才請擁有者重新驗證一次。任何流程都不得顯示、複製、寫檔或提交 Token。

### 自動化後續發行

只有符合 `vN.N.N` 或 `vN.N.N-rc.N` 的標籤能觸發 `.github/workflows/release.yml`。工作流程會驗證精確標籤、簽出該不可變的來源修訂，然後依序：

任何平台封裝開始前，快速閘門必須先確認標籤、版本與 `main` 歷史一致，檢查本次模式所要求的 Release 存在或不存在，並以 Python 3.15 驗證人工整理的四語 Release 說明。這些便宜且具決定性的檢查不得延後到長時間建置之後；發布前仍須再次驗證標籤、產物與 Release 狀態，以防執行期間發生漂移。

1. 安裝已鎖定版本的執行期與發行相依套件；
2. 編譯並稽核公開原始碼樹；
3. 執行完整回歸測試套件；
4. 擷取啟動、50 Hz 嘴型同步與表情仲裁的已去識別化 Python 3.15 Tachyon 證據，接著以取樣數、堆疊讀取錯誤、遺漏取樣、目標結束狀態與 JIT 狀態作為閘門；
5. 使用 PyInstaller 建置 Windows x64 應用程式；
6. 執行封裝後自我測試與事件迴圈 smoke test；
7. 產生可攜式 ZIP，以及每位使用者安裝的 EXE 與 MSI；
8. 靜默安裝、自我測試並移除兩種安裝格式；
9. 在架構相符的原生 runner 上分別建置功能受限的 macOS Apple Silicon（arm64）與 Intel（x86_64）Preview，掛載兩個 DMG，並對每個封裝後的 `.app` 執行契約 smoke test；
10. 在原生 Linux runner 上建置功能受限的 Linux x86_64 Preview，並對封裝後的 `.AppImage` 執行契約 smoke test；
11. 使用獨立的唯讀中繼資料工作產生權威 `SHA256SUMS`、相容 SHA-256 清單、對應精確 Windows 與 Preview 執行期相依集合的獨立可重現 CycloneDX 1.7 SBOM、機器可讀的結構描述／授權／PURL／相依性／隱私驗證報告，以及 Windows 相容的更新資訊清單；
12. 在最小權限發布工作中重新檢查精確產物集合及每個已列入清單的 SHA-256 值；
13. 在發布前立即重新解析標籤，若標籤已移動或遭替換便拒絕發布；
14. 為每個發布檔案建立 GitHub 產物來源證明；
15. 要求並發布人工整理的四語 Release 說明。

`vN.N.N-rc.N` 必須發布為 Pre-release，純 `vN.N.N` 必須發布為 Stable Release；工作流程會阻擋標籤與成熟度不一致。不得重複使用或移動任何已發布標籤。

發布中繼資料工作必須以已保存的 Python 3.15 執行路徑執行所有墨寒專案工具。隔離的 Python 3.14 只能用於尚未支援 3.15 的第三方 SBOM 工具鏈，不得透過 `PATH` 改變後續專案工具的執行環境。

發行與 PR 套件工作流程會將每個 GitHub Action 鎖定至完整 commit。Linux 封裝還會把官方 `appimagetool` 產物鎖定至來源 commit `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`、產物 ID `324406882` 及 SHA-256 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`。

Windows 安裝程式建置會鎖定 Inno Setup `7.0.2` 與 WiX `7.0.0`。Inno Setup 編譯器只能從不可變的官方 `jrsoftware/issrc` Release 下載，使用前必須驗證 GitHub Release 證明與 Pyrsys B.V. Authenticode 簽章。WiX 會使用已明確授權的 `-acceptEula wix7` CI 引數，並使用持續維護的 `Files` harvester，而非已移除的 Heat 工具。

每份 Pull Request 內文與每份人工整理的 Release 說明都必須依序包含完整且非空白的 `## 繁體中文`、`## 简体中文`、`## English`、`## 日本語` 四個章節。必須翻譯該次變更或標籤當時真正成立的事實，不得把後來新增的功能倒填到歷史 PR 或 Release；自動產生的分類標題也要使用相同四語順序。只提供象徵性的一行翻譯，不能取代變更、原因、使用者影響與驗證資訊。

每份四語文件若有 H1，H1 必須依繁中、簡中、English、日文順序並以全形斜線 `／` 分隔；四個語言章節前除該 H1 與空白外，不得出現 prose、徽章、連結或警告。四個語言章節的 H3 以上標題數、段落數、條列數、連結與圖片目的地、code fence，以及 inline-code 技術 token 都必須對等；所有文字、段落、條列、連結、警告與程式碼範例均須完整翻譯且不得扭曲技術術語、版本、路徑、命令或安全邊界。

### 炎劍開源軟體家族品質標準

這是墨寒、FB2Blogger 與 FB2WordPress 共用的長期維護契約；新增炎劍開源軟體時，也必須直接沿用，不得另建降低標準的例外流程。

> **炎劍開源核心宣言：**「劍，我已鍛成；餘下的路，就交給你們了。」

1. 四語一致：重要 README、PR、Release 與使用引導皆維持繁中、簡中、英文、日文事實一致。
2. 真實驗證：只展示實際執行的 CI 與安全掃描，不以徽章代替測試結果。
3. 絕無機密：金鑰、權杖、個資、資料庫與私人內容不得進入版本庫或發布產物。
4. 產物可追溯：發布檔對應明確的標籤與提交，並提供雜湊或同等驗證資料。
5. 不退步：不得為新功能破壞既有正常功能、資料相容性、安全閘門或確認流程。
6. 不誇大平台：CI 通過不等於真機驗證；未實測的平台與功能必須清楚標示限制。
7. 同步對外資訊：程式、文件、Release 與官網的版本、連結及可見行為須保持一致。
8. 拒絕單次手工例外：優先建立可重複、自動化、可測試的流程，不靠臨時人工補救維護。

### 驗證 Release 產物

Release 產物可使用下列命令驗證：

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

### 官網同步

GitHub 發行工作刻意禁止寫入 WordPress，也不保存 WordPress Application Password。共用的 Flameblade Product Release Hub 是三個軟體產品的單一權威來源；其 `flameblade-series-gateway/products.json` 設定會識別每項產品的公開 GitHub 儲存庫與官網目的地。WordPress 端 gateway 依每小時排程讀取公開 GitHub Releases，並更新版本、連結及驗證資訊，不會把安裝程式複製到 Bluehost 儲存空間。

此設計讓官網認證資料留在每個產品儲存庫之外，也避免出現三套彼此競爭的「Release 至官網」實作。新發布的 Release 最晚可能要到下一次每小時更新才會出現在官網；若超過該時間仍未更新，應診斷共用 gateway，不得在此儲存庫加入一次性、直接寫入 WordPress 的步驟。

### 延伸祕密掃描

儲存庫會持續啟用 GitHub secret scanning 與 push protection，並在 Pull Request、`main` 及每週排程執行完整歷史 Gitleaks 檢查。GitHub 帳號層級的非供應商 pattern 與合作夥伴 validity 開關，需要由組織擁有、採用 GitHub Team／Enterprise 且具備 GitHub Secret Protection 的儲存庫；個人公開儲存庫無法啟用這兩項付費組織控制。GitHub 免費的供應商掃描仍保持啟用。

## 简体中文

### 仓库说明

以安全为先、以 Windows 为主要平台的语音交互桌面伴侣，具备动画表情、记忆、权限关卡工具，以及供社区验证且限制清楚的 macOS／Linux Preview 软件包。

### 仓库 Topics

GitHub 仓库应使用以下 Topics：

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
macos
linux
appimage
python
pyside6
openai-api
realtime-api
speech-recognition
text-to-speech
long-term-memory
lip-sync
animated-character
productivity
home-assistant
traditional-chinese
taiwan
open-source
```

### 已准备的公开预发布版

- 标签：`v3.1.1`
- 标题：`MoHan Desktop Assistant v3.1.1`
- 发布条件：只有在所有必要 CI、软件包 smoke、安全及发布政策检查成功后才可发布。
- 内容包括 Windows x64 便携式 ZIP、按用户安装的 EXE 与 MSI、英文／简体中文／日文 MSI 转换文件、macOS Apple Silicon（arm64）与 Intel（x86_64）功能受限 Preview DMG、Linux x86_64 功能受限 Preview AppImage、SHA-256 清单、可重现的 CycloneDX 1.7 SBOM 与验证报告、已去除身份信息的 Tachyon 证据与性能摘要、更新清单及产物证明。

### 后续发布系列

- 可接受的发布标签只能是不可变的 `vN.N.N` 正式版或 `vN.N.N-rc.N` 候选版，其中 RC 编号必须是正整数；其他标签必须在打包或发布前失败。
- Windows 维持正式且完整的产品范围，并保留已验证的 x64 ZIP、EXE、MSI 及 MSI 语言转换文件。
- macOS 分别提供原生 Apple Silicon（arm64）与 Intel（x86_64）`.dmg`，各自包含架构相符的 `.app`；Linux x86_64 提供 `.AppImage`。这些软件包都必须明确标示为功能受限的 Preview：只验证启动、四语显示、按用户路径与安全失效关闭的平台边界，不代表与 Windows 功能相同。
- Pull Request 只能为软件包测试建立短期 CI 产物，不得建立 GitHub Release；只有现有且符合规则的正式版或候选版标签能进入发布工作流。
- Release 说明必须来自人工整理的四语文件 `docs/releases/<tag>.md`，不能只使用自动生成的说明。

### 历史首发版本

- 标签：`v2.0.14-rc.1`
- 标题：`MoHan Desktop Assistant v2.0.14 RC — First Public Preview`
- 因 Microsoft、GitHub 与 Home Assistant 尚未完成真实环境端到端验证，必须标示为预发布版。
- 必须附上 Windows x64 ZIP 与相符的 SHA-256 文本文件。

### 发布前必要检查

```powershell
python tools\audit_public_release.py
python tests\run_all.py
git diff --check
```

绝对不得发布 `.env`、API 密钥、OAuth 凭据／令牌、Home Assistant 令牌、SQLite 数据库、`.mohan-profile` 文件、录音、本地日志或个人设置。

### 重建 README 媒体

媒体生成器会使用隔离的临时配置文件启动真实 Qt 界面、植入仅供演示的内容、捕获文档记载的页面，并生成 36 秒的 H.264／AAC 演示视频；它绝不读取维护者日常使用的墨寒配置文件。

```powershell
$env:QT_QPA_PLATFORM = "windows"
python tools\capture_readme_media.py --ffmpeg "C:\path\to\ffmpeg.exe"
```

若只要更新当前 UI 截图而不重建演示视频，请使用：

```powershell
python tools\capture_readme_media.py --screenshots-only
```

提交重新生成的媒体前：

1. 以完整尺寸检查每张 PNG，确认没有文字被裁切、字符图形损坏或意外包含个人信息。
2. 确认 `docs/media/mohan-demo.mp4` 时长为 30–60 秒、分辨率为 1280×720，且包含 H.264 视频流及非静音 AAC 音频流。
3. 再次执行公开发布审计及完整测试套件。

### 受保护 main 发布流程

仓库的所有变更都必须使用 Pull Request。不得将实现提交直接推送至 `main`、不得跳过检查、不得强制推送 `main`，也不得在必要检查失败或评审对话尚未解决时合并。必要的 Windows CI 检查是 `Windows CI / test`；安全工作流也必须完成，且不得留有尚未处理的高可信度发现。

本仓库的既定合并策略仅允许 squash。所有必要检查成功、Pull Request 的 head SHA 未变化且评审对话全部解决后，Codex 应直接使用 squash 合并；不得在每次发布时重新查询这项已知策略，也不得先尝试已知不允许的 merge commit 或 rebase。合并后必须读回实际 merge commit，发布标签只能建立在该 commit。只有所有者明确更改设置，或 GitHub 实际拒绝 squash 而显示策略可能漂移时，才重新查询。

GitHub 自动化必须使用一条可预测的凭证路径。Pull Request 的读取与更新优先使用已连接的 GitHub 接口；本地 push 使用 Git 自身的凭证管理；`gh` 仅保留用于已连接接口尚未提供的 GitHub Actions 检查与日志。若 `gh auth status` 一次确认凭证失效，在外部状态未变化前不得反复重试、登出或重新登录；应直接改用已连接接口或已登录浏览器。只有必要操作没有等效途径且确实受阻时，才请所有者重新验证一次。任何流程都不得显示、复制、写入文件或提交 Token。

### 自动化后续发布

只有符合 `vN.N.N` 或 `vN.N.N-rc.N` 的标签能触发 `.github/workflows/release.yml`。工作流会验证精确标签、检出该不可变的源修订，然后依次：

任何平台打包开始前，快速关卡必须先确认标签、版本与 `main` 历史一致，检查本次模式所要求的 Release 存在或不存在，并使用 Python 3.15 验证人工整理的四语 Release 说明。这些低成本且具有决定性的检查不得延后到长时间构建之后；发布前仍须再次验证标签、产物与 Release 状态，以防运行期间发生漂移。

1. 安装已锁定版本的运行时与发布依赖软件包；
2. 编译并审计公开源代码树；
3. 执行完整回归测试套件；
4. 捕获启动、50 Hz 嘴型同步与表情仲裁的已去除身份信息 Python 3.15 Tachyon 证据，随后以采样数、堆栈读取错误、遗漏采样、目标退出状态与 JIT 状态作为关卡；
5. 使用 PyInstaller 构建 Windows x64 应用程序；
6. 执行打包后自测与事件循环 smoke test；
7. 生成便携式 ZIP，以及按用户安装的 EXE 与 MSI；
8. 静默安装、自测并移除两种安装格式；
9. 在架构相符的原生 runner 上分别构建功能受限的 macOS Apple Silicon（arm64）与 Intel（x86_64）Preview，挂载两个 DMG，并对每个打包后的 `.app` 执行契约 smoke test；
10. 在原生 Linux runner 上构建功能受限的 Linux x86_64 Preview，并对打包后的 `.AppImage` 执行契约 smoke test；
11. 使用独立的只读元数据任务生成权威 `SHA256SUMS`、兼容 SHA-256 清单、对应精确 Windows 与 Preview 运行时依赖集合的独立可重现 CycloneDX 1.7 SBOM、机器可读的架构描述／许可证／PURL／依赖关系／隐私验证报告，以及 Windows 兼容的更新清单；
12. 在最小权限发布任务中重新检查精确产物集合及每个已列入清单的 SHA-256 值；
13. 在发布前立即重新解析标签，若标签已移动或被替换便拒绝发布；
14. 为每个发布文件建立 GitHub 产物来源证明；
15. 要求并发布人工整理的四语 Release 说明。

`vN.N.N-rc.N` 必须发布为预发布版，纯 `vN.N.N` 必须发布为正式稳定版；工作流会阻止标签与成熟度不一致。不得重复使用或移动任何已发布标签。

发布元数据工作必须使用已保存的 Python 3.15 执行路径运行所有墨寒项目工具。隔离的 Python 3.14 只能用于尚未支持 3.15 的第三方 SBOM 工具链，不得通过 `PATH` 改变后续项目工具的运行环境。

发布与 PR 软件包工作流会将每个 GitHub Action 锁定至完整 commit。Linux 打包还会把官方 `appimagetool` 产物锁定至源 commit `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`、产物 ID `324406882` 及 SHA-256 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`。

Windows 安装程序构建会锁定 Inno Setup `7.0.2` 与 WiX `7.0.0`。Inno Setup 编译器只能从不可变的官方 `jrsoftware/issrc` Release 下载，使用前必须验证 GitHub Release 证明与 Pyrsys B.V. Authenticode 签名。WiX 会使用已明确授权的 `-acceptEula wix7` CI 参数，并使用持续维护的 `Files` harvester，而非已移除的 Heat 工具。

每份 Pull Request 正文与每份人工整理的 Release 说明都必须依次包含完整且非空白的 `## 繁體中文`、`## 简体中文`、`## English`、`## 日本語` 四个章节。必须翻译该次变更或标签当时真正成立的事实，不得把后来新增的功能倒填到历史 PR 或 Release；自动生成的分类标题也要使用相同四语顺序。只提供象征性的一行翻译，不能取代变更、原因、用户影响与验证信息。

每份四语文档若有 H1，H1 必须按繁中、简中、English、日文顺序并以全角斜线 `／` 分隔；四个语言章节前除该 H1 与空白外，不得出现 prose、徽章、链接或警告。四个语言章节的 H3 以上标题数、段落数、列表项数、链接与图片目标、code fence，以及 inline-code 技术 token 都必须对等；所有文字、段落、列表项、链接、警告与代码示例均须完整翻译且不得歪曲技术术语、版本、路径、命令或安全边界。

### 炎剑开源软件家族质量标准

这是墨寒、FB2Blogger 与 FB2WordPress 共用的长期维护契约；新增炎剑开源软件时，也必须直接沿用，不得另建降低标准的例外流程。

> **炎剑开源核心宣言：**“剑，我已锻成；余下的路，就交给你们了。”

1. 四语一致：重要 README、PR、Release 与使用指引均维持繁中、简中、英文、日文事实一致。
2. 真实验证：只展示实际运行的 CI 与安全扫描，不以徽章代替测试结果。
3. 绝无机密：密钥、令牌、个人资料、数据库与私人内容不得进入版本库或发布产物。
4. 产物可追溯：发布文件对应明确的标签与提交，并提供哈希值或同等验证资料。
5. 不退步：不得为新功能破坏已有正常功能、数据兼容性、安全关卡或确认流程。
6. 不夸大平台：CI 通过不等于真机验证；未实测的平台与功能必须清楚标示限制。
7. 同步对外信息：程序、文档、Release 与官网的版本、链接及可见行为须保持一致。
8. 拒绝一次性手工例外：优先建立可重复、自动化、可测试的流程，不靠临时人工补救维护。

### 验证 Release 产物

Release 产物可使用以下命令验证：

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

### 官网同步

GitHub 发布任务刻意禁止写入 WordPress，也不保存 WordPress Application Password。共用的 Flameblade Product Release Hub 是三个软件产品的单一权威来源；其 `flameblade-series-gateway/products.json` 配置会识别每项产品的公开 GitHub 仓库与官网目标。WordPress 端 gateway 按每小时计划读取公开 GitHub Releases，并更新版本、链接及验证信息，不会把安装程序复制到 Bluehost 存储空间。

此设计让官网凭据留在每个产品仓库之外，也避免出现三套彼此竞争的“Release 至官网”实现。新发布的 Release 最晚可能要到下一次每小时更新才会出现在官网；若超过该时间仍未更新，应诊断共用 gateway，不得在此仓库加入一次性、直接写入 WordPress 的步骤。

### 扩展秘密扫描

仓库会持续启用 GitHub secret scanning 与 push protection，并在 Pull Request、`main` 及每周计划执行完整历史 Gitleaks 检查。GitHub 账户级非供应商 pattern 与合作伙伴 validity 开关，需要由组织拥有、采用 GitHub Team／Enterprise 且具备 GitHub Secret Protection 的仓库；个人公开仓库无法启用这两项付费组织控制。GitHub 免费的供应商扫描仍保持启用。

## English

### Repository description

Safety-first, Windows-first voice-interactive desktop companion with animated expressions, memory, permission-gated tools, and clearly limited macOS/Linux Preview packages for community validation.

### Repository Topics

Use the following GitHub repository Topics:

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
macos
linux
appimage
python
pyside6
openai-api
realtime-api
speech-recognition
text-to-speech
long-term-memory
lip-sync
animated-character
productivity
home-assistant
traditional-chinese
taiwan
open-source
```

### Prepared public pre-release

- Tag: `v3.1.1`
- Title: `MoHan Desktop Assistant v3.1.1`
- Publication condition: publish only after every required CI, package smoke, security, and release-policy check succeeds.
- Includes the Windows x64 portable ZIP, per-user EXE and MSI installers, English/Simplified Chinese/Japanese MSI transforms, macOS Apple Silicon (arm64) and Intel (x86_64) limited Preview DMGs, Linux x86_64 limited Preview AppImage, SHA-256 catalog, reproducible CycloneDX 1.7 SBOMs and validation report, sanitized Tachyon evidence and performance summary, update manifest, and artifact attestations.

### Next release line

- Accepted release tags are immutable stable `vN.N.N` or candidate `vN.N.N-rc.N` tags, with a positive RC number; every other tag must fail before packaging or publication.
- Windows remains the formal, complete product surface and retains its verified x64 ZIP, EXE, MSI, and MSI language transforms.
- macOS receives separate native Apple Silicon (arm64) and Intel (x86_64) `.dmg` files, each containing a matching `.app`; Linux x86_64 receives an `.AppImage`. All must be explicitly labeled as limited Preview packages: they validate launch, four-language rendering, per-user paths, and fail-closed platform boundaries, not feature parity with Windows.
- Pull Requests may build short-lived CI artifacts for package testing only and cannot create a GitHub Release; only an existing valid stable or candidate tag can enter the publication workflow.
- The Release description must come from the curated four-language file `docs/releases/<tag>.md`; generated notes alone are not accepted.

### Historical initial release

- Tag: `v2.0.14-rc.1`
- Title: `MoHan Desktop Assistant v2.0.14 RC — First Public Preview`
- Mark it as a pre-release because Microsoft, GitHub, and Home Assistant have not completed real-environment end-to-end validation.
- Attach the Windows x64 ZIP and matching SHA-256 text file.

### Required pre-publication checks

```powershell
python tools\audit_public_release.py
python tests\run_all.py
git diff --check
```

Never publish `.env`, API keys, OAuth credentials/tokens, Home Assistant tokens, SQLite databases, `.mohan-profile` files, recordings, local logs, or personal settings.

### Rebuild the README media

The media generator launches the real Qt interface with an isolated temporary profile, seeds sample-only content, captures the documented pages, and produces a 36-second H.264/AAC demonstration. It never reads the maintainer's normal MoHan profile.

```powershell
$env:QT_QPA_PLATFORM = "windows"
python tools\capture_readme_media.py --ffmpeg "C:\path\to\ffmpeg.exe"
```

To refresh only the current UI screenshots without rebuilding the demonstration video, use:

```powershell
python tools\capture_readme_media.py --screenshots-only
```

Before committing regenerated media:

1. Inspect every PNG at full size for clipped text, malformed character art, and accidental personal information.
2. Confirm `docs/media/mohan-demo.mp4` is 30–60 seconds, 1280×720, and contains an H.264 video stream and a non-silent AAC audio stream.
3. Run the public-release audit and complete test suite again.

### Protected-main release workflow

All repository changes must use a Pull Request. Do not push implementation commits directly to `main`, bypass checks, force-push `main`, or merge while a required check is failing or a review conversation is unresolved. The required Windows CI check is `Windows CI / test`; security workflows must also complete without an unresolved high-confidence finding.

The repository's established merge policy only permits squash merging. Once every required check passes, the Pull Request head SHA is unchanged, and all review conversations are resolved, Codex must merge directly with squash. Do not re-query this known policy for every release, and do not first attempt a known-disallowed merge commit or rebase. After merging, read back the actual merge commit and create the release tag only on that commit. Re-query the policy only when the owner explicitly changes the setting or GitHub actually rejects squash, indicating possible policy drift.

GitHub automation must use one predictable credential path. Prefer the connected GitHub integration for reading and updating Pull Requests; use Git's own credential manager for local pushes; reserve `gh` for GitHub Actions checks and logs that the connected integration does not expose. If `gh auth status` confirms an invalid credential once, do not retry, log out, or log in again while the external state is unchanged; switch directly to the connected integration or a signed-in browser. Ask the owner to reauthenticate once only when an indispensable operation has no equivalent path and is genuinely blocked. Never display, copy, write to disk, or commit a Token.

### Automated future releases

Only `vN.N.N` or `vN.N.N-rc.N` tags trigger `.github/workflows/release.yml`. The workflow validates the exact tag, checks out that immutable source revision, and then:

Before any platform package starts, the fast gate must confirm that the tag, version, and `main` history agree, require the Release to exist or not exist as dictated by the selected mode, and validate the curated four-language Release notes with Python 3.15. These cheap, decisive checks must not be deferred until after long builds. The tag, artifacts, and Release state are still revalidated immediately before publication to detect in-flight drift.

1. installs pinned runtime and release dependencies;
2. compiles and audits the public source tree;
3. runs the full regression suite;
4. captures sanitized Python 3.15 Tachyon evidence for startup, 50 Hz lip sync, and expression arbitration, then gates sample count, stack-read errors, missed samples, target exit status, and JIT state;
5. builds the Windows x64 application with PyInstaller;
6. runs packaged self-test and event-loop smoke tests;
7. produces a portable ZIP plus per-user EXE and MSI installers;
8. silently installs, self-tests, and removes both installer formats;
9. builds separate limited macOS Apple Silicon (arm64) and Intel (x86_64) Previews on matching native runners, mounts both DMGs, and executes each packaged `.app` contract smoke test;
10. builds the limited Linux x86_64 Preview on a native Linux runner and executes the packaged `.AppImage` contract smoke test;
11. uses a separate read-only metadata job to produce canonical `SHA256SUMS`, a compatibility SHA-256 catalog, separate reproducible CycloneDX 1.7 SBOMs for the exact Windows and Preview runtime dependency sets, a machine-readable schema/license/PURL/dependency/privacy validation report, and the Windows-compatible update manifest;
12. rechecks the exact artifact set and every cataloged SHA-256 value inside a minimal publication job;
13. re-resolves the tag immediately before publication and refuses a moved or replaced tag;
14. creates GitHub artifact provenance attestations for every published file;
15. requires and publishes the curated four-language Release description.

Every `vN.N.N-rc.N` tag must publish as a pre-release, while a plain `vN.N.N` tag must publish as a stable release. The workflow rejects a tag/maturity mismatch. Never reuse or move any published tag.

The release metadata job must run every MoHan-owned tool with the saved Python 3.15 executable. The isolated Python 3.14 runtime is restricted to third-party SBOM tooling that does not yet support 3.15 and must never change later project-tool execution through `PATH`.

The release and PR package workflows pin every GitHub Action to a full commit. Linux packaging additionally pins the official `appimagetool` asset to source commit `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`, asset ID `324406882`, and SHA-256 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`.

Windows installer builds pin Inno Setup `7.0.2` and WiX `7.0.0`. The Inno Setup compiler is downloaded only from the immutable official `jrsoftware/issrc` Release, then checked with GitHub Release attestation and its Pyrsys B.V. Authenticode signature before use. WiX runs with the explicitly authorized `-acceptEula wix7` CI argument and uses its maintained `Files` harvester instead of the removed Heat tool.

Every Pull Request body and every curated Release description must contain complete, non-empty `## 繁體中文`, `## 简体中文`, `## English`, and `## 日本語` sections in that order. Translate the facts that were true for that specific change or tag; never backfill a historical PR or Release with features introduced later. Generated category headings follow the same four-language order. A symbolic one-line translation is not a substitute for the change, reason, user impact, and verification information.

When a four-language document has an H1, that H1 must present Traditional Chinese, Simplified Chinese, English, and Japanese in order, separated by the fullwidth slash `／`; no prose, badge, link, or warning may precede the four language sections except that H1 and blank lines. The four language sections must have equivalent counts of H3-or-deeper headings, paragraphs, list items, link and image destinations, code fences, and inline-code technical tokens. Every statement, paragraph, list item, link, warning, and code example must be translated completely without distorting technical terms, versions, paths, commands, or safety boundaries.

### Flameblade Open Source Software Family Quality Standard

This is the shared long-term maintenance contract for MoHan, FB2Blogger, and FB2WordPress. Every new Flameblade open-source product adopts it directly and must not create a lower-standard exception path.

> **Flameblade open-source declaration:** “I have forged this sword. What comes next is up to you.”

1. Four-language consistency: material README, PR, Release, and user guidance facts stay aligned in Traditional Chinese, Simplified Chinese, English, and Japanese.
2. Honest verification: show only CI and security scans that actually run; badges never substitute for test results.
3. No secrets: keys, tokens, personal data, databases, and private content never enter source control or release artifacts.
4. Traceable artifacts: every published file maps to a specific tag and commit and includes a checksum or equivalent verification.
5. No regressions: new work must not break working behavior, data compatibility, safety gates, or confirmations.
6. No platform overclaiming: passing CI is not real-device validation; untested platforms and features state their limits clearly.
7. Synchronized public information: source, documentation, Releases, and website versions, links, and visible behavior stay aligned.
8. No one-off manual exceptions: prefer repeatable, automated, testable maintenance over temporary manual repairs.

### Verify Release artifacts

Verify Release artifacts with the following commands:

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

### Official website synchronization

The GitHub release job is deliberately not allowed to write to WordPress and stores no WordPress Application Password. The shared Flameblade Product Release Hub is the single authority for all three software products; its `flameblade-series-gateway/products.json` configuration identifies the public GitHub repository and website destination for each product. The WordPress-side gateway reads public GitHub Releases on its hourly schedule and refreshes the version, links, and verification information without copying installers into Bluehost storage.

This design keeps website credentials outside every product repository and avoids three competing release-to-site implementations. A newly published Release may take until the next hourly refresh to appear on the website. If the website does not update after that interval, diagnose the shared gateway rather than adding a one-off direct WordPress write step to this repository.

### Extended secret scanning

The repository keeps GitHub secret scanning and push protection enabled and also runs a full-history Gitleaks check on Pull Requests, `main`, and a weekly schedule. GitHub's account-level non-provider pattern and partner validity toggles require an organization-owned GitHub Team/Enterprise repository with GitHub Secret Protection; a personal public repository cannot enable those two paid organization controls. GitHub's free provider scanning remains active.

## 日本語

### リポジトリの説明

安全性を最優先し、Windows を主要プラットフォームとする音声対話型デスクトップコンパニオンです。アニメーション表情、記憶、権限ゲート付きツールに加え、コミュニティ検証用として制限を明記した macOS／Linux Preview パッケージを備えます。

### リポジトリ Topics

GitHub リポジトリでは次の Topics を使用します。

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
macos
linux
appimage
python
pyside6
openai-api
realtime-api
speech-recognition
text-to-speech
long-term-memory
lip-sync
animated-character
productivity
home-assistant
traditional-chinese
taiwan
open-source
```

### 準備済みの公開プレリリース

- タグ：`v3.1.1`
- タイトル：`MoHan Desktop Assistant v3.1.1`
- 公開条件：必須の CI、パッケージ smoke、セキュリティ、リリースポリシーの全検査が成功した場合に限り公開します。
- Windows x64 ポータブル ZIP、ユーザー単位の EXE および MSI インストーラー、英語／簡体字中国語／日本語の MSI 変換ファイル、macOS Apple Silicon（arm64）および Intel（x86_64）の機能限定 Preview DMG、Linux x86_64 の機能限定 Preview AppImage、SHA-256 カタログ、再現可能な CycloneDX 1.7 SBOM と検証レポート、匿名化済み Tachyon 証拠と性能要約、更新マニフェスト、成果物証明を含みます。

### 次のリリース系列

- 受け付けるリリースタグは、不変の正式版 `vN.N.N` または候補版 `vN.N.N-rc.N` だけで、RC 番号は正の整数でなければなりません。それ以外のタグはパッケージ化または公開前に失敗します。
- Windows は正式かつ完全な製品範囲を維持し、検証済みの x64 ZIP、EXE、MSI、MSI 言語変換ファイルを保持します。
- macOS には Apple Silicon（arm64）用と Intel（x86_64）用のネイティブ `.dmg` を個別に提供し、それぞれ対応する `.app` を収録します。Linux x86_64 には `.AppImage` を提供します。いずれも機能限定 Preview と明記し、起動、四言語表示、ユーザー単位パス、安全に失敗停止するプラットフォーム境界だけを検証するもので、Windows との機能同等性を示すものではありません。
- Pull Request はパッケージ検査用の短期 CI 成果物だけを作成でき、GitHub Release は作成できません。既存かつ有効な正式版または候補版タグだけが公開ワークフローへ進めます。
- Release 説明は、人手で整備した四言語ファイル `docs/releases/<tag>.md` を使用しなければならず、自動生成ノートだけでは認められません。

### 過去の初回リリース

- タグ：`v2.0.14-rc.1`
- タイトル：`MoHan Desktop Assistant v2.0.14 RC — First Public Preview`
- Microsoft、GitHub、Home Assistant が実環境でのエンドツーエンド検証を完了していないため、プレリリースとして表示します。
- Windows x64 ZIP と対応する SHA-256 テキストファイルを添付します。

### 公開前の必須検査

```powershell
python tools\audit_public_release.py
python tests\run_all.py
git diff --check
```

`.env`、API キー、OAuth 認証情報／トークン、Home Assistant トークン、SQLite データベース、`.mohan-profile` ファイル、録音、ローカルログ、個人設定は絶対に公開しません。

### README メディアの再生成

メディア生成ツールは、隔離した一時プロファイルで実際の Qt 画面を起動し、デモ専用内容を投入して文書対象ページを撮影し、36 秒の H.264／AAC デモ動画を生成します。保守担当者が通常使用する墨寒プロファイルは一切読み取りません。

```powershell
$env:QT_QPA_PLATFORM = "windows"
python tools\capture_readme_media.py --ffmpeg "C:\path\to\ffmpeg.exe"
```

デモ動画を再生成せず、現在の UI スクリーンショットだけを更新する場合は、次を使用します。

```powershell
python tools\capture_readme_media.py --screenshots-only
```

再生成したメディアをコミットする前に、次を行います。

1. 各 PNG を原寸で確認し、文字の欠け、文字図形の崩れ、個人情報の意図しない混入がないことを確認します。
2. `docs/media/mohan-demo.mp4` が 30～60 秒、1280×720 で、H.264 映像ストリームと無音ではない AAC 音声ストリームを含むことを確認します。
3. 公開リリース監査と完全なテストスイートを再実行します。

### 保護された main の公開フロー

リポジトリのすべての変更には Pull Request を使用します。実装コミットを `main` へ直接 push すること、検査を迂回すること、`main` を force-push すること、必須検査の失敗中またはレビュー会話の未解決中にマージすることは禁止します。必須の Windows CI 検査は `Windows CI / test` です。セキュリティワークフローも、未解決の高信頼度検出を残さず完了しなければなりません。

このリポジトリの既定のマージポリシーでは squash マージだけを許可します。全必須検査が成功し、Pull Request の head SHA が変わらず、すべてのレビュー会話が解決した後、Codex は squash で直接マージしなければなりません。リリースごとにこの既知のポリシーを再照会したり、許可されないことが既知の merge commit や rebase を先に試したりしてはなりません。マージ後は実際の merge commit を読み戻し、その commit にだけリリースタグを作成します。所有者が設定を明示的に変更した場合、または GitHub が実際に squash を拒否してポリシーの変化が疑われる場合に限り、再照会します。

GitHub 自動化では、予測可能な認証経路を一つだけ使用します。Pull Request の読み取りと更新には接続済み GitHub 連携を優先し、ローカルからの push には Git 自身の認証情報管理を使用し、`gh` は接続済み連携が提供しない GitHub Actions の検査とログにだけ使用します。`gh auth status` で認証情報の無効を一度確認した後は、外部状態が変わらない限り、再試行、ログアウト、再ログインを繰り返してはなりません。接続済み連携またはログイン済みブラウザーへ直ちに切り替えます。不可欠な操作に同等の経路がなく、実際に処理が停止した場合に限り、所有者へ一度だけ再認証を依頼します。どの処理でも Token を表示、複製、ファイル保存、commit してはなりません。

### 今後の自動リリース

`.github/workflows/release.yml` を起動できるのは `vN.N.N` または `vN.N.N-rc.N` タグだけです。ワークフローは正確なタグを検証し、その不変のソースリビジョンを checkout してから、次を順に実行します。

どのプラットフォームのパッケージ化も始める前に、高速ゲートでタグ、バージョン、`main` 履歴の一致を確認し、選択したモードに応じて Release が存在すること、または存在しないことを要求し、Python 3.15 で人手整備の四言語 Release 説明を検証します。低コストで決定的な検査を長時間ビルドの後まで遅らせてはなりません。実行中の変化を検出するため、公開直前にもタグ、成果物、Release 状態を再検証します。

1. バージョン固定済みのランタイム依存関係とリリース依存関係をインストールします。
2. 公開ソースツリーをコンパイルして監査します。
3. 完全な回帰テストスイートを実行します。
4. 起動、50 Hz リップシンク、表情調停について匿名化済み Python 3.15 Tachyon 証拠を取得し、サンプル数、スタック読取エラー、欠落サンプル、対象終了状態、JIT 状態をゲートとして検査します。
5. PyInstaller で Windows x64 アプリケーションをビルドします。
6. パッケージ化後の自己テストとイベントループ smoke test を実行します。
7. ポータブル ZIP と、ユーザー単位の EXE および MSI インストーラーを生成します。
8. 両インストーラー形式をサイレントインストールし、自己テスト後に削除します。
9. 対応するネイティブ runner で macOS Apple Silicon（arm64）用と Intel（x86_64）用の機能限定 Preview を個別にビルドし、両 DMG をマウントして、パッケージ化した各 `.app` の契約 smoke test を実行します。
10. ネイティブ Linux runner で Linux x86_64 の機能限定 Preview をビルドし、パッケージ化した `.AppImage` の契約 smoke test を実行します。
11. 独立した読み取り専用メタデータジョブで、正規 `SHA256SUMS`、互換 SHA-256 カタログ、正確な Windows および Preview ランタイム依存集合ごとの再現可能な CycloneDX 1.7 SBOM、機械可読なスキーマ／ライセンス／PURL／依存関係／プライバシー検証レポート、Windows 互換更新マニフェストを生成します。
12. 最小権限の公開ジョブ内で、正確な成果物集合とカタログ記載の各 SHA-256 値を再検査します。
13. 公開直前にタグを再解決し、移動または置換されたタグを拒否します。
14. 公開する全ファイルに GitHub 成果物由来証明を作成します。
15. 人手で整備した四言語 Release 説明を必須とし、その説明を公開します。

`vN.N.N-rc.N` は Pre-release、純粋な `vN.N.N` は Stable Release として公開し、タグと成熟度が一致しなければワークフローが拒否します。公開済みタグは再利用も移動もしません。

リリースメタデータジョブでは、保存済みの Python 3.15 実行パスを使って墨寒所有の全ツールを実行しなければなりません。隔離した Python 3.14 は、まだ 3.15 をサポートしていない第三者 SBOM ツールチェーンだけに限定し、`PATH` を通じて後続のプロジェクトツール実行環境を変更してはなりません。

リリースおよび PR パッケージワークフローは、すべての GitHub Action を完全な commit に固定します。Linux パッケージ化ではさらに、公式 `appimagetool` 成果物をソース commit `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`、成果物 ID `324406882`、SHA-256 `a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0` に固定します。

Windows インストーラービルドでは Inno Setup `7.0.2` と WiX `7.0.0` を固定します。Inno Setup コンパイラーは不変の公式 `jrsoftware/issrc` Release からだけダウンロードし、使用前に GitHub Release 証明と Pyrsys B.V. Authenticode 署名を検証します。WiX は明示的に許可された `-acceptEula wix7` CI 引数を使用し、削除済みの Heat ではなく、保守中の `Files` harvester を使用します。

すべての Pull Request 本文と人手で整備する Release 説明には、完全で空でない `## 繁體中文`、`## 简体中文`、`## English`、`## 日本語` の各セクションをこの順序で含めます。その変更またはタグの時点で事実だった内容を翻訳し、後に追加された機能を過去の PR や Release へ遡及記載してはなりません。自動生成するカテゴリ見出しも同じ四言語順序にします。象徴的な一行翻訳だけでは、変更内容、理由、利用者への影響、検証情報の代わりになりません。

四言語文書に H1 がある場合、H1 は繁体字中国語、簡体字中国語、English、日本語の順に並べ、全角スラッシュ `／` で区切ります。四つの言語セクションより前には、その H1 と空行以外の prose、バッジ、リンク、警告を置きません。各言語セクションでは、H3 以上の見出し数、段落数、リスト項目数、リンクおよび画像の参照先、code fence、inline-code 技術 token を同等にします。すべての文、段落、リスト項目、リンク、警告、コード例を完全に翻訳し、技術用語、バージョン、パス、コマンド、安全境界を歪めてはなりません。

### 炎剣オープンソース・ソフトウェア・ファミリー品質基準

これは墨寒、FB2Blogger、FB2WordPress に共通する長期保守契約です。新しい炎剣オープンソース製品も直接この契約を採用し、基準を下げる例外経路を設けてはなりません。

> **炎剣オープンソース宣言：**「この剣は、私が鍛え上げました。あとは皆さんに託します。」

1. 四言語の整合：重要な README、PR、Release、利用案内の事実を繁体字中国語・簡体字中国語・英語・日本語で一致させます。
2. 正直な検証：実際に動く CI とセキュリティ検査だけを示し、バッジをテスト結果の代用にしません。
3. 機密情報を含めない：鍵、トークン、個人情報、データベース、私的内容をリポジトリや配布物へ入れません。
4. 追跡可能な成果物：配布ファイルを特定のタグとコミットへ結び付け、ハッシュ値などの検証情報を提供します。
5. 後退させない：新機能のために既存動作、データ互換性、安全ゲート、確認手順を壊しません。
6. 対応 OS を誇張しない：CI 成功を実機検証とは見なさず、未検証の OS と機能の制限を明記します。
7. 公開情報を同期：ソース、文書、Release、公式サイトの版、リンク、見える動作を一致させます。
8. 一度限りの手作業を例外化しない：一時的な手直しより、再利用可能で自動化・テスト可能な保守手順を優先します。

### Release 成果物の検証

Release 成果物は次のコマンドで検証できます。

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

### 公式サイトとの同期

GitHub リリースジョブは意図的に WordPress への書き込みを禁止され、WordPress Application Password も保存しません。共通の Flameblade Product Release Hub が三つのソフトウェア製品すべての単一の正規情報源であり、その `flameblade-series-gateway/products.json` 設定が各製品の公開 GitHub リポジトリと公式サイトの反映先を特定します。WordPress 側 gateway は一時間ごとのスケジュールで公開 GitHub Releases を読み取り、インストーラーを Bluehost ストレージへコピーせずに、バージョン、リンク、検証情報を更新します。

この設計により、公式サイトの認証情報を各製品リポジトリの外に保ち、競合する三つの Release-to-site 実装を避けます。新しい Release が公式サイトに表示されるまで、次の一時間ごとの更新までかかる場合があります。その間隔を過ぎても更新されない場合は、共通 gateway を診断し、このリポジトリへ一度限りの WordPress 直接書き込み手順を追加してはなりません。

### 拡張シークレットスキャン

リポジトリでは GitHub secret scanning と push protection を有効に保ち、Pull Request、`main`、週次スケジュールで全履歴の Gitleaks 検査も実行します。GitHub アカウント単位の非プロバイダー pattern とパートナー validity の切り替えには、組織所有で GitHub Team／Enterprise および GitHub Secret Protection を備えたリポジトリが必要です。個人の公開リポジトリでは、この二つの有料組織向け制御を有効にできません。GitHub の無料プロバイダースキャンは引き続き有効です。
