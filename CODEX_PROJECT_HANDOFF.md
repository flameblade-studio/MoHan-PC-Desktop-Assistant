## 2026-09-15 Codex 與 DeepSeek 共享交接

繁體中文：擁有者已授權 DeepSeek Harness 在 Codex 週額度恢復前接續 2–3 天，再由 Codex 接回。統一入口為 `D:/FlamebladeStudio/CodexProjects/shared/agent-handoff/START_HERE.md`；最新逐項證據見其 `mohan/CURRENT_STATUS.md`、`SOURCE_PINS.json` 與 `TASKS.json`，接手須用工具核對實際檔案與 checkpoint。以下較早的歷史紀錄不覆蓋新 receipt。此交接未安裝正式素材；既有 1443 筆 dirty 狀態保留。107 是 scratch runtime verified；108/01 真實缺口尚未解決；82/09 恢復 708 px 後仍有 22 px 原生頸部 visibility 待接。115 O 已批准並凍結，117 去背待 root 複核與整合；114 A、116 三張仍待擁有者確認。116 另張遭拒絕的生成未重試。全身、半身與四妝容整套替換仍未完成。

简体中文：经所有者授权，使用上述共享入口交接给 DeepSeek，再由 Codex 接回。接手必须核对 checkpoint 和实际文件，较早历史不得覆盖新 receipt。既有工作树保留，正式素材安装未完成，待确认与阻塞项目见共享状态。

English: The owner authorizes DeepSeek to continue for 2–3 days, then Codex to resume. Use the shared entry above, verify checkpoints and actual files, and preserve the dirty checkout. Older history must not override newer receipts. Scratch results, pending owner reviews, blocked generation, and incomplete formal installation are recorded separately in the shared status.

日本語：所有者の承認に基づき、DeepSeek が 2～3 日継続し、その後 Codex が再開します。上記共有入口と実ファイルを照合し、未コミット作業を保持してください。古い履歴で新しい receipt を上書きせず、試作・承認待ち・生成停止・未完了の正式導入を共有状態に従って扱います。

## 2026-09-15 左右90小開口退回與重製採用

繁體中文：user「臉的五官又偏掉了」的兩個附件SHA精確對應110/plus090-small與minus090-small（281b142176ca7c44a3e99cf7c3dfbe14ed529fc35cfe998c9e9adb59e95387e7／827b8a0f03c050383471048d57721a7d565c193f0ea2c20e3ff0b30247dd1bca），已記110/owner-rejection.json。ambient107瀏覽頁不是此回報的圖，不能推論撤回107漢服或87閉口原圖批准。110曾把19正面齒列圖作輔助參照，可能造成側臉重新解讀（原因為推論，非工具已證明）。

111改用各自87已批准同側全身原圖作唯一參照，由builtin imagegen整張重製小開口，沒有貼嘴、補臉或改RGB。plus source SHA a45d104a001e5460c876875398cd59a4e2309dc2b6a884826a6e0a0f911f7404；minus source SHA 090c4c0332ecefa757faa58f2c051e44e4f9e3b2e1655d5be4f750b330d6dabf；原生1024x1536，已copy回workspace與generated原檔逐byte相同。generation-receipt SHA43fa2e9e5ff5cf38f884e4be8ea7653243ac5f7d82f636880cd140c1505f37fd；review SHA70e0bc333ed73f5c4ec1c829d4aa1495471b9c717cbce3f4eb5513e36a6da38d，提供同側閉口與重製小開口同尺寸比較。call_RaEODp8NrulJj1BbrEiuRolt「兩張都可以採用」，owner-approval SHAddfd8a1af1a868e14995fd7ae427a0d6df12b8e98306b0bbf5e8fdec530ba60e，source-receipt SHAee5fca01db8182278009f7121b6c290bf3f375a3bc69589200be7ddf07c34298。112接續已批准雙張離線去背，尚未宣告完成。

32原persist→build成功，29頁；歷史已採用人物69、取代6、現行63、hold4、可用59，89/90仍兩組待owner。authority SHA05e1848942f10155f9d490b4f74cd448eed9961ffe93866e4826abc8a9ec2875，coverage e3e27ba0e2c1879bd7ce73678365dc097b21810ea989319ad44c7e5b72f819b1，receipt5281a3cde4dee34e9dff2b2ade4cd1d11288a98871d2607bc697963c089f9409。111批准明確加入revised_identity_states，舊65hold不應套到新批准小開口；既有4張舊側臉眨眼仍hold。正式寫入0。

108修正三項preflight錯誤後工具已備妥：Path參數、Pillow save回None、原生visibility改0/255幾何避免alpha平方；fixture exit0且非產品測試。prepare SHA7b02c5a197059067811f2ca2c928c5f1d216f64b71150eef0ac15c4c4a03a759。82/07雖補指甲洞，root仍見手層混藍白衣料而未選；08只校正外边界所有權，root已看目前預覽，待封存SHA再跑108neutral。107 registry-verification SHA1eac2b94a27ae271be408af15ef93bf7163bfd46ef9b4730a1fe3e29fefcb8f1驗227個SHA引用及36個可解碼PNG，對應當時28頁snapshot；111新增後該歷史snapshot SHA不再是最新32。

简体中文：110两张因五官偏移退回。111仅用同侧87原图重制，用户已采用；112去背中。32现29页、69历史批准、59可用、4旧来源hold，89/90仍待确认。108已修正预处理错误，待08封存后试接，正式写入0。

English: The attachments identify rejected speech candidates110 exactly. They do not revoke87 neutral or107 garment approval. Both complete single-reference redraws111 are owner-approved; matting112 is underway. Registry32 has29 review pages,69 historical adopted and59 available sources, with four old identity holds and reviews89/90 pending. Cheek108 awaits sealed components08. No formal writes.

日本語：添付画像と一致する110発話候補は五官ずれで差し戻し。87の同じ側の原画だけで全体を再制作した111の2枚は承認済み、112切り抜きを進行中です。32は29ページ、採用履歴69・利用可能59・旧4素材保留、89/90確認待ち。108は08の封存後に試着確認予定、正式書き込み0です。

## 2026-09-15 恍然大悟可拆漢服 12 態實際穿脫完成

繁體中文：104 完整漢服批准維持（owner SHA 634f28b8a3a1ee8f4af52217c4ede6dd02dabd1f59d69bc0d680c7ebb7b5e7c8）。107 已完成衣裝單層的 source-bound 提取，103 完整原生頭臉／雙手繼續作皮膚所有者。partition-01/02 因殘留皮膚、灰上衣或白袖陰影被切除而退回；03未跑；04完成36張但獨立審查發現袖外半透明alpha被切掉；05還原外緣卻夾帶領口髮絲，未選取。最終06保留04內部衣裝分界，只在103 native visibility為0的衣裝外緣接回105原生alpha，沒有改RGB、描新五官或烘整個人物。06 receipt SHA fefdb800d0968c83038345517d9f2d853dfb49eff4a5a826b87075a323eed5c4；independent-verification SHA 18b27ec04aec78bc103931ae0411bbc5c42e8aafc3fc45d1d792dec1b695fe95，4個原生袖緣取樣alpha全相同，新增14,934點均不侵入native頭／手遮罩，白／黑底無重大外緣問題。

107/candidate-06-all-states：實際ActiveOutfitOverlay + LayeredParametricFaceRenderer跑12態×none/Hanfu/none-return共36張，exit0；receipt SHA 55f72809db821b48346b6332967801d3902e24241bb810f105ebca90e448e801。root-verification SHA a3ffd68b5ec35a3fc3e2e49d3406cc77345856bcb30b7084329b53d484e965b1：Qt預乘RGBA逐像素核對所有none/return、上半頭及全部保留原生像素都是0差。root目視neutral-rest、small-closed、a-half、o-rest，衣領袖口、完整雙手與齒列連貫，root-visual-review SHA 99a9a1bff262179bcb913819d20f12875f0387dad9ca67411b3134a7ad4f2c06。selected-runtime.json SHA cbd393c540c44a58b94c2a48deb502505a22cd6932562155115d9d700edfe85d，status scratch_runtime_verified；技術分層不創造重複原圖owner批准。review.html已產生36張引用並交open_in_codex，工具只回queued，未宣稱瀏覽器DOM已開成功。

32原persist→build已收錄107，28頁、89/90兩組仍待owner；authority SHA bf210d88ba8fc8a859d32a1b52595201a7bd12e1b763e30d8fef9ef046ad7e7c，coverage c5c2f150a905c901be3475a9759e63ebf4fbfe86f6439259d51dcd928d1cc0fa，receipt c35173695780154bc25a13838808fbc7df61d27a5f6a85214539aad64081c792。整套24角度／7動作／4妝容仍未完成，107其餘髮型、髮飾與妝容待接，正式寫入0。32首次插入程式時置於receipt初始化之前曾失敗，已移到103證據更新之後並成功重跑；失敗的中間snapshot不可當成有效收據。外緣脚本最初因無scipy匯入失敗，已直接沿既有cv2實作，不安裝新依賴。

托腮82/source-components-07尚在修正：root發現膚色分類錯把白指甲／暗手紋移入衣裝，skin層有洞；必須保留完整手部內部、只處理真實衣料边界。108 prepare_fit.py及build_runtime.py已備妥但尚未選取新07或跑render；57整頭＋77完整手部皮膚與衣裝雙層要先root目視試接。不得宣稱托腮袖口已修好。109接續唯讀盤點四妝容舊五官綁定問題；沒有生成或套用新妝容。

简体中文：107最终06完成12态36张实际穿脱，原生头手及脱衣回復逐像素零差，袖外透明边缘已复核。32收录28页，89/90仍待确认。托腮07指甲归属仍需修正，108尚未运行，四妆容／其他外观与全局正式替换未完成。

English: Eureka107 candidate06 completes 36 actual wardrobe renders across twelve native states. Original RGB, preserved native head/hands and undressed roundtrips are verified; original sleeve matte is restored without claiming native skin. Registry32 records this scratch-stage result and retains pending reviews89/90. Cheek07 nail/hand ownership still needs correction;108 has not run. Makeup and global formal installation remain incomplete. No formal writes.

日本語：107の候補06は12状態・36枚の着脱を実描画し、元RGB、保持した頭部・手、脱衣後の復帰一致を確認しました。袖のalpha外縁も検証済みで32へ記録。89/90は確認待ちです。頬杖07の爪・手の所有権を修正中で108は未実行、化粧と全体の正式置換も未完了です。正式書き込み0です。

## 2026-09-15 可拆衣裝邊界接續

繁體中文：103 新增 visible-review.html，以12張已驗證的實際預覽提供完整動作／臉部切換，原封存review.html不變；32 build已更新入口，27頁、2組待owner（89/90）。104完整漢服批准及105去背保持有效。106正在準備同源的完整衣裝單層與103原生visibility；107的prepare_fit、實際runtime runner與穿脫比較頁builder已備妥，尚未執行。衣裝內部不必強拆袖口，既有ReviewedGarmentPose允許非空任意數目的ordered_layers；完整衣裝可獨立穿脫，皮膚不可混入衣裝。

82/manual-boundaries-06完成凍結，receipt SHA279dd8e3344204d2691e970e8587a96154a9f59fc8aa043d5aa63a743e71f251。Root目視仍有水平手上方灰背景縫與左下指尖截斷，root-visual-review SHA73d00d0a046ec45ed017081807ecb1289429db503d0fb58149aa73148cedd156，退回不擴12態。451像素gap是膚色啟發式診斷，不能當全部不可避免缺口的證明。停止反覆描57手硬接77袖，改於82/source-components-07提取77批准原圖的完整雙手／前臂為獨立skin layer，衣裝另層；108沿既有API准备57整頭+77完整皮膚／衣裝組件試接，none回57。尚無07/108完成成果，不可宣稱修好。91/design-check確認既有模式支持，沒有現成57/77配對；不改產品API或正式素材，正式寫入0。

简体中文：103新增实际预览页。106/107准备单层可拆衣装；06仍有灰缝和截指，已退回。07/108改用77完整手部作为独立皮肤层配合衣装，保持57整头并在脱衣后回57，尚未完成。

English: Runtime103 has a new visible review. Boundary106 and runtime107 prepare a single detachable clothing layer. Boundary06 is rejected for a gray gap and clipped fingertips. Components07 and fit108 will pair intact approved77 hands as a separate skin layer with clothing, retain the complete57 head, and restore57 when undressed. No new runtime or formal writes are claimed.

日本語：103に実描画比較ページを追加。106/107は単一の着脱衣装層を準備中です。06は隙間と指先切れで差し戻し。07/108は承認済み77の手を独立皮膚層として衣装と組み、57の頭部を保って脱衣時に57へ戻す試作を準備中。正式書き込み0です。

## 2026-09-15 恍然大悟原生渲染完成，完整漢服採用

繁體中文：103 實際 LayeredParametricFaceRenderer 產出 12 種 front-eureka 表情，沿用 FacePose.FRONT 與 eureka_front 系列表情路由，沒有不存在的 EUREKA enum。receipt SHA de894667a854e11696f56d04f8bfc1b04a0407ff0e058eba09a6ba19c3da3de7，verification 16cb06e108db8cf32613727e429bb993013a51341778b3bc05e6ba5f951abb01，manifest 98498078f3bda78a81c30f62dec85a1099b6f7460c6a84088c8fbcc597b568c7。root-verification SHA 046a94c5b6541c871237bf8e3e9aa473787b1c852cd86bc6f40723d9d67e6407：12 張 premultiplied RGBA 與固定來源全部逐像素零差；root 看過 neutral-rest、neutral-half、small-rest、a-closed、o-half 五張實際預覽，整臉、齒列、舉指與雙臂無明顯缺失。未接衣裝，正式寫入0。原圖12態的owner批准維持，不製造另一個重複原圖批准。

104 恍然大悟漢服由 builtin imagegen 以 38 原生動作與 77 已批准漢服款式產出完整新原圖，沒有局部補臉或貼嘴。source SHA dfb3fe60f1318bd888c59bbc9e0a221a60d3e30f4c1498b82d1fa87e7ff5fffe；generation-receipt 0576dd8a2e35afbd936fb80c233057100054fd83f21d8b080313b8eb9eeb341f。使用者 call_bMYlw4VDYeT7kPJrD9KrWiIt「可以採用」，owner approval SHA 634f28b8a3a1ee8f4af52217c4ede6dd02dabd1f59d69bc0d680c7ebb7b5e7c8。105 離線去背1張exit0，receipt 736272616f6dd725611cf2b30c099589dd26f6a50759046aa5ee9b5f25e24b3a，root-verification 0ad511320ad9f019cee1bcc5b5389338c008467827e7e791955a84a3868a8b1d；1254² RGB/alpha sidecar零差，root看過四色背景。106接續衣裝語意邊界提案，未選層。

91 candidate-01 首次实际 none→Hanfu→none 三張已跑完，receipt f48ea3cd35e87adba7499174ff3078975453582b0b98d477cc97dbe4687edefb，脫衣回復原生零差。root 視覺退回（root-visual-review SHA 700836242c8f48f82f34c6ad2faee334bd5e0c3d845afdcaf811877d3be31038）：袖口細縫、水平手上方灰上衣殘留，以及袖口下方小塊白衣。05分層收據 6a25bb36be9f05e1e88e87b097e8538009e79b33bd5e2c4d3e4f74182ce9878e 保持不變；不可把此neutral試接擴成合格12態。正在診斷77與57手部邊界差异和分層alpha接縫，禁止塗補RGB掩飾。

32 最新 persist/build：27 個比較頁，歷史人物批准67、取代6、現行61、hold4、可用57；衣裝來源另2。authority bf210d88ba8fc8a859d32a1b52595201a7bd12e1b763e30d8fef9ef046ad7e7c，coverage f9829778ecaf468006f8daef1ba349126e24c3af04b60c3b32e1d3b7aa820efe，receipt 812b4a5762b3a7a81c15e26cbc4b10416375bfddbf5d1ff9f4105eb2c3094994。89八張、90四張仍待owner。沒有修改產品程式，沒有重跑不相關pytest，正式寫入0。

简体中文：103完成12态实际渲染，root核对预乘RGBA零差。104完整汉服已采用，105去背完成，106准备分层。91穿脱试接回復零差但袖口细缝及灰上衣残留仍需修正，尚未採用。89/90待确认，正式写入0。

English: Runtime103 produces twelve native Eureka states; root verifies exact premultiplied RGBA equality. Complete Hanfu original104 is approved and matting105 verified. Semantic partition106 is next. Cheek probe91 restores the bare source exactly, but cuff seams and a gray-top remnant are visually rejected. Reviews89/90 remain pending; no formal writes.

日本語：103のひらめき12状態は実描画と元画像のpremultiplied RGBA一致を検証済みです。104漢服原画は承認済み、105切り抜き済みで106分離を準備中です。91は着脱復帰が一致する一方、袖口の隙間と灰色肌着の残りで外観差し戻しです。89/90確認待ち、正式書き込み0です。

## 2026-09-15 恍然大悟 12 態原圖全部採用

繁體中文：99 三張說話的 owner approval SHA d1cbea0cb4b5090b2d132164cc22239dc25e3f5f1887aaadd144fc1a2e277a8e；100 去背 receipt ddad1321a9b33d4f73cf245013fc1acb0c4bce38935158b42609cacc21675bfe，root verification 4dd8a7c1d98d569e495081b966ae3a4d05dfe384e562ec63458196be657abe10。使用者 call_3YAZoTZbZhbncRO9SzJAF1Au「六張都採用」已封存 101/owner-approval.json SHA 0abb282dca8e2f08436929071a8bd3309b5674fca14aa9902e4211a9b204b88d；101 六張原生 1254² RGB 整張生成、原始副本不變。102 離線去背 exit 0，receipt f5028b4e567ac9094ae5d54b8688e9c3a14a820f1befeffc2291f035ee46492f；root-verification c4412d0cf69ff726f0c9ef5d804dae7915485852f4b35dec0ea51bb46f19252f。六張 RGB 與 alpha sidecar 逐像素零差，root 已看完六張四色背景，髮髻、臉、舉指、雙臂無明顯缺失。38/97/99/101 組成恍然大悟 12 態，103 準備實際 renderer，獨立合約審查後執行；此刻未宣告完成 runtime。

32 使用原 persist_progress.py → build_review.py，已收錄 101 採用，歷史人物批准 67、取代 6、現行 61、hold 4、可用 57，衣裝另 1。89 左側半身 8 張與 90 左右 60 度全身 4 張仍待 owner 回覆。25 個比較頁，正式素材寫入 0，整套尚未完成。

82 CPU 控制證明相同 SAM 仍有格洞與錯分，不再重試。manual-boundaries-04 已凍結但 root 退回：領口切入頸部，托臉前臂遮罩只到 830、實際延伸至約 918，袖口與水平手邊界錯置。05 依原生 77 完整圖重畫語意 alpha 邊界，沒有改 RGB。91/prepare_sourcebound_fit.py 將只選 77 的 garment/left_cuff/right_cuff；頭頸與雙手保留 57 原生 12 態，手遮罩僅用於遮擋參照。待 05 完成通知和 root 目視後先跑 91 neutral 3 張，再視結果扩到 36 張，尚未執行。

简体中文：恍然大悟 12 态原图已全部采用，102 六张去背保留原 RGB，实际渲染 103 待独立审查后执行。托腮边界 04 已退回，05 修订中，91 尚未执行。89/90 仍待确认，正式写入 0。

English: All twelve Eureka source states are owner-approved. Batch102 preserves native RGB and alpha; root viewed all six four-background previews. Runtime103 awaits independent contract review before execution. Cheek boundary04 is rejected; boundary05 continues, and runtime91 has not run. Reviews89/90 remain pending. No formal writes.

日本語：ひらめき 12 状態の原画はすべて承認済みです。102 の元 RGB と alpha を検証し、6 枚の背景別プレビューを確認しました。103 は独立契約確認後に実行します。頬杖の境界04は差し戻し、05を修正中で91は未実行です。89/90 は確認待ち、正式書き込み0です。

## 2026-09-15 恍然大悟眨眼採用及去背完成

繁體中文：使用者 call_buHZ9N8Q7Up8j6cOuw2O3ThS「兩張都採用」已封存於97/owner-approval.json（SHA 6a9a0f8969eae1b73e503fbe195d7cf3caae402e59ca5655d32ee8af985f2cc2）。98離線去背2張完成，receipt SHA 6564cd7102e3093d90a64ac4e5e8f9c3e732be44bf6da9c57ebb44d75e4a039f；root-verification SHA b2aad2800aa7cb51f25da372d40ab2c0aa9f6e7fdb5050a13449689eaadea6c8，independent-verification SHA e4af0559178ff55778dded7ff247b720c68680344df77e004a6dd1d27f00b96b。1254²、RGB與alpha sidecar逐像素零差，兩張四背景均目視，沒有明顯缺失的髮髻、臉、手指或肩線。模型初始化曾長時間延遲，之後正常完成，並非已確認的環境故障。正式寫入0。

99恍然大悟small/A/O完整說話原圖由builtin imagegen各生成一次，以38已批准原圖及19/21批准嘴型為參照，已copy至99且未修改像素／未去背。generation-receipt SHA 13c55c7bc80ecc3488c760ad9ca24c7ac51b631228b600eb7ee169fbb2f212cb，review SHA 3e2412e8f1b2fb572d15095901c8fd81c894c08b1eb9222d7147fc68ea3fef30；root看過全部3張，已提問等待owner，不能當已批准。32總覽24個比較頁，三組待確認：89八張、90四張、99三張；97兩張已採用。現行authority SHA 2a6a753e659b61f08cd1def1b7d12913144c8272222c8194e0e456f53ec775ec，coverage SHA e1f53721a2e34a1dcbaed81008672fdd4784be08e367ea260da6fb7bf54195af，receipt SHA 4e00aad5bfadbd07b5fbe274c92fb2a3ae5650b6b8c265f2681049da302b78b9；歷史58、取代6、現行52、hold4、可用48，衣裝來源另1，全局未完成。

96的6張左右90閉口眼態來源核對完成，但現有完整表情provider拒絕neutral-only，實際render 0張。96/correction.json SHA e060ea3bf0dfb73ebb1d22aa5fe9ac1019ae700bad2d17c37afa01349949bc59修正助理最初的錯誤推論：合約要求6個viseme ID×3眼態，並不要求18張獨立新原圖；42既有FAMILY把CONSONANT/I/E對到small、A對到a、U/O對到o。應補齊各側3個嘴型家族×3眼態，沿用既有完整合約，不必為本次素材引入neutral-only暫用provider。96 probe exit0只表示成功記錄拒絕，不代表runtime通過。助理曾執行相關pytest25 passed/35.05s與全repo Ruff，未更改產品程式。

82單次CPU float32 SAM控制已完成，與CUDA幾乎相同（IoU 0.999395–0.999937）；格狀洞和混入臉/袖口/手仍存在，未選層。停止相同模型重試，82/manual-boundaries-04改以原生RGB對照描繪語意alpha邊界，原始RGB、位置、尺寸保持；待root看候選，再以91實際衣裝流程檢視穿脫。91仍未render，既有72的裸肩/双手腕問題未宣告修好。

简体中文：97两张眨眼已批准，98去背及独立验证完成。99三张完整说话原图待确认，89/90仍待确认。96只有闭口帧，补齐三个嘴型家族后沿用现有合约；82 CPU验证未消除遮罩问题，转为明确语义边界，91尚未接合。正式写入0。

English: Eureka blinks97 are approved; matting98 preserves native RGB and alpha, with root and independent visual/technical verification. Three intact speaking originals99 await owner review, along with89/90. Probe96 renders zero frames because neutral-only is incomplete; correction96 confirms existing aliases allow three mouth families across six viseme IDs. CPU control82 reproduces mask defects, so explicit semantic alpha tracing is in progress; runtime91 has not run. No formal writes.

日本語：97の瞬き2原画は承認済み、98は原RGBとalphaを検証済みです。99の発話3原画と89/90は確認待ちです。96は閉口のみでは描画不可ですが、既存の3口形から6音素IDへの対応を継続します。82のCPU対照でも境界欠陥が残り、明示的なalpha境界を制作中で91は未実行、正式書き込み0です。

## 2026-09-15 左右 90 度全身四張眨眼採用

新增審閱97：root 用 builtin imagegen 以38已採用 eureka 完整原圖作唯一參照，完成半閉眼 SHA db79f11a80ea0b0b88062468bd93fca5e39089d96e05041a0a3edaef6ee70fa9、閉眼 SHA 493c6f3fed04edb8e273fe937db892d442a0c388a69121c98cf74248ed7ff6cd，均1254×1254 RGB、與生成raw逐byte相同，未去背／未加工RGB。97 generation-receipt SHA f6a1ff6d8469121b731c6a6547be0f06f58ed6656ca273434800af2cccc8c3e8，review HTML SHA bf54eab25e8a043336c4176bfb0f8be12abadb883a9c2e3758cfebedaaafea3c，已提問，兩張待owner。32總覽現有23個比較頁入口、3組待確認（89八張、90四張、97兩張）；authority/coverage未變，receipt SHA 74f81dee4ed6dfe77cf288abbd314ee41053ebc22bb782ea3b6d455735d5b9b4。94採用獨立audit SHA 946ad4a7ef74c790b032fb77baa7098105d56ef1aeffd579aca7069491f827f8核對50/50現行來源相符，舊portrait四張仍hold。 / 新增97两张恍然大悟眨眼，待确认。 / Two intact eureka blink originals97 await owner review; no matting or RGB edits. / 97のひらめき瞬き2原画は確認待ちです。

接續成果：95 四張批准眨眼離線去背已完成，receipt SHA 9657f64d1140971d502861d2a0656b4e738d3355af75880a071350f22d153418，root-verification SHA 2f363c933e4a290b1a9d2c758608934a5ecb86f8d36b17eda97eab1e883baf44；root 已看全部四色背景，原生尺寸 1024×1536、RGB 與 alpha sidecar 核對零差。32 writer/build 已收錄95：authority SHA 5ceae5b4da907669dc11ee21ad7ef2ea20ececb3538800194e85892f47108aca，receipt SHA 0ffd1afc251fa7260983b840b5dfdeed7a4a011be0ace6424ddc3a65854e0e7e。82 candidate02-revision02 仍有規則孔洞及混入區域，receipt SHA 4c5b6fef5b3faa0392a99ac40bed377ef09b0aaf79c029354135da822a389f60，未選層；改做單次相同來源與點提示的 CPU float32 對照以診斷。96 隔離 stage 接續核對現有實際 renderer 的左右90六態眨眼接法，不可拿閉口圖補成假12嘴型。使用者「繼續作業」不等於對89/90尚待審原圖的視覺批准。 / 95四张已去背并核对，82改做CPU诊断，96接续实际渲染。 / Batch95 is verified; CPU diagnostic82 and the six-state runtime96 continue. Reviews89/90 remain pending explicit visual decisions. / 95検証済み、82 CPU診断と96実描画を継続し、89/90は確認待ちです。

繁體中文：使用者 call_5Zl6342LENBwU00bvh13v2xM 回覆「4 張都採用」，94/owner-approval.json SHA 4d7bea9fb91bb53d750ecd75bffa3335d8d7088be92894185f453ac63f3a8757 固定新左右 90 度完整全身半閉眼與閉眼各 2 張。32 權威已登記：歷史人物批准 56、被新版取代 6、現行槽位 50、舊側臉眨眼 hold 4、可用 46，另有衣裝來源 1。94 全身眨眼批准不能恢復舊側臉眨眼。95 離線去背接續作業；92 的兩張完整 90 度全身去背已完成，receipt SHA 47dea8a7d0e9210c05440f0cacb24f9dcbbf0b709674adfad49f5aec18fda167，原 RGB/尺寸/alpha sidecar 零差，root 看過兩张四色預覽，獨立驗證 SHA 7e632cc5b99a01e4c427d988956f68dcfbff406ee7af49202effc62164bc1220。

