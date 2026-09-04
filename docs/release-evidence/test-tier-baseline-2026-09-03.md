# 測試閘門分層基線／测试闸门分层基线／Test-tier baseline／テスト階層ベースライン

## 繁體中文

- 量測日期為 `2026-09-03`，基線提交為 `d58b11e`；以下數字是本工作樹在分層改動前的實測結果。
- 完整套使用 `py -3.15 tests/run_all.py`，退出碼為 0，結尾為 `ALL_364_TESTS_OK`，共 364 個測試模組，總耗時 1355.850 秒（22 分 35.850 秒）。
- 慢速模組沿用 `tests/run_all.py` 的 `_test_commands`、`_isolated_environment` 與 `_run_with_retry`，逐一在獨立子程序量測 wall-clock；沒有修改測試內容，也沒有啟用重試。
- 下列是同一批 68 個慢速候選模組的實測排序；數字是每個隔離子程序的實際耗時，不是 pytest 內部單一測試函式耗時。
- `tests/test_multisensory_speech_regression.py`：153.434 秒。
- `tests/test_state_fuzz.py`：67.095 秒。
- `tests/test_layered_face_calibration.py`：65.715 秒。
- `tests/test_expression_pipeline.py`：31.347 秒。
- `tests/test_full_ui_localization.py`：29.127 秒。
- `tests/test_build_half_body_layered_rig.py`：28.311 秒。
- `tests/test_post_speech_motion_performance.py`：23.226 秒。
- `tests/test_outfit_pack_makeup.py`：17.954 秒。
- `tests/test_ui_smoke.py`：17.530 秒。
- `tests/test_post_speech_motion_provider_matrix.py`：16.017 秒。
- 這 68 個候選模組逐一退出碼皆為 0，沒有重試；完整套則以 1355.850 秒作為固定成本基線。
- 分層完成後的 gate 以同一 runner 從第一個模組重跑 365 個模組，退出碼 0、結尾為 `ALL_365_TESTS_OK`，總耗時 1329.981 秒（22 分 09.981 秒）；無模組重試。
- 這次 gate 以模組內所有 runner 子命令的 wall-clock 合計排序，最慢十項為：`test_multisensory_speech_regression.py` 129.103 秒、`test_state_fuzz.py` 60.032 秒、`test_layered_face_calibration.py` 59.653 秒、`test_expression_pipeline.py` 29.592 秒、`test_build_half_body_layered_rig.py` 28.466 秒、`test_full_ui_localization.py` 25.603 秒、`test_layered_full_body.py` 25.335 秒、`test_post_speech_motion_performance.py` 19.897 秒、`test_realtime_mouth_completion.py` 18.162 秒、`test_flagship_physics.py` 16.887 秒。
- 本輪工作樹以 `python tests/run_all.py fast --changed-from main` 實測選出 26 個模組，退出碼 0、結尾為 `ALL_26_TESTS_OK`，耗時 78.004 秒。
- 同輪開工盤點確認 `assets/pose-atlas/v5-base/` 有 76 個檔案（24 個 PNG），`assets/pose-atlas/v5-base-layered/` 有 603 個檔案（600 個 PNG）；PNG 實測均為 1024×1536 RGBA，並逐檔量測 SHA-256。
- 以各目錄內相對路徑排序後串接「路徑|檔案 SHA-256」所得的全檔案盤點聚合 SHA-256 為：`v5-base=9c042126…521b5f`；`v5-base-layered=2d5c6bf7…0f934a`。
- 盤點依據包含 `assets/pose-atlas/v5-base/BUILD-METADATA.json`、`assets/pose-atlas/v5-base-layered/layer_manifest.json` 與實際檔案；本報告只記錄計數與基線，不改動正式素材。

## 简体中文

