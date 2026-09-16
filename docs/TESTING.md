# 墨寒 v4 測試策略／墨寒 v4 测试策略／MoHan v4 Testing Strategy／墨寒 v4 テスト戦略

## 繁體中文

### 執行策略

- `tests/run_all.py` 動態發現完整的 `test_*.py` 測試套件、依檔名排序，並將每個測試檔隔離在獨立 Python 子程序中執行。這可避免 `QCoreApplication` 與 `QApplication` 在同一程序內反覆建立及原生清理時互相干擾。
- 隔離程序會完整呈現失敗：任何測試檔回傳非零狀態時，總測試立即失敗並保留該檔名與狀態碼。
- 自動化測試、Windows EXE 真機驗收、封裝與發布是不同門檻；每次通過只完成對應門檻，其餘門檻維持自身狀態。
- 測試閘門分三層，仍由同一個 `tests/run_all.py` 執行：開發中每次改動用 `fast`（`python tests/run_all.py fast`），依 `tests/impact_map.json` 選取受影響測試並保留契約測試；提交前用 `gate`（`python tests/run_all.py gate`，也是預設完整套）；排程或隔夜，以及需要集中檢查封裝／跨平台／長時間資產、語音、UI 項目時用 `nightly`（`python tests/run_all.py nightly`）。
- `fast --changed-from <git-ref>`（例如 `python tests/run_all.py fast --changed-from main`）會納入指定 ref 之後的提交及目前工作樹、暫存區、未追蹤檔案。
- 若 `fast` 的檔案對照、Git ref 或 impact map 處於不可用狀態，會安全退回完整套並印出 `FAST_FALLBACK_TO_GATE`；`gate` 保留結尾 `ALL_..._TESTS_OK`，不帶參數仍等同 `gate`。

### 完整回歸暫時狀態

- 2026-09-04 的 gate 已從第一個模組重新執行 365 個測試模組，退出碼為 0，結尾為 `ALL_365_TESTS_OK`，總耗時 1329.981 秒（22 分 09.981 秒）。
- 本次完整 gate 的模組重試數為 0；分層前的 364 模組基線、分層後的 gate 與最慢十項實測，均記錄於 `docs/release-evidence/test-tier-baseline-2026-09-03.md`。
- 歷史註記：更早一次未完成的完整回歸曾在第 66 支測試遇到四語契約失敗；該歷史結果與本次已通過的 gate 分別保留。
- `app.py` 現已縮減為 13 個實體行，內容限定為薄型 composition root；這項成果完成架構門檻，完整回歸、封裝與發布仍各自依對應門檻判定。

### 目前待完成的發布先決條件

- Python 3.15／Qt 的正式發布條件仍待完成：目前固定的 PySide6 6.11.1 官方 metadata 排除 Python 3.15。Qt 官方提供完整且一致的 Python 3.15 相容套件，並在乾淨環境通過標準 resolver 驗證後，即具備解除條件。
- PoseAtlas 的正式發布條件仍待完成：具可驗證來源與再散布權的 24 個完整全身旋轉視角、landmarks、hands 與真實 `release-audits.json` 仍在齊備中。
- 完整回歸 gate 已通過；v4 的可發布與已發布狀態，會在上述其他先決條件全數完成後成立。

### 已自動通過

以下列出已具備的對應自動化證據；v4 的其餘發布門檻各自保留獨立狀態：

- OpenCV 真模型載入契約、模型檔完整性，以及空白影格、缺少模型或分析失敗時的安全回退。
- Windows、OpenAI、Realtime、Azure 與 Dragon HD 共用的語音生命週期、供應器中立路由、完成／中斷與回退契約；每一項外部服務的即時帳號與裝置驗收仍是獨立門檻。
- 一般攜帶檔維持非敏感資料範圍；敏感內容須明確勾選並以強密碼加密；錯誤密碼或驗證失敗時保留目前設定的契約。
- 繁體中文、簡體中文、英文、日文的鍵值、順序、預留欄位、UTF-8 與亂碼檢查。
- 視覺模型的來源、雜湊、大小、SBOM／NOTICE 登錄與竄改偵測契約。
- 視覺、攝影機或模型停用／不可用時，相關新能力進入安全停用狀態並保留既有功能的回退契約。