89 左側半身 12 態比較頁已提供：75 的 4 張睜眼已採用，85/88 的 8 張新眨眼待確認，HTML SHA 72a82e17fcd66df337cafaf62420620473ff7363ffe9c757365355019697b07。90 四張左右 60 度全身眨眼仍待獨立答覆。82 第一輪衣裝遮罩有內部孔洞，托臉手掌包含多餘臉／袖口／另一手，尚未選用；第二輪語意邊界續做，不能把 SAM score 當作通過。91 實際 none→Hanfu→none runner 已加入 exact requested/effective selection、選定輸出與來源批准鏈核對，區別 1 態 probe 與 12 態完整 coverage；等待合格 82 selected layers，尚未執行。正式素材寫入 0，產品程式未更改，未重跑不相關 pytest。

简体中文：94 的四张新完整侧身眨眼已采用并登记，95 继续去背。92 两张全身已完成保留原像素的去背。89 半身八张与90全身四张眨眼仍待确认；82衣装遮罩需修正，91未执行。正式写入0。

English: Review94 seals four approved complete profile-body blink originals. Authority counts are 56 historical, six superseded, 50 current, four held and 46 available character sources, plus one garment source. Batch92 passed native RGB, size and alpha checks and preview review. Batch95 is in progress. Eight half-body blinks89 and four oblique-body blinks90 await separate owner decisions. First-pass garment masks82 are unselected because of holes and mixed skin regions; runtime91 has not run. No formal asset or product-code writes.

日本語：94の新しい全身横顔瞬き4原画は承認・登録済みで、95の切り抜きを進めています。92の全身2原画は元RGB・寸法・alpha一致を検証済みです。89の半身8原画と90の全身4原画は確認待ち、82の衣装境界を修正中で91は未実行です。正式書き込み0です。

## 2026-09-15 總覽四組共 8 張全部採用

後續即時採用：使用者 call_3S0O3YiBefrh15M8zjm0ySvr 回覆「兩張都採用」，87 新左右 90° 完整全身已封存採用，approval SHA 7e8f85cdf5ae6c29009564ed2330ba83ed090d6d3a4a37bd2598dde0c37e79c8。+90 source SHA b3a4e4203891ea40e3ebe8f9b6d602251fc3677f4ea2ed44d7b738c6a2df1534、−90 SHA ac44c0d96c2cac1bd999a1cab1ea79b370da59b22f0f4bde1dad05a86d34f1e3，原生 1024×1536 RGB。55/60 舊全身移入 superseded；現有歷史人物批准 52、已取代 6、現行槽位 46、hold 舊側臉眨眼 4、可用 42，另採用衣裝來源 1。92 雙張去背等待 82 釋放 GPU。86 四張完整 ±60 全身眨眼已完成且 root 看過，90 比較頁待使用者，HTML SHA fde748c2e22fedd88714e804657705992c1a7b4f089b8a8e0bc2e9c7ff3ec303。85 半身偏側閉口半閉眼/閉眼完成，88 六張說話眨眼及93四張新90全身眨眼接續製作。 / 新90度全身已采用，90比较页的四张60度眨眼待确认。 / New complete profiles87 are accepted; four oblique full-body blinks in review90 await owner review. / 新版90度全身87は承認済み、90の60度全身瞬き4原画は確認待ちです。

繁體中文：使用者於 32 總覽回覆「我全部確認過了，都沒問題了」，採用 71 新左右 90° 側臉 2 張、75 半身偏側 small/A/O 3 張、77 新托腮漢服 1 張、79 左右 60° 完整全身 2 張。80/owner-approval.json SHA fe2e12b7369237ed9c431fbf0f03fcecc043c886c2a98498d920de3106a91ad2 封存當時四頁與總覽；只採用新來源，歷史有疑慮對照不恢復。7 張人物來源 + 1 張衣裝來源分列，歷史人物採用 50、已取代 4、現行 46、舊 90° 衍生仍 hold 6，未 hold 可用 40。全套 24 全身角度／7 半身動作／4 妝容仍在整合，正式寫入 0。

81 離線批次去背 8 張 exit 0，模型 revision 5d6b6f8adcb5b417c871b1d84ceaae9871355b7f。receipt SHA ffe1159a16e3cd53eb1f040b40bb21171ae571f8688ac536c8f11517eecf3712；root 逐像素核對原 RGB、原生尺寸、alpha sidecar 全相同，獨立核對 SHA aa905cf76e03efd2d9ceeaa1b6306edd4765b7719b0baacb5474daac9cbd2979，已看過全 8 張四色背景預覽。82 新托腮衣裝分層進行中。83/84 新完整左右 90° 全身已生成待審，87 比較頁並排 71 已採用側臉；85 半身偏側閉口眨眼 2 張、86 完整左右 60° 眨眼 4 張續製，未批准前不去背。32 沿用 persist_progress.py → build_review.py，不改成只讀摘要。產品程式未變，未重跑相同 pytest。

简体中文：总览四组 8 张新原图全部采用，80 封存批准；81 去背与原始像素核对通过。旧 90 度衍生 6 张仍暂停。新完整 90 度全身、眨眼及托腮可拆衣装继续，正式写入 0。

English: Batch80 seals owner acceptance of eight new sources from reviews71/75/77/79, comprising seven native character originals and one garment source. Offline batch81 preserves all eight native RGB arrays, dimensions, and alpha sidecars; root reviewed all four-background previews. Six older profile derivatives remain held. New complete profile sources83/84 await review87; cheek partitions82 and blink originals85/86 are in progress. No product code changes or formal asset writes.

日本語：総覧の新規8原画がすべて承認され、80に保存しました。81の切り抜きは元RGB・寸法・alpha一致を検証済み。旧90度派生6原画は保留を維持し、全身・瞬き・着脱衣装を続けています。正式書き込み0です。

## 2026-09-15 左右 60 採用後的接續作業

收尾入口：32 總覽現有18個比較頁入口、4組待確認；HTML SHA 8b0603ca83fc8a507b08a458632f7afb44a3968210cbe3518812d710acc3d713，receipt SHA cad91ec8dbd68ab61e9c6009a301abc5771c17811837fcce31498e469d868934。persist/build 退出碼均0，歷史採用43、已取代2、hold8、可用33，正式寫入0。32/persist_progress.py 原有更新18/I06/O/14權威與進度的程序已保留；助理曾改為唯讀摘要而省略此行為，root 從原工具輸出恢復完整255行原稿（32/persist-progress-before-rewrite-log-11119.py，SHA608638...c9214），把新增唯讀摘要獨立為snapshot_progress.py並由原入口最後呼叫。後續沿用persist_progress.py→build_review.py，勿只執行snapshot取代權威更新。托腮12張原圖採用保持有效，72退回只針對舊漢服接合。 / 32总览4组待确认，原权威更新流程已保留。 / The original authority writer is preserved and invokes the new snapshot exporter last; four review groups remain pending. / 従来の承認・進捗更新処理を維持し、4組が確認待ちです。

本段最新進度：74 托腮漢服完整原圖已完成，source SHA ff21cfd9d49c1d0c8bb551b9c40616a227483a127e5337f6acc012f6b343a37f；root 看過肩線/手腕及臉，77 比較頁 HTML SHA fd60e43a81ea164ae03849be0f7760618a6fda0d3eab6d1a411559626f3daa3e 已送使用者，仍待採用。76/78 兩張完整灰色全身也已完成：+60 SHA e10a43146c5711098c46b82fa415d8a25c8f2257421fc332521398528b83a9ae，−60 SHA 7dc1cc6d49db179cd1a52da6bd8aa19c1465efb9c9f6b3f12246c131711a5cbd，皆1024×1536 RGB。79 比較頁 HTML SHA 84d37852bab8c038d8f14166e2fbd990c6f997ab01a8f75ba3fc06473e25c63a 已並排各自68已採用五官，待 owner 評斷縮至全身後的鼻口/眼神、頸肩/衣裝。71、75、77、79 共四組審閱問題仍待回覆；不得把待確認的新原圖當作已批准。所有來源以完成通知後的固定審閱副本消費；正式寫入仍0。 / 最新74、76、78完整原图已完成，77与79已送审；71、75、77、79均等待用户，正式写入0。 / Complete sources74,76,78 are ready; reviews71,75,77,79 await owner answers. No formal writes. / 74・76・78原画が完成し、71・75・77・79は所有者確認待ち、正式書き込み0です。

繁體中文：68 兩張新 60° 已採用；73 離線去背 exit 0，source RGB/alpha sidecar 逐像素核對通過，保留 +60 的 1102×1427、−60 的 1102×1428。receipt SHA bdcf0caae3dc46a98795fa9131902b43f4f5f58e6b2829aeb07de40f5e3afa9e，獨立核對 SHA 784b631bb51bc7279356ab9319c80bc295ad9e17b01a82e3122196ce1ee164d9；root 看過兩張四色背景預覽。新 ±90 的 69/70 已完成，71 比較頁第三欄待擁有者判斷，尚未去背或採用：+90 source SHA 50b695e42f5415999a544299137967a9940711fbccf72473d14746e3bdcbb71a，−90 SHA 1fc0e4c734407bb99527eb0d43c7e3f0749c50f3dd4aa37a5307d0ef98a9709c。

托腮 57 已完成 12 種原生 runtime 與獨立來源核對；72 衣装 none→Hanfu→none 的回復零差，但 root 親看 Hanfu 發現肩帶/裸肩露出與水平手腕重複，已寫 root-visual-review.json 退回外觀，不能擴成 12 張或正式安裝。74 依批准的 30 托腮完整灰素體重新穿回同款雙前襟白劍紋漢服，僅原圖製作中。62 半身偏側小開口/A/O 已完成 root 與獨立目視，75 比較頁待使用者採用，HTML SHA 6d203ae1742e9cfbcd1898083e5abfb933108f55dfd566ff95491ba5fbff1e57。76 開始以 68 的 +60 批准臉及既有同角度身體/衣裝製作完整全身原圖。所有新候選均尚未批准；正式素材寫入仍為 0。

简体中文：新版左右60已采用且完成保留原像素的去背；71两张90与75偏侧三张说话待确认。72托腮汉服有肩线/手腕重叠，退回完整原图重制。74汉服与76全身原图制作中，正式写入0。

English: Revised 60-degree sources are approved and matted with original RGB and native dimensions preserved. Profile review71 and three half-body speech originals in review75 await owner acceptance. The actual cheek wardrobe probe72 restores the bare frame exactly, but its dressed output visibly misaligns shoulders and duplicates a wrist; it is rejected for appearance. Complete source work74 and76 is in progress. No formal asset writes.

日本語：新版左右60度は承認・切り抜き済みです。71の左右90度と75の半身発話3原画は確認待ち。72の漢服は肩と手首の重複で外観不合格、74と76の完全原画を制作中です。正式素材の書き込みは0です。

## 2026-09-15 正側面角色一致性疑慮

左右60最新採用：call_Gbi5ZjIArdNxdz4MLcqpm3lH「兩張都可以採用」。68/owner-approval.json SHA c618c1a62a09e44936c9349f8dd6d328bceb344456704ef8b3f0a5101f88449f，reviewed-at-approval 封存 HTML SHA899e7f19dc967d9bb7179ee7740a3f5117de36fbf1435be2b857147818f9063f。後續只取68/plus-060-new.source.png SHA b633f578b6d828bd1af1f7a0bc361467ed1dbd3101f733788cc3e14574897e32 與68/minus-060-new.source.png SHA9a46d0d90aafac0550b7bd6c1904c3a19b0e6aba9c989e0c6590722b5fdc3623；後者原生1102×1428已批准，不要因一列高度差重製。67原v02工作檔曾因助理尺寸重試換成未批准84a00e版本，68批准copy始終未變；generation lineage已改指保存的exec-50a433原始收據，記錄修正前approval於68/approval-record-before-lineage-correction.json。之後必須等助理明確完成再取其生成檔送審；所有已送審／批准複本不可變。69/70以68固定來源重繪±90。歷史批准原圖43，舊±60兩張已被新版取代，仍有8張舊90相關來源暫緩使用；正式寫入0。 / 左右60新版已采用，后续只引用68封存副本，90继续重绘。 / Revised +/-60 originals are approved; immutable review68 copies are the authority. The approved minus60 image is natively 1102x1428; never regenerate to remove a single pixel row. Profiles69/70 are in progress. / 左右60度新版が承認され、68の固定コピーを参照して90度を再制作中です。

最新回覆：使用者目測明確指出 +60、+90、−60、−90 有疑慮。65/owner-feedback.json 已記錄，32/global authority 的 source_use_holds 暫緩 10 張既有側面相關來源的安裝與衍生（41 張歷史批准中 31 張不受本次暫緩影響）。既有批准紀錄保留；不可拿它們覆蓋最新疑慮。只以 18 正面與 27 同側 30 度作參照，66/67 先重繪完整左右 60 度，確認連貫後再做 90 度；61 側面眨眼暫不續用。其餘正面及托腮整合繼續。 / 用户明确标记四个角度有疑虑，10 张相关旧来源暂停使用，先以正面和30度重绘左右60度。 / The owner explicitly flagged +/-60 and +/-90; ten previously approved related sources are held from installation and derivative generation. Redraw +/-60 from frontal and same-side 30-degree authorities first, then address 90 degrees. Other approved work continues. / 所有者が±60度と±90度を指定し、関連10原画は使用保留。正面と同側30度から60度を再制作し、確認後90度へ進みます。

繁體中文：使用者澄清 ±90 與 00 的疑慮是「是否仍是同一個墨寒」，不能以側面比較漂亮作為一致性通過的理由。Root 與 Luna 唯讀檢視 18、27、31、36、64：共通五官仍存在，鼻唇與下巴輪廓有疑似重繪漂移，角度與光影影響尚不能排除。65/review.html 以既有高解析原圖排成兩組 0→30→60→90，8 個來源複本 byte-identical；assessment.json 記錄判讀限制。使用者未撤銷個別批准，整套跨角度一致性仍未完成確認，正式寫入 0。61 的 +90 全身兩張眨眼與 62 的偏側三張說話已生成、待目視；57 托腮 12 種 runtime 完成，root 看過 A 閉眼預覽，獨立來源核對及衣裝來源盤點續行。

简体中文：用户关心的是正侧面是否仍为同一墨寒。共通特征存在，但鼻唇与下巴有疑似重绘偏移；65 用现有原图比较 0/30/60/90，未撤销单图批准，整套一致性尚未确认，正式写入 0。

English: The owner clarified that recognizability across front and profiles is the concern. Shared features remain, but nasal/lip/chin contours may have drifted during redraws. Review65 compares intact existing 0/30/60/90 sources. Individual approvals remain; whole-set consistency is unconfirmed and formal writes remain zero. Outputs 61/62 await visual review; bare cheek runtime57 is complete with independent checks ongoing.

日本語：所有者の懸念は正面と側面で同じ墨寒に見えるかです。共通特徴は残っていますが、鼻・口・顎の描き直しによる変化は未解決です。65 は既存原画の角度比較で、個別承認は維持、全角度の整合確認と正式導入は未完了です。

## 2026-09-15 托腮完整表情採用與實際漢服選擇接合

繁體中文：使用者 call_bmhw1fx9Iag2dP2XJuN1kg6Y 回覆「8 張都採用」，52 已逐 byte 封存當時 review/job/source receipt，owner-approval SHA c01e35d9904264ca4416db0b9f6a283124b2fb635ced0cb675e51ae93d7b104b。托腮 12 種完整原圖齊備；56 的8張離線 BiRefNet 去背已完成，root 獨立核 SHA、1254²、原 RGB 零差、L=RGBA alpha、alpha 0..255，receipt SHA 1e54cb094b34e8bf7033112c652872f45b6dd3b1414dc2fe2cb2c950f6c92776。57 正以完整原圖接原生托腮 runtime，非眼嘴局部拼貼。

實際 ActiveOutfitOverlay 的53 probe查出正式 reviewed-garments manifest 只有 cheek-rest，front-crossed 因而走舊官方 outerwear，產生衣領／胸前／手臂殘影。Root沒有改現有替換 guard 或弱化檢查；candidate-04-reviewed-stage在隔離 asset root加入既有 reviewed-native-garments schema，用已批准50整張灰素體及25衣服／手部圖層。真實官方衣装選擇 installed，none→Hanfu→none回切，共36張（12狀態×3）與批准50 fit顯示差≤2、alpha差0。receipt SHA eeaa037f98e0d06680728c2398b20128999d45d84337c0ee59fc8995dff6abf4。root看過A睜眼漢服及O閉眼回復灰素體，無原領袖殘片；其餘以像素對照覆蓋。此結果只限隔離staging及該衣装，其他髮型／髮飾／妝容仍待整合。獨立Luna來源追蹤在53/diagnosis-03/。

+90完整全身54獲使用者call_bc9Qy7vqtYEfwVzI5deEn43Y「可以採用」，55 owner-approval SHA7654cb5d8824de8c3c2013bfd209163f8b391c61336ca8a3bbdd4eac60bedd49，批准原圖SHA96b39199214c2fae6ab46554c1113d516b3067ae8926d26d62e26a6a7f3e510c。59單張離線去背保留1024×1536原RGB，receipt SHA0b020f6e1c3c869b1a9e286c2927c01f59895c83b32d8bff9ddb94f9e5645f14；root已看四色背景預覽。-90完整全身58也獲call_5LLsdWzLggA60XqVD8NZ8FAf「可以採用」，60批准SHA a7be83ab2dafb3eb7a5d62278a2cf9d010bd45b82679691fdf68e472d3227db3，63去背receipt SHA e4b42fd89b2bf972168d07d18cdb94e36f648646a5c547c43c456cb73f3581a5；61開始以批准54獨立生成半閉眼／閉眼完整全身，未批准前不去背。

當前41張已批准原圖，另12全身正面接合及12修正半身接合。全身24方向、半身7動作、四妝容與可拆外觀範圍持續，整套正式寫入仍0。產品碼本段未變；沿用同一工作階段已通過42項相關pytest及全repo Ruff，未為資料接合重跑相同測試，未宣稱全repo pytest全綠。既有sidecar/outline差異仍未解除。

简体中文：托腮8张新眨眼全部采用并完成原RGB不变的离线去背，12状态齐备。正式front-crossed缺少reviewed garment记录导致旧衣装残影；隔离staging通过既有manifest契约和真实衣装选择，36张none／Hanfu／none输出与批准版本一致。+90完整全身采用且去背，累计41张批准原图；其余侧面动态、7动作、四妆与正式接入仍在进行，正式写入0。

English: The owner accepted eight new cheek blink originals, completing twelve cheek states; offline alpha matting preserves their RGB exactly. The real wardrobe probe exposed a missing front-crossed reviewed-garment manifest entry. Existing production APIs with an isolated exact-source manifest reproduce the approved body/clothes/hands across 36 none/Hanfu/none outputs, displayed delta <=2 and alpha delta 0. The complete +90 full-body source was also accepted and matted, bringing approved originals to 41. Remaining expressions, angles, four makeup looks and detachable appearance are still in progress; no formal asset writes. Prior 42 affected tests and repository Ruff remain the relevant code evidence; no new product code or full-repository pytest claim.

日本語：頬杖の新規瞬き8原画が承認され、12状態が揃いました。RGBを保持した切り抜きも完了しています。実際の衣装選択でfront-crossedのreviewed登録不足を確認し、既存契約を使う隔離環境で着脱36出力が承認済み合成と一致しました。+90度全身原画も承認・切り抜き済みで原画は41点です。他の角度・表情・4化粧・着脱外観と正式導入は継続中、正式書き込みは0です。

## 2026-09-14 半身完整表情接合採用與四耳修正

繁體中文：托腮 SMALL/A/O 三張原圖（review46）獲採用，原圖批准總數 31；47 去背保留原 RGB。半身 front-crossed 12 種灰素體／漢服接合先於 review43 獲採用，後在實際 runtime48 發現兩側舊耳殘留。原因是 correction03 保留完整舊頭 alpha，不能以新頭可蓋住舊頭為假設。root 50 改成整頭替換：舊 body alpha y≤620 清零，620..638 恢復；新頭 alpha 沿用已批准來源且從640開始頸部淡出。638以下與原接合逐像素相同，24張灰／漢服實際輸出已核對。使用者 call_IQuRHTvuZMiiJTrQvHI0AEha 回覆「可以採用」，approval SHA 6f2fe9d85c5be31f4ab8c305ad219c63dc67e02d43b419a48000d31405e85fed。43/48 的舊接合已有 superseded 記錄；原始31張來源批准保持有效。現在為全身正面12種、修正半身正面12種接合採用；全域正式素材寫入仍0。

半身完整表情模組新增 strict manifest/source snapshot、整張表情+獨立外觀、依顯示端點 cacheKey 的眨眼。39項測試後，三項獨立審查問題已補：contexts擴到168、atomic adapter測試、每pose四family bindings完整驗證，42項affected regression與全repoRuff pass。另全身appearance replacement-order修正曾通過95項affected tests及2項錯誤邊界測試。完整衣櫃store/core restoration與所有四妝尚未驗證，不可把staging adapter認成正式全路徑驗收。詳細契約見 docs/complete-halfbody-expressions.md。±90 fit24 candidate06仍有頸肩接縫，±30 fit44 candidate08因耳頰殘片/接縫退回；不得直接套其餘角度。接續托腮說話眨眼、各角度原生接合與可拆外觀。

简体中文：托腮3张说话原图采用后共31张批准原图。半身12种接合出现旧耳残留，已用完整头部alpha替换修正，24张灰素体／汉服输出再次获采用。全身正面12种及修正半身12种接合有效，正式写入0。半身完整表情、显示端点眨眼及manifest校验完成42项相关测试，完整衣柜与四妆整合尚未完成；侧面／偏侧接缝仍需修正。

English: Approved originals total 31 after the three cheek speech sources. The first twelve frontal half-body fits exposed the old ears beneath the new head. Review50 removes the complete old head alpha and preserves the approved canonical head; all 24 gray/Hanfu runtime outputs were reviewed and the owner accepted the twelve repaired states. Prior fit43/runtime48 are superseded for installation. Twelve full-body frontal fits and twelve corrected half-body fits are approved; formal writes remain zero. The optional complete-halfbody provider passed 42 affected regression tests and full-repository Ruff after independent-review follow-ups. Full wardrobe-store/core-restoration and four-look integration remain unverified. Profile/oblique neck seams remain rejected.

日本語：頬杖の発話3原画が承認され、原画は計31枚です。半身12状態で旧耳が露出する問題を旧頭部全体のalpha置換で修正し、灰素体／漢服24出力を確認後、所有者が再承認しました。旧43/48接合は置換対象として無効、全身正面12・修正半身正面12状態が承認済みです。正式書き込みは0。半身表情機能は関連42テストとRuffを通過しましたが、衣装ストア・既存素体復元・4化粧の統合、および側面の首肩接合は未完了です。

## 2026-09-14 總覽全部批准：28 張來源與 12 張全身接合

繁體中文：使用者於 canonical-global-progress-32 總覽確認「我全部批准確認」。本批採用 27 的左右 30°、36 的左右 60°、30 的半身偏側與托腮、38 的四個半身動作，共 10 張新原圖；另採用 40 的 12 張全身正面接合。加上先前批准來源，現有 28 張原圖。batch SHA256 4298dac598ee84fbddb95f613ab26058b24e2cc83c286a85b867fa7bd76b062a 保留當時審閱快照，各組 owner-approval.json 記錄採用狀態。全身 24 方向、半身 7 動作、四妝容與可拆外觀仍在接合；未列於總覽且主線退回的半身正面領口接合須修正。正式素材本次對齊寫入數仍為 0。狀態以 scratchpad/mohan-canonical-global-progress-32/coverage.json 與 hairline-18/global-authority.json 為準。

简体中文：用户批准总览本批 10 张原图及 12 张全身正面接合，累计 28 张原图。24 个全身方向、7 个半身动作、四种妆容及可拆外观继续整合。未列出的半身领口接合不在本批批准范围；本次正式素材写入仍为 0。

English: The owner approved all listed review candidates: ten new originals and twelve frontal full-body native fits. There are now 28 approved originals. Global integration still covers 24 full-body views, seven half-body actions, four makeup looks and detachable appearance. The unlisted, rejected half-body neckline fit remains under correction. No formal asset writes in this alignment batch.

日本語：一覧の新規原画 10 枚と全身正面の接合 12 枚が承認され、承認済み原画は計 28 枚です。全身 24 方向、半身 7 動作、4 化粧および着脱可能な外観の統合は継続中です。一覧にない半身の襟元接合は修正中で、本整合作業での正式素材書き込みは 0 です。

## 2026-09-14 全角度對齊接續：12 張正面與左右側面已採用
繁體中文：使用者提醒全身及半身各角度均須對齊。canonical-speaking-blink-23 的 6 張說話眨眼全部採用，正面共 12 張來源固定；22/26 去背檢查原 RGB 與尺寸保留。canonical-profiles-31 左右 90° 完整原圖獲「兩側都採用」。canonical-turnaround-27 的左右 30° 與 canonical-halfbody-review-30 的偏側／托腮新原圖尚待答覆。全身 24 方向、半身 7 動作逐項狀態在 canonical-global-progress-32/coverage.json，尚未全數對齊或正式安裝。半身 front-crossed fit25 領口灰缺口經 root 退回；完整表情替換的 soft-alpha 混合缺陷交由 native_blink 修正。保留各動作手勢、四妝容與可拆外觀要求。

简体中文：正面 12 张与左右 90° 来源已获采用，左右 30° 及偏侧／托腮尚待确认。24 个全身方向与 7 个半身动作继续对齐；领口缺口和软遮罩混合问题修正中，尚未完成正式替换。

English: Twelve frontal expression sources and both 90-degree profiles are approved. The 30-degree pair and two half-body poses await owner review. Global coverage remains 24 full-body directions and seven half-body actions; native fitting, soft-alpha blending correction, detachable appearance, four makeup looks and formal installation are incomplete.

日本語：正面 12 原画と左右 90 度が承認されました。左右 30 度と半身の横向き／頬杖は確認待ちです。全身 24 方向・半身 7 動作の整合、襟元と半透明合成の修正、独立外観と 4 化粧、正式導入は未完了です。

## 2026-09-14 原漢服五官基準與新髮際線：六張完整表情已批准

使用者指定原漢服图的五官為全域基準，要求全身所有角度、半身所有動作與四款妝容均對齊。固定來源 canonical-face-gray-16/canonical-face.source.png（1744cf41…）；初次灰素體 16 因額頭過大退回，降低髮際線的 hairline-18 原圖（462352f3…）已獲「可以採用」。鼻翼、人中、上下唇厚薄、嘴角走向與下巴比例也納入檢查；御姊圖 12 只保留髮際線參考用途，不能取代原漢服五官。

新 canonical-small-19（0ed1a452…）使用者以同 SHA 附件確認「這張我是真的覺得沒問題」。canonical-rest-blink-20 的 HALF/CLOSED 獲「可以採用」；兩張原尺寸為 1102×1428，保留原檔未裁切。canonical-vowels-21 的 A/O 獲「可以，這次很棒」。以上 6 張完整來源與所有批准記錄固定於 scratchpad/mohan-canonical-hairline-18/global-authority.json。舊灰素體的歷史批准仍保留，但其表情家族不能當作新五官對齊完成。

三位 Luna Max：plus090 在 canonical-approved-matting-22 單次離線去背 6 張已批准原圖；native_blink 修復 complete-expression-code-review-01 指出的手袖動作遺失、收口過渡與輸入契約問題；minus090 完成全身來源盤點，後續接合新完整頭部。全身 24 view、半身 7 action 的來源稽核在 canonical-face-alignment-17，盤點不等於角色外觀驗收。+90 native-fit-01 仍有額頭灰缺口與 only-garment 後頸／肩背破口，不可正式採用；−90 fit03 頭髻及衣装接合改善，仍須納入新全域五官比對。正式牙齒新檔仍 0，既有有效安裝交易未變。

English: The original Hanfu face is the global anatomy authority across all views, actions and makeup. The owner accepted the corrected hairline and six coherent canonical sources: neutral open/half/closed and SMALL/A/O open. Preserve actual generated sizes and approved originals. Matting, speaking blinks, global fitting, code-review fixes and formal integration remain pending. Previous source approvals are historical evidence, not acceptance against this new authority.

