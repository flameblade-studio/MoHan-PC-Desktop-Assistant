# V5 二代素體目前狀態／V5 二代素体现况／V5 second-generation body status／V5 第二世代素体の現況

## 2026-09-23 Session 36 外觀退件／外观退件／Visual rejection／外観の却下

最新／最新／Latest／最新：主人採用的近手 04 已單獨原子安裝，正式新行程重載 10/10 幀與 staging 精確相同；本輪正式寫入 1 檔，衣裝 pack 未變。衣料 04 因修錯位置未採用，紅框接縫來源候選 05 等候採用，未抽取／安裝。近手已安装并通过 10 帧正式重载；衣料 05 待采用。Hand 04 is installed and all 10 formal frames match staging; cloth 05 awaits adoption and is not installed. 手 04 は導入済みで正式描画 10 枚が staging と一致、衣料 05 は採用待ちで未導入。手部證據見 `scratchpad/mohan-v5-minus060-skirt-167/root-hand-install-36/REPORT.md`；衣料比較見 `scratchpad/mohan-v5-minus060-skirt-167/root-repair-36/cuff-candidate-05/review.html`。下列保留先前記錄。

繁體中文：主人退回 Session 35 已安裝近手的蹼狀輪廓及遠手下方 S 形藍邊。新候選 04 已在 W167 `root-repair-36/review.html` 展示，等候主人採用；原生手 RGB 保留，局部藍衣缘對齊袖口並延伸至裙底。正式 renderer 在隔離環境實際渲染 1 幀，兩個修正區域外像素差 0；不是完整回歸或桌面 UI 驗收。正式素材本輪寫入 0，正式檔仍是舊退件版本。詳見 `candidate-04/evidence.json`。

简体中文：旧安装版本已被退回；候选 04 已实际隔离渲染并展示，等待外观采用，尚未安装。

English: The installed hand and blue edge were rejected. Candidate 04 has one actual isolated runtime frame and is awaiting owner visual adoption; no formal asset writes this session.

日本語：旧導入版は却下済み。候補 04 を隔離環境で 1 枚実描画して提示し、外観の採用待ちです。正式素材は未更新です。

## 2026-09-23 Session 35 裙襬與近手／裙摆与近手／Skirt and near hand／裾と手の修正

繁體中文：−60° 已採用裙身局部抽取與原生近手硬邊修復已正式安裝，共 2 檔且有備份／receipt。衣料 alpha 保留，近手 215 個 alpha 邊緣像素修整、內部原生 RGB 保留。合併 staging 40 幀通過，正式新行程重載 40/40 相同；Flash pytest 13 passed、全庫 Ruff exit 0。最新原尺寸／normalised 與手部比較在 `scratchpad/mohan-v5-minus060-skirt-167/root-install-35/review.html`，完整 SHA 與命令見同目錄 `REPORT.md`。新展示尺寸採用／接入、缺證據的幾何量測及桌面 UI 仍開放，第 3 項領口沿用既有結清。下方保留歷史。

简体中文：−60° 裙摆局部与原生近手遮罩修复已安装，2 文件可回滚，40 帧正式重载与合并 staging 完全相同。新展示尺寸、缺失的几何证据及桌面 UI 仍未结案。

English: The adopted −60° skirt patch and native near-hand matte correction are installed as two reversible targets. All 40 fresh formal-renderer frames match combined staging exactly. Display-scale adoption/integration, unsupported geometry evidence and desktop UI remain open; subsequent sections retain history.

日本語：採用済み −60° の裾と原生の手のマスクを 2 ファイルに正式導入し、復元用コピーを保存。正式再描画 40 枚は統合 staging と完全一致。表示縮尺の採用・導入、形状証拠不足、デスクトップ UI は未完了。以下は履歴です。

## 2026-09-22 Session 34 裙身修正候選／裙身修正候选／Skirt repair candidate／スカート修正候補

繁體中文：使用者指出 −60° 白裙異常彎曲；已確認正式衣層在尺寸規格化前就有此缺陷。W167 `scratchpad/mohan-v5-minus060-skirt-167/review.html` 提供修正來源 01，僅白裙及相鄰藍邊待採用；生成圖外圍光暈不採用。尚未抽取、正式接入或完成新候選 runtime 驗證，正式素材 0 寫入。第 2 項保持開放，第 3 項领口維持結清。

简体中文：−60° 裙身修正来源 01 待采用，仅处理裙身局部，排除外围光晕；未提取或安装。

English: The −60° skirt kink exists before scale normalization. Repair source 01 awaits owner approval of the drape only; exclude the raw halo. No extraction, installation or new runtime validation.

日本語：−60° の屈曲は縮尺補正前から存在。修正素材 01 のスカート線を採用待ちで、光暈は除外。抽出・導入・新規 runtime 検証は未実施です。

## 2026-09-22 Session 33 可見證據與尺寸比較／可见证据与尺寸比较／Visible evidence and display scale／可視証拠と縮尺

繁體中文：第 2 項已新增可見證據診斷契約及 24 角素體／衣装的原始與等比規格化對照（96 張全圖、±090 共 74 種代表狀態檢查）。最新頁面 `scratchpad/mohan-v5-visible-geometry-scale-166/root-integration/preview-04/review.html`；新尺寸尚待主人採用，正式素材未改。診斷有 27 個圖層支持的模型投影值，4 筆比例警示與缺證據項保留，完整幾何 audit=false，不能當作生物幾何認證。相關回歸 48 passed；主線最後修改後 22 passed，全庫 Ruff exit 0。最終實測與 SHA 見 W166 `root-integration/receipt.json`，完整界線見 W166 `REPORT.md`。第 3 項領口已結清；桌面 UI 未驗收。下方為歷史。

