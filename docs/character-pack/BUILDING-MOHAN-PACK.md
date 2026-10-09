# 建置墨寒角色包／构建墨寒角色包／Building the MoHan Character Pack／墨寒キャラクターパックのビルド

## 繁體中文

`tools/build_character_pack.py` 依 `docs/character-pack/mohan-inventory.json` 的 `runtime_data` 與 `product_validation_data` 範圍建置完整墨寒角色包。輸出保留每個實體檔案的 repo 相對路徑與原始位元組；兩個 `.mohan-outfit` 內已列出的 1,332 個虛擬成員不會重複封裝。`assets/characters/mohan/pack-source.json` 保存包身分、權利狀態、有限核准範圍、元件入口與驗證上限；它是只供建置器使用的支援描述，在正式清冊中屬 `excluded_support`，不會列入 `manifest.json` 的 `files` 或角色包 payload。

實體 payload 由正式清冊中的執行期檔案與產品自測檔案組成，最新數量與位元組數以 `mohan-inventory.json` 的 `scope_counts` 為準；`pack-source.json` 的支援檔身分不會增加這個數字。最終數字由當下正式清冊實測，不在程式中寫死。建置器逐檔重算大小與 SHA-256，任何清冊漂移都會在建立輸出前失敗。manifest 的四語顯示名、正式名與別名由現有 persona 資料投影；`flameblade.character-rig.v1` 是同時包含 rig 與 `mohan-body-v2` v2 綁定的唯一既有入口，因此只建立一筆 `fullbody_rig` component，正式讀取器從同一份已驗證內容取得全身與半身契約，不偽造平行格式或獨立 body-profile 檔。`appearance/defaults.json` 是正式 payload 與必要 component，由角色來源嚴格驗證；`active_outfit_id` 的既有 sentinel 不屬外觀資料。來源與核准引用保留各自原 scope，不能解讀為整包散布核准。

### 大小政策

本建置採用做法 (a)：只在墨寒建置與驗證呼叫明確傳入 768 MiB 的 ZIP 容器與合計上限；角色包格式的 256 MiB／512 MiB 預設完全不變。做法 (b) 若只拆出兩個外觀包，本體仍約 535 MiB，超過預設合計上限；若再拆成多個包，則必須先決定 DLC 歸屬、相依下載與安裝生命週期。這些事項仍待擁有者決定，因此本步不建立 `dependencies` 或多包語意。

### 建置與驗證

輸出位置必須尚不存在。兩種輸出都會在正式移入目標前，以 `domain.character_pack` validator 和 `pack-source.json` 記錄的明確上限完整驗證：

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.2.zip
```

成功輸出包含 `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明確驗證上限與 `CHARACTER_PACK_VALID=1`。ZIP 使用排序後的成員、1980-01-01 固定時間戳、固定權限、無額外 metadata、`ZIP_STORED` 與停用 ZIP64；同一輸入兩次會得到相同 `package_hash` 與完全相同的 ZIP bytes。資料夾與 ZIP 的邏輯 `package_hash` 相同。

本步不改產品讀取路徑、安裝、更新或執行期組裝。`distribution.access` 是擁有者已裁定的 `public`，`standalone_downloadable` 與再散布皆已允許，四類素材採 CC BY-NC-ND 4.0；DLC 關係仍待擁有者決定。

## 简体中文

`tools/build_character_pack.py` 按 `docs/character-pack/mohan-inventory.json` 的 `runtime_data` 与 `product_validation_data` 范围构建完整墨寒角色包。输出保留每个实体文件的 repo 相对路径与原始字节；两个 `.mohan-outfit` 中已列出的 1,332 个虚拟成员不会重复打包。`assets/characters/mohan/pack-source.json` 保存包身份、权利状态、有限批准范围、组件入口和验证上限；它是仅供构建器使用的支持描述，在正式清册中属于 `excluded_support`，不会列入 `manifest.json` 的 `files` 或角色包 payload。