日本語: 元の漢服の顔を全角度・全動作・全化粧の基準とし、修正した生え際と閉口の開眼／半閉眼／閉眼、SMALL/A/O の計 6 原画が承認されました。実際の画像寸法を保持します。切り抜き、発話中の瞬き、全体の接合、コード修正と正式導入は未完了です。

简体中文: 原汉服五官成为全角度、全动作与四款妆容的统一基准。用户已批准较低发际线及闭口睁眼／半闭眼／闭眼、SMALL/A/O 共 6 张完整原图。保留实际尺寸与历史批准，去背、说话眨眼、全局接合、代码审查修正和正式安装仍待完成。

## 2026-09-14 完整說話表情：A/O 已批准，眨眼契約修正中

使用者批准灰素體完整大開口 A 與圓唇 O「兩張都採用」，精確來源與批准在 scratchpad/mohan-complete-gray-vowels-10。A/O 已單次離線 BiRefNet 去背，來源 RGB 保留。SMALL/A/O 全頭原生框在 scratchpad/mohan-complete-expression-frames-14/open-states，等比縮放 51/151，頸部 351–377 列銜接，377 列以下原素體 RGBA 不變；目前是備妥的動畫來源，尚未宣稱实际 renderer 已接入。

同款 SMALL 半閉眼／閉眼在 scratchpad/mohan-complete-small-blink-11，自然閉口在 scratchpad/mohan-complete-rest-12，均仍待擁有者裁決。眨眼稽核實測 OPEN/HALF/CLOSED 三張 SHA 完全相同，確認舊嘴型路徑覆蓋了眨眼；native_blink_luna_max 正修正明確完整表情 state 契約與測試，舊 speech_frames 與 legacy 行為須保留。

側面尚有可拆開關缺陷：−90 fit02 的衣裝誤遮原髮髻，已要求 fit03；+90 hair native-fit-01 四狀態仍皆含藍白衣裝，不能稱為 all-off／hairstyle-only 通過，已要求真實灰素體開關或明示相容性依賴。未增加正式安裝，原有效 8 筆交易／160 次寫入／156 個唯一目標維持；撤回的嘴部拼貼正式檔仍為 0。

English: The owner approved the complete gray A/O portraits. Their RGB-preserving mattes and three complete-head native frames are prepared in scratch. Blink and neutral sources await owner decisions; the renderer's complete-expression state contract is being fixed. Both profile appearance switches still have defects. No new formal installation.

日本語: 灰色素体の完全な A/O 表情が承認され、RGB を保持した切り抜きと全頭部フレームを準備しました。瞬きと閉口原画は確認待ちで、完全表情の状態契約を修正中です。側面外観スイッチに未解決の欠陥があり、新しい正式導入はありません。

简体中文: 用户批准灰素体完整 A/O 表情，已准备保留 RGB 的透明原图及全头部帧。眨眼和自然闭口原图待确认，完整表情状态契约修正中；两侧外观开关仍有缺陷，未新增正式安装。

## 2026-09-14 最新批准：獨立 +90° 髮型與完整灰色說話表情

使用者先退回去髮飾整人像的五官，後批准獨立完整髮型「可以採用，接回原人物」。來源 scratchpad/mohan-plus090-hair-05/hairstyle.source.png，SHA 4b304c00f482e350830f16837aeff9c353b519605d0b81c20f16e326c9a5e37d；owner-approval.json SHA 1addde182beaae60aa518b0eb29a93dee41d3c80629539069a1d4cacc6976883。此批准可繼續去背、分前後深度與實際獨立開關接合，原人物以已批准 +90° sword 原圖為準。退回的 17c 整人像及首張假棋盤背景髮型 04 均維持退回。新短路徑比較頁已在瀏覽器清單顯示正確標題，內含 2 張與原檔 SHA 相同的 PNG。

使用者也回覆「可以採用完整表情」，批准 D11/complete-expression-gray-08/small-gray-complete.source.png（d1c04dedce6de086c32b854e761e8d62631a9a653202091530abcb106e277e48）；owner-approval.json SHA 1db74ee6532ec7dd9404a9c901cda03dfeddc3263c3f84466a59c3fd761b92e6。Root 的首張實際正面合成在 scratchpad/mohan-complete-expression-fit-09，整張皮膚表情（額頭、眉眼、臉頰、嘴、下巴、頸部）只用單一等比轉換，沒有單獨扭曲牙齒；source RGB 保留。僅完成睜眼 SMALL／REST 試合成，完整頭耳接合、來源相容眨眼、A/O、四款妝容與正式安裝仍待處理。不能恢復先前已撤回的 13 個 mouth-only 檔。

3 位 Luna Max 的有效指派：plus090 正在 native-fit-01 接合新完整髮型；minus090 正在完整衣裝 fit-02 修正背肩露皮膚與長髮開關；native_blink 已完成 sidecar 唯讀稽核，正在 outline-remediation-plan-01 釐清同來源完整輪廓修復方式。sidecar 契約稽核明確發現 16 張額外 blink 與 15 張缺少 outline，沒有任意修改正式檔或放寬測試。正式有效交易仍 8 筆／160 次寫入／156 個唯一目標，新口腔正式檔 0。

English: The owner accepted the separate +90 hairstyle and the complete gray frontal speaking portrait. Both exact approvals are saved. Hairstyle fitting preserves the original approved character. The first complete-expression SMALL runtime is a scratch candidate; blink, A/O, makeup and installation remain pending. Returned mouth-only files stay withdrawn.

日本語: 独立した +90° の髪型と灰色素体の完全な話し表情が承認され、原画と承認を固定しました。髪型は承認済み人物へ統合中です。SMALL の初回実行時合成は作業候補で、瞬き・A/O・化粧・正式導入は未完了です。

简体中文: 用户批准独立 +90° 发型与完整灰素体说话表情，原图和批准已固定。发型接回原已批准人物，SMALL 首次运行期合成仅为工作候选；眨眼、A/O、四款妆容与正式安装仍待完成，已退回的嘴部拼接文件保持撤下。

## 2026-09-14 最新：三個嘴型拼接退回，改保留完整表情

最新 +90° 裁決：使用者指出去髮飾整人像「這張五官好像偏移了，不是墨寒」，退回 yaw+090-hair-no-ornament.source.png（17c17acdeba0d573417cc5193d77cfe80ef11fbbb1737caf542be5627901a016）。精確回饋記錄在 wardrobe-sword-02/complete-hidden-surfaces-03/plus090-hair-owner-feedback.json，覆蓋生成當時的待審狀態；該圖沒有拆層或正式接入。已批准原 sword 人物／臉仍有效，後續製作獨立完整髮型，臉與身體固定取自原批准來源。−90° 完整衣裝首次 runtime 仍有背肩裸露及全開狀態缺長髮問題，root 已退回要求實際開關修正，不能報成通過。

使用者先批准 06 原圖、小開口 runtime 11 及 07 A／03 O 原圖，後再指出「這張的嘴型怎麼看起來有點突兀」及「總之這三個表情拼湊起來總覺得不夠自然」。最新裁決優先：SMALL/A/O 只移植嘴部的接合全部退回；原本完整原圖的齒列與御姊神情批准仍保留，不能將舊小開口批准當作目前接合通過。

本輪先以共同 installer 新增 13 檔（6 viseme 嘴型、6 口腔妝容保護遮罩、1 provenance），再按 A 回饋暫時用 SMALL 覆蓋 3 檔。完整回饋後已精確核 SHA，將這 13 個新檔存入 scratch archive 並撤下；沒有刪除原有正式檔。16 次歷史寫入與撤回分別保留，仍有效的原 8 筆交易／160 次寫入／156 個唯一目標維持原狀。正式原生新牙齒素材現為 0。完整證據位於 oral-dentition-source-01/approved-dentition-native-copy-11/{installed-backup-04,a-fit-withdrawn-05,mouth-only-withdrawn-06}。

只貼整臉的 complete-expression-fit-07 也由 root 退回：臉頰旁帶入長髮像素。接著用內建 imagegen 將已批准 06 完整人物原圖的外觀轉成簡單髮髻／灰色細肩帶素體，保留整體表情作為生成約束，不聲稱臉或牙齒像素完全相同。新圖 complete-expression-gray-08/small-gray-complete.source.png SHA d1c04dedce6de086c32b854e761e8d62631a9a653202091530abcb106e277e48，1187 × 1326，尚未拆層／送新美術測試／安裝。比較頁 complete-expression-gray-08/review.html 已開啟並提出外觀問題，待使用者判斷；不能自行推定通過。

技術能力保留：optional speech_frames 與 speech_oral_masks、按 viseme 選擇原生圖、唇妝後口腔保護、前髮正確遮擋；初始化拒絕空透明嘴型／遮罩，凍結 bytes；atomic adapter 取得快取副本，只有具名 paint_after_makeup 才視為支援該階段。withdrawal 後相關回歸 125 passed / 44.73s / exit 0，全庫 Ruff exit 0。tests/test_pose_atlas_assets.py 的舊 exact sidecar 清單仍失敗（額外 16 張 blink、缺 15 張 body_outline），正在查既有來源與架構記錄，未放寬條件；不可宣稱全庫全綠。

3 位 Luna Max：minus090 正在將已批准無長髮遮擋的完整白劍紋衣裝原圖接回（S/complete-hidden-surfaces-03/yaw-090-garment-complete.source.png，SHA e40dbb84ad77d800aa419d69763fb0af9e0ea4e90621669291e2e41687f830b3，使用者「可以採用」）；plus090 沿用既有無髮飾完整髮型做實際獨立開關；native_blink 停止半身只貼嘴候選，已盤點完整表情來源，現查上述既有 sidecar 契約差異。7 個半身動作仍全數在範圍內，不能只完工正面全身。

English: The owner returned all three mouth-only fits as unnatural. Their 13 newly added formal files were archived and withdrawn, preserving all pre-existing assets. The approved original portraits remain references. A new complete gray-base small-speaking portrait is pending visual review. Related checks: 125 passed; repository Ruff passed. A pre-existing exact sidecar-list gate remains unresolved. Profiles and all seven half-body actions continue.

日本語: SMALL/A/O の口部分だけの合成は不自然として差し戻され、新規の正式 13 ファイルを保存して撤去しました。既存素材は保持しています。完全な表情を維持した灰色素体の新原画は外観確認待ちです。関連 125 件と Ruff は通過、従来の補助画像リストの不整合は調査中です。

简体中文: 用户退回三个仅移植嘴部的接合，已归档撤下新增正式 13 文件，未删除既有素材。原本批准的完整表情仍作为参考；新灰素体完整原图待视觉判断。相关 125 项与 Ruff 通过，旧补充素材清单不一致仍在调查。侧面与七个半身动作继续处理。

比較頁開啟修正：完整說話頁深層路徑長 269 字元，在 app 顯示 ERR_FILE_NOT_FOUND；同內容另存 scratchpad/mohan-complete-expression-review-08.html（121 字元），兩份 SHA 一致 b78b814149bbcd5085be33fe8201c90446eba1e0e949ab69fd77c0e95db8aece。瀏覽器清單已觀察到短路徑標題「墨寒｜完整說話表情」。CUA 不允許 file URL 內容讀取，因此未宣稱 DOM／截圖驗證；比較圖亦已直接顯示於對話。後續新比較頁使用短路徑與內嵌圖，避免重開相同失敗 URL。

## 以下為歷史過程，外觀裁決以上節最新狀態為準

## 2026-09-14 牙齒須配合御姊神情

本節最新進度：root 看過 05 後判定眼神變化仍過於保守，因此依相同原正面來源再製作整體眉眼與嘴型協調的 06。最新比較頁是 oral-dentition-source-01/poised-gaze-06/review.html，三欄為原閉口／04／06。06 完整原圖 SHA ae6537aa37e4d3f19a901907ba1bacd280cd3008842fb5f41ec7e9be7ba237a1，1187 × 1326；完整提示及來源見該目錄 generation-inputs.json。06 眼神與嘴型需作為完整表情共同檢視，不能只移植牙齒又丟失其眉眼搭配。06 外觀裁決待回覆；05 保存為未採用候選，正式素材未寫入。

4 張已批准灰色全身 HALF/CLOSED 已完成單次離線 BiRefNet，來源批准固定為 18d9948d…2a8，RGBA 均 1024 × 1536 且原 RGB 保留。收據在 approved-two-piece-gray-alignment-01/whole-native-motion-binding-03/local-alpha-01/receipt.json；正在準備原生眨眼 staging。−090 服裝全開合成的白裙／內袖／手腕／鞋缺口已修正，髮際細灰邊確認來自原始 matting；preview-only 全開遮罩尚須改為實際每項外觀開關的 runtime 路徑。

English update: Version 06 visibly coordinates relaxed upper eyelids and the mouth; it is the current pending owner review. Version 05 remains an unaccepted candidate. Four previously approved gray blink sources completed one offline matting batch and proceed independently to native blink staging.

日本語の更新: 現在の確認対象は眉眼と口元を合わせた 06 です。05 は未採用候補として保存しています。承認済み灰色まばたき原画 4 点のローカル切り抜きが完了し、別途統合中です。

简体中文更新: 当前待确认的是眉眼与嘴型协同的 06，05 保留为未采用候选。已批准灰色眨眼 4 张已单批去背，独立继续原生接入。


使用者明確退回 mature-expression-revision-04，原句「我覺得還是超可愛，墨寒的牙齒應該要和整體表情搭配，透露出一種御姊感覺」。前一版單純減少露齒量未達標；04 receipt 已更新為 owner_requested_poised_expression_revision，先前 B 款選擇保留歷史，不等於新嘴型可以正式採用。

root 以原本已批准閉口正面為唯一影像參照，重新製作整臉說話提案，整合沉穩眼神、放鬆嘴角、俐落唇形與較平衡的自然齒列。完整原圖在 oral-dentition-source-01/poised-expression-05/poised-speech.source.png，SHA 0578afe026c96e2a0be6b6d3f633cde22e53ff19952420b98d546b6a492c337d，1187 × 1326。generation-inputs.json 保存內建 imagegen 的完整提示、參照角色、原始生成路徑及使用者回饋；review.html 並列原閉口、被退回的 04 與 05 新提案，附原生整臉／嘴型近照。05 待使用者外觀裁決，沒有去背、拆層或正式安裝。

口腔稽核已落盤 oral-dentition-source-01/runtime-audit-01/{inventory.json,audit.md}：全身 24 個 teeth_tongue 皆透明且目前 renderer 沒有讀取牙齒層；半身 7 動作走原生說話區域，3 組合併 teeth_tongue 沒有獨立上下齒。後續須建立明確逐來源的口腔與牙齒接入。three Luna 持續分側外觀修復，以及已批准 4 張灰色原生 HALF/CLOSED 的離線單批 BiRefNet；這些批准不因牙齒提案被退回而撤銷。正式交易數未增加。

English: The owner rejected revision 04's cute impression and requested coordinated teeth and a poised mature expression. Revision 05 uses the original approved closed-mouth face as its sole image reference. The complete portrait, prompt, hashes and comparison are saved; appearance remains pending and no formal assets were installed. Existing approved profile work continues independently.

日本語: 04 は可愛すぎる印象として差し戻され、歯と顔全体を合わせた落ち着いた大人の表情が要求されました。元の承認済み閉口原画だけを参照して 05 を作成し、比較ページと出典を保存しました。外観は確認待ちで、正式導入数は増えていません。

简体中文: 用户退回 04 的可爱感，要求牙齿配合整体御姐神情。05 仅以原批准闭口脸为图像依据，已保存完整原图、提示、哈希与比较页，等待外观裁决。已批准侧面作业继续，正式交易数不变。


## 2026-09-14 B 牙齒款式已選；張嘴神情需保留成熟氣質

使用者在 dental-options-02 比較頁明確選擇「那就B吧」。B 清秀柔和原圖 SHA 為 202afab6b436352d72a61b789e093aa862d9c792e7aa64b3607170bbbb03f6f2，精確批准紀錄見 oral-dentition-source-01/dental-options-02/owner-approval.json（a54e2b4e…ee1f）。先前牙齒款式待選擇狀態由此選擇取代。

接著直接依 B 原圖製作較大開口及圓唇說話完整原圖，保存於 oral-dentition-source-01/approved-B-motion-03/。使用者隨即指出露齒後「降齡了，看起來太可愛稚齡」，這两張新動態未採用，精確回饋見 owner-feedback.json。B 選擇保留歷史，實際嘴型仍需成熟神情修正，禁止將 B 選擇誤推為全部新動態或正式安裝批准。

root 改以原閉口正面為五官及神情權威，B 僅參照牙齒白度，製作較收斂的完整說話提案。原圖、提示、來源角色與 receipt 保存於 oral-dentition-source-01/mature-expression-revision-04/；比較頁並列原閉口、前一版較大開口、新提案，附同座標整臉及嘴型近看。新提案 1187 × 1326，待外觀裁決，沒有去背、抽取或正式素材寫入。

三位既有 Luna 分別繼續兩側可拆外觀修復與全身／半身口腔入口稽核。口腔初查發現全身 teeth_tongue 為透明佔位圖，仍須固定逐檔證據與 renderer 引用後再實作；不能宣稱已有牙齒說話通路。正式安裝交易數未增加。

English: The owner selected B's tooth design, then rejected the youthful impression of the new open-mouth variants. B's selection remains recorded, while mature expression fitting is pending. A new complete portrait returns to the original closed-mouth identity and uses B only for tooth color. Original sources, prompts and comparison are saved; no formal installation occurred.

日本語: 歯の B 案は選択済みですが、その後の開口原画は幼く可愛すぎる印象として修正対象になりました。元の閉口時の顔と表情を基準に、露出を抑えた新しい話し顔を作成し比較ページへ保存しました。新しい表情は確認待ちで、正式導入は行っていません。

简体中文: 用户选择 B 齿形后，指出新张嘴图降龄、太可爱。B 选择保留记录，新动态需修正成熟神情。新提案以原闭口脸与表情为依据，B 仅参照牙齿白度，已保存原图、提示与比较页，待外观确认，未正式安装。


## 2026-09-14 灰衣原生動態全數批准；新增牙齒款式候選

使用者明確表示「目前比較頁的各張圖片都已經達到我的標準了」，批准 profile-motion-review-02/review.html?revision=gray-native-motion-03 的 7 張完整灰色原圖。精確 7 份來源 SHA 與原句已固定於 profile-motion-review-02/owner-approval-gray-native-motion-03.json（18d9948d…2a8）；whole-native-blink-01、whole-native-plus090-motion-02 及比較頁收據已更新。此批准取代下方歷史待回覆狀態，並未批准新露齒候選。

使用者新增真實口腔與整齊自然亮白牙齒，要求避免過白。root 已直接參照已批准正面素顏原圖產出完整小幅張嘴與較大開口來源，保存於 approved-installation-06/oral-dentition-source-01/。使用者覺得第一版象牙白齒列未符合想像，要求其他選擇；因此再以同一張小幅張嘴原圖製作自然清透、清秀柔和、清晰亮白 3 款，位於 oral-dentition-source-01/dental-options-02/。4 欄原圖／近照比較頁已完成並送交 app 顯示；外觀仍待選擇。完整 prompts、reference、工具與原檔來源在各 generation-inputs.json，未對牙齒候選去背、拆層或寫入正式素材。第一張小幅開口及 3 款替代實際均為 1187 × 1325；正面基準與較大開口為 1187 × 1326，不可宣稱畫布完全相同或默默拉伸。

左右已批准白劍紋衣裝仍在可拆外觀實際合成修復。−090 第二輪仍有灰色髮邊／鞋旁散點，+090 rest-stage-04 仍有髮頸碎片、白衣及鞋口缺口；均未通過 root 整合檢視。原圖批准保留，像素重建吻合不代表合成可採用。正式安裝累計維持 8 筆交易、160 次寫入、156 個唯一目標，本節沒有新增正式交易。

English: All 7 gray native motion sources are now owner-approved and hash-bound. New dental sources and 3 same-mouth style alternatives are saved with prompts and a self-contained comparison, pending the owner's choice. Their real canvas sizes are recorded. Detachable profile appearance fitting still has visible defects; no new formal installation occurred.

日本語: 灰色の原生動作原画 7 点はすべて承認済みです。新しい口腔・歯の原画と歯の外観 3 案を保存し、比較ページを作成しました。歯の外観は選択待ちです。左右の着せ替え合成には残存欠損があり、正式導入数は増えていません。

简体中文: 灰色原生动态 7 张已全部获准，来源与批准已固定。新口腔原图及同嘴型 3 款牙齿方案已保存并制作比较页，等待外观选择。两侧可拆外观合成仍有缺陷，正式安装计数不变。


## 2026-09-14 +090 動態衣裝來源對齊

本節追加：profile-motion-review-02/review.html 已完成灰色來源換代，7 張全身原圖及 28 張同座標近看均內嵌；舊頁封存 legacy-v1。root 已看新 +090 頭部、嘴型與肩帶近看，並重新送出 5 張動態的外觀裁決，尚無回覆。-090 衣裝首輪灰底合成因內袖、白裙破洞及手口漏出灰短褲被 root 退回，證據見 wardrobe-sword-02/root-fit-review-01.json，正在修正語意分層。衣裝原圖本身的批准保留，正式交易數未增加。

使用者指出 profile-motion-review-02 的 +090 肩帶、款式與顏色未跟 -090 灰色两截式對齊。核對後發現：上方灰色執行期近看與下方三張黑色寬肩帶肖像原圖混用。既有已批准 +090 灰色全身 REST 原圖仍為 e0c03689…e7c58f；不因頁面混用而撤回此批准。

已以該灰色細肩帶全身原圖作唯一影像輸入，經內建 imagegen 產生 HALF、CLOSED、SPEAKING 三張完整原生動態；保存於 approved-installation-06/approved-two-piece-gray-alignment-01/whole-native-plus090-motion-02/。完整來源、提示與 SHA 見 generation-inputs.json、receipt.json。三張 SHA 分別 d6766035…4523b、4580cd11…3129、f5902b5c…3a681。正在替換比較頁候選，三張均待使用者檢視；沒有去背、分層或正式安裝，舊黑背心動態原圖保留作历史來源。-090 HALF/CLOSED 仍維持先前待確認狀態。兩側白劍紋漢服與髮質的「兩側都採用」批准繼續有效，appearance 分層獨立進行。

English: The +090 motion page mixed approved gray runtime crops with legacy black broad-strap portraits. Three complete motion frames now derive directly from the approved gray fullbody REST source. Candidate review is being updated; motion approval and formal integration remain pending.

日本語: +090 の動作ページに旧黒色タンクトップの原画が混在していました。承認済みの灰色全身原画から動作 3 枚を作成し、確認ページを更新中です。新動作は確認待ちで、衣装と髪の承認は有効です。

简体中文: +090 动态页混用了已批准灰色运行期画面与旧黑色宽肩带肖像。现从灰色全身原图制作三张完整动态，正在更新比较页，尚待外观确认及正式接入。白剑纹衣装与发质批准继续有效。

## 2026-09-14 左右側臉五官批准；衣装回到原雙前襟白劍紋

本節最新追加狀態：使用者已回覆「兩側都採用」，明確批准下述兩張最終白劍紋漢服與髮質；精確問題 call_3wwspf0BDbU2HrcgNAxTHYkU 與 SHA 已保存於 wardrobe-sword-02/owner-approval.json。因此本節稍早「待檢視」的生成快照已由此批准覆蓋。兩張均已在單次離線 BiRefNet 批次完成去背，RGBA、alpha 與四底色預覽在 wardrobe-sword-02/local-alpha-01/；原始 RGB 保留，root 已看過兩張預覽。正在分側拆出可拆衣裝、髮型、髮飾與鞋並試合成，還未新增正式素材交易。新動態仍按各自來源批准，不受此次衣髮批准自動涵蓋。

最新使用者明確表示「+90、-90側面的臉五官都合格了」，但退回兩側偏離原雙前襟白劍紋的衣裝，以及 -090 毛躁長髮。精確來源綁定見 approved-installation-06/approved-two-piece-gray-alignment-01/complete-appearance-fit-01/owner-face-acceptance-20260914.json；只批准五官，不延伸為完整新衣裝或動態批准。

正確衣裝權威是 v4-hanfu-alignment-20260910/prototype-sword-authority-20260910/authority.json 與原始設計；同層 authority-lock.json 的 V4 衣裝參照已被原型取代。新製作直接输入既有 prototype-front-design-01、同側偏側面衣裝原圖及原型 costume-front-context.png；不能再以舊 ±090 鈷藍珠飾套裝當衣裝權威。

兩張完整修正版保存於 complete-appearance-fit-01/wardrobe-sword-02/：yaw-090-sword.source.png（3debeb5c…17cb5）與 yaw+090-sword.source.png（73831b41…f8382），均 1024×1536 RGB。-090 首張衣裝版髮尾仍亂，已保留為 source-v1；最終版依原 +090 絲滑後髮參照重製完整來源。3 次內建圖像工具的提示、實際參照及原檔 SHA 見 generation-prompts.json 與 generation-receipt.json。兩側保持正側面，前襟劍紋依遮擋顯示，-090 隱藏遠側銀鏈、+090 保留可見銀鏈。新完整衣裝與髮質待擁有者檢視，尚未去背、分層或正式安裝。

比較頁採 PNG 原始位元組內嵌 HTML，避免本機預覽外部圖片載入失敗。前版頁面與來源保留。這輪沒有正式素材寫入，累計仍為 8 筆交易、160 次寫入、156 個唯一目標。-090 的兩次肖像動態貼合因眼周殘影及髮際／耳側缺口退回；whole-native-blink-01 新完整灰色 HALF/CLOSED 仍待外觀確認，先前其他動態批准不被撤銷。

English: Both profile faces are owner-approved, while their cobalt outfits and the -090 frizzy tail were rejected. Two complete navy/white sword-panel wardrobe sources now use the original costume prototype and existing garment images directly. The final -090 tail is smoothed from the accepted +090 hair reference. New complete appearance sources await owner review; formal installation totals are unchanged.

日本語: 左右の横顔は承認済みですが、衣装と -090 の乱れた後ろ髪は差し戻されました。原型と既存素材を直接参照した白剣模様の衣装原画 2 点を作成しました。新しい全体外観は確認待ちで、正式導入数は増えていません。

简体中文: 两侧五官已批准，偏离原型的衣装及 -090 毛躁后发被退回。新两张完整原图直接参考原双前襟白剑纹素材，-090 后发已整理顺直。新整体外观待确认，正式写入数量未增加。

## 2026-09-14 灰色兩截式三張已批准；托腮已正式替換

使用者「三張都採用」明確批准左右 90° 與新版托腮灰色兩截式原圖；精確來源與批准見 I06/approved-two-piece-gray-alignment-01/owner-approval.json（4106f969…49ab）。三張均完成本機 BiRefNet，未重畫衣料或臉。

托腮正式來源已切為 assets/expressions/cheek_native_gray_20260914.png（d73525ef…fed13），保留既有 BCC8 原生閉眼／說話、可拆藍白衣装與圖層像素。4 檔交易與回復備份見該目錄 cheek-native-integration-01/installed-backup-01/receipt.json。正式預設載入器收到舊黑背心輸入仍正確選用新灰色來源，24 個穿衣／卸衣、素顏／淡妝／標準妝、閉眼／說話畫面與候選逐張 SHA 相同。61 項相關 pytest 通過、全庫 Ruff 通過；首輪因 C 槽 pytest 暫存權限失敗，改專案新暫存目錄後通過，未更動測試要求。

正式累计 8 筆交易、160 次寫入、156 個唯一目標。左右全身灰色原生分層已完成，髮型／衣裝及眨眼正在適配；不可宣稱全部換代完成。標準妝眼下細點已確認原版也存在，獨立列入彩妝缺陷；正式全域套件仍缺華麗妝選項。另一組 +090／-030 動態肖像未展示於灰色批准頁，仍待其外觀確認。

