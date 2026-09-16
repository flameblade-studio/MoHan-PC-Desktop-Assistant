# 可插拔語音供應器／可插拔语音供应器／Pluggable Speech Providers／交換可能な音声プロバイダー

## 繁體中文

`v2.1.0-rc.1` 建立語音供應器的穩定邊界。Windows 本機女聲、OpenAI 文字語音與
Azure Speech 預覽透過同一個登錄層接入，嘴型、音量、播放完成訊號與表情狀態仍由
既有單一權威流程管理。

資料庫只保存不受翻譯影響的穩定代號；舊版繁中、簡中與英文名稱會自動遷移。
Realtime 離線、雲端服務未完成、金鑰待補或供應器待辨識時，都優先回到使用者選定的 Windows
女性本機語音。Windows 女性聲音清單為空時，程式會說明原因並維持女性聲音限定。

繁中與簡中介面的 Windows 本機語音共用 `zh-TW`／`zh-CN` 中文女性聲線池，
顯示範圍限定為 `zh-TW`／`zh-CN` 女性聲線；英文與日文介面仍保留各自相符的女性聲線。

Azure Speech 預覽必須由使用者自行申請 Azure Speech 資源，輸入資源金鑰與相符區域；
金鑰以 Windows DPAPI 分開加密，其儲存邊界限定於安全憑證存放區。介面只列出官方標示為
女性且已列入墨寒允許清單的繁中、簡中、英文與日語 Neural 聲線。本次新增的跨語系普通話選項限定使用 Standard Neural；Dragon HD／HD Omni 由獨立 Preview 供應器管理。中文介面可跨語系選擇臺灣華語與簡體普通話，依目前介面語言優先排序並保留原有預設。Dragon HD／HD Omni 因方案、計費與區域支援不同，維持獨立 Preview 清單。設定完整後才送出網路請求；服務未完成時，
同一句話只回退一次到 Windows 女性本機語音。Azure 免費額度、費率、資料處理與
可用區域以 Microsoft 當期規則為準。

`v3.1.0` 將 Dragon HD／HD Omni 公開為另一個由使用者主動啟用的可選 Preview 供應器，
使用獨立於一般 Azure Speech 的金鑰、區域與聲線設定。它要求使用者自行建立 S0 資源，
只顯示官方標示的女性聲線，並依所選區域顯示具備支援的 HD Flash。HD 服務未完成時，
同一句話依序只嘗試一次一般 Azure Speech 與 Windows 本機女聲，將嘗試次數固定為一次並控制計費。
Dragon HD 的事件範圍是合成音訊，viseme 由本機 50 Hz 音訊分析提供；Azure WAV 完整緩衝後，播放與既有 50 Hz 本機音訊
分析同步開始，因此區域網路延遲只增加發話前等待，嘴型偏移持續由音訊分析結果決定。
Central India S0 已完成真實 Windows 合成與播放驗證，但臺灣連線等待明顯；
使用者應優先選擇實際延遲可接受且支援所需聲線的區域。

自動測試已涵蓋區域限制、SSML 跳脫、女性聲線白名單、固定 HTTPS 端點、錯誤訊息
維持金鑰機密性、播放完成與 Windows 回退。2026 年 8 月 11 日已使用真實 Azure Speech Free F0、East Asia 資源完成 HTTPS 合成、有效 RIFF 音訊與 Windows 實際播放驗證；預覽標示仍保留，以反映各帳號、區域、配額及當期服務差異。

設定方式：先在 Microsoft Azure 建立 Speech 資源，再到墨寒「語音」頁選擇
Azure Speech（預覽），填入該資源顯示的區域與其中一把金鑰，選擇女性聲線後按
「試聽」。墨寒透過 Microsoft HTTPS REST 介面直接運作。
金鑰只輸入墨寒的安全設定欄位，並留在 GitHub、對話紀錄與截圖範圍之外。

