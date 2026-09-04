# 關鍵防護變異稽核／关键防护变异审计／Critical Guard Mutation Audit／重要防護のミューテーション監査

## 繁體中文

2026-09-04 在 test/gate-mutation-audit 分支逐輪執行「破壞、定向測試、記錄、立即還原」。共稽核 13 列防護；原有測試 12 列有效、1 列紙糊。每輪產品與資產變異還原後，工作樹均回到該輪前狀態。

| 防護 | 真實變異 | 變異後測試結果 | 判定／補強 |
|---|---|---|---|
| 妝容安全區像素 | 讓 makeup_layer_escapes 永遠回傳 false；另移除 WardrobeService.install 的驗證接線 | test_pixel_gate_blocks_layers_outside_the_safe_region 兩輪皆退出碼 1：DID NOT RAISE | 有效；同時守住判斷器與匯入接線 |
| 官方包保留 ID／不可移除 | 分別移除 install_outfit_pack 的保留 ID 分支、remove_outfit_pack 的官方 ID 分支 | test_official_packs_cannot_be_removed_or_shadowed 兩輪皆退出碼 1：DID NOT RAISE／錯誤訊息不符 | 有效 |
| 素體世代匯入與執行期 | 移除 manifest body-profile 比對；另移除 WardrobeService.apply 的 incompatible 阻擋 | test_wardrobe_body_profile_gate 兩輪皆退出碼 1：DID NOT RAISE／套件被當成可用 | 有效；匯入與執行期皆命中 |
| 行數棘輪 | application.presentation_ports 增加一行；另減少一行但不降低基線 | test_layered_facade_cycles 兩輪皆退出碼 1：1060 大於 1059；baseline 1059 大於 measured 1058 | 有效；只降不升兩面皆命中 |
| 四語文件平行 | 新增只有繁中的文件 | tools/check_four_language_docs.py 退出碼 1：缺少固定順序的四語區段 | 有效 |
| 發行資產 SHA-256 釘選 | 將受保護 idle_front.png 暫換成同尺寸、不同 SHA-256 的合法 PNG | test_inno_setup_and_artwork_contract 退出碼 1：實測 3f970a… 不等於 e99cc4… | 有效；還原後 SHA-256 與備份一致 |
| 工具權限 fail-closed | 移除未知權限字串回退分支 | test_unknown_permission_string_fails_closed 退出碼 1：create_file 回傳 bogus | 有效 |
| 風險分級與雙確認 | 將 script／scene 降為 home_control；另移除 RED 雙確認分支 | test_home_routine_risk_grading 與 test_flagship_safety 皆退出碼 1：home_control 不等於 home_routine／確認數不符 | 有效 |
| 緊急停止 | 讓無 plan_id 的 cancel 不設定任何事件 | test_cancel_without_an_identifier_still_stops_everything 退出碼 1：緊急停止未能停下全部計畫 | 有效 |
| 具名取消隔離 | 恢復未知 plan_id 會取消全部的舊行為 | test_cancelling_an_unknown_plan_leaves_running_plans_alone 退出碼 1：未知 ID 波及執行中計畫 | 有效；讀庫時納入的額外關鍵防護 |
| Gitleaks 自有閘門 | 把工作流程的 gitleaks detect 改成 echo | test_secret_defense_and_community_files 退出碼 1：找不到 gitleaks detect | 有效；證明工作流程接線，未假稱本機重跑完整歷史掃描 |
| v120 空層契約 | 將執行期 ornament 錯接到非空 face 圖層 | test_v120_empty_layers_physics.py 退出碼 1：cheek ornament 非全透明 | 有效；合法空層仍為 ornament、hair_left、hair_right、sleeve_left、sleeve_right |
| 二代素材 provenance | 將 BUILD-METADATA.json 的 source_authorization 改成 unconfirmed | 原 PoseAtlas／身份／release automation 測試退出碼 0；新增 test_pose_atlas_generation_provenance.py 後相同變異退出碼 1：unconfirmed 不等於已確認授權 | 紙糊；成因是既有程式與測試都未讀授權／再散布欄位；已補測授權、再散布、promotion、status、24 張實檔 SHA-256 |

正式素材盤點：v5-base 實測 76 個檔案（24 張 PNG），v5-base-layered 實測 603 個檔案（600 張 PNG）；全部 PNG 均為 1024×1536、RGBA。以各目錄內排序後串接「檔名|檔案 SHA-256」計算，聚合值分別為 9C0421262083ED6A2473EDE4CF05F4762FB749BD4B8670D6FEFB3AD399521B5F 與 2D5C6BF79FE18AE2D44F651E6CC192A651B8BB142710BFD61F297B1D980F934A。