- 测量日期为 `2026-09-03`，基线提交为 `d58b11e`；以下数字是本工作树在分层改动前的实测结果。
- 完整套使用 `py -3.15 tests/run_all.py`，退出码为 0，结尾为 `ALL_364_TESTS_OK`，共 364 个测试模块，总耗时 1355.850 秒（22 分 35.850 秒）。
- 慢速模块沿用 `tests/run_all.py` 的 `_test_commands`、`_isolated_environment` 与 `_run_with_retry`，逐一在独立子进程测量 wall-clock；没有修改测试内容，也没有启用重试。
- 下列是同一批 68 个慢速候选模块的实测排序；数字是每个隔离子进程的实际耗时，不是 pytest 内部单个测试函数耗时。
- `tests/test_multisensory_speech_regression.py`：153.434 秒。
- `tests/test_state_fuzz.py`：67.095 秒。
- `tests/test_layered_face_calibration.py`：65.715 秒。
- `tests/test_expression_pipeline.py`：31.347 秒。
- `tests/test_full_ui_localization.py`：29.127 秒。
- `tests/test_build_half_body_layered_rig.py`：28.311 秒。
- `tests/test_post_speech_motion_performance.py`：23.226 秒。
- `tests/test_outfit_pack_makeup.py`：17.954 秒。
- `tests/test_ui_smoke.py`：17.530 秒。
- `tests/test_post_speech_motion_provider_matrix.py`：16.017 秒。
- 这 68 个候选模块逐一退出码皆为 0，没有重试；完整套则以 1355.850 秒作为固定成本基线。
- 分层完成后的 gate 使用同一个 runner 从第一个模块重跑 365 个模块，退出码 0、结尾为 `ALL_365_TESTS_OK`，总耗时 1329.981 秒（22 分 09.981 秒）；没有模块重试。
- 本次 gate 按每个模块全部 runner 子命令的 wall-clock 合计排序，最慢十项为：`test_multisensory_speech_regression.py` 129.103 秒、`test_state_fuzz.py` 60.032 秒、`test_layered_face_calibration.py` 59.653 秒、`test_expression_pipeline.py` 29.592 秒、`test_build_half_body_layered_rig.py` 28.466 秒、`test_full_ui_localization.py` 25.603 秒、`test_layered_full_body.py` 25.335 秒、`test_post_speech_motion_performance.py` 19.897 秒、`test_realtime_mouth_completion.py` 18.162 秒、`test_flagship_physics.py` 16.887 秒。
- 本轮工作树以 `python tests/run_all.py fast --changed-from main` 实测选出 26 个模块，退出码 0、结尾为 `ALL_26_TESTS_OK`，耗时 78.004 秒。
- 同轮开工盘点确认 `assets/pose-atlas/v5-base/` 有 76 个文件（24 个 PNG），`assets/pose-atlas/v5-base-layered/` 有 603 个文件（600 个 PNG）；PNG 实测均为 1024×1536 RGBA，并逐文件测量 SHA-256。
- 按各目录内相对路径排序后串接“路径|文件 SHA-256”所得的全文件盘点聚合 SHA-256 为：`v5-base=9c042126…521b5f`；`v5-base-layered=2d5c6bf7…0f934a`。
- 盘点依据包含 `assets/pose-atlas/v5-base/BUILD-METADATA.json`、`assets/pose-atlas/v5-base-layered/layer_manifest.json` 与实际文件；本报告只记录计数与基线，不改动正式素材。

## English

- The measurement date is `2026-09-03` and the baseline commit is `d58b11e`; the figures below were measured in this worktree before tiering changes.
- The complete suite used `py -3.15 tests/run_all.py`, exited 0, ended with `ALL_364_TESTS_OK`, covered 364 test modules, and took 1355.850 seconds (22 minutes 35.850 seconds).
- Slow-module timing reused `tests/run_all.py` through `_test_commands`, `_isolated_environment`, and `_run_with_retry`, measuring each module in an isolated child process with wall-clock timing; test contents were unchanged and retries were disabled.
- The following is the measured order for the same 68 slow-candidate modules; each value is the isolated child-process elapsed time, rather than an individual pytest function time.
- `tests/test_multisensory_speech_regression.py`: 153.434 seconds.
- `tests/test_state_fuzz.py`: 67.095 seconds.
- `tests/test_layered_face_calibration.py`: 65.715 seconds.
- `tests/test_expression_pipeline.py`: 31.347 seconds.
- `tests/test_full_ui_localization.py`: 29.127 seconds.
- `tests/test_build_half_body_layered_rig.py`: 28.311 seconds.
- `tests/test_post_speech_motion_performance.py`: 23.226 seconds.
- `tests/test_outfit_pack_makeup.py`: 17.954 seconds.
- `tests/test_ui_smoke.py`: 17.530 seconds.
- `tests/test_post_speech_motion_provider_matrix.py`: 16.017 seconds.
- All 68 candidate modules exited 0 individually without retries; 1355.850 seconds is the complete-suite fixed-cost baseline.
- After tiering, the gate reran all 365 modules from the first module through the same runner, exited 0, ended with `ALL_365_TESTS_OK`, and took 1329.981 seconds (22 minutes 09.981 seconds); no module was retried.
- This gate's slowest-ten ranking sums the wall-clock time of all runner subcommands belonging to each module: `test_multisensory_speech_regression.py` 129.103 seconds, `test_state_fuzz.py` 60.032 seconds, `test_layered_face_calibration.py` 59.653 seconds, `test_expression_pipeline.py` 29.592 seconds, `test_build_half_body_layered_rig.py` 28.466 seconds, `test_full_ui_localization.py` 25.603 seconds, `test_layered_full_body.py` 25.335 seconds, `test_post_speech_motion_performance.py` 19.897 seconds, `test_realtime_mouth_completion.py` 18.162 seconds, and `test_flagship_physics.py` 16.887 seconds.
- In this worktree, `python tests/run_all.py fast --changed-from main` selected 26 modules, exited 0, ended with `ALL_26_TESTS_OK`, and took 78.004 seconds.
- The same session's opening inventory found 76 files (24 PNGs) in `assets/pose-atlas/v5-base/` and 603 files (600 PNGs) in `assets/pose-atlas/v5-base-layered/`; every PNG measured 1024×1536 RGBA and each file received a SHA-256 measurement.
- The all-file inventory SHA-256, formed within each directory by sorting relative paths and joining `path|file SHA-256`, was `v5-base=9c042126…521b5f` and `v5-base-layered=2d5c6bf7…0f934a`.
- The inventory evidence includes `assets/pose-atlas/v5-base/BUILD-METADATA.json`, `assets/pose-atlas/v5-base-layered/layer_manifest.json`, and the physical files; this report records counts and baseline only and does not modify formal assets.

