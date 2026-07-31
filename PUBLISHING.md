# GitHub publication settings

## Repository description

Safety-first Windows voice-interactive desktop companion with animated
expressions, long-term memory, productivity workflows, permission-gated tools,
OpenAI Realtime, cloud connectors, and Home Assistant integration.

## Topics

Use these GitHub repository Topics:

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
python
pyside6
openai-api
realtime-api
speech-recognition
text-to-speech
long-term-memory
lip-sync
animated-character
productivity
home-assistant
traditional-chinese
taiwan
open-source
```

## Initial release

- Tag: `v2.0.14-rc.1`
- Title: `MoHan Desktop Assistant v2.0.14 RC — First Public Preview`
- Mark as a pre-release because Microsoft, GitHub, and Home Assistant have not
  completed real-environment end-to-end validation.
- Attach the Windows x64 ZIP and matching SHA-256 text file.

## Required pre-publication checks

```powershell
python tools\audit_public_release.py
python tests\run_all.py
git diff --check
```

Never publish `.env`, API keys, OAuth credentials/tokens, Home Assistant tokens,
SQLite databases, `.mohan-profile` files, recordings, local logs, or personal
settings.

## Rebuild the README media

The media generator launches the real Qt interface with an isolated temporary
profile, seeds sample-only content, captures the documented pages, and produces
a 36-second H.264/AAC demonstration. It never reads the maintainer's normal
MoHan profile.

```powershell
$env:QT_QPA_PLATFORM = "windows"
python tools\capture_readme_media.py --ffmpeg "C:\path\to\ffmpeg.exe"
```

Before committing regenerated media:

1. Inspect every PNG at full size for clipped text, malformed character art,
   and accidental personal information.
2. Confirm `docs/media/mohan-demo.mp4` is 30–60 seconds, 1280×720, contains an
   H.264 video stream and a non-silent AAC audio stream.
3. Run the public-release audit and complete test suite again.

## Protected-main release workflow

All repository changes must use a pull request. Do not push implementation
commits directly to `main`, bypass checks, force-push `main`, or merge while a
required check or review conversation is unresolved. The required Windows CI
check is `Windows CI / test`.
