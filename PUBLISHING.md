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

## Current public pre-release

- Tag: `v2.1.0-rc.1`
- Title: `MoHan Desktop Assistant v2.1.0 RC1`
- Published: 2026-08-04
- Includes the Windows x64 portable ZIP, per-user EXE and MSI installers,
  English/Simplified Chinese/Japanese MSI transforms, SHA-256 catalog,
  CycloneDX SBOM, update manifest, and artifact attestations.

## Historical initial release

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

To refresh only the current UI screenshots without rebuilding the demonstration
video, use:

```powershell
python tools\capture_readme_media.py --screenshots-only
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
check is `Windows CI / test`. Security workflows must also complete without an
unresolved high-confidence finding.

## Automated future releases

Future `v`-prefixed semantic-version tags trigger `.github/workflows/release.yml`.
The workflow checks out the exact tag and then:

1. installs pinned runtime and release dependencies;
2. compiles and audits the public source tree;
3. runs the full regression suite;
4. builds the Windows x64 application with PyInstaller;
5. runs packaged self-test and event-loop smoke tests;
6. produces a portable ZIP plus per-user EXE and MSI installers;
7. silently installs, self-tests, and removes both installer formats;
8. produces a complete SHA-256 catalog, CycloneDX SBOM, and signed update
   manifest;
9. creates GitHub artifact provenance attestations;
10. generates categorized Release Notes and publishes every asset; and
11. synchronizes the marker-managed official WordPress download block when
    the required repository secrets are configured.

Tags containing a prerelease suffix such as `-rc.1` are published as
pre-releases. Stable semantic tags are published as normal releases. Never
reuse or move a published tag; create a new version instead.

Every pull-request body and every curated Release description must contain
four complete sections in this order: Taiwan Traditional Chinese, Simplified
Chinese, English, and Japanese. Translate the facts that were true for that
specific change or tag; never backfill a historical PR or Release with features
introduced later. The generated category headings follow the same four-language
order. A symbolic one-line translation is not a substitute for the change,
reason, user impact, and verification information.

Release artifacts can be verified with:

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

## Official website synchronization

Create a dedicated, least-privilege WordPress user and an Application Password.
Store the values only as GitHub Actions repository secrets:

- `WORDPRESS_BASE_URL`: `https://www.flamebladestudio.com.tw`
- `WORDPRESS_USERNAME`: the dedicated release-sync username
- `WORDPRESS_APP_PASSWORD`: the WordPress Application Password
- `WORDPRESS_DOWNLOAD_PAGE_ID`: optional existing page ID; when omitted, the
  workflow finds or creates the `mohan-desktop-assistant` page

The workflow never stores these values in source, logs, release files, the
update manifest, or the application. It replaces only content enclosed by
`MOHAN_RELEASE_START` and `MOHAN_RELEASE_END` markers.

The WordPress page is a bilingual product and contributor landing page. Its
images and every installer link point to the public GitHub repository or GitHub
Releases; the workflow never uploads EXE, MSI, ZIP, video, or release artifacts
to WordPress, so release growth does not consume Bluehost media storage. Add the
published page to the site's primary navigation once; later releases update the
managed page content automatically without changing the menu entry.

## Extended secret scanning

The repository keeps GitHub secret scanning and push protection enabled and
also runs a full-history Gitleaks check on pull requests, `main`, and a weekly
schedule. GitHub's account-level non-provider pattern and partner validity
toggles require an organization-owned GitHub Team/Enterprise repository with
GitHub Secret Protection; a personal public repository cannot enable those two
paid organization controls. GitHub's free provider scanning remains active.
