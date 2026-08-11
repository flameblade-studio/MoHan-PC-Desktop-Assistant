# 可插拔語音供應器／可插拔语音供应器／Pluggable Speech Providers／交換可能な音声プロバイダー

## 繁體中文

`v2.1.0-rc.1` 建立語音供應器的穩定邊界。Windows 本機女聲、OpenAI 文字語音與
Azure Speech 預覽透過同一個登錄層接入，嘴型、音量、播放完成訊號與表情狀態仍由
既有單一權威流程管理。

資料庫只保存不受翻譯影響的穩定代號；舊版繁中、簡中與英文名稱會自動遷移。
Realtime 離線、雲端失敗、金鑰缺漏或未知供應器都優先回到使用者選定的 Windows
女性本機語音。若 Windows 沒有任何明確標示為女性的聲音，程式會說明原因，
不會暗中改用男性聲音。

繁中與簡中介面的 Windows 本機語音共用 `zh-TW`／`zh-CN` 中文女性聲線池，
不顯示 `en-US` Zira；英文與日文介面仍保留各自相符的女性聲線。

Azure Speech 預覽必須由使用者自行申請 Azure Speech 資源，輸入資源金鑰與相符區域；
金鑰以 Windows DPAPI 分開加密，不寫入資料庫、日誌或 GitHub。介面只列出官方標示為
女性且已列入墨寒允許清單的繁中、簡中、英文與日語 Neural 聲線。本次新增的跨語系普通話選項只使用 Standard Neural，排除 Dragon HD／HD Omni。中文介面可跨語系選擇臺灣華語與簡體普通話，依目前介面語言優先排序並保留原有預設。Dragon HD／HD Omni 因方案、計費與區域支援不同，不混入免費預設清單。設定不完整時不會送出網路請求；服務失敗時，
同一句話只回退一次到 Windows 女性本機語音。Azure 免費額度、費率、資料處理與
可用區域以 Microsoft 當期規則為準。

自動測試已涵蓋區域限制、SSML 跳脫、女性聲線白名單、固定 HTTPS 端點、錯誤訊息
不洩漏金鑰、播放完成與 Windows 回退。2026 年 8 月 11 日已使用真實 Azure Speech Free F0、East Asia 資源完成 HTTPS 合成、有效 RIFF 音訊與 Windows 實際播放驗證；預覽標示仍保留，以反映各帳號、區域、配額及當期服務差異。

設定方式：先在 Microsoft Azure 建立 Speech 資源，再到墨寒「語音」頁選擇
Azure Speech（預覽），填入該資源顯示的區域與其中一把金鑰，選擇女性聲線後按
「試聽」。墨寒使用 Microsoft 的 HTTPS REST 介面，不另外安裝 Azure SDK。
切勿把金鑰貼到 GitHub、對話紀錄或截圖中。

未來候選包含 ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly，以及
Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候選前都必須逐一驗證 Windows、
繁中、簡中、英文、日語、女性聲線、延遲、中斷、嘴型同步、封裝體積、隱私與商用
授權；程式授權與聲音模型授權必須分開檢查。

### Microsoft 官方參考