简体中文：可见证据诊断与 24 角等比尺寸对照已交付，新尺寸仍待采用，正式素材未改。4 个模型比例警示和缺证据项保留，完整几何未通过。领口事项已结清；桌面 UI 未验证。

English: Evidence-aware diagnostics and the 24-view scale comparison are delivered, pending owner approval and formal display integration. Source artwork is unchanged. Four model-ratio flags and missing evidence remain; full biometric geometry is not certified. Collar findings are closed; desktop UI is unverified.

日本語：可視証拠診断と 24 視角の縮尺比較を作成し、採用と正式導入は保留中です。原素材は未変更。比率警告 4 件と証拠不足を保持し、完全な形状監査合格ではありません。襟元は完了、デスクトップ UI は未検証です。

## 2026-09-22 Session 32 量測與領口／测量与领口／Measurements and collars／計測と襟元

繁體中文：第 3 項領口 48/48 差異已逐項確認為已採用衣料的正常覆蓋，身分層與衣料外差異為 0，保留舊 raw findings。第 2 項完成 24 張正式圖的高度實測、17 角共 170 筆模型比例及 3 個 JSON 的 SHA 修復正式安裝；654 PNG 不變。完整 18 欄幾何與尺寸稽核仍未通過：缺深度尺度、被遮蔽五官與耳／髮際等來源，且高度有真實超標。先前 22 簽章／24 身高缺口敘述已更正：非正背面應為 23，宣告高度與本次實測分列。正式工具來源錯誤已修好，完整 audit exit 1 如實保留。相關正式測試 10 passed、Flash v2 27 passed／1 skipped、全庫 Ruff exit 0。詳見 `scratchpad/mohan-v5-measure-collar-165/REPORT.md`。下方均為歷史；桌面 UI 仍未驗收，二代素體未全體結案。

简体中文：48 项领口差异已结清。24 图高度与 170 个模型比例已测量，3 个 SHA 元数据修复已安装，654 PNG 不变。完整 18 栏几何和尺寸审计仍因缺证据及尺寸偏差未通过，原始失败保留。桌面 UI 未验证；下文为历史。

English: All 48 collar findings are closed as adopted garment coverage. Heights of 24 images and 170 model ratios were measured; three hash-only metadata repairs are installed, with 654 PNGs unchanged. Full 18-field geometry and scale auditing still fails on missing evidence and actual scale differences. Desktop UI remains unverified; sections below retain history.

日本語：襟元 48 件は採用済み衣装による正常な被覆と確認しました。24 枚の高さとモデル比率 170 件を計測し、SHA メタデータ 3 件を修復、654 PNG は未変更です。18 項目の完全な形状・縮尺監査は証拠不足と縮尺差で未合格。デスクトップ UI は未検証、以下は履歴です。

## 2026-09-22 Session 31 最終接入／最终接入／Final integration／最終導入

繁體中文：已採用的 13 角灰藍衣裝、−120 背部修正、新 −90 側臉與 +90 完整鏡像 07、下唇接縫及髮緣 alpha 修補均已正式安裝。四份原子收據共 147 次檔案替換、145 個不同目標。正式 renderer 重載 100 張與已審 staging 完全相符，24/24 角有可見衣裝；56 列妝容／髮飾有效範圍檢查無範圍外變動。全專案 Ruff exit 0。三工作包的授權素材接入完成；完整證據見 `scratchpad/mohan-v5-hanfu-unified-all-164/root-integration-31/REPORT.md`。歷史 1,200 次檢查的 48 個領口／頸部原始差異保留，沒有宣稱全矩陣零失敗；執行中的桌面 UI 及缺少的幾何量測未驗收。來源仍分為 22 外部精確原圖與 2 採用側臉派生鏈。沒有軟體發布。以下均為歷史階段紀錄。

简体中文：13 角服装、−120 背部、新侧脸与完整镜像 07、下唇接缝和发缘 alpha 修复已正式安装。147 次替换涉及 145 个不同目标；100 张正式重载与审核版本一致，24 角均显示服装。历史 48 个领口差异保留；未验证运行中的桌面 UI 或补齐几何测量，没有发布软件。下文保留历史。

English: Adopted garments, the −120 back repair, approved profiles including whole-mirror 07, lip seam and hair-alpha fixes are installed. Four receipts cover 147 replacements across 145 unique targets. All 100 fresh formal-renderer frames match accepted staging and all 24 views are dressed. Historical 48 collar findings remain recorded; running desktop UI and missing geometry measurements are not claimed verified. No software release. Sections below are historical.

日本語：採用済み衣装、−120 背面、新側面と全体鏡像 07、下唇の継ぎ目と髪端 alpha 修正を正式導入。4 受領記録で 145 個の対象に計 147 回書換え、正式再描画 100 枚が確認済み staging と一致し、24 角度すべてで衣装を表示。過去の襟元 48 件は保持。起動中 UI と未取得の形状計測は未検証で、ソフトウェアは未公開。以下は履歴です。

## 繁體中文

2026-09-22 最新：joint-stage-17 組裝 134 目標完成，但 renderer 前測 12 次有 8 次 ±090 選衣回退，退出碼 1；完整矩陣未啟動，新側臉／鏡像 07／新衣裝尚未正式安裝。使用者轉作原生 Flash 規範與 Router 設定；Router、角色及技能已安裝，靜態檢查通過，須重開 Codex 後才可驗證實際派工。舊 Codex 子代理已停止。二代素體工作保留待續，沒有結案。

