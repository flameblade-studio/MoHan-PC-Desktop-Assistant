# 角色資料 fallback 清冊／角色数据 fallback 清单／Character-data fallback inventory／キャラクターデータ fallback 一覧

## 繁體中文


狀態：2026-10-08 實測盤點；本工作包只記錄，不移除任何相容路徑。

### 判定原則

本清冊收錄角色資料、角色素材或舊 profile 欄位缺漏時，程式改用固定值、內建角色資料、上一份有效資料或舊素材路徑的位置。角色包 validator 或 typed loader 直接拒絕缺件的行為另列為 fail-closed 邊界，不算 fallback。

「舊使用者資料依賴」只在 storage、migration 或測試有直接證據時標為「是」；只有格式或 API 相容測試時標為「未證實」。

### 實際 fallback

| ID | 程式位置 | 觸發條件與結果 | 舊使用者資料依賴 |
|---|---|---|---|
| F-01 | `infrastructure/complete_halfbody_expressions.py:111-116`；`infrastructure/detachable_halfbody_assets.py:54-59`；`infrastructure/layered_face_renderer.py:224-259,312-320` | 選用的 complete 或 detachable 半身素材目錄未安裝時回 `None` 或空 pixmap，renderer 依序嘗試 native、detachable、gesture portrait，最後改走既有 `render_pose()` 分層素材；已安裝但損壞的 manifest 仍報錯。 | 未證實；這是安裝素材狀態，測試見 `tests/test_half_body_blink_makeup_order.py:65`。 |
| F-02 | `application/adaptive_character_runtime.py:149-150,177-182,242-268`；`presentation/companion_core.py:127-152` | fullbody 素材缺漏、停用、framing 不可用或 dispatch 失敗時，先保留 last-known-good，沒有時沿用原子 frame 的舊半身 body 並標記 `used_legacy=True`；啟動 composition 失敗會關閉 adaptive 路徑。 | 否；測試是執行期素材缺件，見 `tests/test_adaptive_character_app_wiring.py:117`、`tests/test_full_body_performance_bridge.py:302`。 |
| F-03 | `domain/pose_runtime_loader.py:137-169,204-235,460-461` | `PoseRuntimeLoader` 一開始使用注入的 `fallback_atlas`；manifest、讀取或解碼失敗時拒絕候選並保留目前 active atlas。 | 未證實；只有 API 或合成測試使用 `legacy-v3` 的 `builtin-three-view`，見 `tests/test_pose_runtime_loader.py:156,197`，未找到產品 composition 呼叫。 |
| F-04 | `domain/pose_pack.py:24,132-134,327-355` | pose pack manifest 為 v1 時建立 `legacy-v3` rig contract；這是明確舊格式讀取，不是缺包後自動改讀另一包。 | 未證實；只有 `tests/test_pose_pack.py:321` 的合成舊包證據，未找到舊 profile 儲存 pose pack 的證據。 |
| F-05 | `presentation/companion_face_animation.py:379-384`；`domain/face_rig.py:138-150`；`domain/companion_animation_contract.py:45-48`；`presentation/companion_face_assets.py:682-690`；`presentation/companion_visual_physics.py:395-403` | 未載入的 expression 改用 `idle`；未知 pose 改用 `FacePose.FRONT`，未知 viseme 改用 `Viseme.E`；姿勢沒有 silhouette 時用 rig 的 front silhouette；表情專屬 physics layer 缺漏時用呼叫端姿勢層。 | 未證實；未找到 profile 或 storage 測試證明依賴。 |
| F-06 | `presentation/companion_blink_composite.py:129-179` | 專屬 half-blink 缺漏時嘗試通用 `blink_half{suffix}`，仍缺漏則保留原 frame；專屬 closed-blink 缺漏時讀通用 `blink{suffix}`。 | 未證實；這是素材相容路徑。 |
| F-07 | `domain/character_pack/character_data_models.py:36-44`；`domain/app_profile.py:64-84`；`domain/sensory_synesthesia.py:144-151`；`domain/language_support.py:121-129` | 未支援語系統一選 `zh-TW` persona、runtime dialogue 或 reminder；支援語系仍讀各自角色資料。 | 未證實；`ui_language` 可儲存，但沒有舊 profile 曾含未支援語系的證據；快照測試見 `tests/test_persona_dialogue_voice_extraction.py:154`。 |
| F-08 | `domain/app_profile.py:87-95`；`integrations/ai_client.py:375`；`presentation/dashboard_settings_persistence.py:188-196` | profile 的 `persona_prompt` 缺少或空白時使用角色 persona；非空白自訂值保留並個人化，遷移只替換已知舊內建 prompt。 | 是；`infrastructure/profile_transfer.py:127`、`tests/test_public_profile_persona.py:21`、`tests/test_profile_transfer.py:172` 直接驗證保存與匯入。 |
| F-09 | `application/companion_phrasebook.py:67-93,103-126`；`application/proactive_companion_composition.py:43-50` | 客製 phrasebook 或 scenario 缺漏時讀角色包內建台詞；內建也沒有該 key 時回空字串。 | 是；portable profile 包含 phrasebook，`tests/test_profile_transfer.py:566` 驗證舊 v1 自訂 welcome 保留。 |
| F-10 | `domain/speech_configuration.py:98-110,144-167`；使用點包括 `presentation/companion_speech_runtime.py:376,453,540,639,1014`、`presentation/dashboard_voice.py:237,243,711,742`、`presentation/companion_core.py:544,698` | voice DB 欄位或一次性 migration marker 缺漏時，使用 `assets/characters/mohan/voice/profile.json` 的預設 provider、voice、rate、volume 與 instructions；既有使用者覆寫保持優先。 | 是；`tests/test_core.py:104` 與 `tests/test_character_persona_data.py` 的 voice migration 測試，以及 `infrastructure/profile_transfer.py:118`。 |
| F-11 | `infrastructure/db.py:101-107,525-555`；`domain/language_support.py:17-23` | `existing_install` 的舊 DB 缺 profile 欄位時用 `LEGACY_PROFILE_DEFAULTS` 以 `INSERT OR IGNORE` 補齊；只有 transcription prompt 等於已知舊值時才重建本地化 prompt，其他使用者值保留。 | 是；這段程式只為既有安裝執行。尚未找到專門覆蓋 `existing_install=True` 的測試，因此證據是明確 migration 分支，不宣稱已有測試覆蓋。 |

