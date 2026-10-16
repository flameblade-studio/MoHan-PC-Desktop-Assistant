# 墨寒手勢互動規格／墨寒手势交互规格／MoHan Gesture Interaction Specification／墨寒ジェスチャー操作仕様

## 繁體中文

> 本文件描述 v4.0.0 的開發中契約。手部模型整合、Windows EXE 實機測試與正式發布仍各自處於待完成狀態；完成與發布聲明以相應閘門通過為準。

### 預設、安全與安全回退邊界

手勢互動的預設狀態為關閉，啟用由使用者明確操作。攝影機或模型待備、模型載入失敗、追蹤中斷或信心不足時，功能會進入明確的安全停用狀態；手勢結果保持空值，聊天、語音、2.5D 角色與其他既有功能維持正常。原始攝影機影像的處理範圍限定於即時記憶體；錄製產物限定為正規化的單手 21 點骨架樣本，並保存於專用敏感資料邊界。

### 八個內建手勢與預設映射

八個內建手勢為：揮手（`wave`）→ 顯示控制台；噓聲手勢（`silence`）→ 靜音；張開手掌（`open-palm`）→ 停止目前語音；握拳（`closed-fist`）→ 維持目前狀態；拇指向上（`thumbs-up`）→ 墨寒以正向表情回應；拇指向下（`thumbs-down`）→ 維持目前狀態；指向左方（`point-left`）→ 維持目前狀態；指向右方（`point-right`）→ 維持目前狀態。使用者可用下拉選單重新綁定動作；內建手勢提供停用與重設操作，且其定義持續受到保護。

### 自訂、授權與攜帶

使用者可新增、改名、刪除自訂手勢，並錄製正規化的單手 21 點骨架樣本；刪除範圍限定為所選自訂定義與骨架樣本，攝影機、模型、其他手勢與個人資料維持原狀。自訂文字進入既有安全命令流程；任意程式執行位於這條流程的能力範圍之外。敏感裝置、雲端服務及其他需授權能力仍須通過既有權限與確認。一般攜帶檔的內容範圍為手勢開關、定義名稱、映射等非敏感中繼資料。骨架樣本在使用者明確勾選敏感資料並設定強密碼時，可進入加密的敏感攜帶內容；一般資料庫維持非敏感資料範圍。所有攜帶內容的欄位限定為可攜設定與明確選取的敏感骨架資料，原始影像、作業系統權限、裝置狀態與本機路徑維持於各自的本機邊界。匯入環境的模型仍待備時，手勢功能保持安全停用。

### 模型來源與正式發布門檻

OpenCV Zoo 的 `palm_detection_mediapipe_2023feb.onnx` 與 `handpose_estimation_mediapipe_2023feb.onnx` 均為 Apache-2.0、FP32，合計約 7.6 MB。兩個模型已從不可變上游 commit 取得，完成 SHA 與檔案大小核對、OpenCV 5 實際載入驗證，並登錄於 SBOM 與第三方 NOTICE。Windows EXE 真攝影機實機驗證、完整回歸測試、封裝與正式發布仍處於待完成狀態；完成與發布聲明在這些門檻全數通過後成立。

## 简体中文

> 本文档描述 v4.0.0 的开发中契约。手部模型集成、Windows EXE 真机测试与正式发布仍各自处于待完成状态；完成与发布声明以相应关卡通过为准。

### 默认、安全与安全回退边界

手势交互的默认状态为关闭，启用由用户明确操作。摄像头或模型待备、模型加载失败、跟踪中断或置信度不足时，功能会进入明确的安全停用状态；手势结果保持空值，聊天、语音、2.5D 角色与其他现有功能维持正常。原始摄像头图像的处理范围限定于实时内存；录制产物限定为归一化的单手 21 点骨架样本，并保存于专用敏感数据边界。

### 八个内置手势与默认映射