### 2026-09-22 10:00 +08:00 身分與頸部修正追加

繁體中文：最新使用者已採用新側臉、五張眼口來源，以及頭頸／身體／手完整鏡像的 +090 候選 07。04、05、06 的不自然頸肩接合均排除，未正式安裝。新左右側原生分層、24 表情、可拆衣装、妝容與髮飾進入聯合隔離驗證。其餘 12 角衣裝已有 600 次實際檢查通過，仍待整組採用與安裝；七半身正式回歸 336/336 相同。本 session 早先安裝的 10 個語意分層 PNG 及 1 個銀飾包是既有完成項，不代表這次新側臉已安裝。詳見 `notes/2026-09-22-codex-v5-angle-repair-30.md`；下方各階段保留歷史。二代素體尚未結案。

2026-09-22，狀態以正式檔案、安裝收據及實際 renderer 為準。以下各項分開計算，不能把可選項目數或成功輸出影格當作完整外觀驗收。

工作階段 29：−090、−165 以原生 V5 頭部及可拆衣層在隔離正式 renderer 各渲染 52 張、機械失敗 0；−090 的手部借用已採用 +090 V5 原生手鏡像，並非該角來源精確手。頸袖、腰帶及原生髮緣仍有外觀缺陷，兩角未採用或安裝。另 11 角已隔離抽取，但目視 11/11 退件。−105／−120 新來源的原生手縮放失去柔邊並補回深灰殘片；+090 銀飾隔離裁去 20 個相撞像素後可切換，尚未正式安裝。擁有者再度貼出 −090 整張生成候選並指出「這張特別不像」，原圖 SHA 與退件紀錄見 `scratchpad/mohan-v5-hanfu-unified-all-164/owner-rejection-yaw-090-candidate-01.json`；正式包未使用該圖。全專案 Ruff 退出碼 0。本階段正式寫入 0，工作包一、二仍開放。詳見 `notes/2026-09-22-codex-v5-all-angle-extraction-29.md`。

工作階段 28：其餘 13 角皆有隔離檢視稿；8 張衣裝來源的離線去背技術稽核 8/8 通過，其中新增 −165 姿態試作仍因頸肩斷口退回。11 張原生頭部合成預覽已製作，另有 −090、−165 草稿。手部補接需縮放／位移，頸袖與 ±165 角度仍有外觀偏差；13 角沒有新的擁有者採用、可拆正式抽取、正式安裝或 runtime 驗收。髮飾開關無差異的原因已定位為 +090 銀飾 20 像素與 −090 舊衣領 85 像素的保護區碰撞。完整證據與限制見 `notes/2026-09-22-codex-v5-all-angle-candidate-audit-28.md`、`scratchpad/mohan-v5-hanfu-unified-all-164/review-28.html`。

最新工作階段 27：正式 24 角度各渲染 1 張 neutral/rest，6 個角度（−090、−105、−120、−135、−150、−165）選衣無作用；9 個正面相鄰角度可沿用灰藍款、+090 與 −180 已採用接入，另 13 個角度仍須統一款式。使用者已退回不像 V5 的 −090 生成候選；修正版 04 以原生 V5 頭部與已採用衣料製作，仍有接縫且未採用。正式舊散髮選擇現改為全身原生髮髻，不再雙重疊髮；選單四語標示舊代號。原生 ±090 分層僅有隔離候選，42 張裸身零差但髮飾開／關無像素變化，故未安裝。詳見 `notes/2026-09-22-codex-v5-fullbody-identity-audit-27.md` 與 `scratchpad/mohan-v5-hanfu-unified-all-164/review.html`。下表保留前一工作階段的分項基線，不能覆蓋此最新診斷。

最新決定：使用者選定正面灰藍薄紗漢服，並以「可以」採用 +090° 側面與 −180° 背面兩張衣裝設計。兩張已離線去背、抽取可拆衣層，完成隔離環境 100 次實際渲染、0 failures，以及 96 張原生頭部／手部核對；8 個素材目標已原子安裝，收據見 `scratchpad/mohan-v5-hanfu-unified-front-163/formal-installation-26/receipt.json`。僅衣料局部對齊，原生 V5 臉、髮髻、手保持各自來源。正式重載結果及限制見 `notes/2026-09-22-codex-v5-hanfu-pair-adoption-26.md`。

本次只涵蓋兩個角度與隔離設定中的原生髮型；其餘 22 個角度尚未完成這輪統一驗收，不能沿用下表舊矩陣宣告全部通過。新散髮不在結案範圍。原生髮際灰邊、+090° 髮層混入部分身體像素、髮型／髮飾獨立切換與選單語意仍待處理；本次未改共用原生圖層或使用者衣櫃。

