### 素體只合成預設髮型／素体仅合成默认发型／Base bodies compose only default hair／素体は既定の髪だけを合成

- 素體畫面依宣告順序只保留 base、hair-back、hair-front 與 ornament，略過身體修正、妝容、服裝層及共用遮罩；缺少預設頭髮時仍回報錯誤。／素体画面按声明顺序只保留 base、hair-back、hair-front 与 ornament，略过身体修正、妆容、服装层及共享遮罩；缺少默认头发时仍报告错误。／Base body views keep only base, hair-back, hair-front, and ornament in their declared order, omitting body fixes, makeup, clothing layers, and the shared mask; missing default hair still produces an error.／素体表示は base、hair-back、hair-front、ornament のみを宣言順で保持し、身体補正、メイク、服装レイヤー、共有マスクを省きます。既定の髪が欠けている場合は引き続きエラーを表示します。

- 林可芸頭髮層的服裝邊緣像素移入服裝層，保持完整穿衣重組結果，並更新清冊與角色包 lock。／林可芸头发层的服装边缘像素移入服装层，保持完整穿衣重组结果，并更新清册与角色包 lock。／Move clothing edge pixels from Lin Keyun hair to garment layers, preserve the clothed reconstruction, and update the inventory and character-pack lock.／林可芸の髪レイヤーにある衣装の境界画素を衣装レイヤーへ移し、着衣時の再合成結果を維持して、インベントリとキャラクターパックの lock を更新します。
