# 2026-09-24 Claude Opus 5.5 主控：V5 二代素體接續

- 協作 session：`codex-claude-opus55-v5-resume-7b9d52dfc6c7`（actor 欄位只接受 codex/deepseek，實際主控為 Claude Opus 5.5，子代理 Claude Sonnet 5）。
- 接手點：revision 200（`64fe713d…feb7a`），status／verify／claim 均 exit 0，inventory_complete=true、access_warning_count=0。
- Git：branch `integration/worktree-consolidation-20260916`，HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`，`git status --porcelain=v1` 225 項，全部保留。無 commit／PR／merge／tag／發布。

## 開輪阻礙與處理

1. hitos 帳號讀不到 Codex 沙箱建立的歷史 pytest／scratchpad 暫存（handoff status `EPERM realpath`）。擁有者以系統管理員對清單路徑執行 `icacls … /grant hitos:(OI)(CI)RX /T`（只加讀取，不改內容／擁有者）；重掃不可讀 0，git status 回到 225。
2. 發現 `codex-20260924-routing-sol-max-01` 在 revision 198 之後持鎖。擁有者授權接管；執行時該 session 已自行 checkpoint 199（僅派工設定）與 release 200，故未動鎖檔、未接管。紀錄：`shared/agent-handoff/reviews/claude-opus55-lock-takeover-20260924/takeover.log`。

## 工作單元 1：四角眼態 revision04（已抽取、隔離合成；主控目視通過；非擁有者驗收）

- revision03 −60 退回原因（主控實測）：
  - 眼皮摺痕虛線：`cv2.INTER_LANCZOS4` 在 1254→426 縮小時不做低通，細線被取樣成點列；同圖 `INTER_AREA` 對照平滑。
  - 遠側眼緣淡邊：遮罩超出臉輪廓，部分 alpha 輪廓像素被來源色覆蓋。
- revision04：`scratchpad/mohan-v5-visible-geometry-scale-166/session48/four-eye-extraction-luna/revision04-claude/extract_eye_revision04.py`
  - 預乘通道以 `INTER_AREA` 縮小一次、反預乘一次。
  - 圖層限制在 root 的填洞輪廓（alpha≥128）內，輪廓部分 alpha 像素保持原生。曾試 2px 內縮，因 ±60 遠側眼位於輪廓上、閉眼時仍睜開而放棄。
  - 上方擴張 40 source px 覆蓋 root 自身雙眼皮摺痕（否則閉眼上方殘留短黑痕），並以下眉 468 點（46,53,52,65,55／276,283,282,295,285）＋6px 防護線裁切，眉毛保持原生。
  - 其餘沿用 revision03：幾何核心 alpha 255、僅外緣 3px 羽化、不以 RGB 差決定 opacity、8 張來源不重生。
- 命令：`.venv315\Scripts\python.exe <上列腳本> yaw-075-pitch+00 yaw-060-pitch+00 yaw+060-pitch+00 yaw+075-pitch+00`，exit 0。
- 收據：`revision04-claude/receipt.yaw-075-pitch+00_yaw-060-pitch+00_yaw+060-pitch+00_yaw+075-pitch+00.json`，SHA `b719961ea2f003dc1905479669ff002a5156fb6fcbdd2c04564000752bf3979f`。
- 技術指標（8 張）：圖層外改動、alpha 改動、輪廓外緣改動、y≥341 改動全為 0；SIFT inliers 564–723。腳本 Ruff check／format 通過。
- 主控目視（同尺度近照與原尺寸 5 倍）：虛線、短黑痕、遠側淡邊消失，眉毛原生，四角半閉／閉眼完整。殘留：±75 閉眼遠側輪廓外仍有少量原生睫毛細絲（在部分 alpha 輪廓上，眨眼層不改 alpha 故無法移除），留待擁有者整體審查。

## 進行中（子代理，各自唯一寫入目錄）

- A 腳踝缺口：`session48/feet-binding-claude-01/`。
- B 分層像素差稽核：`session48/root-rest-runtime-01/pixel-diff-audit-claude-01/`。
- C 新四角臉部零件＋眨眼隔離圖集：`session48/four-face-dynamic-binding-claude-01/`。

正式資產寫入 0；沒有新採用素材正式安裝。

## 工作單元 2：分層後 140／101／138／5 像素差定位（子代理 B，主控審閱採納）

- 目錄：`session48/root-rest-runtime-01/pixel-diff-audit-claude-01/`（audit.py、audit.json、REPORT.md、四角熱圖與放大對照）。命令 `.venv315\Scripts\python.exe …\audit.py` exit 0，四角差異數與先前回報完全一致。
- 比較前提核對：四份 runtime-receipt 的 DISPLAY-PLACEMENT、four_face_binding、妝容改動一致，只差 overlay asset root 是否經 `repartition()`；+75 root08 未改頭身檔。
- 結論（主控看過 −75 熱圖）：差異全部落在下巴／耳後／髮際與頸部交界窄帶（各 bbox ≤20×20），不在眼鼻口頰等身分區。成因是 `stage_hanfu_binding.py::repartition()` 以硬邊多邊形把頭層拆成 base／hair_back／body，使 renderer `_heal_registered_seams`（半徑 7）與 `_restore_authority_face` 的取代邊界位移；另有 ≤1 的 PIL／Qt 合成捨入。判定無害，可沿用分層資產。
- 限制：未以插樁重渲做逐像素位元級歸因；±60 有半數差異落在簡化 7px 環模型外（可能是 hair_left/right、jaw 的聯集環）。正式接入前不宣稱「零差」，改記為「僅接縫帶差異、身分區零差」。
- 子代理 D（華麗妝半閉／閉眼推導，9 個既有眼皮角度）已派：`session48/glamour-eye-states-claude-01/`。

## 工作單元 3：腳踝缺口（子代理 A，主控審閱採納為隔離修復）

- 目錄 `session48/feet-binding-claude-01/`（ROOT-CAUSE.md、FORMAL-INSTALL-PLAN.md、receipt.json、render-proof/）。全部命令 exit 0。
- 根因（正式素材缺陷）：−45／−30 未登記於新版 `v5-garment-visibility/manifest.json`，runtime 退回舊 `v5-appearance-replacement-masks/mohan.official.blue-white-hanfu/<view>.png`；該遮罩清空整段腳踝皮膚，而漢服 outerwear 裙擺與鞋之間本身透明 → 空鞋。
- 隔離修復：只在 asset-root 副本的兩個遮罩 y≥1150，將「遮罩清空且原生 body 有像素且衣裝 alpha<128」處改為不清空，露出既有原生皮膚；−45 改 5318 px、−30 改 4899 px，框外 0；bare 重渲逐位元組不變，漢服重渲腳踝框外差 0。
- 主控目視：修復前後近照，腳自裙擺連續入鞋、無接縫或膚色斷層。正式安裝只需替換兩個遮罩（SHA 見 FORMAL-INSTALL-PLAN.md），列入最終安裝計畫，待擁有者整體外觀審查。
- 子代理另記：renderer `_makeup_safe_regions()` 依賴 `assets/makeup-eye-apertures/`、`assets/makeup-foundation-safe-regions/`，缺漏會使衣裝 fail-closed 且 exit 0。

## 工作單元 4：淡妝／經典妝對新四角的幾何重綁（主控）

- 腳本 `session48/new-four-makeup-retarget-claude-01/retarget_makeup.py`。
- run-01 退回（保留為證據）：正式 light/classic 層是含舊臉像素的不透明替換補丁，直接 468 點分段仿射會把舊眼睛、鼻緣貼到新臉（+60 經典半閉眼可見）。
- run-02 方法：每眼態計算「Lab(舊臉＋妝層) − Lab(舊臉)」妝效差，連同層支撐 alpha 以舊原生 468 點→新臉 motion 地標分段仿射，疊回新臉自身像素（rest：root-four-face-03；half/closed：再疊 revision04 眼皮）；妝效 <1 ΔE 處透明，保持新臉眼孔與膚色原生。不改配色與形狀。
- 命令 `.venv315\Scripts\python.exe …\retarget_makeup.py --output run-02` exit 0，36 層；Ruff 通過。
- 例外：+75 舊臉沒有原生眨眼畫格，舊半閉／閉眼層本身就把眼睛畫閉，妝效無法與閉眼分離 → +75 light/classic half/closed 4 層列為待辦，改用與華麗妝半閉／閉眼相同的眼皮帶推導。
- 主控目視（四角 × 素顏／淡／經典 × 三眼態 3 倍近照）：唇色與眼皮暈色落在新臉正確位置，經典半閉／閉眼保留正式版同款柔和橢圓暈色；無舊臉殘像。尚未進 runtime（待新四角臉部分層圖集與新 safe regions）。

## 工作單元 5：新四角臉部分層＋眨眼隔離圖集（子代理 C，主控審閱採納為隔離候選）

- 目錄 `session48/four-face-dynamic-binding-claude-01/`；atlas 以 copy2 完整複製正式 v5-base（106）／v5-base-layered（658），逐檔 SHA 核對、無共用 inode。
- 四角 authority 換 root-four-face-03；臉部 17 層用正式 `build_yaw000_golden_template.build()` 從新 authority 切出；base／hair_back 改用 root07 地標臉橢圓法（golden 的 hair 遮罩把肩頸膚色誤判為髮，證據 `step3_golden_vs_root07_evidence.json`）；+60 遠側眼細分層依工具既有 `--empty-layers` 宣告空；四角寫入 blink-binding v2（+75 首次有眨眼）；mouth_center_x 以新地標重算；DISPLAY-PLACEMENT 只更新新 authority SHA 與 visible_bounds，scale／offset 不變。
- 第一版主控退回：runtime 頸部出現舊臉粉色橫帶與舊髮絲黑點（body 層保留了 y<341 舊像素）。step3b 修正：y<341 body 由新 authority 重建，y≥341 改動 0，覆蓋缺口 0、重疊 0、舊暗點 0；25 層聯集與 authority alpha 完全相等。
- 載入：其他 20 角動態欄位與正式逐項相同；語意稽核 600 檔 0 issue；runtime-v2 素顏 36 幀＋漢服 4 幀（衣裝改動 294k–351k 像素）。
- 主控目視：頸部與 root03 候選一樣平順；四角 rest／half／closed 雙眼皆正確閉合（+60 遠側眼也閉上，子代理「看不到」的說法有誤但結果正確）。
- 發現：用正式漢服包時新四角髮飾位置錯誤、−75 露出肩帶、+75 頸部硬切 → 由單元 7 與整合時套用 root08 領口修復處理。

## 工作單元 6：華麗妝半閉／閉眼第一版（子代理 D）— 主控退回

- `session48/glamour-eye-states-claude-01/` 第一版以 classic half/closed 足跡為範圍。實圖近側眼出現方形深紫色塊、直角硬邊並延伸眼下（瘀青感）。根因：classic half/closed eyes 是不透明方形替換補丁，不是眼皮暈色範圍。
- 已改派 revision02：以睫毛線／閉合線幾何量測 rest 妝容隨「距睫毛線高度」的剖面，等比套到半閉／閉眼眼皮帶，不用 classic 足跡、不上眼下；同時產生新四角華麗妝與 +75 淡／經典半閉閉眼。

## 工作單元 7：新四角漢服髮飾重綁（主控）

- 腳本 `session48/new-four-headwear-rebind-claude-01/rebind_headwear.py`，`--output run-01` exit 0；Ruff 通過。
- 方法：舊臉 468 點→新臉地標最小平方「等比縮放＋平移」（不旋轉），預乘一次重取樣；縮放 1.038–1.107，擬合 RMS 1.47–3.00 px。
- 主控目視：四角髮飾坐在新髮髻上，相對位置與舊頭一致。+75 流蘇懸於頭後且有分離小碎片，正式舊臉版本即相同，屬既有素材設計，列給擁有者判斷，不在本輪修改。

## 進行中

- 子代理 D revision02（華麗妝半閉／閉眼、新四角、+75 淡經典半閉閉眼）：`glamour-eye-states-claude-01/revision02/`。
- 子代理 E 最終整合隔離環境與 13 角渲染矩陣：`session48/integration-claude-01/`。

## 工作單元 6（續）：華麗妝半閉／閉眼 revision02 退回、revision03 採為整合候選

- revision02：改用睫毛線／閉合線幾何，方塊消失；但主控放大近照見整片灰褐煙燻，推定 rest 差值混入摺痕光影差。退回。
- revision03（`glamour-eye-states-claude-01/revision03/`）：rest 差值分眼線帶（0–2px）與眼影帶（2px 至可見眼皮 60%，不取摺痕以上），每欄穩健中位數；half/closed 眼線貼閉合線、眼影自閉合線以 smoothstep 淡出，色相角與 rest 眼影帶中位數差 0.00–8.12°（容差 10°）；y≥400、眉毛、下眼皮以下、可見眼孔改動 0。含新四角華麗妝與 +75 淡／經典半閉閉眼，共 28 層。
- 主控目視（−30、−60 四倍近照）：梅褐眼影沿閉合線平滑淡出＋眼線，無方塊硬邊、無眼下暈染。閉眼眼線帶比 rest 略深（偏煙燻），屬濃淡偏好，列入擁有者審查，不再自行調整。

## 工作單元 8：最終整合第一輪（子代理 E）與主控裁決

- `session48/integration-claude-01/`：階段 A–D 全部實跑 exit 0；asset-root 全 copy2、無共用 inode；312＋32 幀實際渲染 0 錯誤；妝容限臉部／alpha 0（234/234）、漢服衣裝（156/156）通過；9 角對正式基線 17/18 完全 0 差；半身 7 姿勢 member 與正式相同；DISPLAY-PLACEMENT 只差新四角 SHA／bounds。
- 發現與主控裁決：
  1. 正式安全區為 v2 手繪、工具拒絕重算 → 11 項妝被退回舊臉內容（+75 錯位白塊）。依安全區檔政策「核准矩形聯集」（前例 `mohan-v2-final-runtime-matrix-160/prepare_safe_region_compatibility.py`），主控新增 `session48/safe-regions-claude-01/prepare_safe_region_union.py`：新四角依新 rig 以工具規則重算＋核准妝層範圍，±90 保留手繪框＋核准華麗妝範圍；其他 silhouette 與遮罩不變；候選 SHA `b85aabbe30c15f08e731868165b6a758e6806d8bbfc648297f0c0c44caf0357c`，exit 0。正式安裝需擁有者授權（比照前例）。
  2. 華麗妝腮紅未對新四角重定位 → 主控擴充 retarget 工具 `--variants glamorous --slots cheeks foundation`（華麗妝眼唇仍只准來自擁有者採用來源），`run-03-glamorous-cheeks` 4 層，exit 0。
  3. yaw+000 眼態閘門 8 筆：正式包 classic／glamorous 在 half/closed 各有獨立 foundation 層（y194–390），屬既有設計；閘門改為「blink 疊層∪該眼態妝層∪rest 妝層」聯集內。
  4. hanfu yaw-030 腳踝框外 4 像素（alpha 2–15 羽化邊）：豁免區改為遮罩實際改動像素外擴 2px。
  5. 髮飾 receipt 的 owner_visual_acceptance=false 正確（主控目視≠擁有者驗收）。
- 已請子代理 E 以上述輸入重建重渲（第二輪）。

## 工作單元 9：整合第二輪（子代理 E）審查

- `integration-claude-01/round2/`：套安全框候選 b85aabbe（--check 通過）＋華麗妝新四角腮紅；94 項妝全部套用、0 項超框；verify_makeup_layers 通過；半身 7 姿勢與正式相同；312＋32 幀 0 錯誤；妝容限臉部 208/208、漢服 156/156 通過。
- 眼態閘門（精確定義並修正 DISPLAY-PLACEMENT 座標漏換）192/208 通過；剩 36 項全在 ±90（−90 無眨眼畫格、用眼皮下移備援，量測模型未完全貼合）。主控目視 ±90 half/closed 閉眼正常、無破圖。
- 腳踝豁免 −45 框外 66px、−30 2320px：主控放大比對，差異＝鞋內露出的原生腳＋鞋緣細邊，白裙下擺不變，屬預期修復內容。
- 主控目視另發現並已派修：
  1. −90 華麗妝半閉／閉眼沿用正式舊層 → 眨眼時妝消失。
  2. +75 華麗妝 half/closed 睫毛線外側米白點列：量測非變亮（ΔL>3 僅 1–2px），是眼線／眼影沿閉合線覆蓋斷續。
  → 子代理 D revision04：以渲染幀＋DISPLAY-PLACEMENT 反換算補 −90；閉合線附近沿眼長方向連續化，並加連續性自動檢查。
- 13 角漢服華麗妝頭部一覽：眼唇妝一致、髮飾在髮髻上、領口正常；+75 流蘇懸空為正式既有設計。新四角 −60 三款妝 × 三眼態一致乾淨。

## 工作單元 10：整合第三輪審查與閉眼眼孔遮罩

- round3（`integration-claude-01/round3/`）：用 revision04（含 yaw-090、閉合線連續化）96 項妝全部套用；閘門結果與 round2 相同，無新退化。
- 主控看真實渲染幀：−75、−60、+75 華麗妝閉眼眼皮上有淺米色塊；原生畫布合成無此問題。根因：`infrastructure/active_outfit_overlay_layers.py::_makeup_exclusion_region` 對沒有眼態眼孔遮罩的角度，所有眼態都挖掉「rest 虹膜−眼皮」，閉眼時眼皮中央留下未上妝的洞（淡色經典妝看不出，濃梅色華麗妝明顯）。
- 修正沿用正面與 ±90 既有 v2 機制：主控新增 `safe-regions-claude-01/prepare_eye_aperture_masks.py`，10 個側面角（±15、±30、±45、±60、±75）加入 rest／half 眼孔＝原挖除範圍（行為不變）、closed＝空，加 native_visibility 宣告（閉眼眼孔不可見）；粉底遮罩設為該角 base 範圍（這些角無粉底層，無作用）。候選 SHA `413967b6e94920e5177ea6ecf9809587dc1c162202fd5a9274a03ac158161bf1`，格式解析 31 角通過。
- 曾試「半閉眼孔＝rest 眼孔扣半閉眨眼層覆蓋」：多數角度結果為 0，因半閉眨眼畫格是自畫半睜眼的替換圖，「被覆蓋」≠「不可見」，有讓經典／淡妝畫進眼珠的回歸風險，已放棄。
- 第四輪（round4）已派：只套此候選，核心閘門為與 round3 逐像素比對（rest／half 必須 0 差，closed 只能在眼部變化）。

## 工作單元 11：整合第四輪、擁有者驗收頁草稿、領口破圖

- round4（`integration-claude-01/round4/`）：只套閉眼眼孔候選 413967b6；check／完整解析／verify_makeup_layers 通過；312＋32 幀 0 錯誤。核心回歸：rest／half 208 格與 round3 逐像素 0 差；closed 只有 36 格（10 側角 × 有妝變體 × 衣裝）改變且全在眼部框內；none closed 0 差。主控目視 10 側角華麗妝閉眼淺色塊已消失。
- 擁有者驗收頁草稿：`session48/owner-review-claude-01/`（build_owner_review.py，16 張圖取自 round4 實際渲染，標籤用專案字型 LXGW WenKai TC）。尚未交擁有者。
- 主控抽查頁面又發現新四角漢服破圖：−75 V 領內露出舊內衣肩帶；+75 左側領緣模糊拖影與鋸齒。已派子代理 F（`session48/collar-repair-claude-01/`），+75 先以正式舊臉渲染對照判斷是否既有。
- 既有問題（與正式基線逐像素 0 差，非本次造成，列給擁有者判斷）：±90 漢服頸部露細黑肩帶、−15 漢服 V 領露黑色內衣、+75 髮飾流蘇懸空。

## 工作單元 12：±75 領口調查結論、驗收頁定稿（等待擁有者驗收）

- 子代理 F（`session48/collar-repair-claude-01/`）：以正式資產根（舊臉＋正式漢服包）同 renderer 對照，−75 領緣線與 +75 左領緣缺口與本次新臉逐像素相同；清空外袍 PNG 的消融測試使兩者消失 → 屬正式漢服外袍素材邊緣既有瑕疵，非本輪造成。遮罩無邊界可調，未修改。子代理曾誤判為髮絲層並做無效修改，已在其 receipt 標記推翻、不得當作修復。主控看過新舊對照，同意結論。
- 驗收頁定稿：`session48/owner-review-claude-01/index.html`（17 張圖，round4 實際渲染；第九節列既有問題對照）。owner_visual_acceptance=false。
- 狀態：保留協作鎖，等待擁有者外觀驗收；驗收前不寫正式資產。

## 工作單元 13：擁有者驗收退件（2026-09-25）與修正計畫

擁有者原話：「問題還蠻多的，我都用紅線框起來了：漢服底下腳踝部位失蹤、華麗妝好幾張上眼皮有膚色雜點、好幾張雙眼眼部看起來像是剪貼上去的，雙眼周圍的膚色和臉部膚色不同。」（附 6 張標註截圖）驗收頁 round4 不採用。

主控根因與分派：
1. 腳踝失蹤（−15、+15、+30、+45、+60，素顏與華麗妝）：同 −45／−30 的舊替換遮罩清空腳踝；子代理 G `session48/feet-binding-claude-02/` 以 round4 asset-root 為底，24 角全面偵測後修復。
2. 華麗妝半閉上眼皮膚色雜點：半閉仍沿用 rest 虹膜挖除，被放下的眼皮皮膚被挖出洞。主控新增 `safe-regions-claude-01/prepare_half_aperture_masks.py`：半閉眼孔＝rest 眼孔中「原生半閉與原生 rest 差 ΔE76<15」仍可見的部分（−90 無眨眼畫格，改用 round4 實際渲染幀並以 DISPLAY-PLACEMENT 反換算）。12 角，每角停挖 19–93 px；候選 SHA `eff8e06d3d3c6502e549188ac7d8f72d3055ce298aff5709d464ba26ba138631`，exit 0。
3. 眼部剪貼感、眼周膚色不同：正式 light／classic 的 half/closed eyes 是不透明方形替換補丁；正面 yaw+000 的 classic／glamorous half/closed foundation 比 rest 明顯更亮（y194–390 整臉）。子代理 D revision05：light／classic 13 角 half/closed 改用睫毛線方法由各自 rest 眼妝推導（保持各自色彩），正面 half/closed foundation 與 rest 視覺一致。
- 以上完成後做整合第五輪並重做驗收頁；未完成前不再交驗收。

## 工作單元 14：退件修正進度

- 子代理 D revision05（`glamour-eye-states-claude-01/revision05/`）：light／classic 全 13 角 half/closed 改用睫毛線方法由各自 rest 眼妝推導（52 項檢查 0 違規）；正面 yaw+000 classic／glamorous half/closed foundation 以 rest foundation 妝效重建，眼部外平均 ΔE 0.013。
- 整合 round5 階段 A5 通過（半閉眼孔候選 eff8e06d、腳踝第一輪 4 檔）；B5 停下：revision05 的 4 張正面 foundation 各有 706–845 px 落在正式 foundation 安全遮罩外（眼部）。主控裁決：runtime 本就以該遮罩裁切 foundation，故預先裁切＝渲染結果相同且不改安全邊界。主控新增 `session48/foundation-clip-claude-01/clip_foundation.py`，exit 0，輸出 stage-fragment.json。
- 子代理 G 腳踝 round2：改用「裸身有、漢服透明」判定發現 18 角有缺口，並指出遮罩需以 DISPLAY-PLACEMENT 反推座標。主控審總覽退回：(1) 修過頭，+000、+105、±150、±165、−180 鞋外露出裸足腳趾；(2) +75 漢服 fail-closed（疑用正式漢服包而非 root08 暫存包）。已要求 round3：只修鞋口上方、裙擺以下腳踝帶，以 round4 asset-root 為底重做，用暫存漢服包。
- 教訓：驗收圖與審查頁一律改用淺綠背景；深色背景會藏住透明缺口（round4 驗收頁因此漏看腳踝）。
- 子代理 G 腳踝 round3（`feet-binding-claude-02/round3/`）：以 round4 asset-root 重做；只修鞋口上方、裙擺下緣以下腳踝帶（同欄 40px 內接續鞋子＋連通寬度 ≥10px 過濾），6 角修復（+15、−15、+30、+45、+60、+105），round2 修過頭處全部收回；改用 round4 暫存漢服包，24 角衣裝像素 ≥280,452、無 fail-closed；裸身 24 角逐位元組不變。主控看淺綠底 24 角總覽與 +105 近照，接受。
- 已請整合 round5 續做：foundation 裁切 fragment＋腳踝 round3 差異檔。

## 工作單元 15：腳踝改用 Codex 補繪（擁有者選方向 1）

- 擁有者：「只要是會露出腳踝的角度，幾乎沒有正常的。你不覺得看起來膚色腳踝都沒有填滿整隻鞋嗎」。主控確認：原生腳與漢服鞋款的位置／粗細不對應，鞋口內側為鞋內裡或空隙，露出原生皮膚無法填滿。
- 派 Codex gpt-6-luna：伺服器拒絕（`The 'gpt-6-luna' model is not supported when using Codex with a ChatGPT account.`，記錄於 `ankle-fill-claude-01/yaw-030-pitch+00/codex-run.gpt6-luna-refused.log`），依規定回報未改用他模型。擁有者指示「改用 gpt-5.6-luna 繪圖」；獨立 CODEX_HOME（主控 scratchpad `codex-home-luna`，model gpt-5.6-luna、effort xhigh＝5.6 世代最高）。
- −30 試點成功（1341×1173，縮回 534×467；對位 phase correlation 位移 <0.1px）。只擷取新增皮膚僅得鞋緣細縫；擁有者看對照（`20-owner-compare-yaw-030.png`）後選 1：以 Luna 版取代裙擺以下整個腳部區域，擴到 ±15、±30、±45、±60。
- 其餘 7 角 Luna 批次執行中（`ankle-fill-claude-01/run_luna_batch.sh`）；接入工具交子代理 G（`feet-binding-claude-02/luna-foot-01/`），以 −30 打通流程。
- 整合 round5（`integration-claude-01/round5/`）：粉底裁切與腳踝 round3 已套，148 項妝全部套用；剪貼感閘門 156/156（最大平均 ΔE 0.70）；半閉雜點與剪貼感主控待於最終驗收頁再目視確認。

## 工作單元 16：Luna 腳部接入（主控接手修正）

- 擁有者批准（`ankle-fill-claude-01/owner-approval-ankle-01.json`，SHA 2b49083c…）：−45、+60 第二版採用；+45 第二版退回（右側腳踝曲線不如 +60 自然），第三版（附 +60 為曲線參考）待擁有者回覆。
- 子代理 G luna-foot-01／02 兩次宣稱修好，但主控放大比對實際渲染仍見垂直接縫與 +15 鞋底重影；主控自行量測 02 的 +15 腳部逐欄最大差 23、>60 佔 2.3%，與其回報不符。根因（主控）：鞋子與裙擺同在 outerwear 圖層，以「裙擺下緣曲線」界定取代區時，鞋子緊貼裙擺的欄位被當成裙擺而漏換，舊鞋與 Luna 鞋拼接。
- 主控修正 `feet-binding-claude-02/luna-foot-03/stage_apply_luna2.py`：取代區＝渲染座標下「目前畫面與 Luna 差異 >24」∪「原生身體外露處」，外擴 5px、補洞，再以 DISPLAY-PLACEMENT 正向映射逐原生像素取色（gather）。以 round5 asset-root-v2 與暫存漢服包 copy2 重建，7 角（−60、−45、−30、−15、+15、+30、+60）套用 exit 0；`check_render.py` 實際渲染量測腳部下 70% 平均差 5.5–9.6；逐欄最大差集中在另一裙擺圖層的紗邊 1–2px 位移（腳部外）。主控 3 倍與 6 倍放大確認無接縫、無重影，皮膚紋理與 Luna 一致。
- 對照總覽：`luna-foot-03/40-owner-feet-7views-render.png`（左目前正式渲染、右接入後實際渲染）。
- 擁有者：「7角可以。+45第三版不行。」（`owner-approval-ankle-02.json`，SHA ba0a9772…）；+45 第四版（從原畫面重畫、附 +30／+60 參考）退回：「前面的腳形狀跟+60差很多」。第五版改由主控把已採用 +60 前腳等比 0.944 以鞋跟對位貼到 +45（`yaw+045-pitch+00/make_guide_v5.py`→`22-guide-…png`）作為引導，Luna 只調和視角與邊緣；擁有者：「+45第五版可以」（`owner-approval-ankle-03.json`，SHA 10bc78df…）。已以 luna-foot-03 同法接入 +45，渲染與 Luna 一致（差異僅為刺繡細紋重取樣）。
- 整合 round6：7 角腳部與參考渲染腳踝帶 0 差；其他閘門與 round5 同。round7（加 +45）進行中。

## 工作單元 17：整合 round7／round8 與眼態妝容強度問題

- round7：8 角 Luna 腳部接入，腳踝帶與 luna-foot-03 參考渲染逐像素 0 差；妝容限臉部 234/234、漢服 156/156、剪貼感 ΔE 156/156（最大 0.70）。
- 主控核對發現眨眼時妝容變淡或消失（淡妝最明顯）。子代理 D revision06 自稱強度校準 106/114 合規，但 round8 實測 classic half/closed 可見改動 / rest ≈ 0、light ≈ 0.005。主控查層：revision06 classic-half-yaw-030 alpha 最高 5、light-closed 最高 7（revision05 為 10–34）；正式 rest 眼層 classic alpha 255、light 64。子代理量法錯誤，已退回做 revision07，並指定與整合相同的驗收量法（原生 authority＋眨眼疊層為底，每通道和 >12，y150–265，分眼，half/closed 為 rest 的 0.5–1.5 倍）。
- 驗收頁腳本 `session48/owner-review-claude-02/`：改讀 round7+、8 角腳部對照、正面眼部裁切框修正；待眼態妝定案後產生。

## 工作單元 18：眼態妝改由 Codex gpt-6-sol 繪製（2026-09-25～27）

- revision07（子代理 D）：light 可用；classic 半閉／閉眼出現大片灰紫與垂直方條、glamorous 出現方形色塊 → 主控退回演算法推導路線。
- 擁有者指示繪圖助理改 gpt-6-sol medium；codex-cli 0.154.0 以 ChatGPT 帳號呼叫 gpt-6-sol 被拒（`codex-gpt6-sol-refused.log`）。擁有者同意更新 CLI：npm `@openai/codex` 0.154.0→0.157.0，gpt-6-sol 測試可用。獨立 CODEX_HOME `codex-home-sol`（需 `--skip-git-repo-check`）。
- 新流程 `session48/eye-state-makeup-sol-01/`：prepare_inputs.py（原生眼態底圖、睜眼帶妝參考、睜眼素顏參考，4 倍放大；−90 無眨眼畫格改用 round8 bare 渲染幀以 DISPLAY-PLACEMENT 反換算）→ Sol 依 BRIEF 繪製 → extract_makeup.py（ECC 仿射對位，Lab 妝效差，限睜眼妝層＋舊眼皮範圍外擴的安全區，羽化，預乘縮回原生畫布）。
- −30 試點 4 張（ECC 0.986–0.998），擁有者：「試點可以，擴大到13角」（`owner-approval-sol-pilot.json`，SHA b0b4d0a6…）。其餘 12 角 48 張批次繪製中。淡妝沿用 revision07。
- 12 角 48 張 Sol 繪製全部 exit 0；抽取 ECC 0.963–0.999。主控看華麗妝／經典妝 13 角三眼態總覽（`30-overview-*.png`）：眨眼時兩眼妝容皆在、濃淡與睜眼相稱、無方塊或直條。
- 發現正式 +90 眨眼畫格（blink_half／closed）在眼珠處有封閉透明洞，眨眼時露出睜眼眼白（白藍三角）＋黑點，素顏也看得到。主控 `session48/blink-hole-fix-claude-01/fix_blink_holes.py`：只補完全封閉的透明洞，以「authority＋眨眼層」合成色 Telea 補色，half 38 px、closed 25 px，洞外不變；其他 11 角無封閉洞（初版用形態閉合與 0 RGB 補色產生灰點，已棄用重做）。+90 眼妝以修補後底圖重抽。
- 第九輪替換清單 `eye-state-makeup-sol-01/stage-fragment.json`（SHA 8a7ea3c7…）；已派整合 round9。

## 工作單元 19：round9 B9 ±90 眼妝超框裁決（2026-09-27）
- 整合子代理 round9 在 B9 停下：±90 的華麗妝／經典妝 half／closed 共 8 層有 10%～55% 像素在正式 eyes 安全框外（y 185–231）；其餘 140 項全數通過；未寫妝包、未渲染。A9（+90 眨眼補洞）乾淨完成。
- 主控目視遮罩疊圖：框外像素是抽取殘影（+90 沿側臉輪廓線的色差、顴骨殘色；−90 淡邊），不是眼皮眼妝。裁決：裁切美術，驗證器與安全區（eff8e06d…）不變。
- `eye-state-makeup-sol-01/clip_profile_eyes.py`：alpha 乘上「框聯集內 3px 羽化、框外 0」遮罩；輸出 `clipped-profile/`，8 張框外像素皆 0，收據 `clipped-profile/receipt.json`；前後對照 `clipped-profile/20-before-after.png`（眼皮妝色保留、無硬直線）。
- `build_stage_fragment.py` 改為 ±90 取裁切版；新碎片 SHA 54a2f7a4…，已請整合子代理續跑 B9／C9／D9。

## 工作單元 20：round9 完成與主控親自核對（2026-09-27）
- 整合子代理 round9 完成：B9 148 項全套用 0 超框、verify_makeup_layers 通過、暫存妝包 SHA 2a038492…；C9 312＋32 幀 0 錯誤；妝容只動臉部 234/234、漢服衣裝 156/156、剪貼感 ΔE 156/156（最大 0.70）、8 角腳踝帶與 luna-foot-03 逐像素相同；眼態侷限 32 項（±90 既有）與漢服對正式 6 項與 round8 相同。正式檔 SHA 未變。
- 主控親自看實際渲染（淺綠背景）：三種妝 13 角三眼態無方塊、無直條、眼周無剪貼感；華麗妝眼皮放大無膚色雜點；漢服 8 角腳踝膚色填滿鞋口。觀察：−15 半閉／閉眼妝比相鄰角度淡、±90 半閉眼影較淡；±90 半閉上眼皮摺痕為素顏原生眨眼畫格既有。
- 驗收頁 `owner-review-claude-02/` 改讀 round9，更新說明、判斷事項與安裝範圍；index.html SHA e30551c8…；owner_visual_acceptance=false，等待擁有者驗收。

## 工作單元 21：擁有者第九輪驗收退件與方向裁決（2026-09-27）
- 擁有者退件：(1) 髮飾有的角度有銀鏈流蘇、有的沒有，外觀與位置各角度未對齊（要以髮飾絕對座標對齊）；(2) 經典妝、淡妝、素顏外觀無明顯區別；(3) 華麗妝睜眼／半閉上眼線有黑色雜點，眼妝不順暢（截圖 13 角多數）。
- 主控查證：9 個舊角度髮飾與正式版逐角相同（正式漢服包既有設計落差）；−60 為不同款藍花藤冠、−75 款式不同、±90 只有小銀飾、+30 多小白花。淡妝／經典妝眼層在原生解析度幾乎與素顏相同。華麗妝上眼線為睫毛線上方一列暗紅黑色離散點，來自華麗妝睜眼眼層本身。
- 擁有者裁決（AskUserQuestion）：髮飾以 +000 正面那套（髮髻頂銀絲鳳冠＋珍珠、右側藍花簪＋銀鏈流蘇）為 13 角標準，位置依正面換算對齊，先 1 角試點；淡妝／經典妝由主控擬規格，Sol 畫 −30 試點；華麗妝上眼線由 Sol 重畫為平順連續線（保持顏色與形狀），先 −30 試點。
- 試點（`session48/owner-fix-r10-claude-01/`）：prepare_pilots.py → Sol（run_sol.sh，gpt-6-sol medium）→ extract_pilots.py → make_previews.py。
  - 眼線 −30：Sol 重畫為連續上眼線，ECC 0.9987；預覽 20-preview-liner.png。
  - 淡妝／經典妝 −30：依主控規格（淡妝＝蜜桃裸粉眼影、細棕內眼線、淡蜜桃腮紅、豆沙粉唇；經典妝＝暖大地色眼影、黑棕微揚眼線、玫瑰豆沙腮紅、玫瑰紅唇）。抽取門檻改 MIN_DE 3／FULL_DE 7（舊 4／14 會把中等濃度妝打折）。發現眼部框與腮紅框重疊 55px，腮紅被眼層全強度吃走；加「眼妝區」（睜眼輪廓上 22、下 7、側 14 px）分界。淡妝腮紅強度 0.6 倍（SLOT_STRENGTH）。預覽 21-preview-makeup.png：素顏＜淡妝＜經典妝＜華麗妝。
  - 髮飾 −60：底圖＝漢服幀以素顏幀補回舊髮飾區；第 1 版流蘇過短（attempt-01 保留），BRIEF 補「藍花與流蘇大小長度同 −45」後第 2 版合格，ECC 0.9815；預覽 22-preview-headwear.png。
  - 預覽合成原本未做透明度 source-over，髮飾在背景上的部分被吃掉；已改 Porter-Duff（prepare_pilots.over）。
- 擁有者退回髮飾試點：「規格、配戴位置、銀鏈流蘇的長短、外觀根本沒有統一」。主控查證：當作標準的 0／−30／−45 參考彼此就不一致（流蘇款式與長度各異），逐角讓 Sol 推算必然各自發揮 → 放棄逐角繪製。
- 新方法（`owner-fix-r10-claude-01/headwear-design/`）：Sol 依正面髮飾畫一張標準設計圖 `10-sol-raw.png`（鳳冠／銀簪＋藍花＋銀鏈流蘇，均勻淺綠底），為 13 角唯一外觀來源；`render_headwear.py` 去背切零件，以髮髻中心為原點的固定立體座標投影到各角（鳳冠包覆髮髻正面圓柱、銀簪橫穿、藍花在她左側、流蘇固定長度垂直下垂且永遠正對鏡頭），尺寸除以 DISPLAY-PLACEMENT scale 使顯示大小一致，4 倍超取樣後預乘縮小。遮擋按零件：鳳冠落在輪廓內且在中心面後方 3px 以上隱藏；銀簪只在輪廓外可見（埋在頭髮裡）；藍花＋流蘇整組依花心深度顯示或隱藏。髮髻錨點為主控人工標定 `bun-anchors.json`（自動擬合圓會圈到整顆頭，失敗）。
- 觀察：素體髮髻本身各角大小形狀不一（±60～90 為雙層大髻），髮飾只能以各角實際髮髻為錨。
- 預覽 `headwear-design/30-preview-13-views.png`：負角度藍花流蘇整組在頭後被擋（物理正確），0～+90 可見且規格一致。

## 工作單元 22：擴大到 13 角（2026-09-27）
- 擁有者：「髮飾可以，眼線、妝容試點也可以，擴大到13角」；收據 `owner-fix-r10-claude-01/owner-approval-r10-pilots.json`（SHA 0ed65d24…），外觀最終驗收與正式安裝仍未批准。
- 睜眼妝：prepare_batch.py（templates/ 內 BRIEF 範本）→ run_batch.sh（xargs 4 路）36 張全 exit 0，ECC 0.993–0.999；extract_pilots.py 新增「只畫在身體上」規則（authority alpha ≥ 128；初版內縮 2px 會削掉 ±90 唇緣與臉緣腮紅，已改）。總覽 `40-overview-rest-0/1.png`。
- +60 華麗妝鼻樑外灰白點來自保留的華麗妝腮紅層（新四角腮紅／唇有少量像素在身體外）→ `glamorous-body-clip/clip_to_body.py` 以同一規則裁 13 角華麗妝腮紅與唇（每層移除 1–23 px）。
- 眨眼妝：`session48/eye-states-r10-claude-01/`（沿用 sol-01 已採用方法，參考改為新睜眼妝；BRIEF 加「眼線平順連續」；抽取 MIN_DE 3／FULL_DE 7、裁在眼部框內 3px 羽化）；三款 × 13 角 × 半閉／閉眼共 78 張派 Sol 中。
- 髮飾執行期硬規則查核：`crown-safe` 髮飾碰到「臉部底層遮罩扣頂端 1/5 ∪ 五官核心」即 OutfitPackError（fail-closed）。以同規則量新 13 層：重疊皆 0。
- 擁有者：「半身7姿勢也一起換成新妝」。半身底圖＝`assets/expressions/complete-expressions/frames/<pose>-neutral-<rest|half|closed>.rgba.png`（1254²，與妝層對齊）；5 個 front-* 姿勢共用 front 臉部素材但妝層各自不同。腳本以 authority_path 分流 yaw／姿勢；BRIEF 加「手部不得上妝」。
- 半身問題與修正：(1) 華麗妝眼層無封閉洞 → 淡妝／經典妝眼層抓不到眼睛（0 px）；姿勢改用素材 eyelid＋iris 為睜眼範圍，眼妝區依眼寬比例（face_scale＝eyelid 寬／21）放大。(2) 腮紅超出安全框被切成直線 → 腮紅改為框內淡出（框短邊 20%），眼／唇維持 3px；13 角總覽確認腮紅未變淡。(3) 正式 left-neutral 華麗妝唇層有半透明方塊覆蓋到臉外背景，身體範圍裁切移除 3,499 px。
- 7 姿勢睜眼妝 21 張完成（總覽 41-overview-poses-0.png）；13 角眨眼妝 78 張、7 姿勢眨眼妝 42 張派 Sol 中。眨眼妝抽取亦加身體範圍規則。替換清單產生腳本 build_stage_fragment.py 已寫（待眨眼妝完成後執行）。
- 眨眼妝：13 角 78 張、7 姿勢 42 張全 exit 0；抽取最低 ECC 0.980；總覽 `eye-states-r10-claude-01/50-eyes-*.png`、`51-poses-*.png`。觀察：−30 淡妝半閉／閉眼偏粉紅（其睜眼妝本就較粉），留待擁有者判斷。
- 關鍵修正：執行期半閉／閉眼時整張睜眼眼層被眨眼眼層替換（active_outfit_overlay_layers.py:348–359），且眼妝／腮紅各有強度滑桿 → 眼層不得夾帶腮紅。改為 (1) 眼妝區軟邊（ZONE_SOFT_PX 1.5）並與腮紅互補分配（cheeks 權重＝cheek_fade×(1−eye_share)）；(2) 半身素材 eyelid 已含下眼瞼，下緣留白 0（yaw 維持 7）。驗證：眼層單看無粉紅帶、整臉合成無接縫。
- 替換清單 `owner-fix-r10-claude-01/stage-fragment.json`（SHA 468047b2…）：rest 180＋eye_states 120＋headwear 13。主控預檢：300 張妝層以正式 makeup_layer_escapes 對 round9 安全區（eff8e06d…）超框 0。已派整合子代理 round10（A10–D10）。

## 工作單元 23：round10 核對與半身眼腮分界修正（2026-09-27～28）
- round10 完成（子代理）：313 層全套用、清單外成員位元組與 round9 相同；verify_makeup_layers 通過；344 幀＋半身 84 幀（LayeredParametricFaceRenderer 正式路徑）0 錯誤；閘門與 round9 相同，無新退化；髮飾區另列。
- 主控目視 round10：13 角髮飾統一、眼線連續、四款濃淡分明；半身淡妝／經典妝在 front-exasperated 等姿勢有腮紅直線切口與眼下粉紅帶。根因：共用 rig（cheek／lean／front）的 eyelid／iris 圖層與各姿勢實際眼位差 20–60 px（exasperated 為閉眼且頭傾斜）。
- 修正：主控在 3 倍格線圖人工標定 7 姿勢眼睛橢圓 `owner-fix-r10-claude-01/pose-eyes.json`（front-exasperated 列 closed_at_rest：眼線在睫毛線上不挖空）；眼妝區依眼寬比例放大（face_scale＝平均眼寬／21）。重抽 14 組半身淡／經典妝 → 新清單 45ebac21…（與 round10 差 28 項，全為半身淡／經典妝 rest 層）；rest 180 張預檢超框 0。已派 round11 增量。
- 驗收頁 build_owner_review.py 已改讀 round10、新增「十、半身 7 姿勢」、移除過時「+75 髮飾流蘇（正式同）」與「半身 7 姿勢不變」字樣；待 round11 後改讀 round11 半身幀。
- round11（子代理）：28 層增量，素顏／華麗妝 42 幀與 round10 逐像素相同，淡／經典妝 42 幀全有更新。主控核對發現 front-exasperated 半閉／閉眼右頰方形淡斑：傾斜姿勢唇框延伸到頰部，唇層帶腮紅；眼妝區下緣隨臉放大把腮紅劃進眼層，眨眼被替換而消失。
- 修正（extract_pilots.py）：lip_zone＝素顏嘴唇（唇框內 Lab a* 高於中位數 8 的最大區塊）外擴 3px×眼寬比例，唇層只留此區，腮紅權重×(1−lip_share)；眼妝區下緣固定 7px 不隨臉放大。`blink_check.py`（42-blink-check-*.png）模擬執行期眨眼合成：切口消失、腮紅眨眼不變；13 角總覽正常。新清單 5e9e2a5b…（較 round11 變 94 層，全為淡／經典妝 rest），預檢超框 0；已派 round12。
- round12（子代理）：94 層增量；全身素顏／華麗妝 156 幀與 round10 逐像素相同、半身素顏／華麗妝 42 幀與 round11 相同；閘門同 round10；新閘門「眨眼不帶走腮紅」半身 28/28 通過，全身 20 格未過皆為既有（±90 素顏眨眼位移 16、yaw+000 經典妝眼態粉底 4，華麗妝同幅）。
- 主控核對 round12 半身：扶額切口消失、眨眼腮紅不變。驗收頁改讀 round12（全身與半身），修正拼圖黑帶，待決事項補 front-mock-scold 閉眼深色斑痕（素顏同，正式眨眼畫格既有）。index.html SHA 361441215a52…，送擁有者整體外觀驗收。

## 工作單元 24：round12 驗收退件與根因（2026-09-28）
- 擁有者：漢服 +90 無頭飾；半身 7 姿勢半閉／閉眼雙眼錯位、外觀怪異（素顏亦然）。另指示繪圖助理模型改 gpt-5.6-sol medium：codex-home-sol/config.toml 已改（原檔備份 config.toml.gpt-6-sol.bak），試跑回報 model: gpt-5.6-sol、exit 0。
- +90 根因：domain/outfit_pack_official.py:57 `_PLUS090_FACE_SAFE_HEADWEAR_SHA256` 白名單；新 +90 頭飾 SHA 43491aa8… 不在名單 → native_overlay_is_redundant 整層略過（active_outfit_overlay.py:677）。正式修法須於正式安裝時補白名單＋測試（需擁有者授權）；隔離預覽以行程內 monkeypatch 呈現。
- 半身眨眼根因（渲染路徑）：round10–12 半身渲染對 render_overlay 傳空 QPixmap，CompleteHalfbodyRenderer.blink() 回傳整張端點畫格；正式路徑為 companion_blink_composite._blink_composite（blink_masks[pose] 遮罩眼部貼片 → blink(base, state, eye_patch, makeup_context)）。審查頁半身眨眼圖非使用者實際所見。
- 另：外觀輪廓（v5-appearance-silhouettes）在全身頭部帶會聯集整條頭部橫帶，不裁頭飾（已查證）。
- 已派 round13：A13 +90 頭飾隔離預覽；B13 以正式眨眼路徑渲染半身，正式基線與 round12 並列，判定是否既有問題。
- round13（子代理）：A13 +90 頭飾以行程內白名單補丁預覽，12 幀可見、0 OutfitPackError，其他角度與 round12 位元組相同（主控目視 +90 鳳冠＋藍花流蘇正確）。B13 以正式路徑（465px 半身資產、真實 _build_blink_masks／_blink_composite）渲染正式基線與 round12：front-exasperated 不眨（EYES_CLOSED_EXPRESSIONS）；front-eureka／mock-hit／mock-scold 閒置不眨、說話時才眨；cheek-rest 只有 closed 眨。主控放大核對：cheek-rest 閉眼遠側眼仍睜、left-neutral 閉眼殘影眼珠，在正式基線即存在（素顏逐位元組相同）→ 既有半身眨眼素材缺陷，非妝容造成；round12 未惡化。
- 擁有者裁決：半身眨眼「這批一起修」。正式來源：complete-expressions manifest 各姿勢 half／closed 端點＝rest 底圖＋eye_patch（scratchpad/mohan-v2-v5-eye-state-source-discovery-148/isolated-bare-eye-patches/eye-patches/<pose>.<state>.rgba.png，約 35k px 大塊貼片，內含錯位眼睛）；companion 另有 idle_*_half／closed 等 465px 來源。
- 試點 `session48/halfbody-blink-fix-claude-01/`：prepare_inputs.py（rest 眼眉 4 倍裁切＋BRIEF）→ gpt-5.6-sol（4 張全 exit 0，log 確認 model: gpt-5.6-sol）→ collect_raw.py → build_patches.py（ECC 對位 0.88–0.97；遮罩＝pose-eyes 橢圓外擴 14×12px、羽化 6px；1254² 全畫布 RGBA 貼片 ~10.8k px）。預覽 20-pilot-composite.png：left-neutral、cheek-rest 雙眼一致半閉／閉合、位置對齊、無殘影、無接縫。
- 擁有者退件試點 1：閉眼雙眼眼袋不自然、疑似拼貼。修正 build_patches.py：遮罩上方外擴 14px、下方只到下眼瞼＋2px（眼袋保留原圖），羽化 4px；以遮罩外 8px 環帶的 Lab 平均差做膚色校正。第 2 版試點已送擁有者。
- 擁有者退件試點 2：全閉眼仍像兩個眼袋（睜眼下眼瞼殘留於閉合睫毛線下）。修正：LOWER_MARGIN 依眼態（half 2px 保留原眼袋；closed 20px 換到臉頰上緣），closed 以 cv2.seamlessClone（Poisson）融合；第 3 版試點送擁有者。
- 擁有者：第 3 版試點「可以，擴大到其他會眨眼的姿勢」（收據 halfbody-blink-fix-claude-01/owner-approval-halfbody-blink-pilot.json）。front-crossed／eureka／mock-hit／mock-scold 8 張 gpt-5.6-sol 全 exit 0；6 姿勢 12 張貼片 ECC 0.84–0.97，總覽 22-all-composite.png：雙眼一致、無雙層眼袋、mock-scold 舊深色斑痕消失。front-exasperated 不眨眼不處理。
- 眨眼妝：eye-states-r10-claude-01/prepare_inputs.py 半身底圖改為 rest＋新貼片；舊半身眨眼妝移到 superseded-halfbody-v1/；36 張（6 姿勢×3 妝×2 眼態）派 gpt-5.6-sol 中。
- 待辦：新貼片需以正式格式替換 complete-expressions 各口型族（neutral/a/o/small）half／closed 畫格，以及 465px companion 眨眼來源（idle_front／idle_lean／eureka_front／mock_hit_front／mock_scold 的 _half／_closed 與 cheek 用 blink 系列），再以正式眨眼路徑渲染核對。
- 36 張半身眨眼妝全 exit 0，抽取 ECC≥0.995；總覽 eye-states-r10-claude-01/52-halfbody-v2-*.png 主控目視通過。新清單 44f633a2…（較 round12 只變 36 個半身 eye_state）。已派 round14：A14 妝包替換；B14 在隔離區重建 complete-expressions 半身眨眼畫格與 465px companion 眨眼來源；C14 正式眨眼路徑 (a)正式／(b)round14 並列；D14 審查頁。
- round14（子代理）：A14 36 成員替換、verify 通過；B14(1) complete-expressions 48 畫格隔離重建（貼片與各口型族底圖精確對齊）；B14(2) 465px companion 來源阻塞：companion 底圖（idle_lean.png 等）與 complete 底圖不同（平均差 72–82/255），貼片座標不相容，依限制未自創縮放；C14 兩路徑渲染 0 錯誤，眨眼時眼周外像素 0 變動，complete1254 路徑 round14 雙眼一致閉合、無殘影。
- 主控查 layered_face_renderer.py:117/311–317：正式渲染器在眨眼時優先走 CompleteHalfbodyRenderer.blink（complete 畫格端點，companion patch 只當 alpha 範圍），465 可能僅為後備。已派 round14b 以正式應用組裝判定實際像素來源（(a)正式／(b)指向 round14 complete-expressions）。
- round14b（子代理）判定：實際路徑（companion_face_animation.py:780-796 → companion_blink_runtime.py:25-52 → _blink_composite → render_overlay → CompleteHalfbodyRenderer.blink）真正眨眼的 22 格像素全部來自 complete-expressions；465 _half／_closed 檔只經 _masked_region 提供範圍（實際由寫死的 blink_masks 決定）。B14(2) 阻塞撤回：只需 complete-expressions 重建即可。front-eureka／mock-hit／mock-scold 閒置不眨（Contract B）、cheek-rest half 無來源＝rest，皆正式既有行為。
- 主控放大 b_round14 cheek-rest closed：遠側眼仍殘留眼白。根因：presentation/companion_face_assets.py:181-184 _blink_regions["cheek"] 第二矩形 QRect(198,153,61,34) 只到 y=187 且邊緣漸層，遠側眼下半未被替換。修正需改原始碼（併入正式安裝授權範圍，同 +90 白名單）。已派 round14c：覆蓋率表＋建議矩形、行程內 monkeypatch 預覽、實際路徑驗收幀 frames-actual、眼白殘留自動檢查。left-neutral 新版已確認修好。
- round14c（子代理）：覆蓋率表與建議矩形（cheek 眼1→(198,153,68,44)、lean 眼1→(191,153,67,40)、front 兩眼上緣 146 高 41）；行程內 monkeypatch 預覽。主控放大確認 cheek-rest 閉眼遠側眼白殘影在建議矩形下消失。
- 主控核對 frames-actual 發現：(1) 465 路徑四款妝逐像素相同＝完全未套妝（round13 B13／round14 C14 companion465／14c 的妝容相關結論失效）；(2) front-eureka closed.speaking 她的左眼未閉。已派 round14d：查未套妝根因並修正渲染設定、判定 eureka 說話眨眼像素來源與正式修法選項、重跑 frames-actual-v2。驗收頁 build_owner_review.py 已改：半身讀 frames-actual（待改 v2）、會說話才眨眼姿勢用 speaking 眨眼、hanfu +90 讀 round13 白名單預覽；尚未送擁有者。
- round14d（子代理）：未套妝根因＝其渲染腳本 ActiveOutfitOverlay(store, P/"assets") 傳錯根目錄（應為專案根），讀安全區失敗被 apply_animated 吞掉；修正後 v2 六姿勢有妝（none vs glamorous max 116–188）。eureka 說話單眼未閉根因＝presentation/companion_blink_brow_guard.py preserve_gesture_brows（eureka 專屬寬門檻 DARK 155／WIDTH 9）挖除範圍侵入眼部，底下 rest 睜眼透出；像素來源仍為 complete-expressions。主控目視 v2 華麗妝：妝容可見，eureka 閉眼一眼仍睜。
- 主控裁決採方案 2（眉毛保護扣除 blink_masks 眼部範圍的硬邊界，門檻不動），已派 round14e 行程內預覽（frames-actual-v3）。正式安裝時的原始碼修改清單累計：outfit_pack_official.py +90 白名單、companion_face_assets.py _blink_regions、companion_blink_brow_guard.py 硬邊界（皆需測試）。驗收頁半身已改讀 frames-actual-v2。
- round14e（子代理）：方案 2 行程內修補 companion_blink_composite 命名空間內的 preserve_gesture_brows（guard 扣除 blink_masks[pose] alpha>0），門檻未動；eureka 兩眼 closed_fraction 對稱（0.196／0.211），眉毛保護於眼部遮罩外逐像素不變，mock-hit／scold 遮罩外與 v2 相同。
- 驗收頁更新：半身改讀實際路徑 frames-actual-v2（手勢三姿勢讀 v3 speaking），+90 hanfu 讀 round13 預覽，說明／待決事項／安裝範圍（含三項程式碼修改）更新；index.html SHA eed1e5c3…，送擁有者整體驗收。

## 工作單元 25：閉眼眼袋下橫線（2026-09-28）
- 擁有者退件：front-mock-scold／eureka／crossed、left-neutral 閉眼時雙眼眼袋下方多一條橫線。主控根因判斷：閉眼貼片下緣延伸至眼下 20px（Poisson 融合換眼袋），但實際路徑只在 _blink_regions 矩形內替換，round14c 建議矩形下緣橫切貼片 → 上新眼袋、下舊皮膚的水平接縫。已派 round14f：矩形只向下與左右擴大至完整涵蓋同 rig 所有貼片（上緣不動以保眉毛保護）、重渲 frames-actual-v4、接縫量化驗證。
- round14f（子代理）量測否定主控假設：矩形未切到貼片不透明區；橫線位於貼片本身。主控放大 1254 合成確認：閉眼 Poisson 融合在眼下留下淡水平邊與細直紋。修正 build_patches.py：閉眼改為膚色校正＋寬羽化（STATE_FEATHER closed 14px，LOWER_MARGIN 22），移除 Poisson；舊貼片存 patches-v3-poisson/。6 姿勢重建（closed alpha ~16–18k px），24-all-closed-feather.png 主控目視：無橫線、無直紋、單一眼袋。貼片變大，實際路徑眨眼矩形可能需向下擴大（待整合驗證）。送擁有者先看 1254 貼片圖。
- 擁有者：「可以，繼續」（v4 貼片，收據 owner-approval-halfbody-blink-v4.json；patches/receipt.json SHA 0dc8415f…）。已派 round14g：complete-expressions-v4 重建、依 v4 貼片範圍重算 465 眨眼矩形（上緣不動）、frames-actual-v4 實際路徑渲染與眼下接縫量化驗證。
- round14g（子代理）：complete-expressions-v4 48 畫格重建；矩形重算（cheek 眼0 (160,153,55,38)、眼1 (198,153,70,45)；lean 眼0 (153,153,55,35)、眼1 (191,153,68,40)；front 眼0 (178,146,55,41)、眼1 (220,146,56,41)），貼片 alpha 無超出；有妝、眉毛保護與 v3 相同、腮紅唇不變；cheek-rest half 無來源＝rest（既有）。主控放大實際渲染閉眼：眼下無橫線、雙眼閉合。驗收頁半身改讀 frames-actual-v4/rendered，送擁有者整體驗收。

## 工作單元 26：全身說話嘴型（2026-09-28）
- 擁有者指出驗收頁「六、新四角說話嘴型」A、O 全是閉嘴。主控查證：round12 嘴型幀與閉嘴幀 0 差異；正式版全身亦幾乎不張嘴（yaw+000 A 24px、−060 8px、−030 0px），只有 ±90 有 complete_expression_frames（neutral／a／o／small × rest／half／closed，viseme 對應 A→a、CONSONANT／E／I→small、O／U→o，motion_policy preserve_body_layers＋head-neck replacement_mask）。擁有者裁決「這批一起做」。
- 方案：其餘 11 角比照 ±90 建立 complete-expression 畫格；由 gpt-5.6-sol 在閉嘴原圖畫 a／o／small 嘴型，取嘴部羽化貼片套到 rest／half／closed。試點 yaw+000（fullbody-mouth-claude-01/：prepare_inputs.py、build_mouths.py；ECC 0.979–0.998；20-pilot.png）已送擁有者。待解：開口時唇妝層會蓋到口腔，需口腔遮罩（complete group 的 oral_mask）。
- 擁有者：「可以，擴大到其他角度」（收據 fullbody-mouth-claude-01/owner-approval-mouth-pilot.json）。10 角 30 張 gpt-5.6-sol 全 exit 0；ECC 0.979–0.999。build_mouths.py 新增：口腔遮罩 <view>.<shape>.oral.png（唇凸包外擴 4px 內暗色或齒色像素）；側臉張嘴時唇與下巴超出閉嘴輪廓，Sol 以灰底補空隙 → 以灰底偵測（|RGB−128|<14）產生繪圖輪廓 coverage，貼片 alpha＝mask×coverage，並輸出 <view>.<shape>.erase.png（原輪廓內被畫成背景處），合成＝先以 erase 降底圖 alpha 再 source-over。主控放大 ±75／+60：灰藍色消失、輪廓自然。總覽 21-all.png 送擁有者。
- 待接入：比照 ±90 建立 11 角 complete-expression 群組（frames×{a,o,small}×{rest,half,closed}＋neutral＋replacement_mask＋oral_masks），half／closed 需與眨眼畫格組合；erase（輪廓變更）如何進入 complete frame 的 alpha 需整合子代理依 _replace_complete_expression_region 行為設計。
- 擁有者：「可以，繼續接入」（收據 owner-approval-mouth-11views.json；patches/receipt.json SHA eaa65acb…）。已派 round15：A15 複製 round14；B15 比照 ±90 建 11 角 complete-expression 群組（a／o／small／neutral × rest／half／closed、oral_masks、head-neck replacement_mask、preserve_body_layers），驗證 erase 輪廓在 replacement 流程中確實生效；C15 渲染與回歸（閉嘴須與 round14 逐像素相同、口紅不入口腔）；D15 審查頁。
- round15（子代理）：11 角 complete-expression 群組建於隔離 asset-root（frames 6 viseme×3 眼態、oral_masks、neutral、replacement_mask），220 嘴型幀 0 錯誤；round12 標準矩陣與「round12 現版腳本重跑」逐項一致；閉嘴 rest 8/22 格與 round14 有 <0.1% 反鋸齒差（新 neutral 路徑）；oral 範圍內華麗妝殘留 44/110 格。主控目視：素顏 A／O／小張口正確；華麗妝口紅仍為閉嘴唇形，張嘴時嘴角外留深色線（正式渲染器上妝後會以 oral_mask 還原口腔，故問題在唇妝未跟嘴型）。
- 擁有者裁決：「張嘴時口紅依嘴型重畫」。妝包格式目前只有 eye_states（domain/makeup_eye_states.py、outfit_pack._makeup_variant），無 viseme 唇妝 → 需擴充妝包格式與渲染（程式碼修改，併入正式安裝）。試點 mouth-lipstick-claude-01/：prepare_inputs.py（說話素顏底＋閉嘴口紅參考）→ gpt-5.6-sol → extract_lips.py（Lab 差、限嘴型貼片範圍扣口腔）；yaw+000 華麗妝／經典妝 × A／O，ECC 0.98–0.996，21-pilot.png 主控目視：只塗唇、口腔乾淨、嘴角無深線。送擁有者。
- 擁有者：口紅試點「可以，擴大到其他角度」（收據 mouth-lipstick-claude-01/owner-approval-lipstick-pilot.json）。3 妝 × 11 角 × a／o／small＝99，扣試點 4 張，95 張派 gpt-5.6-sol 中。之後：抽取、總覽核對、派整合子代理在隔離區擴充妝包格式（viseme 唇妝）與渲染驗證（程式碼修改第 4 項）。
- 95 張口紅全 exit 0；99 層抽取 ECC≥0.974；總覽 mouth-lipstick-claude-01/30-overview-{glamorous,classic,light}.png 主控目視：只塗唇、口腔乾淨、嘴角無深線、濃淡淡＜經典＜華麗。已派 round16：行程內擴充妝包 mouth_states（a／o／small 唇層）＋驗證＋渲染替換接點（附等價 diff），安全區必要時依「現框∪唇妝 bbox」擴大；暫存包 99 層；C16 渲染驗證（嘴角深線、口腔、閉嘴不變、全身回歸）。
- round16（子代理）：行程內 mouth_states（a／o／small 唇層）＋ _makeup_layers 替換接點（viseme 需沿 layered_full_body_renderer → active_outfit_overlay → active_outfit_overlay_layers 補傳，等價 diff 於 stage_c16_render.py 檔頭）；lips 安全框 3 角各擴 1px（現框∪唇妝 bbox）；妝包本體不動、99 層以 sidecar 載入；440 幀 0 錯誤、閉嘴與 round15 相同。主控放大發現 yaw+000 O 華麗／經典嘴角外仍有暗線：逐層歸因 foundation 77px（rest 粉底帶閉嘴唇緣暗邊）。修正 mouth-foundation-claude-01/derive_foundation.py：粉底 alpha×(1−嘴型貼片 alpha)，6 張；原生座標模擬確認暗線消失。已派 round16b：mouth_states 在 foundation silhouette 成對攜帶 lips＋foundation、13 角嘴角環帶重量、口腔殘色逐層歸因。
- round16b（子代理）回報粉底修正「無肉眼改善、素顏也有線」。主控查證：素顏乾淨（其判斷錯誤）；v2 幀扣 display offset 後嘴角外僅 16px 差異（foundation 77→4px，粉底修正有效），可見鋸齒橫紋在新唇妝範圍內＝口紅被挖。根因：_makeup_exclusion_region 以 rest rig 口縫（(oral_cavity∪teeth_tongue)−(lip_upper∪lip_lower)，domain/outfit_pack_makeup.py:75）排除，yaw+000 69px 中 43px 橫切 O 唇妝。已派 round16c：說話時口腔排除改用嘴型 oral.png，v3 重渲、唇妝範圍未上色像素表、8 倍放大。程式碼修改第 4 項範圍＝mouth_states schema＋_makeup_layers viseme＋呼叫鏈傳遞＋_makeup_exclusion_region 嘴型口腔。
- round16c（子代理）：_makeup_exclusion_region 說話時改讀嘴型 oral.png（CLOSED 走原函式），v3 528 幀；主控未親驗說話幀前先查其「閉嘴 60/88 非逐位元＝雜訊」結論：yaw+000 classic／glamorous 閉嘴唇部 612–641px、max 136–152 差異，none 0 → 放大確認閉嘴唇妝被換成他組（疑 _round16_viseme 殘留或快取未依 viseme 失效）＝回歸非雜訊。已派 round16d：修狀態洩漏、快取鍵加 viseme（等價 diff）、v4 重渲＋渲染順序交叉驗證。
- round16d（子代理）：根因＝正式 ActiveOutfitOverlay 圖層快取鍵（_phase_layers_by_view、_layers_by_view*）不含 viseme；v3 說話 O／CONSONANT 亦受污染。腳本層以既有 _invalidate_view 失效；等價 diff：快取鍵加 viseme。v4 528 幀：閉嘴 vs round15 0 失敗、順序交叉驗證 44/44 逐位元相同。主控目視 v4：三款妝閉嘴／A／O／小張口口紅隨嘴形、嘴角乾淨。
- 驗收頁第六節改為「全身 11 角說話嘴型」（四款妝各一張，讀 round16/frames-mouth-v4，依 DISPLAY-PLACEMENT 換算裁切），安裝範圍與程式碼清單加入說話嘴型／唇妝／粉底／快取鍵。index.html dec665e4…，送擁有者。未決小項：−15／+45 口腔殘色 16–39px。

## 工作單元 27：擁有者最終驗收與正式安裝（2026-09-28）
- 擁有者：「1.採用2.另開工單3.授權正式安裝」。批准收據 session48/owner-final-approval-20260928.json（SHA 2057d242…，owner_appearance_approved、install_authorized、4 項程式碼修改；commit／push／PR／merge／release 未授權）。
- 另開工單：交接 TASKS.json 新增 v5-existing-hanfu-neck-issues-ticket-20260928（±75 領緣、±90 細肩帶、−15 V 領內衣）。
- 已派整合子代理 INSTALL-1（唯一寫入者）：階段一 4 項程式碼＋迴歸測試＋pytest／run_all／ruff；階段二 staged 正式包（mouth_states 入 manifest）＋完整 asset 差異＋approved_asset_install plan／install（yaw+075 blink 疊層來源須查核准）；階段三 新行程正式驗證。每階段停下回報。
- INSTALL-1 階段一（子代理）：4 項程式碼＋測試（新 domain/makeup_mouth_states.py、tests/test_makeup_mouth_states.py、tests/test_official_native_headwear.py；改 outfit_pack_official、companion_face_assets、companion_blink_brow_guard、companion_blink_composite、_outfit_pack_models、outfit_pack、outfit_pack_makeup、active_outfit_overlay、active_outfit_overlay_layers、layered_full_body_renderer 與相關測試）；針對性 30 檔 248 passed／7 failed（既有）；ruff 全庫通過；run_all 在第 104/473 模組既有失敗中止。子代理違規使用 git stash（共用堆疊）→ 主控以 checkpoint 214 快照 --untracked-files=all 比對：遺失 0、新增 13 全為本包檔案、既有 dirty 內容變動 4 檔皆在範圍內。主控重跑 7 筆失敗確認與本包無關。已批准階段二並禁止再用 git stash；install 前需再停一次回報目標清單。
- INSTALL-1 階段二停點（子代理）：round16 asset-root vs 正式 assets 差異＋2 正式包＝352 目標（238 新增／114 變更）；Stage 2 補 domain/outfit_pack.py `_partial_pose_assets`、`_declared_asset_paths` 含 mouth_states（＋測試）；唇層改名 viseme-*（身分保護字詞）；正式 loader／verify_makeup_layers 以 round16 安全區通過；preflight 352/352。子代理以「查無核准」排除 yaw+075 blink＋binding 3 檔。主控裁決：驗收頁「正式安裝範圍」第一項即「新四角…眨眼畫格與綁定」，且 +060／−060／−075 已納入，+075 補回（355 目標），approval 加 index.html 證據；核准直接 install，後續測試與階段三正式驗證一次回報。
- 安全警告（Irreversible Local Destruction）查核：子代理 `rm -f` 刪除自己產生的第一版 install-approval／install-plan（352 項，SHA 9b43592f…／c529ce82…）後重建；建置腳本無其他刪除；正式素材未受影響。已要求改以版本檔名保存、禁止刪除任何專案檔案（approved_asset_install rollback 除外）。
- INSTALL-1 完成（子代理）：355 目標（含 yaw+075 blink 補回）preflight／install 成功，approval 1c856714…、plan 1b5044c0…、收據 59e98a82…，備份 114 檔於 install-claude-01/install-receipt/backup/。第一版 352 項 approval 9b43592f…／plan c529ce82… 已被刪（紀錄保留 SHA）。安裝後：正式渲染全身說話嘴型 264 幀與 round16d v4 逐位元相同；全身標準矩陣 312 幀 300 相同、12 幀為 +90 漢服頭飾可見（預期）；ruff 通過；test_official_default_pack 3 失敗（常數過時）、test_full_body_authored_blink 1 新失敗（yaw+000 改走 complete-expression）。
- 主控查證：半身眨眼 v4（round14/complete-expressions-v4，48 格＋manifest）未納入安裝（計畫 assets/expressions 目標 0）。已派 INSTALL-2：補裝、半身正式驗證（先查服裝差異來源）、授權更新測試常數（EXPECTED_MAKEUP_VARIANTS=3、PROBES 取已核准資產實體像素、authored blink 測試改用 legacy view 或替身，不降低斷言）。
- INSTALL-2（子代理）：半身眨眼 v4 48 格＋manifest，approval 1fd69373…、plan eca0496e…、收據 784b5964…；服裝差異根因＝其驗證腳本未先 render 穿裝 rest；修正後半身 96 幀與 round14g v4 逐位元相同。測試常數依授權更新（EXPECTED_MAKEUP_VARIANTS=3、PROBES 附來源、authored blink 測試清除 complete_expression_frames 保留斷言）；針對性 250 passed／6 failed（既有）；ruff 通過。主控核對兩份收據 404 個目標 SHA 與現況 0 不符；stash 清單空。
- 交接：TASKS.json 新增正式安裝紀錄與既有測試失敗工單；CURRENT_STATUS.md 頂部更新。