### Fail-closed 與固定預設邊界

| ID | 邊界 | 結論 |
|---|---|---|
| N-01 | `domain/character_pack/character_data.py:159-197`；`domain/character_rig_data.py:366-683`；`domain/character_expression_data.py:118-422`；`infrastructure/character_source_pack.py:299-573` | Persona、四語 dialogue、events、voice、rig、expression 或必需 pack component 缺漏或損壞時直接拒絕，沒有改讀寫死角色資料；測試見 `tests/test_character_runtime_data.py` 與 `tests/test_character_source.py:237-284`。 |
| N-02 | `application/service_container.py:123-237,364-365` | `create_default_character_source()` 目前固定建立 `LegacyMohanCharacterSource`；這是第一階段維持既有執行行為的 composition 預設，不是角色 JSON 缺漏後才啟動的 fallback。pack reader 與 legacy adapter 欄位等值測試見 `tests/test_character_source.py:292-348`。 |

### 後續處置

所有 F 項目維持現狀，直到林可芸測試角色完成眨眼、說話、姿勢、換裝、上妝、提醒、對話、語音、缺少 optional capability 與惡意包負例測試。屆時逐項判定保留、資料化或移除；本清冊不預先替擁有者決定相容政策。

## 简体中文


状态：2026-10-08 实测盘点；本工作包只记录，不移除任何兼容路径。

### 判定原则

本清单收录角色数据、角色素材或旧 profile 字段缺失时，程序改用固定值、内置角色数据、上一份有效数据或旧素材路径的位置。角色包 validator 或 typed loader 直接拒绝缺件的行为另列为 fail-closed 边界，不算 fallback。

“旧用户数据依赖”只在 storage、migration 或测试有直接证据时标为“是”；只有格式或 API 兼容测试时标为“未证实”。

