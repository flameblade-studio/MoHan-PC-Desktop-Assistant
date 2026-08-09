# Changelog

All notable public changes to MoHan Desktop Assistant are documented here.

## v2.3.0 RC1 — planned, not yet published

### 繁體中文

- 全面遷移至 CPython 3.15.0rc1，產品執行、測試與所有封裝不再保留舊版
  Python 路徑；全專案採用 PEP 810 明示延遲導入並加入靜態治理稽核。
- 導入 PEP 814 `frozendict` 深層不可變設定、PEP 798 推導式解包、PEP 686
  UTF-8 檔案稽核、PEP 661 哨兵治理及 `bytearray.take_bytes()` 音訊緩衝。
- 加入 PEP 799 Tachyon 取樣分析，可直接檢查啟動、50 Hz 嘴型同步與表情
  仲裁器；JIT 開關均通過完整測試，2.3.0 RC1 預設啟用並保留相容性停用開關。
- CI 與 Release 以有效樣本、讀取錯誤、漏採樣及 JIT 狀態阻擋不合格的
  Tachyon 證據，並發布去識別化結果；CycloneDX 1.7 SBOM 強制完整依賴圖、
  PURL、SPDX 授權、官方結構驗證及 100% 覆蓋率。
- 所有 GitHub Actions JavaScript 動作強制使用 Node 24；PySide6 以受控 ABI3
  輪子驗證跨越 3.15 中繼資料限制，安全掃描與完整發布閘門維持不變。

### 简体中文

- 全面迁移至 CPython 3.15.0rc1，产品、测试和所有发布包不再保留旧版
  Python 路径；全项目采用 PEP 810 显式延迟导入并加入治理审计。
- 导入不可变配置、推导式解包、UTF-8 文件审计、内建哨兵治理及新的音频
  缓冲 API；Tachyon 可分析启动、50 Hz 口型同步和表情仲裁器。
- JIT 开关均通过完整测试；2.3.0 RC1 默认启用，并保留兼容性停用开关。GitHub
  Actions 全部强制 Node 24，并维持 ABI、依赖安全和发布验证闸门。
- CI 与 Release 以有效样本、读取错误、漏采样及 JIT 状态阻止不合格的
  Tachyon 证据，并发布去识别化结果；CycloneDX 1.7 SBOM 强制完整依赖图、
  PURL、SPDX 授权、官方结构验证及 100% 覆盖率。

### English

- Moves the product, tests, and every package exclusively to CPython
  3.15.0rc1, with project-wide explicit PEP 810 lazy imports and governance.
- Adds immutable configuration, unpacking comprehensions, UTF-8 auditing,
  sentinel governance, and the new bytearray audio-buffer API.
- Adds Tachyon profiling for startup, 50 Hz lip sync, and expression
  arbitration. Both JIT modes pass the complete suite; 2.3.0 RC1 defaults JIT on
  while retaining a compatibility disable switch.
- Forces Node 24 for every GitHub JavaScript action and preserves Stable ABI,
  dependency-audit, packaging, and release safety gates.
- Gates sanitized Tachyon evidence on valid samples, stack-read error, missed
  samples, and JIT state. CycloneDX 1.7 SBOMs require complete dependency
  graphs, PURLs, SPDX licenses, official schema validation, and 100% coverage.

### 日本語

- 製品、テスト、全パッケージを CPython 3.15.0rc1 のみに移行し、PEP 810
  の明示的遅延インポートと継続監査を全プロジェクトへ導入しました。
- 不変設定、推論式アンパック、UTF-8 監査、センチネル管理、新しい音声
  バッファー API、Tachyon による 50 Hz 口形・表情解析を導入しました。
- JIT の有無は全テストに合格し、2.3.0 RC1 では既定で有効にしながら互換性用の
  無効化設定を残します。GitHub Actions はすべて Node 24 を強制します。
- Tachyon 証拠は有効サンプル、読取エラー、漏れ、JIT 状態で判定し、匿名化して
  公開します。CycloneDX 1.7 SBOM は完全な依存関係、PURL、SPDX ライセンス、
  公式スキーマ検証、100% 網羅を必須とします。

## v2.2.0 RC2 — 2026-08-07

### 繁體中文

- 托腮待機姿勢在說話期間改用中性嘴角基底：保留眼角笑意，但固定左右嘴角，
  只讓中央嘴唇依 A／I／U／E／O 與開合程度變化，避免誇張咧嘴與殘影。
