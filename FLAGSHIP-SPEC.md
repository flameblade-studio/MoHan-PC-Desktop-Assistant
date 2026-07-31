# MoHan Flagship 2.0 specification

## Execution pipeline

`input → intent → structured plan → local policy → preview/confirmation → tool
execution → result verification → audit/undo information`

The AI produces proposals only. The local application owns authority.

## Supported surfaces

- Windows allowlisted websites, folders, applications, and recoverable file work.
- User-created workflows and schedules.
- Home Assistant local control and health status.
- Google, Microsoft, and GitHub OAuth connector foundations.
- Private-network mobile status and command page.
- App-window screenshots and allowlisted read-only remote files.
- Local camera presence detection.
- Tiered, expiring, exportable local memory.

## Four remote and smart-home boundaries

1. Mobile remote: opt-in, paired-device tokens, status and commands, revocable.
2. Smart home: Home Assistant OS remains independent from the Windows PC.
3. Camera: off by default, visible, local-only, no silent recording.
4. Remote screen/files: app window only and explicit folder allowlists.

## Acceptance gates

- All v1.21.9 source regression tests pass.
- New safety, planner-contract, remote-auth, injection, whitelist, database,
  workflow, Home Assistant, backup, and lifecycle tests pass.
- No regression in Realtime, transcription, TTS, lip sync, animation, physics,
  expression selection, drag behavior, reminders, task timing, or migration.
- Packaged executable passes self-test and repeated clean-profile smoke tests.
- Existing profile migration preserves identity, models, voices, memories,
  conversations, work records, reminders, animation, and personal configuration.
- Remote, camera, cloud, and Home Assistant components remain separately
  disableable; the offline desktop core continues to work.