### 实际 fallback

| ID | 程序位置 | 触发条件与结果 | 旧用户数据依赖 |
|---|---|---|---|
| F-01 | `infrastructure/complete_halfbody_expressions.py:111-116`；`infrastructure/detachable_halfbody_assets.py:54-59`；`infrastructure/layered_face_renderer.py:224-259,312-320` | 选择的 complete 或 detachable 半身素材目录未安装时返回 `None` 或空 pixmap，renderer 依次尝试 native、detachable、gesture portrait，最后改走既有 `render_pose()` 分层素材；已安装但损坏的 manifest 仍报错。 | 未证实；这是安装素材状态，测试见同一路径（另见：`tests/test_half_body_blink_makeup_order.py:65`）。 |
| F-02 | `application/adaptive_character_runtime.py:149-150,177-182,242-268`；`presentation/companion_core.py:127-152` | fullbody 素材缺失、停用、framing 不可用或 dispatch 失败时，先保留 last-known-good，没有时沿用原子 frame 的旧半身 body 并标记 `used_legacy=True`；启动 composition 失败会关闭 adaptive 路径。 | 否；测试是运行时素材缺件（另见：`tests/test_adaptive_character_app_wiring.py:117`、`tests/test_full_body_performance_bridge.py:302`）。 |
| F-03 | `domain/pose_runtime_loader.py:137-169,204-235,460-461` | `PoseRuntimeLoader` 一开始使用注入的 `fallback_atlas`；manifest、读取或解码失败时拒绝候选并保留当前 active atlas。 | 未证实；仅 API 或合成测试使用该路径（另见：`legacy-v3`、`builtin-three-view`、`tests/test_pose_runtime_loader.py:156,197`）。 |
| F-04 | `domain/pose_pack.py:24,132-134,327-355` | pose pack manifest 为 v1 时建立 `legacy-v3` rig contract；这是明确旧格式读取，不是缺包后自动改读另一包。 | 未证实；只有合成旧包测试（另见：`tests/test_pose_pack.py:321`）。 |
| F-05 | `presentation/companion_face_animation.py:379-384`；`domain/face_rig.py:138-150`；`domain/companion_animation_contract.py:45-48`；`presentation/companion_face_assets.py:682-690`；`presentation/companion_visual_physics.py:395-403` | 未加载的 expression 改用 `idle`；未知 pose 改用 `FacePose.FRONT`，未知 viseme 改用 `Viseme.E`；姿势没有 silhouette 时使用 rig 的 front silhouette；表情专属 physics layer 缺失时使用调用端姿势层。 | 未证实；未找到 profile 或 storage 测试。 |
| F-06 | `presentation/companion_blink_composite.py:129-179` | 专属 half-blink 缺失时尝试通用 `blink_half{suffix}`，仍缺失则保留原 frame；专属 closed-blink 缺失时读取通用 `blink{suffix}`。 | 未证实；这是素材兼容路径。 |
| F-07 | `domain/character_pack/character_data_models.py:36-44`；`domain/app_profile.py:64-84`；`domain/sensory_synesthesia.py:144-151`；`domain/language_support.py:121-129` | 不支持的语言统一选择 `zh-TW` persona、runtime dialogue 或 reminder；支持的语言仍读取各自角色数据。 | 未证实；没有旧 profile 包含不支持语言的证据（另见：`ui_language`、`tests/test_persona_dialogue_voice_extraction.py:154`）。 |
| F-08 | `domain/app_profile.py:87-95`；`integrations/ai_client.py:375`；`presentation/dashboard_settings_persistence.py:188-196` | profile 的 `persona_prompt` 缺少或为空时使用角色 persona；非空自定义值保留并个性化，迁移只替换已知旧内置 prompt。 | 是；上述路径直接验证保存与导入（另见：`infrastructure/profile_transfer.py:127`、`tests/test_public_profile_persona.py:21`、`tests/test_profile_transfer.py:172`）。 |
| F-09 | `application/companion_phrasebook.py:67-93,103-126`；`application/proactive_companion_composition.py:43-50` | 自定义 phrasebook 或 scenario 缺失时读取角色包内置台词；内置也没有该 key 时返回空字符串。 | 是；portable profile 包含 phrasebook（另见：`tests/test_profile_transfer.py:566`）。 |
| F-10 | `domain/speech_configuration.py:98-110,144-167`；使用點包括 `presentation/companion_speech_runtime.py:376,453,540,639,1014`、`presentation/dashboard_voice.py:237,243,711,742`、`presentation/companion_core.py:544,698` | voice DB 字段或一次性 migration marker 缺失时，使用角色 voice profile 的默认值；既有用户覆盖保持优先（另见：`assets/characters/mohan/voice/profile.json`）。 | 是；上述测试与 profile transfer 为直接证据（另见：`tests/test_core.py:104`、`tests/test_character_persona_data.py`、`infrastructure/profile_transfer.py:118`）。 |
| F-11 | `infrastructure/db.py:101-107,525-555`；`domain/language_support.py:17-23` | `existing_install` 的旧 DB 缺 profile 字段时用 `LEGACY_PROFILE_DEFAULTS` 以 `INSERT OR IGNORE` 补齐；只有 transcription prompt 等于已知旧值时才重建本地化 prompt，其他用户值保留。 | 是；此分支只为既有安装执行，但未找到专门测试（另见：`existing_install=True`）。 |

