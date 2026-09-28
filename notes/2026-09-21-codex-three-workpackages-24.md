# 三個工作包：目前成果與未通過項目

Session `codex-20260921-v5-closeout-three-24`；專案 `D:/FlamebladeStudio/CodexProjects/2026-09-02/mohan-front-layer-repair`。
本輪沿用 branch `integration/worktree-consolidation-20260916`、HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`。全部既有 dirty 工作保留；本輪末段 Git status 168 項。無 commit、PR、merge、軟體 release、publish 或 tag。

## 現況

1. 髮型／髮飾獨立切換仍未完成。已定位並正式修正 front-eureka 漏綁原生造型的錯誤；其餘六姿勢像素未改。新自創散髮未獲採用。
2. 24-view 聯合外觀矩陣未通過。已修復一個過期 blink source SHA；實際 1,488 張渲染中 100 項衣裝失敗，全部出現在 ±90°，另有其他角度可見接合偏差。
3. 現況文件與歷史任務分離，舊文件導向 `docs/v5-body-current-status.md`；未將 1、2 包的缺陷改寫成完成。

## 髮型來源及本輪判斷錯誤

Owner 先選擇「另做符合 V5 的散髮候選，給我看過再接入」。主代理誤解成可以另創髮型，產生 `scratchpad/mohan-v5-appearance-closeout-162/front-crossed.loose-hair-candidate-01.png`，1254×1254 RGBA，SHA-256 `d9d6d1593814c742565cb7f235ca5540531896d1cecdf17aac0ac25afc3df102`。

Owner 回覆：「我從來沒看過墨寒有這個髮型，你是自創的？」已保存 `hair-candidate-owner-response-01.json`，`owner_appearance_approved=false`。該候選沒有抽取、沒有安裝，不可用作墨寒既有造型或原生臉依據。生成器亦改算了臉部；先前量測 ROI 平均 RGB 差 30.7379，僅作拒絕混用的佐證，不是人臉品質分數。

其後核對到已採用的 `scratchpad/mohan-canonical-eureka-hanfu-104/eureka-hanfu.source.png`：SHA-256 `dfb3fe60f1318bd888c59bbc9e0a221a60d3e30f4c1498b82d1fa87e7ff5fffe`。其 `owner-approval.json` SHA-256 `634f28b8a3a1ee8f4af52217c4ede6dd02dabd1f59d69bc0d680c7ebb7b5e7c8`，採用原圖為 V5 髮髻，沒有被錯誤疊上的舊散髮／銀髮飾。

正式 reviewed-garments manifest 的 front-eureka 原先 `native_appearance_selections={}`；另外六姿勢有原生造型 alias。此次僅補上缺少的兩個選擇綁定，恢復已採用原圖的原生髮髻。未修改任何正式 PNG、renderer 或使用者衣櫃。原生去背既有髮際／頸側灰邊仍可見，本次沒有清理，也未宣稱所有 alpha 外觀完美。

## 正式安裝（兩個中繼資料目標）

| 目標 | 安裝前 SHA-256 | 安裝後 SHA-256 |
| --- | --- | --- |
| `assets/pose-atlas/v5-base/yaw+000-pitch+00.blink-binding.json` | `4cc908c27efb3b13fd09293d280761f108ae40de7cf353345f2facce6040df68` | `8e4e15ff35bab76b8a4f4ae70a162e0d72312c376d7ffaf04c6ff49b9637f1e1` |
| `assets/expressions/reviewed-garments/manifest.json` | `95d5e3377265d97ab31f94a02edaff23de4a61494cec021b4c4d0b5d4b4dad93` | `fbd77443f37924f7be269b000993b192db2974a8138f37b7261877af7635e512` |

全部使用 `tools/art_pipeline/approved_asset_install.py` 的 SHA 預檢、原子替換、備份與 receipt；兩次各 1 個目標，退出碼均 0。前一個 blink 綁定來源全 RGB 與原 pin 的 Git blob 相同，僅既有 alpha 不同；本輪保留現有 PNG，經 72 張嚴格候選與預設正式 renderer 逐像素相同後重綁。預設 renderer 沒有啟用 explicit-authority 嚴格檢查，不能把首次嚴格模式失敗說成預設 App 啟動失敗。

`W` 以下代表 `scratchpad/mohan-v5-appearance-closeout-162/`：

| 證據 | SHA-256 |
| --- | --- |
| `W/blink-repin-installation-05/receipt.json` | `7abda774e9628b2859bb074036a75fe38180ac5fd9ef3a79c9b555d755dd7d8e` |
| `W/native-eureka-installation-08/receipt.json` | `d6cf42b63f6cc0fe02d5b7a012989c33ae2c5aab3c77b2c6202339e24b6bd485` |
| `W/native-eureka-formal-09/validation.json` | `d116c2017a3815f77f3f57b9a9a220db9bf0d1e8d5e4c11d85f1b386bdac32d0` |
| `W/fullbody-matrix-06/validation.json` | `52185f91d2fd14b6c1b9505a4895fe26fdc3cd197971e906ee85bedebf8c407c` |
| `W/profile-categories-10/validation.json` | `0f6bd3399a72029901278e6d3d071890ffdcd9e7305a0741c4ad6a1c884a4900` |

兩個安裝目錄各有 `plan.json`、`receipt.json` 及 `backup/assets/...` 原檔。receipt 不涵蓋未列入計畫的檔案。

## 實際執行與驗證

Python 命令均用專案 `.venv315/Scripts/python.exe`。以下 `W` 依上節展開；不表示命令列存在名為 W 的環境變數。

| 命令／實際 API | 退出碼與結果 |
| --- | --- |
| `python W/audit_halfbody.py halfbody-switch-01` | 0；35 張診斷，7/7 還原相同。舊髮型套用有可見疊影，不算外觀通過 |
| `python W/audit_fullbody.py fullbody-smoke-01` | 1；首次 explicit-authority source pin 不相符 |
| `python W/audit_blink_bindings.py` | 1；早期保守的「眨眼區不得有來源像素差」檢查。其後確認只有來源 alpha 變動，未把此失敗改寫成成功 |
| `python W/audit_fullbody.py fullbody-smoke-02` | 0；96 張機械輸出。當時沒有 fail-closed fallback 斷言，不能當作完整衣裝驗收 |
| `python W/diagnose_profile_fallback.py` | 0；記錄 ±90° `Runtime garment overlaps protected identity` |
| `python W/repair_blink_binding.py` | 0；72 張新舊逐像素相同，預檢 1 目標通過 |
| `approved_asset_install.install(ROOT, W/blink-repin-staging-04/install.plan.json, W/blink-repin-installation-05)` | 0；1 目標已安裝，收據與備份存在 |
| `python W/audit_fullbody.py fullbody-matrix-06 --matrix --strict` | 1；1,488 張，mechanical_errors=0，appearance_failures=100，24/24 還原相同 |
| `python W/restore_eureka_native.py` | 0；336 張候選＋336 張前正式基線；六姿勢全像素不變；eureka 無妝 12 態頭部前 500 列與原生 V7 runtime 相同；預檢 1 目標通過 |
| `python W/restore_eureka_native.py --install` | 0；1 目標已安裝 |
| `python W/verify_eureka_formal.py` | 0；正式重新載入 336 張，與 staging 差異 0，失敗 0 |
| `python W/diagnose_profile_categories.py` | 0；診斷成功記錄五個不合格圖層，並非衣裝通過 |
| `python -m pytest tests/test_full_body_blink_source_binding.py tests/test_full_body_authored_blink.py tests/test_full_body_authority_source.py -q --basetemp D:/FlamebladeStudio/CodexProjects/.qa/mohan-three-packs-24-bindings` | 0；48 passed |
| `python -m pytest tests/test_reviewed_garment_assets.py tests/test_reviewed_garment_overlay.py -q --basetemp D:/FlamebladeStudio/CodexProjects/.qa/mohan-three-packs-24-native` | 0；21 passed |
| `python -m ruff check .` | 0；全專案通過 |
| `python tools/check_four_language_docs.py` | 0；Git 已追蹤文件通過。新未追蹤現況頁另用 audit_document 檢查 |

文件 checker 單元測試先前 7 passed，但不等於實際文件合格。首次直接稽核新現況頁 exit 1（四語段落／表格／inline code 不對稱）；補齊後，三份變更文件各自 `audit_document(Path(name))` 回傳空錯誤清單，合併命令 exit 0。此直接稽核包含尚未加入 Git 的新現況頁。

一般 `git diff --check` 曾因既有資產 JSON 的 CRLF 尾端判定 exit 1；沒有正規化需保留 SHA 的素材。`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check` exit 0，保留其他空白檢查；最終再核對結果記於交接筆記。

## 全身失敗的具體定位

官方 archive SHA-256 `529b96a8d487370493d6aaf88dfae01fd76abe8d99aa0868c32700bf652f60ba`，本輪未改。以目前正式身份保護區測得：

| 視角 | archive 圖層 | 侵入像素數 |
| --- | --- | --- |
| −90° | `hanfu-robe-blue-white-yaw-090-pitch+00-outerwear.png` | 85 |
| −90° | `loose-hair-ink-black-yaw-090-pitch+00-front.png` | 1 |
| +90° | `hanfu-robe-blue-white-yaw+090-pitch+00-outerwear.png` | 70 |
| +90° | `loose-hair-ink-black-yaw+090-pitch+00-front.png` | 37 |
| +90° | `silver-hairpiece-silver-yaw+090-pitch+00-headwear.png` | 20 |

完整 member SHA、位置與 protected-face 路徑在 `profile-categories-10/validation.json`。計數為 Qt 的 alpha mask 與禁入區交集，不能推論只有這些像素有外觀問題。肉眼亦看見 +075° 舊黑背心露出、+135°／+150° 衣裝與身體接合不符等問題；不能只裁掉臉部碰撞就宣布 24 角度完成。

## 下一步界線

- 髮型以墨寒既有已採用參考為準。原生 V5 髮髻已有來源證據；獨立散髮需先鎖定既有造型依據，再依原生臉／身體對齊。不得重用本輪自創候選作為既有設計。
- 全身保留嚴格身份保護；修復來源對齊後重跑失敗角度及其影響範圍，完整聯合矩陣通過以前保持開放。不能調弱遮罩驗證或拿未穿衣的 fallback 算成功。
- 目前沒有人工操作桌面 App 的驗收；本輪使用正式 Qt renderer 的 offscreen 實際合成、局部逐像素比對和主代理看圖。
- 來源血緣 22＋2 的已完成成果、七姿勢 V7、三款妝容及七姿勢漢服保持；舊的成功矩陣只對舊輸入有效，本輪 manifest 修正用新的 336 張正式核對收據。

## 助理與交接

依 local-ai skill，本機 Qwen3.8-27B 對 `reviewed_garment_overlay.py` 與測試作唯讀審查，272 tokens / 19.1 秒 / 14.3 tokens/s，exit 0。主代理用正式素材獨立重現，並負責所有來源判定、圖像作業、正式寫入與驗證。四語翻譯另由同一模型起草，2740 tokens / 94.6 秒 / 29.0 tokens/s，exit 0；主代理修正英日文用詞及語意後整合。沒有把 smoke 測試當作外部 DeepSeek 已接觸專案資料的證據。

起點 revision 150／`d11e3198de802792b789fbcfa32ef4b2592f2c9786d8daa93b9b2ee5cb2a9e15` 已按 status → verify → claim。中途 checkpoint revision 151／`ec7394114038e73b988a462344aa3d3f7b69be473a5d8490900943af05d85cda`。收尾依同一 session 更新 CURRENT_STATUS、TASKS、extra 清單，再 checkpoint、release、唯讀 verify。checkpoint 與 verify 是列入範圍的內容校驗，不是全盤備份或美術採用。