主線同步為 fast-forward、無衝突。合併後最終閘門：ruff、Python 3.15 慣用法與四語稽核皆退出碼 0；`QT_QPA_PLATFORM=offscreen py -3.15 tests/run_all.py` 退出碼 0，384／384 模組通過，最後一行為 `ALL_384_TESTS_OK`。

## 简体中文

2026-09-04 在 test/gate-mutation-audit 分支逐轮执行“破坏、定向测试、记录、立即还原”。共审计 13 行防护；原有测试 12 行有效、1 行纸糊。每轮产品与资产变异还原后，工作树均回到该轮前状态。

| 防护 | 真实变异 | 变异后测试结果 | 判定／补强 |
|---|---|---|---|
| 妆容安全区像素 | 让 makeup_layer_escapes 永远返回 false；另移除 WardrobeService.install 的验证接线 | test_pixel_gate_blocks_layers_outside_the_safe_region 两轮均退出码 1：DID NOT RAISE | 有效；同时守住判断器与导入接线 |
| 官方包保留 ID／不可移除 | 分别移除 install_outfit_pack 的保留 ID 分支、remove_outfit_pack 的官方 ID 分支 | test_official_packs_cannot_be_removed_or_shadowed 两轮均退出码 1：DID NOT RAISE／错误信息不符 | 有效 |
| 素体世代导入与运行时 | 移除 manifest body-profile 比对；另移除 WardrobeService.apply 的 incompatible 阻挡 | test_wardrobe_body_profile_gate 两轮均退出码 1：DID NOT RAISE／套件被当成可用 | 有效；导入与运行时均命中 |
| 行数棘轮 | application.presentation_ports 增加一行；另减少一行但不降低基线 | test_layered_facade_cycles 两轮均退出码 1：1060 大于 1059；baseline 1059 大于 measured 1058 | 有效；只降不升两面均命中 |
| 四语文件平行 | 新增只有繁中的文件 | tools/check_four_language_docs.py 退出码 1：缺少固定顺序的四语区段 | 有效 |
| 发布资产 SHA-256 钉选 | 将受保护 idle_front.png 暂换成同尺寸、不同 SHA-256 的合法 PNG | test_inno_setup_and_artwork_contract 退出码 1：实测 3f970a… 不等于 e99cc4… | 有效；还原后 SHA-256 与备份一致 |
| 工具权限 fail-closed | 移除未知权限字符串回退分支 | test_unknown_permission_string_fails_closed 退出码 1：create_file 返回 bogus | 有效 |
| 风险分级与双确认 | 将 script／scene 降为 home_control；另移除 RED 双确认分支 | test_home_routine_risk_grading 与 test_flagship_safety 均退出码 1：home_control 不等于 home_routine／确认数不符 | 有效 |
| 紧急停止 | 让无 plan_id 的 cancel 不设置任何事件 | test_cancel_without_an_identifier_still_stops_everything 退出码 1：紧急停止未能停下全部计划 | 有效 |
| 具名取消隔离 | 恢复未知 plan_id 会取消全部的旧行为 | test_cancelling_an_unknown_plan_leaves_running_plans_alone 退出码 1：未知 ID 波及运行中计划 | 有效；读库时纳入的额外关键防护 |
| Gitleaks 自有闸门 | 把工作流的 gitleaks detect 改成 echo | test_secret_defense_and_community_files 退出码 1：找不到 gitleaks detect | 有效；证明工作流接线，未声称本机重跑完整历史扫描 |
| v120 空层契约 | 将运行时 ornament 错接到非空 face 图层 | test_v120_empty_layers_physics.py 退出码 1：cheek ornament 非全透明 | 有效；合法空层仍为 ornament、hair_left、hair_right、sleeve_left、sleeve_right |
| 二代素材 provenance | 将 BUILD-METADATA.json 的 source_authorization 改成 unconfirmed | 原 PoseAtlas／身份／release automation 测试退出码 0；新增 test_pose_atlas_generation_provenance.py 后相同变异退出码 1：unconfirmed 不等于已确认授权 | 纸糊；成因是既有程序与测试都未读授权／再散布字段；已补测授权、再散布、promotion、status、24 张实档 SHA-256 |

正式素材盘点：v5-base 实测 76 个文件（24 张 PNG），v5-base-layered 实测 603 个文件（600 张 PNG）；按各目录内排序后拼接“文件名|文件 SHA-256”计算，聚合值分别为 9C0421262083ED6A2473EDE4CF05F4762FB749BD4B8670D6FEFB3AD399521B5F 与 2D5C6BF79FE18AE2D44F651E6CC192A651B8BB142710BFD61F297B1D980F934A。

主线同步为 fast-forward、无冲突。合并后最终闸门：ruff、Python 3.15 惯用法与四语审计均退出码 0；`QT_QPA_PLATFORM=offscreen py -3.15 tests/run_all.py` 退出码 0，384／384 模块通过，最后一行为 `ALL_384_TESTS_OK`。

