# 私有墨寒角色包操作指南／私有墨寒角色包操作指南／Private MoHan Character Pack Guide／非公開の墨寒キャラクターパック運用ガイド

## 繁體中文

### 這一步的邊界

`flameblade-studio/mohan-character-pack` 是擁有者核定的私有角色包倉庫。公開墨寒專案保留 `character-pack.lock.json`，以版本、邏輯 `package_hash`、逐檔 SHA-256、ZIP SHA-256 與位元組數指向一個確定的私有 Release 附件。本階段不改寫公開歷史、不刪除公開專案內任何角色素材，也不改安裝、更新、執行期或 352 格標準畫面的既有行為。

預設藍白漢服與內建妝容屬於墨寒角色包。服裝及配飾 DLC 是掛在角色包下的獨立小包；佈景主題 DLC 與角色包無關。角色素材授權與再散布狀態仍由擁有者決定；私有技術路徑不代表新增任何散布或開源授權。

### 由擁有者建立私有倉庫

1. 在 GitHub 的 `flameblade-studio` 組織選擇 **New repository**。
2. 倉庫名稱填入 `mohan-character-pack`，可見性選擇 **Private**。
3. 建立全新倉庫，不匯入或改寫公開墨寒專案的 Git 歷史。
4. 每一版角色包用私有倉庫的 Release 保存；tag 使用 `mohan-pack-v<角色包版本>`，附件名稱使用 `flameblade.mohan-<角色包版本>.zip`。
5. 公開專案目前仍保留角色圖。移除公開素材屬最後階段，執行前必須再次取得擁有者明確核准。

### 由擁有者建立只讀鑰匙

GitHub Release API 需要可讀取該私有倉庫的 fine-grained personal access token。這把鑰匙由擁有者在 GitHub 網頁建立；工程代理不建立、不接收也不代貼鑰匙。

1. 進入 GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens**，選擇 **Generate new token**。
2. Resource owner 選擇 `flameblade-studio`；Repository access 選擇 **Only select repositories**，只勾選 `mohan-character-pack`。
3. Repository permissions 只開啟 **Contents: Read-only**；Metadata 維持 GitHub 自動提供的 read-only，不開啟寫入或其他權限。設定適當期限；若組織要求核准，完成組織核准流程。
4. 產生後直接前往公開墨寒專案的 **Settings → Secrets and variables → Actions → New repository secret**。
5. Secret 名稱填 `MOHAN_CHARACTER_PACK_TOKEN`，值貼入剛建立的 token。不要放入 Actions variable、檔案、命令列參數、issue、PR 或日誌。

新的一致性 workflow 不讀取這個 secret，也不連私有倉庫；它只用公開 PR 內的素材重建角色包並核對 lock。因此外部 fork PR 沒有 secret 仍能執行這項檢查。日後只有擁有者倉庫內、確實需要下載私有角色包的封裝工作才可讀取 secret；fork PR 本來就不會取得 Actions secret。

### 發行新版並更新鎖定

1. 在公開墨寒工作樹更新角色包資料與 `assets/characters/mohan/pack-source.json` 的 `pack_version`，保留尚未決定的授權欄位原狀。
2. 重新產生並檢查清冊：

   ```powershell
   python tools/build_character_inventory.py
   python tools/build_character_inventory.py --check
   ```

3. 用明確的 `--update` 同時建立要上傳的可重現 ZIP 與新 lock。輸出路徑必須尚不存在，範例版本請換成這次版本：

   ```powershell
   python tools/verify_character_pack_lock.py --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.0.zip
   python tools/verify_character_pack_lock.py
   ```

4. 在私有倉庫建立 tag `mohan-pack-v1.0.0` 的 Release，原樣上傳 `.quality-tmp/split/flameblade.mohan-1.0.0.zip`。不要重新壓縮、改名或編輯 ZIP。
5. 核對命令輸出的 `PACKAGE_HASH`、`ARCHIVE_SHA256`、`ARCHIVE_BYTES` 與 `character-pack.lock.json` 完全一致，再審查並提交 lock。一般驗證永遠不自動改 lock；只有明確傳入 `--update` 才會重寫。

