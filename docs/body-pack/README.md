# 素體包發布／素体包发布／Body Pack Release／素体パックの公開

## 繁體中文

妝容以已選中影格的來源姿勢為幾何權威。manifest 中別名與來源姿勢的完整 state→檔案綁定相同（path／SHA-256）；渲染器依此解析唯一來源姿勢，再選擇其 makeup_view_id、眼態與產品嘴型規則。front／idle_front 的來源為 front-crossed；attentive_front 的來源為 front-attentive_front，各自使用原有妝容剪影。保留姿勢 front-crossed／cheek-rest 使用產品既有 rest 妝容嘴型規則；完整表情姿勢使用 neutral=None、small=I、a=A、o=O。來源已由既有綁定識別，沿用現行 domain 契約與 fingerprint。

source.json 固定素體版本、來源檔案的 bytes/SHA-256、上游 sidecar 收據及 layer dependency。release 建置會先逐檔核對來源，再由 tools/build_body_pack.py 從指定 bald-natural11、gestures3、固定 final core masks 與已核准的 LK layer manifest 重建所有嘴型。建置輸出只放在 .quality-tmp/body-release-1/，不納入來源樹。

更新 lock 時執行 python tools/verify_body_pack_lock.py --update；靜態檢查執行 python tools/verify_body_pack_lock.py。更新會由 source.json 讀取版本，建立 mohan-body-v2 manifest 與可重現 ZIP，並寫入 lock 的檔案、大小及 SHA-256。CI 只重建並比對，不發布或上傳。

來源核對硬性要求 body fingerprint 為 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c。上游歷史 metadata 與 9 筆 gestures PNG hash 漂移保留在 source receipt；它們不會被覆寫成已通過的舊 manifest。完整 CC BY-NC-ND 4.0 法律條文和四語 NOTICE 隨套件提供。

## 简体中文

妆容以已选中帧的来源姿势为几何权威。manifest 中别名与来源姿势的完整 state→文件绑定相同（path／SHA-256）；渲染器据此解析唯一来源姿势，再选择其 makeup_view_id、眼态与产品嘴型规则。front／idle_front 的来源为 front-crossed；attentive_front 的来源为 front-attentive_front，各自使用原有妆容剪影。保留姿势 front-crossed／cheek-rest 使用产品既有 rest 妆容嘴型规则；完整表情姿势使用 neutral=None、small=I、a=A、o=O。来源已由既有绑定识别，沿用当前 domain 契约与 fingerprint。

source.json 固定素体版本、来源文件的 bytes/SHA-256、上游 sidecar 收据及 layer dependency。release 构建会先逐文件核对来源，再由 tools/build_body_pack.py 从指定 bald-natural11、gestures3、固定 final core masks 与已批准的 LK layer manifest 重建全部嘴型。构建输出只放在 .quality-tmp/body-release-1/，不纳入来源树。

更新 lock 时运行 python tools/verify_body_pack_lock.py --update；静态检查运行 python tools/verify_body_pack_lock.py。更新会从 source.json 读取版本，生成 mohan-body-v2 manifest 与可重现 ZIP，并写入 lock 的文件、大小及 SHA-256。CI 只重建并比对，不发布或上传。

来源核对要求 body fingerprint 必须为 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c。上游历史 metadata 与 9 条 gestures PNG hash 漂移保留在 source receipt；不会被改写成旧 manifest 已通过。套件附带完整 CC BY-NC-ND 4.0 法律条文及四语 NOTICE。

## English

Makeup geometry follows the source pose of the selected frame. Manifest aliases share the complete state-to-file bindings of the source pose (path and SHA-256); the renderer resolves that unique source before selecting makeup_view_id, eye state, and the product mouth-state rules. front/idle_front use front-crossed; attentive_front uses front-attentive_front, each with its authored makeup silhouette. Retained front-crossed/cheek-rest poses use the existing rest makeup mouth-state rules of the product; complete expression poses use neutral=None, small=I, a=A, o=O. Existing bindings identify the source, retaining the current domain contract and fingerprint.

source.json pins the body-pack version, source-file byte counts and SHA-256 digests, upstream-sidecar receipts, and layer dependency. A release build verifies every declared source file, then tools/build_body_pack.py rebuilds all mouth states from the designated bald-natural11 and gestures3 sources, fixed final core masks, and the approved LK layer manifest. Build output stays under .quality-tmp/body-release-1/ and is excluded from the source tree.

Run python tools/verify_body_pack_lock.py --update to update the lock, or python tools/verify_body_pack_lock.py for static verification. The update reads the version from source.json, rebuilds the mohan-body-v2 manifest and reproducible ZIP, then records file paths, sizes, and SHA-256 digests in the lock. CI rebuilds and compares without publishing or uploading.

The source check requires body fingerprint 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c. Historical upstream metadata and nine stale gesture PNG hashes remain recorded in the source receipt; they are not rewritten as passing historical manifests. The pack includes the complete CC BY-NC-ND 4.0 legal code and a four-language NOTICE.

## 日本語

メイクの形状は選択したフレームのソース姿勢を基準にします。manifest の別名はソース姿勢と同じ全 state→ファイル対応（path／SHA-256）を持ちます。レンダラーは一意のソースを解決してから makeup_view_id、眼の状態、製品の口形規則を選びます。front／idle_front は front-crossed、attentive_front は front-attentive_front を使い、それぞれ元のメイク輪郭に従います。保持された front-crossed／cheek-rest は製品の既存 rest メイク口形規則を使用し、完全表情姿勢は neutral=None、small=I、a=A、o=O を使用します。既存の対応でソースを識別できるため、現行 domain 契約と fingerprint を維持します。

source.json はボディパックのバージョン、各ソースファイルの bytes/SHA-256、上流 sidecar の記録、レイヤー依存関係を固定します。リリースビルドは宣言された全ファイルを検証し、tools/build_body_pack.py が指定された bald-natural11 と gestures3、固定済み final core masks、承認済み LK layer manifest から全口形を再構築します。ビルド成果物は .quality-tmp/body-release-1/ に置き、ソースツリーには含めません。

lock 更新には python tools/verify_body_pack_lock.py --update、静的検証には python tools/verify_body_pack_lock.py を実行します。更新処理は source.json からバージョンを読み、mohan-body-v2 manifest と再現可能な ZIP を再構築して、lock にファイルパス、サイズ、SHA-256 を記録します。CI は再構築と照合のみを行い、公開・アップロードは行いません。

ソース検証では body fingerprint 6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c を必須とします。上流の履歴 metadata と gestures PNG の古い hash 9 件は source receipt に記録し、過去の manifest を合格扱いに書き換えません。パックには CC BY-NC-ND 4.0 の法的条文全文と四言語 NOTICE を含めます。