## English

On 2026-09-04, each round on branch test/gate-mutation-audit followed “break, run the focused test, record, restore immediately.” Thirteen guard rows were audited: 12 existing guards were effective and 1 was a paper guard. Every product or asset mutation returned the worktree to its pre-round state after restoration.

| Guard | Real mutation | Mutated test result | Verdict／addition |
|---|---|---|---|
| Makeup safe-region pixels | Forced makeup_layer_escapes to always return false; separately removed the validation wiring from WardrobeService.install | test_pixel_gate_blocks_layers_outside_the_safe_region exited 1 in both rounds: DID NOT RAISE | Effective; both validator and import wiring are covered |
| Official reserved ID／non-removability | Separately removed the reserved-ID branch from install_outfit_pack and the official-ID branch from remove_outfit_pack | test_official_packs_cannot_be_removed_or_shadowed exited 1 in both rounds: DID NOT RAISE／wrong error | Effective |
| Body generation at import and runtime | Removed manifest body-profile comparison; separately removed the incompatible block from WardrobeService.apply | test_wardrobe_body_profile_gate exited 1 in both rounds: DID NOT RAISE／pack treated as applicable | Effective; import and runtime both hit |
| Line-count ratchet | Added one line to application.presentation_ports; separately removed one line without lowering the baseline | test_layered_facade_cycles exited 1 in both rounds: 1060 exceeds 1059; baseline 1059 exceeds measured 1058 | Effective; both no-increase and ratchet-down sides hit |
| Four-language document parity | Added a Traditional-Chinese-only document | tools/check_four_language_docs.py exited 1: fixed-order four-language sections missing | Effective |
| Release asset SHA-256 pin | Replaced protected idle_front.png with a valid same-size PNG having a different SHA-256 | test_inno_setup_and_artwork_contract exited 1: measured 3f970a… differs from e99cc4… | Effective; restored SHA-256 matched the backup |
| Tool permission fail-closed | Removed fallback for unknown permission strings | test_unknown_permission_string_fails_closed exited 1: create_file returned bogus | Effective |
| Risk grading and double confirmation | Downgraded script／scene to home_control; separately removed the RED double-confirmation branch | test_home_routine_risk_grading and test_flagship_safety each exited 1: home_control differs from home_routine／confirmation count mismatch | Effective |
| Emergency stop | Made cancel without plan_id set no event | test_cancel_without_an_identifier_still_stops_everything exited 1: emergency stop did not stop all plans | Effective |
| Named-cancellation isolation | Restored the old behavior where an unknown plan_id cancels everything | test_cancelling_an_unknown_plan_leaves_running_plans_alone exited 1: unknown ID affected a running plan | Effective; additional critical guard found during repository review |
| Gitleaks owned gate | Replaced the workflow gitleaks detect command with echo | test_secret_defense_and_community_files exited 1: gitleaks detect missing | Effective; proves workflow wiring, not a claimed local full-history scan |
| v120 empty-layer contract | Miswired runtime ornament to the non-empty face layer | test_v120_empty_layers_physics.py exited 1: cheek ornament was not fully transparent | Effective; legal empty layers remain ornament, hair_left, hair_right, sleeve_left, sleeve_right |
| Generation-2 asset provenance | Changed source_authorization in BUILD-METADATA.json to unconfirmed | Existing PoseAtlas／identity／release automation tests exited 0; after adding test_pose_atlas_generation_provenance.py, the same mutation exited 1: unconfirmed differs from approved authorization | Paper guard; existing code and tests did not read authorization／redistribution fields; added checks for authorization, redistribution, promotion, status, and SHA-256 of all 24 files |

Formal asset inventory: v5-base contains 76 files (24 PNGs), and v5-base-layered contains 603 files (600 PNGs); every PNG measured 1024×1536 RGBA. Sorting each directory and joining `filename|file SHA-256` gives aggregate values 9C0421262083ED6A2473EDE4CF05F4762FB749BD4B8670D6FEFB3AD399521B5F and 2D5C6BF79FE18AE2D44F651E6CC192A651B8BB142710BFD61F297B1D980F934A respectively.

The main sync was a conflict-free fast-forward. After the merge, ruff, the Python 3.15 idiom audit, and the four-language audit all exited 0; `QT_QPA_PLATFORM=offscreen py -3.15 tests/run_all.py` exited 0, all 384／384 modules passed, and the final line was `ALL_384_TESTS_OK`.

## 日本語

2026-09-04、test/gate-mutation-audit ブランチで各ラウンドを「破壊、対象テスト、記録、即時復元」の順に実行しました。13 行の防護を監査し、既存テストは 12 行が有効、1 行が見せかけでした。製品・素材の各変異は復元後、作業ツリーがラウンド前の状態に戻りました。

