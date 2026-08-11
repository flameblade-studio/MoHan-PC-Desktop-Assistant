# 參數化分層 2.5D 臉部計畫／参数化分层 2.5D 脸部计划／Parametric Layered 2.5D Face Plan／パラメトリック多層 2.5D フェイス計画

## 繁體中文

### 目的與界線

本計畫以不破壞墨寒現有穩定功能為最高前提，將整張表情圖片切換完整改造為可連續控制的分層 2.5D 臉部。它不引進影片、3D 引擎、雲端渲染或執行期生成式模型，也不改變角色五官。正面、朝左、托腮三種姿態與全部既有表情、眨眼及嘴型必須在同一交付中完成；現有渲染器保留為立即回退路徑，但不作為延後任何姿態的分期方案。

### 現有基礎

- `lip_sync.py` 繼續是所有語音供應器共用的 50 Hz 嘴型時序唯一真實來源。
- `expression_system.py` 繼續擁有表情選擇、優先級與持續時間；渲染器不得自行決定情緒。
- 現有 `VisemeFrame` 已提供離散嘴型、連續下顎開度與權重，可在不改變供應器契約下擴充。
- `app.py` 已有臉、眼睛、頭髮、袖子與飾品圖層，但臉部合成責任必須逐步移出這個組裝外殼。

### 目標架構

1. `face_rig.py`：不依賴 Qt 的不可變資料模型，描述姿態、眼皮、眉毛、視線、紅暈、微笑、唇寬、唇圓、嘴部開度與下顎位移。
2. `face_motion.py`：把表情決策與 `VisemeFrame` 合成單一 `FaceMotionFrame`；擁有共同發音、平滑、限速與語音結束歸零規則。
3. `face_assets.py`：載入並驗證每個姿態的透明圖層、遮罩、錨點、局部網格及素材版本；缺少或失真的素材必須安全失敗。
4. `face_renderer.py`：定義小型 `FaceRendererPort`，並提供既有相容渲染器與新的參數化渲染器。兩者接收相同輸入，切換不改變語音、表情或資料庫。
5. `app.py`：只負責組裝、Qt 計時器及顯示最終畫面，不再擁有共同發音或臉部變形規則。

資料流固定為：語音供應器 → `lip_sync.py` → `VisemeFrame` → `face_motion.py` → `FaceMotionFrame` → `FaceRendererPort` → Qt 畫面。不得建立第二套嘴型時鐘、表情仲裁器或語音供應器專用動畫路徑。

### 圖層與變形

每個已支援姿態分成基底皮膚、左右眼皮與眼線、左右眉、虹膜／視線、雙頰紅暈、上唇、下唇、嘴角、口腔、牙齒／舌頭遮罩及下顎／下巴影響區。優先使用局部控制點與小型三角網格變形；光流只可用於離線產生或驗證中間素材，不加入正式執行期依賴。所有圖層使用同一座標系、錨點清冊與角色身分來源。

### 語音與共同發音

- 保留 20 ms／50 Hz 輸入契約，視覺更新可維持目前約 60 Hz 的平滑插值。
- 已完成合成的 TTS 可使用短距離、具上限的前視窗口，使下一個音素提早影響唇圓與唇寬，但畫面不得早於實際播放起點。
- Realtime 與麥克風串流只能使用因果平滑與目前／過去訊號，不得以不可得的未來資料製造延遲。
- 閉唇音、擦音、母音、靜音與語音結束都必須有明確狀態；最後的閉嘴事件具有最高終止權，不得被晚到的音訊分析重新打開。
- 情緒控制眼角、眉毛與紅暈；發音控制嘴唇、嘴角與下顎。兩者只在 `face_motion.py` 明確合成，避免微笑嘴角與說話嘴型互相打架。

### 一次完整導入的施工順序