### 本機一鍵取得

先把 token 放入目前程序的環境變數，再執行一個下載命令。輸出目錄必須尚不存在。PowerShell 7 可用遮罩輸入，完成後立即清除程序環境變數：

```powershell
$env:MOHAN_CHARACTER_PACK_TOKEN = Read-Host "MoHan private-pack read token" -MaskInput
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan
Remove-Item Env:MOHAN_CHARACTER_PACK_TOKEN
```

工具只從 `MOHAN_CHARACTER_PACK_TOKEN` 讀取鑰匙，不接受 token 命令列參數，也不輸出或寫入鑰匙。它先核對 ZIP 的 SHA-256 與位元組數，再以 lock 內 S6 明確上限執行 `domain.character_pack` validator，全部通過後才在暫存目錄解壓並一次移入目的地。缺鑰匙、下載失敗、雜湊不符、包格式錯誤或目的地已存在都以非零退出，且不留下半套目的目錄。

## 简体中文

### 本步骤的边界

`flameblade-studio/mohan-character-pack` 是所有者批准的私有角色包仓库。公开墨寒项目保留 `character-pack.lock.json`，通过版本、逻辑 `package_hash`、逐文件 SHA-256、ZIP SHA-256 和字节数指向一个确定的私有 Release 附件。本阶段不改写公开历史、不删除公开项目中的任何角色素材，也不改变安装、更新、运行时或 352 格标准画面的现有行为。

默认蓝白汉服和内置妆容属于墨寒角色包。服装和配饰 DLC 是挂在角色包下的独立小包；主题 DLC 与角色包无关。角色素材授权和再分发状态仍由所有者决定；私有技术路径不代表新增任何分发或开源授权。

### 由所有者建立私有仓库

1. 在 GitHub 的 `flameblade-studio` 组织选择 **New repository**。
2. 仓库名称填写 `mohan-character-pack`，可见性选择 **Private**。
3. 建立全新仓库，不导入或改写公开墨寒项目的 Git 历史。
4. 每一版角色包用私有仓库的 Release 保存；tag 使用 `mohan-pack-v<角色包版本>`，附件名称使用 `flameblade.mohan-<角色包版本>.zip`。
5. 公开项目目前仍保留角色图。移除公开素材属于最后阶段，执行前必须再次取得所有者明确批准。

### 由所有者建立只读密钥

GitHub Release API 需要可读取该私有仓库的 fine-grained personal access token。此密钥由所有者在 GitHub 网页建立；工程代理不建立、不接收也不代贴密钥。

1. 进入 GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens**，选择 **Generate new token**。
2. Resource owner 选择 `flameblade-studio`；Repository access 选择 **Only select repositories**，只勾选 `mohan-character-pack`。
3. Repository permissions 只开启 **Contents: Read-only**；Metadata 保持 GitHub 自动提供的 read-only，不开启写入或其他权限。设置适当期限；若组织要求批准，完成组织批准流程。
4. 生成后直接前往公开墨寒项目的 **Settings → Secrets and variables → Actions → New repository secret**。
5. Secret 名称填写 `MOHAN_CHARACTER_PACK_TOKEN`，值粘贴刚建立的 token。不要放入 Actions variable、文件、命令行参数、issue、PR 或日志。

新的一致性 workflow 不读取此 secret，也不连接私有仓库；它只使用公开 PR 内的素材重建角色包并核对 lock。因此外部 fork PR 没有 secret 仍能执行此项检查。以后只有所有者仓库内、确实需要下载私有角色包的打包工作才可读取 secret；fork PR 本来就不会取得 Actions secret。

### 发布新版并更新锁定

