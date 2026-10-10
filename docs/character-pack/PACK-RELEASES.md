# 角色包公開發布與下載／角色包公开发布与下载／Public Character-Pack Releases and Downloads／キャラクターパックの公開と取得

## 繁體中文

### 發布位置與版本

墨寒與林可芸角色包都公開附於 `flameblade-studio/MoHan-PC-Desktop-Assistant` 的 GitHub 發布頁，不使用另一個角色包倉庫，也不需要任何下載金鑰。角色包標籤與墨寒程式版本分開：墨寒使用 `mohan-pack-v1.0.3`，附件為 `flameblade.mohan-1.0.3.zip`；林可芸使用 `lin-keyun-pack-v1.0.2`，附件為 `flameblade.lin-keyun-1.0.2.zip`。

兩個角色包的素材與付費 DLC 均採 CC BY-NC-ND 4.0；完整條款以各包內的 `LICENSE.md` 與儲存庫 `ASSETS-LICENSE.md` 為準。公開下載不改變個別來源與核准紀錄的既有範圍，也不替擁有者決定尚未裁定的 DLC 與角色包關係。

### 下載與驗證

輸出目錄必須尚不存在。下載器從 lock 建立公開 Release 附件網址，不讀取憑證或環境變數；它依序核對 ZIP 位元組數、ZIP SHA-256、角色包格式、引擎相容性、manifest 與逐檔內容。全部通過後才從同一父目錄的暫存區原子移入；任何失敗都不留下半套目的目錄。

```powershell
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan

python tools/fetch_character_pack.py --lock docs/character-pack/lin-keyun-pack.lock.json --output .quality-tmp/split/flameblade.lin-keyun
```

### 發布新版與更新 lock

先更新角色資料與 `pack-source.json` 的版本，再重產清冊。以對應 profile 建立可重現 ZIP 與 lock；輸出路徑必須尚不存在。把該 ZIP 原樣附到上述公開專案的對應角色包標籤，不重新壓縮、改名或編輯。

```powershell
python tools/build_character_inventory.py
python tools/build_character_inventory.py --check
python tools/verify_character_pack_lock.py --profile mohan --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.3.zip
python tools/verify_character_pack_lock.py --profile mohan
python tools/verify_character_pack_lock.py --profile lin-keyun --update --archive-output .quality-tmp/split/flameblade.lin-keyun-1.0.2.zip
python tools/verify_character_pack_lock.py --profile lin-keyun
```

## 简体中文

### 发布位置与版本

墨寒与林可芸角色包都公开附于 `flameblade-studio/MoHan-PC-Desktop-Assistant` 的 GitHub 发布页，不使用另一个角色包仓库，也不需要任何下载密钥。角色包标签与墨寒程序版本分开：墨寒使用 `mohan-pack-v1.0.3`，附件为 `flameblade.mohan-1.0.3.zip`；林可芸使用 `lin-keyun-pack-v1.0.2`，附件为 `flameblade.lin-keyun-1.0.2.zip`。

两个角色包的素材与付费 DLC 均采用 CC BY-NC-ND 4.0；完整条款以各包内的 `LICENSE.md` 与仓库 `ASSETS-LICENSE.md` 为准。公开下载不改变单独来源与批准记录的现有范围，也不替所有者决定尚未裁定的 DLC 与角色包关系。

### 下载与验证

输出目录必须尚不存在。下载器从 lock 建立公开 Release 附件网址，不读取凭据或环境变量；它依次核对 ZIP 字节数、ZIP SHA-256、角色包格式、引擎兼容性、manifest 与逐文件内容。全部通过后才从同一父目录的临时区原子移入；任何失败都不留下不完整的目标目录。

```powershell
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan

python tools/fetch_character_pack.py --lock docs/character-pack/lin-keyun-pack.lock.json --output .quality-tmp/split/flameblade.lin-keyun
```

### 发布新版与更新 lock

先更新角色数据与 `pack-source.json` 的版本，再重新生成清单。使用对应 profile 建立可重现 ZIP 与 lock；输出路径必须尚不存在。把该 ZIP 原样附到上述公开项目的对应角色包标签，不重新压缩、改名或编辑。

```powershell
python tools/build_character_inventory.py
python tools/build_character_inventory.py --check
python tools/verify_character_pack_lock.py --profile mohan --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.3.zip
python tools/verify_character_pack_lock.py --profile mohan
python tools/verify_character_pack_lock.py --profile lin-keyun --update --archive-output .quality-tmp/split/flameblade.lin-keyun-1.0.2.zip
python tools/verify_character_pack_lock.py --profile lin-keyun
```