### Fail-closed 与固定默认边界

| ID | 边界 | 结论 |
|---|---|---|
| N-01 | `domain/character_pack/character_data.py:159-197`；`domain/character_rig_data.py:366-683`；`domain/character_expression_data.py:118-422`；`infrastructure/character_source_pack.py:299-573` | 缺失或损坏时直接拒绝，不改读写死角色数据（另见：`tests/test_character_runtime_data.py`、`tests/test_character_source.py:237-284`）。 |
| N-02 | `application/service_container.py:123-237,364-365` | 这是第一阶段维持既有运行行为的 composition 默认，不是角色 JSON 缺失后才启动的 fallback（另见：`create_default_character_source()`、`LegacyMohanCharacterSource`、`tests/test_character_source.py:292-348`）。 |

### 后续处置

所有 F 项目维持现状，直到林可芸测试角色完成上述测试；届时逐项判定保留、数据化或移除，本清单不预先替所有者决定兼容政策。

## English


Status: measured on 2026-10-08; this work package records compatibility paths and removes none.

### Classification rule

This inventory covers places where missing character data, assets, or legacy profile fields select a fixed value, bundled character data, last-known-good data, or a legacy asset path. Direct rejection by a character-pack validator or typed loader is listed separately as a fail-closed boundary, not a fallback.

“Existing-user-data dependency” is marked “yes” only when storage, migration, or tests provide direct evidence; format-only or API-only compatibility is marked “not demonstrated.”

### Active fallbacks