## 日本語

- 測定日は `2026-09-03`、ベースラインコミットは `d58b11e` です。以下は階層化変更前にこのワークツリーで実測した数値です。
- 完全スイートは `py -3.15 tests/run_all.py` で実行し、終了コード 0、末尾 `ALL_364_TESTS_OK`、364 テストモジュール、所要 1355.850 秒（22 分 35.850 秒）でした。
- 遅いモジュールの計測は `tests/run_all.py` の `_test_commands`、`_isolated_environment`、`_run_with_retry` を再利用し、各モジュールを独立した子プロセスで wall-clock 計測しました。テスト内容は変更せず、再試行は無効にしました。
- 以下は同じ 68 個の遅い候補モジュールの実測順です。数値は独立子プロセスの経過時間であり、pytest 内部の個別テスト関数の時間ではありません。
- `tests/test_multisensory_speech_regression.py`：153.434 秒。
- `tests/test_state_fuzz.py`：67.095 秒。
- `tests/test_layered_face_calibration.py`：65.715 秒。
- `tests/test_expression_pipeline.py`：31.347 秒。
- `tests/test_full_ui_localization.py`：29.127 秒。
- `tests/test_build_half_body_layered_rig.py`：28.311 秒。
- `tests/test_post_speech_motion_performance.py`：23.226 秒。
- `tests/test_outfit_pack_makeup.py`：17.954 秒。
- `tests/test_ui_smoke.py`：17.530 秒。
- `tests/test_post_speech_motion_provider_matrix.py`：16.017 秒。
- 68 個の候補モジュールはすべて個別に終了コード 0、再試行なしでした。完全スイートの固定コスト基線は 1355.850 秒です。
- 階層化後の gate は同じ runner で先頭から 365 モジュールを再実行し、終了コード 0、末尾 `ALL_365_TESTS_OK`、所要 1329.981 秒（22 分 09.981 秒）でした。モジュールの再試行はありません。
- 今回の gate の遅い上位十件は、各モジュールに属する runner サブコマンドの wall-clock を合計した順位です：`test_multisensory_speech_regression.py` 129.103 秒、`test_state_fuzz.py` 60.032 秒、`test_layered_face_calibration.py` 59.653 秒、`test_expression_pipeline.py` 29.592 秒、`test_build_half_body_layered_rig.py` 28.466 秒、`test_full_ui_localization.py` 25.603 秒、`test_layered_full_body.py` 25.335 秒、`test_post_speech_motion_performance.py` 19.897 秒、`test_realtime_mouth_completion.py` 18.162 秒、`test_flagship_physics.py` 16.887 秒です。
- このワークツリーでは `python tests/run_all.py fast --changed-from main` が 26 モジュールを選択し、終了コード 0、末尾 `ALL_26_TESTS_OK`、所要 78.004 秒でした。
- 同じセッションの開始時棚卸しでは `assets/pose-atlas/v5-base/` が 76 ファイル（PNG 24 個）、`assets/pose-atlas/v5-base-layered/` が 603 ファイル（PNG 600 個）でした。全 PNG は実測で 1024×1536 RGBA、各ファイルの SHA-256 も計測しました。
- 各ディレクトリ内の相対パス順に並べて `パス|ファイル SHA-256` を連結した全ファイル棚卸し SHA-256 は、`v5-base=9c042126…521b5f`、`v5-base-layered=2d5c6bf7…0f934a` です。
- 棚卸しの根拠は `assets/pose-atlas/v5-base/BUILD-METADATA.json`、`assets/pose-atlas/v5-base-layered/layer_manifest.json`、実ファイルです。本報告は個数と基線のみを記録し、正式素材は変更していません。