English: All three gray two-piece sources are owner-approved. The gray cheek source is formally installed with rollback and 24 exact default-loader frame matches; 61 relevant tests and full-repository Ruff pass. Both gray fullbody profiles remain in fitting, and known pre-existing cosmetics defects remain open.

日本語: 灰色の原画 3 点は承認済みです。頬杖の正式原画を置換し、24 状態の一致、関連テスト 61 件と Ruff を確認しました。左右の全身と既存のメイク不具合は作業中です。

简体中文: 三张灰色两截式原图已批准，托腮已正式替换并有回退备份；24 个实际产品状态一致，61 项相关测试及全库 Ruff 通过。左右全身仍在适配，旧彩妆问题尚未完成。

## 2026-09-14 最新批准：兩張完整兩截式側面進入原生整合

使用者在 approved-profile-two-piece-review-01/review.html?revision=reference-fixed-02 回覆「我全部批准，繼續作業」，批准 -090 e9ae383c…536482 與 +090 3a8999dd…8d6b4 的兩張完整全身原圖。完整原檔 SHA 與精確批准見 approved-installation-06/approved-profile-two-piece-rebuild-01/owner-approval.json（f5ead27a…4104）。本機 BiRefNet 已一次完成兩張去背，保留原 RGB，root 已看過四底色預覽；正在拆出原生圖層、接回既有已批准動態與可拆衣裝。

- 已批准的 -090 / +030 六張 HALF、CLOSED、SPEAKING 肖像繼續採用。另一組 -030 / +090 新動態尚未顯示在本次兩截式頁中，不能自動標為已批准。
- 全身 REST 肖像至新全身的單一相似變換保存在 approved-two-piece-motion-binding-01/registration.json；此幾何診斷不等同外觀批准。動態對位仍以實際合成近看確認。
- 本節寫入時，正式交易仍 7 筆、156 次寫入、153 個唯一目標。全批替換未完成，不得把分層暫存算成已安裝。舊失敗候選及下方歷史 pending 狀態由本節精確批准覆蓋；不得重跑舊收據寫入器撤銷批准。

English: The owner approved both complete two-piece side-view sources. Local RGB-preserving matting is complete; native layers, approved motion registration and detachable appearance integration are in progress. Formal totals remain unchanged. The opposite motion portraits were not shown on this approval page.

日本語: 左右 90 度の上下別衣装の全身原画 2 枚は承認済みです。ローカル切り抜きが完了し、原画座標のレイヤーと動作・着せ替えを統合中です。正式導入の件数はまだ増えていません。

简体中文: 两张完整两截式侧面原图已批准并完成本机去背，正在整合原生图层、已批准动态及可拆外观。正式写入数量未增加；另一组未展示的动态仍待确认。

## 2026-09-14 最新裁決：保留既有兩截式，只重製不一致的左右側面

最新追加批准：使用者回覆「6 張都採用」，精確涵蓋 -090 / +030 的 HALF、CLOSED、SPEAKING 肖像；approved-installation-06/approved-turnaround-motion-review-01/owner-approval.json 已固定六張原檔 SHA，兩份生成收據及比較頁均更新為已採用。此批准保留，並不涵蓋另一組新動態或本次完整全身。

本次兩張完整兩截式全身原圖已保存於 approved-installation-06/approved-profile-two-piece-rebuild-01/：-090 e9ae383c…536482 朝畫面右，+090 3a8999dd…8d6b4 朝畫面左；各自對照已批准側臉，使用者外觀確認待回覆。比較頁為 approved-profile-two-piece-review-01/review.html，+090 使用 opposite-angles 的 bare-v2 原圖。原有長背心候選比較页已停用。正式素材未因本次生成或批准紀錄而增加寫入。

English: The six -090/+030 motion portraits are now explicitly owner-approved. The two new fullbody two-piece sources remain pending appearance review; formal files are unchanged.

日本語: -090/+030 の動作原画 6 点は承認済みです。新しい左右全身原画 2 点は外観確認待ちで、正式素材への書き込みはありません。

简体中文: -090/+030 的六张动态原图已明确批准；新两截式全身两张仍待外观确认，正式素材未写入。

使用者先指定沿用既有合格素體，並澄清兩截式內衣才是偏好，舊款替換僅是個別角度受安全機制限制的折衷。隨後又指出舊 +90° / -90° 的臉確實不同，因此本輪只重製這兩個完整側面；其餘合格原圖與既有圖層繼續沿用。精確指示、五份輸入雜湊及來源角色見 approved-installation-06/approved-profile-two-piece-rebuild-01/owner-source-decision.json。

以已批准的兩個柔和側臉作五官與神情參照，直接沿用使用者提供的正面及各側原圖中的兩截式衣款、體態與站姿。先前 -090 新全身把上衣畫成遮腰長背心，已退回；+030 新全身停放為未採用候選。既有肖像批准保留，新完整全身原圖仍須完成外觀確認後才進入分層與正式替換。正式寫入計數維持 installation-progress.json 的既有值。

English: Reuse accepted source art. Rebuild only the two inconsistent +/-90-degree fullbody identities while preserving the referenced two-piece clothes. The long-tank candidate is rejected; new fullbody outputs require appearance review. Earlier approved portraits remain accepted.

日本語: 合格済み原画を再利用し、人物の顔が一致しない左右 90 度の全身だけを再制作します。既存の上下別衣装を保ち、新たな全身原画は外観確認待ちです。

简体中文: 沿用既有合格原图，只重制身份不一致的左右 90 度全身；保留原两截式衣款。长背心候选已退回，新全身待外观确认，原肖像批准保留。

## 2026-09-14 最新狀態：四個側面與偏側面原圖已批准

- 最新使用者裁決：-030 與 +090 修正版「兩張都採用」。精確來源見 approved-turnaround-opposite-angles-01/owner-approval.json；+090 僅 bare-v2 批准，bare v1 因角度不符退回。之前 +030 / -090 soft-gaze 的批准仍有效，見 front-authority-turnaround-01/owner-approval.json。
- 四張高解析原圖都已用本機 BiRefNet 去背、RGB 原樣保留。+030 / -090 的 HALF、CLOSED、SPEAKING 共 6 張已補齐，approved-turnaround-motion-review-01/review.html 供檢視；新動態仍等待外觀確認。不能將原始表情批准延伸成全部動態或全部角度批准。
- 全身組裝尚未成功：+030 初版裁切斷頸、未去除原灰背景；-090 candidate-02 髮際錯位、耳周洞與領口背心殘片。已退回，不得正式安裝。正在分開處理完整素體、完整髮型與衣裝，禁止 RGB 補洞或獨立五官變形。
- 正式交易數仍 7 筆、寫入操作 156 次、唯一目標 153 個。全身／半身全部換代尚未完成。不得重跑舊 pending/rejection receipt writers 覆蓋新批准。

English: Four portrait identities (-090, -030, +030, +090 v2) are explicitly approved. All four have local RGB-preserving mattes. Six motion portraits for the first pair await owner appearance review. Fullbody assemblies retain visible fit defects and are rejected for installation; formal totals remain unchanged.

日本語: 四方向の原画は承認済みです。最初の二方向の動作原画 6 点は外観確認待ちです。全身の接合には不具合があり、正式素材への導入はまだ行っていません。

简体中文: 四个方向的原图已批准，均完成本机去背。首批两角的 6 张动态原图待外观确认；全身接合仍有明显问题，不能视为全部替换完成。

## 2026-09-14 最新批准：兩個柔和眼神角度進入原生整合

**繁體中文。** 使用者批准「兩個角度都可以了，繼續往下做吧。」精確批准為 `approved-installation-06/front-authority-turnaround-01/owner-approval.json`：+030 threequarter-soft-gaze 0d4152…、-090 profile-soft-gaze 99e963… 兩張完整素顏肖像。正在本機去背、完整頭頸接回全身，以及同來源 HALF/CLOSED/說話製作。原先被否決的側面、偏側面與銳利眼神版本仍退回；本次沒有將所有角度或新動態自動算成已批准。正式安裝計數仍以 installation-progress.json 為準。

**简体中文。** 两个柔和眼神角度已明确批准，继续本地去背、完整头颈接合与原生动态制作；旧版拒收结果保留，其余角度尚未验收。

**English.** The owner approved the exact +030 and -090 soft-gaze whole portraits. Local matting, complete head-and-neck integration, and source-bound motion authoring are authorized to proceed. Earlier rejected variants remain rejected; other views and new motion states are not automatically accepted.

**日本語。** 柔らかな視線の +030 と -090 の完成肖像が承認され、ローカル切り抜き、頭部・首の統合、同じ原画からの動作制作を継続します。旧候補の却下は維持し、他角度や新動作の受入れとは区別します。

## 2026-09-14 最新裁決：全身側面與偏側面的人物一致性退回

### 正面基準重製比較已更新：柔和眼神版

**繁體中文。** `approved-installation-06/front-authority-turnaround-01/` 保存 5 張完整肖像與逐張提示詞、SHA、來源收據。使用者先說側面較像但眼神與神情仍有差，接著否決第一版 30° 與放鬆版 90°「眼神太銳利」。最新待審為 `threequarter-soft-gaze.png` 和 `profile-soft-gaze.png`；以同一張 41ab… 正面素顏作身份基準，偏側視線轉向左前方。兩張皆未獲新的使用者外觀批准。`review.html?revision=soft-gaze-03` 預設新兩版，保留旧版本切換及臉部／神情近看。原圖沒有做局部 RGB 修補，也未去背、抽層或正式安裝。比較頁 JavaScript 語法與本機引用檢查通過；瀏覽器操作工具以 URL 政策阻擋 file 頁面，所以未完成工具內的頁面目視確認，未規避限制。

**简体中文。** 已保存五张完整肖像、提示词和来源记录。上一组因眼神太锐利退回；最新两个柔和眼神候选等待用户判断。未去背、拆层或替换正式人物素材。比较页语法与引用检查通过，浏览器工具的 file URL 限制阻止了页面目视确认。

**English.** Five whole portraits and their exact prompts and source hashes are retained. The previous pair was rejected for a sharp gaze; the two soft-gaze portraits await owner identity and expression review. No new portrait was matted, partitioned, or formally installed. Preview syntax and local references pass; Browser Use URL policy prevented visual inspection of the file page.

**日本語。** 完整な肖像 5 枚とプロンプト、原画のハッシュを保存しました。前の組は鋭い目つきとして却下され、最新の柔らかな視線の 2 候補は所有者による確認待ちです。切り抜き、レイヤー分割、正式導入は行っていません。比較ページの構文と参照先は確認済みですが、ブラウザーツールの file URL 制限によりページの目視確認はできていません。

使用者指出全身側面、偏側面五官偏離正面素體，並否決新增 +030 全身原圖。最新裁決優先於下方技術安裝完成紀錄。-090 native03 的 45 + 3 檔安裝仍存在，髮簪方向與嘴型程式修正保留，但人物外觀不能宣稱已通過；+030 拒收來源及去背衍生物禁止整合。

目前以 owner-approval.json 最近核准的正面素顏（41ab5aab15243633f3b782f14b87721a39a3a09d3f861feb7a9bf3b50eb1d6b1）為完整頭部身份與表情基準。front-authority-turnaround-01 的新側面得到『有比較像了，但還是有差別』，使用者指出眼神與整體表情；正在完整重製，尚無新的身份批准。相關來源与正式交易見 identity-rebaseline-20260914-01/current-owner-identity-rejection.json。上述兩目錄皆位於 approved-installation-06。新一輪僅製作比較原圖，未抽層、送測試或替換正式人物。

**English.** Current owner feedback rejects the side and oblique identities against the frontal bare-face reference. Existing technical fixes remain installed; identity acceptance is withdrawn. New full portraits remain under visual review, with no new formal promotion.

## 2026-09-14 側面髮簪方向與不露齒說話嘴型已正式替換

權威進度為 `scratchpad/halfbody-makeup-consistency-20260913-01/four-look-v4-standard-01/approved-installation-06/installation-progress.json`（以下簡稱 I06，不是另外一個資料夾）。目前 7 筆交易、156 次檔案寫入、153 個唯一正式目標；已逐一核對每個目標最後交易的 SHA。全批四款彩妝與全部舊素材替換仍未完成，不能將本側面完成誤報為全批完成。使用者已授權替換全部舊素材、五姿勢 HALF、必要時直接重製完整來源；沒有提交、推送、合併、發布或修改使用者個人 store。

- 髮簪銀鏈流蘇應在不可見側。正式 `mohan.official.blue-white-hanfu.mohan-outfit` SHA `529b96a8d487370493d6aaf88dfae01fd76abe8d99aa0868c32700bf652f60ba` 已安裝；-090 完整髮型與銀冠可拆，+090 配件未變。`profile-native03-installed-backup/receipt.json` 為 45 檔主交易（34 舊檔、11 新檔），`profile-native03-speech-installed-backup/receipt.json` 為 3 檔嘴型及來源紀錄補充交易。所有舊檔有備份。
- 原生素體使用 `profile-native-body-same-coordinate-03/partitions-03` 和 `native-source-geometry-03.json`。原生眼位、睜眼、HALF/CLOSED、整頭 y<360 替換與領口的語義分層已接回正式；禁止退回 partitions01/02、錯位 478 landmarks 或 runtime01/03。source RGB SHA `d3e0...` 與 canonical authority PNG SHA `b5a6add49565aa7edef0b5c693f72c6a410f2e1ba9a07bdf35e3cc5544304634` 是不同用途。BUILD normalized digest 已修正為後者，正式 `PoseAtlasAssets` 24 視角載入通過。
- 使用者否決 `profile-native03-speech-source-01` 的孤立白牙。source02 在完整全身尺寸重製後仍有亮點，root 也拒收，兩版都沒有安裝。改用放大的完整側臉重製 `profile-native03-speech-source-03/yaw-090-speech.portrait.png`；口內為自然暗部、不露齒。只做完整肖像縮放回原生 crop 座標與語義口部抽取，沒有塗白牙或 RGB 點修。正式 oral PNG、mouth authority lineage 和 BUILD 同一筆補充交易完成。
- `LayeredFullBodyRenderer._paint_visible_cavity` 改用原生 lip/corner 範圍保護下巴；舊固定臉高 76% 切到嘴唇，不能重用。`tests/test_full_body_native_speech_bounds.py` 是實際像素回歸。安裝後 3 項口部測試通過（3.73 s），全庫 Ruff 通過。之前 67 項安裝後測試的 1 個 empty-oral 失敗已由本次來源與相關測試解決，當時其餘 66 項通過；未重跑全庫 pytest，不將重疊測試數字相加。
- 實際正式產品 18 幀在 `I06/I06/profile-native03-formal-speech-runtime-02`（子代理實際寫出一層字面 I06，保留原路徑，不要猜成 -01）。穿衣帶髮飾／卸髮飾／素體各 6 狀態；9 組同眼態 neutral/speech 的 mouth 外 RGBA 差為 0。其餘 12 可見角度與 11 後側的程式回歸證據是 `native-speech-clip-audit-01/receipt.json`；該歷史檢查的 -090 pending 已由正式 18 幀補齊。五個其他代表角度實際嘴型圖已由 root 看過。預覽入口 `profile-hairpin-direction-review/review.html`，可切換 18 狀態及頭、眼、嘴、全身近看。
- 一般半身完整底妝分解 `front-crossed-glamorous-rest-reallocated-foundation-baseline-01` 已被 root 拒收：眉外矩形、虹膜／下眼瞼接縫、側臉硬色帶。數值 coverage error ≤1 不能代表外觀成立；收據已標 root-rejected-visible-seams，不可再以同一公式局部重補或擴量。需重新製作與原生五官完全相容的完整同姿勢妝容來源。原來已批准的是樣式，不是本候選。

尚待處理：其餘五個一般半身原生 REST 與彩妝正式路由、+015/+090 舊輪廓殘留、其餘九個全身動態來源、31-view 四款正式彩妝 ZIP（目前 staged 636/744，未正式替換）。本 -090 後髮與領口在高倍率仍可見細邊，已記錄而未作 RGB 點修。root 技術／視覺檢視不冒稱新一輪使用者外觀批准。

**简体中文。** 侧面髮簪方向和无露齿说话嘴型已安装，18 张正式产品图通过对应检查。7 笔交易共 156 次写入、153 个唯一目标。全批四款彩妆和半身来源替换仍未完成，失败的局部色块候选不安装。

**English.** The far-side tassel correction and no-visible-tooth speech source are installed. Seven transactions total 156 file writes across 153 unique targets, with latest hashes verified. Eighteen default-product frames and the affected speech tests pass; full-repository Ruff passes, but the full test suite was not rerun. The global four-look replacement remains incomplete; the halfbody decomposition with visible seams was rejected. No new owner appearance approval, commit, push, merge, release or user-profile mutation is claimed.

**日本語。** 側面の髪飾り方向と歯を見せない発話素材を正式導入しました。7 件の処理で 156 回の書込み、153 個の固有対象を確認しています。製品の 18 状態と関連テストは成功していますが、四種類のメイクと半身素材の全体置換は未完了です。見える継ぎ目のある候補は採用していません。

## 2026-09-13 最新決定：全身 04 已被使用者否決

最新續作入口：`scratchpad/halfbody-makeup-consistency-20260913-01/FULLBODY_RECOVERY_HANDOFF.md`。新 -090 三妝面與本機 BiRefNet 去背候選在 `fullbody-source-bound-repair-01/review.html`，尚待使用者採用；`fullbody-runtime-diagnostic-02` 已修復蒐集器預設穿戴造成的來源混用，只有兩角度 6 狀態，明確 `authoring_ready=false`。全身 24 角度的人物、衣裝與動態整合仍未完成。不要將舊 fullbody 04、source-baseline-drift-review 歷史快照或兩張新診斷當作全批通過。

使用者抽驗後明確指出妝容差異不足、人物一致性很糟；yaw -090 的眼妝落在臉頰，yaw -180 的頭部也不是正後方。`native-fullbody-adaptation-04` 全部 24 角度已退出待採用清單。先前「等待使用者回答」已失效，不得沿用為批准或再次要求採用同一批。

目前 `scratchpad/halfbody-makeup-consistency-20260913-01/review.html` 僅列 7 半身姿勢／12 狀態，頁首說明全身退回。失敗圖保留於 `rejected-fullbody-04-review.html`；正式退回紀錄為同目錄 `fullbody-recovery-state.json`。已批准的是加強妝容方向；此次不撤銷方向，也不代表半身已獲整批外觀驗收。

後續先核對實際 V4／V5 原圖、SHA、角度與同人同衣一致性，再製作可見且正確對位的妝容。先前像素／邊界檢查使用同一套可能錯誤的來源幾何，沒有驗證人物身份或眼睛位置，不能當作外觀通過。正式素材尚未因這次修正更換。

### 2026-09-13 原生角度適配與動態候選／原生角度适配与动态候选／Native angle adaptation and motion candidates／原生視点と動作への適用候補

**繁體中文。** 本節接續已批准的「這次方向可以，繼續適配全身與半身」。最新半身為 `scratchpad/halfbody-makeup-consistency-20260913-01/native-halfbody-adaptation-04/receipt.json`，7 姿勢、12 個既有原生狀態，SHA `813b682d1213ef03f5e8a7db059a33d046dfb8df0fc1ab478cd158a210ab494b`。底妝、眼妝、腮紅、唇妝均獨立，兩款眼妝有各自的已批准來源。01～03 為歷史候選，直接續作 04，不再回到舊五姿勢來源或舊水平眉毛遮罩。

**简体中文。** `native-runtime-staging-03` 已接半身 04；`native-v3-product-preview-02/receipt.json` SHA `f8eaa0c5d897e5e4d0210b3c42fef6187f5daf463b3f014b216381097dbce05f`，通过实际产品绘图生成托腮／无奈共 72 张状态和开关预览。bare 三种 slot mode 完全一致。五个恢复的半身姿势只有静态原图，不能宣称新的闭眼／说话动态或完整隐藏身体已完成。正式素材、用户配置均未替换。

**English.** The new closed-eye adapter separates broad approved pigment from thin fibers. Shadow is bound between the actual native brow and lid; lash fibers keep eye-width scale and point below the closed lid. This fixes the source brow-clearance hole moving onto the lid, without transferring donor face pixels. Full-body lower pigment is independently bound to the native lower lid. The native brow search accounts for foreshortened far eyes. Failed/interrupted candidate directories are preserved. No new image generation, background removal, commit, push, package, merge or release in this adaptation continuation.

**日本語。** 濃くした方針は承認済みですが、新しい各視点の外観採用は未確定です。比較ページは `scratchpad/halfbody-makeup-consistency-20260913-01/review.html`。実製品描画の頬杖・困惑プレビューは `native-v3-product-preview-01/review.html?assets=../native-v3-product-preview-02` です。全身の最終候補と検査結果は同ディレクトリの `ADAPTATION_HANDOFF.md` および比較ページの receipt を参照してください。

後續正式接入的具體限制：全身正式 `makeup-safe-regions.json` 仍只有 yaw+000 的 canonical foundation/aperture maps 非空；各角度候選中的 coverage/aperture 需要依原生來源正式登錄。現行 v2 parser 的 rest/half aperture 不允許空值，因此無可見眼睛的側後角度需要明確的來源與遮擋契約，不能以擴大到全畫布、虛構眼睛或繞過安全範圍檢查解決。五個新半身姿勢也尚無正式原生動態端點。本次全身分層比較不代表全身正式 pack 已整合。

最終候選證據／Final candidate evidence：全身 `native-fullbody-adaptation-04/receipt.json` SHA `324bacf1246f252856878d9dda39ee6fa3a0779c79ffbb8b0ef3b813661a778d` 已完成 24／72；統一比較頁 receipt SHA `a943c37505110731ac5542ee557f73f45216a8657c8e03837ef4b358b0f0bdbb` 為 31 組／84 狀態。`adaptation-boundary-check.json` SHA `eb31628288351e2b30bbe3b81736dad604ad284b84009965cb2caa8757cac452` 核對 672 個分層 SHA、168 張精確重組、native bare／眼部開口／輪廓與正式來源 pin，exit 0。全庫 Ruff、比較頁 JavaScript 語法檢查通過；未重跑全庫 pytest。各角度外觀採用問題已送出，仍待使用者回答；方向批准不改寫為整批外觀批准。

### 2026-09-13 加強妝容方向已批准／加强妆容方向已批准／Stronger makeup direction approved／強めのメイク方針を承認

**繁體中文。** 使用者批准第二組生成樣式：**「這次方向可以，繼續適配全身與半身」**。精確批准與來源為 `scratchpad/halfbody-makeup-consistency-20260913-01/approved-style-direction.json`、`tutorial-informed-targets-v2/receipt.json`；第一組 `tutorial-informed-targets/` 已被否決為太淡，不能再標示等待批准。v2 淡妝 SHA `e498f69be39da2485399e4db733570d5765a87330cf609b107d213148964378c`、標準妝 SHA `0e528757a531e125e047fbbaeaaf03de263e6d5edf6e75bf4144335660e3c2be`。批准包含樣式方向及 24 全身／7 半身適配；不等於後續每張遮罩、動態或正式替換已驗收。

**简体中文。** 第二组加强版样式已获采用，继续在每个当前原生姿势适配。正面四槽抽层在 `approved-front-extraction-02/`；第一版眼缘遮罩切断睫毛根的问题已修正。五个新版半身 rest 预览在 `native-halfbody-adaptation-01/`，未修改正式素材。

**English.** The second stronger pair is owner-approved as a shared style direction. Same-source four-slot extraction 02 preserves protected native eye/mouth pixels, silhouette and out-of-face pixels, with maximum target reconstruction error 1. Five current half-body rest poses now have distinct light/classic pigments. Native reviewed-motion v3 (9 new + 32 compatibility checks) and exasperated appearance v3 (13 new + 26 compatibility checks) passed their focused checks; version 1 formal assets remain unchanged. Full-repository Ruff passed before the subsequent scratch adaptation work. No commit, push, merge, package or release.

**日本語。** 強めた第 2 案の方針が承認され、全身 24 視点と半身 7 ポーズへの適用を進めています。現在の原生顔を保持し、薄化粧と標準化粧は別々の目元素材です。現時点の候補や自動検査は全視点の外観承認を意味しません。

補充／Correction：`assets/makeup-safe-regions.json` 的 31 個條目雖都有 `foundation_masks` 欄位，**只有 yaw+000 的 rest/half/closed map 非空**。其他全身角度需使用其原生 478 landmarks 與圖層建立候選範圍；不能把欄位數當作完成數。`fullbody-authoring-inputs.json` 記錄正式來源與繪圖入口。以下較早節的「生成提案仍待批准／v3 尚在開發」已由本節覆蓋。

### 2026-09-13 全身與半身共用彩妝修訂／全身与半身共用彩妆修订／Shared full and half-body makeup revision／全身と半身の共通メイク改訂

**繁體中文。** 使用者先否決 donor LAB 場轉移的眼下重影與色塊，再否決 `v4-strength-candidate` 中位色調與原生遮罩版的底妝不均、眼影及假睫毛不足、淡妝與標準妝只有透明度差異。兩版都未安裝，前版在 `rejected-field-transfer/`、後版收據標為 `owner_rejected`。不要再用逐像素膚色閾值形成粉底覆蓋洞，或只將同一圖層乘 `.55` 冒充不同眼妝。

**简体中文。** 两版数学妆效转移均被否决，未安装。使用者要求参考台湾、日本、中国大陆彩妆教学，且明确将全身 24 视角一并纳入，使其与半身 7 姿势保持一致。必须保留各自原生身份，淡妆与标准妆使用不同细节素材。

**English.** The owner rejected both donor-field transfer (ghost eyes and blocks) and native-mask median-tone transfer (uneven foundation and missing eye/lash detail). Neither candidate was installed. Scope now explicitly includes coordinated refinement of 24 full-body views and seven half-body poses. Use distinct authored light/classic eye details on current native identities; do not substitute an opacity multiplier for design differences.

**日本語。** 色差転写の残像と、次の色調版の不均一なファンデーション・目元の不足が却下されました。両候補とも正式導入していません。全身 24 視点と半身 7 ポーズを共通方針で調整し、薄化粧と標準化粧は個別の目元素材で表現します。

目前入口／Current entry：`scratchpad/halfbody-makeup-consistency-20260913-01/review.html` 已改為原生素顏與兩款新正面完整妝面比較；`tutorial-informed-targets/` 保存 built-in imagegen 的兩次輸出原檔、完整 prompts 與收據，狀態為 `awaiting_owner_visual_review`。這兩張僅是妝面樣式候選，尚未抽層、未宣稱逐像素五官相等、未替換衣裝或正式素體。共同方案見 `makeup-style-brief.md`，臺日教學見 `taiwan-makeup-reference.md` 與 `japan-makeup-reference.md`；已讀文字及官方影片說明，未播放影片。舊七姿勢頁保留於 `rejected-tone-review.html`。／The two generated front portraits are appearance targets only, with full prompts and provenance retained. They are not installed assets or a claim of pixel-identical facial geometry.／生成した正面 2 枚は外観候補のみで、レイヤー抽出も正式導入も未実施です。

程式進度／Code status：既有全身 `native-front-v4-makeup-10/pigment-residual-review-04/recipe.py` 的 SourceAtop／minimal residual 公式已抽成 `tools/art_pipeline/cosmetic_residual.py`，以四槽舊素材比較完全相等。BCC8 與無奈 v2 四槽 foundation 支援已完成相容檢查；正式 manifests 仍為 v1 三槽。上一輪實測：原生動作相關 22 項、新 foundation 15 項、無奈舊新共 26 項、residual 3 項通過，全庫 Ruff 通過。v3 分別選取 light/classic 素材接線正在獨立模組中實作，完成後補結果。／v1 formal assets remain installed; v2 code support does not imply art approval. v3 variant-specific loading is in progress.／正式素材は v1 のまま、v3 の個別妝款読み込みを実装中です。

沒有提交、推送、合併、打包或發布。五個新版半身仍只有可見分層，未驗證完整衣下身體。／No commit, push, merge, package or release. Five newer half-body sources still lack verified hidden anatomy.／コミット・公開は行っておらず、5 ポーズの衣服下素体は未検証です。

