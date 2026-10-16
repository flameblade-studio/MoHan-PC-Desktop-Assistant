# MPL-2.0 合規條件與所有權邊界／MPL-2.0 合规条件与所有权边界／MPL-2.0 Compliance Conditions and Ownership Boundaries／MPL-2.0 コンプライアンス条件と所有権の境界

## 繁體中文

### 0. 文件狀態與證據索引

- 文件版本：2026-09-07。
- 文件狀態：條件與作業規範，不是目前已驗證合規證明。本文件不加入白名單、不改 runtime，也不把套件級驗證證據擴張成完整正式發行驗收。
- 規範來源：[MPL-2.0 正式授權文本](https://www.mozilla.org/en-US/MPL/2.0/)；[Mozilla MPL-2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)（Q5、Q6、Q8、Q11）。FAQ 是導讀，不取代授權文本、適用法律或律師意見。
- 正式套件級 manifest：third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1；SHA-256 66902730587ea554a0d54421cdb683037543e88ad6e64f179e4ba114e09b2ba2）。它記錄 certifi 2026.7.22（MPL-2.0，Windows runtime 與 local art tooling）、tqdm 4.70.0（MPL-2.0 AND MIT，local art tooling）、orjson 3.12.0（MPL-2.0 AND (Apache-2.0 OR MIT)，local art tooling）。
- scope 紀錄：certifi 2026.7.22 是 Azure Speech → azure-core → requests 的間接 Windows runtime 依賴，也被 local-art-tooling 使用；root 已另行 pin 並補 Windows SBOM。tqdm 與 orjson 只列 local-art-tooling。這是 root 提供的證據索引，不等於完整正式發行驗收。
- 正式 license text：third_party_licenses/mpl/MPL-2.0.txt；source archive 位於 third_party_licenses/mpl/sources/，各檔案 SHA 以 manifest 為準；實際 source／notice 是否足以發行，仍以 root receipt 與正式發行閘門為準。

### 1. 定義、授權與商業使用

- §1.4 的 Covered Software 包含附有 Exhibit A notice 的 Source Code Form、Executable Form 與 Modifications。
- §1.10 的 Modification 包括因新增、刪除或修改 Covered Software 而產生的 source file，以及含有 Covered Software 的新 source file；修改過的 MPL 檔案仍按 MPL 處理。
- §2.1 提供全球、免權利金、非專屬的著作權與專利授權，涵蓋使用、重製、提供、修改、展示、執行與散布；不消滅第三方權利。§2.3 不授予商標權。
- MPL-2.0 可用於公司與商業情境；商業散布仍須完成 §3 的來源、通知與權利保存條件。

### 2. 內部使用與對外散布

- 只在組織內使用或修改：FAQ Q5 說使用本身不產生對外散布義務。仍保存來源、授權、SHA 與 notices，讓狀態可稽核。
- 同一組織內提供修改版或未修改版：FAQ Q6 將組織內 distribution 視為 private distribution；本文件不把它當成已完成對外 source delivery。
- 對組織外提供 MPL source：§3.1 要求 Covered Software 與 Modifications 以 MPL 提供，告知 recipient 授權與來源取得方式，不限制其 MPL source 權利。
- 對組織外提供由未修改 MPL source 編譯的 executable 或 library：§3.2 要告知 MPL source 的位置與方式；executable 可採其他授權，但不得妨礙 source 權利（FAQ Q8）。
- MPL 檔案與自有檔案組成 Larger Work：依 §3.3／FAQ Q11，不含 MPL 程式碼的新檔案可保留自身授權；MPL 檔案、Modifications、source 通知與 notices 仍須符合 MPL。將軟體副本交付組織外 recipient、客戶、下載者或代理商時，進入對外散布檢查；僅提供伺服器端服務、未交付軟體副本，不因 MPL 本身產生網路服務源碼公開義務。

### 3. 套件檔案級 source、notices 與修改紀錄

- 每個可散布套件、archive、installer、wheel、library 或 executable 都要有檔案級 license/source manifest：套件版本、artifact SHA、每個 MPL 檔案路徑、上游版本、原始／現行 SHA、修改狀態與日期。
- manifest 要連結 MPL license text／LICENSE、copyright／patent／disclaimer／limitation notices、source bundle 位置與 recipient 取得說明。executable 散布要在合理、及時且不超過散布成本的條件下提供 preferred form for modification 的 source。
- 受 MPL 管理的 source file 保留 Exhibit A header；格式不適合時在合理位置提供 license／notice 並由 manifest 連回。§3.4 不得移除或改變上游 notices 的實質內容，除非更正事實錯誤。
- 每次修改記錄原始／現行路徑與 SHA、日期、patch/diff、原因、上游版本與 source bundle 位置。非 MPL 且由本專案擁有的檔案維持其真實授權；修改 MPL 檔案不會自動改變不含 MPL 程式碼的自有檔案授權。
- 來源寫作 MIT AND MPL-2.0 時，AND 是同時成立的義務，絕不可暗改成 MIT OR MPL-2.0。只有上游權利人明確授予 OR／雙授權／三授權時才照原文記錄。套件 metadata、掃描器與 wrapper 不得自行改寫。
- §3.5 的 warranty、support、indemnity、liability 必須明確由本專案以自身名義提供，不暗示 contributor 背書，並由本專案承擔相應義務。

### 4. Root 閘門與目前決定

root 在改 allowlist、恢復 runtime 或允許對外發行前，須取得套件／版本／license text／immutable SHA、檔案級對照、headers／LICENSE／THIRD_PARTY_NOTICES、修改紀錄、source bundle 與 recipient 通知，並在 receipt 記錄 reviewer、時間與最終授權。任一項缺少就保持 blocked。

本次文件決定：allowlist_change_by_this_document＝false；full_release_compliance_verified_by_this_document＝false；runtime_resume_by_this_document＝false。manifest 與 root 的套件級驗證可作審查輸入，但這份文件不作完整正式發行已合規的宣稱，也不替第三方權利人授權。

---

## 简体中文

### 0. 文档状态与证据索引

- 文档版本：2026-09-07。
- 文档状态：条件和操作规范，不是当前已验证合规证明。本文件不加入白名单、不改 runtime，也不把软件包级验证证据扩展成完整正式发布验收。
- 规范来源：[MPL-2.0 正式许可证文本](https://www.mozilla.org/en-US/MPL/2.0/)；[Mozilla MPL-2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)（Q5、Q6、Q8、Q11）。FAQ 是导读，不取代许可证文本、适用法律或律师意见。
- 正式软件包级 manifest：third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1；SHA-256 66902730587ea554a0d54421cdb683037543e88ad6e64f179e4ba114e09b2ba2）。它记录 certifi 2026.7.22（MPL-2.0，Windows runtime 与 local art tooling）、tqdm 4.70.0（MPL-2.0 AND MIT，local art tooling）、orjson 3.12.0（MPL-2.0 AND (Apache-2.0 OR MIT)，local art tooling）。
- scope 记录：certifi 2026.7.22 是 Azure Speech → azure-core → requests 的间接 Windows runtime 依赖，也被 local-art-tooling 使用；root 已另行 pin 并补 Windows SBOM。tqdm 与 orjson 只列 local-art-tooling。这是 root 提供的证据索引，不等于完整正式发布验收。
- 正式 license text：third_party_licenses/mpl/MPL-2.0.txt；source archive 位于 third_party_licenses/mpl/sources/，各文件 SHA 以 manifest 为准；实际 source／notice 是否足以发布，仍以 root receipt 与正式发布闸门为准。

### 1. 定义、许可与商业使用

- §1.4 的 Covered Software 包含附有 Exhibit A notice 的 Source Code Form、Executable Form 与 Modifications。
- §1.10 的 Modification 包括因新增、删除或修改 Covered Software 而产生的 source file，以及包含 Covered Software 的新 source file；修改过的 MPL 文件仍按 MPL 处理。
- §2.1 提供全球、免版税、非排他的著作权与专利许可，涵盖使用、复制、提供、修改、展示、执行和分发；不消灭第三方权利。§2.3 不授予商标权。
- MPL-2.0 可用于公司与商业情境；商业分发仍须完成 §3 的来源、通知和权利保存条件。

### 2. 内部使用与对外分发

- 只在组织内使用或修改：FAQ Q5 表示使用本身不会产生对外分发义务。仍保存来源、许可证、SHA 和 notices，使状态可审计。
- 在同一组织内提供修改版或未修改版：FAQ Q6 将组织内 distribution 视为 private distribution；本文件不把它当作已完成对外 source delivery。
- 向组织外提供 MPL source：§3.1 要求 Covered Software 与 Modifications 按 MPL 提供，告知 recipient 许可证和来源取得方式，不限制其 MPL source 权利。
- 向组织外提供由未修改 MPL source 编译的 executable 或 library：§3.2 要告知 MPL source 的位置和方式；executable 可以采用其他许可证，但不得妨碍 source 权利（FAQ Q8）。
- MPL 文件与自有文件组成 Larger Work：按 §3.3／FAQ Q11，不含 MPL 代码的新文件可以保留自身许可证；MPL 文件、Modifications、source 通知和 notices 仍须符合 MPL。将软件副本交付给组织外 recipient、客户、下载者或代理商时，进入对外分发检查；仅提供服务器端服务、未交付软件副本，不因 MPL 本身产生网络服务源代码公开义务。

### 3. 软件包文件级 source、notices 与修改记录

- 每个可分发软件包、archive、installer、wheel、library 或 executable 都要有文件级 license/source manifest：软件包版本、artifact SHA、每个 MPL 文件路径、上游版本、原始／当前 SHA、修改状态和日期。
- manifest 要链接 MPL license text／LICENSE、copyright／patent／disclaimer／limitation notices、source bundle 位置和 recipient 取得说明。executable 分发要在合理、及时且不超过分发成本的条件下提供 preferred form for modification 的 source。
- 受 MPL 管理的 source file 保留 Exhibit A header；格式不适合时在合理位置提供 license／notice 并由 manifest 关联。§3.4 不得删除或改变上游 notices 的实质内容，除非更正事实错误。
- 每次修改记录原始／当前路径和 SHA、日期、patch/diff、原因、上游版本与 source bundle 位置。非 MPL 且由本项目拥有的文件维持真实许可证；修改 MPL 文件不会自动改变不含 MPL 代码的自有文件许可证。
- 来源写作 MIT AND MPL-2.0 时，AND 是同时成立的义务，绝不能暗改成 MIT OR MPL-2.0。只有上游权利人明确授予 OR／双许可证／三许可证时才照原文记录。软件包 metadata、扫描器与 wrapper 不得自行改写。
- §3.5 的 warranty、support、indemnity、liability 必须明确由本项目以自身名义提供，不暗示 contributor 背书，并由本项目承担相应义务。

### 4. Root 闸门与当前决定

root 在改 allowlist、恢复 runtime 或允许对外发布前，须取得软件包／版本／license text／immutable SHA、文件级对照、headers／LICENSE／THIRD_PARTY_NOTICES、修改记录、source bundle 和 recipient 通知，并在 receipt 中记录 reviewer、时间与最终授权。任一项缺少就保持 blocked。

本次文件决定：allowlist_change_by_this_document＝false；full_release_compliance_verified_by_this_document＝false；runtime_resume_by_this_document＝false。manifest 和 root 的软件包级验证可作审查输入，但本文件不声明完整正式发布已合规，也不替第三方权利人授权。

---

## English

### 0. Document status and evidence index

- Document version: 2026-09-07.
- Document status: conditional operational policy, not a present compliance certification. This document does not change the allowlist or runtime and does not expand package-level verification evidence into complete formal release acceptance.
- Normative sources: [MPL-2.0 legal text](https://www.mozilla.org/en-US/MPL/2.0/) and [Mozilla MPL-2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) (Q5, Q6, Q8, Q11). The FAQ is guidance and does not replace the license, applicable law, or legal advice.
- Formal package-level manifest: third_party_licenses/mpl/components.json (schema mohan.mpl-compliance.v1; SHA-256 66902730587ea554a0d54421cdb683037543e88ad6e64f179e4ba114e09b2ba2). It records certifi 2026.7.22 (MPL-2.0, Windows runtime and local-art tooling), tqdm 4.70.0 (MPL-2.0 AND MIT, local-art tooling), and orjson 3.12.0 (MPL-2.0 AND (Apache-2.0 OR MIT), local-art tooling).
- Scope record: certifi 2026.7.22 is an indirect Windows runtime dependency in the Azure Speech → azure-core → requests chain and is also used by local-art tooling; root separately pinned it and added the Windows SBOM. tqdm and orjson are listed only for local-art tooling. This is a root-provided evidence index, not complete formal release acceptance.
- Formal license text: third_party_licenses/mpl/MPL-2.0.txt; source archives are under third_party_licenses/mpl/sources/ and their SHA values are governed by the manifest. Whether source and notices are sufficient for release remains subject to root’s receipt and formal release gate.

### 1. Definitions, rights, and commercial use

- Under §1.4, Covered Software includes Source Code Form with the Exhibit A notice, Executable Form, and Modifications.
- Under §1.10, a Modification includes a source file created by adding, deleting, or modifying Covered Software, and any new source file containing Covered Software. A modified MPL file remains subject to MPL.
- §2.1 grants a worldwide, royalty-free, non-exclusive copyright and patent license for use, reproduction, making available, modification, display, performance, and distribution; it does not erase third-party rights. §2.3 grants no trademark rights.
- MPL-2.0 supports company and commercial use; commercial distribution still must meet the source, notice, and rights-preservation conditions in §3.

### 2. Internal use versus external distribution

- Use or modification only inside the organization: FAQ Q5 says use itself creates no external-distribution obligation. Preserve provenance, license data, SHA values, and notices for auditability.
- Provide changed or unchanged software inside the same organization: FAQ Q6 treats distribution inside an organization as private distribution; this document does not treat it as completed external source delivery.
- Provide MPL source outside the organization: §3.1 requires Covered Software and Modifications to be provided under MPL, with recipient notice and a reasonable way to obtain the license and source; do not restrict MPL source rights.
- Provide an executable or library compiled from someone else’s unchanged MPL source outside the organization: §3.2 requires notice of where and how to obtain the MPL source. Another executable license is allowed only if it does not interfere with source rights (FAQ Q8).
- Combine MPL files with first-party files in a Larger Work: under §3.3／FAQ Q11, new files containing no MPL code may retain their own license; MPL files, Modifications, source notices, and notices must still satisfy MPL. Delivery of software copies to outside recipients, customers, downloaders or resellers enters the distribution review. Server-side service use without delivery of software copies does not itself trigger a network-source disclosure obligation under MPL.

### 3. File-level package source, notices, and modification records

- Every distributable package, archive, installer, wheel, library, or executable must have a file-level license/source manifest with package version, artifact SHA, every MPL file path, upstream version, original／current SHA, modification state, and date.
- The manifest must point to the MPL license text／LICENSE, copyright／patent／disclaimer／limitation notices, source-bundle location, and recipient instructions. An executable distribution must provide the preferred form for modification on reasonable, timely terms at no more than distribution cost.
- Keep the Exhibit A header in MPL-governed source files; if the format cannot carry one, provide the license／notice in a reasonable location and link it from the manifest. §3.4 forbids removing or altering the substance of upstream notices except to correct factual errors.
- Record every change with original／current path and SHA, date, patch/diff, reason, upstream version, and source-bundle location. A non-MPL first-party file keeps its true license; modifying an MPL file does not automatically change a first-party file that contains no MPL code.
- If provenance says MIT AND MPL-2.0, AND is a conjunctive obligation set; never silently rewrite it as MIT OR MPL-2.0. Record OR／dual licensing／tri-licensing only when expressly granted by the upstream rights holder. Package metadata, scanners, and wrappers may not rewrite it.
- Any §3.5 warranty, support, indemnity, or liability term must be clearly offered by this project on its own behalf, without implying contributor endorsement; this project bears the corresponding obligations.

### 4. Root gate and current decision

Before root changes the allowlist, resumes the runtime, or permits external release, obtain package／version／license text／immutable SHA evidence, the file-level mapping, headers／LICENSE／THIRD_PARTY_NOTICES, modification records, a source bundle, and recipient notice instructions. Record reviewer, time, and final authorization in the receipt. Keep the state blocked if any item is missing.

Decision recorded here: allowlist_change_by_this_document = false; full_release_compliance_verified_by_this_document = false; runtime_resume_by_this_document = false. The manifest and root’s package-level verification may be review input, but this document makes no claim of complete formal release compliance and grants no rights for third-party owners.

---

## 日本語

### 0. 文書状態と証拠インデックス

- 文書バージョン：2026-09-07。
- 文書状態：条件付き運用規程であり、現時点の適合証明ではない。本書は allowlist や runtime を変更せず、パッケージ単位の検証証拠を完全な正式リリース受入れへ拡張しない。
- 規範資料：[MPL-2.0 正式ライセンス本文](https://www.mozilla.org/en-US/MPL/2.0/) および [Mozilla MPL-2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)（Q5、Q6、Q8、Q11）。FAQ は補足であり、ライセンス本文、適用法、法律意見を置き換えない。
- 正式なパッケージ単位 manifest：third_party_licenses/mpl/components.json（schema mohan.mpl-compliance.v1、SHA-256 66902730587ea554a0d54421cdb683037543e88ad6e64f179e4ba114e09b2ba2）。certifi 2026.7.22（MPL-2.0、Windows runtime と local-art tooling）、tqdm 4.70.0（MPL-2.0 AND MIT、local-art tooling）、orjson 3.12.0（MPL-2.0 AND (Apache-2.0 OR MIT)、local-art tooling）を記録する。
- scope 記録：certifi 2026.7.22 は Azure Speech → azure-core → requests の間接的な Windows runtime 依存であり、local-art tooling でも使用される。root は別途 pin と Windows SBOM の追加を行った。tqdm と orjson は local-art tooling のみである。これは root が提供した証拠インデックスであり、完全な正式リリース受入れではない。
- 正式 license text：third_party_licenses/mpl/MPL-2.0.txt。source archive は third_party_licenses/mpl/sources/ にあり、各 SHA は manifest に従う。source と notice がリリースに十分かどうかは、root の receipt と正式リリースゲートに従う。

### 1. 定義、権利、商用利用

- §1.4 の Covered Software には、Exhibit A notice 付きの Source Code Form、Executable Form、Modifications が含まれる。
- §1.10 の Modification には、Covered Software を追加、削除、変更して作成した source file と、Covered Software を含む新しい source file が含まれる。変更した MPL ファイルは引き続き MPL の対象である。
- §2.1 は使用、複製、提供、変更、表示、実行、配布などについて、世界的、無償、非独占の著作権および特許ライセンスを与える。第三者の権利を消すものではない。§2.3 は商標権を与えない。
- MPL-2.0 は企業利用と商用利用を許容するが、商用配布でも §3 の source、notice、権利保存の条件を満たす必要がある。

### 2. 内部利用と外部配布

- 組織内だけで利用・変更する場合：FAQ Q5 は利用自体に外部配布義務はないと説明する。監査可能性のため、出所、ライセンス、SHA、notices は保存する。
- 同じ組織内で変更版または未変更版を提供する場合：FAQ Q6 は組織内の distribution を private distribution と扱う。本書では外部向け source delivery の完了とは扱わない。
- 組織外へ MPL source を提供する場合：§3.1 により Covered Software と Modifications を MPL で提供し、recipient にライセンスと source の取得方法を知らせ、MPL source の権利を制限しない。
- 他者の未変更 MPL source からコンパイルした executable または library を組織外へ提供する場合：§3.2 により MPL source の場所と取得方法を知らせる。別の executable license は source の権利を妨げない場合だけ許される（FAQ Q8）。
- MPL ファイルと自社ファイルを Larger Work に組み合わせる場合：§3.3／FAQ Q11 により、MPL コードを含まない新規ファイルは自分のライセンスを維持できる。MPL ファイル、Modifications、source 通知、notices は MPL を満たす必要がある。ソフトウェアのコピーを組織外の recipient、顧客、ダウンロード利用者、代理店へ渡す場合は配布を審査する。コピーを渡さないサーバー側サービスの提供だけでは、MPL によるネットワークサービスのソース公開義務は生じない。

### 3. ファイル単位のパッケージ source、notices、変更記録

- 配布可能な各パッケージ、archive、installer、wheel、library、executable に、パッケージ版、artifact SHA、各 MPL ファイルのパス、上流版、元／現行 SHA、変更状態、日付を記録したファイル単位の license/source manifest を置く。
- manifest は MPL license text／LICENSE、copyright／patent／disclaimer／limitation notices、source bundle の場所、recipient の取得説明へリンクする。executable 配布では preferred form for modification の source を合理的、適時、配布費用を超えない条件で提供する。
- MPL 管理下の source file は Exhibit A header を保持する。形式上置けない場合は合理的な場所に license／notice を置き、manifest から参照する。§3.4 により上流 notice の実質を削除・変更せず、事実誤認だけを訂正する。
- 変更ごとに元／現行パスと SHA、日付、patch/diff、理由、上流版、source bundle 内の場所を記録する。MPL ではない自社所有ファイルは実際のライセンスを維持し、MPL コードを含まない自社ファイルのライセンスを自動変更しない。
- 出所記録が MIT AND MPL-2.0 なら、AND は同時に満たす義務であり、MIT OR MPL-2.0 に暗黙に書き換えない。OR／dual licensing／tri-licensing は上流権利者の明示許諾がある場合だけ記録する。metadata、スキャナ、wrapper は書き換えられない。
- §3.5 の warranty、support、indemnity、liability は本プロジェクト自身の名義であることを明確にし、contributor の承認を暗示せず、対応する義務を本プロジェクトが負う。

### 4. Root ゲートと現在の決定

root が allowlist を変更し、runtime を再開し、または外部リリースを許可する前に、パッケージ／版／license text／immutable SHA、ファイル単位の対照、headers／LICENSE／THIRD_PARTY_NOTICES、変更記録、source bundle、recipient 通知を揃え、receipt に reviewer、時刻、最終認可を記録する。不足が一つでもあれば blocked のままとする。

本書の決定：allowlist_change_by_this_document＝false、full_release_compliance_verified_by_this_document＝false、runtime_resume_by_this_document＝false。manifest と root のパッケージ単位検証はレビュー入力にできるが、本書は完全な正式リリース適合を主張せず、第三者権利者に代わって許諾もしない。

---