- [Speech 定價與免費額度](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech 服務區域](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [文字轉語音 REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [語言與聲線支援](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)

## 简体中文

`v2.1.0-rc.1` 建立语音供应器的稳定边界。Windows 本地女声、OpenAI 文字语音与
Azure Speech 预览通过同一个注册层接入，嘴型、音量、播放完成信号与表情状态仍由
现有单一权威流程管理。

数据库只保存不受翻译影响的稳定代号；旧版繁中、简中与英文名称会自动迁移。
Realtime 离线、云端失败、密钥缺失或未知供应器时，都优先回到用户选择的 Windows
女性本地语音。如果 Windows 没有任何明确标示为女性的声音，程序会说明原因，
不会暗中改用男性声音。

繁中与简中界面的 Windows 本地语音共用 `zh-TW`／`zh-CN` 中文女性声线池，
不显示 `en-US` Zira；英文与日文界面仍保留各自匹配的女性声线。

Azure Speech 预览要求用户自行申请 Azure Speech 资源，并输入资源密钥与相符区域；
密钥由 Windows DPAPI 单独加密，不会写入数据库、日志或 GitHub。界面只列出官方标示为
女性且已列入墨寒允许列表的繁中、简中、英文与日语 Neural 声线。本次新增的跨语言普通话选项只使用 Standard Neural，排除 Dragon HD／HD Omni。中文界面可跨语言选择台湾华语与简体普通话，按当前界面语言优先排序并保留原有默认值。Dragon HD／HD Omni 因方案、计费与区域支持不同，不混入免费默认列表。设置不完整时不会发出网络请求；服务失败时，
同一句话只回退一次到 Windows 女性本地语音。Azure 免费额度、费率、数据处理与
可用区域以 Microsoft 当期规则为准。

自动测试已经覆盖区域限制、SSML 转义、女性声线白名单、固定 HTTPS 端点、错误信息
不泄漏密钥、播放完成与 Windows 回退。2026 年 8 月 11 日已使用真实 Azure Speech Free F0、East Asia 资源完成 HTTPS 合成、有效 RIFF 音频与 Windows 实际播放验证；仍保留“预览”标示，以反映不同账号、区域、配额及当前服务的差异。

设置方式：先在 Microsoft Azure 建立 Speech 资源，再到墨寒“语音”页选择
Azure Speech（预览），填入该资源显示的区域与其中一把密钥，选择女性声线后点击
“试听”。墨寒使用 Microsoft 的 HTTPS REST 接口，不另外安装 Azure SDK。
切勿把密钥粘贴到 GitHub、对话记录或截图中。

未来候选包括 ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly，以及
Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候选前都必须逐一验证 Windows、
繁中、简中、英文、日语、女性声线、延迟、中断、嘴型同步、打包体积、隐私与商业
授权；程序许可证与声音模型许可证必须分别检查。

### Microsoft 官方参考

- [Speech 定价与免费额度](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech 服务区域](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [文字转语音 REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [语言与声线支持](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)

## English

`v2.1.0-rc.1` establishes a stable speech-provider boundary. Windows local female speech,
OpenAI text-to-speech, and the Azure Speech preview enter through the same registry layer;
lip sync, volume, playback-completion signals, and expression state remain under the existing
single authoritative flow.

The database stores only stable, locale-independent IDs; legacy Traditional Chinese,
Simplified Chinese, and English names migrate automatically. When Realtime is offline, a
cloud service fails, a key is missing, or a provider is unknown, MoHan first returns to the
user-selected Windows local female voice. If Windows has no voice explicitly identified as
female, the application explains why instead of silently selecting a male voice.

Traditional and Simplified Chinese UI share the Windows local `zh-TW`/`zh-CN`
Chinese female-voice pool and do not show `en-US` Zira. English and Japanese UI
retain their matching female voices.

The Azure Speech preview requires users to create their own Azure Speech resource and enter
its key and matching region. Windows DPAPI encrypts the key separately; the key is never
written to the database, logs, or GitHub. The UI lists only voices officially identified as
female Neural options for Traditional Chinese, Simplified Chinese, English, and Japanese that MoHan explicitly allows. The newly exposed cross-locale Mandarin options use Standard Neural only and exclude Dragon HD and HD Omni. Chinese UI can select both Taiwan Mandarin and Simplified Chinese Mandarin, ordered with the current interface locale first while preserving existing defaults. Dragon HD and HD Omni stay out of the free default list because their tier, billing, and regional support differ. Incomplete settings
cause no network request; a service failure falls back once for the same utterance to Windows
local female speech. Current Microsoft rules govern Azure free quotas, pricing, data handling,
and regional availability.

Automated tests cover region restrictions, SSML escaping, the female-voice allowlist, the fixed
HTTPS endpoint, secret-safe error messages, playback completion, and Windows fallback. On August 11, 2026, a real Azure Speech Free F0 resource in East Asia completed HTTPS synthesis, valid RIFF audio validation, and actual Windows playback. The Preview label remains to reflect account, region, quota, and current-service differences.

To configure it, first create a Speech resource in Microsoft Azure. On MoHan's “Voice” page,
select Azure Speech (Preview), enter the region shown by that resource and one of its keys,
choose a female voice, and select “Preview.” MoHan uses Microsoft's HTTPS REST interface and
does not install the Azure SDK. Never paste the key into GitHub, conversation records, or
screenshots.

Future candidates include ElevenLabs, Google Cloud Text-to-Speech, Amazon Polly, and local
Sherpa-ONNX, Piper, or Kokoro deployments. Before adding a candidate, independently validate
Windows, Traditional Chinese, Simplified Chinese, English, Japanese, the female-voice policy,
latency, interruption, lip sync, package size, privacy, and commercial licensing. Review the
software license and voice-model license separately.

### Official Microsoft references

- [Speech pricing and free tier](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech service regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [Text-to-speech REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [Language and voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)

## 日本語

`v2.1.0-rc.1` は、音声プロバイダーの安定した境界を確立します。Windows 本機女性音声、
OpenAI テキスト読み上げ、Azure Speech プレビューは同じ登録層を通して接続され、
口形、音量、再生完了シグナル、表情状態は引き続き既存の単一の正規経路が管理します。

データベースには翻訳の影響を受けない安定 ID だけを保存し、旧版の繁体字中国語、
簡体字中国語、英語の名称は自動移行します。Realtime がオフライン、クラウドサービスが
失敗、キーが不足、またはプロバイダーが不明な場合は、利用者が選択した Windows 本機の
女性音声へ最初に戻ります。Windows に女性と明示された音声が一つもない場合、
男性音声へ密かに切り替えず、アプリケーションが理由を説明します。

繁体字・簡体字中国語画面の Windows 本機音声は `zh-TW`／`zh-CN` の中国語女性音声
プールを共有し、`en-US` Zira は表示しません。英語・日本語画面には、それぞれに
適合する女性音声を引き続き表示します。

Azure Speech プレビューを使うには、利用者自身が Azure Speech リソースを作成し、
そのキーと対応するリージョンを入力する必要があります。キーは Windows DPAPI で個別に
暗号化され、データベース、ログ、GitHub には書き込まれません。画面に表示するのは、
繁体字中国語、簡体字中国語、英語、日本語について公式に女性と示され、墨寒の許可リストへ明示した Neural 音声だけです。今回追加する言語横断の普通話選択肢は Standard Neural だけを使用し、Dragon HD／HD Omni を除外します。中国語画面では台湾華語と簡体字普通話を言語横断で選択でき、現在の画面言語を優先して並べ、従来の既定値を維持します。Dragon HD／HD Omni はプラン、課金、対応リージョンが異なるため無料の既定一覧へ混在させません。設定が不完全な場合はネットワーク要求を送信せず、サービス障害時は同じ発話を一度だけ
Windows 本機女性音声へフォールバックします。Azure の無料枠、料金、データ処理、
利用可能リージョンには Microsoft のその時点の規則が適用されます。

自動テストは、リージョン制限、SSML エスケープ、女性音声の許可リスト、固定 HTTPS
エンドポイント、キーを漏らさないエラーメッセージ、再生完了、Windows フォールバックを
網羅しています。2026 年 8 月 11 日、East Asia の実 Azure Speech Free F0 リソースで HTTPS 合成、有効な RIFF 音声、Windows での実再生を検証しました。アカウント、リージョン、割り当て、当期サービスの差異を示すため「プレビュー」表示は維持します。

設定するには、まず Microsoft Azure で Speech リソースを作成します。墨寒の「音声」ページで
Azure Speech（プレビュー）を選択し、そのリソースに表示されたリージョンとキーの一つを入力し、
女性音声を選んで「試聴」を押します。墨寒は Microsoft の HTTPS REST インターフェースを使用し、
Azure SDK を追加インストールしません。キーを GitHub、対話履歴、スクリーンショットへ
貼り付けないでください。

将来の候補には ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly、およびローカルの
Sherpa-ONNX、Piper、Kokoro などがあります。候補を追加する前に、Windows、繁体字中国語、
簡体字中国語、英語、日本語、女性音声ポリシー、遅延、中断、口形同期、パッケージ容量、
プライバシー、商用ライセンスを個別に検証する必要があります。ソフトウェアのライセンスと
音声モデルのライセンスは分けて確認します。

### Microsoft 公式リファレンス

- [Speech の料金と無料枠](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech サービスのリージョン](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [テキスト読み上げ REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [対応言語と音声](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
