# Project governance / 專案治理

MoHan is currently maintained by **CHOU MING HUA (`@hitoshic1982`)**.
Maintainer decisions prioritize user safety, privacy, backward compatibility,
and the long-term character and product vision documented in this repository.

墨寒目前由 **CHOU MING HUA（`@hitoshic1982`）**維護。專案決策優先考量
使用者安全、隱私、向後相容性，以及本儲存庫記載的長期角色與產品願景。

## How changes are accepted / 變更如何納入

1. Every repository change uses a pull request.
2. Required CI and security checks must pass.
3. Review conversations must be resolved.
4. Changes must not weaken permission, secret-storage, profile-transfer, or
   regression-test boundaries.
5. The maintainer may request narrower scope, additional tests, or migration
   safeguards before merging.

1. 所有儲存庫變更都必須使用 Pull Request。
2. 必要的 CI 與安全檢查必須通過。
3. 審查對話必須處理完畢。
4. 變更不得削弱權限、機密儲存、個人資料轉移或回歸測試邊界。
5. 合併前，維護者可要求縮小範圍、增加測試或補上資料遷移保護。

## Decision model / 決策方式

Discussion and evidence are welcome. The maintainer makes the final merge and
release decision while the project has a single primary maintainer. If a stable
maintainer team forms later, this document will be revised to describe roles,
review authority, and succession.

專案歡迎討論與證據。在目前只有一位主要維護者的階段，由維護者作成最終合併與
發布決定。若未來形成穩定維護團隊，本文件將補充角色、審查權限與接續制度。

## Security and privacy / 安全與隱私

Do not open public issues containing vulnerabilities, credentials, private
conversations, recordings, personal databases, or unredacted screenshots.
Follow [SECURITY.md](SECURITY.md) for private reporting.

請勿在公開 Issue 張貼漏洞、憑證、私人對話、錄音、個人資料庫或未遮蔽截圖。
安全問題請依 [SECURITY.md](SECURITY.md) 私下回報。
