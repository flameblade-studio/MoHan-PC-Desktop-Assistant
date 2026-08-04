# Changelog

All notable public changes to MoHan Desktop Assistant are documented here.

## Unreleased — v2.1.0-rc.1 candidate

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