- Realtime、Windows 本機語音、OpenAI 自然語音與 Azure Speech 統一使用
  20 毫秒／50 Hz 嘴型節拍，縮短張嘴、閉嘴與母音切換延遲。
- 聲音與第一個嘴型從同一播放閘門起跑；聲音結束後拒收遲到母音，只允許
  最終閉嘴訊號通過，避免嘴型先停或聲音結束後再次張嘴。
- 托腮待機眨眼改用完整雙眼遮罩；眼皮閉合時不再殘留睜眼狀態的上眼線，
  一般待機與情境表情共用同一套座標與合成來源。
- 強化標籤發行流程的 Draft Release 復原與清理機制，失敗的發布不會留下
  可被誤認為正式版本的殘缺發行項目。
- 四語 README 新增兩張統一規格的創作歷程圖版，說明炎劍如何逐格檢查
  眼睛、嘴角與語音嘴型，並以測試把二十多年的夢想鍛造成開源作品。

### 简体中文

- 托腮待机姿势在说话期间改用中性嘴角基础：保留眼角笑意，但固定左右嘴角，
  只让中央嘴唇按照 A／I／U／E／O 与开合程度变化，避免夸张咧嘴和残影。
- Realtime、Windows 本地语音、OpenAI 自然语音及 Azure Speech 统一使用
  20 毫秒／50 Hz 口型节拍，缩短张嘴、闭嘴与元音切换延迟。
- 声音与第一个口型从同一播放闸门起跑；声音结束后拒收迟到元音，只允许
  最终闭嘴信号通过，避免口型先停或声音结束后再次张嘴。
- 托腮待机眨眼改用完整双眼遮罩；眼皮闭合时不再残留睁眼状态的上眼线，
  普通待机与情境表情共用同一套坐标及合成来源。
- 强化标签发布流程的 Draft Release 恢复与清理机制，失败的发布不会留下
  容易被误认为正式版本的不完整发布项目。
- 四语 README 新增两张统一规格的创作历程图版，说明炎剑如何逐帧检查
  眼睛、嘴角与语音口型，并以测试将二十多年的梦想锻造成开源作品。

### English

- Gives the chin-rest pose a neutral speech-mouth base: the smiling eyes remain,
  both corners stay fixed, and only the central lips follow A/I/U/E/O and jaw
  aperture, eliminating the exaggerated grin and corner ghosting.
- Moves Realtime, Windows local speech, OpenAI natural speech, and Azure Speech
  onto one 20 ms / 50 Hz viseme clock with shorter open, close, and vowel-change
  transitions.
- Releases audio and the first viseme through the same playback gate, rejects
  late vowels after playback ends, and permits only the final closed-mouth cue.
- Replaces the complete bilateral eye area during chin-rest idle blinks, so
  open-eye eyeliner cannot remain above closed eyelids; idle and contextual
  expressions now share one authoritative mask definition.
- Makes tagged Draft Release publication recoverable and cleans up failed
  attempts so incomplete assets cannot resemble a finished public release.
- Adds two aligned creation-history panels to all four README languages,
  documenting the frame-by-frame care behind MoHan's eyes, mouth corners, and
  lip sync—and the dream Flameblade is turning into open-source software.

### 日本語

- 頬杖姿勢の発話中は中立な口角ベースを使用します。目元の笑みを残しながら
  左右の口角を固定し、中央の唇だけを A／I／U／E／O と開口量に合わせて
  動かすことで、誇張された笑顔と残像を防ぎます。
- Realtime、Windows ローカル音声、OpenAI 自然音声、Azure Speech を
  共通の 20 ミリ秒／50 Hz 口形周期へ統一し、開口、閉口、母音切り替えの
  遅延を短縮します。
- 音声と最初の口形を同じ再生ゲートから開始し、再生終了後の遅延母音を拒否、
  最後の閉口信号だけを通すことで、口だけが先に止まる現象を防ぎます。
- 頬杖の待機中のまばたきでは両目全体を覆う共通マスクを使用し、閉じた
  まぶたの上に開眼時のアイラインが残らないようにしました。待機表情と
  状況表情は同じ座標・合成定義を共有します。
- タグ発行時の Draft Release を安全に復旧・清理できるようにし、失敗した
  発行が不完全な公開版として残らないようにしました。
- 四言語 README に統一規格の制作過程図を2枚追加し、目、口角、口形を
  フレーム単位で確認しながら夢をオープンソース作品へ鍛える姿勢を伝えます。

## v2.2.0 RC1 — 2026-08-06

### 繁體中文

