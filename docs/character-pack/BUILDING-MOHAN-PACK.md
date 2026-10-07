# 建置墨寒角色包／构建墨寒角色包／Building the MoHan Character Pack／墨寒キャラクターパックのビルド

## 繁體中文

`tools/build_character_pack.py` 依 `docs/character-pack/mohan-inventory.json` 的 `runtime_data` 與 `product_validation_data` 範圍建置完整墨寒角色包。輸出保留每個實體檔案的 repo 相對路徑與原始位元組；兩個 `.mohan-outfit` 內已列出的 1,332 個虛擬成員不會重複封裝。`assets/characters/mohan/pack-source.json` 保存包身分、權利狀態、有限核准範圍、元件入口與驗證上限；它是建置描述，也是由清冊擁有者登記為 `runtime_data` 後依同一規則原樣保留的角色資料。

新增建置描述前的正式清冊基線含 1,702 個實體 payload：1,654 個執行期檔案與 48 個產品自測檔案，合計 619,890,794 bytes。最終數字由當下正式清冊實測，納入 `pack-source.json` 後會自動增加一檔，不在程式中寫死。建置器逐檔重算大小與 SHA-256，任何清冊漂移都會在建立輸出前失敗。manifest 的四語顯示名、正式名與別名由現有 persona 資料投影；`flameblade.character-rig.v1` 是同時包含 rig 與 `mohan-body-v2` v2 綁定的唯一既有入口，因此只建立一筆 rig component，不偽造獨立 body-profile 檔。來源與核准引用保留各自原 scope，不能解讀為整包散布核准。

### 大小政策

本建置採用做法 (a)：只在墨寒建置與驗證呼叫明確傳入 768 MiB 的 ZIP 容器與合計上限；角色包格式的 256 MiB／512 MiB 預設完全不變。做法 (b) 若只拆出兩個外觀包，本體仍約 535 MiB，超過預設合計上限；若再拆成多個包，則必須先決定 DLC 歸屬、相依下載與安裝生命週期。這些事項仍待擁有者決定，因此本步不建立 `dependencies` 或多包語意。

### 建置與驗證

輸出位置必須尚不存在。兩種輸出都會在正式移入目標前，以 `domain.character_pack` validator 和 `pack-source.json` 記錄的明確上限完整驗證：

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.0.zip
```

成功輸出包含 `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明確驗證上限與 `CHARACTER_PACK_VALID=1`。ZIP 使用排序後的成員、1980-01-01 固定時間戳、固定權限、無額外 metadata、`ZIP_STORED` 與停用 ZIP64；同一輸入兩次會得到相同 `package_hash` 與完全相同的 ZIP bytes。資料夾與 ZIP 的邏輯 `package_hash` 相同。

本步不改產品讀取路徑、安裝、更新或執行期組裝。`distribution.access` 是擁有者已裁定的 `private`；`standalone_downloadable` 是 true；再散布與四類素材授權維持 `owner_decision_pending`。

## 简体中文

`tools/build_character_pack.py` 按 `docs/character-pack/mohan-inventory.json` 的 `runtime_data` 与 `product_validation_data` 范围构建完整墨寒角色包。输出保留每个实体文件的 repo 相对路径与原始字节；两个 `.mohan-outfit` 中已列出的 1,332 个虚拟成员不会重复打包。`assets/characters/mohan/pack-source.json` 保存包身份、权利状态、有限批准范围、组件入口和验证上限；它是构建描述，也是由清册所有者登记为 `runtime_data` 后按同一规则原样保留的角色数据。

新增构建描述前的正式清册基线包含 1,702 个实体 payload：1,654 个运行时文件与 48 个产品自测文件，合计 619,890,794 bytes。最终数字从当时的正式清册实测，纳入 `pack-source.json` 后会自动增加一个文件，不在程序中写死。构建器逐文件重算大小与 SHA-256，任何清册漂移都会在建立输出前失败。manifest 的四语显示名、正式名与别名由现有 persona 数据投影；`flameblade.character-rig.v1` 是同时包含 rig 与 `mohan-body-v2` v2 绑定的唯一现有入口，因此只建立一项 rig component，不伪造独立 body-profile 文件。来源与批准引用保留各自原 scope，不能解释为整包分发批准。

### 大小策略

本构建采用做法 (a)：只在墨寒构建与验证调用中明确传入 768 MiB 的 ZIP 容器与合计上限；角色包格式的 256 MiB／512 MiB 默认值完全不变。做法 (b) 若只拆出两个外观包，本体仍约 535 MiB，超过默认合计上限；若再拆成多个包，则必须先决定 DLC 归属、依赖下载与安装生命周期。这些事项仍待所有者决定，因此本步不建立 `dependencies` 或多包语义。

### 构建与验证

输出位置必须尚不存在。两种输出都会在正式移入目标前，使用 `domain.character_pack` validator 和 `pack-source.json` 记录的明确上限完成验证：

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.0.zip
```

成功输出包含 `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明确验证上限与 `CHARACTER_PACK_VALID=1`。ZIP 使用排序后的成员、1980-01-01 固定时间戳、固定权限、无额外 metadata、`ZIP_STORED` 与停用 ZIP64；同一输入两次会得到相同 `package_hash` 与完全相同的 ZIP bytes。文件夹与 ZIP 的逻辑 `package_hash` 相同。

本步不改产品读取路径、安装、更新或运行时装配。`distribution.access` 是所有者已裁定的 `private`；`standalone_downloadable` 是 true；再分发与四类素材授权保持 `owner_decision_pending`。

## English