0. 凍結基準：先完成並實機驗收目前三項視覺修正，保存效能、畫面及封裝容量基準。
1. 邊界抽離：建立資料模型、渲染介面與既有相容渲染器；畫面必須逐像素或在核准容差內等同目前版本。
2. 三姿態素材：同時為 `front`、`lean`、`cheek` 建立眼皮、紅暈、嘴唇、嘴角與下顎圖層；任何姿態缺漏都視為整體尚未完成。
3. 連續嘴型：加入唇寬、唇圓、開度、下顎與共同發音插值，完成繁中、簡中、英文、日文的代表音句測試。
4. 表情疊加：加入眉毛、眼角笑意、紅暈與眨眼的獨立混合，消除膚色覆蓋及表情／發音衝突。
5. 全姿態整合：一次接通 `front`、`lean`、`cheek` 與所有既有表情；每個姿態都需獨立素材稽核與實機驗收，但不得拆成多次上線。
6. 比較與切換：新渲染器在測試與診斷模式產生離線對照，不在使用者執行期重複渲染。全部門檻通過後一次設為預設，既有渲染器至少保留一個完整候選版本作為回退。

### 不可妥協的驗收門檻

- 現有完整回歸、架構、四語、安全、SBOM、封裝與公開內容稽核全部通過。
- 50 Hz 提示頻率不變；第一個已播放提示維持 40 ms 內，長音訊平均間隔誤差維持 3 ms 內。
- 臉部渲染平均低於 8 ms、P95 低於 16 ms、P99 低於 24 ms，且不得劣於已保存的同機基準而無明確效益證據。
- 語音結束後嘴型與聲音同時結束；重複、延遲或亂序完成事件不得重開嘴巴。
- 眨眼不得改變紅暈；說話不得留下嘴角、眼線或舊嘴型殘影；不同姿態切換不得產生跳位或雙重輪廓。
- 角色五官、臉型、髮飾及服裝身分必須符合權威素材，並由使用者在實機以正常比例及放大檢視驗收。
- 記錄冷啟動、記憶體、CPU、JIT 開關對照及封裝容量；任何顯著退步都會阻止預設切換。

### 單一完整交付

本次工作一次完成領域資料模型、渲染介面、既有相容轉接器、三姿態素材清冊、連續嘴型、表情圖層與決定性測試。未完成全部三姿態前不得改變正式畫面或發布產物。完成後提交單一 Draft PR，附新舊畫面差異、效能數據、素材容量及回退證據；只有完整通過全部門檻才進入實機驗收與發布。

## 简体中文

### 目的与边界

本计划以不破坏墨寒现有稳定功能为最高前提，将整张表情图片切换完整改造为可连续控制的分层 2.5D 脸部。它不引入视频、3D 引擎、云端渲染或运行时生成式模型，也不改变角色五官。正面、朝左、托腮三种姿态与全部现有表情、眨眼及嘴型必须在同一次交付中完成；现有渲染器保留为即时回退路径，但不作为延后任何姿态的分期方案。

### 现有基础

- `lip_sync.py` 继续是所有语音提供程序共用的 50 Hz 嘴型时序唯一真实来源。
- `expression_system.py` 继续拥有表情选择、优先级与持续时间；渲染器不得自行决定情绪。
- 现有 `VisemeFrame` 已提供离散嘴型、连续下颌开度与权重，可在不改变提供程序契约下扩展。
- `app.py` 已有脸、眼睛、头发、袖子与饰品图层，但脸部合成职责必须逐步移出这个装配外壳。

### 目标架构

1. `face_rig.py`：不依赖 Qt 的不可变数据模型，描述姿态、眼皮、眉毛、视线、红晕、微笑、唇宽、唇圆、嘴部开度与下颌位移。
2. `face_motion.py`：把表情决策与 `VisemeFrame` 合成单一 `FaceMotionFrame`；拥有协同发音、平滑、限速与语音结束归零规则。
3. `face_assets.py`：加载并验证每个姿态的透明图层、遮罩、锚点、局部网格及素材版本；缺少或失真的素材必须安全失败。
4. `face_renderer.py`：定义小型 `FaceRendererPort`，并提供现有兼容渲染器与新的参数化渲染器。两者接收相同输入，切换不改变语音、表情或数据库。
5. `app.py`：只负责装配、Qt 定时器及显示最终画面，不再拥有协同发音或脸部变形规则。