| 範圍 | 已完成證據 | 尚未完成 |
| --- | --- | --- |
| 七姿勢 V7 嘴型／眼態 | 84 個正式影格；86 個安裝目標 SHA 相符；84 張正式 runtime 核對 | 此範圍已完成，I／E／U 仍為既有來源別名 |
| 七姿勢藍白漢服 | 七姿勢已可拆接入；最後五姿勢 16 個安裝目標；336 張正式嘴型／眼態／妝容渲染，0 failures | 不等於髮型／髮飾全部切換通過 |
| 素顏＋三款妝容 | Classic／Light／Glamorous 各 31 剪影；279 張妝容眼態及 31 張素顏合成核對 | 此證據未包含完整全身衣裝、髮型、髮飾聯合驗收 |
| 全身 24 原圖血緣 | 22 個外部原圖不透明 RGB 精確吻合，2 個 ±90° 採用及安裝收據，0 個 Git-only 缺口 | 不等於全部身分量測或發行審計完成 |
| 工作包一：髮型／髮飾 | 七姿勢 35 張切換診斷，7/7 還原相同。已修復 front-eureka 遺漏的原生造型綁定；336 張正式重載與 staging 相同，其餘六姿勢逐像素未變；21 項測試通過 | 七姿勢以 native alias 保留原生髮髻；獨立切換與選單語意未完成。自創散髮候選未採用，新散髮不在結案範圍。此次未處理原生去背的髮際灰邊 |
| 工作包二：全身聯合驗收 | 1,488 張實際渲染完成，100 個衣裝驗收失敗；24/24 還原相同。已修復 1 個 blink source pin，72 張修正前後逐像素相同；48 項測試通過 | 失敗全部出現在 ±90°：兩側衣裝、舊散髮及 +90° 髮飾共五圖層侵入臉保護區而退回素體；+075°、+135°、+150° 等另有衣裝／素體接合偏差。完整矩陣未通過 |
| 工作包三：狀態整理 | 本文件提供現況入口；TASKS 的現況與歷史紀錄分離，過時文件導向本頁 | 工作包一、二的外觀缺陷保持開放；文件整理不代替外觀驗收 |

正式依據：`assets/expressions/complete-expressions/manifest.json`、`assets/expressions/reviewed-garments/manifest.json`、`assets/official-packs/mohan.makeup.builtin.mohan-outfit`、`assets/pose-atlas/v5-base/SOURCE-PROVENANCE.json`。

證據：`scratchpad/mohan-v2-v5-complete-seven-v7-formal-159/`、`scratchpad/mohan-v5-hanfu-five-candidates-161/formal-runtime-validation-08/validation.json`、`scratchpad/mohan-v2-final-runtime-matrix-160/isolated-runtime-validation-v4/validation.json`、`scratchpad/mohan-v5-appearance-closeout-162/`。本輪完整命令、退出碼、限制與 SHA 見 `notes/2026-09-21-codex-three-workpackages-24.md`。

2026-09-12 及更早的來源／接合紀錄仍保留供追溯，不能替代上述 V5 現況。工作樹未提交；未授權軟體發布、合併或標籤。

## 简体中文

2026-09-22 最新：joint-stage-17 已组装 134 个目标，但 renderer 的 12 次前测有 8 次 ±090 选衣回退，退出码 1；完整矩阵未启动，新侧脸／镜像 07／新衣装尚未正式安装。用户转作原生 Flash 规范与 Router 设置；Router、角色及技能已安装，静态检查通过，须重开 Codex 后验证实际委派。旧 Codex 子代理已停止，二代素体保留待续，尚未结案。

### 2026-09-22 10:00 +08:00 身份与颈部修正追加

简体中文：最新用户已采用新侧脸、五张眼口来源，以及头颈／身体／手完整镜像的 +090 候选 07。04、05、06 的不自然颈肩接合均排除，未正式安装。新左右侧原生分层、24 表情、可拆衣装、妆容和头饰进入联合隔离验证。其余 12 角衣装已有 600 次实际检查通过，仍待整组采用和安装；七半身正式回归 336/336 相同。本 session 早先安装的 10 个语义分层 PNG 和 1 个银饰包是已有完成项，不代表此次新侧脸已安装。详见 `notes/2026-09-22-codex-v5-angle-repair-30.md`；下方各阶段保留历史。二代素体尚未结案。

2026-09-22，状态以正式文件、安装收据及实际 renderer 为准。以下各项分开计算，不能把可选项目数或成功输出帧当作完整外观验收。

工作阶段 29：−090 和 −165 使用原生 V5 头部与可拆衣层，在隔离的正式 renderer 中各渲染 52 帧，机械失败 0。−090 的手借用了已采用 +090 的原生 V5 手镜像，并非该角度的精确来源。颈袖、腰带和原生发缘仍有外观缺陷，两角均未采用或安装。其余 11 角已有隔离提取，但目视 11/11 退回。−105／−120 的原生手缩放丢失柔边，并补回深灰残片；+090 银饰隔离裁去 20 个冲突像素后可以切换，尚未正式安装。所有者再次指出 −090 整张生成候选“这张特别不像”；哈希和退回记录见 `scratchpad/mohan-v5-hanfu-unified-all-164/owner-rejection-yaw-090-candidate-01.json`，正式包未使用该图。全项目 Ruff 退出码 0；本阶段正式写入 0，工作包一、二仍开放。详见 `notes/2026-09-22-codex-v5-all-angle-extraction-29.md`。

工作阶段 28：其余 13 个角度均有隔离预览；8 张衣装来源的离线去背景技术检查 8/8 通过，其中新增 −165 姿态试作仍因颈肩断口退回。11 张原生头部合成预览已制作，另有 −090、−165 草稿。手部补接需要缩放／位移，颈部、袖口与 ±165 方向仍有外观偏差；13 个角度没有新的所有者采用、正式可拆提取、正式安装或 runtime 验收。发饰开关无差异的原因已定位为 +090 银饰 20 像素与 −090 旧衣领 85 像素的保护区冲突。证据见 `notes/2026-09-22-codex-v5-all-angle-candidate-audit-28.md`、`scratchpad/mohan-v5-hanfu-unified-all-164/review-28.html`。