- 保留 Windows x64 為完整正式功能版本，沿用已驗證的 ZIP、EXE、MSI 與
  MSI 語言轉換封裝及安裝／移除測試。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）雙架構
  `.app`／`.dmg` 與 Linux x86_64 `.AppImage` 的功能受限
  Preview。兩者只開放啟動、四語介面、平台資料路徑及安全停用邊界，不宣稱
  與 Windows 功能相同，也不接受金鑰、OAuth 或 Home Assistant 權杖。
- Pull Request 只產生短期測試產物；只有不可變的 `v2.2.0-rc.N` 標籤能建立
  GitHub 預發行版。三平台封裝必須在各自原生 CI 執行打包後啟動測試。
- 發行檔統一提供 SHA256SUMS、CycloneDX SBOM、更新清單與 GitHub 產物
  證明；Release 說明必須由繁中、簡中、英文、日文完整策展文件提供。

### 简体中文

- Windows x64 继续作为完整正式功能版本，并保留已验证的 ZIP、EXE、MSI、
  MSI 语言转换包以及安装／卸载测试。
- 新增原生 macOS Apple Silicon（arm64）／Intel（x86_64）双架构
  `.app`／`.dmg` 与 Linux x86_64 `.AppImage` 功能受限
  Preview。两者只开放启动、四语界面、平台数据路径与安全停用边界，不宣称
  与 Windows 功能相同，也不接收密钥、OAuth 或 Home Assistant 令牌。
- Pull Request 只生成短期测试产物；只有不可变的 `v2.2.0-rc.N` 标签能够
  建立 GitHub 预发布版。三个平台都必须在各自原生 CI 完成打包后启动测试。
- 发布文件统一提供 SHA256SUMS、CycloneDX SBOM、更新清单及 GitHub 产物
  证明；Release 说明必须采用繁中、简中、英文、日文完整编写的文件。

### English

- Windows x64 remains the complete product surface with the verified ZIP,
  EXE, MSI, MSI language transforms, and installer lifecycle tests.
- Added native macOS Apple Silicon (arm64) and Intel (x86_64) `.app`/`.dmg`
  packages plus a Linux x86_64 `.AppImage` limited
  Previews. They expose only launch, four-language UI, platform paths, and
  fail-closed boundaries; they claim no Windows feature parity and accept no
  API keys, OAuth credentials, or Home Assistant tokens.
- Pull requests produce short-lived test artifacts only. Only immutable
  `v2.2.0-rc.N` tags can create a GitHub pre-release, after every platform has
  built and executed its package on a native CI runner.
- Releases provide SHA256SUMS, CycloneDX SBOMs, an update manifest, and GitHub
  artifact attestations, with curated Traditional Chinese, Simplified Chinese,
  English, and Japanese release notes.

### 日本語

- Windows x64 を完全機能版として維持し、検証済みの ZIP、EXE、MSI、MSI
  言語変換、およびインストール／削除テストを継続します。
- macOS Apple Silicon（arm64）／Intel（x86_64）両方のネイティブ
  `.app`／`.dmg` と Linux x86_64 `.AppImage` の機能限定
  Preview を追加します。起動、四言語画面、保存先、安全な無効化だけを提供し、
  Windows 版との同等性を主張せず、API キー、OAuth、Home Assistant Token
  の入力も受け付けません。
- Pull Request は短期テスト用成果物だけを作成します。GitHub のプレリリースを
  作成できるのは変更しない `v2.2.0-rc.N` タグだけで、各 OS のネイティブ CI
  上で配布物を作成し、起動確認に合格する必要があります。
- SHA256SUMS、CycloneDX SBOM、更新マニフェスト、GitHub 成果物証明を提供し、
  Release 説明は繁体字中国語・簡体字中国語・英語・日本語で作成します。

## v2.1.0 RC1 — 2026-08-04

### 繁體中文

- 原始碼、Windows CI 與封裝流程完整遷移至 Python 3.14，並保留未來評估
  Python 3.15 lazy imports 的清楚升級邊界。
- 新增日語最小可用介面與人格，首次啟動及互動式 EXE 安裝程式現支援繁中、
  簡中、英文、日文；MSI 維持繁中基底並提供三種語言轉換策略。
- 文字對話預設改為 `gpt-5.6-luna`，移除新使用者介面中的舊 mini 選項；
  既有設定會安全遷移，其他自訂模型不受影響。
- 新增可插拔語音供應器邊界與 Azure Speech 女性聲線預覽。Windows 本機女聲
  仍是無金鑰、離線或服務失敗時的第一回退。