数据流固定为：语音提供程序 → `lip_sync.py` → `VisemeFrame` → `face_motion.py` → `FaceMotionFrame` → `FaceRendererPort` → Qt 画面。不得建立第二套嘴型时钟、表情仲裁器或语音提供程序专用动画路径。

### 图层与变形

每个已支持姿态分为基础皮肤、左右眼皮与眼线、左右眉、虹膜／视线、双颊红晕、上唇、下唇、嘴角、口腔、牙齿／舌头遮罩及下颌／下巴影响区。优先使用局部控制点与小型三角网格变形；光流只可用于离线生成或验证中间素材，不加入正式运行时依赖。所有图层使用同一坐标系、锚点清单与角色身份来源。

### 语音与协同发音

- 保留 20 ms／50 Hz 输入契约，视觉更新可维持目前约 60 Hz 的平滑插值。
- 已完成合成的 TTS 可使用短距离、具上限的前视窗口，使下一个音素提前影响唇圆与唇宽，但画面不得早于实际播放起点。
- Realtime 与麦克风串流只能使用因果平滑与当前／过去信号，不得以不可得的未来数据制造延迟。
- 闭唇音、擦音、元音、静音与语音结束都必须有明确状态；最后的闭嘴事件具有最高终止权，不得被迟到的音频分析重新打开。
- 情绪控制眼角、眉毛与红晕；发音控制嘴唇、嘴角与下颌。两者只在 `face_motion.py` 明确合成，避免微笑嘴角与说话嘴型互相冲突。

### 一次完整导入的施工顺序

0. 冻结基准：先完成并真机验收目前三项视觉修正，保存性能、画面及封装容量基准。
1. 边界抽离：建立数据模型、渲染接口与现有兼容渲染器；画面必须逐像素或在核准容差内等同当前版本。
2. 三姿态素材：同时为 `front`、`lean`、`cheek` 建立眼皮、红晕、嘴唇、嘴角与下颌图层；任何姿态缺漏都视为整体尚未完成。
3. 连续嘴型：加入唇宽、唇圆、开度、下颌与协同发音插值，完成繁中、简中、英文、日文的代表音句测试。
4. 表情叠加：加入眉毛、眼角笑意、红晕与眨眼的独立混合，消除肤色覆盖及表情／发音冲突。
5. 全姿态集成：一次接通 `front`、`lean`、`cheek` 与全部现有表情；每个姿态都需独立素材审计与真机验收，但不得拆成多次上线。
6. 比较与切换：新渲染器在测试与诊断模式生成离线对照，不在用户运行时重复渲染。全部门槛通过后一次设为默认，现有渲染器至少保留一个完整候选版本作为回退。

### 不可妥协的验收门槛

- 现有完整回归、架构、四语、安全、SBOM、封装与公开内容审计全部通过。
- 50 Hz 提示频率不变；第一个已播放提示保持在 40 ms 内，长音频平均间隔误差保持在 3 ms 内。
- 脸部渲染平均低于 8 ms、P95 低于 16 ms、P99 低于 24 ms，且不得在没有明确效益证据时劣于已保存的同机基准。
- 语音结束后嘴型与声音同时结束；重复、延迟或乱序完成事件不得重新张嘴。
- 眨眼不得改变红晕；说话不得留下嘴角、眼线或旧嘴型残影；不同姿态切换不得产生跳位或双重轮廓。
- 角色五官、脸型、发饰及服装身份必须符合权威素材，并由用户在真机以正常比例及放大检视验收。
- 记录冷启动、内存、CPU、JIT 开关对照及封装容量；任何显著退步都会阻止默认切换。

### 单一完整交付

本次工作一次完成领域数据模型、渲染接口、现有兼容适配器、三姿态素材清单、连续嘴型、表情图层与确定性测试。未完成全部三姿态前不得改变正式画面或发布产物。完成后提交单一 Draft PR，附新旧画面差异、性能数据、素材容量及回退证据；只有完整通过全部门槛才进入真机验收与发布。

## English

### Purpose and boundaries