以下為較早整合紀錄，以本節及各最新收據為準。

### 2026-09-13 七姿勢彩妝與來源修正／七姿势彩妆与来源修正／Seven-pose makeup source correction／7 ポーズの化粧出典修正

**繁體中文。** 使用者要求七個半身動作都要有一致且可見的眼妝、腮紅與唇妝差異，並指出這次的五姿勢診斷板誤用前一版素體。`assets/expressions/idle_front.png` 等舊檔不可再作為新版五姿勢的身分依據。以 `scratchpad/halfbody-makeup-consistency-20260913-01/approved-source-catalog.json` 為本次七個來源的精確清單，`pin_current_sources.py` 驗證圖檔與批准來源。舊五姿勢彩妝修订未安裝，原安裝腳本已停用。五個新版來源目前只有同來源可見圖層，完整衣下身體尚未驗證，不能冒稱正式完整素體已換代。

**简体中文。** 七个动作的妆感需要一致可见；五姿势诊断板误用了旧素体，旧候选未安装，安装脚本已停用。新版来源以 `approved-source-catalog.json` 的哈希为准。五个新版可见分层不能冒充已验证完整衣下身体。

**English.** The owner requested visible, consistent eyes, blush and lips across all seven half-body poses, then rejected the diagnostic board for using the older five-pose bodies. Resolve current identities through the pinned `approved-source-catalog.json`, never through legacy expression filenames. The legacy strength archive was not installed and its installer is disabled. Five current sources have visible partitions; their complete hidden anatomy is not verified.

**日本語。** 7 ポーズで目元・頬・唇の化粧差を統一します。5 ポーズの診断に旧素体を誤用したため、旧候補の導入を停止しました。出典は `approved-source-catalog.json` のハッシュで固定し、可視レイヤーのみの素材を完全な衣服下素体と扱わないでください。

目前進度／Current state：托腮 BCC8 的眼線與腮紅已加強，淡妝與其他路徑統一為 `0.55`，24 張正式組合及卸妝還原通過；無奈使用最新再生來源 `0bb3d74a...`，8 張眼頰層已更新並保留 4 張原唇層，正式載入檢查通過，更新後動態繪圖待核對。五個新版妝容候選與七姿勢比較頁持續製作中。32 項本次相關測試與全庫 Ruff 通過。沒有新增生成、去背、提交或發布。

以下為較早整合紀錄，最新來源與進度以上節為準。

### 2026-09-13 最新托腮正式整合／最新托腮正式整合／Current cheek integration／頬杖の正式統合

**繁體中文。** 「左二一致，採用這個托腮來源」及閉眼、微張嘴、黑背心「三項都採用」已落實。`assets/expressions/cheek_native_bcc8.png` 為完整衣下素體；原生臉沿用 BCC8，藍白衣料與雙劍紋直接沿用已批准層。`reviewed-garments/manifest.json` 指向此素體並要求同源動態，閉眼／微張嘴與 9 張可選彩妝已接入。0／0.42／1 三檔差異及卸妝精確還原通過正式繪圖核對。舊托腮保留於 `scratchpad/cheek-approved-formal-integration-20260912-01/before-bcc8-install/`；髮尾與頸側僅做局部 alpha 清理，未增加生成或 BiRefNet 呼叫。素材載入後保持固定快照，已開啟的產品需重啟才採用新的檔案。

**简体中文。** 新托腮原生脸、闭眼、微张嘴与黑背心来源的批准已落实；衣装沿用批准层。三档彩妆及卸妆复原已通过正式渲染核对。旧文件完整保留，新增头颈／发尾清理没有额外生成或去背调用。运行中的产品需重启加载新素材。

**English.** The approved BCC8 cheek identity and three approved source extensions are installed. The new body uses copied native facial pixels with continuous approved neck/arms; the existing garment remains separate. Source-bound eye/mouth endpoints and nine cosmetic layers support bare/light/classic and exact makeup removal. Prior files are retained. Local alpha cleanup used no further generation or matting. Restart an already running product to load the immutable new asset snapshot.

**日本語。** 承認済み BCC8 の顔と、閉眼・微開口・黒いタンクトップの 3 出典を正式配置しました。既存衣装は独立レイヤーのまま使用し、目口の動作と 9 化粧レイヤーを接続しました。素顔・薄化粧・標準化粧と化粧解除を確認済みです。旧素材を保存し、追加生成や背景除去は行っていません。起動中の製品は再起動して新素材を読み込みます。

證據／证据／Evidence／証拠：`scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-install-receipt.json`、`bcc8-validation.json`、`bcc8-runtime-preview/receipt.json`。99 項相關回歸與 12 項新接線測試通過，全庫 Ruff 通過；正式繪圖為 4 狀態 × 3 妝感 × 2 衣裝，共 24 張。／99 related regressions and 12 native-routing checks passed; full Ruff passed. Actual renderer evidence contains 24 combinations.／関連回帰 99 件と新規接続 12 件、全庫 Ruff が成功し、実レンダラー 24 組を記録しました。

範圍／范围／Scope／範囲：此托腮僅有批准的閉嘴及微張嘴端點；完整視窗互動與物理動畫未驗證，獨立髮型更換未在本次新增。其他姿勢仍依各自審閱狀態，沒有提交、推送、合併或發布。／This change does not certify full window interaction, physics, independent hair exchange, other pose art acceptance, or a release.

動態審閱／动态预览／Review／確認：`scratchpad/cheek-approved-formal-integration-20260912-01/bcc8-runtime-preview/review.html`。主審閱頁的新版托腮已連至正式輸出。下節為先前歷史紀錄，以本節和 BCC8 收據為最新狀態。

## 2026-09-12 原生來源修復與托腮正式接線

**繁體中文。** 使用者否決左轉的眼睛、脖子與手。已找到成因：重組曾混入舊 V5 素體，並非較後批准的統一身分。左轉、正面、靈光一現、假打與斥責已在 `scratchpad/*-existing-material-copy-20260912-01/` 改回已批准穿衣原圖的同源可見三層；它們仍是待審閱候選，不是完整可脫衣素體。左轉髮緣與托腮紫邊清理持續在獨立候選目錄；不可把舊版拒絕或原圖批准誤記為本次修正版已接受。

**简体中文。** 用户否决左转的眼睛、脖子与手，原因是混入旧 V5 素体。五个姿势已恢复为较后批准原图的同源可见三层，仍是待审阅候选，不是完整可脱衣素体。左转发缘和托腮紫边在独立候选目录处理，不得把旧版拒绝或原图批准等同于新版接受。

**English.** The owner rejected the left pose's eyes, neck and hands. The mixed reconstruction used an older V5 body instead of the later approved identity. Five poses now reuse same-source visible clothing, head/neck and hand partitions from approved dressed sources. They remain review candidates, not complete detachable anatomy. Left hair-edge and cheek magenta-edge cleanup remain separate candidates; previous source approval is not acceptance of their latest composition.

**日本語。** 左向きの目・首・手が却下された原因は、後の承認済み人物と古い V5 素体の混在でした。5 姿勢を承認済み原画と同じ出典の衣装・頭頸部・手の可視 3 レイヤーへ戻しました。まだ目視確認用の候補であり、完全な着脱可能素体ではありません。左の髪縁と頬杖の紫色の縁は独立した候補で修正中です。

**托腮／托腮／Cheek／頬杖。** 「可以，採用這版托腮」已正式落實於 `assets/expressions/reviewed-garments/` 的 7 檔：遮罩、衣裝、橫手、前景袖口、manifest、批准與 receipt。`native_source_file=idle.png` 與 SHA 必填；原生臉不隨衣裝選擇改變，其他姿勢先退出新分支以保留既有彩妝。／该批准已落实为 7 个正式文件，原生来源文件及 SHA 必填，换衣不换脸，未登记姿势保留原有彩妆。／The approved cheek is installed as seven files. Native filename and SHA are required, identity is independent of garment choice, and unregistered poses retain ordinary makeup.／承認済み頬杖を 7 ファイルで配置し、原生ファイル名と SHA を必須化しました。衣装変更で顔は変わらず、未登録姿勢は既存の化粧経路を保ちます。

**驗證／验证／Validation／検証。** `scratchpad/cheek-approved-formal-integration-20260912-01/formal-verification.json`：正式繪圖 10 張，靜止與批准合成最大 RGB 差 2；來源與架構 46 passed，繪圖與彩妝 38 passed，先前相關回歸 82 passed（範圍重疊，不可相加為獨立總數）；全庫 Ruff exit 0。完整 UI、物理動態與說話唇色尚未完成，沒有提交、推送或發布。／正式渲染 10 张，最大 RGB 差 2；上述测试范围重叠，不可相加。完整 UI、物理动态与说话唇色未完成，无提交、推送、发布。／Ten actual renderer frames; maximum static RGB difference 2. The recorded test groups overlap and must not be summed. Full UI, physics and speech lip pigment remain incomplete; no commit, push or release.／実レンダラー 10 枚、静止画の RGB 最大差 2。テスト群は重複するため合算不可。UI 全体・物理動作・発話時の口紅は未完了で、コミット・プッシュ・公開はしていません。

技術入口／技术入口／Technical entry／技術入口：`docs/reviewed-native-garments.md`。審閱／审阅／Review／確認：`scratchpad/existing-material-repair-review-20260912-01/review.html`。

# 專案交接文件／项目交接文件／Project Handoff／プロジェクト引き継ぎ文書

## 繁體中文

### 2026-09-12 正式彩妝安裝完成範圍／正式彩妆安装范围／Formal makeup installation scope／正式な化粧配置の範囲

* 使用者「採用這組配色」的批准已落實：30-view archive（24 yaw + 6 named pose）已正式安裝，新無奈的 12 個嘴型專屬彩妝另走 source-bound 分流。這是本輪可選彩妝安裝完成，原先 47 項指全庫 Ruff 診斷，已修正且全庫 Ruff 通過；本次不代表完整全身、31-view 逐張人工外觀驗收或發布完成；既有使用者 store 未修改。／用户批准的配色已落实：30-view archive 正式安装，新无奈 12 个嘴型专属彩妆独立分流；原先 47 项指全库 Ruff 诊断，已修正且全库 Ruff 通过；本次不代表完整全身、31-view 逐张人工验收或发布完成，既有用户 store 未修改。／The approved palette is installed in the 30-view archive, with 12 mouth-specific cosmetic layers for the new exasperated portrait routed separately. The earlier 47 refers to repository-wide Ruff findings, which were fixed and now pass. This optional-makeup installation does not certify a complete full body, individual human acceptance of all 31 views, or a release. Existing user stores were not modified.／承認済み配色を 30-view archive に正式配置し、新しい無奈の口形別化粧 12 レイヤーは独立した経路に配置しました。先の 47 件は全庫 Ruff の指摘で、修正済みかつ全庫 Ruff は成功しています。今回の任意化粧の配置は、全身全体、31 view の個別目視受入れ、公開の完了を意味しません。既存ユーザー store は変更していません。
* 正式 archive 與安裝 receipt 的 SHA 已唯讀核對，詳見下方證據。原 archive 已備份；原 foundation 與 archive 內舊無奈成員保留，新無奈產品使用獨立來源。正式 factory 無環境變數時 cosmetics_available=true，appearance 共 14 層（12 妝 + 衣裝/replace）。／正式 archive 和 receipt SHA 已核对，旧 archive 已备份；foundation 与 archive 原无奈成员保留。默认 factory 无环境变量时 14 层 appearance 可用。／Formal archive and receipt hashes were independently verified; the previous archive is backed up, with foundation and legacy archive exasperated members preserved. Without an environment override, the formal factory exposes cosmetics_available=true and 14 appearance layers: 12 cosmetics plus garment and replacement mask.／正式 archive と receipt の SHA を独立確認し、旧 archive をバックアップしました。foundation と archive 内の旧無奈素材は保持しています。環境変数なしの正式 factory では cosmetics_available=true、appearance は化粧 12 と衣装・replace の計 14 レイヤーです。
* 六 named pose 的新增亮紫線已消除，原圖淡邊保持；輪廓 3 px 帶無彩妝，原輪廓 RGBA 差 0。最終另移除四個 closed 圖的耳前髮際孤島與六姿勢 12 個眼層的眉區溢出，僅托腮安全區右端擴 1 px 收入實際睫毛。+030 closed 的 1,338 個藍邊像素與 -090 rest 的 685 個藍邊像素在 bare/classic 相同，經原生圖、Qt 直接解碼與產品逐像素追溯，皆為 Alpha 1–7 的 8-bit 預乘量化；灰底每頻道誤差低於 1/255，不能據此認定原生圖有可見純藍缺陷。／新增亮紫线已消除，原图淡边保留；另清除闭眼耳前孤岛与眉区溢出，只有托腮安全区右端增加 1 px 实际睫毛。+030 closed 的 1,338 和 -090 rest 的 685 个蓝边像素在 bare/classic 相同，追溯为 Alpha 1–7 的 8-bit 预乘量化；灰底每通道误差低于 1/255，不据此认定原图存在可见纯蓝缺陷。／The added bright purple fringe is removed while the faint original edge is preserved; the 3 px contour band has no pigment and source-edge RGBA difference is zero. Final corrections removed four closed-state preauricular hairline islands and brow spill in 12 eye layers across six poses; only cheek-rest's right safe-region edge grew by 1 px to include a real lash. The 1,338 blue-edge pixels in +030 closed and 685 in -090 rest are identical in bare/classic and arise from 8-bit premultiplied conversion at Alpha 1–7, reproduced by direct Qt decoding of the raw authority. Gray-background channel error is below 1/255; this does not establish a visible pure-blue defect in the native art.／追加された鮮やかな紫線を除去し、原画の淡い縁色を保持しました。輪郭 3 px に化粧はなく、原輪郭 RGBA の差は 0 です。最終修正で閉眼 4 枚の耳前生え際の孤立部分と 6 姿勢 12 眼レイヤーの眉へのはみ出しを除き、托腮のみ実際のまつ毛のため安全領域右端を 1 px 広げました。+030 closed の青い縁 1,338 ピクセルと -090 rest の 685 ピクセルは bare/classic で同じで、Alpha 1–7 の 8-bit 事前乗算の量子化に由来し、原画の Qt 直接読込でも再現します。灰色背景での各チャンネル誤差は 1/255 未満であり、原画に視認可能な純青の欠陥があるとは判定できません。
* 藍邊追溯證據／蓝边溯源证据／Blue-edge provenance evidence／青い縁の由来の証拠：`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.json`、`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.md`。
* 驗證為分批受影響範圍：49 張真產品 QA 圖通過；runtime/appearance/browguard/packbuilder 39 passed（39.03 s），文件/changelog/分層檢查測試 23 passed（1.58 s），另 25 項受影響測試及安裝後 12 項 store/cache 測試通過（後者 24.13 s）。全庫 Ruff 通過；分層 import checker 330 模組通過，只新增 service_container→exasperated_candidate_assets 精確組合邊。這不是全庫測試套件全跑。／验证按受影响范围分批执行：49 张真产品图、39+23 项主线测试、另 25 项及安装后 12 项通过；全库 Ruff 和 330 模块 import checker 通过，不等于全库测试全跑。／Validation was scoped: 49 actual product QA frames passed; 39 runtime/appearance/browguard/packbuilder tests passed in 39.03 s, 23 documentation/changelog/layered-checker tests in 1.58 s, a separate 25 affected tests passed, and 12 post-installation store/cache tests passed in 24.13 s. Full-repository Ruff and the 330-module import checker passed; only the exact service_container→exasperated_candidate_assets composition edge was registered. This was not a full-repository test-suite run.／検証は影響範囲ごとに実施しました。実際の製品 QA 49 画像、runtime 等 39 件（39.03 秒）、文書等 23 件（1.58 秒）、別の関連 25 件、配置後 store/cache 12 件（24.13 秒）が成功しました。全庫 Ruff と 330 モジュールの import checker も成功し、service_container→exasperated_candidate_assets の正確な構成辺のみ登録しました。全テストスイートの実行ではありません。

證據／证据／Evidence／証拠：

* `assets/official-packs/mohan.makeup.builtin.mohan-outfit`: SHA-256 `2a92685c89f97e9799d7c8ba7ea8c65859cfef400008bcded5e838c16fbf2a84`.
* `B/cross-angle-makeup-approved-integration-20260912-01/formal-native30-install-receipt.json`: SHA-256 `284a2cc8bf3d7570ac88f6a8350132861ad56f75d45408f8b390f7a28ba64979`.
* `B/cross-angle-makeup-approved-integration-20260912-01/official-makeup-before-native30.mohan-outfit`: SHA-256 `51ee53cfbf0e082e18be7d1af775a331a61aad60d7e51ec36453aa4c57b461a6`.
* `B/cross-angle-makeup-product-qa-20260912-01/native30-qa-20260912-01/receipt.json`: SHA-256 `fb959b2ba6789fde54f4eeb6f7c6dc1ede37c2b1f6d7641b113b5a11679054b8`.
* 新無奈／新无奈／Exasperated／無奈 `assets/expressions/source-bound-exasperated/receipt.json`: SHA-256 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`.

`B` = `scratchpad/v4-identity-rebuild-20260905/v4-hanfu-alignment-20260910/source-bound-halfbody-sword-sync-20260911-01`.

### 以下保留先前階段紀錄，以本節最終狀態為準／以下保留历史记录／Earlier-stage history follows; this final status takes precedence／以下は過去の記録であり、本節の最終状態を優先します

### 2026-09-12 配色批准與輪廓修正／配色批准与轮廓修正／Palette approval and edge correction／配色承認と輪郭修正

**繁體中文。** 使用者已明確表示「採用這組配色」。此為跨角度可選彩妝配色批准，不等於逐張素材再次核准或完整全身驗收。整合分為 30 個既有 view 的 archive（24 yaw + 6 named pose）與新無奈獨立來源分流；新無奈依 rest/mid/open/round 保留嘴型專屬唇支持。新無奈彩妝正式安裝已確認；30-view archive 尚未完成，詳見下方安裝證據。

**简体中文。** 用户已明确表示“采用这组配色”。这是跨角度可选彩妆配色批准，不等于逐张资源再次批准或完整全身验收。集成分为 30 个既有 view 的 archive（24 yaw + 6 named pose）与新无奈独立来源路径；新无奈按 rest/mid/open/round 保留各嘴型唇部支持。新无奈彩妆正式安装已确认；30-view archive 尚未完成，见下方证据。

**English.** The owner approved this palette. This approves the optional cross-angle color scheme, not a second per-image approval or complete full-body acceptance. Integration separates a 30-view archive (24 yaw views and six named poses) from the new source-bound exasperated portrait, whose rest/mid/open/round states retain separate lip supports. Formal cosmetic installation is confirmed for the new exasperated portrait; the 30-view archive remains pending, as detailed below.

**日本語。** 所有者はこの配色の採用を承認しました。これは角度間で一貫した任意の化粧の配色承認であり、各素材の再承認や全身全体の受入れではありません。統合は 30 view の archive（24 yaw と 6 named pose）と新しい無奈の独立した原画対応経路に分け、無奈の rest/mid/open/round はそれぞれの唇支持を維持します。新しい無奈の化粧は正式配置を確認済みですが、30-view archive は未完了です。詳細は以下に記録します。

### 新無奈安裝已確認、30-view archive 尚未完成／新无奈已安装、30-view archive 待完成／Exasperated installed; 30-view archive pending／無奈は配置済み、30-view archive は未完了

**繁體中文。** 新無奈的 12 個可選彩妝圖層已正式安裝到 `assets/expressions/source-bound-exasperated/`；主線回報 `validate_formal_exasperated_install` exit 0。現有七 parts、三嘴型、衣裝、replace mask、批准檔與 base manifest 的 SHA 均保留。共 28 個被 receipt 釘選的非 receipt 檔、29 個總檔，其中 24 PNG。正式 receipt SHA 已唯讀核對為 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`；安裝前備份位於本批次 `cross-angle-makeup-approved-integration-20260912-01/exasperated-before-makeup/`。30-view archive 仍在組包，safe-region 真閘門正在修正，不能宣稱全批完成。

**简体中文。** 新无奈的 12 个可选彩妆图层已正式安装，主线验证 exit 0；原七 parts、三嘴型、衣装、replace mask、批准文件和 base manifest SHA 保持相同。共 28 个被 receipt 固定的非 receipt 文件、29 个总文件，其中 24 PNG；receipt SHA 与上述值一致，旧文件已备份。30-view archive 仍在组包并修正 safe-region 验证失败，未全部完成。

**English.** Twelve optional cosmetic layers are formally installed for the new exasperated portrait; the main agent reports successful formal validation. Hashes of the prior seven parts, three mouths, garment, replacement mask, approval file, and base manifest remain unchanged. There are 28 pinned non-receipt files, 29 files in total, and 24 PNGs. The receipt hash above was independently read and verified; the pre-installation copy is retained at the backup path above. The 30-view archive is still being packaged, with a genuine safe-region gate failure under correction. Overall completion is not claimed.

**日本語。** 新しい無奈の任意の化粧 12 レイヤーは正式配置済みで、主担当は正式検証の exit 0 を報告しています。既存の 7 parts、3 口形、衣装、replace mask、承認ファイル、base manifest の SHA は保持しています。receipt が固定する本体ファイルは 28 件、合計 29 件、そのうち PNG は 24 件です。上記 receipt SHA は読み取りで独立確認し、配置前のバックアップも保存しています。30-view archive は組み立て中で、safe-region 検証の失敗を修正しており、全体の完了は主張しません。

### 確認過的修正與限制／已确认的修正与限制／Verified corrections and limits／確認済みの修正と制限

- 六 named pose 已收斂彩妝 alpha：只使用原圖不透明輪廓內側，輪廓 3 px 帶為零顏料，向內 4 px 柔化。托腮彩妝新增的亮紫線已消除；原圖本身極淡邊色保留，未修改原 RGB 或輪廓。六姿勢 × 三狀態的輪廓 RGBA 與灰底改變均為 0。／六个 named pose 的彩妆 alpha 已限制在原图不透明内部，轮廓 3 px 带无颜料，向内 4 px 柔化；新增亮紫线已消除，原图淡边保留，18 个姿势状态的轮廓和灰底变化均为 0。／Pigment alpha is confined inside the opaque source, with a clear 3 px contour band and a 4 px inward transition. The added bright purple line is removed; the faint original fringe remains, with no source RGB or contour edits. All 18 pose/state edge and gray-background comparisons are unchanged.／化粧 alpha を不透明な原画の内側に限定し、輪郭 3 px は無色、さらに内側 4 px でなじませました。追加された鮮やかな紫線は除去しましたが、原画の淡い縁色は保持しています。原 RGB と輪郭は編集せず、18 姿勢状態の輪郭と灰色背景の差は 0 です。
- 三 gesture 的 speaking+closed 使用真產品眨眼合成；眉保護依原眉與對位後 donor 眉形狀排除，沒有用水平裁線或關閉眨眼掩蓋問題。mock-hit 的真眼部偏移為顯示座標 (0,2)，對應原生約 (0,5.394)；其 closed 材料已依實際 profile 更正。／三个 gesture 使用真实产品闭眼合成，按原眉和对位后 donor 眉形保护；mock-hit 的显示偏移 (0,2) 已反映在闭眼材料。／The three gesture closed states use actual product blink composition with source-shaped protection of original and aligned donor brows. Mock-hit's real display offset (0,2), approximately (0,5.394) natively, is reflected in its closed material.／3 gesture の閉眼は実際の製品合成を使用し、原眉と位置合わせ後の donor 眉の形状を保護します。mock-hit の実際の表示座標 (0,2)、原生座標で約 (0,5.394) を閉眼素材に反映しました。
- 眉保護快取上限 8 筆，以眉區內容、尺寸、表情為鍵；嘴型改變不重算。465 畫布 warm 中位 0.1925 ms、p95 0.2594 ms，首次含 CV 初始化 28.34 ms。相關回歸曾 13 passed；最後補測 expression 參數分支為 5 passed，限定 Ruff 通過。此文件工作未重跑程式。／眉保护缓存最多 8 项，嘴型变化复用；相关回归 13 passed，最后参数分支补测 5 passed，限定 Ruff 通过。／The brow cache is bounded to eight entries keyed by brow content, dimensions, and expression. On a 465 canvas, warm median/p95 were 0.1925/0.2594 ms; first initialization was 28.34 ms. Related regression passed 13 tests; the subsequent expression-branch correction passed five tests and scoped Ruff. Documentation did not rerun code.／眉保護キャッシュは最大 8 件で、口形の変化では再計算しません。465 画布の warm 中央値/p95 は 0.1925/0.2594 ms、初期化を含む初回は 28.34 ms。関連回帰は 13 件、後続の表情引数の修正は 5 件成功し、対象 Ruff も成功しています。

證據／证据／Evidence／証拠：本批次 `cross-angle-makeup-poses-native-20260912-01/` 的 `edge-repair-receipt.json`、`edge-repair-v1-backup/`、各姿勢 `source-v1-v2-edge-closeup.png` 與 `source-v1-v2-face.png`、`brow-runtime-preservation.json`、`guard-performance.json`、`anchor-profile-verification.json`。細邊比較使用 PNG，不依賴 JPEG 色度取樣。／Fine-edge comparisons use lossless PNG rather than JPEG chroma sampling.

### 先前階段紀錄／先前阶段记录／Earlier-stage history／以前の段階の記録

### 2026-09-12 最新預設整合狀態／最新默认集成状态／Current default integration／現在の既定統合

**繁體中文。** 使用者明確批准：「我批准了，可以替換預設素材了。另外繼續完成跨角度一致的可選彩妝」。正式來源為 `assets/expressions/source-bound-exasperated/`，批准原文、來源 SHA 與逐檔安裝 SHA 記於該目錄 `receipt.json`。本次僅新無奈 `front-exasperated` 的七個原生可拆分層、rest 與 mid/open/round 嘴型、衣裝及 replace mask 接入預設；其餘姿勢與角度沿用現有路徑。舊七姿勢撤回批次未重新啟用。跨角度一致的可選彩妝持續製作，`cosmetics_status=not_approved`，目前新無奈維持素顏。這不代表 31 角度、完整全身或發布完成。

**简体中文。** 用户已明确批准替换默认素材，并要求继续完成跨角度一致的可选彩妆。正式目录为 `assets/expressions/source-bound-exasperated/`；批准原文、来源和安装 SHA 见 `receipt.json`。本次仅新无奈 `front-exasperated` 的七个原生可拆图层、rest 与 mid/open/round 嘴型、衣装及 replace mask 接入默认；其他姿势与角度沿用原路径，旧七姿势撤回批次未重新启用。可选彩妆仍在制作且未获批准，新无奈保持素颜。不代表 31 个角度、完整全身或发布完成。

**English.** The owner explicitly authorized default replacement and requested continued work on consistent optional makeup across angles. The formal installation is `assets/expressions/source-bound-exasperated/`; its `receipt.json` preserves the owner statement, source SHA, and installed file hashes. Only the new `front-exasperated` portrait's seven native detachable parts, rest and mid/open/round mouths, garment, and replacement mask enter the default path. Other poses and angles retain their existing paths; the withdrawn seven-pose batch remains disabled. Optional cross-angle cosmetics remain in progress and unapproved, so this portrait remains without optional makeup. This does not certify 31 angles, a complete full body, or a release.

**日本語。** 所有者は既定素材の置き換えを明示的に承認し、角度間で一貫した任意の化粧の制作継続を指示しました。正式素材は `assets/expressions/source-bound-exasperated/` にあり、`receipt.json` に承認文、原画 SHA、配置ファイルの SHA を保存しています。既定経路に導入するのは、新しい `front-exasperated` のネイティブ分離可能な 7 パーツ、rest と mid/open/round の口形、衣装と replace mask のみです。他の姿勢と角度は従来の経路を使い、撤回した 7 姿勢の素材は再有効化していません。任意の化粧は制作中で未承認のため、この姿勢は素顔を維持します。31 角度、全身全体、リリースの完了を意味しません。