| ID | Code location | Trigger and result | Existing-user-data dependency |
|---|---|---|---|
| F-01 | `infrastructure/complete_halfbody_expressions.py:111-116`；`infrastructure/detachable_halfbody_assets.py:54-59`；`infrastructure/layered_face_renderer.py:224-259,312-320` | When an optional complete or detachable half-body directory is absent, the loader returns `None` or a null pixmap; the renderer tries native, detachable, and gesture portraits before the existing layered `render_pose()` path. A present but invalid manifest still fails. | Not demonstrated; this is installed-asset state, covered at `tests/test_half_body_blink_makeup_order.py:65`. |
| F-02 | `application/adaptive_character_runtime.py:149-150,177-182,242-268`；`presentation/companion_core.py:127-152` | Missing or disabled full-body assets, unavailable framing, or dispatch failure retain last-known-good output, otherwise reuse the atomic frame's legacy half-body frame with `used_legacy=True`; composition startup failure disables the adaptive path. | No; tests cover runtime asset absence (See also `tests/test_adaptive_character_app_wiring.py:117`, `tests/test_full_body_performance_bridge.py:302`). |
| F-03 | `domain/pose_runtime_loader.py:137-169,204-235,460-461` | `PoseRuntimeLoader` starts with an injected `fallback_atlas`; manifest, read, or decode failure rejects the candidate and retains the active atlas. | Not demonstrated; only API and synthetic tests use this path, and no product composition caller was found (See also `legacy-v3`, `builtin-three-view`, `tests/test_pose_runtime_loader.py:156,197`). |
| F-04 | `domain/pose_pack.py:24,132-134,327-355` | A v1 pose-pack manifest creates a `legacy-v3` rig contract; this is explicit legacy-format reading, not automatic selection of another pack after a missing pack. | Not demonstrated; only a synthetic legacy-pack test exists (See also `tests/test_pose_pack.py:321`). |
| F-05 | `presentation/companion_face_animation.py:379-384`；`domain/face_rig.py:138-150`；`domain/companion_animation_contract.py:45-48`；`presentation/companion_face_assets.py:682-690`；`presentation/companion_visual_physics.py:395-403` | An unloaded expression selects `idle`; unknown pose and viseme values select `FacePose.FRONT` and `Viseme.E`; a pose without a silhouette uses the rig's front silhouette; a missing expression-specific physics layer uses the caller's pose layer. | Not demonstrated; no profile or storage dependency test was found. |
| F-06 | `presentation/companion_blink_composite.py:129-179` | A missing dedicated half blink tries `blink_half{suffix}` and otherwise preserves the original frame; a missing dedicated closed blink reads `blink{suffix}`. | Not demonstrated; this is asset compatibility. |
| F-07 | `domain/character_pack/character_data_models.py:36-44`；`domain/app_profile.py:64-84`；`domain/sensory_synesthesia.py:144-151`；`domain/language_support.py:121-129` | Unsupported locales select `zh-TW` persona, runtime dialogue, or reminders; supported locales continue to read their own character data. | Not demonstrated; `ui_language` is stored, but no evidence shows an old profile containing an unsupported locale (See also `tests/test_persona_dialogue_voice_extraction.py:154`). |
| F-08 | `domain/app_profile.py:87-95`；`integrations/ai_client.py:375`；`presentation/dashboard_settings_persistence.py:188-196` | A missing or blank profile `persona_prompt` uses the character persona; nonblank custom content is preserved and personalized, while migration replaces only known legacy bundled prompts. | Yes; the cited profile-transfer and tests directly verify preservation and import (See also `infrastructure/profile_transfer.py:127`, `tests/test_public_profile_persona.py:21`, `tests/test_profile_transfer.py:172`). |
| F-09 | `application/companion_phrasebook.py:67-93,103-126`；`application/proactive_companion_composition.py:43-50` | A missing custom phrasebook or scenario reads bundled character lines; if the bundled catalog also lacks the key, the result is an empty string. | Yes; portable profiles contain the phrasebook, and the cited v1 test preserves a custom welcome (See also `tests/test_profile_transfer.py:566`). |
| F-10 | `domain/speech_configuration.py:98-110,144-167`；使用點包括 `presentation/companion_speech_runtime.py:376,453,540,639,1014`, `presentation/dashboard_voice.py:237,243,711,742`, `presentation/companion_core.py:544,698` | Missing voice DB fields or the one-time migration marker use provider, voice, rate, volume, and instruction defaults from the character voice profile; existing user overrides retain priority (See also `assets/characters/mohan/voice/profile.json`). | Yes; voice migration tests and profile transfer provide direct evidence (See also `tests/test_core.py:104`, `tests/test_character_persona_data.py`, `infrastructure/profile_transfer.py:118`). |
| F-11 | `infrastructure/db.py:101-107,525-555`；`domain/language_support.py:17-23` | For an `existing_install`, missing legacy DB profile fields are supplied with `LEGACY_PROFILE_DEFAULTS` through `INSERT OR IGNORE`; the localized transcription prompt is rebuilt only when the stored prompt equals the known legacy value, preserving other user values. | Yes; the branch runs only for existing installations, although no dedicated `existing_install=True` test was found. |

### Fail-closed and fixed-default boundaries