This plan fully replaces whole-expression image switching with a continuously controlled, layered 2.5D face without regressing MoHan's stable behavior. It introduces no video, 3D engine, cloud renderer, or runtime generative model, and it does not alter the character's identity. Front, left-facing, and chin-rest poses, with every existing expression, blink, and viseme, must be completed in one delivery. The current renderer remains an immediate rollback path, not a staged excuse to defer any pose.

### Existing foundations

- `lip_sync.py` remains the single source of truth for the shared 50 Hz mouth timeline used by every speech provider.
- `expression_system.py` continues to own expression selection, priority, and duration; a renderer never chooses emotion.
- The existing `VisemeFrame` already carries a discrete viseme, continuous jaw aperture, and weight, so it can evolve without changing provider contracts.
- `app.py` already has face, eye, hair, sleeve, and ornament layers, but face-composition responsibility must move out of this composition shell incrementally.

### Target architecture

1. `face_rig.py`: Qt-independent immutable models for pose, eyelids, brows, gaze, blush, smile, lip width, lip rounding, mouth aperture, and jaw displacement.
2. `face_motion.py`: combines an expression decision and `VisemeFrame` into one `FaceMotionFrame`; it owns coarticulation, smoothing, rate limits, and speech-end neutralization.
3. `face_assets.py`: loads and validates transparent layers, masks, anchors, local meshes, and asset versions for each pose; missing or malformed assets fail safely.
4. `face_renderer.py`: defines a small `FaceRendererPort` and provides both the compatible legacy renderer and the new parametric renderer. Both consume the same input, so switching changes no speech, expression, or database behavior.
5. `app.py`: only composes dependencies, owns Qt timers, and displays the final frame; it no longer owns coarticulation or facial-deformation rules.

The fixed data flow is: speech provider → `lip_sync.py` → `VisemeFrame` → `face_motion.py` → `FaceMotionFrame` → `FaceRendererPort` → Qt display. A second mouth clock, expression arbiter, or provider-specific animation path is prohibited.

### Layers and deformation

Each supported pose separates base skin, left and right eyelids and eyeliner, left and right brows, irises/gaze, cheek blush, upper lip, lower lip, mouth corners, oral cavity, teeth/tongue masks, and the jaw/chin influence region. Prefer local control points and small triangular meshes. Optical flow may only generate or validate intermediate assets offline and must not become a production runtime dependency. Every layer uses one coordinate system, anchor manifest, and authoritative character-identity source.

### Speech and coarticulation

- Preserve the 20 ms/50 Hz input contract; visual updates may retain the current approximately 60 Hz interpolation.
- Fully synthesized TTS may use a short, bounded look-ahead window so the next phoneme can begin influencing lip rounding and width, but visuals must never precede the real playback-start gate.
- Realtime and microphone streams use causal smoothing with current and past signals only; unavailable future data must not be simulated at the cost of latency.
- Bilabials, fricatives, vowels, silence, and speech completion all have explicit states. The final close event has terminal authority and late analysis may not reopen the mouth.
- Emotion controls eye corners, brows, and blush; articulation controls lips, mouth corners, and jaw. They combine explicitly only in `face_motion.py`, preventing smiling corners from fighting speech shapes.

### Construction order for one complete delivery

0. Freeze the baseline: finish real-device acceptance of the three current visual fixes and preserve performance, image, and package-size baselines.
1. Extract the boundary: add the models, renderer port, and compatible legacy renderer; output must remain pixel-identical or within an approved tolerance.
2. Three-pose assets: build eyelid, blush, lip, mouth-corner, and jaw layers for `front`, `lean`, and `cheek` together; any missing pose means the delivery is incomplete.
3. Continuous articulation: add lip width, rounding, aperture, jaw, and coarticulation interpolation, with representative Taiwan Traditional Chinese, Simplified Chinese, English, and Japanese utterance tests.
4. Expression layering: independently blend brows, smiling eyes, blush, and blinks to eliminate skin replacement and expression/articulation conflicts.
5. All-pose integration: connect `front`, `lean`, `cheek`, and every existing expression in one change. Each pose still requires an independent asset audit and real-device acceptance, but they are not released separately.
6. Comparison and switch: the new renderer produces offline comparisons in tests and diagnostics, not duplicate rendering during user runtime. It becomes the default once, after every gate passes, and the legacy renderer remains available for at least one complete release-candidate cycle.