八个内置手势为：挥手（`wave`）→ 显示控制台；嘘声手势（`silence`）→ 静音；张开手掌（`open-palm`）→ 停止当前语音；握拳（`closed-fist`）→ 维持当前状态；拇指向上（`thumbs-up`）→ 墨寒以正向表情回应；拇指向下（`thumbs-down`）→ 维持当前状态；指向左方（`point-left`）→ 维持当前状态；指向右方（`point-right`）→ 维持当前状态。用户可用下拉选单重新绑定动作；内置手势提供停用与重置操作，并且其定义持续受到保护。

### 自定义、授权与携带

用户可新增、改名、删除自定义手势，并录制归一化的单手 21 点骨架样本；删除范围限定为所选自定义定义与骨架样本，摄像头、模型、其他手势与个人数据维持原状。自定义文字进入现有安全命令流程；任意程序执行位于该流程的能力范围之外。敏感设备、云服务及其他需要授权的能力仍须通过现有权限与确认。普通可移植文件的内容范围为手势开关、定义名称、映射等非敏感元数据。骨架样本在用户明确勾选敏感数据并设置强密码时，可进入加密的敏感可移植内容；普通数据库维持非敏感数据范围。所有可移植内容的字段限定为可移植设置与明确选取的敏感骨架数据，原始图像、操作系统权限、设备状态与本地路径维持于各自的本地边界。导入环境的模型仍待备时，手势功能保持安全停用。

### 模型来源与正式发布关卡

OpenCV Zoo 的 `palm_detection_mediapipe_2023feb.onnx` 与 `handpose_estimation_mediapipe_2023feb.onnx` 均为 Apache-2.0、FP32，合计约 7.6 MB。两个模型已从不可变上游 commit 获取，完成 SHA 与文件大小核对、OpenCV 5 实际加载验证，并登记于 SBOM 与第三方 NOTICE。Windows EXE 真摄像头实机验证、完整回归测试、打包与正式发布仍处于待完成状态；完成与发布声明在这些关卡全部通过后成立。

## English

> This document defines a v4.0.0 contract under development. Hand-model integration, real Windows EXE validation, and formal release each remain pending; completion and release claims begin after their corresponding gates pass.

### Defaults, safety, and safe fallback boundaries

Gesture interaction is off by default, and the user explicitly enables it. When a camera or model remains pending, model loading fails, tracking is lost, or confidence is insufficient, the feature enters a visible safe-disabled state. The gesture result remains empty while chat, speech, the 2.5D character, and established features continue normally. Raw camera-image processing is confined to transient memory. Recording output is limited to normalized 21-point single-hand skeleton samples stored within the dedicated sensitive-data boundary.

### Eight built-in gestures and default mappings

The eight built-ins are: Wave (`wave`) → show the control center; Quiet gesture (`silence`) → mute audio; Open palm (`open-palm`) → stop current speech; Closed fist (`closed-fist`) → retain the current state; Thumbs up (`thumbs-up`) → MoHan responds positively; Thumbs down (`thumbs-down`) → retain the current state; Point left (`point-left`) → retain the current state; and Point right (`point-right`) → retain the current state. Users can rebind each action through a drop-down selector. Built-ins provide disable and reset operations, while their definitions remain protected.

### Custom gestures, authorization, and portability

Users can add, rename, delete, and record custom gestures as normalized 21-point single-hand skeleton samples. Deletion scope is the selected custom definition and its skeleton samples; the camera, models, other gestures, and personal data remain intact. Custom text enters the established safe-command pipeline, with arbitrary program execution outside that pipeline's capability scope. Sensitive devices, cloud services, and other permission-bound capabilities still require their existing authorization and confirmation. An ordinary portable profile's content scope is non-sensitive metadata such as the gesture switch, definition names, and mappings. Skeleton samples may enter encrypted sensitive portable content when the user explicitly selects sensitive export and supplies a strong password; the ordinary database retains its non-sensitive-data scope. All portable-content fields are limited to portable settings and explicitly selected sensitive skeleton data, while raw images, operating-system permissions, device state, and local paths remain within their respective local boundaries. An import whose required models remain pending keeps gesture interaction safely disabled.