| ID | Boundary | Conclusion |
|---|---|---|
| N-01 | `domain/character_pack/character_data.py:159-197`；`domain/character_rig_data.py:366-683`；`domain/character_expression_data.py:118-422`；`infrastructure/character_source_pack.py:299-573` | Missing or invalid required data is rejected directly; no hard-coded character data is selected (See also `tests/test_character_runtime_data.py`, `tests/test_character_source.py:237-284`). |
| N-02 | `application/service_container.py:123-237,364-365` | This is the phase-one composition default that preserves current behavior, not a fallback activated by missing character JSON (See also `create_default_character_source()`, `LegacyMohanCharacterSource`, `tests/test_character_source.py:292-348`). |

### Follow-up disposition

Every F item remains unchanged until the Lin Keyun test character passes blink, speech, pose, outfit, makeup, reminder, dialogue, voice, missing optional-capability, and malicious-pack negative tests. Each item can then be retained, data-driven, or removed; this inventory does not decide compatibility policy for the owner.

## 日本語


状態：2026-10-08 の実測棚卸し。本作業パッケージでは互換経路を記録するだけで削除しない。

### 判定基準

この一覧は、キャラクターデータ、素材、旧 profile 項目が欠けた場合に固定値、内蔵データ、直前の有効データ、旧素材経路を選ぶ箇所を対象とする。character-pack validator または typed loader が欠落を直接拒否する場合は fail-closed 境界として別記し、fallback には数えない。

「既存ユーザーデータ依存」は storage、migration、test に直接証拠がある場合だけ「あり」とし、形式または API の互換試験だけの場合は「未証明」とする。

### 実際の fallback

