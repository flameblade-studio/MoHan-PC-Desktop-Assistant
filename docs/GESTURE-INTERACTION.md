# 墨寒手勢互動規格／墨寒手势交互规格／MoHan Gesture Interaction Specification／墨寒ジェスチャー操作仕様

## 繁體中文

> 本文件描述 v4.0.0 的開發中契約，不代表手部模型、Windows EXE 實機測試或正式發布已完成；上述開發中狀態不代表已完成或已發布。

### 預設、安全與失敗邊界

手勢互動預設關閉，必須由使用者明確啟用。沒有攝影機、缺少模型、模型載入失敗、追蹤中斷或信心不足時，功能會明確安全停用，不推測手勢，也不影響聊天、語音、2.5D 角色或其他既有功能。原始攝影機影像不保存、不進入資料庫、攜帶檔、日誌或遙測；錄製只產生正規化的單手 21 點骨架樣本，且骨架樣本不得進入一般資料庫或一般攜帶檔。

### 八個內建手勢與預設映射

八個內建手勢為：揮手（`wave`）→ 顯示控制台；噓聲手勢（`silence`）→ 靜音；張開手掌（`open-palm`）→ 停止目前語音；握拳（`closed-fist`）→ 不執行動作；拇指向上（`thumbs-up`）→ 墨寒以正向表情回應；拇指向下（`thumbs-down`）→ 不執行動作；指向左方（`point-left`）→ 不執行動作；指向右方（`point-right`）→ 不執行動作。使用者可用下拉選單重新綁定動作；內建手勢可停用或重設，但不可刪除。

### 自訂、授權與攜帶

使用者可新增、改名、刪除自訂手勢，並錄製正規化的單手 21 點骨架樣本；刪除只移除所選自訂定義與骨架樣本，不刪除攝影機、模型、其他手勢或個人資料。自訂文字只會送入既有安全命令流程，不能直接執行任意程式；敏感裝置、雲端服務及其他需授權能力仍須通過既有權限與確認。一般攜帶檔只可包含手勢開關、定義名稱、映射等非敏感中繼資料，不得包含 21 點骨架樣本。骨架樣本只允許在使用者明確勾選敏感資料並設定強密碼時，進入加密的敏感攜帶內容；不得進入一般資料庫。任何攜帶內容都不包含原始影像、作業系統權限、裝置狀態或本機路徑；匯入缺少模型時保持安全停用。

### 模型來源與正式發布門檻

OpenCV Zoo 的 `palm_detection_mediapipe_2023feb.onnx` 與 `handpose_estimation_mediapipe_2023feb.onnx` 均為 Apache-2.0、FP32，合計約 7.6 MB。兩個模型已從不可變上游 commit 取得，完成 SHA 與檔案大小核對、OpenCV 5 實際載入驗證，並登錄於 SBOM 與第三方 NOTICE。仍未完成 Windows EXE 真攝影機實機驗證、完整回歸測試、封裝與正式發布；這些門檻未通過不得宣稱完成或發布。

## 简体中文

> 本文档描述 v4.0.0 的开发中契约，不代表手部模型、Windows EXE 真机测试或正式发布已经完成；上述开发中状态不代表已经完成或发布。

### 默认、安全与失败边界

手势交互默认关闭，必须由用户明确启用。没有摄像头、缺少模型、模型加载失败、跟踪中断或置信度不足时，功能会明确安全停用，不推测手势，也不影响聊天、语音、2.5D 角色或其他现有功能。原始摄像头图像不保存、不进入数据库、可移植文件、日志或遥测；录制只产生归一化的单手 21 点骨架样本，且骨架样本不得进入普通数据库或普通可移植文件。

### 八个内置手势与默认映射

八个内置手势为：挥手（`wave`）→ 显示控制台；嘘声手势（`silence`）→ 静音；张开手掌（`open-palm`）→ 停止当前语音；握拳（`closed-fist`）→ 不执行动作；拇指向上（`thumbs-up`）→ 墨寒以正向表情回应；拇指向下（`thumbs-down`）→ 不执行动作；指向左方（`point-left`）→ 不执行动作；指向右方（`point-right`）→ 不执行动作。用户可用下拉选单重新绑定动作；内置手势可停用或重置，但不可删除。

### 自定义、授权与携带

用户可新增、改名、删除自定义手势，并录制归一化的单手 21 点骨架样本；删除只移除所选自定义定义与骨架样本，不删除摄像头、模型、其他手势或个人数据。自定义文字只会送入现有安全命令流程，不能直接执行任意程序；敏感设备、云服务及其他需要授权的能力仍须通过现有权限与确认。普通可移植文件只能包含手势开关、定义名称、映射等非敏感元数据，不得包含 21 点骨架样本。骨架样本只有在用户明确勾选敏感数据并设置强密码时，才可进入加密的敏感可移植内容；不得进入普通数据库。任何可移植内容都不包含原始图像、操作系统权限、设备状态或本地路径；导入后缺少模型时保持安全停用。

### 模型来源与正式发布关卡

OpenCV Zoo 的 `palm_detection_mediapipe_2023feb.onnx` 与 `handpose_estimation_mediapipe_2023feb.onnx` 均为 Apache-2.0、FP32，合计约 7.6 MB。两个模型已从不可变上游 commit 获取，完成 SHA 与文件大小核对、OpenCV 5 实际加载验证，并登记于 SBOM 与第三方 NOTICE。仍未完成 Windows EXE 真摄像头实机验证、完整回归测试、打包与正式发布；这些关卡未通过不得宣称完成或发布。

## English