最新工作阶段 27：正式 24 个角度各渲染 1 帧 neutral/rest，6 个角度（−090、−105、−120、−135、−150、−165）选衣后没有变化；9 个正面相邻角度可沿用灰蓝款，+090 与 −180 已采用并接入，另 13 个角度仍需统一款式。用户已退回不像 V5 的 −090 生成候选；修正版 04 使用原生 V5 头部和已采用衣料，仍有接缝且未获采用。正式旧散发选择现改为全身原生发髻，不再双重叠发；菜单以四语标示旧代号。原生 ±090 分层只有隔离候选，42 帧素体零差，但发饰开／关没有像素变化，因此未安装。详见 `notes/2026-09-22-codex-v5-fullbody-identity-audit-27.md` 与 `scratchpad/mohan-v5-hanfu-unified-all-164/review.html`。下表保留前一工作阶段的分项基线，不能覆盖此最新诊断。

最新决定：用户选定正面灰蓝薄纱汉服，并以“可以”采用 +090° 侧面与 −180° 背面两张衣装设计。两张已离线去背、提取可拆衣层，完成隔离环境 100 次实际渲染、0 failures，以及 96 张原生头部／手部核对；8 个素材目标已原子安装，收据见 `scratchpad/mohan-v5-hanfu-unified-front-163/formal-installation-26/receipt.json`。仅衣料局部对齐，原生 V5 脸、发髻、手保持各自来源。正式重载结果及限制见 `notes/2026-09-22-codex-v5-hanfu-pair-adoption-26.md`。

本次只涵盖两个角度与隔离设置中的原生发型；其余 22 个角度尚未完成这轮统一验收，不能沿用下表旧矩阵宣告全部通过。新散发不在结案范围。原生发际灰边、+090° 发层混入部分身体像素、发型／发饰独立切换与菜单语义仍待处理；本次未改共用原生图层或用户衣柜。

| 范围 | 已完成证据 | 尚未完成 |
| --- | --- | --- |
| 七姿势 V7 嘴型／眼态 | 84 个正式帧；86 个安装目标 SHA 相符；84 张正式 runtime 核对 | 此范围已完成，I／E／U 仍为既有来源别名 |
| 七姿势蓝白汉服 | 七姿势已可拆接入；最后五姿势 16 个安装目标；336 张正式嘴型／眼态／妆容渲染，0 failures | 不等于发型／发饰全部切换通过 |
| 素颜＋三款妆容 | Classic／Light／Glamorous 各 31 剪影；279 张妆容眼态及 31 张素颜合成核对 | 此证据未包含完整全身衣装、发型、发饰联合验收 |
| 全身 24 原图血缘 | 22 个外部原图不透明 RGB 精确吻合，2 个 ±90° 采用及安装收据，0 个 Git-only 缺口 | 不等于全部身份测量或发行审计完成 |
| 工作包一：发型／发饰 | 七姿势 35 张切换诊断，7/7 还原相同。已修复 front-eureka 遗漏的原生造型绑定；336 张正式重载与 staging 相同，其余六姿势逐像素未变；21 项测试通过 | 七姿势以 native alias 保留原生发髻；独立切换与菜单语义未完成。自创散发候选未采用，新散发不在结案范围。此次未处理原生去背的发际灰边 |
| 工作包二：全身联合验收 | 1,488 张实际渲染完成，100 个衣装验收失败；24/24 还原相同。已修复 1 个 blink source pin，72 张修正前后逐像素相同；48 项测试通过 | 失败全部出现在 ±90°：两侧衣装、旧散发及 +90° 发饰共五图层侵入脸保护区而退回素体；+075°、+135°、+150° 等另有衣装／素体接合偏差。完整矩阵未通过 |
| 工作包三：状态整理 | 本文件提供现况入口；TASKS 的现况与历史记录分离，过时文件导向本页 | 工作包一、二的外观缺陷保持开放；文件整理不代替外观验收 |

正式依据：`assets/expressions/complete-expressions/manifest.json`、`assets/expressions/reviewed-garments/manifest.json`、`assets/official-packs/mohan.makeup.builtin.mohan-outfit`、`assets/pose-atlas/v5-base/SOURCE-PROVENANCE.json`。

证据：`scratchpad/mohan-v2-v5-complete-seven-v7-formal-159/`、`scratchpad/mohan-v5-hanfu-five-candidates-161/formal-runtime-validation-08/validation.json`、`scratchpad/mohan-v2-final-runtime-matrix-160/isolated-runtime-validation-v4/validation.json`、`scratchpad/mohan-v5-appearance-closeout-162/`。本轮完整命令、退出码、限制与 SHA 见 `notes/2026-09-21-codex-three-workpackages-24.md`。

2026-09-12 及更早的来源／接合记录仍保留供追溯，不能替代上述 V5 现况。工作树未提交；未授权软件发布、合并或标签。

## English

Latest, 2026-09-22: joint-stage-17 assembled 134 targets, but 8 of 12 actual renderer preflight checks failed through ±090 outfit fallback (exit 1). The full matrix has not run; the new profiles, mirror 07 and garments are not installed. The owner redirected work to native Flash rules and Router setup. Router, role and skill are installed with passing static checks; reopen Codex before verifying an actual delegation. Legacy Codex children are stopped. The V5 body task remains open.

### 2026-09-22 10:00 +08:00 Identity and neck repair update