| ID | コード位置 | 条件と結果 | 既存ユーザーデータ依存 |
|---|---|---|---|
| F-01 | `infrastructure/complete_halfbody_expressions.py:111-116`；`infrastructure/detachable_halfbody_assets.py:54-59`；`infrastructure/layered_face_renderer.py:224-259,312-320` | 任意の complete または detachable 半身素材ディレクトリが未導入なら `None` または空 pixmap を返し、renderer は native、detachable、gesture portrait の順に試して最後に既存の分層 `render_pose()` へ移る。存在する manifest が壊れている場合は失敗する。 | 未証明。導入素材の状態であり、試験は同パスを参照（参照：`tests/test_half_body_blink_makeup_order.py:65`）。 |
| F-02 | `application/adaptive_character_runtime.py:149-150,177-182,242-268`；`presentation/companion_core.py:127-152` | fullbody 素材の欠落・無効化、framing 不可、dispatch 失敗では last-known-good を優先し、なければ atomic frame の旧半身 body を `used_legacy=True` で使用する。composition の起動失敗では adaptive 経路を無効化する。 | なし。試験対象は実行時素材の欠落（参照：`tests/test_adaptive_character_app_wiring.py:117`、`tests/test_full_body_performance_bridge.py:302`）。 |
| F-03 | `domain/pose_runtime_loader.py:137-169,204-235,460-461` | `PoseRuntimeLoader` は注入された `fallback_atlas` から開始し、manifest・読取・decode の失敗では候補を拒否して active atlas を保持する。 | 未証明。API と合成試験だけが利用し、製品 composition の呼出しは見つからない（参照：`legacy-v3`、`builtin-three-view`、`tests/test_pose_runtime_loader.py:156,197`）。 |
| F-04 | `domain/pose_pack.py:24,132-134,327-355` | pose pack manifest が v1 なら `legacy-v3` rig contract を作る。これは明示的な旧形式読取であり、pack 欠落後に別 pack を自動選択する動作ではない。 | 未証明。合成した旧 pack の試験だけがある（参照：`tests/test_pose_pack.py:321`）。 |
| F-05 | `presentation/companion_face_animation.py:379-384`；`domain/face_rig.py:138-150`；`domain/companion_animation_contract.py:45-48`；`presentation/companion_face_assets.py:682-690`；`presentation/companion_visual_physics.py:395-403` | 未読込の expression は `idle`、未知の pose と viseme は `FacePose.FRONT` と `Viseme.E`、silhouette のない pose は rig の front silhouette、表情専用 physics layer の欠落は呼出し元の pose layer を使う。 | 未証明。profile または storage の依存試験は見つからない。 |
| F-06 | `presentation/companion_blink_composite.py:129-179` | 専用 half-blink がなければ `blink_half{suffix}` を試し、それもなければ元 frame を保つ。専用 closed-blink がなければ `blink{suffix}` を読む。 | 未証明。素材互換経路である。 |
| F-07 | `domain/character_pack/character_data_models.py:36-44`；`domain/app_profile.py:64-84`；`domain/sensory_synesthesia.py:144-151`；`domain/language_support.py:121-129` | 未対応 locale は `zh-TW` の persona、runtime dialogue、reminder を選び、対応 locale は各自のキャラクターデータを読む。 | 未証明。`ui_language` は保存されるが、未対応 locale を含む旧 profile の証拠はない（参照：`tests/test_persona_dialogue_voice_extraction.py:154`）。 |
| F-08 | `domain/app_profile.py:87-95`；`integrations/ai_client.py:375`；`presentation/dashboard_settings_persistence.py:188-196` | profile の `persona_prompt` が欠落または空ならキャラクター persona を使い、空でないカスタム値は保持・個人化する。migration は既知の旧内蔵 prompt だけを置換する。 | あり。記載の profile-transfer と試験が保持・取込を直接検証する（参照：`infrastructure/profile_transfer.py:127`、`tests/test_public_profile_persona.py:21`、`tests/test_profile_transfer.py:172`）。 |
| F-09 | `application/companion_phrasebook.py:67-93,103-126`；`application/proactive_companion_composition.py:43-50` | カスタム phrasebook または scenario がなければ内蔵キャラクター台詞を読み、内蔵側にも key がなければ空文字列を返す。 | あり。portable profile に phrasebook があり、記載の v1 試験で custom welcome の保持を検証する（参照：`tests/test_profile_transfer.py:566`）。 |
| F-10 | `domain/speech_configuration.py:98-110,144-167`；使用點包括 `presentation/companion_speech_runtime.py:376,453,540,639,1014`、`presentation/dashboard_voice.py:237,243,711,742`、`presentation/companion_core.py:544,698` | voice DB 項目または一回限りの migration marker がなければ character voice profile の provider、voice、rate、volume、instructions の既定値を使い、既存ユーザーの上書きを優先する（参照：`assets/characters/mohan/voice/profile.json`）。 | あり。voice migration 試験と profile transfer が直接証拠となる（参照：`tests/test_core.py:104`、`tests/test_character_persona_data.py`、`infrastructure/profile_transfer.py:118`）。 |
| F-11 | `infrastructure/db.py:101-107,525-555`；`domain/language_support.py:17-23` | `existing_install` の旧 DB で profile 項目が欠ける場合は `LEGACY_PROFILE_DEFAULTS` を `INSERT OR IGNORE` で補い、保存 prompt が既知の旧値と一致する場合だけローカライズ prompt を再構築して他のユーザー値を保持する。 | あり。この分岐は既存インストール専用だが、専用試験は見つからない（参照：`existing_install=True`）。 |

### Fail-closed と固定既定境界

| ID | 境界 | 結論 |
|---|---|---|
| N-01 | `domain/character_pack/character_data.py:159-197`；`domain/character_rig_data.py:366-683`；`domain/character_expression_data.py:118-422`；`infrastructure/character_source_pack.py:299-573` | 必要データの欠落・破損は直接拒否し、ハードコードされたキャラクターデータへ切り替えない（参照：`tests/test_character_runtime_data.py`、`tests/test_character_source.py:237-284`）。 |
| N-02 | `application/service_container.py:123-237,364-365` | これは現行挙動を保つ第一段階の composition 既定であり、character JSON 欠落時に起動する fallback ではない（参照：`create_default_character_source()`、`LegacyMohanCharacterSource`、`tests/test_character_source.py:292-348`）。 |

### 後続対応

すべての F 項目は林可芸テストキャラクターが眨き、発話、pose、outfit、makeup、reminder、dialogue、voice、optional capability 欠落、悪意ある pack の負例試験を通るまで維持する。その後に各項目の保持・データ化・削除を判断し、本一覧は所有者に代わって互換方針を決定しない。