### 仍需 Windows EXE 與真 Webcam 驗收

- 真攝影機列舉、權限、啟停、拔除重接、鏡像座標、不同光線，以及身分、物品、八個內建手勢與噓聲融合的誤觸發／漏判。
- Windows、OpenAI、Realtime、Azure、Dragon HD 在實際帳號、區域、裝置與網路條件下的聲音輸出、切換、失敗回退及嘴型同步。
- 安裝後實際匯出與匯入一般／敏感攜帶檔，確認取消、錯誤密碼、檔案遭修改及攝影機保持關閉等結果。
- 在視覺停用、Webcam 或模型待備、外部服務失敗時，驗證聊天、語音、2.5D 角色、設定與其他既有功能仍可正常使用。

### 封裝與發布工作待完成

- v4 的 Windows EXE／安裝包封裝、既有安裝覆蓋升級、捷徑與工具列圖示、解除安裝／回復及安裝包內容稽核仍處於待完成狀態。
- 正式安裝包仍須核對模型、授權、SBOM、NOTICE、雜湊與發布資產一致性。
- 本文件的聲明範圍是目前測試證據；v4 封裝、發布與完整發布門檻狀態仍待相應證據成立。

## 简体中文

### 执行策略

- `tests/run_all.py` 动态发现完整的 `test_*.py` 测试套件、按文件名排序，并将每个测试文件隔离在独立 Python 子进程中执行。这样可避免 `QCoreApplication` 与 `QApplication` 在同一进程内反复创建及原生清理时互相干扰。
- 进程隔离会完整呈现失败：任何测试文件返回非零状态时，总测试立即失败，并保留该文件名与状态码。
- 自动化测试、Windows EXE 真机验收、打包与发布是不同关卡；每次通过只完成对应关卡，其余关卡维持自身状态。
- 测试关卡分三层，仍由同一个 `tests/run_all.py` 执行：开发中每次改动用 `fast`（`python tests/run_all.py fast`），依据 `tests/impact_map.json` 选择受影响测试并保留契约测试；提交前用 `gate`（`python tests/run_all.py gate`，也是默认完整套）；排程或隔夜，以及需要集中检查打包／跨平台／长时间资产、语音、UI 项目时用 `nightly`（`python tests/run_all.py nightly`）。
- `fast --changed-from <git-ref>`（例如 `python tests/run_all.py fast --changed-from main`）会纳入指定 ref 之后的提交以及当前工作树、暂存区、未跟踪文件。
- 如果 `fast` 的文件对应关系、Git ref 或 impact map 处于不可用状态，会安全退回完整套并打印 `FAST_FALLBACK_TO_GATE`；`gate` 保留结尾 `ALL_..._TESTS_OK`，不带参数仍等同 `gate`。

### 完整回归暂时状态

- 2026-09-04 的 gate 已从第一个模块重新执行 365 个测试模块，退出码为 0，结尾为 `ALL_365_TESTS_OK`，总耗时 1329.981 秒（22 分 09.981 秒）。
- 本次完整 gate 的模块重试数为 0；分层前的 364 模块基线、分层后的 gate 与最慢十项实测，均记录于 `docs/release-evidence/test-tier-baseline-2026-09-03.md`。
- 历史注记：更早一次未完成的完整回归曾在第 66 个测试遇到四语契约失败；该历史结果与本次已经通过的 gate 分别保留。
- `app.py` 现已缩减为 13 个物理行，内容限定为轻量 composition root；该成果完成架构关卡，完整回归、打包与发布仍各自按对应关卡判定。

### 当前待完成的发布先决条件

- Python 3.15／Qt 的正式发布条件仍待完成：当前固定的 PySide6 6.11.1 官方 metadata 排除 Python 3.15。Qt 官方提供完整且一致的 Python 3.15 兼容软件包，并在干净环境中通过标准 resolver 验证后，即具备解除条件。
- PoseAtlas 的正式发布条件仍待完成：具有可验证来源与再分发权的 24 个完整全身旋转视角、landmarks、hands 与真实 `release-audits.json` 仍在齐备中。
- 完整回归 gate 已通过；v4 的可发布与已发布状态，会在上述其他先决条件全部完成后成立。

### 已自动通过

以下列出已具备的对应自动化证据；v4 的其余发布关卡各自保留独立状态：