### Model provenance and release gate

OpenCV Zoo `palm_detection_mediapipe_2023feb.onnx` and `handpose_estimation_mediapipe_2023feb.onnx` are Apache-2.0 FP32 models totaling approximately 7.6 MB. Both were obtained from immutable upstream commits; their SHA values and file sizes were verified, they were loaded successfully with OpenCV 5, and they are recorded in the SBOM and third-party NOTICE. Real-camera validation in the Windows EXE, complete regression testing, packaging, and release remain pending. Completion and release claims begin after all of these gates pass.

## 日本語

> 本文書は開発中の v4.0.0 契約を示します。手モデルの統合、Windows EXE 実機検証、正式公開はそれぞれ完了待ちで、完了と公開の表明は対応する関門を通過した後に成立します。

### 既定値、安全性、安全なフォールバック境界

ジェスチャー操作の既定状態は無効で、利用者が明示的に有効化します。カメラまたはモデルが準備中、モデル読み込みに失敗、追跡が途切れる、信頼度が不足する場合、機能は明示的な安全停止状態へ移行します。ジェスチャー結果を空に保ち、会話、音声、2.5D キャラクター、既存機能を正常に継続します。元のカメラ画像の処理範囲は一時メモリに限定します。記録出力は正規化した片手 21 点骨格サンプルに限定し、専用の機密データ境界内に保存します。

### 八つの内蔵ジェスチャーと既定割り当て

八つの内蔵ジェスチャーは、手を振る（`wave`）→ コントロールセンターを表示、静かにの合図（`silence`）→ ミュート、開いた手のひら（`open-palm`）→ 現在の発話を停止、握りこぶし（`closed-fist`）→ 現在の状態を維持、親指を立てる（`thumbs-up`）→ 墨寒が肯定的に応える、親指を下げる（`thumbs-down`）→ 現在の状態を維持、左を指す（`point-left`）→ 現在の状態を維持、右を指す（`point-right`）→ 現在の状態を維持、です。利用者はドロップダウンで割り当てを変更できます。内蔵項目は無効化または初期化を提供し、その定義を継続して保護します。

### カスタム、許可、可搬性

利用者はカスタムジェスチャーを追加、改名、削除し、正規化した片手 21 点骨格サンプルとして記録できます。削除範囲は選択したカスタム定義と骨格サンプルに限定し、カメラ、モデル、他のジェスチャー、個人データを維持します。カスタム文字は既存の安全なコマンド経路を通り、任意プログラムの直接実行は経路の能力範囲外です。機密性の高い機器、クラウドサービス、その他の許可対象機能には、既存の許可と確認が必要です。通常の可搬プロファイルの内容範囲は、有効状態、定義名、割り当てなどの非機密メタデータです。骨格サンプルは、利用者が機密データの書き出しを明示的に選択し、強力なパスワードを設定した場合に、暗号化された機密可搬内容へ含められます。通常データベースは非機密データ範囲を維持します。可搬内容のフィールドは可搬設定と明示選択した機密骨格データに限定し、元画像、OS 権限、機器状態、ローカルパスはそれぞれのローカル境界に維持します。必要なモデルが準備中の環境へ取り込んだ場合、ジェスチャー機能を安全な無効状態に保ちます。

### モデル出典と正式公開ゲート

OpenCV Zoo の `palm_detection_mediapipe_2023feb.onnx` と `handpose_estimation_mediapipe_2023feb.onnx` は、いずれも Apache-2.0 の FP32 モデルで、合計約 7.6 MB です。両モデルは不変な上流 commit から取得し、SHA とファイルサイズの照合、OpenCV 5 での実読み込み検証を完了し、SBOM と第三者 NOTICE に登録済みです。Windows EXE による実カメラ実機検証、完全な回帰テスト、パッケージ化、正式公開は完了待ちです。機能完成と正式公開の表明は、これらの関門をすべて通過した後に成立します。