1. 在公开墨寒工作树更新角色包数据和 `assets/characters/mohan/pack-source.json` 的 `pack_version`，保留尚未决定的授权字段原状。
2. 重新生成并检查清单：

   ```powershell
   python tools/build_character_inventory.py
   python tools/build_character_inventory.py --check
   ```

3. 用明确的 `--update` 同时建立要上传的可重现 ZIP 和新 lock。输出路径必须尚不存在，示例版本请替换为本次版本：

   ```powershell
   python tools/verify_character_pack_lock.py --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.0.zip
   python tools/verify_character_pack_lock.py
   ```

4. 在私有仓库建立 tag `mohan-pack-v1.0.0` 的 Release，原样上传 `.quality-tmp/split/flameblade.mohan-1.0.0.zip`。不要重新压缩、改名或编辑 ZIP。
5. 核对命令输出的 `PACKAGE_HASH`、`ARCHIVE_SHA256`、`ARCHIVE_BYTES` 与 `character-pack.lock.json` 完全一致，再审查并提交 lock。一般验证永远不自动修改 lock；只有明确传入 `--update` 才会重写。

### 本地一键获取

先把 token 放入当前进程的环境变量，再执行一个下载命令。输出目录必须尚不存在。PowerShell 7 可使用掩码输入，完成后立即清除进程环境变量：

```powershell
$env:MOHAN_CHARACTER_PACK_TOKEN = Read-Host "MoHan private-pack read token" -MaskInput
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan
Remove-Item Env:MOHAN_CHARACTER_PACK_TOKEN
```

工具只从 `MOHAN_CHARACTER_PACK_TOKEN` 读取密钥，不接受 token 命令行参数，也不输出或写入密钥。它先核对 ZIP 的 SHA-256 和字节数，再按 lock 内 S6 明确上限执行 `domain.character_pack` validator，全部通过后才在临时目录解压并一次移入目标目录。缺少密钥、下载失败、哈希不符、包格式错误或目标目录已存在都会以非零状态退出，且不留下半套目标目录。

## English

### Scope of this step

`flameblade-studio/mohan-character-pack` is the owner-approved private character-pack repository. The public MoHan repository retains `character-pack.lock.json`, which identifies one exact private Release asset by version, logical `package_hash`, per-file SHA-256 values, ZIP SHA-256, and byte count. This phase does not rewrite public history, remove any character asset from the public repository, or change existing installation, update, runtime, or 352-cell golden behavior.

The default blue-and-white Hanfu and built-in makeup belong to the MoHan character pack. Clothing and accessory DLCs are separate small packages attached to a character pack; theme DLCs are unrelated to character packs. Character-asset licensing and redistribution remain owner decisions. A private technical path grants no new distribution or open-source permission.

### Owner setup of the private repository

1. Choose **New repository** in the GitHub `flameblade-studio` organization.
2. Enter `mohan-character-pack` and select **Private** visibility.
3. Create a new repository without importing or rewriting the public MoHan Git history.
4. Store each character-pack version as a Release in the private repository. Use `mohan-pack-v<pack version>` for the tag and `flameblade.mohan-<pack version>.zip` for the asset name.
5. Character images remain in the public repository during this phase. Removing them is the final phase and requires renewed, explicit owner approval before execution.

### Owner setup of the read-only credential

The GitHub Release API requires a fine-grained personal access token that can read this one private repository. The owner creates it in the GitHub web interface. The engineering agent does not create, receive, or paste the credential.

1. Open GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens**, then choose **Generate new token**.
2. Select `flameblade-studio` as the resource owner. Under Repository access choose **Only select repositories** and select only `mohan-character-pack`.
3. Grant only **Contents: Read-only** under Repository permissions. Leave Metadata at GitHub's automatically supplied read-only access and grant no write or unrelated permission. Choose an appropriate expiry and complete organization approval if required.
4. Open the public MoHan repository's **Settings → Secrets and variables → Actions → New repository secret**.
5. Name the secret `MOHAN_CHARACTER_PACK_TOKEN` and paste the new token as its value. Never place it in an Actions variable, file, command-line argument, issue, PR, or log.

