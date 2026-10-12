# 素體包發布／素体包发布／Body Pack Release／素体パックの公開

## 繁體中文

source.json 固定素體版本、來源檔案的 bytes/SHA-256、上游 sidecar 收據及 layer dependency。release 建置會先逐檔核對來源，再由 tools/build_body_pack.py 從指定 bald-natural11、gestures3、固定 final core masks 與已核准的 LK layer manifest 重建所有嘴型。建置輸出只放在 .quality-tmp/body-release-1/，不納入來源樹。

更新 lock 時執行 python tools/verify_body_pack_lock.py --update；靜態檢查執行 python tools/verify_body_pack_lock.py。更新會由 source.json 讀取版本，建立 mohan-body-v2 manifest 與可重現 ZIP，並寫入 lock 的檔案、大小及 SHA-256。CI 只重建並比對，不發布或上傳。

來源核對硬性要求 body fingerprint 為 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c。上游歷史 metadata 與 9 筆 gestures PNG hash 漂移保留在 source receipt；它們不會被覆寫成已通過的舊 manifest。完整 CC BY-NC-ND 4.0 法律條文和四語 NOTICE 隨套件提供。

## 简体中文

source.json 固定素体版本、来源文件的 bytes/SHA-256、上游 sidecar 收据及 layer dependency。release 构建会先逐文件核对来源，再由 tools/build_body_pack.py 从指定 bald-natural11、gestures3、固定 final core masks 与已批准的 LK layer manifest 重建全部嘴型。构建输出只放在 .quality-tmp/body-release-1/，不纳入来源树。

更新 lock 时运行 python tools/verify_body_pack_lock.py --update；静态检查运行 python tools/verify_body_pack_lock.py。更新会从 source.json 读取版本，生成 mohan-body-v2 manifest 与可重现 ZIP，并写入 lock 的文件、大小及 SHA-256。CI 只重建并比对，不发布或上传。

来源核对要求 body fingerprint 必须为 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c。上游历史 metadata 与 9 条 gestures PNG hash 漂移保留在 source receipt；不会被改写成旧 manifest 已通过。套件附带完整 CC BY-NC-ND 4.0 法律条文及四语 NOTICE。

## English

source.json pins the body-pack version, source-file byte counts and SHA-256 digests, upstream-sidecar receipts, and layer dependency. A release build verifies every declared source file, then tools/build_body_pack.py rebuilds all mouth states from the designated bald-natural11 and gestures3 sources, fixed final core masks, and the approved LK layer manifest. Build output stays under .quality-tmp/body-release-1/ and is excluded from the source tree.

Run python tools/verify_body_pack_lock.py --update to update the lock, or python tools/verify_body_pack_lock.py for static verification. The update reads the version from source.json, rebuilds the mohan-body-v2 manifest and reproducible ZIP, then records file paths, sizes, and SHA-256 digests in the lock. CI rebuilds and compares without publishing or uploading.

The source check requires body fingerprint 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c. Historical upstream metadata and nine stale gesture PNG hashes remain recorded in the source receipt; they are not rewritten as passing historical manifests. The pack includes the complete CC BY-NC-ND 4.0 legal code and a four-language NOTICE.

## 日本語

source.json はボディパックのバージョン、各ソースファイルの bytes/SHA-256、上流 sidecar の記録、レイヤー依存関係を固定します。リリースビルドは宣言された全ファイルを検証し、tools/build_body_pack.py が指定された bald-natural11 と gestures3、固定済み final core masks、承認済み LK layer manifest から全口形を再構築します。ビルド成果物は .quality-tmp/body-release-1/ に置き、ソースツリーには含めません。

lock 更新には python tools/verify_body_pack_lock.py --update、静的検証には python tools/verify_body_pack_lock.py を実行します。更新処理は source.json からバージョンを読み、mohan-body-v2 manifest と再現可能な ZIP を再構築して、lock にファイルパス、サイズ、SHA-256 を記録します。CI は再構築と照合のみを行い、公開・アップロードは行いません。

ソース検証では body fingerprint 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c を必須とします。上流の履歴 metadata と gestures PNG の古い hash 9 件は source receipt に記録し、過去の manifest を合格扱いに書き換えません。パックには CC BY-NC-ND 4.0 の法的条文全文と四言語 NOTICE を含めます。
