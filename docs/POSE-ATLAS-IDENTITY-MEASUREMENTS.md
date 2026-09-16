# 姿態圖集身分量測／姿态图集身份测量／PoseAtlas identity measurements／PoseAtlas 本人性計測

## 繁體中文

`tools/build_pose_atlas_identity_measurements.py` 讀取正式姿態圖集的 `BUILD-METADATA.json`、24 張 PNG 與同目錄的 24 份 `*.landmarks.json`。工具從 PNG 的 `IHDR` 核對實際畫布；對每個宣告 478 點的視角，再於 `project_root` 內開啟 `artifact.path`，核對 `artifact.sha256`、同一 PNG、實際點數及每筆 `x`、`y`、`z` 的有限數值。來源不一致時以結束碼 `2` 停止且不寫報告。

以 `target_subject_height / canvas_height` 取得 24 個正規化人物高度後，工具直接呼叫 `domain.character_identity_audit.audit_character_identity` 的既有尺度規則。`measurements.json` 保留完整視角來源、17 個可用的原生 478 點 artifact 雜湊與模型資訊、6 個後方四分之三視角缺口、1 個正後方無臉結果，以及實際尺度錯誤。

這份工具不推導 18 欄臉部幾何簽章，也不把原生臉部點數視為簽章。23 個非正後方簽章尚未量測或尺度稽核失敗時，狀態維持阻擋並回傳結束碼 `1`；它不表示外觀驗收、24 視角／600 層完成或可發布。

```powershell
python -m tools.build_pose_atlas_identity_measurements --atlas-root assets/pose-atlas/v5-base --project-root . --output tmp/body-identity-measurements-20260910
```

## 简体中文

`tools/build_pose_atlas_identity_measurements.py` 读取正式姿态图集的 `BUILD-METADATA.json`、24 张 PNG 和同目录的 24 份 `*.landmarks.json`。工具从 PNG 的 `IHDR` 核对实际画布；对每个声明 478 点的视角，再在 `project_root` 内打开 `artifact.path`，核对 `artifact.sha256`、同一 PNG、实际点数及每条 `x`、`y`、`z` 的有限数值。来源不一致时以退出码 `2` 停止且不写报告。

工具以 `target_subject_height / canvas_height` 得到 24 个归一化人物高度，再直接调用 `domain.character_identity_audit.audit_character_identity` 的现有尺度规则。`measurements.json` 保留完整视角来源、17 个可用的原生 478 点 artifact 哈希与模型信息、6 个后方四分之三视角缺口、1 个正后方无脸结果，以及实际尺度错误。

此工具不推导 18 栏脸部几何签名，也不把原生脸部点数视为签名。23 个非正后方签名尚未测量或尺度审计失败时，状态保持阻挡并返回退出码 `1`；它不表示外观验收、24 视角／600 层完成或可以发布。

```powershell
python -m tools.build_pose_atlas_identity_measurements --atlas-root assets/pose-atlas/v5-base --project-root . --output tmp/body-identity-measurements-20260910
```

## English

`tools/build_pose_atlas_identity_measurements.py` reads the formal atlas `BUILD-METADATA.json`, 24 PNG files, and 24 co-located `*.landmarks.json` files. It reads each PNG `IHDR` to verify the actual canvas. For every view claiming 478 points, it opens `artifact.path` within `project_root` and verifies `artifact.sha256`, the same PNG, the actual point count, and finite `x`, `y`, and `z` values. A source mismatch stops with exit code `2` and writes no report.

The tool calculates 24 normalized subject heights as `target_subject_height / canvas_height`, then calls the existing scale rules in `domain.character_identity_audit.audit_character_identity`. `measurements.json` retains every view source, the artifact hashes and model information for 17 available native 478-point results, six missing rear-three-quarter results, one rear result without a face, and the actual scale errors.

The tool does not derive the 18-field face geometry signature or treat native face points as a signature. While the 23 non-rear signatures remain unmeasured or the scale audit fails, the status stays blocked and the tool returns exit code `1`. This report does not establish appearance acceptance, 24-view/600-layer completion, or release readiness.

```powershell
python -m tools.build_pose_atlas_identity_measurements --atlas-root assets/pose-atlas/v5-base --project-root . --output tmp/body-identity-measurements-20260910
```

## 日本語

`tools/build_pose_atlas_identity_measurements.py` は正式なアトラスの `BUILD-METADATA.json`、24 枚の PNG、同じディレクトリにある 24 個の `*.landmarks.json` を読み取ります。PNG の `IHDR` から実キャンバスを照合します。478 点を宣言する各視点では、`project_root` 内の `artifact.path` を開き、`artifact.sha256`、同一 PNG、実際の点数、各 `x`、`y`、`z` の有限値を検証します。原画契約が一致しない場合はレポートを書かず終了コード `2` で停止します。

`target_subject_height / canvas_height` で 24 個の正規化人物高を求め、`domain.character_identity_audit.audit_character_identity` の既存尺度規則を直接呼び出します。`measurements.json` には全視点の原画、利用可能な 17 件のネイティブ 478 点 artifact のハッシュとモデル情報、欠落した後方四分の三視点 6 件、顔のない真後ろ 1 件、実際の尺度エラーを記録します。

このツールは 18 項目の顔形状シグネチャを導出せず、ネイティブ顔点をシグネチャとは扱いません。真後ろ以外の 23 シグネチャが未計測、または尺度監査が失敗している間は阻止状態を維持し、終了コード `1` を返します。このレポートは外観受入、24 視点／600 レイヤー完了、公開可能性を示しません。

```powershell
python -m tools.build_pose_atlas_identity_measurements --atlas-root assets/pose-atlas/v5-base --project-root . --output tmp/body-identity-measurements-20260910
```
