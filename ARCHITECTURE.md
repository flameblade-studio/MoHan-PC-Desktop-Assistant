# MoHan architecture

This file is the maintenance contract for human contributors and Codex.

## Dependency direction

Dependencies point downward only:

1. `app.py` is the Windows character shell. `service_container.py` is the
   explicit runtime composition root.
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
- Desktop dependency injection is constructor-based. FastAPI `Depends` belongs
  only in a future HTTP boundary; importing FastAPI into the PySide desktop
  core is prohibited.
- OpenAI/Windows speech timing has one source of truth: `lip_sync.py`.
- Portable profile rules have one source of truth: `profile_transfer.py`.
- Secrets are never stored in SQLite and never enter portable profile files.

## Data ownership

- `db.py`: conversations, memories, tasks, ideas, work history and settings.
- `secret_store.py`: Windows-user-bound DPAPI secrets.
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