### 執行期與驗證／运行时与验证／Runtime and validation／実行時と検証

- `application/service_container.py:face_renderer_factory` 在未設定 `MOHAN_EXASPERATED_CANDIDATE_DIR` 時解析正式目錄並呼叫 `validate_formal_exasperated_install`；正式衣裝缺失會報錯。環境變數僅保留絕對路徑候選覆寫。／未设置环境变量时使用并验证正式目录；缺失正式衣装会报错，仅保留绝对路径候选覆盖。／Without the environment override, the factory resolves and validates the formal directory and rejects missing formal appearance; candidate overrides must be absolute paths.／環境変数による上書きがなければ正式ディレクトリを検証し、正式衣装の欠落はエラーにします。候補の上書きは絶対パスに限ります。
- 受影響的正式預設、原候選、語音、眨眼、分層及封裝檢查共 48 passed（exit 0）；隔離手區域與相依注入回歸另有 3 passed（exit 0），修正了測試假資源路徑只對 `.` 生效。最後一次全庫 `ruff check .` exit 0。文件修改未重跑程式測試。／受影响的默认、候选、语音、眨眼、分层和打包检查共 48 passed（exit 0）；隔离手区域与依赖注入另有 3 passed（exit 0），测试假资源路径仅对 `.` 生效。最后一次全库 `ruff check .` exit 0；文档修改未重跑程序测试。／The affected default, candidate, speech, blink, layering, and packaging checks passed 48 tests (exit 0). Isolated hand-region and dependency-injection checks passed three more (exit 0) after limiting the test resource override to `.`. The final repository-wide `ruff check .` exited 0; documentation edits did not rerun code tests.／既定経路、候補、音声、まばたき、レイヤー、梱包の関連検査は 48 件成功（exit 0）、手領域の分離と依存性注入は追加で 3 件成功（exit 0）しました。テスト用の資源パス上書きは `.` のみに限定しました。最後の全リポジトリ `ruff check .` は exit 0 で、文書編集後にコードのテストは再実行していません。
- 正式收據 SHA-256 `29eb66ec6bc413d5bac37c17c753ccfc75f364dfa20aebc98b395b9a4940e633`；正式目錄共 16 檔，其中 12 張 PNG 均為 1254×1254 RGBA。衣裝核准檔路徑以安裝根目錄為基準（`path_base=install_root`）；審閱頁 SHA、使用者原文及逐檔 SHA 均留於正式收據。／正式收据 SHA-256 如上；目录共 16 个文件，其中 12 张 PNG 均为 1254×1254 RGBA。衣装批准文件路径以安装根目录为基准，审核页 SHA、用户原文和逐文件 SHA 均见收据。／The formal receipt SHA-256 is shown above; the directory has 16 files, including 12 PNGs at 1254×1254 RGBA. The garment approval path is relative to the installation root (`path_base=install_root`); the receipt records the reviewed page SHA, owner statement, and every installed file hash.／正式な受領記録の SHA-256 は上記のとおりです。16 ファイル中 12 枚の PNG はすべて 1254×1254 RGBA です。衣装承認ファイルのパスは配置ルートを基準とし、審査ページの SHA、所有者の承認文、全ファイルの SHA は受領記録に保存しています。
- 獨立 Qt/PIL 驗證：alpha 一致，不透明 RGB 最大差 1，預乘 RGB 最大差 1.985；不宣稱完整 RGBA 相同。／独立 Qt/PIL 验证 alpha 一致，不透明 RGB 最大差 1，预乘 RGB 最大差 1.985，不宣称完整 RGBA 相同。／Independent Qt/PIL comparison has identical alpha, maximum opaque RGB difference 1, and maximum premultiplied RGB difference 1.985; full RGBA equality is not claimed.／独立した Qt/PIL 比較では alpha は一致し、不透明 RGB の最大差は 1、事前乗算 RGB の最大差は 1.985 です。全 RGBA の一致は主張しません。

### 以下為先前階段紀錄，預設狀態以上方最新紀錄為準／以下为历史记录／Earlier-stage history; current status above takes precedence／以下は過去の段階の記録です

### 2026-09-12 半身接合修復退回重做

使用者否決三張腕部重組與 35 格動態合成。全庫 Ruff 47 項已修正，但素材正式整合未完成。失敗的 49 PNG + manifest 已完整保留移出預設 assets/expressions/detachable 路徑，舊 receipt 的接合判定已撤回。現況、證據與待辦見 scratchpad/seam-repair-current-status-20260912.md；新 imagegen 三張來源候選等待目視判斷，不得視為已核准素材。


### 2026-09-12 無奈原圖已核准、原生可見分層完成

無奈重生原圖已獲「這張可以」核准。7 個原生可見分區重組一致；共同產線只完成支援的 4 角色及剩餘前景，尚非完整素體或正式執行期。三種新嘴型已取回核准原圖，遮罩外像素一致，等待新嘴型目視確認。最新來源、SHA、對照與限制見 scratchpad/seam-repair-current-status-20260912.md 的最新段落。

### 2026-09-12 無奈衣裝與嘴型產品候選接線

三嘴與新衣裝已核准，已接單一 MOHAN_EXASPERATED_CANDIDATE_DIR opt-in 產品路徑，七部件與可拆衣裝、來源綁定嘴型均有實際465畫布驗證。新彩妝不採用，保持核准素顏；預設資產仍未替換。runtime31、appearance19、架構10、文件9測試通過，全庫Ruff通過。完整證據與未完成項目見 scratchpad/seam-repair-current-status-20260912.md 最新段落及其 root-integration-checkpoint.json。

本文件記錄 MoHan-PC-Desktop-Assistant 專案的發行交接資訊，供後續維護者與協作者參考。

### 最新發行狀態

- 版本：v4.2.1
- 發行狀態：已完成發行
- 標籤：`v4.2.1`
- 來源分支：`release/v4.2.1`（合併後已完成分支清理）
- 目標分支：`main`

### 本次完成的改善（v4.2.1）

- 全身動態一致性：先前 placeholder 版本的 `resolve_speech` 回傳 `None`，說話時採用靜態嘴型，legacy 表情路徑也會重置 `_adaptive_full_body_active`。v4.2.1 將全身渲染與嘴型動態整合為同一條穩定路徑。
- 嘴型同步：實作 `resolve_speech` 從 `.hands.json` 的 `protected_regions.face` 讀取臉部座標，產生程序化嘴型圖層，並讓 `update_speech_layers` 在嘴型閉合時回到靜態照片。
- 揮手回應：`set_state` 在全身模式下跳過 legacy 表情切換，保留肢體動畫，讓揮手/走動仍有可見的肢體回應。

### 發行流程記錄

- 完整回歸測試 280/280 全綠。
- squash 合併 PR，建立標籤 `v4.2.1` 並推送，觸發 release.yml。
- 產出正式 Release（draft=false、prerelease=false）。

### 後續維護注意事項

- 發行來源（分支、合併後 main、版本、標籤、GitHub Release）必須指向同一不可變提交。
- 遵循 PUBLISHING.md 的 squash-only 與四語治理規範。
- 遵循 .clinerules.md 的排除清單與 Token 節省規範。

## 简体中文

### 2026-09-12 正式彩妝安裝完成範圍／正式彩妆安装范围／Formal makeup installation scope／正式な化粧配置の範囲

* 使用者「採用這組配色」的批准已落實：30-view archive（24 yaw + 6 named pose）已正式安裝，新無奈的 12 個嘴型專屬彩妝另走 source-bound 分流。這是本輪可選彩妝安裝完成，原先 47 項指全庫 Ruff 診斷，已修正且全庫 Ruff 通過；本次不代表完整全身、31-view 逐張人工外觀驗收或發布完成；既有使用者 store 未修改。／用户批准的配色已落实：30-view archive 正式安装，新无奈 12 个嘴型专属彩妆独立分流；原先 47 项指全库 Ruff 诊断，已修正且全库 Ruff 通过；本次不代表完整全身、31-view 逐张人工验收或发布完成，既有用户 store 未修改。／The approved palette is installed in the 30-view archive, with 12 mouth-specific cosmetic layers for the new exasperated portrait routed separately. The earlier 47 refers to repository-wide Ruff findings, which were fixed and now pass. This optional-makeup installation does not certify a complete full body, individual human acceptance of all 31 views, or a release. Existing user stores were not modified.／承認済み配色を 30-view archive に正式配置し、新しい無奈の口形別化粧 12 レイヤーは独立した経路に配置しました。先の 47 件は全庫 Ruff の指摘で、修正済みかつ全庫 Ruff は成功しています。今回の任意化粧の配置は、全身全体、31 view の個別目視受入れ、公開の完了を意味しません。既存ユーザー store は変更していません。
* 正式 archive 與安裝 receipt 的 SHA 已唯讀核對，詳見下方證據。原 archive 已備份；原 foundation 與 archive 內舊無奈成員保留，新無奈產品使用獨立來源。正式 factory 無環境變數時 cosmetics_available=true，appearance 共 14 層（12 妝 + 衣裝/replace）。／正式 archive 和 receipt SHA 已核对，旧 archive 已备份；foundation 与 archive 原无奈成员保留。默认 factory 无环境变量时 14 层 appearance 可用。／Formal archive and receipt hashes were independently verified; the previous archive is backed up, with foundation and legacy archive exasperated members preserved. Without an environment override, the formal factory exposes cosmetics_available=true and 14 appearance layers: 12 cosmetics plus garment and replacement mask.／正式 archive と receipt の SHA を独立確認し、旧 archive をバックアップしました。foundation と archive 内の旧無奈素材は保持しています。環境変数なしの正式 factory では cosmetics_available=true、appearance は化粧 12 と衣装・replace の計 14 レイヤーです。
* 六 named pose 的新增亮紫線已消除，原圖淡邊保持；輪廓 3 px 帶無彩妝，原輪廓 RGBA 差 0。最終另移除四個 closed 圖的耳前髮際孤島與六姿勢 12 個眼層的眉區溢出，僅托腮安全區右端擴 1 px 收入實際睫毛。+030 closed 的 1,338 個藍邊像素與 -090 rest 的 685 個藍邊像素在 bare/classic 相同，經原生圖、Qt 直接解碼與產品逐像素追溯，皆為 Alpha 1–7 的 8-bit 預乘量化；灰底每頻道誤差低於 1/255，不能據此認定原生圖有可見純藍缺陷。／新增亮紫线已消除，原图淡边保留；另清除闭眼耳前孤岛与眉区溢出，只有托腮安全区右端增加 1 px 实际睫毛。+030 closed 的 1,338 和 -090 rest 的 685 个蓝边像素在 bare/classic 相同，追溯为 Alpha 1–7 的 8-bit 预乘量化；灰底每通道误差低于 1/255，不据此认定原图存在可见纯蓝缺陷。／The added bright purple fringe is removed while the faint original edge is preserved; the 3 px contour band has no pigment and source-edge RGBA difference is zero. Final corrections removed four closed-state preauricular hairline islands and brow spill in 12 eye layers across six poses; only cheek-rest's right safe-region edge grew by 1 px to include a real lash. The 1,338 blue-edge pixels in +030 closed and 685 in -090 rest are identical in bare/classic and arise from 8-bit premultiplied conversion at Alpha 1–7, reproduced by direct Qt decoding of the raw authority. Gray-background channel error is below 1/255; this does not establish a visible pure-blue defect in the native art.／追加された鮮やかな紫線を除去し、原画の淡い縁色を保持しました。輪郭 3 px に化粧はなく、原輪郭 RGBA の差は 0 です。最終修正で閉眼 4 枚の耳前生え際の孤立部分と 6 姿勢 12 眼レイヤーの眉へのはみ出しを除き、托腮のみ実際のまつ毛のため安全領域右端を 1 px 広げました。+030 closed の青い縁 1,338 ピクセルと -090 rest の 685 ピクセルは bare/classic で同じで、Alpha 1–7 の 8-bit 事前乗算の量子化に由来し、原画の Qt 直接読込でも再現します。灰色背景での各チャンネル誤差は 1/255 未満であり、原画に視認可能な純青の欠陥があるとは判定できません。
* 藍邊追溯證據／蓝边溯源证据／Blue-edge provenance evidence／青い縁の由来の証拠：`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.json`、`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.md`。
* 驗證為分批受影響範圍：49 張真產品 QA 圖通過；runtime/appearance/browguard/packbuilder 39 passed（39.03 s），文件/changelog/分層檢查測試 23 passed（1.58 s），另 25 項受影響測試及安裝後 12 項 store/cache 測試通過（後者 24.13 s）。全庫 Ruff 通過；分層 import checker 330 模組通過，只新增 service_container→exasperated_candidate_assets 精確組合邊。這不是全庫測試套件全跑。／验证按受影响范围分批执行：49 张真产品图、39+23 项主线测试、另 25 项及安装后 12 项通过；全库 Ruff 和 330 模块 import checker 通过，不等于全库测试全跑。／Validation was scoped: 49 actual product QA frames passed; 39 runtime/appearance/browguard/packbuilder tests passed in 39.03 s, 23 documentation/changelog/layered-checker tests in 1.58 s, a separate 25 affected tests passed, and 12 post-installation store/cache tests passed in 24.13 s. Full-repository Ruff and the 330-module import checker passed; only the exact service_container→exasperated_candidate_assets composition edge was registered. This was not a full-repository test-suite run.／検証は影響範囲ごとに実施しました。実際の製品 QA 49 画像、runtime 等 39 件（39.03 秒）、文書等 23 件（1.58 秒）、別の関連 25 件、配置後 store/cache 12 件（24.13 秒）が成功しました。全庫 Ruff と 330 モジュールの import checker も成功し、service_container→exasperated_candidate_assets の正確な構成辺のみ登録しました。全テストスイートの実行ではありません。

證據／证据／Evidence／証拠：

* `assets/official-packs/mohan.makeup.builtin.mohan-outfit`: SHA-256 `2a92685c89f97e9799d7c8ba7ea8c65859cfef400008bcded5e838c16fbf2a84`.
* `B/cross-angle-makeup-approved-integration-20260912-01/formal-native30-install-receipt.json`: SHA-256 `284a2cc8bf3d7570ac88f6a8350132861ad56f75d45408f8b390f7a28ba64979`.
* `B/cross-angle-makeup-approved-integration-20260912-01/official-makeup-before-native30.mohan-outfit`: SHA-256 `51ee53cfbf0e082e18be7d1af775a331a61aad60d7e51ec36453aa4c57b461a6`.
* `B/cross-angle-makeup-product-qa-20260912-01/native30-qa-20260912-01/receipt.json`: SHA-256 `fb959b2ba6789fde54f4eeb6f7c6dc1ede37c2b1f6d7641b113b5a11679054b8`.
* 新無奈／新无奈／Exasperated／無奈 `assets/expressions/source-bound-exasperated/receipt.json`: SHA-256 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`.

`B` = `scratchpad/v4-identity-rebuild-20260905/v4-hanfu-alignment-20260910/source-bound-halfbody-sword-sync-20260911-01`.

### 以下保留先前階段紀錄，以本節最終狀態為準／以下保留历史记录／Earlier-stage history follows; this final status takes precedence／以下は過去の記録であり、本節の最終状態を優先します

### 2026-09-12 配色批准與輪廓修正／配色批准与轮廓修正／Palette approval and edge correction／配色承認と輪郭修正

**繁體中文。** 使用者已明確表示「採用這組配色」。此為跨角度可選彩妝配色批准，不等於逐張素材再次核准或完整全身驗收。整合分為 30 個既有 view 的 archive（24 yaw + 6 named pose）與新無奈獨立來源分流；新無奈依 rest/mid/open/round 保留嘴型專屬唇支持。新無奈彩妝正式安裝已確認；30-view archive 尚未完成，詳見下方安裝證據。

**简体中文。** 用户已明确表示“采用这组配色”。这是跨角度可选彩妆配色批准，不等于逐张资源再次批准或完整全身验收。集成分为 30 个既有 view 的 archive（24 yaw + 6 named pose）与新无奈独立来源路径；新无奈按 rest/mid/open/round 保留各嘴型唇部支持。新无奈彩妆正式安装已确认；30-view archive 尚未完成，见下方证据。

**English.** The owner approved this palette. This approves the optional cross-angle color scheme, not a second per-image approval or complete full-body acceptance. Integration separates a 30-view archive (24 yaw views and six named poses) from the new source-bound exasperated portrait, whose rest/mid/open/round states retain separate lip supports. Formal cosmetic installation is confirmed for the new exasperated portrait; the 30-view archive remains pending, as detailed below.

**日本語。** 所有者はこの配色の採用を承認しました。これは角度間で一貫した任意の化粧の配色承認であり、各素材の再承認や全身全体の受入れではありません。統合は 30 view の archive（24 yaw と 6 named pose）と新しい無奈の独立した原画対応経路に分け、無奈の rest/mid/open/round はそれぞれの唇支持を維持します。新しい無奈の化粧は正式配置を確認済みですが、30-view archive は未完了です。詳細は以下に記録します。

### 新無奈安裝已確認、30-view archive 尚未完成／新无奈已安装、30-view archive 待完成／Exasperated installed; 30-view archive pending／無奈は配置済み、30-view archive は未完了

**繁體中文。** 新無奈的 12 個可選彩妝圖層已正式安裝到 `assets/expressions/source-bound-exasperated/`；主線回報 `validate_formal_exasperated_install` exit 0。現有七 parts、三嘴型、衣裝、replace mask、批准檔與 base manifest 的 SHA 均保留。共 28 個被 receipt 釘選的非 receipt 檔、29 個總檔，其中 24 PNG。正式 receipt SHA 已唯讀核對為 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`；安裝前備份位於本批次 `cross-angle-makeup-approved-integration-20260912-01/exasperated-before-makeup/`。30-view archive 仍在組包，safe-region 真閘門正在修正，不能宣稱全批完成。

**简体中文。** 新无奈的 12 个可选彩妆图层已正式安装，主线验证 exit 0；原七 parts、三嘴型、衣装、replace mask、批准文件和 base manifest SHA 保持相同。共 28 个被 receipt 固定的非 receipt 文件、29 个总文件，其中 24 PNG；receipt SHA 与上述值一致，旧文件已备份。30-view archive 仍在组包并修正 safe-region 验证失败，未全部完成。

**English.** Twelve optional cosmetic layers are formally installed for the new exasperated portrait; the main agent reports successful formal validation. Hashes of the prior seven parts, three mouths, garment, replacement mask, approval file, and base manifest remain unchanged. There are 28 pinned non-receipt files, 29 files in total, and 24 PNGs. The receipt hash above was independently read and verified; the pre-installation copy is retained at the backup path above. The 30-view archive is still being packaged, with a genuine safe-region gate failure under correction. Overall completion is not claimed.

**日本語。** 新しい無奈の任意の化粧 12 レイヤーは正式配置済みで、主担当は正式検証の exit 0 を報告しています。既存の 7 parts、3 口形、衣装、replace mask、承認ファイル、base manifest の SHA は保持しています。receipt が固定する本体ファイルは 28 件、合計 29 件、そのうち PNG は 24 件です。上記 receipt SHA は読み取りで独立確認し、配置前のバックアップも保存しています。30-view archive は組み立て中で、safe-region 検証の失敗を修正しており、全体の完了は主張しません。

### 確認過的修正與限制／已确认的修正与限制／Verified corrections and limits／確認済みの修正と制限

- 六 named pose 已收斂彩妝 alpha：只使用原圖不透明輪廓內側，輪廓 3 px 帶為零顏料，向內 4 px 柔化。托腮彩妝新增的亮紫線已消除；原圖本身極淡邊色保留，未修改原 RGB 或輪廓。六姿勢 × 三狀態的輪廓 RGBA 與灰底改變均為 0。／六个 named pose 的彩妆 alpha 已限制在原图不透明内部，轮廓 3 px 带无颜料，向内 4 px 柔化；新增亮紫线已消除，原图淡边保留，18 个姿势状态的轮廓和灰底变化均为 0。／Pigment alpha is confined inside the opaque source, with a clear 3 px contour band and a 4 px inward transition. The added bright purple line is removed; the faint original fringe remains, with no source RGB or contour edits. All 18 pose/state edge and gray-background comparisons are unchanged.／化粧 alpha を不透明な原画の内側に限定し、輪郭 3 px は無色、さらに内側 4 px でなじませました。追加された鮮やかな紫線は除去しましたが、原画の淡い縁色は保持しています。原 RGB と輪郭は編集せず、18 姿勢状態の輪郭と灰色背景の差は 0 です。
- 三 gesture 的 speaking+closed 使用真產品眨眼合成；眉保護依原眉與對位後 donor 眉形狀排除，沒有用水平裁線或關閉眨眼掩蓋問題。mock-hit 的真眼部偏移為顯示座標 (0,2)，對應原生約 (0,5.394)；其 closed 材料已依實際 profile 更正。／三个 gesture 使用真实产品闭眼合成，按原眉和对位后 donor 眉形保护；mock-hit 的显示偏移 (0,2) 已反映在闭眼材料。／The three gesture closed states use actual product blink composition with source-shaped protection of original and aligned donor brows. Mock-hit's real display offset (0,2), approximately (0,5.394) natively, is reflected in its closed material.／3 gesture の閉眼は実際の製品合成を使用し、原眉と位置合わせ後の donor 眉の形状を保護します。mock-hit の実際の表示座標 (0,2)、原生座標で約 (0,5.394) を閉眼素材に反映しました。
- 眉保護快取上限 8 筆，以眉區內容、尺寸、表情為鍵；嘴型改變不重算。465 畫布 warm 中位 0.1925 ms、p95 0.2594 ms，首次含 CV 初始化 28.34 ms。相關回歸曾 13 passed；最後補測 expression 參數分支為 5 passed，限定 Ruff 通過。此文件工作未重跑程式。／眉保护缓存最多 8 项，嘴型变化复用；相关回归 13 passed，最后参数分支补测 5 passed，限定 Ruff 通过。／The brow cache is bounded to eight entries keyed by brow content, dimensions, and expression. On a 465 canvas, warm median/p95 were 0.1925/0.2594 ms; first initialization was 28.34 ms. Related regression passed 13 tests; the subsequent expression-branch correction passed five tests and scoped Ruff. Documentation did not rerun code.／眉保護キャッシュは最大 8 件で、口形の変化では再計算しません。465 画布の warm 中央値/p95 は 0.1925/0.2594 ms、初期化を含む初回は 28.34 ms。関連回帰は 13 件、後続の表情引数の修正は 5 件成功し、対象 Ruff も成功しています。

證據／证据／Evidence／証拠：本批次 `cross-angle-makeup-poses-native-20260912-01/` 的 `edge-repair-receipt.json`、`edge-repair-v1-backup/`、各姿勢 `source-v1-v2-edge-closeup.png` 與 `source-v1-v2-face.png`、`brow-runtime-preservation.json`、`guard-performance.json`、`anchor-profile-verification.json`。細邊比較使用 PNG，不依賴 JPEG 色度取樣。／Fine-edge comparisons use lossless PNG rather than JPEG chroma sampling.

### 先前階段紀錄／先前阶段记录／Earlier-stage history／以前の段階の記録

### 2026-09-12 最新預設整合狀態／最新默认集成状态／Current default integration／現在の既定統合

**繁體中文。** 使用者明確批准：「我批准了，可以替換預設素材了。另外繼續完成跨角度一致的可選彩妝」。正式來源為 `assets/expressions/source-bound-exasperated/`，批准原文、來源 SHA 與逐檔安裝 SHA 記於該目錄 `receipt.json`。本次僅新無奈 `front-exasperated` 的七個原生可拆分層、rest 與 mid/open/round 嘴型、衣裝及 replace mask 接入預設；其餘姿勢與角度沿用現有路徑。舊七姿勢撤回批次未重新啟用。跨角度一致的可選彩妝持續製作，`cosmetics_status=not_approved`，目前新無奈維持素顏。這不代表 31 角度、完整全身或發布完成。

**简体中文。** 用户已明确批准替换默认素材，并要求继续完成跨角度一致的可选彩妆。正式目录为 `assets/expressions/source-bound-exasperated/`；批准原文、来源和安装 SHA 见 `receipt.json`。本次仅新无奈 `front-exasperated` 的七个原生可拆图层、rest 与 mid/open/round 嘴型、衣装及 replace mask 接入默认；其他姿势与角度沿用原路径，旧七姿势撤回批次未重新启用。可选彩妆仍在制作且未获批准，新无奈保持素颜。不代表 31 个角度、完整全身或发布完成。

**English.** The owner explicitly authorized default replacement and requested continued work on consistent optional makeup across angles. The formal installation is `assets/expressions/source-bound-exasperated/`; its `receipt.json` preserves the owner statement, source SHA, and installed file hashes. Only the new `front-exasperated` portrait's seven native detachable parts, rest and mid/open/round mouths, garment, and replacement mask enter the default path. Other poses and angles retain their existing paths; the withdrawn seven-pose batch remains disabled. Optional cross-angle cosmetics remain in progress and unapproved, so this portrait remains without optional makeup. This does not certify 31 angles, a complete full body, or a release.

**日本語。** 所有者は既定素材の置き換えを明示的に承認し、角度間で一貫した任意の化粧の制作継続を指示しました。正式素材は `assets/expressions/source-bound-exasperated/` にあり、`receipt.json` に承認文、原画 SHA、配置ファイルの SHA を保存しています。既定経路に導入するのは、新しい `front-exasperated` のネイティブ分離可能な 7 パーツ、rest と mid/open/round の口形、衣装と replace mask のみです。他の姿勢と角度は従来の経路を使い、撤回した 7 姿勢の素材は再有効化していません。任意の化粧は制作中で未承認のため、この姿勢は素顔を維持します。31 角度、全身全体、リリースの完了を意味しません。

### 執行期與驗證／运行时与验证／Runtime and validation／実行時と検証

- `application/service_container.py:face_renderer_factory` 在未設定 `MOHAN_EXASPERATED_CANDIDATE_DIR` 時解析正式目錄並呼叫 `validate_formal_exasperated_install`；正式衣裝缺失會報錯。環境變數僅保留絕對路徑候選覆寫。／未设置环境变量时使用并验证正式目录；缺失正式衣装会报错，仅保留绝对路径候选覆盖。／Without the environment override, the factory resolves and validates the formal directory and rejects missing formal appearance; candidate overrides must be absolute paths.／環境変数による上書きがなければ正式ディレクトリを検証し、正式衣装の欠落はエラーにします。候補の上書きは絶対パスに限ります。
- 受影響的正式預設、原候選、語音、眨眼、分層及封裝檢查共 48 passed（exit 0）；隔離手區域與相依注入回歸另有 3 passed（exit 0），修正了測試假資源路徑只對 `.` 生效。最後一次全庫 `ruff check .` exit 0。文件修改未重跑程式測試。／受影响的默认、候选、语音、眨眼、分层和打包检查共 48 passed（exit 0）；隔离手区域与依赖注入另有 3 passed（exit 0），测试假资源路径仅对 `.` 生效。最后一次全库 `ruff check .` exit 0；文档修改未重跑程序测试。／The affected default, candidate, speech, blink, layering, and packaging checks passed 48 tests (exit 0). Isolated hand-region and dependency-injection checks passed three more (exit 0) after limiting the test resource override to `.`. The final repository-wide `ruff check .` exited 0; documentation edits did not rerun code tests.／既定経路、候補、音声、まばたき、レイヤー、梱包の関連検査は 48 件成功（exit 0）、手領域の分離と依存性注入は追加で 3 件成功（exit 0）しました。テスト用の資源パス上書きは `.` のみに限定しました。最後の全リポジトリ `ruff check .` は exit 0 で、文書編集後にコードのテストは再実行していません。
- 正式收據 SHA-256 `29eb66ec6bc413d5bac37c17c753ccfc75f364dfa20aebc98b395b9a4940e633`；正式目錄共 16 檔，其中 12 張 PNG 均為 1254×1254 RGBA。衣裝核准檔路徑以安裝根目錄為基準（`path_base=install_root`）；審閱頁 SHA、使用者原文及逐檔 SHA 均留於正式收據。／正式收据 SHA-256 如上；目录共 16 个文件，其中 12 张 PNG 均为 1254×1254 RGBA。衣装批准文件路径以安装根目录为基准，审核页 SHA、用户原文和逐文件 SHA 均见收据。／The formal receipt SHA-256 is shown above; the directory has 16 files, including 12 PNGs at 1254×1254 RGBA. The garment approval path is relative to the installation root (`path_base=install_root`); the receipt records the reviewed page SHA, owner statement, and every installed file hash.／正式な受領記録の SHA-256 は上記のとおりです。16 ファイル中 12 枚の PNG はすべて 1254×1254 RGBA です。衣装承認ファイルのパスは配置ルートを基準とし、審査ページの SHA、所有者の承認文、全ファイルの SHA は受領記録に保存しています。
- 獨立 Qt/PIL 驗證：alpha 一致，不透明 RGB 最大差 1，預乘 RGB 最大差 1.985；不宣稱完整 RGBA 相同。／独立 Qt/PIL 验证 alpha 一致，不透明 RGB 最大差 1，预乘 RGB 最大差 1.985，不宣称完整 RGBA 相同。／Independent Qt/PIL comparison has identical alpha, maximum opaque RGB difference 1, and maximum premultiplied RGB difference 1.985; full RGBA equality is not claimed.／独立した Qt/PIL 比較では alpha は一致し、不透明 RGB の最大差は 1、事前乗算 RGB の最大差は 1.985 です。全 RGBA の一致は主張しません。