English: The owner has now adopted the new profile, five local expression sources, and +090 candidate 07 as a complete mirror of the head, neck, body and hands. Unnatural neck/shoulder joins 04, 05 and 06 are excluded and were not formally installed. The new native layers, 24 expressions, detachable garments, makeup and headwear are entering combined isolated validation. The other twelve garment views have passed 600 actual checks but still await whole-set adoption and installation. All 336 formal half-body regression frames match. Ten semantic partition PNGs and one headwear archive installed earlier in this session remain completed historical work; they do not mean the new profiles are installed. See `notes/2026-09-22-codex-v5-angle-repair-30.md`. Sections below retain historical states. The second-generation body task is not closed.

As of 2026-09-22, status is based on formal files, installation receipts, and actual renderers. The following scopes are accounted for separately; option counts or successfully generated frames do not establish complete appearance acceptance.

Session 29: the isolated formal renderer produced 52 frames each for −090 and −165 with detachable cloth and native V5 heads, with zero mechanical failures. The −090 hands were mirrored from the adopted +090 native V5 source rather than being source-exact for −090. Neck, cuff, sash, and native hair-edge defects remain; neither view was approved or installed. The other 11 views were isolated for extraction but failed visual review 11/11. New −105/−120 hand fitting lost native feathered alpha and reintroduced dark remnants; an isolated +090 silver-ornament clip makes switching visible after removing 20 colliding pixels, but is not installed. The owner again rejected the full-frame generated −090 candidate as unlike MoHan; its exact hash and rejection are in `scratchpad/mohan-v5-hanfu-unified-all-164/owner-rejection-yaw-090-candidate-01.json`, and the formal pack does not use it. Full-repository Ruff passed; formal writes in this session: zero. Work packages 1 and 2 remain open. See `notes/2026-09-22-codex-v5-all-angle-extraction-29.md`.

Session 28: isolated previews now cover the 13 remaining views. Offline matting passed technical checks for eight clothing sources, but the new −165 pose trial was rejected for a neck/shoulder gap. Eleven previews combine new cloth with the native V5 head, with separate −090 and −165 drafts. Hands still require fitting, and neck, cuff, and ±165 orientation defects remain visible. None of these 13 views has new owner appearance approval, formal detachable extraction, installation, or runtime acceptance. Headwear switching remains invisible because the +090 silver ornament intersects the protected region by 20 pixels and the old −090 collar by 85 pixels. Evidence and limitations: `notes/2026-09-22-codex-v5-all-angle-candidate-audit-28.md` and `scratchpad/mohan-v5-hanfu-unified-all-164/review-28.html`.

Session 27 update: one neutral/rest frame was rendered for each of the 24 formal angles. Outfit selection had no visible effect in six views (−090, −105, −120, −135, −150, −165). Nine central views retain the selected gray-blue style; +090 and −180 were previously adopted and installed; 13 other views still need a unified design. The owner rejected the generated −090 portrait as unlike V5. Review 04 composites the native V5 head with previously adopted cloth, but has seams and is neither approved nor installed. The legacy official loose-hair selection now resolves to the native full-body bun without a duplicate overlay, with clarified labels in four languages. The ±090 native repartition is isolated only: 42 bare frames are pixel-identical, but headwear on/off produces no visible change, so the candidate was not installed. See `notes/2026-09-22-codex-v5-fullbody-identity-audit-27.md` and `scratchpad/mohan-v5-hanfu-unified-all-164/review.html`. The table below retains the preceding session's itemized baseline and does not supersede this diagnosis.

Latest decision: the owner selected the front-facing gray-blue sheer Hanfu and approved the +090° side and −180° back clothing designs with “可以”. Both underwent offline matting and detachable extraction, followed by 100 actual runtime checks in an isolated staging environment with zero failures and native head/hand checks across 96 frames. Eight asset targets were installed atomically; see `scratchpad/mohan-v5-hanfu-unified-front-163/formal-installation-26/receipt.json`. Only fabric was fitted locally; native V5 face, bun and hand sources remain authoritative. Formal reload results and limitations are recorded in `notes/2026-09-22-codex-v5-hanfu-pair-adoption-26.md`.

This scope covers two angles with native hair in an isolated profile. The other 22 angles have not completed this unification review, and the historical matrix below is not a current full pass. New loose hair is out of scope. Native hairline gray fringes, body pixels misclassified into +090° hair layers, independent hair/headwear switching and selection semantics remain open. Shared native layers and the owner's wardrobe were not changed.

| Scope | Completed evidence | Still open |
| --- | --- | --- |
| Seven-pose V7 mouth/eye states | 84 formal frames; all 86 installation target hashes match; 84 formal runtime frames verified | This scope is complete; I/E/U remain existing source aliases |
| Seven-pose blue-white Hanfu | Seven detachable poses integrated; the last five had 16 installation targets; 336 formal mouth/eye/makeup renders, 0 failures | Does not establish complete hairstyle/headwear switching |
| Bare face + three makeup variants | Classic/Light/Glamorous each cover 31 silhouettes; 279 makeup/eye composites and 31 bare controls verified | This evidence does not include joint full-body outfit, hairstyle, and headwear acceptance |
| Provenance for 24 full-body views | 22 exact opaque-RGB external-source matches, two adopted ±90° profile installation receipts, no Git-only gaps | Does not establish completion of every identity measurement or release audit |
| Work package 1: hairstyle/headwear | 35 switching diagnostic frames across seven poses; 7/7 restores identical. Repaired the missing front-eureka native-style binding; 336 formal reloads match staging, the other six poses remain pixel-identical; 21 tests passed | Native aliases retain the original bun in all seven poses; independent switching and selection semantics remain incomplete. The invented loose-hair candidate was not adopted; a new hairstyle is out of scope. Native matting hairline gray fringes were not repaired |
| Work package 2: combined full-body appearance | 1,488 actual renders, 100 outfit failures; 24/24 restores identical. Repaired one blink-source pin with 72 pixel-identical before/after renders; 48 tests passed | All failures occur at ±90°: the two garment layers, two legacy hair layers, and +90° headwear intersect identity protection and cause bare-body fallback. Other registration defects are visible at +075°, +135°, +150°, and additional views. The complete matrix did not pass |
| Work package 3: status reconciliation | This page provides the current status; TASKS separates current work from historical records, and outdated documents link here | Appearance defects in packages 1 and 2 remain open; documentation is not appearance acceptance |