The new consistency workflow neither reads this secret nor connects to the private repository. It rebuilds the pack solely from public PR contents and checks the lock, so fork PRs can run it without a secret. Only a future packaging job in the owner's repository that truly downloads the private pack may read the secret; fork PRs do not receive Actions secrets.

### Publishing a new version and updating the lock

1. Update the pack data and `pack_version` in `assets/characters/mohan/pack-source.json` in the public MoHan worktree. Preserve every undecided license field.
2. Regenerate and check the inventory:

   ```powershell
   python tools/build_character_inventory.py
   python tools/build_character_inventory.py --check
   ```

3. Use explicit `--update` to produce both the reproducible upload ZIP and the new lock. The output path must not exist; replace the example version with the current version:

   ```powershell
   python tools/verify_character_pack_lock.py --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.0.zip
   python tools/verify_character_pack_lock.py
   ```

4. Create a Release tagged `mohan-pack-v1.0.0` in the private repository and upload `.quality-tmp/split/flameblade.mohan-1.0.0.zip` unchanged. Do not recompress, rename, or edit the ZIP.
5. Confirm that `PACKAGE_HASH`, `ARCHIVE_SHA256`, and `ARCHIVE_BYTES` match `character-pack.lock.json` exactly before reviewing and committing the lock. Ordinary verification never updates the lock; only explicit `--update` rewrites it.

### One-command local fetch

Put the token in the current process environment, then run one fetch command. The output directory must not exist. PowerShell 7 can mask the input; remove the process environment variable immediately afterward:

```powershell
$env:MOHAN_CHARACTER_PACK_TOKEN = Read-Host "MoHan private-pack read token" -MaskInput
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan
Remove-Item Env:MOHAN_CHARACTER_PACK_TOKEN
```

The tool reads the credential only from `MOHAN_CHARACTER_PACK_TOKEN`. It accepts no token command-line option and never prints or writes the token. It first verifies the ZIP SHA-256 and byte count, then runs the `domain.character_pack` validator with the explicit S6 limits pinned in the lock. Only a fully valid pack is extracted into a staging directory and moved into place at once. A missing token, failed download, checksum mismatch, invalid pack, or existing destination returns nonzero and leaves no partial destination.

## 日本語

### この段階の範囲

`flameblade-studio/mohan-character-pack` は、所有者が承認した非公開キャラクターパックリポジトリです。公開の墨寒プロジェクトには `character-pack.lock.json` を残し、バージョン、論理 `package_hash`、各ファイルの SHA-256、ZIP の SHA-256、バイト数によって一つの非公開 Release 添付ファイルを特定します。この段階では公開履歴を書き換えず、公開プロジェクトのキャラクター素材を削除せず、既存のインストール、更新、ランタイム、352 セルの標準画像の挙動も変更しません。

既定の青白い漢服と内蔵メイクは墨寒キャラクターパックに属します。衣装とアクセサリーの DLC はキャラクターパックに付属する独立した小規模パックです。テーマ DLC はキャラクターパックと無関係です。キャラクター素材のライセンスと再配布状態は引き続き所有者が決定します。非公開の技術経路によって新しい配布許可やオープンソース許可が生じることはありません。

### 所有者による非公開リポジトリの作成

1. GitHub の `flameblade-studio` Organization で **New repository** を選択します。
2. リポジトリ名を `mohan-character-pack` とし、可視性に **Private** を選択します。
3. 公開の墨寒プロジェクトの Git 履歴をインポートまたは書き換えず、新しいリポジトリを作成します。
4. 各バージョンのキャラクターパックを非公開リポジトリの Release に保存します。tag は `mohan-pack-v<パックバージョン>`、添付ファイル名は `flameblade.mohan-<パックバージョン>.zip` とします。
5. この段階ではキャラクター画像を公開リポジトリに残します。公開素材の削除は最終段階に属し、実行前に所有者の明示的な再承認が必要です。

### 所有者による読み取り専用資格情報の作成

