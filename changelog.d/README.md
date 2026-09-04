# CHANGELOG 片段規則／CHANGELOG 片段规则／CHANGELOG Fragment Rules／CHANGELOG フラグメント規則

## 繁體中文

`changelog.d/` 以一個變更一個檔案保存尚未發布的變更，讓不同 Pull Request 不必共同編輯 `CHANGELOG.md`。

### 寫法

- 新片段使用一個 `###` 標題，依序寫繁中／簡中／English／日本語，並以全形斜線 `／` 分隔。
- 每條 `*` 條列也必須依同一順序提供四個非空白語言片段，以 `／` 分隔；四語的條列數、技術 token 與事實必須平行。
- 檔名使用穩定的小寫 kebab-case，例如 `issue-140-migration.md`；不要修改 `CHANGELOG.md` 的未發布內容。
- Release Please 先在 release PR 產生版本標題，接著由 `tools/assemble_changelog.py --version <version>` 依檔名排序組裝；成功寫入後才刪除片段。`--dry-run` 只預覽。

本次遷移的既有三個變更保留原文，使用四個語言小節的相容格式；組裝時只把四語標題與條列重新排成斜線格式，文字逐字保留。組裝器與稽核同時支援這種格式。片段檔不應記錄憑證、個人資料或未驗證的發布承諾。

## 简体中文

`changelog.d/` 以一个变更一个文件保存尚未发布的变更，让不同 Pull Request 不必共同编辑 `CHANGELOG.md`。

### 写法

- 新片段使用一个 `###` 标题，依次写繁中／简中／English／日本語，并以全角斜线 `／` 分隔。
- 每条 `*` 列表项也必须按相同顺序提供四个非空语言片段，以 `／` 分隔；四语的列表项数、技术 token 与事实必须平行。
- 文件名使用稳定的小写 kebab-case，例如 `issue-140-migration.md`；不要修改 `CHANGELOG.md` 的未发布内容。
- Release Please 先在 release PR 产生版本标题，接着由 `tools/assemble_changelog.py --version <version>` 按文件名排序组装；成功写入后才删除片段。`--dry-run` 只预览。

本次迁移的既有三个变更保留原文，组装时只把四语标题与列表项重新排列为斜线格式，文字逐字保留。组装器与审计同时支持这种格式。片段文件不应记录凭据、个人资料或未经验证的发布承诺。

## English

`changelog.d/` stores one not-yet-released change per file, so separate Pull Requests do not have to edit the same part of `CHANGELOG.md`.

### Format

- Use one `###` title for a new fragment, in Traditional Chinese／Simplified Chinese／English／Japanese order, separated by the full-width slash `／`.
- Each `*` bullet must provide four non-empty language parts in the same order, separated by `／`; bullet counts, technical tokens, and facts must remain parallel.
- Use a stable lowercase kebab-case filename such as `issue-140-migration.md`; do not edit the unreleased part of `CHANGELOG.md`.
- Release Please first creates the version heading on its release PR; then `tools/assemble_changelog.py --version <version>` sorts and assembles the fragments. Fragments are deleted only after a successful write. `--dry-run` only previews.

The three changes migrated in this task retain their original wording in a compatibility format with four language sections; assembly only rearranges the four-language titles and bullets into slash rows, preserving every word. The assembler and audit support that format as well. A fragment must not record credentials, personal data, or an unverified release promise.

## 日本語

`changelog.d/` には未公開の変更を一つの変更につき一ファイルで保存し、別々の Pull Request が同じ `CHANGELOG.md` の箇所を編集しないようにします。

### 書式

- 新しいフラグメントには `###` 見出しを一つ置き、繁体字中国語／簡体字中国語／English／日本語の順に、全角スラッシュ `／` で区切って書きます。
- 各 `*` 箇条書きにも同じ順序で空でない四つの言語部分を置き、`／` で区切ります。箇条書き数、技術 token、事実を四言語で揃えます。
- `issue-140-migration.md` のような安定した小文字 kebab-case のファイル名を使い、`CHANGELOG.md` の未公開部分を直接編集しません。
- Release Please が先に release PR 上でバージョン見出しを作成し、その後 `tools/assemble_changelog.py --version <version>` がファイル名順に組み立てます。正常に書き込んだ後だけフラグメントを削除します。`--dry-run` はプレビューだけです。

今回移行した三つの変更は、元の文言を四言語の小見出しによる互換形式で保持します。組み立て時は四言語の見出しと箇条書きをスラッシュ行へ並べ替えるだけで、各語を保持します。組み立てツールと監査はこの形式にも対応します。フラグメントへ認証情報、個人データ、未検証の公開約束を記録してはいけません。
