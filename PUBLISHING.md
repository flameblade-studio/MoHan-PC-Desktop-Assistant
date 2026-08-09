# GitHub publication settings

## Repository description

Safety-first Windows-first voice-interactive desktop companion with animated
expressions, memory, permission-gated tools, and clearly limited macOS/Linux
Preview packages for community validation.

## Topics

Use these GitHub repository Topics:

```text
desktop-assistant
virtual-assistant
voice-assistant
ai-companion
desktop-companion
windows
macos
linux
appimage
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

## Prepared public pre-release

- Tag: `v2.3.0-rc.1`
- Title: `MoHan Desktop Assistant v2.3.0 RC1`
- Publication: only after every required CI, package smoke, security, and
  release-policy check succeeds
- Includes the Windows x64 portable ZIP, per-user EXE and MSI installers,
  English/Simplified Chinese/Japanese MSI transforms, macOS Apple Silicon
  (arm64) and Intel (x86_64) limited Preview DMGs, Linux x86_64 limited Preview
  AppImage, SHA-256 catalog, reproducible CycloneDX 1.7 SBOMs and validation
  report, sanitized Tachyon evidence and performance summary, update manifest,
  and artifact attestations.

## Next release line

- Accepted release tags: immutable `v2.3.0-rc.N` tags where `N` is a positive
  integer. Other tags fail before packaging or publication.
- Windows remains the formal, complete product surface and keeps its verified
  x64 ZIP, EXE, MSI, and MSI language transforms.
- macOS receives separate native Apple Silicon (arm64) and Intel (x86_64)
  `.dmg` files, each containing a matching `.app`; Linux x86_64 receives an
  `.AppImage`. All are explicitly **limited Preview** packages: they validate
  launch, four-language rendering, per-user paths, and fail-closed platform
  boundaries, not feature parity with Windows.
- Pull requests may build short-lived CI artifacts for package testing only.
  They cannot create a GitHub Release. Only an existing `v2.3.0-rc.N` tag can
  enter the publication workflow.
- The Release description must come from the curated four-language file
  `docs/releases/<tag>.md`; generated notes alone are not accepted.

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

During this migration, only `v2.3.0-rc.N` tags trigger
`.github/workflows/release.yml`. The workflow validates the exact tag, checks
out that immutable source revision, and then:

1. installs pinned runtime and release dependencies;
2. compiles and audits the public source tree;
3. runs the full regression suite;
4. captures sanitized Python 3.15 Tachyon evidence for startup, 50 Hz lip sync,
   and expression arbitration, then gates sample count, stack-read error,
   missed samples, target exit status, and JIT state;
5. builds the Windows x64 application with PyInstaller;
6. runs packaged self-test and event-loop smoke tests;
7. produces a portable ZIP plus per-user EXE and MSI installers;
8. silently installs, self-tests, and removes both installer formats;
9. builds separate limited macOS Apple Silicon (arm64) and Intel (x86_64)
   Previews on matching native runners, mounts both DMGs, and executes each
   packaged `.app` contract smoke test;
10. builds the limited Linux x86_64 Preview on a native Linux runner and
   executes the packaged AppImage contract smoke test;
11. uses a separate read-only metadata job to produce canonical `SHA256SUMS`,
    a compatibility SHA-256 catalog, separate reproducible CycloneDX 1.7 SBOMs
    for the exact Windows and Preview runtime dependency sets, a machine-readable
    schema/license/PURL/dependency/privacy validation report, and the
    Windows-compatible update manifest;
12. rechecks the exact artifact set and every cataloged SHA-256 value inside a
    minimal publication job;
13. re-resolves the tag immediately before publication and refuses a moved or
    replaced tag;
14. creates GitHub artifact provenance attestations for every published file;
15. requires and publishes the curated four-language Release description.

Every tag in this release line is published as a pre-release. Never reuse or
move a published tag; create a new `v2.3.0-rc.N` tag instead. A future stable
release requires a separate, reviewed policy change rather than silently
broadening this gate.

The release and PR package workflows pin every GitHub Action to a full commit.
Linux packaging additionally pins the official AppImage `appimagetool` asset
to source commit `8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81`, asset ID
`324406882`, and SHA-256
`a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0`.
Windows installer builds pin Inno Setup `7.0.2` and WiX `7.0.0`. The Inno
Setup compiler is downloaded only from the immutable official
`jrsoftware/issrc` release, then checked with GitHub release attestation and
its Pyrsys B.V. Authenticode signature before use. WiX runs with the explicitly
authorized `-acceptEula wix7` CI argument and uses its maintained `Files`
harvester instead of the removed Heat tool.

Every pull-request body and every curated Release description must contain
four complete sections in this order: Taiwan Traditional Chinese, Simplified
Chinese, English, and Japanese. Translate the facts that were true for that
specific change or tag; never backfill a historical PR or Release with features
introduced later. The generated category headings follow the same four-language
order. A symbolic one-line translation is not a substitute for the change,
reason, user impact, and verification information.

## 炎劍開源軟體家族品質標準 / 炎剑开源软件家族质量标准 / Flameblade Open Source Software Family Quality Standard / 炎剣オープンソース・ソフトウェア・ファミリー品質基準

這是墨寒、FB2Blogger 與 FB2WordPress 共用的長期維護契約；新增炎劍開源
軟體時，也應直接沿用，不另建降低標準的例外流程。

> **繁體中文：**「劍，我已鍛成；餘下的路，就交給你們了。」
>
> **简体中文：**“剑，我已锻成；余下的路，就交给你们了。”
>
> **English:** “I have forged this sword. What comes next is up to you.”
>
> **日本語：**「この剣は、私が鍛え上げました。あとは皆さんに託します。」

### 繁體中文

1. 四語一致：重要 README、PR、Release 與使用引導皆維持繁中、簡中、英文、日文事實一致。
2. 真實驗證：只展示實際執行的 CI 與安全掃描，不以標籤代替測試結果。
3. 絕無機密：金鑰、權杖、個資、資料庫與私人內容不得進入版本庫或發布產物。
4. 產物可追溯：發布檔對應明確的標籤與提交，並提供雜湊或同等驗證資料。
5. 不退步：不得為新功能破壞既有正常功能、資料相容性、安全閘門或確認流程。
6. 不誇大平台：CI 通過不等於真機驗證；未實測的平台與功能必須清楚標示限制。
7. 同步對外資訊：程式、文件、Release 與官網的版本、連結及可見行為須保持一致。
8. 拒絕單次手工例外：優先建立可重複、自動化、可測試的流程，不靠臨時人工補救維護。

### 简体中文

1. 四语一致：重要 README、PR、Release 与使用指引均维持繁中、简中、英文、日文事实一致。
2. 真实验证：只展示实际运行的 CI 与安全扫描，不以徽章代替测试结果。
3. 绝无机密：密钥、令牌、个人资料、数据库与私人内容不得进入版本库或发布产物。
4. 产物可追溯：发布文件对应明确的标签与提交，并提供哈希值或同等验证资料。
5. 不退步：不得为新功能破坏已有正常功能、数据兼容性、安全关卡或确认流程。
6. 不夸大平台：CI 通过不等于真机验证；未实测的平台与功能必须清楚标示限制。
7. 同步对外信息：程序、文档、Release 与官网的版本、链接及可见行为须保持一致。
8. 拒绝一次性手工例外：优先建立可重复、自动化、可测试的流程，不靠临时人工补救维护。

### English

1. Four-language consistency: material README, PR, Release, and user guidance facts stay aligned in Traditional Chinese, Simplified Chinese, English, and Japanese.
2. Honest verification: show only CI and security scans that actually run; badges never substitute for test results.
3. No secrets: keys, tokens, personal data, databases, and private content never enter source control or release artifacts.
4. Traceable artifacts: every published file maps to a specific tag and commit and includes a checksum or equivalent verification.
5. No regressions: new work must not break working behavior, data compatibility, safety gates, or confirmations.
6. No platform overclaiming: passing CI is not real-device validation; untested platforms and features state their limits clearly.
7. Synchronized public information: source, documentation, Releases, and website versions, links, and visible behavior stay aligned.
8. No one-off manual exceptions: prefer repeatable, automated, testable maintenance over temporary manual repairs.

### 日本語

1. 四言語の整合：重要な README、PR、Release、利用案内の事実を繁体字中国語・簡体字中国語・英語・日本語で一致させます。
2. 正直な検証：実際に動く CI とセキュリティ検査だけを示し、バッジをテスト結果の代用にしません。
3. 機密情報を含めない：鍵、トークン、個人情報、データベース、私的内容をリポジトリや配布物へ入れません。
4. 追跡可能な成果物：配布ファイルを特定のタグとコミットへ結び付け、ハッシュ値などの検証情報を提供します。
5. 後退させない：新機能のために既存動作、データ互換性、安全ゲート、確認手順を壊しません。
6. 対応 OS を誇張しない：CI 成功を実機検証とは見なさず、未検証の OS と機能の制限を明記します。
7. 公開情報を同期：ソース、文書、Release、公式サイトの版、リンク、見える動作を一致させます。
8. 一度限りの手作業を例外化しない：一時的な手直しより、再利用可能で自動化・テスト可能な保守手順を優先します。

Release artifacts can be verified with:

```powershell
Get-FileHash .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip -Algorithm SHA256
gh attestation verify .\MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.zip --repo hitoshic1982/MoHan-PC-Desktop-Assistant
```

## Official website synchronization

The GitHub release job is deliberately not allowed to write to WordPress and
stores no WordPress Application Password. The shared Flameblade Product Release
Hub is the single authority for all three software products: its
`flameblade-series-gateway/products.json` configuration identifies the public
GitHub repository and website destination for each product. The WordPress-side
gateway reads public GitHub Releases on its hourly schedule and refreshes the
version, links, and verification information without copying installers into
Bluehost storage.

This design keeps website credentials outside every product repository and
avoids three competing release-to-site implementations. A newly published
release may take until the next hourly refresh to appear on the website. If the
website does not update after that interval, diagnose the shared gateway rather
than adding a one-off direct WordPress write step to this repository.

## Extended secret scanning

The repository keeps GitHub secret scanning and push protection enabled and
also runs a full-history Gitleaks check on pull requests, `main`, and a weekly
schedule. GitHub's account-level non-provider pattern and partner validity
toggles require an organization-owned GitHub Team/Enterprise repository with
GitHub Secret Protection; a personal public repository cannot enable those two
paid organization controls. GitHub's free provider scanning remains active.