## English

### Release location and versions

The MoHan and Lin Keyun character packs are public assets on GitHub Releases in `flameblade-studio/MoHan-PC-Desktop-Assistant`. They use no separate character-pack repository and require no download credential. Character-pack tags are separate from MoHan application versions: MoHan uses `mohan-pack-v1.0.3` with `flameblade.mohan-1.0.3.zip`; Lin Keyun uses `lin-keyun-pack-v1.0.2` with `flameblade.lin-keyun-1.0.2.zip`.

Both character packs and paid DLC use CC BY-NC-ND 4.0; the embedded `LICENSE.md` files and the repository's `ASSETS-LICENSE.md` carry the complete terms. Public download does not expand the recorded scope of individual source or approval records and does not decide the still-pending relationship between DLC and a character pack.

### Download and validation

The output directory must not exist. The fetcher builds the public Release asset URL from the lock and reads no credential or environment variable. It verifies ZIP byte count, ZIP SHA-256, character-pack format, engine compatibility, manifest identity, and every payload file in that order. Only a fully valid pack moves atomically from a staging directory on the same parent path; any failure leaves no partial destination.

```powershell
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan

python tools/fetch_character_pack.py --lock docs/character-pack/lin-keyun-pack.lock.json --output .quality-tmp/split/flameblade.lin-keyun
```

### Publishing a version and updating its lock

Update the character data and the version in `pack-source.json`, then regenerate the inventory. Use the matching profile to create the reproducible ZIP and lock; the output path must not exist. Attach that ZIP unchanged to the corresponding character-pack tag in the public project above without recompressing, renaming, or editing it.

```powershell
python tools/build_character_inventory.py
python tools/build_character_inventory.py --check
python tools/verify_character_pack_lock.py --profile mohan --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.3.zip
python tools/verify_character_pack_lock.py --profile mohan
python tools/verify_character_pack_lock.py --profile lin-keyun --update --archive-output .quality-tmp/split/flameblade.lin-keyun-1.0.2.zip
python tools/verify_character_pack_lock.py --profile lin-keyun
```

## 日本語

### 公開場所とバージョン

墨寒と林可芸のキャラクターパックは、`flameblade-studio/MoHan-PC-Desktop-Assistant` の GitHub Releases で公開します。別のキャラクターパックリポジトリや取得用資格情報は使いません。キャラクターパックのタグは墨寒アプリのバージョンと分離します。墨寒は `mohan-pack-v1.0.3` と `flameblade.mohan-1.0.3.zip`、林可芸は `lin-keyun-pack-v1.0.2` と `flameblade.lin-keyun-1.0.2.zip` を使用します。

両キャラクターパックの素材と有料 DLC には CC BY-NC-ND 4.0 を適用し、完全な条件は各パックの `LICENSE.md` とリポジトリの `ASSETS-LICENSE.md` に記載します。公開取得によって個別の出典や承認記録の範囲は拡大せず、未決定の DLC とキャラクターパックの関係も変更しません。

### 取得と検証

出力先は未作成である必要があります。取得ツールは lock から公開 Release 添付ファイルの URL を構成し、資格情報や環境変数を読みません。ZIP のバイト数、SHA-256、キャラクターパック形式、エンジン互換性、manifest、各ファイルを順に照合します。すべて合格したパックだけを同じ親パスの一時領域から原子的に移動し、失敗時に不完全な出力先を残しません。

```powershell
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan

python tools/fetch_character_pack.py --lock docs/character-pack/lin-keyun-pack.lock.json --output .quality-tmp/split/flameblade.lin-keyun
```

### 新版の公開と lock の更新

キャラクターデータと `pack-source.json` のバージョンを更新し、一覧を再生成します。対応 profile で再現可能な ZIP と lock を作成します。出力先は未作成である必要があります。その ZIP を再圧縮、改名、編集せず、上記公開プロジェクトの対応するキャラクターパックタグへ添付します。

```powershell
python tools/build_character_inventory.py
python tools/build_character_inventory.py --check
python tools/verify_character_pack_lock.py --profile mohan --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.3.zip
python tools/verify_character_pack_lock.py --profile mohan
python tools/verify_character_pack_lock.py --profile lin-keyun --update --archive-output .quality-tmp/split/flameblade.lin-keyun-1.0.2.zip
python tools/verify_character_pack_lock.py --profile lin-keyun
```
