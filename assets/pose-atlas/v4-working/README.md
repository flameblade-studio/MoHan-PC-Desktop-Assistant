# PoseAtlas v4 工作證據／工作证据／Working Evidence／作業証拠

## 繁體中文

本目錄保存可重現的本機工作版本，正式 Release 仍須完成下列門檻。

PNG 檔是已正規化的原生 RGBA 素材。身體 sidecar 使用 alpha 輪廓註冊；手部 sidecar 只包含專案 ONNX 手部模型在固定增強流程後產生的觀測值。固定增強內容記錄於 `BUILD-METADATA.json`。自然遮擋以明確宣告表示，關鍵點座標僅採用真實觀測。

來源授權與再散布權仍待擁有人確認，並完成視覺審查後才能解除限制。

## 简体中文

本目录保存可复现的本地工作版本，正式 Release 仍须完成下列门槛。

PNG 文件是已经标准化的原生 RGBA 素材。身体 sidecar 使用 alpha 轮廓注册；手部 sidecar 只包含项目 ONNX 手部模型在固定增强流程后生成的观测值。固定增强内容记录在 `BUILD-METADATA.json` 中。自然遮挡通过明确声明表示，关键点坐标仅采用真实观测。

来源许可与再分发权仍待所有者确认，并完成视觉审查后才能解除限制。

## English

This directory holds a reproducible local working build; formal Release requires the gates below.

The PNG files are normalized native RGBA assets. Body sidecars use alpha-silhouette registration; hand sidecars contain only observations produced by the project ONNX hand model after the fixed augmentations recorded in `BUILD-METADATA.json`. Natural occlusion uses explicit declarations; landmark coordinates come exclusively from real observations.

Source authorization and redistribution rights remain blocked until the owner confirms the rights and completes visual review.

## 日本語

このディレクトリは再現可能なローカル作業ビルドを保存します。正式 Release には以下のゲートの完了が必要です。

PNG ファイルは正規化した native RGBA 素材です。身体 sidecar は alpha シルエット登録を使用し、手部 sidecar には `BUILD-METADATA.json` に記録した固定拡張をプロジェクトの ONNX 手部モデルへ適用して得た観測値だけを含めます。自然な遮蔽は明示的な宣言で表し、landmark 座標は実際の観測のみを使用します。

出典の許諾と再配布権は、所有者による権利確認と視覚レビューが完了するまで保留します。