> This document defines a v4.0.0 contract under development. It does not claim that the hand models, real Windows EXE validation, or the release are complete.

### Defaults, safety, and failure boundaries

Gesture interaction is off by default and requires explicit user enablement. If no camera or model is available, model loading fails, tracking is lost, or confidence is insufficient, the feature visibly fails closed without guessing a gesture or affecting chat, speech, the 2.5D character, or established features. Raw camera images are never retained or written to the database, portable profile, logs, or telemetry. Recording produces only normalized 21-point single-hand skeleton samples, and those samples must never enter the ordinary database or an ordinary portable profile.

### Eight built-in gestures and default mappings

The eight built-ins are: Wave (`wave`) → show the control center; Quiet gesture (`silence`) → mute audio; Open palm (`open-palm`) → stop current speech; Closed fist (`closed-fist`) → no action; Thumbs up (`thumbs-up`) → MoHan responds positively; Thumbs down (`thumbs-down`) → no action; Point left (`point-left`) → no action; and Point right (`point-right`) → no action. Users can rebind each action through a drop-down selector. Built-ins may be disabled or reset, but cannot be deleted.

### Custom gestures, authorization, and portability

Users can add, rename, delete, and record custom gestures as normalized 21-point single-hand skeleton samples. Deletion removes only the selected custom definition and its skeleton samples; it does not remove the camera, models, other gestures, or personal data. Custom text enters the established safe-command pipeline and never directly executes arbitrary programs. Sensitive devices, cloud services, and other permission-bound capabilities still require their existing authorization and confirmation. An ordinary portable profile may contain only non-sensitive metadata such as the gesture switch, definition names, and mappings; it must never contain 21-point skeleton samples. Skeleton samples may enter encrypted sensitive portable content only when the user explicitly selects sensitive export and supplies a strong password; they must never enter the ordinary database. No portable content includes raw images, operating-system permissions, device state, or local paths. An import without the required models remains safely disabled.

### Model provenance and release gate

OpenCV Zoo `palm_detection_mediapipe_2023feb.onnx` and `handpose_estimation_mediapipe_2023feb.onnx` are Apache-2.0 FP32 models totaling approximately 7.6 MB. Both were obtained from immutable upstream commits; their SHA values and file sizes were verified, they were loaded successfully with OpenCV 5, and they are recorded in the SBOM and third-party NOTICE. Real-camera validation in the Windows EXE, complete regression testing, packaging, and release are still unfinished. This status does not claim that the feature is complete or released.

## 日本語

> 本文書は開発中の v4.0.0 契約を示すもので、手モデル、Windows EXE 実機検証、正式公開の完了を主張しません。

### 既定値、安全性、失敗時の境界

ジェスチャー操作は既定で無効であり、利用者による明示的な有効化が必要です。カメラまたはモデルがない、モデル読み込みに失敗する、追跡が途切れる、信頼度が不足する場合は、ジェスチャーを推測せず、会話、音声、2.5D キャラクター、既存機能に影響を与えず明示的かつ安全に停止します。元のカメラ画像を保存せず、データベース、可搬プロファイル、ログ、テレメトリーへ書き込みません。記録で生成するのは正規化した片手 21 点骨格サンプルだけであり、そのサンプルを通常データベースまたは通常の可搬プロファイルへ含めません。

### 八つの内蔵ジェスチャーと既定割り当て

八つの内蔵ジェスチャーは、手を振る（`wave`）→ コントロールセンターを表示、静かにの合図（`silence`）→ ミュート、開いた手のひら（`open-palm`）→ 現在の発話を停止、握りこぶし（`closed-fist`）→ 何もしない、親指を立てる（`thumbs-up`）→ 墨寒が肯定的に応える、親指を下げる（`thumbs-down`）→ 何もしない、左を指す（`point-left`）→ 何もしない、右を指す（`point-right`）→ 何もしない、です。利用者はドロップダウンで割り当てを変更できます。内蔵項目は無効化または初期化できますが、削除できません。

### カスタム、許可、可搬性

利用者はカスタムジェスチャーを追加、改名、削除し、正規化した片手 21 点骨格サンプルとして記録できます。削除するのは選択したカスタム定義と骨格サンプルだけで、カメラ、モデル、他のジェスチャー、個人データは削除しません。カスタム文字は既存の安全なコマンド経路だけを通り、任意のプログラムを直接実行しません。機密性の高い機器、クラウドサービス、その他の許可対象機能には、既存の許可と確認が必要です。通常の可搬プロファイルに含められるのは、有効状態、定義名、割り当てなどの非機密メタデータだけで、21 点骨格サンプルを含めません。骨格サンプルは、利用者が機密データの書き出しを明示的に選択し、強力なパスワードを設定した場合に限り、暗号化された機密可搬内容へ含められます。通常データベースには保存しません。いずれの可搬内容にも元画像、OS 権限、機器状態、ローカルパスを含めず、必要なモデルがない環境へ取り込んだ場合は安全に無効のままとします。

### モデル出典と正式公開ゲート

OpenCV Zoo の `palm_detection_mediapipe_2023feb.onnx` と `handpose_estimation_mediapipe_2023feb.onnx` は、いずれも Apache-2.0 の FP32 モデルで、合計約 7.6 MB です。両モデルは不変な上流 commit から取得し、SHA とファイルサイズの照合、OpenCV 5 での実読み込み検証を完了し、SBOM と第三者 NOTICE に登録済みです。一方、Windows EXE による実カメラ実機検証、完全な回帰テスト、パッケージ化、正式公開は未完了です。この状況は機能の完成または正式公開の完了を主張しません。