- 強化長期記憶向量檢索、語義摘要與安全剪枝；新增可關閉的背景工作者，並
  降低即時與非即時語音緩衝延遲。
- 首次啟動精靈與主視窗改為明亮、高對比、較大字級；加入古風科技主視覺、
  墨寒安裝圖、清楚核取方塊及一致的墨寒半身應用程式圖示。
- 語音轉錄提示詞改為依繁中、簡中、英文、日文及使用者設定產生的中性預設，
  不再把炎劍工作室專有詞彙帶給所有使用者；既有自訂提示詞不會被覆蓋。
- 修正首次設定欄位標題的垂直對齊，以及托腮待機姿勢說話時嘴角過度上揚；
  同步更新 README 與官網使用的最新版實機圖。
- 延續姿勢切換、物理圖層與說話銜接的競速修正；RC3 觀察到的抖動需以本版
  候選程式重新實測，不能視為本版回歸。

### 简体中文

- 源代码、Windows CI 与打包流程完整迁移到 Python 3.14，并为未来评估
  Python 3.15 lazy imports 保留清晰的升级边界。
- 新增日语最小可用界面与人格。首次启动及交互式 EXE 安装程序现支持繁中、
  简中、英文、日文；MSI 继续以繁中为基础并提供三种语言转换策略。
- 文字聊天默认改用 `gpt-5.6-luna`，新用户界面移除旧 mini 选项；现有设置
  会安全迁移，其他自定义模型不受影响。
- 新增可插拔语音供应器边界与 Azure Speech 女性声线预览。缺少密钥、离线
  或服务失败时，Windows 本地女声仍是第一回退。
- 改进长期记忆向量检索、语义摘要和安全剪枝；新增可关闭的后台工作线程，
  并降低实时与非实时语音缓冲延迟。
- 首次启动向导与主窗口改为明亮、高对比和较大字号，并加入古风科技主视觉、
  墨寒安装图片、清晰复选框及统一的墨寒半身应用图标。
- 语音转录提示词改为根据繁中、简中、英文、日文及用户设置生成的中性默认值，
  不再把炎剑工作室专用词汇带给所有用户；现有自定义提示词不会被覆盖。
- 修复首次设置字段标题的垂直对齐，以及托腮待机姿势说话时嘴角过度上扬；
  同步更新 README 与官网采用的最新版实机图。

### English

- Migrated source, Windows CI, and packaging to Python 3.14 while preserving
  an explicit boundary for a future Python 3.15 lazy-import evaluation.
- Added a minimum usable Japanese UI and persona. First run and the interactive
  EXE installer now support Traditional Chinese, Simplified Chinese, English,
  and Japanese; the MSI keeps its Traditional Chinese base plus transforms.
- Made `gpt-5.6-luna` the text-chat default and removed the old mini choice
  from the new-user picker without overwriting custom model settings.
- Added a pluggable speech-provider boundary and an opt-in Azure Speech female-
  voice preview. Windows female local speech remains the first offline and
  failure fallback.
- Improved vector memory retrieval, semantic summarization, safe pruning,
  optional background workers, and Realtime/non-Realtime audio buffering.
- Redesigned first run and the main UI with a bright, high-contrast, larger-
  type theme, an ink-and-technology hero, MoHan installer artwork, visible
  checkboxes, and one consistent MoHan half-body application icon.
- Replaced the author-specific transcription default with neutral localized
  prompts generated from each user's language and profile while preserving
  every existing custom prompt.
- Corrected first-run label alignment and the over-wide smile while the
  chin-rest pose speaks, then refreshed the README and website screenshots.

### 日本語

- ソースコード、Windows CI、配布物を Python 3.14 へ移行し、将来の
  Python 3.15 lazy imports 評価に備えた境界を残しました。
- 日本語の最小利用経路と人格を追加しました。初回設定と対話型 EXE
  インストーラーは、繁体字中国語、簡体字中国語、英語、日本語に対応します。
  MSI は繁体字中国語を基準とし、三つの言語変換を提供します。
- 文字会話の既定を `gpt-5.6-luna` に変更し、新規利用者向け一覧から旧 mini
  を削除しました。独自モデル設定は上書きしません。
- 交換可能な音声供給元と Azure Speech 女性音声プレビューを追加しました。
  キー不足、オフライン、障害時は Windows 本機女性音声へ最初に戻ります。
- 長期記憶のベクトル検索、意味要約、安全な整理、任意の背景ワーカー、音声
  バッファーを改善しました。