GitHub Release API には、この非公開リポジトリだけを読み取れる fine-grained personal access token が必要です。所有者が GitHub の Web 画面で作成します。工程代理は資格情報を作成、受領、代理入力しません。

1. GitHub の **Settings → Developer settings → Personal access tokens → Fine-grained tokens** を開き、**Generate new token** を選択します。
2. Resource owner に `flameblade-studio` を選択します。Repository access では **Only select repositories** を選び、`mohan-character-pack` だけを指定します。
3. Repository permissions は **Contents: Read-only** だけを有効にします。Metadata は GitHub が自動で付与する read-only のままにし、書き込み権限や無関係な権限を付与しません。適切な有効期限を設定し、Organization の承認が必要な場合は承認手続きを完了します。
4. 公開の墨寒リポジトリで **Settings → Secrets and variables → Actions → New repository secret** を開きます。
5. Secret 名を `MOHAN_CHARACTER_PACK_TOKEN` とし、新しい token を値として貼り付けます。Actions variable、ファイル、コマンドライン引数、issue、PR、ログには保存しません。

新しい整合性 workflow はこの secret を読み取らず、非公開リポジトリにも接続しません。公開 PR 内の素材だけでパックを再構築して lock と照合するため、外部 fork PR も secret なしで実行できます。将来、所有者のリポジトリ内で非公開パックを実際に取得するパッケージ作業だけが secret を読み取れます。fork PR には Actions secret が渡されません。

### 新版の公開と lock の更新

1. 公開の墨寒ワークツリーでパックデータと `assets/characters/mohan/pack-source.json` の `pack_version` を更新します。未決定のライセンス項目はそのまま保持します。
2. 一覧を再生成して確認します。

   ```powershell
   python tools/build_character_inventory.py
   python tools/build_character_inventory.py --check
   ```

3. 明示的な `--update` で、アップロード用の再現可能 ZIP と新しい lock を同時に生成します。出力先は未作成である必要があります。例のバージョンは今回のバージョンに置き換えます。

   ```powershell
   python tools/verify_character_pack_lock.py --update --archive-output .quality-tmp/split/flameblade.mohan-1.0.0.zip
   python tools/verify_character_pack_lock.py
   ```

4. 非公開リポジトリで tag `mohan-pack-v1.0.0` の Release を作成し、`.quality-tmp/split/flameblade.mohan-1.0.0.zip` を変更せずにアップロードします。ZIP を再圧縮、改名、編集しません。
5. lock をレビューしてコミットする前に、命令出力の `PACKAGE_HASH`、`ARCHIVE_SHA256`、`ARCHIVE_BYTES` が `character-pack.lock.json` と完全に一致することを確認します。通常の検証は lock を自動更新しません。明示的な `--update` だけが書き換えます。

### ローカルでの一命令取得

token を現在のプロセスの環境変数へ設定してから、一つの取得命令を実行します。出力ディレクトリは未作成である必要があります。PowerShell 7 では入力をマスクでき、完了後すぐにプロセス環境変数を削除します。

```powershell
$env:MOHAN_CHARACTER_PACK_TOKEN = Read-Host "MoHan private-pack read token" -MaskInput
python tools/fetch_character_pack.py --output .quality-tmp/split/flameblade.mohan
Remove-Item Env:MOHAN_CHARACTER_PACK_TOKEN
```

ツールは資格情報を `MOHAN_CHARACTER_PACK_TOKEN` からだけ読み取ります。token のコマンドライン引数はなく、token を出力またはファイルへ書き込みません。最初に ZIP の SHA-256 とバイト数を照合し、次に lock に固定された S6 の明示的上限で `domain.character_pack` validator を実行します。すべてに合格したパックだけを一時ディレクトリへ展開し、最後に一度で目的地へ移動します。token 不足、取得失敗、チェックサム不一致、不正なパック、既存の目的地はいずれも 0 以外で終了し、不完全な目的ディレクトリを残しません。
