# 全身眼瞼素材／全身眼睑素材／Full-body eyelid assets／全身のまぶた素材

## 繁體中文

既有 24 視角、每個視角 25 層維持不變。各視角可另外提供 `<view>_blink_half.png` 與 `<view>_blink_closed.png`，兩張必須成對存在且均為 1024×1536 PNG。缺少其中一張或尺寸錯誤時拒絕載入；完全未提供時沿用既有眨眼。

素材必須是對齊該素體的透明眼部補丁，不能夾帶其他部位。半閉眼與閉眼使用既有 `EyeState`，在還原中性臉部後繪製；睜眼時恢復中性素材。使用補丁時避開睜眼眼妝，腮紅、唇妝與其他外觀層仍照常套用。

這是載入能力，不代表新素材已正式接入。正式採用前仍須確認來源、膚色、對位、透明邊緣、可調妝容與實際動畫；減少色素的試組不等同完整素顏。

## 简体中文

现有 24 视角、每个视角 25 层保持不变。各视角可另行提供 `<view>_blink_half.png` 与 `<view>_blink_closed.png`，两张必须成对存在且均为 1024×1536 PNG。缺少其中一张或尺寸错误时拒绝加载；完全未提供时沿用现有眨眼。

素材必须是对齐该素体的透明眼部补丁，不能夹带其他部位。半闭眼与闭眼使用现有 `EyeState`，在恢复中性脸部后绘制；睁眼时恢复中性素材。使用补丁时避开睁眼眼妆，腮红、唇妆与其他外观层仍正常应用。

这是加载能力，不代表新素材已正式接入。正式采用前仍须确认来源、肤色、对齐、透明边缘、可调妆容与实际动画；减少色素的试组不等同完整素颜。

## English

The existing 24 views and 25 layers per view remain unchanged. Each view may additionally provide `<view>_blink_half.png` and `<view>_blink_closed.png`. Both must exist as a pair of 1024×1536 PNGs. A missing partner or incorrect dimensions rejects loading; absence of both preserves legacy blinking.

Assets must be transparent eye-only patches registered to that body, without other body parts. Half and closed states use the existing `EyeState` and paint after neutral-face restoration; reopening restores neutral assets. Authored patches suppress open-eye makeup while blush, lip makeup and other appearance layers remain active.

This loading capability does not establish formal adoption of new artwork. Source, complexion, registration, transparent edges, adjustable makeup and actual animation still require verification before adoption. Reduced-pigment studies are not complete bare-skin assets.

## 日本語

既存の 24 視点、各視点 25 層は変更しません。各視点には追加で `<view>_blink_half.png` と `<view>_blink_closed.png` を指定できます。両方が 1024×1536 PNG の対として存在する必要があります。片方の欠落や寸法の誤りは読み込みを拒否し、両方とも未指定の場合は既存のまばたきを維持します。

素材は素体に位置合わせした透明な目の部分のパッチとし、他の部位を含めてはいけません。半閉眼と閉眼は既存の `EyeState` を使い、中立の顔を復元した後に描画します。開眼時は中立素材に戻ります。パッチ使用時は開眼用アイメイクを抑制し、チーク、リップ、その他の外観レイヤーは維持します。

この読み込み機能は新素材の正式採用を意味しません。採用前には出所、肌色、位置合わせ、透明境界、調整可能なメイク、実際のアニメーションの確認が必要です。色素を減らした試作は完全な素顔素材ではありません。