- OpenCV 真模型加载契约、模型文件完整性，以及空白帧、缺少模型或分析失败时的安全回退。
- Windows、OpenAI、Realtime、Azure 与 Dragon HD 共用的语音生命周期、供应商中立路由、完成／中断与回退契约；每一项外部服务的实时账号与设备验收仍是独立关卡。
- 普通可移植文件维持非敏感数据范围；敏感内容须明确勾选并以强密码加密；错误密码或验证失败时保留当前设置的契约。
- 繁体中文、简体中文、英文、日文的键值、顺序、占位符、UTF-8 与乱码检查。
- 视觉模型的来源、哈希、大小、SBOM／NOTICE 登记与篡改检测契约。
- 视觉、摄像头或模型停用／不可用时，相关新能力进入安全停用状态并保留现有功能的回退契约。

### 仍需 Windows EXE 与真 Webcam 验收

- 真摄像头枚举、权限、启停、拔除重连、镜像坐标、不同光线、长期稳定性，以及身份、物品、八个内置手势与嘘声融合的误触发／漏判。
- Windows、OpenAI、Realtime、Azure、Dragon HD 在实际账号、区域、设备与网络条件下的声音输出、切换、失败回退及嘴型同步。
- 安装后实际导出与导入普通／敏感可移植文件，确认取消、错误密码、文件被修改及摄像头保持关闭等结果。
- 在视觉停用、Webcam 或模型待备、外部服务失败时，验证聊天、语音、2.5D 角色、设置与其他现有功能仍可正常使用。

### 打包与发布工作待完成

- v4 的 Windows EXE／安装包打包、现有安装覆盖升级、快捷方式与任务栏图标、卸载／恢复及安装包内容审计仍处于待完成状态。
- 正式安装包仍须核对模型、许可证、SBOM、NOTICE、哈希与发布资产的一致性。
- 本文件的声明范围是当前测试证据；v4 打包、发布与完整发布关卡状态仍待相应证据成立。

## English

### Execution strategy

- `tests/run_all.py` dynamically discovers the complete `test_*.py` test suite, sorts it by file name, and runs each test file in an isolated Python child process. This prevents native teardown interference when `QCoreApplication` and `QApplication` would otherwise be created and destroyed repeatedly in one process.
- Process isolation surfaces failures completely: a non-zero result from any test file immediately fails the aggregate run and preserves the file name and exit code.
- Automated tests, real-device acceptance in the Windows EXE, packaging, and release are separate gates. Each pass completes its corresponding gate, while the other gates retain their own status.
- The test runner has three tiers and remains the single `tests/run_all.py` entry point: use `fast` (`python tests/run_all.py fast`) for each development change, selecting affected tests through `tests/impact_map.json` while retaining contract tests; use `gate` (`python tests/run_all.py gate`, also the default) before submission for the complete suite; use `nightly` (`python tests/run_all.py nightly`) on a schedule or overnight for packaging smoke, cross-platform, and long-running asset/speech/UI checks.
- `fast --changed-from <git-ref>` (for example, `python tests/run_all.py fast --changed-from main`) includes commits after the selected ref plus current worktree, index, and untracked files.
- When the changed-file mapping, Git ref, or impact map is unavailable to `fast`, it safely falls back to the complete suite and prints `FAST_FALLBACK_TO_GATE`; `gate` retains the ending `ALL_..._TESTS_OK`, and an omitted argument still selects `gate`.

### Temporary complete-regression status

- On 2026-09-04, the gate reran all 365 test modules from the first module, exited 0, ended with `ALL_365_TESTS_OK`, and took 1329.981 seconds (22 minutes 09.981 seconds).
- The module retry count for this complete gate was 0; the pre-tier 364-module baseline, post-tier gate, and measured slowest ten are recorded in `docs/release-evidence/test-tier-baseline-2026-09-03.md`.
- Historical note: an earlier incomplete full run encountered the four-language contract failure at test file 66; that historical result and the now-passing gate remain separately recorded.
- `app.py` is now reduced to 13 physical lines, with its content limited to the thin composition root. This result completes the architecture gate; full regression, packaging, and release remain governed by their respective gates.

### Current release prerequisites awaiting completion