### 以下為先前階段紀錄，預設狀態以上方最新紀錄為準／以下为历史记录／Earlier-stage history; current status above takes precedence／以下は過去の段階の記録です

### 2026-09-12 半身接合修復退回重做

使用者否決三張腕部重組與 35 格動態合成。全庫 Ruff 47 項已修正，但素材正式整合未完成。失敗的 49 PNG + manifest 已完整保留移出預設 assets/expressions/detachable 路徑，舊 receipt 的接合判定已撤回。現況、證據與待辦見 scratchpad/seam-repair-current-status-20260912.md；新 imagegen 三張來源候選等待目視判斷，不得視為已核准素材。


### 2026-09-12 無奈原圖已核准、原生可見分層完成

無奈重生原圖已獲「這張可以」核准。7 個原生可見分區重組一致；共同產線只完成支援的 4 角色及剩餘前景，尚非完整素體或正式執行期。三種新嘴型已取回核准原圖，遮罩外像素一致，等待新嘴型目視確認。最新來源、SHA、對照與限制見 scratchpad/seam-repair-current-status-20260912.md 的最新段落。

### 2026-09-12 無奈衣裝與嘴型產品候選接線

三嘴與新衣裝已核准，已接單一 MOHAN_EXASPERATED_CANDIDATE_DIR opt-in 產品路徑，七部件與可拆衣裝、來源綁定嘴型均有實際465畫布驗證。新彩妝不採用，保持核准素顏；預設資產仍未替換。runtime31、appearance19、架構10、文件9測試通過，全庫Ruff通過。完整證據與未完成項目見 scratchpad/seam-repair-current-status-20260912.md 最新段落及其 root-integration-checkpoint.json。

本文件记录 MoHan-PC-Desktop-Assistant 项目的发行交接信息，供后续维护者与协作者参考。

### 最新发行状态

- 版本：v4.2.1
- 发行状态：已完成发行
- 标签：`v4.2.1`
- 来源分支：`release/v4.2.1`（合并后已完成分支清理）
- 目标分支：`main`

### 本次完成的改进（v4.2.1）

- 全身动态一致性：先前 placeholder 版本的 `resolve_speech` 返回 `None`，说话时采用静态口型，legacy 表情路径也会重置 `_adaptive_full_body_active`。v4.2.1 将全身渲染与口型动态整合为同一条稳定路径。
- 嘴型同步：实现 `resolve_speech` 从 `.hands.json` 的 `protected_regions.face` 读取脸部坐标，产生程序化嘴型图层，并让 `update_speech_layers` 在嘴型闭合时回到静态照片。
- 挥手回应：`set_state` 在全身模式下跳过 legacy 表情切换，保留肢体动画，让挥手/走动仍有可见的肢体回应。

### 发行流程记录

- 完整回归测试 280/280 全绿。
- squash 合并 PR，建立标签 `v4.2.1` 并推送，触发 release.yml。
- 产出正式 Release（draft=false、prerelease=false）。

### 后续维护注意事项

- 发行来源（分支、合并后 main、版本、标签、GitHub Release）必须指向同一不可变提交。
- 遵循 PUBLISHING.md 的 squash-only 与四语治理规范。
- 遵循 .clinerules.md 的排除清单与 Token 节省规范。

## English

### 2026-09-12 正式彩妝安裝完成範圍／正式彩妆安装范围／Formal makeup installation scope／正式な化粧配置の範囲

* 使用者「採用這組配色」的批准已落實：30-view archive（24 yaw + 6 named pose）已正式安裝，新無奈的 12 個嘴型專屬彩妝另走 source-bound 分流。這是本輪可選彩妝安裝完成，原先 47 項指全庫 Ruff 診斷，已修正且全庫 Ruff 通過；本次不代表完整全身、31-view 逐張人工外觀驗收或發布完成；既有使用者 store 未修改。／用户批准的配色已落实：30-view archive 正式安装，新无奈 12 个嘴型专属彩妆独立分流；原先 47 项指全库 Ruff 诊断，已修正且全库 Ruff 通过；本次不代表完整全身、31-view 逐张人工验收或发布完成，既有用户 store 未修改。／The approved palette is installed in the 30-view archive, with 12 mouth-specific cosmetic layers for the new exasperated portrait routed separately. The earlier 47 refers to repository-wide Ruff findings, which were fixed and now pass. This optional-makeup installation does not certify a complete full body, individual human acceptance of all 31 views, or a release. Existing user stores were not modified.／承認済み配色を 30-view archive に正式配置し、新しい無奈の口形別化粧 12 レイヤーは独立した経路に配置しました。先の 47 件は全庫 Ruff の指摘で、修正済みかつ全庫 Ruff は成功しています。今回の任意化粧の配置は、全身全体、31 view の個別目視受入れ、公開の完了を意味しません。既存ユーザー store は変更していません。
* 正式 archive 與安裝 receipt 的 SHA 已唯讀核對，詳見下方證據。原 archive 已備份；原 foundation 與 archive 內舊無奈成員保留，新無奈產品使用獨立來源。正式 factory 無環境變數時 cosmetics_available=true，appearance 共 14 層（12 妝 + 衣裝/replace）。／正式 archive 和 receipt SHA 已核对，旧 archive 已备份；foundation 与 archive 原无奈成员保留。默认 factory 无环境变量时 14 层 appearance 可用。／Formal archive and receipt hashes were independently verified; the previous archive is backed up, with foundation and legacy archive exasperated members preserved. Without an environment override, the formal factory exposes cosmetics_available=true and 14 appearance layers: 12 cosmetics plus garment and replacement mask.／正式 archive と receipt の SHA を独立確認し、旧 archive をバックアップしました。foundation と archive 内の旧無奈素材は保持しています。環境変数なしの正式 factory では cosmetics_available=true、appearance は化粧 12 と衣装・replace の計 14 レイヤーです。
* 六 named pose 的新增亮紫線已消除，原圖淡邊保持；輪廓 3 px 帶無彩妝，原輪廓 RGBA 差 0。最終另移除四個 closed 圖的耳前髮際孤島與六姿勢 12 個眼層的眉區溢出，僅托腮安全區右端擴 1 px 收入實際睫毛。+030 closed 的 1,338 個藍邊像素與 -090 rest 的 685 個藍邊像素在 bare/classic 相同，經原生圖、Qt 直接解碼與產品逐像素追溯，皆為 Alpha 1–7 的 8-bit 預乘量化；灰底每頻道誤差低於 1/255，不能據此認定原生圖有可見純藍缺陷。／新增亮紫线已消除，原图淡边保留；另清除闭眼耳前孤岛与眉区溢出，只有托腮安全区右端增加 1 px 实际睫毛。+030 closed 的 1,338 和 -090 rest 的 685 个蓝边像素在 bare/classic 相同，追溯为 Alpha 1–7 的 8-bit 预乘量化；灰底每通道误差低于 1/255，不据此认定原图存在可见纯蓝缺陷。／The added bright purple fringe is removed while the faint original edge is preserved; the 3 px contour band has no pigment and source-edge RGBA difference is zero. Final corrections removed four closed-state preauricular hairline islands and brow spill in 12 eye layers across six poses; only cheek-rest's right safe-region edge grew by 1 px to include a real lash. The 1,338 blue-edge pixels in +030 closed and 685 in -090 rest are identical in bare/classic and arise from 8-bit premultiplied conversion at Alpha 1–7, reproduced by direct Qt decoding of the raw authority. Gray-background channel error is below 1/255; this does not establish a visible pure-blue defect in the native art.／追加された鮮やかな紫線を除去し、原画の淡い縁色を保持しました。輪郭 3 px に化粧はなく、原輪郭 RGBA の差は 0 です。最終修正で閉眼 4 枚の耳前生え際の孤立部分と 6 姿勢 12 眼レイヤーの眉へのはみ出しを除き、托腮のみ実際のまつ毛のため安全領域右端を 1 px 広げました。+030 closed の青い縁 1,338 ピクセルと -090 rest の 685 ピクセルは bare/classic で同じで、Alpha 1–7 の 8-bit 事前乗算の量子化に由来し、原画の Qt 直接読込でも再現します。灰色背景での各チャンネル誤差は 1/255 未満であり、原画に視認可能な純青の欠陥があるとは判定できません。
* 藍邊追溯證據／蓝边溯源证据／Blue-edge provenance evidence／青い縁の由来の証拠：`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.json`、`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.md`。
* 驗證為分批受影響範圍：49 張真產品 QA 圖通過；runtime/appearance/browguard/packbuilder 39 passed（39.03 s），文件/changelog/分層檢查測試 23 passed（1.58 s），另 25 項受影響測試及安裝後 12 項 store/cache 測試通過（後者 24.13 s）。全庫 Ruff 通過；分層 import checker 330 模組通過，只新增 service_container→exasperated_candidate_assets 精確組合邊。這不是全庫測試套件全跑。／验证按受影响范围分批执行：49 张真产品图、39+23 项主线测试、另 25 项及安装后 12 项通过；全库 Ruff 和 330 模块 import checker 通过，不等于全库测试全跑。／Validation was scoped: 49 actual product QA frames passed; 39 runtime/appearance/browguard/packbuilder tests passed in 39.03 s, 23 documentation/changelog/layered-checker tests in 1.58 s, a separate 25 affected tests passed, and 12 post-installation store/cache tests passed in 24.13 s. Full-repository Ruff and the 330-module import checker passed; only the exact service_container→exasperated_candidate_assets composition edge was registered. This was not a full-repository test-suite run.／検証は影響範囲ごとに実施しました。実際の製品 QA 49 画像、runtime 等 39 件（39.03 秒）、文書等 23 件（1.58 秒）、別の関連 25 件、配置後 store/cache 12 件（24.13 秒）が成功しました。全庫 Ruff と 330 モジュールの import checker も成功し、service_container→exasperated_candidate_assets の正確な構成辺のみ登録しました。全テストスイートの実行ではありません。

證據／证据／Evidence／証拠：

* `assets/official-packs/mohan.makeup.builtin.mohan-outfit`: SHA-256 `2a92685c89f97e9799d7c8ba7ea8c65859cfef400008bcded5e838c16fbf2a84`.
* `B/cross-angle-makeup-approved-integration-20260912-01/formal-native30-install-receipt.json`: SHA-256 `284a2cc8bf3d7570ac88f6a8350132861ad56f75d45408f8b390f7a28ba64979`.
* `B/cross-angle-makeup-approved-integration-20260912-01/official-makeup-before-native30.mohan-outfit`: SHA-256 `51ee53cfbf0e082e18be7d1af775a331a61aad60d7e51ec36453aa4c57b461a6`.
* `B/cross-angle-makeup-product-qa-20260912-01/native30-qa-20260912-01/receipt.json`: SHA-256 `fb959b2ba6789fde54f4eeb6f7c6dc1ede37c2b1f6d7641b113b5a11679054b8`.
* 新無奈／新无奈／Exasperated／無奈 `assets/expressions/source-bound-exasperated/receipt.json`: SHA-256 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`.

`B` = `scratchpad/v4-identity-rebuild-20260905/v4-hanfu-alignment-20260910/source-bound-halfbody-sword-sync-20260911-01`.

### 以下保留先前階段紀錄，以本節最終狀態為準／以下保留历史记录／Earlier-stage history follows; this final status takes precedence／以下は過去の記録であり、本節の最終状態を優先します

### 2026-09-12 配色批准與輪廓修正／配色批准与轮廓修正／Palette approval and edge correction／配色承認と輪郭修正

**繁體中文。** 使用者已明確表示「採用這組配色」。此為跨角度可選彩妝配色批准，不等於逐張素材再次核准或完整全身驗收。整合分為 30 個既有 view 的 archive（24 yaw + 6 named pose）與新無奈獨立來源分流；新無奈依 rest/mid/open/round 保留嘴型專屬唇支持。新無奈彩妝正式安裝已確認；30-view archive 尚未完成，詳見下方安裝證據。

**简体中文。** 用户已明确表示“采用这组配色”。这是跨角度可选彩妆配色批准，不等于逐张资源再次批准或完整全身验收。集成分为 30 个既有 view 的 archive（24 yaw + 6 named pose）与新无奈独立来源路径；新无奈按 rest/mid/open/round 保留各嘴型唇部支持。新无奈彩妆正式安装已确认；30-view archive 尚未完成，见下方证据。

**English.** The owner approved this palette. This approves the optional cross-angle color scheme, not a second per-image approval or complete full-body acceptance. Integration separates a 30-view archive (24 yaw views and six named poses) from the new source-bound exasperated portrait, whose rest/mid/open/round states retain separate lip supports. Formal cosmetic installation is confirmed for the new exasperated portrait; the 30-view archive remains pending, as detailed below.

**日本語。** 所有者はこの配色の採用を承認しました。これは角度間で一貫した任意の化粧の配色承認であり、各素材の再承認や全身全体の受入れではありません。統合は 30 view の archive（24 yaw と 6 named pose）と新しい無奈の独立した原画対応経路に分け、無奈の rest/mid/open/round はそれぞれの唇支持を維持します。新しい無奈の化粧は正式配置を確認済みですが、30-view archive は未完了です。詳細は以下に記録します。

### 新無奈安裝已確認、30-view archive 尚未完成／新无奈已安装、30-view archive 待完成／Exasperated installed; 30-view archive pending／無奈は配置済み、30-view archive は未完了

**繁體中文。** 新無奈的 12 個可選彩妝圖層已正式安裝到 `assets/expressions/source-bound-exasperated/`；主線回報 `validate_formal_exasperated_install` exit 0。現有七 parts、三嘴型、衣裝、replace mask、批准檔與 base manifest 的 SHA 均保留。共 28 個被 receipt 釘選的非 receipt 檔、29 個總檔，其中 24 PNG。正式 receipt SHA 已唯讀核對為 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`；安裝前備份位於本批次 `cross-angle-makeup-approved-integration-20260912-01/exasperated-before-makeup/`。30-view archive 仍在組包，safe-region 真閘門正在修正，不能宣稱全批完成。

**简体中文。** 新无奈的 12 个可选彩妆图层已正式安装，主线验证 exit 0；原七 parts、三嘴型、衣装、replace mask、批准文件和 base manifest SHA 保持相同。共 28 个被 receipt 固定的非 receipt 文件、29 个总文件，其中 24 PNG；receipt SHA 与上述值一致，旧文件已备份。30-view archive 仍在组包并修正 safe-region 验证失败，未全部完成。

**English.** Twelve optional cosmetic layers are formally installed for the new exasperated portrait; the main agent reports successful formal validation. Hashes of the prior seven parts, three mouths, garment, replacement mask, approval file, and base manifest remain unchanged. There are 28 pinned non-receipt files, 29 files in total, and 24 PNGs. The receipt hash above was independently read and verified; the pre-installation copy is retained at the backup path above. The 30-view archive is still being packaged, with a genuine safe-region gate failure under correction. Overall completion is not claimed.

**日本語。** 新しい無奈の任意の化粧 12 レイヤーは正式配置済みで、主担当は正式検証の exit 0 を報告しています。既存の 7 parts、3 口形、衣装、replace mask、承認ファイル、base manifest の SHA は保持しています。receipt が固定する本体ファイルは 28 件、合計 29 件、そのうち PNG は 24 件です。上記 receipt SHA は読み取りで独立確認し、配置前のバックアップも保存しています。30-view archive は組み立て中で、safe-region 検証の失敗を修正しており、全体の完了は主張しません。

### 確認過的修正與限制／已确认的修正与限制／Verified corrections and limits／確認済みの修正と制限

- 六 named pose 已收斂彩妝 alpha：只使用原圖不透明輪廓內側，輪廓 3 px 帶為零顏料，向內 4 px 柔化。托腮彩妝新增的亮紫線已消除；原圖本身極淡邊色保留，未修改原 RGB 或輪廓。六姿勢 × 三狀態的輪廓 RGBA 與灰底改變均為 0。／六个 named pose 的彩妆 alpha 已限制在原图不透明内部，轮廓 3 px 带无颜料，向内 4 px 柔化；新增亮紫线已消除，原图淡边保留，18 个姿势状态的轮廓和灰底变化均为 0。／Pigment alpha is confined inside the opaque source, with a clear 3 px contour band and a 4 px inward transition. The added bright purple line is removed; the faint original fringe remains, with no source RGB or contour edits. All 18 pose/state edge and gray-background comparisons are unchanged.／化粧 alpha を不透明な原画の内側に限定し、輪郭 3 px は無色、さらに内側 4 px でなじませました。追加された鮮やかな紫線は除去しましたが、原画の淡い縁色は保持しています。原 RGB と輪郭は編集せず、18 姿勢状態の輪郭と灰色背景の差は 0 です。
- 三 gesture 的 speaking+closed 使用真產品眨眼合成；眉保護依原眉與對位後 donor 眉形狀排除，沒有用水平裁線或關閉眨眼掩蓋問題。mock-hit 的真眼部偏移為顯示座標 (0,2)，對應原生約 (0,5.394)；其 closed 材料已依實際 profile 更正。／三个 gesture 使用真实产品闭眼合成，按原眉和对位后 donor 眉形保护；mock-hit 的显示偏移 (0,2) 已反映在闭眼材料。／The three gesture closed states use actual product blink composition with source-shaped protection of original and aligned donor brows. Mock-hit's real display offset (0,2), approximately (0,5.394) natively, is reflected in its closed material.／3 gesture の閉眼は実際の製品合成を使用し、原眉と位置合わせ後の donor 眉の形状を保護します。mock-hit の実際の表示座標 (0,2)、原生座標で約 (0,5.394) を閉眼素材に反映しました。
- 眉保護快取上限 8 筆，以眉區內容、尺寸、表情為鍵；嘴型改變不重算。465 畫布 warm 中位 0.1925 ms、p95 0.2594 ms，首次含 CV 初始化 28.34 ms。相關回歸曾 13 passed；最後補測 expression 參數分支為 5 passed，限定 Ruff 通過。此文件工作未重跑程式。／眉保护缓存最多 8 项，嘴型变化复用；相关回归 13 passed，最后参数分支补测 5 passed，限定 Ruff 通过。／The brow cache is bounded to eight entries keyed by brow content, dimensions, and expression. On a 465 canvas, warm median/p95 were 0.1925/0.2594 ms; first initialization was 28.34 ms. Related regression passed 13 tests; the subsequent expression-branch correction passed five tests and scoped Ruff. Documentation did not rerun code.／眉保護キャッシュは最大 8 件で、口形の変化では再計算しません。465 画布の warm 中央値/p95 は 0.1925/0.2594 ms、初期化を含む初回は 28.34 ms。関連回帰は 13 件、後続の表情引数の修正は 5 件成功し、対象 Ruff も成功しています。

證據／证据／Evidence／証拠：本批次 `cross-angle-makeup-poses-native-20260912-01/` 的 `edge-repair-receipt.json`、`edge-repair-v1-backup/`、各姿勢 `source-v1-v2-edge-closeup.png` 與 `source-v1-v2-face.png`、`brow-runtime-preservation.json`、`guard-performance.json`、`anchor-profile-verification.json`。細邊比較使用 PNG，不依賴 JPEG 色度取樣。／Fine-edge comparisons use lossless PNG rather than JPEG chroma sampling.

### 先前階段紀錄／先前阶段记录／Earlier-stage history／以前の段階の記録

### 2026-09-12 最新預設整合狀態／最新默认集成状态／Current default integration／現在の既定統合

**繁體中文。** 使用者明確批准：「我批准了，可以替換預設素材了。另外繼續完成跨角度一致的可選彩妝」。正式來源為 `assets/expressions/source-bound-exasperated/`，批准原文、來源 SHA 與逐檔安裝 SHA 記於該目錄 `receipt.json`。本次僅新無奈 `front-exasperated` 的七個原生可拆分層、rest 與 mid/open/round 嘴型、衣裝及 replace mask 接入預設；其餘姿勢與角度沿用現有路徑。舊七姿勢撤回批次未重新啟用。跨角度一致的可選彩妝持續製作，`cosmetics_status=not_approved`，目前新無奈維持素顏。這不代表 31 角度、完整全身或發布完成。

**简体中文。** 用户已明确批准替换默认素材，并要求继续完成跨角度一致的可选彩妆。正式目录为 `assets/expressions/source-bound-exasperated/`；批准原文、来源和安装 SHA 见 `receipt.json`。本次仅新无奈 `front-exasperated` 的七个原生可拆图层、rest 与 mid/open/round 嘴型、衣装及 replace mask 接入默认；其他姿势与角度沿用原路径，旧七姿势撤回批次未重新启用。可选彩妆仍在制作且未获批准，新无奈保持素颜。不代表 31 个角度、完整全身或发布完成。

**English.** The owner explicitly authorized default replacement and requested continued work on consistent optional makeup across angles. The formal installation is `assets/expressions/source-bound-exasperated/`; its `receipt.json` preserves the owner statement, source SHA, and installed file hashes. Only the new `front-exasperated` portrait's seven native detachable parts, rest and mid/open/round mouths, garment, and replacement mask enter the default path. Other poses and angles retain their existing paths; the withdrawn seven-pose batch remains disabled. Optional cross-angle cosmetics remain in progress and unapproved, so this portrait remains without optional makeup. This does not certify 31 angles, a complete full body, or a release.

**日本語。** 所有者は既定素材の置き換えを明示的に承認し、角度間で一貫した任意の化粧の制作継続を指示しました。正式素材は `assets/expressions/source-bound-exasperated/` にあり、`receipt.json` に承認文、原画 SHA、配置ファイルの SHA を保存しています。既定経路に導入するのは、新しい `front-exasperated` のネイティブ分離可能な 7 パーツ、rest と mid/open/round の口形、衣装と replace mask のみです。他の姿勢と角度は従来の経路を使い、撤回した 7 姿勢の素材は再有効化していません。任意の化粧は制作中で未承認のため、この姿勢は素顔を維持します。31 角度、全身全体、リリースの完了を意味しません。

### 執行期與驗證／运行时与验证／Runtime and validation／実行時と検証

- `application/service_container.py:face_renderer_factory` 在未設定 `MOHAN_EXASPERATED_CANDIDATE_DIR` 時解析正式目錄並呼叫 `validate_formal_exasperated_install`；正式衣裝缺失會報錯。環境變數僅保留絕對路徑候選覆寫。／未设置环境变量时使用并验证正式目录；缺失正式衣装会报错，仅保留绝对路径候选覆盖。／Without the environment override, the factory resolves and validates the formal directory and rejects missing formal appearance; candidate overrides must be absolute paths.／環境変数による上書きがなければ正式ディレクトリを検証し、正式衣装の欠落はエラーにします。候補の上書きは絶対パスに限ります。
- 受影響的正式預設、原候選、語音、眨眼、分層及封裝檢查共 48 passed（exit 0）；隔離手區域與相依注入回歸另有 3 passed（exit 0），修正了測試假資源路徑只對 `.` 生效。最後一次全庫 `ruff check .` exit 0。文件修改未重跑程式測試。／受影响的默认、候选、语音、眨眼、分层和打包检查共 48 passed（exit 0）；隔离手区域与依赖注入另有 3 passed（exit 0），测试假资源路径仅对 `.` 生效。最后一次全库 `ruff check .` exit 0；文档修改未重跑程序测试。／The affected default, candidate, speech, blink, layering, and packaging checks passed 48 tests (exit 0). Isolated hand-region and dependency-injection checks passed three more (exit 0) after limiting the test resource override to `.`. The final repository-wide `ruff check .` exited 0; documentation edits did not rerun code tests.／既定経路、候補、音声、まばたき、レイヤー、梱包の関連検査は 48 件成功（exit 0）、手領域の分離と依存性注入は追加で 3 件成功（exit 0）しました。テスト用の資源パス上書きは `.` のみに限定しました。最後の全リポジトリ `ruff check .` は exit 0 で、文書編集後にコードのテストは再実行していません。
- 正式收據 SHA-256 `29eb66ec6bc413d5bac37c17c753ccfc75f364dfa20aebc98b395b9a4940e633`；正式目錄共 16 檔，其中 12 張 PNG 均為 1254×1254 RGBA。衣裝核准檔路徑以安裝根目錄為基準（`path_base=install_root`）；審閱頁 SHA、使用者原文及逐檔 SHA 均留於正式收據。／正式收据 SHA-256 如上；目录共 16 个文件，其中 12 张 PNG 均为 1254×1254 RGBA。衣装批准文件路径以安装根目录为基准，审核页 SHA、用户原文和逐文件 SHA 均见收据。／The formal receipt SHA-256 is shown above; the directory has 16 files, including 12 PNGs at 1254×1254 RGBA. The garment approval path is relative to the installation root (`path_base=install_root`); the receipt records the reviewed page SHA, owner statement, and every installed file hash.／正式な受領記録の SHA-256 は上記のとおりです。16 ファイル中 12 枚の PNG はすべて 1254×1254 RGBA です。衣装承認ファイルのパスは配置ルートを基準とし、審査ページの SHA、所有者の承認文、全ファイルの SHA は受領記録に保存しています。
- 獨立 Qt/PIL 驗證：alpha 一致，不透明 RGB 最大差 1，預乘 RGB 最大差 1.985；不宣稱完整 RGBA 相同。／独立 Qt/PIL 验证 alpha 一致，不透明 RGB 最大差 1，预乘 RGB 最大差 1.985，不宣称完整 RGBA 相同。／Independent Qt/PIL comparison has identical alpha, maximum opaque RGB difference 1, and maximum premultiplied RGB difference 1.985; full RGBA equality is not claimed.／独立した Qt/PIL 比較では alpha は一致し、不透明 RGB の最大差は 1、事前乗算 RGB の最大差は 1.985 です。全 RGBA の一致は主張しません。

### 以下為先前階段紀錄，預設狀態以上方最新紀錄為準／以下为历史记录／Earlier-stage history; current status above takes precedence／以下は過去の段階の記録です

### 2026-09-12 半身接合修復退回重做

使用者否決三張腕部重組與 35 格動態合成。全庫 Ruff 47 項已修正，但素材正式整合未完成。失敗的 49 PNG + manifest 已完整保留移出預設 assets/expressions/detachable 路徑，舊 receipt 的接合判定已撤回。現況、證據與待辦見 scratchpad/seam-repair-current-status-20260912.md；新 imagegen 三張來源候選等待目視判斷，不得視為已核准素材。


### 2026-09-12 無奈原圖已核准、原生可見分層完成

無奈重生原圖已獲「這張可以」核准。7 個原生可見分區重組一致；共同產線只完成支援的 4 角色及剩餘前景，尚非完整素體或正式執行期。三種新嘴型已取回核准原圖，遮罩外像素一致，等待新嘴型目視確認。最新來源、SHA、對照與限制見 scratchpad/seam-repair-current-status-20260912.md 的最新段落。

