# Security policy / 安全政策

## Supported versions / 支援版本

Security fixes are applied to the current public preview and the latest
development branch. Older preview builds may not receive individual patches.
Before reporting a problem, reproduce it with the newest release or current
`main` branch whenever practical.

安全修正以目前公開預覽版及最新的 `main` 開發分支為主，較舊的預覽版本不保證
逐版修補。若情況允許，請先使用最新 Release 或 `main` 分支確認問題仍可重現。

## Trust boundaries

The model is not an authority. Tool execution is authorized only by the local
policy engine. A model response, webpage, email, file, voice transcript, remote
request, workflow, or Home Assistant device cannot grant itself permission.

Risk levels:

- Green: read, search, status, and allowlisted open actions.
- Blue: reversible local changes and ordinary smart-home controls.
- Yellow: external effects, camera, remote screen, calendar changes, and sending.
- Red: destructive or safety-sensitive operations.

Yellow actions always require confirmation. Red actions require two confirmations
or are blocked. Payment, purchase, password export, disabling security, arbitrary
shell, and administrator shell are permanently non-automatable.

## Credentials

OpenAI, Home Assistant, and OAuth secrets use Windows DPAPI and separate files.
They must not be committed to Git, SQLite, logs, screenshots, exported memory, or
support bundles.

## Remote access

Remote service is disabled by default. Non-loopback binding requires an explicit
acknowledgement that an encrypted private transport such as Tailscale is in use.
Do not port-forward the service to the public internet.

Remote devices receive random one-time pairing tokens, which are stored only as
SHA-256 hashes in SQLite. Tokens can be revoked. Endpoints use per-device
permissions, request-size limits, rate limiting, no-store headers, and protected
file rules.

## Smart home

Locks, alarms, heaters, and climate equipment remain high risk regardless of
model wording. The assistant does not expose arbitrary Home Assistant service
calls. Keep physical controls and life-safety alarms operational independently.

## Reporting a vulnerability / 回報安全漏洞

Do not open a public Issue for an unpatched vulnerability. Use GitHub's
[private vulnerability reporting
channel](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new)
and include:

- affected version and Windows version;
- the smallest reproducible sequence;
- expected and observed security boundaries;
- impact and whether exploitation requires local access;
- redacted logs or screenshots only.

Never include real API keys, OAuth tokens, addresses, faces, private email,
recordings, database files, or Home Assistant URLs. If private reporting is
unavailable, open a public Issue titled `[Security contact request]` without
technical details so that a private channel can be arranged.

請勿把尚未修補的漏洞直接公開為 Issue。請優先使用 GitHub 的
[私人漏洞通報管道](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new)，
並提供受影響版本、Windows 版本、最小重現步驟、預期與實際安全邊界、影響範圍，
以及去識別化後的紀錄或截圖。不得附上真實 API 金鑰、OAuth 權杖、住址、臉部、
私人郵件、錄音、資料庫或 Home Assistant 網址。

The maintainer aims to acknowledge a report within seven days and provide an
initial assessment within fourteen days. These are targets rather than service
guarantees. Please allow time for a coordinated fix before public disclosure.

維護者目標是在七日內確認收到通報、十四日內提供初步研判；此為處理目標而非
服務保證。請在修正與公告協調完成前，暫緩公開漏洞細節。
