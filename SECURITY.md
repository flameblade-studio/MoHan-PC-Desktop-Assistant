# Security policy / 安全政策

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

## Reporting

Do not include real API keys, OAuth tokens, addresses, faces, private email, or
Home Assistant URLs in a public report. Describe reproduction steps with redacted
examples and include the affected version.
