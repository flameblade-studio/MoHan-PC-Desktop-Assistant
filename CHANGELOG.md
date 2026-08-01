# Changelog

All notable public changes to MoHan Desktop Assistant are documented here.

## Unreleased

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