- The Python 3.15／Qt formal-release prerequisite remains pending: the currently pinned official PySide6 6.11.1 metadata excludes Python 3.15. The prerequisite becomes clearable after Qt publishes a complete, consistent Python 3.15-compatible set and the standard resolver verifies it in clean environments.
- The PoseAtlas formal-release prerequisite remains pending: the 24 complete full-body rotational views with verifiable provenance and redistribution rights, their landmarks and hands, and genuine `release-audits.json` remain in preparation.
- The complete regression gate now passes; v4 gains releasable and released status after the remaining prerequisites are complete.

### Automated evidence currently passed

The following lists the corresponding automated evidence already established; all remaining v4 release gates retain their independent status:

- Real OpenCV model-loading contracts, model-file integrity, and safe fallback for blank frames, missing models, or analysis failures.
- Provider-neutral speech lifecycle, routing, completion/interruption, and fallback contracts shared by Windows, OpenAI, Realtime, Azure, and Dragon HD. Live account and device acceptance for each external service remains a separate gate.
- Contracts that keep ordinary portable profiles within the non-sensitive data scope, require explicit selection and strong-password encryption for sensitive content, and preserve current settings after a wrong password or validation failure.
- Key, ordering, placeholder, UTF-8, and corruption checks for Traditional Chinese, Simplified Chinese, English, and Japanese.
- Vision-model source, hash, size, SBOM/NOTICE registration, and tamper-detection contracts.
- Fallback contracts that place the affected new capability in a safe-disabled state when vision, the camera, or a model is disabled or unavailable, while preserving established features.

### Still requires Windows EXE and real-webcam acceptance

- Real-camera enumeration, permission handling, enable/disable, unplug/reconnect, mirrored coordinates, varied lighting, and false-positive/missed-detection checks for identity, objects, all eight built-in gestures, and silence-request fusion.
- Speech output, switching, failure fallback, and lip synchronization for Windows, OpenAI, Realtime, Azure, and Dragon HD under real accounts, regions, devices, and network conditions.
- Real export and import of ordinary and sensitive portable profiles from an installed build, including cancellation, wrong-password, modified-file, and camera-remains-off outcomes.
- With vision disabled, a webcam or model pending, or failed external services, verification that chat, speech, the 2.5D character, settings, and other established features remain usable.

### Packaging and release work awaiting completion

- The v4 Windows EXE/installer, in-place upgrade over an existing installation, shortcut and taskbar icons, uninstall/recovery, and package-content audit remain pending.
- A final installer must still be checked for consistency among models, licenses, SBOM, NOTICE, hashes, and release assets.
- This document's claim scope is the current testing evidence; v4 packaging, release, and complete release-gate status await their corresponding evidence.

## 日本語

### 実行方針

- `tests/run_all.py` は完全な `test_*.py` テストスイートを動的に検出してファイル名順に並べ、各テストファイルを独立した Python 子プロセスで隔離実行します。これにより、同一プロセス内で `QCoreApplication` と `QApplication` を繰り返し生成、ネイティブ終了処理する際の干渉を防ぎます。
- プロセス分離は失敗を完全に表示します。いずれかのテストファイルがゼロ以外を返した時点で全体を失敗とし、ファイル名と終了コードを保持します。
- 自動テスト、Windows EXE での実機受入試験、パッケージ化、公開は別々のゲートです。各通過は対応するゲートを完了し、その他のゲートはそれぞれの状態を維持します。
- テストランナーには三つの階層があり、入口は引き続き単一の `tests/run_all.py` です。開発中の各変更には `fast`（`python tests/run_all.py fast`）を使い、`tests/impact_map.json` から影響テストを選び、契約テストを残します。提出前には `gate`（`python tests/run_all.py gate`、既定値でもあります）で完全スイートを実行し、スケジュールまたは夜間には `nightly`（`python tests/run_all.py nightly`）でパッケージ化スモーク、クロスプラットフォーム、長時間の資産／音声／UI テストを集約します。
- `fast --changed-from <git-ref>`（例：`python tests/run_all.py fast --changed-from main`）は指定 ref より後のコミットと、現在のワークツリー、インデックス、未追跡ファイルを含めます。
- 変更ファイルの対応付け、Git ref、または impact map が `fast` から利用できない場合は、安全に完全スイートへ戻り `FAST_FALLBACK_TO_GATE` を表示します。`gate` の末尾 `ALL_..._TESTS_OK` は維持され、引数を省略した場合も `gate` を選択します。