### Non-negotiable acceptance gates

- The complete existing regression, architecture, four-language, security, SBOM, packaging, and public-content audits pass.
- The 50 Hz cue rate remains unchanged; the first played cue remains within 40 ms and long-audio mean interval error remains within 3 ms.
- Face rendering remains below 8 ms mean, 16 ms P95, and 24 ms P99, and may not regress against the stored same-machine baseline without evidence of a clear benefit.
- Mouth motion ends with audio; duplicate, late, or out-of-order completion events never reopen it.
- Blinks never alter blush; speech leaves no mouth-corner, eyeliner, or old-viseme residue; pose transitions produce no jumps or doubled contours.
- Facial features, face shape, hair ornaments, and costume identity match the authoritative assets and pass the user's real-device review at normal and enlarged scales.
- Cold start, memory, CPU, JIT on/off comparison, and package size are recorded; any material regression blocks default activation.

### One complete delivery

This work completes the domain models, renderer port, compatible legacy adapter, three-pose asset manifest, continuous articulation, expression layers, and deterministic tests together. Production visuals and release artifacts do not change until all three poses are complete. One Draft PR then presents old/new image differences, performance data, asset size, and rollback evidence; real-device acceptance and release begin only after every gate passes.

## 日本語

### 目的と境界

本計画は、墨寒の安定した既存機能を後退させず、表情画像全体の切り替えを、連続制御できる多層 2.5D フェイスへ全面的に改造します。動画、3D エンジン、クラウドレンダリング、実行時生成モデルは導入せず、キャラクターの顔立ちも変更しません。正面、左向き、頬杖の三姿勢と、既存の全表情、まばたき、ビセームを一回の成果物で完成させます。現行レンダラーは即時ロールバック経路として残しますが、姿勢を先送りする段階導入には使いません。

### 既存の基盤

- `lip_sync.py` は、すべての音声プロバイダーが共有する 50 Hz 口形タイムラインの唯一の信頼できる情報源であり続けます。
- `expression_system.py` は表情の選択、優先順位、継続時間を引き続き所有し、レンダラーが感情を独自判断してはいけません。
- 既存の `VisemeFrame` は離散ビセーム、連続的な顎の開度、重みをすでに持つため、プロバイダー契約を変えずに拡張できます。
- `app.py` には顔、目、髪、袖、装飾のレイヤーがありますが、顔合成の責務はこの構成シェルから段階的に分離します。

### 目標アーキテクチャ

1. `face_rig.py`：姿勢、まぶた、眉、視線、赤み、微笑み、唇の幅、唇の丸み、口の開度、顎の変位を表す、Qt 非依存の不変データモデルです。
2. `face_motion.py`：表情決定と `VisemeFrame` を一つの `FaceMotionFrame` に統合し、調音結合、平滑化、変化速度制限、発話終了時の中立化を所有します。
3. `face_assets.py`：各姿勢の透過レイヤー、マスク、アンカー、局所メッシュ、素材バージョンを読み込み検証します。不足または破損した素材は安全に失敗させます。
4. `face_renderer.py`：小さな `FaceRendererPort` を定義し、現行互換レンダラーと新しいパラメトリックレンダラーを提供します。両者は同じ入力を受け取り、切り替えても音声、表情、データベースの動作は変わりません。
5. `app.py`：依存関係の構成、Qt タイマー、最終画面の表示だけを担い、調音結合や顔変形規則を所有しません。

データフローは、音声プロバイダー → `lip_sync.py` → `VisemeFrame` → `face_motion.py` → `FaceMotionFrame` → `FaceRendererPort` → Qt 表示に固定します。第二の口形時計、表情調停器、プロバイダー固有のアニメーション経路は禁止します。

### レイヤーと変形

対応する各姿勢を、基底肌、左右のまぶたとアイライン、左右の眉、虹彩／視線、頬の赤み、上唇、下唇、口角、口腔、歯／舌マスク、顎／あご先の影響領域に分けます。局所制御点と小規模な三角形メッシュを優先します。オプティカルフローは中間素材のオフライン生成または検証にのみ使用でき、本番実行時依存にはしません。すべてのレイヤーは一つの座標系、アンカーマニフェスト、権威あるキャラクター同一性素材を使用します。