Formal authority: `assets/expressions/complete-expressions/manifest.json`, `assets/expressions/reviewed-garments/manifest.json`, `assets/official-packs/mohan.makeup.builtin.mohan-outfit`, `assets/pose-atlas/v5-base/SOURCE-PROVENANCE.json`.

Evidence: `scratchpad/mohan-v2-v5-complete-seven-v7-formal-159/`, `scratchpad/mohan-v5-hanfu-five-candidates-161/formal-runtime-validation-08/validation.json`, `scratchpad/mohan-v2-final-runtime-matrix-160/isolated-runtime-validation-v4/validation.json`, `scratchpad/mohan-v5-appearance-closeout-162/`. Commands, exit codes, limits, and hashes for this session are in `notes/2026-09-21-codex-three-workpackages-24.md`.

Source and alignment records from 2026-09-12 and earlier remain available for traceability; they do not supersede current V5 status. The worktree is uncommitted; software release, merge, and tagging are not authorized.

## 日本語

2026-09-22 最新：joint-stage-17 は 134 対象を組み立てましたが、実 renderer 前検査 12 件中 8 件で ±090 の衣装選択が素体へ戻り、終了コードは 1 でした。全行列検証は未実行で、新側面・鏡像 07・衣装は未導入です。所有者の指示でネイティブ Flash 規則と Router 設定へ移行しました。Router・役割・スキルは導入済み、静的検査に合格し、実際の委任検証には Codex の再起動が必要です。旧 Codex 子代理は停止済みで、V5 素体作業は未完了です。

### 2026-09-22 10:00 +08:00 顔と首の修正追記

日本語：新しい横顔・眼口素材 5 枚・頭頸部と身体と手を完全鏡像にした +090 候補 07 が採用されました。不自然な首肩接合 04・05・06 は除外し、正式配置していません。新素体レイヤー・24 表情・分離式衣装・メイク・飾りは合同の隔離検証に進んでいます。他の衣装 12 方向は実検査 600 件が成功しましたが、一括採用と配置は未完了です。半身 336 枚の正式回帰は全件一致しました。この session の先行作業で配置した意味レイヤー PNG 10 件と銀飾り pack 1 件は過去の完了項目であり、新横顔の配置完了を意味しません。詳しくは `notes/2026-09-22-codex-v5-angle-repair-30.md` を参照してください。以下は各段階の過去の記録であり、第二世代素体はまだ完了していません。

2026-09-22 時点の状態は、正式ファイル、配置記録、および実際の renderer に基づきます。以下の範囲は個別に扱い、選択肢の数や画像出力の成功を外観全体の受入れとはみなしません。

作業段階 29：−090 と −165 は原生 V5 の頭部と分離可能な衣装を用い、隔離した正式 renderer で各 52 枚を描画し、機械的失敗は 0 でした。−090 の手は採用済み +090 の原生 V5 の手を反転したもので、−090 原画との厳密一致ではありません。首・袖・帯・原生髪の縁に外観上の欠陥が残り、両方向とも未承認・未配置です。ほかの 11 方向は隔離抽出しましたが、目視 11/11 が不合格でした。新しい −105／−120 の手の位置合わせでは原生の柔らかい alpha が失われ、暗い残片が再混入しました。+090 の銀飾りは衝突する 20 画素を隔離で除くと切替可能ですが、正式配置はしていません。所有者は −090 の全体生成画像を再び「この画像は特に似ていない」と却下しました。正確な SHA と記録は `scratchpad/mohan-v5-hanfu-unified-all-164/owner-rejection-yaw-090-candidate-01.json` にあり、正式 pack はこの画像を使っていません。全 repository の Ruff は成功、今回の正式ファイル書込みは 0 です。作業 1・2 は引き続き未完了です。詳細は `notes/2026-09-22-codex-v5-all-angle-extraction-29.md` を参照してください。

作業段階 28：残り 13 方向の隔離プレビューを作成しました。衣装ソース 8 枚のオフライン背景除去は技術確認 8/8 ですが、新しい −165 姿勢試作は首と肩の欠損により却下しました。11 方向は原生 V5 の頭部と新しい布地を合成し、−090 と −165 は別の草稿です。手は縮小・移動による仮合わせで、首・袖口・±165 の向きに外観上の欠陥が残ります。13 方向の新規外観承認、正式な分離抽出、配置、runtime 受入れはまだありません。髪飾りの切替に差がない原因は、+090 の銀飾りが保護領域と 20 画素、旧 −090 の襟が 85 画素重なることです。証拠と制限は `notes/2026-09-22-codex-v5-all-angle-candidate-audit-28.md` と `scratchpad/mohan-v5-hanfu-unified-all-164/review-28.html` に記録しました。