未來候選包含 ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly，以及
Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候選前都必須逐一驗證 Windows、
繁中、簡中、英文、日語、女性聲線、延遲、中斷、嘴型同步、封裝體積、隱私與商用
授權；程式授權與聲音模型授權必須分開檢查。

### Microsoft 官方參考

- [Speech 定價與免費額度](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech 服務區域](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [文字轉語音 REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [語言與聲線支援](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- [Dragon HD／HD Omni 官方說明](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices)

## 简体中文

`v2.1.0-rc.1` 建立语音供应器的稳定边界。Windows 本地女声、OpenAI 文字语音与
Azure Speech 预览通过同一个注册层接入，嘴型、音量、播放完成信号与表情状态仍由
现有单一权威流程管理。

数据库只保存不受翻译影响的稳定代号；旧版繁中、简中与英文名称会自动迁移。
Realtime 离线、云端失败、密钥待补或供应器待识别时，都优先回到用户选择的 Windows
女性本地语音。Windows 女性声音列表为空时，程序会说明原因并保持女性声音限定。

繁中与简中界面的 Windows 本地语音共用 `zh-TW`／`zh-CN` 中文女性声线池，
显示范围限定为 `zh-TW`／`zh-CN` 女性声线；英文与日文界面仍保留各自匹配的女性声线。

Azure Speech 预览要求用户自行申请 Azure Speech 资源，并输入资源密钥与相符区域；
密钥由 Windows DPAPI 单独加密，其存储边界限定于安全凭据存储区。界面只列出官方标示为
女性且已列入墨寒允许列表的繁中、简中、英文与日语 Neural 声线。本次新增的跨语言普通话选项限定使用 Standard Neural；Dragon HD／HD Omni 由独立 Preview 供应器管理。中文界面可跨语言选择台湾华语与简体普通话，按当前界面语言优先排序并保留原有默认值。Dragon HD／HD Omni 因方案、计费与区域支持不同，保持独立 Preview 列表。设置完整后才发出网络请求；服务未完成时，
同一句话只回退一次到 Windows 女性本地语音。Azure 免费额度、费率、数据处理与
可用区域以 Microsoft 当期规则为准。

`v3.1.0` 将 Dragon HD／HD Omni 公开为另一个由用户主动启用的可选 Preview 供应器，
使用独立于一般 Azure Speech 的密钥、区域与声线设置。它要求用户自行建立 S0 资源，
只显示官方标示的女性声线，并按所选区域显示具备支持的 HD Flash。HD 服务未完成时，
同一句话依次只尝试一次一般 Azure Speech 与 Windows 本地女声，将尝试次数固定为一次并控制计费。
Dragon HD 的事件範圍是合成音訊，viseme 由本機 50 Hz 音訊分析提供；Azure WAV 完整缓冲后，播放与现有 50 Hz 本地音频
分析同步开始，因此区域网络延迟只增加发话前等待，嘴型偏移持续由音频分析结果决定。
Central India S0 已完成真实 Windows 合成与播放验证，但台湾连接等待明显；
用户应优先选择实际延迟可接受且支持所需声线的区域。

自动测试已经覆盖区域限制、SSML 转义、女性声线白名单、固定 HTTPS 端点、错误信息
保持密钥机密性、播放完成与 Windows 回退。2026 年 8 月 11 日已使用真实 Azure Speech Free F0、East Asia 资源完成 HTTPS 合成、有效 RIFF 音频与 Windows 实际播放验证；仍保留“预览”标示，以反映不同账号、区域、配额及当前服务的差异。

设置方式：先在 Microsoft Azure 建立 Speech 资源，再到墨寒“语音”页选择
Azure Speech（预览），填入该资源显示的区域与其中一把密钥，选择女性声线后点击
“试听”。墨寒通过 Microsoft HTTPS REST 接口直接运行。
密钥只输入墨寒的安全设置字段，并留在 GitHub、对话记录与截图范围之外。

未来候选包括 ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly，以及
Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候选前都必须逐一验证 Windows、
繁中、简中、英文、日语、女性声线、延迟、中断、嘴型同步、打包体积、隐私与商业
授权；程序许可证与声音模型许可证必须分别检查。

### Microsoft 官方参考

- [Speech 定价与免费额度](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech 服务区域](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [文字转语音 REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [语言与声线支持](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- [Dragon HD／HD Omni 官方说明](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices)

## English

`v2.1.0-rc.1` establishes a stable speech-provider boundary. Windows local female speech,
OpenAI text-to-speech, and the Azure Speech preview enter through the same registry layer;
lip sync, volume, playback-completion signals, and expression state remain under the existing
single authoritative flow.

The database stores only stable, locale-independent IDs; legacy Traditional Chinese,
Simplified Chinese, and English names migrate automatically. When Realtime is offline, a
cloud service is unavailable, a key is pending, or a provider awaits identification, MoHan first returns to the
user-selected Windows local female voice. When the Windows female-voice list is empty, the application explains why and preserves the female-voice requirement.

Traditional and Simplified Chinese UI share the Windows local `zh-TW`/`zh-CN`
Chinese female-voice pool and scope the displayed list to `zh-TW`/`zh-CN` female voices. English and Japanese UI
retain their matching female voices.

The Azure Speech preview requires users to create their own Azure Speech resource and enter
its key and matching region. Windows DPAPI encrypts the key separately; its storage boundary is the secure credential store. The UI lists only voices officially identified as
female Neural options for Traditional Chinese, Simplified Chinese, English, and Japanese that MoHan explicitly allows. The newly exposed cross-locale Mandarin options use Standard Neural; the separate Preview provider manages Dragon HD and HD Omni. Chinese UI can select both Taiwan Mandarin and Simplified Chinese Mandarin, ordered with the current interface locale first while preserving existing defaults. Dragon HD and HD Omni use a separate Preview list because their tier, billing, and regional support differ. Complete settings enable network requests; an unavailable service falls back once for the same utterance to Windows
local female speech. Current Microsoft rules govern Azure free quotas, pricing, data handling,
and regional availability.

`v3.1.0` publishes Dragon HD/HD Omni as another optional Preview provider that is
enabled explicitly by the user and uses key, region, and voice settings independent from standard
Azure Speech. Users create their own S0 resource; the UI lists only officially identified
female voices and shows HD Flash where the selected region supports it. For one
utterance, unavailable HD service falls back once to standard Azure Speech and then once to Windows
local female speech, fixing each attempt count at one and controlling charges. Dragon HD provides synthesized audio, while the local 50 Hz audio analysis provides visemes. After the Azure WAV is fully buffered, playback and the existing local 50 Hz audio
analysis start together, so regional latency delays speech onset and remains separate from the audio-derived mouth offset. A real Central India S0 resource passed Windows synthesis and
playback validation, but Taiwan experienced a noticeable wait; users should prefer a
supported region with acceptable measured latency.

Automated tests cover region restrictions, SSML escaping, the female-voice allowlist, the fixed
HTTPS endpoint, secret-safe error messages, playback completion, and Windows fallback. On August 11, 2026, a real Azure Speech Free F0 resource in East Asia completed HTTPS synthesis, valid RIFF audio validation, and actual Windows playback. The Preview label remains to reflect account, region, quota, and current-service differences.

To configure it, first create a Speech resource in Microsoft Azure. On MoHan's “Voice” page,
select Azure Speech (Preview), enter the region shown by that resource and one of its keys,
choose a female voice, and select “Preview.” MoHan operates directly through Microsoft's HTTPS REST interface. Enter the key only in MoHan's secure settings field and keep it outside GitHub, conversation records, and
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
- [Official Dragon HD/HD Omni guide](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices)

## 日本語

`v2.1.0-rc.1` は、音声プロバイダーの安定した境界を確立します。Windows 本機女性音声、
OpenAI テキスト読み上げ、Azure Speech プレビューは同じ登録層を通して接続され、
口形、音量、再生完了シグナル、表情状態は引き続き既存の単一の正規経路が管理します。

データベースには翻訳の影響を受けない安定 ID だけを保存し、旧版の繁体字中国語、
簡体字中国語、英語の名称は自動移行します。Realtime がオフライン、クラウドサービスが
利用待ち、キーが準備中、またはプロバイダーの識別待ちの場合は、利用者が選択した Windows 本機の
女性音声へ最初に戻ります。女性音声一覧が空の場合、アプリケーションが理由を説明し、女性音声の条件を維持します。

繁体字・簡体字中国語画面の Windows 本機音声は `zh-TW`／`zh-CN` の中国語女性音声
プールを共有し、表示範囲を `zh-TW`／`zh-CN` 女性音声に限定します。英語・日本語画面には、それぞれに
適合する女性音声を引き続き表示します。

Azure Speech プレビューを使うには、利用者自身が Azure Speech リソースを作成し、
そのキーと対応するリージョンを入力する必要があります。キーは Windows DPAPI で個別に
暗号化され、保存境界を安全な資格情報ストアに限定します。画面に表示するのは、
繁体字中国語、簡体字中国語、英語、日本語について公式に女性と示され、墨寒の許可リストへ明示した Neural 音声だけです。今回追加する言語横断の普通話選択肢は Standard Neural を使用し、Dragon HD／HD Omni は独立した Preview プロバイダーで管理します。中国語画面では台湾華語と簡体字普通話を言語横断で選択でき、現在の画面言語を優先して並べ、従来の既定値を維持します。Dragon HD／HD Omni はプラン、課金、対応リージョンが異なるため独立した Preview 一覧を使います。設定完了後にネットワーク要求を送信し、サービス利用待ちの場合は同じ発話を一度だけ
Windows 本機女性音声へフォールバックします。Azure の無料枠、料金、データ処理、
利用可能リージョンには Microsoft のその時点の規則が適用されます。

`v3.1.0` は Dragon HD／HD Omni を、利用者が明示的に有効化する任意の別 Preview
プロバイダーとして公開します。通常の Azure Speech とはキー、リージョン、音声設定を
独立した設定として保持します。利用者自身の S0 リソースを必要とし、公式に女性と示された音声だけを
表示し、選択リージョンが対応する HD Flash を表示します。HD サービス利用待ちの場合、同じ発話は通常の
Azure Speech、Windows 本機女性音声の順に各一回だけ切り替え、試行回数を各一回に固定し、課金を制御します。
Dragon HD は合成音声を提供し、viseme は本機 50 Hz 音声解析が提供します。Azure WAV を完全にバッファした後、再生と
既存の 50 Hz 本機音声解析を同時開始するため、リージョン遅延は発話開始前の待ち時間だけを
増やし、口形オフセットは音声解析結果から決定します。Central India S0 の実リソースで
Windows の合成と再生を検証しましたが、台湾からは明確な待ち時間がありました。利用者は
必要な音声に対応し、実測遅延を許容できるリージョンを優先してください。

自動テストは、リージョン制限、SSML エスケープ、女性音声の許可リスト、固定 HTTPS
エンドポイント、キーの機密性を維持するエラーメッセージ、再生完了、Windows フォールバックを
網羅しています。2026 年 8 月 11 日、East Asia の実 Azure Speech Free F0 リソースで HTTPS 合成、有効な RIFF 音声、Windows での実再生を検証しました。アカウント、リージョン、割り当て、当期サービスの差異を示すため「プレビュー」表示は維持します。

設定するには、まず Microsoft Azure で Speech リソースを作成します。墨寒の「音声」ページで
Azure Speech（プレビュー）を選択し、そのリソースに表示されたリージョンとキーの一つを入力し、
女性音声を選んで「試聴」を押します。墨寒は Microsoft の HTTPS REST インターフェースから直接動作します。キーは墨寒の安全な設定欄だけに入力し、GitHub、対話履歴、スクリーンショットの
範囲外に保持してください。

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
- [Dragon HD／HD Omni 公式ガイド](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices)