### 完全回帰の暫定状況

- 2026-09-04 の gate は先頭から 365 テストモジュールを再実行し、終了コード 0、末尾 `ALL_365_TESTS_OK`、所要 1329.981 秒（22 分 09.981 秒）でした。
- 今回の完全 gate のモジュール再試行数は 0 です。階層化前の 364 モジュール基線、階層化後の gate、実測した遅い上位十件は `docs/release-evidence/test-tier-baseline-2026-09-03.md` に記録しています。
- 履歴注記：以前の未完了な完全回帰では 66 番目のテストファイルで四言語契約が失敗しました。この過去の結果と現在合格している gate は、個別に記録します。
- `app.py` は現在 13 物理行まで縮小され、内容を薄い composition root に限定しています。この成果でアーキテクチャゲートを完了し、完全回帰、パッケージ化、公開はそれぞれのゲートで判定します。

### 現在完了待ちの公開前提条件

- Python 3.15／Qt の正式公開条件は完了待ちです。現在固定している公式 PySide6 6.11.1 metadata は Python 3.15 を除外しています。Qt が完全で整合した Python 3.15 対応一式を公開し、新規環境の標準 resolver で検証を終えた後に解除条件が成立します。
- PoseAtlas の正式公開条件は完了待ちです。出典と再配布権を検証できる完全全身回転 24 視角、landmarks、hands、真正な `release-audits.json` は現在準備中です。
- 完全回帰 gate は合格しました。残る前提条件をすべて完了した後、v4 の公開可能・公開済み状態が成立します。

### 通過済みの自動化証拠

以下は確立済みの自動化証拠を示します。v4 の残る公開ゲートは、それぞれ独立した状態を維持します。

- OpenCV 実モデルの読み込み契約、モデルファイルの完全性、空白フレーム、モデル欠落、解析失敗時の安全なフォールバック。
- Windows、OpenAI、Realtime、Azure、Dragon HD で共有する、プロバイダー非依存の音声ライフサイクル、経路選択、完了／中断、フォールバック契約。各外部サービスの実アカウントと実機による受入試験は別のゲートとして残ります。
- 通常の可搬プロファイルを非機密データ範囲に保ち、機密内容には明示的な選択と強力なパスワード暗号化を求め、誤ったパスワードや検証失敗時には現在の設定を維持する契約。
- 繁体字中国語、簡体字中国語、英語、日本語のキー、順序、プレースホルダー、UTF-8、文字化け検査。
- 視覚モデルの出所、ハッシュ、サイズ、SBOM／NOTICE 登録、改ざん検出の契約。
- 視覚、カメラ、モデルが無効または利用不能な場合、該当する新機能を安全停止状態にし、既存機能を維持するフォールバック契約。

### Windows EXE と実 Webcam で必要な受入試験

- 実カメラの列挙、権限、有効化／無効化、抜き差し後の再接続、鏡像座標、異なる照明、および本人、物体、八つの内蔵ジェスチャー、静音要求融合の誤検出／見落とし。
- 実際のアカウント、リージョン、機器、ネットワーク条件における Windows、OpenAI、Realtime、Azure、Dragon HD の音声出力、切り替え、失敗時フォールバック、口形同期。
- インストール済み環境で通常／機密可搬プロファイルを実際に書き出し、読み込み、取消、誤パスワード、改ざんファイル、カメラが無効のままであることを確認する試験。
- 視覚無効、Webcam またはモデルの準備中、外部サービス失敗時にも、会話、音声、2.5D キャラクター、設定、その他の既存機能が利用できることの確認。

### パッケージ化・公開作業の完了待ち

- v4 の Windows EXE／インストーラー作成、既存環境への上書き更新、ショートカットとタスクバーアイコン、アンインストール／復旧、パッケージ内容監査は完了待ちです。
- 正式インストーラーでは、モデル、ライセンス、SBOM、NOTICE、ハッシュ、公開資産の一致を引き続き確認する必要があります。
- 本文書の表明範囲は現在のテスト証拠です。v4 のパッケージ化、公開、すべての公開ゲート通過状態は、対応する証拠の確立を待ちます。