作業段階 27 の更新：正式 24 方向を neutral/rest で各 1 枚描画し、6 方向（−090、−105、−120、−135、−150、−165）では衣装選択が画面に反映されませんでした。正面付近の 9 方向は選定済みの灰青色を維持し、+090 と −180 は既に採用・配置済みですが、ほかの 13 方向は衣装デザインの統一が必要です。V5 に似ていない −090 の生成人物画像は所有者が却下しました。修正版 04 は原生 V5 の頭部と採用済みの布地を合成したものですが、継ぎ目が残り、未採用・未配置です。旧公式の長髪選択は全身の原生お団子髪として扱い、重ね描きを止めました。表示名は四言語で明示しています。±090 の原生レイヤー再分割は隔離候補のみで、素体 42 枚は画素一致しますが、髪飾りのオン／オフには見た目の差がないため正式配置していません。詳細は `notes/2026-09-22-codex-v5-fullbody-identity-audit-27.md` と `scratchpad/mohan-v5-hanfu-unified-all-164/review.html` を参照してください。以下の表は前作業段階の項目別基準であり、この最新診断を上書きしません。

最新の決定：所有者は正面の灰青色の薄紗漢服を選び、「可以」と返答して +090° 側面と −180° 背面の衣装デザインを採用しました。両画像のオフライン背景除去と分離抽出を完了し、隔離環境での実際の描画 100 回は失敗 0、96 フレームで原生の頭部と手を照合しました。素材 8 件を原子的に配置済みです。記録は `scratchpad/mohan-v5-hanfu-unified-front-163/formal-installation-26/receipt.json` を参照してください。局所的な位置調整は布地のみで、V5 の顔・お団子髪・手は元の画像を維持します。正式再読込の結果と制限は `notes/2026-09-22-codex-v5-hanfu-pair-adoption-26.md` に記録します。

今回の対象は、隔離設定で原生髪型を使用した二方向のみです。残り 22 方向の統一確認は未完了で、下表の過去の検証行列を全体の合格とは扱いません。新しい長髪は対象外です。原生の生え際の灰色の縁、+090° の髪レイヤーに混在する身体画素、髪型・髪飾りの独立切替と選択肢の意味は未解決です。共用の原生レイヤーと利用者の衣装設定は変更していません。

| 範囲 | 完了した証拠 | 未完了 |
| --- | --- | --- |
| 七ポーズ V7 口形・眼状態 | 正式 84 フレーム、配置対象 86 件の SHA 一致、正式 runtime 84 枚を照合 | この範囲は完了。I／E／U は既存ソースの別名 |
| 七ポーズの藍白漢服 | 七ポーズを分離可能に導入。最後の五ポーズは配置対象 16 件。口形・眼状態・化粧の正式描画 336 枚、失敗 0 | 髪型・髪飾りの全切替の受入れを意味しない |
| 素顔と三種の化粧 | Classic／Light／Glamorous がそれぞれ 31 シルエットに対応。化粧・眼状態 279 枚と素顔 31 枚を照合 | 全身衣装・髪型・髪飾りを組み合わせた受入れは含まない |
| 全身 24 原画の出所 | 外部原画との不透明 RGB 一致 22 件、採用済み ±90° 側面の配置記録 2 件、Git-only の欠落 0 | 身元計測の全項目や公開監査の完了を意味しない |
| 作業 1：髪型・髪飾り | 七ポーズ 35 枚の切替診断、復元 7/7 一致。front-eureka の原生髪型の綁定漏れを修復。正式再読込 336 枚が staging と一致し、他の六ポーズは画素不変。関連テスト 21 件成功 | 全七ポーズは native alias で原生のお団子髪を保持。独立切替と選択肢の意味の修正は未完了。創作した長髪候補は未採用で、新しい髪型は対象外。原生の背景除去による生え際の灰色の縁は未修正 |
| 作業 2：全身の複合検証 | 実際に 1,488 枚を描画し、衣装検証 100 件が失敗。復元 24/24 一致。瞬きソース pin 一件を修復し、前後 72 枚の画素一致を確認。関連テスト 48 件成功 | 全失敗は ±90°。両側の衣装と旧長髪、+90° の髪飾りの計五レイヤーが顔保護領域に重なり素体へ復帰する。+075°、+135°、+150° 等にも衣装と素体の接合ずれがある。完全な検証行列は不合格 |
| 作業 3：状態整理 | 本ページを現況の入口とし、TASKS の現況と履歴を分離。古い文書から本ページへ案内 | 作業 1・2 の外観欠陥は未解決のまま保持。文書整理は外観受入れの代わりにならない |

正式な根拠：`assets/expressions/complete-expressions/manifest.json`、`assets/expressions/reviewed-garments/manifest.json`、`assets/official-packs/mohan.makeup.builtin.mohan-outfit`、`assets/pose-atlas/v5-base/SOURCE-PROVENANCE.json`。

証拠：`scratchpad/mohan-v2-v5-complete-seven-v7-formal-159/`、`scratchpad/mohan-v5-hanfu-five-candidates-161/formal-runtime-validation-08/validation.json`、`scratchpad/mohan-v2-final-runtime-matrix-160/isolated-runtime-validation-v4/validation.json`、`scratchpad/mohan-v5-appearance-closeout-162/`。今回のコマンド、終了コード、制限、SHA は `notes/2026-09-21-codex-three-workpackages-24.md` を参照してください。

2026-09-12 以前の出所・接合記録は追跡のために保持しますが、上記の V5 現況を置き換えません。作業ツリーは未コミットであり、ソフトウェアの公開・マージ・タグ付けは未承認です。
