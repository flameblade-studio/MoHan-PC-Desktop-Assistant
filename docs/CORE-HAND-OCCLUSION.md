# 核心手部遮擋／核心手部遮挡／Core hand occlusion／コアの手の遮蔽

## 繁體中文

正式組裝入口會從素體骨架目錄載入 `<pose-prefix>_visible_hand_left.png` 與 `<pose-prefix>_visible_hand_right.png`，使用完整畫布 RGBA 的透明度表示可見手部，並於建立合成器時固定內容。兩檔皆不存在時沿用舊行為；只缺一檔、尺寸錯誤或沒有透明度時直接失敗。此接點不會自行安裝或核可新素材。

`ActiveOutfitOverlay` 的選用接點 `visible_hand_region(view_id)` 只接受核心提供的固定姿勢可見手部區域。提供者在合成器存續期間必須保持不變；更換素體時重建合成器。遮罩應只包含核可的可見皮膚，不能從服裝包讀取，也不能以矩形猜測手的位置。

衣料及既有 `behind-hands` 規則會避開該區域，`front-of-hands` 配件仍可遮擋。空區域表示該姿勢沒有可見手部；超出畫布或缺少已宣告的姿勢規則會失敗。未提供接點的既有流程保持原樣。這不是完整手臂動畫或正式素材安裝；候選驗證使用隔離的核心遮罩，正式接入仍需美術批准與完整驗證。

## 简体中文

正式组装入口会从素体骨架目录加载 `<pose-prefix>_visible_hand_left.png` 与 `<pose-prefix>_visible_hand_right.png`，使用完整画布 RGBA 的透明度表示可见手部，并在创建合成器时固定内容。两文件均不存在时沿用旧行为；只缺一个文件、尺寸错误或没有透明度时直接失败。此接点不会自行安装或批准新素材。

`ActiveOutfitOverlay` 的可选接点 `visible_hand_region(view_id)` 只接受核心提供的固定姿势可见手部区域。提供者在合成器存续期间必须保持不变；更换素体时重建合成器。遮罩应只包含核可的可见皮肤，不能从服装包读取，也不能以矩形猜测手的位置。

衣料及既有 `behind-hands` 规则会避开该区域，`front-of-hands` 配件仍可遮挡。空区域表示该姿势没有可见手部；超出画布或缺少已声明的姿势规则会失败。未提供接点的既有流程保持原样。这不是完整手臂动画或正式素材安装；候选验证使用隔离的核心遮罩，正式接入仍需美术批准与完整验证。

## English

The production composition root loads `<pose-prefix>_visible_hand_left.png` and `<pose-prefix>_visible_hand_right.png` from the core rig directory. Full-canvas RGBA alpha identifies visible hands and is snapshotted when the compositor is created. If both files are absent, legacy behavior is retained. A missing partner, incorrect dimensions or absent alpha fails immediately. This boundary does not install or approve new artwork by itself.

The optional `visible_hand_region(view_id)` boundary in `ActiveOutfitOverlay` accepts only core-owned visible-hand regions for fixed poses. The provider must remain immutable throughout the compositor's lifetime; rebuild the compositor when changing the body. Masks contain approved visible skin only. They must not come from clothing packs or guessed rectangular hand positions.

Garments and existing `behind-hands` rules exclude that region, while `front-of-hands` accessories can still cover it. An empty region means no visible hands in that pose. Out-of-canvas masks or missing declared pose rules fail. Existing paths without the provider remain unchanged. This is not complete arm animation or production asset installation. Candidate validation uses isolated core masks; production integration still requires visual approval and full validation.

## 日本語

正式な組み立て入口は、素体リグのディレクトリから `<pose-prefix>_visible_hand_left.png` と `<pose-prefix>_visible_hand_right.png` を読み込みます。全キャンバス RGBA のアルファが可視の手を示し、合成器の作成時に内容を固定します。両方がなければ従来の動作を維持し、片方の欠落、寸法の誤り、アルファの欠落は直ちに失敗します。この境界自体は新しい素材の導入や承認を行いません。

`ActiveOutfitOverlay` の任意の境界 `visible_hand_region(view_id)` は、固定ポーズのコア所有の可視手領域だけを受け取ります。合成器の存続中は提供者を変更せず、素体を変更するときは合成器を再構築します。マスクには承認済みの可視皮膚だけを含めます。衣装パックから読み込んだり、長方形で手の位置を推測したりしてはいけません。

衣服と既存の `behind-hands` 規則はこの領域を避け、`front-of-hands` アクセサリーは引き続き覆うことができます。空の領域は、そのポーズに可視の手がないことを意味します。画布外のマスクや宣言済みのポーズ規則の欠落は失敗します。提供者のない既存経路は変更しません。完全な腕のアニメーションや正式素材の導入ではありません。候補検証では隔離されたコアマスクを使用し、正式導入には引き続き美術承認と完全な検証が必要です。