实体 payload 由正式清册中的运行时文件与产品自测文件组成，最新数量与字节数以 `mohan-inventory.json` 的 `scope_counts` 为准；`pack-source.json` 的支持文件身份不会增加这个数字。最终数字由当时的正式清册实测，不在程序中写死。构建器逐文件重算大小与 SHA-256，任何清册漂移都会在建立输出前失败。manifest 的四语显示名、正式名与别名由现有 persona 数据投影；`flameblade.character-rig.v1` 是同时包含 rig 与 `mohan-body-v2` v2 绑定的唯一现有入口，因此只建立一项 `fullbody_rig` component，正式读取器从同一份已验证内容取得全身与半身契约，不伪造平行格式或独立 body-profile 文件。`appearance/defaults.json` 是正式 payload 与必要 component，由角色来源严格验证；`active_outfit_id` 的现有 sentinel 不属于外观数据。来源与批准引用保留各自原 scope，不能解释为整包分发批准。

### 大小策略

本构建采用做法 (a)：只在墨寒构建与验证调用中明确传入 768 MiB 的 ZIP 容器与合计上限；角色包格式的 256 MiB／512 MiB 默认值完全不变。做法 (b) 若只拆出两个外观包，本体仍约 535 MiB，超过默认合计上限；若再拆成多个包，则必须先决定 DLC 归属、依赖下载与安装生命周期。这些事项仍待所有者决定，因此本步不建立 `dependencies` 或多包语义。

### 构建与验证

输出位置必须尚不存在。两种输出都会在正式移入目标前，使用 `domain.character_pack` validator 和 `pack-source.json` 记录的明确上限完成验证：

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.2.zip
```

成功输出包含 `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明确验证上限与 `CHARACTER_PACK_VALID=1`。ZIP 使用排序后的成员、1980-01-01 固定时间戳、固定权限、无额外 metadata、`ZIP_STORED` 与停用 ZIP64；同一输入两次会得到相同 `package_hash` 与完全相同的 ZIP bytes。文件夹与 ZIP 的逻辑 `package_hash` 相同。

本步不改产品读取路径、安装、更新或运行时装配。`distribution.access` 是所有者已裁定的 `public`，`standalone_downloadable` 与再分发均已允许，四类素材采用 CC BY-NC-ND 4.0；DLC 关系仍待所有者决定。

## English

`tools/build_character_pack.py` builds the complete MoHan character pack from the `runtime_data` and `product_validation_data` scopes in `docs/character-pack/mohan-inventory.json`. Every physical file keeps its repository-relative path and original bytes. The 1,332 virtual members already contained in the two `.mohan-outfit` archives are not packaged twice. `assets/characters/mohan/pack-source.json` records package identity, rights states, narrow approval scopes, typed component entry points, and validation limits. It is a builder-only support declaration classified as `excluded_support` in the formal inventory, so it is absent from the `manifest.json` `files` list and character-pack payload.

Physical payloads are the formal inventory's runtime files plus product self-test files; the current counts and byte totals come from `scope_counts` in `mohan-inventory.json`. The support-file status of `pack-source.json` does not increase that count. The final count is measured from the current formal inventory and is not hardcoded in the program. The builder remeasures every byte count and SHA-256 and fails before creating output if the inventory has drifted. Four-language display names, the canonical name, and aliases are projected from the existing persona data. `flameblade.character-rig.v1` is the sole existing entry point that contains both the rig and its `mohan-body-v2` v2 binding, so the manifest uses one `fullbody_rig` component. The production reader obtains both full-body and half-body contracts from that same validated content without inventing a parallel format or a separate body-profile file. `appearance/defaults.json` is a formal payload and required component validated strictly through the character source; the established `active_outfit_id` sentinel is not appearance data. Source and approval references retain their original narrow scopes and do not authorize distribution of the whole package.

### Size policy

The build uses option (a): only MoHan build and validation calls explicitly pass 768 MiB ZIP-container and aggregate limits. The character-pack format defaults remain unchanged at 256 MiB and 512 MiB. Under option (b), removing only the two appearance archives still leaves an approximately 535 MiB core, above the default aggregate limit. Splitting further would first require decisions about DLC ownership, dependency downloads, and installation lifecycle. Those decisions remain with the owner, so this step does not introduce `dependencies` or multi-package semantics.

### Build and validation

