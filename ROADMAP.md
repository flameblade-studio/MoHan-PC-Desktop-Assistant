# MoHan roadmap / 墨寒開發路線圖

This roadmap communicates direction, not deadlines. Safety, privacy, data
compatibility, and regression protection take priority over feature count.

本路線圖用來說明方向，不代表交付期限。安全、隱私、資料相容性及避免舊功能
退步，永遠優先於功能數量。

## Stable foundations / 穩定基礎

- Windows 10/11 desktop companion built with Python and PySide6.
- Traditional Chinese text chat, standard transcription, and Realtime voice.
- Expression arbitration, blink, AIUEO visemes, gaze, and motion effects.
- Tasks, ideas, editable long-term memory, timers, and reminders.
- Permission-gated tools, local SQLite data, DPAPI secret storage, and portable
  profile transfer.
- Google Gmail, Calendar, and Drive flows validated in the maintainer's real
  environment.
- Protected-main workflow, Windows CI, security policy, public-release audit,
  and automated regression suite.

## Public-preview integrations / 公開預覽整合

- Microsoft Outlook, OneDrive, and Calendar: implementation exists; real tenant
  end-to-end validation remains pending.
- GitHub assistant tools: implementation exists; real repository end-to-end
  validation remains pending.
- Home Assistant: permission boundaries and connector foundations exist; real
  server and physical-device validation remains pending.

These integrations must remain opt-in and must not be presented as fully
validated until reproducible real-environment evidence is available.

上述整合一律維持自願啟用；在取得可重現的真實環境驗證證據前，不得宣稱已完成
完整驗證。

## Near-term quality goals / 近期品質目標

- Expand real-device and real-account integration test coverage.
- Improve accessibility, onboarding clarity, diagnostics, and recovery paths.
- Continue animation and voice-sync quality work without breaking deterministic
  idle, speech-completion, and expression rules.
- Improve contributor documentation and isolate more feature boundaries where
  evidence shows maintenance friction.
- Add code signing when sustainable funding makes a trusted Windows certificate
  practical.

## Contribution priorities / 歡迎協作方向

- Reproducible bug reports that contain no secrets or private data.
- Accessibility and Traditional Chinese UX improvements.
- Windows packaging, audio-device, and multi-display compatibility.
- Safe connector adapters with explicit permissions, confirmation, and rollback.
- Tests and documentation that reduce maintenance risk.

Please open a Feature Request before implementing a large change. Security
findings must follow [SECURITY.md](SECURITY.md) and must not be posted publicly.

大型功能開始實作前，請先提出 Feature Request。安全問題請遵照
[SECURITY.md](SECURITY.md)，不要公開張貼漏洞、金鑰或私人資料。
