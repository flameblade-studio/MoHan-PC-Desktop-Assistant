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