- 初回設定と本体画面を明るく高コントラストな大きめ文字へ刷新し、古風と
  技術を融合した背景、墨寒のインストール画像、見やすいチェック欄、統一した
  墨寒半身アイコンを追加しました。
- 音声文字起こしの既定文を、繁体字中国語、簡体字中国語、英語、日本語と
  利用者設定から作る中立的な内容へ変更しました。既存の独自文は上書きしません。
- 初回設定の項目名の縦位置と、頬杖姿勢で話す際の過度に広い笑顔を修正し、
  README と公式サイトの実機画像を最新版へ更新しました。

Verification: 56/56 automated test programs passed for the current RC1 source. The
tagged Windows release workflow also passed source auditing, packaged self-test,
silent EXE/MSI install and uninstall verification, checksum and SBOM generation,
artifact attestation, and security checks.

## v2.0.14 RC3 — 2026-08-02

- Added a Traditional Chinese / Simplified Chinese / English first-run wizard
  and minimum usable English and zh-CN UI paths for chat, voice, permissions,
  profile, work modes, and reminders.
- Added complete English and Simplified Chinese MoHan persona prompts plus
  language-matched offline replies, mode announcements, and built-in reminder
  speech. Switching the UI language translates untouched defaults between all
  three languages without overwriting custom reminder text.
- Changed new-user speech output to Windows local voice so the basic experience
  works without an OpenAI API key. Windows voice selection now lists only
  voices verified as female; zh-TW continues to prefer Microsoft Yating while
  zh-CN prefers a matching installed female voice.
- Added a dedicated Simplified Chinese README and quick-start instructions.
- Added secure in-app stable/preview update checks with official-host
  allowlisting, semantic-version validation, size limits, SHA256 verification,
  explicit install confirmation, and preserved local profiles.
- Added automated Windows x64 EXE and MSI installers with silent
  install/self-test/uninstall verification in GitHub Actions.
- Expanded releases with a complete checksum catalog, CycloneDX SBOM, update
  manifest, artifact attestations, and categorized generated release notes.
- Added optional marker-scoped WordPress download-page synchronization using
  GitHub Secrets and a dedicated WordPress Application Password.
- Added full-history Gitleaks checks as a compensating control for GitHub
  Secret Protection features unavailable to personal public repositories.
- Decoupled the visible “墨寒思考中” status from character expressions.
  Routine text and voice questions now keep a natural pose, complex prompts
  react only after a noticeable delay, and unusually slow responses use the
  existing expression arbiter with cancellation, cooldown, and deduplication.
- Unified AI wait cleanup across successful replies, API failures, standard
  voice, and Realtime transitions so thinking cannot linger into speech or
  remain after playback.

Verification: 45/45 automated test programs passed before the RC3 pull
request. The tagged release workflow must additionally pass public-content
audit, packaged self-test, event-loop smoke test, silent EXE/MSI install and
uninstall verification, checksum generation, SBOM generation, and artifact
attestation before publication completes.

## v2.0.14 RC — 2026-07-31

- Fixed OpenAI streaming WAV headers overflowing during application-local
  volume processing, which could make all cloud speech silent.
- Rebuilt adjusted WAV headers from the audio bytes actually received instead
  of copying streaming placeholder lengths.
- Added automatic Windows Yating fallback when OpenAI speech generation or
  playback fails.
- Routed safe read-only Gmail, Google Calendar, and Google Drive commands from
  the normal text conversation box into the permission-gated tool planner.
- Added regression coverage for cloud-speech fallback, streaming WAV volume
  processing, Gmail chat routing, and work-timer isolation.

Verification: 38/38 automated test programs, real OpenAI TTS playback,
packaged self-test, packaged event-loop smoke test, and post-archive self-test
passed before this release candidate.

## v2.0.13 RC — 2026-07-31

- Added a single motion compositor for breathing, speech emphasis, gaze, and
  emotional gestures.
- Fixed occasional character twitching and layer separation during action
  changes.
- Preserved synchronized body, face, eye, hair, sleeve, and ornament layers.
- Smoothed return-to-idle motion after speech.
- Removed synthetic eye highlights that could appear as white artifacts.
- Improved blink, expression, and AIUEO viseme continuity.
- Added configurable character display scaling.
- Added portable profile transfer and modular service boundaries.
- Added explicit public-preview notices for unverified Microsoft, GitHub, and
  Home Assistant integrations.

Verification: 37 automated test programs and a 25,000-step mixed animation,
speech, gaze, and physics stress test passed before this release candidate.
