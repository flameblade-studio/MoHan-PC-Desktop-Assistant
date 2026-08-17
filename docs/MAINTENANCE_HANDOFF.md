# MoHan Maintenance Handoff

This file is the durable, version-controlled continuation point for the
project. Keep it current whenever a release, repair, or platform-validation
task changes state. It contains no credentials, personal conversation history,
or locally stored media.

## Cloud source of truth

- Repository: `hitoshic1982/MoHan-PC-Desktop-Assistant`
- Stable release: `v4.0.0`
- Release baseline on `main`: `e730c08dc985ba0e76a09ccb5cc255c8ecae0d4a`
- Current repair PR: [#63](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/63)
- Current repair branch: `fix/v4-readme-windows-ci`

Use GitHub, rather than a local Codex conversation, as the portable source for
code, documentation, release evidence, and this handoff. Before working on a
different computer, clone the repository and open the current PR or `main`.

## PR #63 scope

The branch contains the post-v4.0.0 repair set:

1. Four-language README wording updated from v3.1.2-era statements to the
   published v4.0.0 state.
2. Windows CI teardown corrected so retained Qt objects cannot turn an already
   passing test into a child-process timeout.
3. The dashboard no longer renders a second companion portrait. The desktop
   companion remains the single visible, draggable conversation character;
   the dashboard shows a live status card for mode, pose/expression, voice,
   camera sensing, and gesture state.
4. Camera presence and activity are surfaced through the proactive companion
   path; recognized waves open the keyboard conversation surface, acknowledge
   the user with expression and speech, and update the status card without
   being allowed to block the interaction itself.
5. Sleep-mode acknowledgement no longer switches to a fallback voice; drag
   support and dropdown popup contrast have been corrected.

## Verification state

The latest CI state must always be checked on PR #63 before merging. Required
checks are:

- Windows CI (including full regression and installer path)
- Preview Package CI: Linux AppImage, macOS arm64 DMG, macOS x86_64 DMG
- Cross-platform core
- CodeQL, dependency review, security audit, secret defense, and four-language
  PR governance

The known Windows CI failures addressed during this repair were:

- missing `QPoint` import in the desktop-drag type annotations;
- gesture status-card presentation being allowed to turn a successful
  `SHOW_DASHBOARD` gesture into a failed gesture boundary.

Do not merge or tag a new release from this branch while any required check is
red. If a check fails, inspect its GitHub Actions job log, make the smallest
direct repair, rerun the relevant local check where available, commit, push,
and re-check the complete required set.

## Manual Windows acceptance after CI is green

On a Windows installation of the merged build, verify these short user-facing
flows:

1. Open the dashboard: only one MoHan character is visible, on the desktop;
   the dashboard contains a status card rather than a portrait duplicate.
2. Type a message in the dashboard: the desktop companion remains usable.
3. Save settings: only the intended acknowledgement is spoken.
4. Enable local camera sensing, appear in frame, move, and wave: presence and
   motion receive a companion response; a wave opens the dashboard, shows
   `Wave recognized` / its localized equivalent, changes expression, and
   produces the normal acknowledgement.
5. Switch to sleep mode: voice identity remains consistent and the desktop
   companion can still be dragged smoothly.
6. Open every dashboard dropdown: option text remains readable with the same
   light visual language as the selected control.

Record any real-device discrepancy in a GitHub issue or a follow-up PR. This
keeps the result portable and reviewable without relying on a single machine's
chat history.

## Continuation procedure

1. Fetch `main` and open the newest open PR.
2. Read this file and the PR description before changing code.
3. Use the CI checks and exact job logs as the release evidence.
4. After all required checks pass, merge the PR to `main`, then verify the
   merged commit and GitHub release/tag alignment.
5. Update this handoff with the final merge SHA, validation results, and any
   remaining real-device follow-up before committing the record.

## `儲存進度` operating command

When the project owner says **「儲存進度」**, treat it as authorization to
perform this complete checkpoint procedure without requiring a separate list
of routine approvals:

1. Inspect the active branch, working tree, latest commit, open PRs, and
   GitHub Actions state.
2. Update this handoff with completed work, current commit/PR references,
   verification results, unresolved items, and the exact continuation step.
3. Run a proportionate non-destructive verification for the changes made in
   the current session.
4. Commit the checkpoint deliberately and push it to the project repository.
5. Return a concise, copy-ready summary for the cloud ChatGPT project. The
   user may paste that summary there because Codex-local conversation history
   is not a bidirectional ChatGPT conversation sync.

Do not include API keys, tokens, passwords, private local paths unrelated to
the project, or raw conversation transcripts in the checkpoint.
