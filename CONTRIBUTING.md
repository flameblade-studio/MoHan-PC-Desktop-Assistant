# Contributing

Thank you for improving the project.

Please read the [roadmap](ROADMAP.md), [governance model](GOVERNANCE.md),
[architecture contract](ARCHITECTURE.md), and [security policy](SECURITY.md)
before starting a substantial change. Large features should begin with a
Feature Request or Discussion so permission boundaries and compatibility can
be agreed before implementation.

1. Create a focused branch.
2. Keep user data, API keys, recordings, and generated databases out of commits.
3. Preserve backward compatibility for existing SQLite databases.
4. Every new behavioral default must have a user override or documented reason.
5. Do not add profession-specific platforms to a fresh installation.
6. Add or update automated tests for behavior changes.
7. Run the core, UI, animation, speech-state, and packaged migration tests.
8. Describe user-visible changes and privacy/security effects in the pull
   request.
9. Resolve every review conversation and wait for all required GitHub checks.
10. Never bypass protected `main`, force-push it, or reuse a published tag.

Translations should preserve placeholders and avoid changing persisted database
values merely to translate display text.

感謝你協助改善墨寒。較大型的功能請先提出 Feature Request 或 Discussion；
所有變更必須經過 Pull Request、必要測試與安全檢查。請勿提交金鑰、權杖、私人
對話、錄音、個人資料庫或未遮蔽截圖。安全問題請依 [SECURITY.md](SECURITY.md)
私下回報。
