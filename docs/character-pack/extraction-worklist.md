# 角色內容抽離待辦摘要／角色内容抽离待办摘要／Character Extraction Worklist Summary／キャラクター内容抽出一覧

## 繁體中文

實測後，真正仍需搬離引擎或改由角色資料代入的程式檔有 96 個：引擎抽離 62 個、介面名稱參照 34 個。另有 7 個檔案屬墨寒產品殼，可按逐檔理由保留品牌內容。

舊名單另有 36 個檔案只剩人工複核提示，沒有實際內容規則證據，因此不計入待搬數。每個待搬檔只出現在下列一個獨占工作包。

| 工作包 | 獨占檔案數 |
|---|---:|
| 引擎身分參數化 (`engine-identity-parameterization`) | 18 |
| Rig 與素材路徑參數化 (`rig-and-asset-parameterization`) | 44 |
| 介面角色名稱參數化 (`ui-name-parameterization`) | 34 |

### 產品殼允許保留

`application/runtime_bootstrap.py`、`domain/version_info.py`、`infrastructure/app_resources.py`、`infrastructure/profile_transfer.py`、`infrastructure/updater.py`、`presentation/auxiliary_ui_localization.py`、`presentation/preview_app.py`

角色素材授權與 DLC 關係仍待擁有者決定；本清單不改變私有倉庫與獨立下載設計裁定。

詳細證據與逐檔理由見 `extraction-worklist.json`。

## 简体中文

实测后，真正仍需从引擎移出或改为由角色数据代入的程序文件有 96 个：引擎抽离 62 个、界面名称引用 34 个。另有 7 个文件属于墨寒产品壳，可按逐文件理由保留品牌内容。

旧名单另有 36 个文件只剩人工复核提示，没有实际内容规则证据，因此不计入待迁移数。每个待迁移文件只出现在下列一个独占工作包。

| 工作包 | 独占文件数 |
|---|---:|
| 引擎身份参数化 (`engine-identity-parameterization`) | 18 |
| Rig 与素材路径参数化 (`rig-and-asset-parameterization`) | 44 |
| 界面角色名称参数化 (`ui-name-parameterization`) | 34 |

### 产品壳允许保留

`application/runtime_bootstrap.py`、`domain/version_info.py`、`infrastructure/app_resources.py`、`infrastructure/profile_transfer.py`、`infrastructure/updater.py`、`presentation/auxiliary_ui_localization.py`、`presentation/preview_app.py`

角色素材授权与 DLC 关系仍待所有者决定；本清单不改变私有仓库和独立下载设计裁定。

详细证据与逐文件理由见 `extraction-worklist.json`。

## English

Measurement finds 96 source files that still need engine extraction or character-data substitution: 62 engine-extraction files and 34 UI-name references. Another 7 files belong to the MoHan product shell and may retain branded content for their recorded per-file reasons.

The old list leaves 36 manual-review-only hints with no content-rule evidence; they are not counted as extraction work. Every pending file belongs to exactly one exclusive package below.

| Work package | Exclusive files |
|---|---:|
| Engine identity parameterization (`engine-identity-parameterization`) | 18 |
| Rig and asset parameterization (`rig-and-asset-parameterization`) | 44 |
| UI character-name parameterization (`ui-name-parameterization`) | 34 |

### Allowed product-shell files

`application/runtime_bootstrap.py`、`domain/version_info.py`、`infrastructure/app_resources.py`、`infrastructure/profile_transfer.py`、`infrastructure/updater.py`、`presentation/auxiliary_ui_localization.py`、`presentation/preview_app.py`

Character-asset licensing and the DLC relationship still require the owner's decision; this list does not change the private-repository or independent-download decisions.

See `extraction-worklist.json` for detailed evidence and per-file reasons.

## 日本語

実測の結果、エンジンからの抽出またはキャラクターデータによる差し替えが必要なソースは 96 ファイルです。内訳はエンジン抽出 62、UI の名前参照 34 です。別に 7 ファイルは墨寒製品シェルに属し、ファイルごとの理由に従ってブランド内容を保持できます。

旧一覧には実内容の規則証拠がない人工確認専用の候補が 36 ファイル残りますが、抽出数には含めません。各対象ファイルは以下の独占作業パッケージ一つだけに属します。

| 作業パッケージ | 独占ファイル数 |
|---|---:|
| エンジン身元のパラメータ化 (`engine-identity-parameterization`) | 18 |
| Rig と素材パスのパラメータ化 (`rig-and-asset-parameterization`) | 44 |
| UI キャラクター名のパラメータ化 (`ui-name-parameterization`) | 34 |

### 製品シェルで保持可能

`application/runtime_bootstrap.py`、`domain/version_info.py`、`infrastructure/app_resources.py`、`infrastructure/profile_transfer.py`、`infrastructure/updater.py`、`presentation/auxiliary_ui_localization.py`、`presentation/preview_app.py`

キャラクター素材のライセンスと DLC の関係は所有者の決定待ちです。本一覧は非公開リポジトリと独立ダウンロード設計の決定を変更しません。

詳細な証拠とファイルごとの理由は `extraction-worklist.json` を参照してください。
