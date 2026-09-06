# 妝容細節控制／妆容细节控制／Makeup detail controls／メイクの詳細調整

## 繁體中文

雲裳閣保留「妝感濃淡」，並提供眼妝、腮紅、唇妝各自的濃淡滑桿。三項預設為 100%；套件濃度、整體濃度與該項濃度相乘後套用，不改變五官位置。將三項調回 100% 可恢復套件原有的比例。

設定沿用 `makeup.json`，選填的 `slot_intensities` 物件使用 `eyes`、`cheeks`、`lips` 三個鍵，值為 0 到 1。舊檔案沒有此欄位時，三項都是 1；修改整體濃度不會清除細節設定。無效資料保留上一個有效值並透過既有提示流程通知。DLC 格式、妝容安全區、虹膜與口腔排除規則不變。

此控制功能不代表 V4 外觀素材遷移已完成；預設外觀的一致性仍須對每個姿勢另行驗證。

隔離的新素體製作可向 `build_outfit_pack` 傳入由該素體骨架推導的 `makeup_regions`，封裝時仍逐像素檢查安全區。省略參數時沿用已安裝素體的定位；匯入時另依已安裝素體檢查，候選定位不會隨套件覆寫正式定位。

## 简体中文

云裳阁保留“妆感浓淡”，并提供眼妆、腮红、唇妆各自的浓淡滑块。三项默认为 100%；套件浓度、整体浓度与该项浓度相乘后应用，不改变五官位置。将三项调回 100% 可恢复套件原有的比例。

设置沿用 `makeup.json`，可选的 `slot_intensities` 对象使用 `eyes`、`cheeks`、`lips` 三个键，值为 0 到 1。旧文件没有此字段时，三项都是 1；修改整体浓度不会清除细节设置。无效数据保留上一个有效值并通过现有提示流程通知。DLC 格式、妆容安全区、虹膜与口腔排除规则不变。

此控制功能不代表 V4 外观素材迁移已完成；默认外观的一致性仍须对每个姿势单独验证。

隔离的新素体制作可向 `build_outfit_pack` 传入由该素体骨架推导的 `makeup_regions`，封装时仍逐像素检查安全区。省略参数时沿用已安装素体的定位；导入时另依已安装素体检查，候选定位不会随套件覆盖正式定位。

## English

The Wardrobe Pavilion retains overall makeup intensity and adds separate eye makeup, blush and lip makeup sliders. Each defaults to 100%. Pack, overall and slot intensities multiply without moving facial features. Returning all three to 100% restores the pack's original balance.

Settings remain in `makeup.json`. The optional `slot_intensities` object accepts `eyes`, `cheeks` and `lips`, each between 0 and 1. Legacy files default each slot to 1. Changing overall intensity preserves detail settings. Invalid data retains the last valid values and uses the existing notification flow. DLC formats, safe regions and iris/oral exclusions remain unchanged.

These controls do not establish completion of the V4 artwork migration; default appearance equivalence must still be verified for every pose.

An isolated body rebuild may pass rig-derived `makeup_regions` to `build_outfit_pack`; sealing still checks every painted pixel against its safe region. Omitting the argument uses the installed body's calibration. Import independently checks that installed calibration; candidate regions do not overwrite it through a pack.

## 日本語

雲裳閣ではメイク全体の濃さに加え、アイメイク、チーク、リップメイクを個別に調整できます。各項目の既定値は 100% です。パック、全体、各項目の濃さを掛け合わせて適用し、顔の各部位の位置は変更しません。三項目を 100% に戻すと、パック本来の比率に戻ります。

設定は引き続き `makeup.json` に保存します。任意の `slot_intensities` オブジェクトは `eyes`、`cheeks`、`lips` を使用し、各値は 0 から 1 です。旧ファイルでは各項目を 1 として扱い、全体の濃さを変更しても詳細設定を保持します。不正なデータでは直前の有効値を維持し、既存の通知経路で知らせます。DLC 形式、安全領域、虹彩と口腔の除外規則は変更しません。

この調整機能は V4 素材への移行完了を意味しません。既定外観の一致は全ポーズで別途検証する必要があります。

隔離環境で新しい素体を制作する場合、リグから導出した `makeup_regions` を `build_outfit_pack` に渡せます。パック作成時も描画ピクセルごとに安全領域を検証します。省略時はインストール済み素体の位置情報を使用します。インポート時もその位置情報で独立して検証し、候補の位置情報がパック経由で正式な設定を上書きすることはありません。
