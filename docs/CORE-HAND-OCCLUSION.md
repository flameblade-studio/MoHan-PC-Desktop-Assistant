# 核心手部遮擋／核心手部遮挡／Core hand occlusion／コアの手の遮蔽

## 繁體中文

正式組裝入口會從素體骨架目錄載入 `<pose-prefix>_visible_hand_left.png` 與 `<pose-prefix>_visible_hand_right.png`，使用完整畫布 RGBA 的透明度表示可見手部，並於建立合成器時固定內容。兩檔皆省略時沿用舊行為；載入器只接受成對、尺寸正確且具有透明度的檔案。新素材的安裝與核可仍由既有正式流程負責。

`ActiveOutfitOverlay` 的選用接點 `visible_hand_region(view_id)` 只接受核心提供的固定姿勢可見手部區域。提供者在合成器存續期間維持固定；更換素體時重建合成器。遮罩內容限定為核心提供的核可可見皮膚，並以實際遮罩表達手的位置。

衣料及既有 `behind-hands` 規則會避開該區域，`front-of-hands` 配件仍可遮擋。空區域表示該姿勢的可見手部集合為空；有效遮罩位於畫布內，且每個已宣告姿勢皆有對應規則。省略接點時沿用既有流程。這項能力涵蓋核心手部遮擋；完整手臂動畫與正式素材安裝仍各自走既有流程。候選驗證使用隔離的核心遮罩，正式接入仍需美術批准與完整驗證。

## 简体中文

正式组装入口会从素体骨架目录加载 `<pose-prefix>_visible_hand_left.png` 与 `<pose-prefix>_visible_hand_right.png`，使用完整画布 RGBA 的透明度表示可见手部，并在创建合成器时固定内容。两个文件均省略时沿用旧行为；加载器只接受成对、尺寸正确且具有透明度的文件。新素材的安装与批准仍由现有正式流程负责。

`ActiveOutfitOverlay` 的可选接点 `visible_hand_region(view_id)` 只接受核心提供的固定姿势可见手部区域。提供者在合成器存续期间维持固定；更换素体时重建合成器。遮罩内容限定为核心提供的核可可见皮肤，并以实际遮罩表达手的位置。

衣料及既有 `behind-hands` 规则会避开该区域，`front-of-hands` 配件仍可遮挡。空区域表示该姿势的可见手部集合为空；有效遮罩位于画布内，且每个已声明姿势均有对应规则。省略接点时沿用现有流程。这项能力涵盖核心手部遮挡；完整手臂动画与正式素材安装仍各自遵循现有流程。候选验证使用隔离的核心遮罩，正式接入仍需美术批准与完整验证。

## English

The production composition root loads `<pose-prefix>_visible_hand_left.png` and `<pose-prefix>_visible_hand_right.png` from the core rig directory. Full-canvas RGBA alpha identifies visible hands and is snapshotted when the compositor is created. Omitting both files retains legacy behavior. The loader accepts a complete pair with correct dimensions and alpha. New artwork installation and approval remain with the established production process.

The optional `visible_hand_region(view_id)` boundary in `ActiveOutfitOverlay` accepts core-owned visible-hand regions for fixed poses. The provider remains fixed throughout the compositor's lifetime; rebuild the compositor when changing the body. Masks contain core-supplied, approved visible skin and express hand positions through the actual mask geometry.

Garments and existing `behind-hands` rules exclude that region, while `front-of-hands` accessories can still cover it. An empty region represents an empty visible-hand set for that pose. Valid masks stay within the canvas, and every declared pose has a corresponding rule. Omitting the provider retains the existing path. This capability covers core hand occlusion; complete arm animation and production asset installation continue through their established processes. Candidate validation uses isolated core masks; production integration still requires visual approval and full validation.

## 日本語

正式な組み立て入口は、素体リグのディレクトリから `<pose-prefix>_visible_hand_left.png` と `<pose-prefix>_visible_hand_right.png` を読み込みます。全キャンバス RGBA のアルファが可視の手を示し、合成器の作成時に内容を固定します。両方を省略した場合は従来の動作を維持します。ローダーが受け入れるのは、対が揃い、寸法が正しく、アルファを持つファイルです。新しい素材の導入と承認は、既存の正式手順が引き続き担当します。

`ActiveOutfitOverlay` の任意の境界 `visible_hand_region(view_id)` は、固定ポーズのコア所有の可視手領域だけを受け取ります。合成器の存続中は提供者を変更せず、素体を変更するときは合成器を再構築します。マスクには承認済みの可視皮膚だけを含めます。マスクはコアから取得し、実際の形状で手の位置を表現します。

衣服と既存の `behind-hands` 規則はこの領域を避け、`front-of-hands` アクセサリーは引き続き覆うことができます。空の領域は、そのポーズに可視の手がないことを意味します。画布外のマスクや宣言済みのポーズ規則の欠落は失敗します。提供者を省略した経路は従来の動作を維持します。この機能はコアの手の遮蔽を担当し、完全な腕のアニメーションと正式素材の導入はそれぞれ既存の手順に従います。候補検証では隔離されたコアマスクを使用し、正式導入には引き続き美術承認と完全な検証が必要です。