The output path must not already exist. Both forms are fully checked with the `domain.character_pack` validator and the explicit limits recorded in `pack-source.json` before the staged result is moved into place:

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.2.zip
```

Successful output reports `PACKAGE_HASH`, `PAYLOAD_FILES`, `PAYLOAD_BYTES`, the explicit limits, and `CHARACTER_PACK_VALID=1`. ZIP output uses sorted members, the fixed timestamp 1980-01-01, fixed permissions, no extra metadata, `ZIP_STORED`, and disabled ZIP64. Identical inputs produce the same `package_hash` and byte-identical ZIPs. Equivalent directory and ZIP packages share the same logical `package_hash`.

This step does not change product read paths, installation, updates, or runtime composition. The owner-approved `distribution.access` is `public`; `standalone_downloadable` and redistribution are allowed, and all four material categories use CC BY-NC-ND 4.0. The DLC relationship remains an owner decision.

## 日本語

`tools/build_character_pack.py` は `docs/character-pack/mohan-inventory.json` の `runtime_data` と `product_validation_data` の範囲から完全な墨寒キャラクターパックをビルドします。各実ファイルはリポジトリ相対パスと元のバイト列を維持します。二つの `.mohan-outfit` に含まれ、一覧化済みの 1,332 個の仮想メンバーを重複して格納しません。`assets/characters/mohan/pack-source.json` はパックの身元、権利状態、限定された承認範囲、型付きコンポーネント入口、検証上限を記録します。これはビルダー専用の支援記述で、正式一覧では `excluded_support` に分類されるため、`manifest.json` の `files` とキャラクターパック payload には入りません。

実 payload は正式一覧の実行時ファイルと製品セルフテスト用ファイルで構成され、最新の数とバイト数は `mohan-inventory.json` の `scope_counts` に従います。`pack-source.json` は支援ファイルなので、この数を増やしません。最終値はその時点の正式一覧から実測し、プログラムへ固定しません。ビルダーは全ファイルのサイズと SHA-256 を再計測し、一覧が変化していれば出力作成前に失敗します。四言語の表示名、正式名、別名は既存 persona データから投影します。`flameblade.character-rig.v1` は rig と `mohan-body-v2` v2 の結合を同時に含む唯一の既存入口なので、一つの `fullbody_rig` component を使います。正式読取器は同じ検証済み内容から全身と半身の契約を取得し、並行形式や存在しない独立 body-profile ファイルを作りません。`appearance/defaults.json` は正式 payload と必須 component で、キャラクターソースを通じて厳密に検証します。既存の `active_outfit_id` sentinel は外観データではありません。出典と承認の参照は元の限定範囲を維持し、パック全体の配布承認を意味しません。

### サイズ方針

このビルドは方法 (a) を採用します。墨寒のビルドと検証呼び出しだけが、ZIP コンテナと合計サイズに 768 MiB を明示指定します。キャラクターパック形式の既定値 256 MiB／512 MiB は変更しません。方法 (b) で二つの外観パックだけを分離しても、本体は約 535 MiB あり、既定の合計上限を超えます。さらに分割するには、DLC の帰属、依存ダウンロード、インストールのライフサイクルを先に決定する必要があります。これらは所有者の決定待ちなので、本段階では `dependencies` や複数パックの意味を導入しません。

### ビルドと検証

出力先は未作成である必要があります。どちらの形式も、ステージ済み成果物を正式な出力先へ移す前に、`domain.character_pack` validator と `pack-source.json` に記録した明示上限で完全検証します。

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.2.zip
```

成功時は `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明示上限、`CHARACTER_PACK_VALID=1` を出力します。ZIP は並べ替えたメンバー、固定日時 1980-01-01、固定権限、追加 metadata なし、`ZIP_STORED`、ZIP64 無効を使用します。同じ入力から同じ `package_hash` と完全に同じ ZIP bytes を生成します。同等のディレクトリと ZIP は同じ論理 `package_hash` を共有します。

本段階では製品の読込先、インストール、更新、実行時組み立てを変更しません。所有者が決定した `distribution.access` は `public` で、`standalone_downloadable` と再配布を許可し、四種類の素材には CC BY-NC-ND 4.0 を適用します。DLC との関係は所有者の決定待ちです。