| 防護 | 実変異 | 変異後のテスト結果 | 判定／追加 |
|---|---|---|---|
| メイク安全領域ピクセル | makeup_layer_escapes が常に false を返すよう変更し、別ラウンドで WardrobeService.install の検証接続を削除 | test_pixel_gate_blocks_layers_outside_the_safe_region は両ラウンドとも終了コード 1：DID NOT RAISE | 有効；検証器とインポート接続をともに防護 |
| 公式パック予約 ID／削除禁止 | install_outfit_pack の予約 ID 分岐と remove_outfit_pack の公式 ID 分岐を別々に削除 | test_official_packs_cannot_be_removed_or_shadowed は両ラウンドとも終了コード 1：DID NOT RAISE／誤ったエラー | 有効 |
| 素体世代のインポート／実行時 | manifest body-profile 比較を削除し、別ラウンドで WardrobeService.apply の incompatible 阻止を削除 | test_wardrobe_body_profile_gate は両ラウンドとも終了コード 1：DID NOT RAISE／パックが適用可能扱い | 有効；インポートと実行時をともに捕捉 |
| 行数ラチェット | application.presentation_ports に 1 行追加し、別ラウンドで基線を下げずに 1 行削減 | test_layered_facade_cycles は両ラウンドとも終了コード 1：1060 が 1059 超過；baseline 1059 が measured 1058 超過 | 有効；増加禁止と基線引下げをともに捕捉 |
| 四言語文書平行性 | 繁体字中国語だけの文書を追加 | tools/check_four_language_docs.py は終了コード 1：固定順序の四言語節が不足 | 有効 |
| リリース素材 SHA-256 固定 | 保護対象 idle_front.png を同サイズで異なる SHA-256 の正当な PNG に一時交換 | test_inno_setup_and_artwork_contract は終了コード 1：実測 3f970a… が e99cc4… と不一致 | 有効；復元後 SHA-256 はバックアップと一致 |
| ツール権限 fail-closed | 未知権限文字列のフォールバック分岐を削除 | test_unknown_permission_string_fails_closed は終了コード 1：create_file が bogus を返却 | 有効 |
| リスク分類と二重確認 | script／scene を home_control に降格し、別ラウンドで RED の二重確認分岐を削除 | test_home_routine_risk_grading と test_flagship_safety は各終了コード 1：home_control と home_routine が不一致／確認数不一致 | 有効 |
| 緊急停止 | plan_id なしの cancel がイベントを設定しないよう変更 | test_cancel_without_an_identifier_still_stops_everything は終了コード 1：全計画を停止できず | 有効 |
| 名前付き取消の分離 | 未知 plan_id が全取消になる旧挙動を復元 | test_cancelling_an_unknown_plan_leaves_running_plans_alone は終了コード 1：未知 ID が実行中計画へ波及 | 有効；リポジトリ調査で追加した重要防護 |
| Gitleaks 自有ゲート | ワークフローの gitleaks detect を echo に変更 | test_secret_defense_and_community_files は終了コード 1：gitleaks detect が不在 | 有効；ワークフロー接続の証明であり、ローカル全履歴走査の実行主張ではない |
| v120 空レイヤー契約 | 実行時 ornament を非空の face レイヤーへ誤接続 | test_v120_empty_layers_physics.py は終了コード 1：cheek ornament が完全透明でない | 有効；合法な空レイヤーは ornament、hair_left、hair_right、sleeve_left、sleeve_right のまま |
| 第二世代素材 provenance | BUILD-METADATA.json の source_authorization を unconfirmed に変更 | 既存 PoseAtlas／identity／release automation テストは終了コード 0；test_pose_atlas_generation_provenance.py 追加後、同じ変異は終了コード 1：unconfirmed が確認済み許諾と不一致 | 見せかけ；既存コードとテストが許諾／再配布欄位を未参照；許諾、再配布、promotion、status、24 実ファイルの SHA-256 検査を追加 |

正式素材の棚卸しでは、v5-base は 76 ファイル（PNG 24 枚）、v5-base-layered は 603 ファイル（PNG 600 枚）で、全 PNG は実測 1024×1536 RGBA です。各ディレクトリ内をソートし「ファイル名|ファイル SHA-256」を連結した集約値は、それぞれ 9C0421262083ED6A2473EDE4CF05F4762FB749BD4B8670D6FEFB3AD399521B5F と 2D5C6BF79FE18AE2D44F651E6CC192A651B8BB142710BFD61F297B1D980F934A です。

main との同期は衝突のない fast-forward でした。マージ後、ruff、Python 3.15 慣用法、四言語監査はいずれも終了コード 0、`QT_QPA_PLATFORM=offscreen py -3.15 tests/run_all.py` も終了コード 0 です。384／384 モジュールが通過し、最終行は `ALL_384_TESTS_OK` でした。
