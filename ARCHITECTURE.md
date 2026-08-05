# MoHan architecture

This file is the maintenance contract for human contributors and Codex.

## Dependency direction

Dependencies point downward only:

1. `app.py` is the Windows character shell. `service_container.py` is the
   explicit runtime composition root.
   `preview_app.py` is a separate, deliberately limited macOS/Linux package
   shell. It may display platform status and localization, but it must not
   import `app.py`, create cloud/voice/tool services, or expose secret inputs.
2. UI modules (`flagship_ui.py`, `profile_transfer_ui.py`) may call public
   service APIs.
3. Services (`profile_transfer.py`, `speech.py`, `realtime_voice.py`,
   `ai_client.py`, `cloud_connectors.py`, `home_assistant.py`,
   `remote_control.py`) may use domain and storage modules.
4. Domain and storage (`db.py`, `flagship_core.py`, `expression_system.py`,
   `lip_sync.py`, `workflow_engine.py`) never import UI or `app.py`.

Circular local imports are prohibited and enforced by
`tests/test_architecture_contracts.py`.

## Feature boundaries

- Dashboard tabs are mounted through `DashboardFeatureRegistry`. Adding a tab
  changes the composition list, not unrelated tabs.
- Cross-window calls use public methods or Qt signals. `CompanionWindow` must
  never call a private `Dashboard._method`.
- Replaceable speech, Realtime, secret-store and listener dependencies are
  described by small `typing.Protocol` ports in `contracts.py` and enter
  `CompanionWindow` through `CompanionServices`.
- Desktop operating-system behavior enters through `PlatformServicePort` and
  the explicit `platform_windows.py`, `platform_macos.py`, and
  `platform_linux.py` adapters. Core modules must not import `winreg`,
  `winsound`, `ctypes.windll`, or `os.startfile` unconditionally.
- Desktop dependency injection is constructor-based. FastAPI `Depends` belongs
  only in a future HTTP boundary; importing FastAPI into the PySide desktop
  core is prohibited.
- OpenAI/Windows speech timing has one source of truth: `lip_sync.py`.
- Replaceable text-to-speech engines register through `speech_providers.py`.
  Providers may synthesize audio but must not own lip sync, expression state,
  UI, permissions, or fallback policy. Windows verified-female local speech is
  the authoritative offline fallback.
- Persisted local-speech selection uses the platform-neutral `system-local`
  provider ID. The literal legacy ID `windows-local` and localized labels are
  migration inputs only; they must never become a second provider.
- Language policy, response-language instructions, and built-in reminder
  migration have one source of truth in `language_support.py`. English and
  Simplified Chinese display strings and stable internal-to-display mappings
  live in `ui_localization.py`; localized labels must never replace persisted
  internal setting values. zh-CN conversation paths must not pass through the
  Taiwan Traditional Chinese output normalizer.
- Pre-reply wait-expression policy has one source of truth in
  `expression_system.plan_wait_expressions`. The visible “思考中” status is
  informational and must never select a character expression by itself.
- Portable profile rules have one source of truth: `profile_transfer.py`.
- Secrets are never stored in SQLite and never enter portable profile files.
- A limited Preview package does not weaken this rule. Until a native secure
  store is implemented and device-validated, the Preview UI exposes no key,
  OAuth, or token fields and does not construct a feature service that could
  persist them.

## Package boundaries

- Windows ZIP, EXE, and MSI remain the only complete product packages.
- Separate macOS Apple Silicon (arm64) and Intel (x86_64) DMGs plus the Linux
  x86_64 AppImage contain `preview_app.py`, not the Windows `app.py` shell.
  Their purpose is native packaging, startup, localization, path, and
  safety-boundary validation.
- Pull requests may upload short-lived package artifacts after a package-level
  smoke test. They never create a GitHub Release.
- Only an existing `v2.2.0-rc.N` tag may publish the multi-platform candidate.
  A read-only metadata job gathers all platform outputs and creates SBOMs,
  metadata, and checksums. A separate minimal privileged job rechecks the
  exact artifacts and tag commit, attests them, and publishes one Release.
- Every Windows and Preview binary distribution carries the MIT license and
  third-party notices in an end-user-readable location.
- The AppImage build tool is accepted only when its official source commit,
  asset identity, and SHA-256 match the reviewed constants. GitHub Actions are
  pinned to complete commit SHAs.

## Data ownership

- `db.py`: conversations, memories, tasks, ideas, work history and settings.
- `secret_store.py`: the injectable `PlatformSecretStoreFactory` boundary.
  Windows receives user-bound DPAPI stores; an unverified platform receives a
  fail-closed store, never a feature-local plaintext fallback.
- `platform_contracts.py`: platform capabilities, per-user paths, and the
  desktop service protocol. On a platform without verified native secure
  storage, secret persistence fails closed instead of writing plaintext.
- `profile_transfer.py`: portable shared progress; machine permissions and
  secrets are excluded. Every bundle has a snapshot ID; importing the same
  snapshot twice is blocked, and older snapshots receive an overwrite warning.
- `backup_manager.py`: verified local pre-change and daily backups.

## How to add a feature

1. Put domain logic in a new, narrowly named module.
2. Define a small public API; do not reach into another class's private state.
3. Put UI in a separate `<feature>_ui.py` module when it is more than a small
   control.
4. Register its tab or panel at the composition point.
5. Add a contract test for the feature alone and one integration smoke test.
6. Run `test_architecture_contracts.py` and the full regression suite.

Do not add a second setting, timer or signal for behavior that already has a
canonical owner. Extend the owner's public API instead.

## Codex-oriented maintenance rules

- Prefer explicit imports, constructors and signal connections over discovery
  magic or reflection.
- Prefer duck-typed `Protocol` boundaries for external engines and tools.
  Concrete domain objects may remain concrete when their full API is the
  intended invariant.
- Keep a new feature's service, UI and tests under matching searchable names.
- Do not add substantial feature logic to `app.py`; it is a composition shell.
- A feature may use another feature only through a documented public method,
  signal or service API.
- If a change requires touching unrelated modules, first add or improve the
  missing public boundary.
- Never weaken an architecture test merely to make a new dependency pass.