### 2026-09-12 無奈衣裝與嘴型產品候選接線

三嘴與新衣裝已核准，已接單一 MOHAN_EXASPERATED_CANDIDATE_DIR opt-in 產品路徑，七部件與可拆衣裝、來源綁定嘴型均有實際465畫布驗證。新彩妝不採用，保持核准素顏；預設資產仍未替換。runtime31、appearance19、架構10、文件9測試通過，全庫Ruff通過。完整證據與未完成項目見 scratchpad/seam-repair-current-status-20260912.md 最新段落及其 root-integration-checkpoint.json。

This document records the release handoff information for the MoHan-PC-Desktop-Assistant project, for future maintainers and collaborators.

### Latest release status

- Version: v4.2.1
- Release status: released
- Tag: `v4.2.1`
- Source branch: `release/v4.2.1` (branch cleanup completed after merge)
- Target branch: `main`

### Improvements completed in this release (v4.2.1)

- Full-body motion consistency: the earlier placeholder version of `resolve_speech` returned `None`, so speech used a static mouth while the legacy expression path reset `_adaptive_full_body_active`. v4.2.1 unifies full-body rendering and mouth motion on one stable path.
- Lip sync: implemented `resolve_speech` to read the face region from `.hands.json` `protected_regions.face`, produce a procedural mouth layer, and make `update_speech_layers` restore the static photograph when the mouth closes.
- Wave response: `set_state` now skips the legacy expression switch in full-body mode while keeping the gesture animation, so a wave or arrival still gets a visible body response.

### Release process record

- Full regression suite 280/280 green.
- Squash-merged the PR, created the `v4.2.1` tag, pushed it, and triggered release.yml.
- Produced a formal Release (draft=false, prerelease=false).

### Maintenance notes

- The release source (branch, merged main, version, tag, GitHub Release) must point to the same immutable commit.
- Follow PUBLISHING.md squash-only and four-language governance.
- Follow .clinerules.md exclusion list and token-saving rules.

## 日本語

### 2026-09-12 正式彩妝安裝完成範圍／正式彩妆安装范围／Formal makeup installation scope／正式な化粧配置の範囲

* 使用者「採用這組配色」的批准已落實：30-view archive（24 yaw + 6 named pose）已正式安裝，新無奈的 12 個嘴型專屬彩妝另走 source-bound 分流。這是本輪可選彩妝安裝完成，原先 47 項指全庫 Ruff 診斷，已修正且全庫 Ruff 通過；本次不代表完整全身、31-view 逐張人工外觀驗收或發布完成；既有使用者 store 未修改。／用户批准的配色已落实：30-view archive 正式安装，新无奈 12 个嘴型专属彩妆独立分流；原先 47 项指全库 Ruff 诊断，已修正且全库 Ruff 通过；本次不代表完整全身、31-view 逐张人工验收或发布完成，既有用户 store 未修改。／The approved palette is installed in the 30-view archive, with 12 mouth-specific cosmetic layers for the new exasperated portrait routed separately. The earlier 47 refers to repository-wide Ruff findings, which were fixed and now pass. This optional-makeup installation does not certify a complete full body, individual human acceptance of all 31 views, or a release. Existing user stores were not modified.／承認済み配色を 30-view archive に正式配置し、新しい無奈の口形別化粧 12 レイヤーは独立した経路に配置しました。先の 47 件は全庫 Ruff の指摘で、修正済みかつ全庫 Ruff は成功しています。今回の任意化粧の配置は、全身全体、31 view の個別目視受入れ、公開の完了を意味しません。既存ユーザー store は変更していません。
* 正式 archive 與安裝 receipt 的 SHA 已唯讀核對，詳見下方證據。原 archive 已備份；原 foundation 與 archive 內舊無奈成員保留，新無奈產品使用獨立來源。正式 factory 無環境變數時 cosmetics_available=true，appearance 共 14 層（12 妝 + 衣裝/replace）。／正式 archive 和 receipt SHA 已核对，旧 archive 已备份；foundation 与 archive 原无奈成员保留。默认 factory 无环境变量时 14 层 appearance 可用。／Formal archive and receipt hashes were independently verified; the previous archive is backed up, with foundation and legacy archive exasperated members preserved. Without an environment override, the formal factory exposes cosmetics_available=true and 14 appearance layers: 12 cosmetics plus garment and replacement mask.／正式 archive と receipt の SHA を独立確認し、旧 archive をバックアップしました。foundation と archive 内の旧無奈素材は保持しています。環境変数なしの正式 factory では cosmetics_available=true、appearance は化粧 12 と衣装・replace の計 14 レイヤーです。
* 六 named pose 的新增亮紫線已消除，原圖淡邊保持；輪廓 3 px 帶無彩妝，原輪廓 RGBA 差 0。最終另移除四個 closed 圖的耳前髮際孤島與六姿勢 12 個眼層的眉區溢出，僅托腮安全區右端擴 1 px 收入實際睫毛。+030 closed 的 1,338 個藍邊像素與 -090 rest 的 685 個藍邊像素在 bare/classic 相同，經原生圖、Qt 直接解碼與產品逐像素追溯，皆為 Alpha 1–7 的 8-bit 預乘量化；灰底每頻道誤差低於 1/255，不能據此認定原生圖有可見純藍缺陷。／新增亮紫线已消除，原图淡边保留；另清除闭眼耳前孤岛与眉区溢出，只有托腮安全区右端增加 1 px 实际睫毛。+030 closed 的 1,338 和 -090 rest 的 685 个蓝边像素在 bare/classic 相同，追溯为 Alpha 1–7 的 8-bit 预乘量化；灰底每通道误差低于 1/255，不据此认定原图存在可见纯蓝缺陷。／The added bright purple fringe is removed while the faint original edge is preserved; the 3 px contour band has no pigment and source-edge RGBA difference is zero. Final corrections removed four closed-state preauricular hairline islands and brow spill in 12 eye layers across six poses; only cheek-rest's right safe-region edge grew by 1 px to include a real lash. The 1,338 blue-edge pixels in +030 closed and 685 in -090 rest are identical in bare/classic and arise from 8-bit premultiplied conversion at Alpha 1–7, reproduced by direct Qt decoding of the raw authority. Gray-background channel error is below 1/255; this does not establish a visible pure-blue defect in the native art.／追加された鮮やかな紫線を除去し、原画の淡い縁色を保持しました。輪郭 3 px に化粧はなく、原輪郭 RGBA の差は 0 です。最終修正で閉眼 4 枚の耳前生え際の孤立部分と 6 姿勢 12 眼レイヤーの眉へのはみ出しを除き、托腮のみ実際のまつ毛のため安全領域右端を 1 px 広げました。+030 closed の青い縁 1,338 ピクセルと -090 rest の 685 ピクセルは bare/classic で同じで、Alpha 1–7 の 8-bit 事前乗算の量子化に由来し、原画の Qt 直接読込でも再現します。灰色背景での各チャンネル誤差は 1/255 未満であり、原画に視認可能な純青の欠陥があるとは判定できません。
* 藍邊追溯證據／蓝边溯源证据／Blue-edge provenance evidence／青い縁の由来の証拠：`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.json`、`scratchpad/continuation-audit-20260912-01/blue-edge-diagnosis.md`。
* 驗證為分批受影響範圍：49 張真產品 QA 圖通過；runtime/appearance/browguard/packbuilder 39 passed（39.03 s），文件/changelog/分層檢查測試 23 passed（1.58 s），另 25 項受影響測試及安裝後 12 項 store/cache 測試通過（後者 24.13 s）。全庫 Ruff 通過；分層 import checker 330 模組通過，只新增 service_container→exasperated_candidate_assets 精確組合邊。這不是全庫測試套件全跑。／验证按受影响范围分批执行：49 张真产品图、39+23 项主线测试、另 25 项及安装后 12 项通过；全库 Ruff 和 330 模块 import checker 通过，不等于全库测试全跑。／Validation was scoped: 49 actual product QA frames passed; 39 runtime/appearance/browguard/packbuilder tests passed in 39.03 s, 23 documentation/changelog/layered-checker tests in 1.58 s, a separate 25 affected tests passed, and 12 post-installation store/cache tests passed in 24.13 s. Full-repository Ruff and the 330-module import checker passed; only the exact service_container→exasperated_candidate_assets composition edge was registered. This was not a full-repository test-suite run.／検証は影響範囲ごとに実施しました。実際の製品 QA 49 画像、runtime 等 39 件（39.03 秒）、文書等 23 件（1.58 秒）、別の関連 25 件、配置後 store/cache 12 件（24.13 秒）が成功しました。全庫 Ruff と 330 モジュールの import checker も成功し、service_container→exasperated_candidate_assets の正確な構成辺のみ登録しました。全テストスイートの実行ではありません。

證據／证据／Evidence／証拠：

* `assets/official-packs/mohan.makeup.builtin.mohan-outfit`: SHA-256 `2a92685c89f97e9799d7c8ba7ea8c65859cfef400008bcded5e838c16fbf2a84`.
* `B/cross-angle-makeup-approved-integration-20260912-01/formal-native30-install-receipt.json`: SHA-256 `284a2cc8bf3d7570ac88f6a8350132861ad56f75d45408f8b390f7a28ba64979`.
* `B/cross-angle-makeup-approved-integration-20260912-01/official-makeup-before-native30.mohan-outfit`: SHA-256 `51ee53cfbf0e082e18be7d1af775a331a61aad60d7e51ec36453aa4c57b461a6`.
* `B/cross-angle-makeup-product-qa-20260912-01/native30-qa-20260912-01/receipt.json`: SHA-256 `fb959b2ba6789fde54f4eeb6f7c6dc1ede37c2b1f6d7641b113b5a11679054b8`.
* 新無奈／新无奈／Exasperated／無奈 `assets/expressions/source-bound-exasperated/receipt.json`: SHA-256 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`.

`B` = `scratchpad/v4-identity-rebuild-20260905/v4-hanfu-alignment-20260910/source-bound-halfbody-sword-sync-20260911-01`.

### 以下保留先前階段紀錄，以本節最終狀態為準／以下保留历史记录／Earlier-stage history follows; this final status takes precedence／以下は過去の記録であり、本節の最終状態を優先します

### 2026-09-12 配色批准與輪廓修正／配色批准与轮廓修正／Palette approval and edge correction／配色承認と輪郭修正

**繁體中文。** 使用者已明確表示「採用這組配色」。此為跨角度可選彩妝配色批准，不等於逐張素材再次核准或完整全身驗收。整合分為 30 個既有 view 的 archive（24 yaw + 6 named pose）與新無奈獨立來源分流；新無奈依 rest/mid/open/round 保留嘴型專屬唇支持。新無奈彩妝正式安裝已確認；30-view archive 尚未完成，詳見下方安裝證據。

**简体中文。** 用户已明确表示“采用这组配色”。这是跨角度可选彩妆配色批准，不等于逐张资源再次批准或完整全身验收。集成分为 30 个既有 view 的 archive（24 yaw + 6 named pose）与新无奈独立来源路径；新无奈按 rest/mid/open/round 保留各嘴型唇部支持。新无奈彩妆正式安装已确认；30-view archive 尚未完成，见下方证据。

**English.** The owner approved this palette. This approves the optional cross-angle color scheme, not a second per-image approval or complete full-body acceptance. Integration separates a 30-view archive (24 yaw views and six named poses) from the new source-bound exasperated portrait, whose rest/mid/open/round states retain separate lip supports. Formal cosmetic installation is confirmed for the new exasperated portrait; the 30-view archive remains pending, as detailed below.

**日本語。** 所有者はこの配色の採用を承認しました。これは角度間で一貫した任意の化粧の配色承認であり、各素材の再承認や全身全体の受入れではありません。統合は 30 view の archive（24 yaw と 6 named pose）と新しい無奈の独立した原画対応経路に分け、無奈の rest/mid/open/round はそれぞれの唇支持を維持します。新しい無奈の化粧は正式配置を確認済みですが、30-view archive は未完了です。詳細は以下に記録します。

### 新無奈安裝已確認、30-view archive 尚未完成／新无奈已安装、30-view archive 待完成／Exasperated installed; 30-view archive pending／無奈は配置済み、30-view archive は未完了

**繁體中文。** 新無奈的 12 個可選彩妝圖層已正式安裝到 `assets/expressions/source-bound-exasperated/`；主線回報 `validate_formal_exasperated_install` exit 0。現有七 parts、三嘴型、衣裝、replace mask、批准檔與 base manifest 的 SHA 均保留。共 28 個被 receipt 釘選的非 receipt 檔、29 個總檔，其中 24 PNG。正式 receipt SHA 已唯讀核對為 `471f739580037977cca63828939568da3bc13a67c9d72ce19fa6a950750c129d`；安裝前備份位於本批次 `cross-angle-makeup-approved-integration-20260912-01/exasperated-before-makeup/`。30-view archive 仍在組包，safe-region 真閘門正在修正，不能宣稱全批完成。

**简体中文。** 新无奈的 12 个可选彩妆图层已正式安装，主线验证 exit 0；原七 parts、三嘴型、衣装、replace mask、批准文件和 base manifest SHA 保持相同。共 28 个被 receipt 固定的非 receipt 文件、29 个总文件，其中 24 PNG；receipt SHA 与上述值一致，旧文件已备份。30-view archive 仍在组包并修正 safe-region 验证失败，未全部完成。

**English.** Twelve optional cosmetic layers are formally installed for the new exasperated portrait; the main agent reports successful formal validation. Hashes of the prior seven parts, three mouths, garment, replacement mask, approval file, and base manifest remain unchanged. There are 28 pinned non-receipt files, 29 files in total, and 24 PNGs. The receipt hash above was independently read and verified; the pre-installation copy is retained at the backup path above. The 30-view archive is still being packaged, with a genuine safe-region gate failure under correction. Overall completion is not claimed.

**日本語。** 新しい無奈の任意の化粧 12 レイヤーは正式配置済みで、主担当は正式検証の exit 0 を報告しています。既存の 7 parts、3 口形、衣装、replace mask、承認ファイル、base manifest の SHA は保持しています。receipt が固定する本体ファイルは 28 件、合計 29 件、そのうち PNG は 24 件です。上記 receipt SHA は読み取りで独立確認し、配置前のバックアップも保存しています。30-view archive は組み立て中で、safe-region 検証の失敗を修正しており、全体の完了は主張しません。

### 確認過的修正與限制／已确认的修正与限制／Verified corrections and limits／確認済みの修正と制限

- 六 named pose 已收斂彩妝 alpha：只使用原圖不透明輪廓內側，輪廓 3 px 帶為零顏料，向內 4 px 柔化。托腮彩妝新增的亮紫線已消除；原圖本身極淡邊色保留，未修改原 RGB 或輪廓。六姿勢 × 三狀態的輪廓 RGBA 與灰底改變均為 0。／六个 named pose 的彩妆 alpha 已限制在原图不透明内部，轮廓 3 px 带无颜料，向内 4 px 柔化；新增亮紫线已消除，原图淡边保留，18 个姿势状态的轮廓和灰底变化均为 0。／Pigment alpha is confined inside the opaque source, with a clear 3 px contour band and a 4 px inward transition. The added bright purple line is removed; the faint original fringe remains, with no source RGB or contour edits. All 18 pose/state edge and gray-background comparisons are unchanged.／化粧 alpha を不透明な原画の内側に限定し、輪郭 3 px は無色、さらに内側 4 px でなじませました。追加された鮮やかな紫線は除去しましたが、原画の淡い縁色は保持しています。原 RGB と輪郭は編集せず、18 姿勢状態の輪郭と灰色背景の差は 0 です。
- 三 gesture 的 speaking+closed 使用真產品眨眼合成；眉保護依原眉與對位後 donor 眉形狀排除，沒有用水平裁線或關閉眨眼掩蓋問題。mock-hit 的真眼部偏移為顯示座標 (0,2)，對應原生約 (0,5.394)；其 closed 材料已依實際 profile 更正。／三个 gesture 使用真实产品闭眼合成，按原眉和对位后 donor 眉形保护；mock-hit 的显示偏移 (0,2) 已反映在闭眼材料。／The three gesture closed states use actual product blink composition with source-shaped protection of original and aligned donor brows. Mock-hit's real display offset (0,2), approximately (0,5.394) natively, is reflected in its closed material.／3 gesture の閉眼は実際の製品合成を使用し、原眉と位置合わせ後の donor 眉の形状を保護します。mock-hit の実際の表示座標 (0,2)、原生座標で約 (0,5.394) を閉眼素材に反映しました。
- 眉保護快取上限 8 筆，以眉區內容、尺寸、表情為鍵；嘴型改變不重算。465 畫布 warm 中位 0.1925 ms、p95 0.2594 ms，首次含 CV 初始化 28.34 ms。相關回歸曾 13 passed；最後補測 expression 參數分支為 5 passed，限定 Ruff 通過。此文件工作未重跑程式。／眉保护缓存最多 8 项，嘴型变化复用；相关回归 13 passed，最后参数分支补测 5 passed，限定 Ruff 通过。／The brow cache is bounded to eight entries keyed by brow content, dimensions, and expression. On a 465 canvas, warm median/p95 were 0.1925/0.2594 ms; first initialization was 28.34 ms. Related regression passed 13 tests; the subsequent expression-branch correction passed five tests and scoped Ruff. Documentation did not rerun code.／眉保護キャッシュは最大 8 件で、口形の変化では再計算しません。465 画布の warm 中央値/p95 は 0.1925/0.2594 ms、初期化を含む初回は 28.34 ms。関連回帰は 13 件、後続の表情引数の修正は 5 件成功し、対象 Ruff も成功しています。

證據／证据／Evidence／証拠：本批次 `cross-angle-makeup-poses-native-20260912-01/` 的 `edge-repair-receipt.json`、`edge-repair-v1-backup/`、各姿勢 `source-v1-v2-edge-closeup.png` 與 `source-v1-v2-face.png`、`brow-runtime-preservation.json`、`guard-performance.json`、`anchor-profile-verification.json`。細邊比較使用 PNG，不依賴 JPEG 色度取樣。／Fine-edge comparisons use lossless PNG rather than JPEG chroma sampling.

### 先前階段紀錄／先前阶段记录／Earlier-stage history／以前の段階の記録

### 2026-09-12 最新預設整合狀態／最新默认集成状态／Current default integration／現在の既定統合

**繁體中文。** 使用者明確批准：「我批准了，可以替換預設素材了。另外繼續完成跨角度一致的可選彩妝」。正式來源為 `assets/expressions/source-bound-exasperated/`，批准原文、來源 SHA 與逐檔安裝 SHA 記於該目錄 `receipt.json`。本次僅新無奈 `front-exasperated` 的七個原生可拆分層、rest 與 mid/open/round 嘴型、衣裝及 replace mask 接入預設；其餘姿勢與角度沿用現有路徑。舊七姿勢撤回批次未重新啟用。跨角度一致的可選彩妝持續製作，`cosmetics_status=not_approved`，目前新無奈維持素顏。這不代表 31 角度、完整全身或發布完成。

**简体中文。** 用户已明确批准替换默认素材，并要求继续完成跨角度一致的可选彩妆。正式目录为 `assets/expressions/source-bound-exasperated/`；批准原文、来源和安装 SHA 见 `receipt.json`。本次仅新无奈 `front-exasperated` 的七个原生可拆图层、rest 与 mid/open/round 嘴型、衣装及 replace mask 接入默认；其他姿势与角度沿用原路径，旧七姿势撤回批次未重新启用。可选彩妆仍在制作且未获批准，新无奈保持素颜。不代表 31 个角度、完整全身或发布完成。

**English.** The owner explicitly authorized default replacement and requested continued work on consistent optional makeup across angles. The formal installation is `assets/expressions/source-bound-exasperated/`; its `receipt.json` preserves the owner statement, source SHA, and installed file hashes. Only the new `front-exasperated` portrait's seven native detachable parts, rest and mid/open/round mouths, garment, and replacement mask enter the default path. Other poses and angles retain their existing paths; the withdrawn seven-pose batch remains disabled. Optional cross-angle cosmetics remain in progress and unapproved, so this portrait remains without optional makeup. This does not certify 31 angles, a complete full body, or a release.

**日本語。** 所有者は既定素材の置き換えを明示的に承認し、角度間で一貫した任意の化粧の制作継続を指示しました。正式素材は `assets/expressions/source-bound-exasperated/` にあり、`receipt.json` に承認文、原画 SHA、配置ファイルの SHA を保存しています。既定経路に導入するのは、新しい `front-exasperated` のネイティブ分離可能な 7 パーツ、rest と mid/open/round の口形、衣装と replace mask のみです。他の姿勢と角度は従来の経路を使い、撤回した 7 姿勢の素材は再有効化していません。任意の化粧は制作中で未承認のため、この姿勢は素顔を維持します。31 角度、全身全体、リリースの完了を意味しません。

### 執行期與驗證／运行时与验证／Runtime and validation／実行時と検証

- `application/service_container.py:face_renderer_factory` 在未設定 `MOHAN_EXASPERATED_CANDIDATE_DIR` 時解析正式目錄並呼叫 `validate_formal_exasperated_install`；正式衣裝缺失會報錯。環境變數僅保留絕對路徑候選覆寫。／未设置环境变量时使用并验证正式目录；缺失正式衣装会报错，仅保留绝对路径候选覆盖。／Without the environment override, the factory resolves and validates the formal directory and rejects missing formal appearance; candidate overrides must be absolute paths.／環境変数による上書きがなければ正式ディレクトリを検証し、正式衣装の欠落はエラーにします。候補の上書きは絶対パスに限ります。
- 受影響的正式預設、原候選、語音、眨眼、分層及封裝檢查共 48 passed（exit 0）；隔離手區域與相依注入回歸另有 3 passed（exit 0），修正了測試假資源路徑只對 `.` 生效。最後一次全庫 `ruff check .` exit 0。文件修改未重跑程式測試。／受影响的默认、候选、语音、眨眼、分层和打包检查共 48 passed（exit 0）；隔离手区域与依赖注入另有 3 passed（exit 0），测试假资源路径仅对 `.` 生效。最后一次全库 `ruff check .` exit 0；文档修改未重跑程序测试。／The affected default, candidate, speech, blink, layering, and packaging checks passed 48 tests (exit 0). Isolated hand-region and dependency-injection checks passed three more (exit 0) after limiting the test resource override to `.`. The final repository-wide `ruff check .` exited 0; documentation edits did not rerun code tests.／既定経路、候補、音声、まばたき、レイヤー、梱包の関連検査は 48 件成功（exit 0）、手領域の分離と依存性注入は追加で 3 件成功（exit 0）しました。テスト用の資源パス上書きは `.` のみに限定しました。最後の全リポジトリ `ruff check .` は exit 0 で、文書編集後にコードのテストは再実行していません。
- 正式收據 SHA-256 `29eb66ec6bc413d5bac37c17c753ccfc75f364dfa20aebc98b395b9a4940e633`；正式目錄共 16 檔，其中 12 張 PNG 均為 1254×1254 RGBA。衣裝核准檔路徑以安裝根目錄為基準（`path_base=install_root`）；審閱頁 SHA、使用者原文及逐檔 SHA 均留於正式收據。／正式收据 SHA-256 如上；目录共 16 个文件，其中 12 张 PNG 均为 1254×1254 RGBA。衣装批准文件路径以安装根目录为基准，审核页 SHA、用户原文和逐文件 SHA 均见收据。／The formal receipt SHA-256 is shown above; the directory has 16 files, including 12 PNGs at 1254×1254 RGBA. The garment approval path is relative to the installation root (`path_base=install_root`); the receipt records the reviewed page SHA, owner statement, and every installed file hash.／正式な受領記録の SHA-256 は上記のとおりです。16 ファイル中 12 枚の PNG はすべて 1254×1254 RGBA です。衣装承認ファイルのパスは配置ルートを基準とし、審査ページの SHA、所有者の承認文、全ファイルの SHA は受領記録に保存しています。
- 獨立 Qt/PIL 驗證：alpha 一致，不透明 RGB 最大差 1，預乘 RGB 最大差 1.985；不宣稱完整 RGBA 相同。／独立 Qt/PIL 验证 alpha 一致，不透明 RGB 最大差 1，预乘 RGB 最大差 1.985，不宣称完整 RGBA 相同。／Independent Qt/PIL comparison has identical alpha, maximum opaque RGB difference 1, and maximum premultiplied RGB difference 1.985; full RGBA equality is not claimed.／独立した Qt/PIL 比較では alpha は一致し、不透明 RGB の最大差は 1、事前乗算 RGB の最大差は 1.985 です。全 RGBA の一致は主張しません。

### 以下為先前階段紀錄，預設狀態以上方最新紀錄為準／以下为历史记录／Earlier-stage history; current status above takes precedence／以下は過去の段階の記録です

### 2026-09-12 半身接合修復退回重做

使用者否決三張腕部重組與 35 格動態合成。全庫 Ruff 47 項已修正，但素材正式整合未完成。失敗的 49 PNG + manifest 已完整保留移出預設 assets/expressions/detachable 路徑，舊 receipt 的接合判定已撤回。現況、證據與待辦見 scratchpad/seam-repair-current-status-20260912.md；新 imagegen 三張來源候選等待目視判斷，不得視為已核准素材。


### 2026-09-12 無奈原圖已核准、原生可見分層完成

無奈重生原圖已獲「這張可以」核准。7 個原生可見分區重組一致；共同產線只完成支援的 4 角色及剩餘前景，尚非完整素體或正式執行期。三種新嘴型已取回核准原圖，遮罩外像素一致，等待新嘴型目視確認。最新來源、SHA、對照與限制見 scratchpad/seam-repair-current-status-20260912.md 的最新段落。

### 2026-09-12 無奈衣裝與嘴型產品候選接線

三嘴與新衣裝已核准，已接單一 MOHAN_EXASPERATED_CANDIDATE_DIR opt-in 產品路徑，七部件與可拆衣裝、來源綁定嘴型均有實際465畫布驗證。新彩妝不採用，保持核准素顏；預設資產仍未替換。runtime31、appearance19、架構10、文件9測試通過，全庫Ruff通過。完整證據與未完成項目見 scratchpad/seam-repair-current-status-20260912.md 最新段落及其 root-integration-checkpoint.json。

本ファイルは MoHan-PC-Desktop-Assistant プロジェクトのリリース引き継ぎ情報を記録し、後続の保守者と協力者の参考に供します。

### 最新リリース状況

- バージョン：v4.2.1
- リリース状況：リリース済み
- タグ：`v4.2.1`
- ソースブランチ：`release/v4.2.1`（マージ後のブランチ整理まで完了）
- ターゲットブランチ：`main`

### 本リリースで完了した改善（v4.2.1）

- 全身モーションの一貫性：以前の placeholder 版 `resolve_speech` は `None` を返し、発話時は静的な口元を使い、レガシー表情経路は `_adaptive_full_body_active` をリセットしていました。v4.2.1 では全身レンダリングと口元モーションを一つの安定した経路へ統合しました。
- リップシンク：`resolve_speech` を実装し、`.hands.json` の `protected_regions.face` から顔領域を読み取り、手続き的な口元レイヤーを生成し、口を閉じた際に `update_speech_layers` が静的写真へ戻すようにしました。
- 手振り応答：`set_state` は全身モードでレガシー表情切り替えをスキップしつつジェスチャーアニメーションを維持し、手振りや来訪に可視の身体応答を残します。

### リリース工程の記録

- 完全回帰テスト 280/280 全緑。
- PR を squash マージし、タグ `v4.2.1` を作成してプッシュし、release.yml を起動しました。
- 正式な Release（draft=false、prerelease=false）を生成しました。

### 保守上の注意

- リリース元（ブランチ、マージ後の main、バージョン、タグ、GitHub Release）は同一の不変コミットを指す必要があります。
- PUBLISHING.md の squash-only と四言語ガバナンスに従います。
- .clinerules.md の除外リストとトークン節約ルールに従います。