`tools/build_character_pack.py` builds the complete MoHan character pack from the `runtime_data` and `product_validation_data` scopes in `docs/character-pack/mohan-inventory.json`. Every physical file keeps its repository-relative path and original bytes. The 1,332 virtual members already contained in the two `.mohan-outfit` archives are not packaged twice. `assets/characters/mohan/pack-source.json` records package identity, rights states, narrow approval scopes, typed component entry points, and validation limits. It is a build declaration and character data retained byte-for-byte by the same rule after the inventory owner registers it as `runtime_data`.

The formal-inventory baseline before adding the build declaration contains 1,702 physical payloads: 1,654 runtime files and 48 product self-test files, totaling 619,890,794 bytes. The final count is measured from the current formal inventory and automatically increases by one after `pack-source.json` is registered; it is not hardcoded in the program. The builder remeasures every byte count and SHA-256 and fails before creating output if the inventory has drifted. Four-language display names, the canonical name, and aliases are projected from the existing persona data. `flameblade.character-rig.v1` is the sole existing entry point that contains both the rig and its `mohan-body-v2` v2 binding, so the manifest uses one rig component and does not invent a separate body-profile file. Source and approval references retain their original narrow scopes and do not authorize distribution of the whole package.

### Size policy

The build uses option (a): only MoHan build and validation calls explicitly pass 768 MiB ZIP-container and aggregate limits. The character-pack format defaults remain unchanged at 256 MiB and 512 MiB. Under option (b), removing only the two appearance archives still leaves an approximately 535 MiB core, above the default aggregate limit. Splitting further would first require decisions about DLC ownership, dependency downloads, and installation lifecycle. Those decisions remain with the owner, so this step does not introduce `dependencies` or multi-package semantics.

### Build and validation

The output path must not already exist. Both forms are fully checked with the `domain.character_pack` validator and the explicit limits recorded in `pack-source.json` before the staged result is moved into place:

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.0.zip
```

Successful output reports `PACKAGE_HASH`, `PAYLOAD_FILES`, `PAYLOAD_BYTES`, the explicit limits, and `CHARACTER_PACK_VALID=1`. ZIP output uses sorted members, the fixed timestamp 1980-01-01, fixed permissions, no extra metadata, `ZIP_STORED`, and disabled ZIP64. Identical inputs produce the same `package_hash` and byte-identical ZIPs. Equivalent directory and ZIP packages share the same logical `package_hash`.

This step does not change product read paths, installation, updates, or runtime composition. `distribution.access` is the owner-approved `private`, `standalone_downloadable` is true, and redistribution plus all four material-license categories remain `owner_decision_pending`.

## 日本語

`tools/build_character_pack.py` は `docs/character-pack/mohan-inventory.json` の `runtime_data` と `product_validation_data` の範囲から完全な墨寒キャラクターパックをビルドします。各実ファイルはリポジトリ相対パスと元のバイト列を維持します。二つの `.mohan-outfit` に含まれ、一覧化済みの 1,332 個の仮想メンバーを重複して格納しません。`assets/characters/mohan/pack-source.json` はパックの身元、権利状態、限定された承認範囲、型付きコンポーネント入口、検証上限を記録します。これはビルド宣言であり、一覧の所有者が `runtime_data` として登録した後は同じ規則でバイト単位に保持するキャラクターデータでもあります。

ビルド宣言追加前の正式一覧の基準値は実 payload 1,702 個です。内訳は実行時ファイル 1,654 個と製品セルフテスト用ファイル 48 個で、合計 619,890,794 bytes です。最終値はその時点の正式一覧から実測し、`pack-source.json` の登録後は自動的に一ファイル増えるため、プログラムへ固定しません。ビルダーは全ファイルのサイズと SHA-256 を再計測し、一覧が変化していれば出力作成前に失敗します。四言語の表示名、正式名、別名は既存 persona データから投影します。`flameblade.character-rig.v1` は rig と `mohan-body-v2` v2 の結合を同時に含む唯一の既存入口なので、一つの rig component を使い、存在しない独立 body-profile ファイルを作りません。出典と承認の参照は元の限定範囲を維持し、パック全体の配布承認を意味しません。

### サイズ方針

このビルドは方法 (a) を採用します。墨寒のビルドと検証呼び出しだけが、ZIP コンテナと合計サイズに 768 MiB を明示指定します。キャラクターパック形式の既定値 256 MiB／512 MiB は変更しません。方法 (b) で二つの外観パックだけを分離しても、本体は約 535 MiB あり、既定の合計上限を超えます。さらに分割するには、DLC の帰属、依存ダウンロード、インストールのライフサイクルを先に決定する必要があります。これらは所有者の決定待ちなので、本段階では `dependencies` や複数パックの意味を導入しません。

### ビルドと検証

出力先は未作成である必要があります。どちらの形式も、ステージ済み成果物を正式な出力先へ移す前に、`domain.character_pack` validator と `pack-source.json` に記録した明示上限で完全検証します。

```powershell
python tools/build_character_pack.py --format directory --output .quality-tmp/split/flameblade.mohan
python tools/build_character_pack.py --format zip --output .quality-tmp/split/flameblade.mohan-1.0.0.zip
```

成功時は `PACKAGE_HASH`、`PAYLOAD_FILES`、`PAYLOAD_BYTES`、明示上限、`CHARACTER_PACK_VALID=1` を出力します。ZIP は並べ替えたメンバー、固定日時 1980-01-01、固定権限、追加 metadata なし、`ZIP_STORED`、ZIP64 無効を使用します。同じ入力から同じ `package_hash` と完全に同じ ZIP bytes を生成します。同等のディレクトリと ZIP は同じ論理 `package_hash` を共有します。

本段階では製品の読込先、インストール、更新、実行時組み立てを変更しません。`distribution.access` は所有者が決定した `private`、`standalone_downloadable` は true です。再配布と四種類の素材ライセンスは `owner_decision_pending` のままです。