### 音声と調音結合

- 20 ms／50 Hz の入力契約を維持し、視覚更新は現在の約 60 Hz の平滑補間を維持できます。
- 合成済み TTS は、次の音素が唇の丸みと幅へ早めに影響する、短く上限付きの先読み窓を使用できます。ただし、映像は実際の再生開始ゲートより先行してはいけません。
- Realtime とマイクストリームは現在および過去の信号だけによる因果平滑化を使い、存在しない未来データを遅延と引き換えに捏造してはいけません。
- 両唇音、摩擦音、母音、無音、発話完了には明示的な状態を設けます。最後の閉口イベントが終端権限を持ち、遅れて到着した分析が口を再び開いてはいけません。
- 感情は目尻、眉、頬の赤みを制御し、調音は唇、口角、顎を制御します。両者は `face_motion.py` でのみ明示的に統合し、微笑む口角と発話口形の競合を防ぎます。

### 一括完成のための施工順序

0. 基準の凍結：現在の三つの視覚修正を実機で受け入れ確認し、性能、画像、パッケージ容量の基準を保存します。
1. 境界の分離：データモデル、レンダラーポート、現行互換レンダラーを追加します。出力はピクセル同一、または承認済み許容差内で現行版と同等でなければなりません。
2. 三姿勢素材：`front`、`lean`、`cheek` のまぶた、赤み、唇、口角、顎レイヤーを同時に構築し、どれか一姿勢でも欠ければ全体未完成とします。
3. 連続調音：唇の幅、丸み、開度、顎、調音結合補間を追加し、台湾繁体字中国語、簡体字中国語、英語、日本語の代表発話テストを完成させます。
4. 表情レイヤー統合：眉、笑う目元、赤み、まばたきを独立合成し、肌色の上書きと表情／調音の競合を解消します。
5. 全姿勢統合：`front`、`lean`、`cheek` と既存の全表情を一括接続します。各姿勢には独立した素材監査と実機受け入れ確認が必要ですが、別々には公開しません。
6. 比較と切り替え：新レンダラーはテストと診断でオフライン比較を生成し、ユーザー実行時に二重レンダリングしません。すべてのゲート通過後に一度だけ既定値へ切り替え、現行レンダラーを少なくとも一つの完全なリリース候補サイクル中はロールバック用に維持します。

### 妥協しない受け入れゲート

- 既存の完全回帰、アーキテクチャ、四言語、セキュリティ、SBOM、パッケージ、公開内容監査がすべて合格します。
- 50 Hz のキュー頻度を維持し、再生後の最初のキューは 40 ms 以内、長時間音声の平均間隔誤差は 3 ms 以内を維持します。
- 顔レンダリングは平均 8 ms 未満、P95 16 ms 未満、P99 24 ms 未満とし、明確な利点の証拠なしに保存済み同一環境基準より悪化してはいけません。
- 口の動きは音声と同時に終了し、重複、遅延、順序逆転した完了イベントが口を再び開いてはいけません。
- まばたきは赤みを変えず、発話後に口角、アイライン、旧ビセームの残像を残さず、姿勢切り替えで跳びや二重輪郭を生じさせません。
- 顔立ち、顔型、髪飾り、衣装の同一性は権威ある素材に一致し、通常倍率と拡大表示でユーザーの実機確認に合格します。
- コールドスタート、メモリ、CPU、JIT 有効／無効比較、パッケージ容量を記録し、重大な悪化があれば既定有効化を阻止します。

### 単一の完全な成果物

本作業では、領域モデル、レンダラーポート、現行互換アダプター、三姿勢素材マニフェスト、連続口形、表情レイヤー、決定論的テストを一括完成させます。三姿勢すべてが完成するまで、本番表示やリリース成果物は変更しません。完成後は単一の Draft PR に新旧画像差分、性能データ、素材容量、ロールバック証拠を添え、全ゲート通過後にのみ実機受け入れ確認と公開へ進みます。
