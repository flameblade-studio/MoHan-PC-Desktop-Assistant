# Pluggable speech providers / 可插拔語音供應器 / 可插拔语音供应器

## 繁體中文

`v2.1.0-rc.1` 建立語音供應器的穩定邊界。Windows 本機女聲、OpenAI 文字語音與 Azure Speech 預覽透過同一個登錄層接入，嘴型、音量、播放完成訊號與表情狀態仍由既有單一權威流程管理。

資料庫只保存不受翻譯影響的穩定代號；舊版繁中、簡中與英文名稱會自動遷移。Realtime 離線、雲端失敗、金鑰缺漏或未知供應器都優先回到使用者選定的 Windows 女性本機語音。若 Windows 沒有任何明確標示為女性的聲音，程式會說明原因，不會暗中改用男性聲音。

Azure Speech 預覽必須由使用者自行申請 Azure Speech 資源，輸入資源金鑰與相符區域；金鑰以 Windows DPAPI 分開加密，不寫入資料庫、日誌或 GitHub。介面只列出官方標示為女性的繁中、簡中與英文聲線。設定不完整時不會送出網路請求；服務失敗時，同一句話只回退一次到 Windows 女性本機語音。Azure 免費額度、費率、資料處理與可用區域以 Microsoft 當期規則為準。

自動測試已涵蓋區域限制、SSML 跳脫、女性聲線白名單、固定 HTTPS 端點、錯誤訊息不洩漏金鑰、播放完成與 Windows 回退。RC 發布前仍需使用真實 Azure 帳號完成端到端試播；在完成前，功能維持「預覽」標示。

設定方式：先在 Microsoft Azure 建立 Speech 資源，再到墨寒「語音」頁選擇 Azure Speech（預覽），填入該資源顯示的區域與其中一把金鑰，選擇女性聲線後按「試聽」。墨寒使用 Microsoft 的 HTTPS REST 介面，不另外安裝 Azure SDK。切勿把金鑰貼到 GitHub、對話紀錄或截圖中。

未來候選包含 ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly，以及 Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候選前都必須逐一驗證 Windows、繁中、簡中、英文、女性聲線、延遲、中斷、嘴型同步、封裝體積、隱私與商用授權；程式授權與聲音模型授權必須分開檢查。

## 简体中文

`v2.1.0-rc.1` 建立稳定的语音供应器边界。Windows 本地女声、OpenAI 文字语音与 Azure Speech 预览共用同一套音量、嘴型、完成信号和失败回退流程。Windows 本地女声仍是 Realtime 离线、云端失败、密钥缺失或未知供应器时的第一回退。

Azure Speech 需要用户自己的资源密钥与相符区域；密钥由 Windows DPAPI 单独加密。界面只列出官方标示为女性的繁中、简中和英文声线。设定不完整时不会发出网络请求；服务失败时，同一句话只回退一次到 Windows 女性语音。自动测试已完成，但真实 Azure 帐号端到端试播完成前仍标示为预览。

请先在 Microsoft Azure 建立 Speech 资源，再到墨寒“语音”页选择 Azure Speech（预览），填入资源区域和其中一把密钥，选择女性声线后试听。墨寒使用 HTTPS REST 接口，不需另外安装 Azure SDK。请勿将密钥贴到 GitHub、对话记录或截图。

未来供应器必须分别验证女性声线、三种界面语言、延迟、中断、嘴型同步、隐私、安装体积及商业授权。程序许可证不代表每一个声音模型也允许商业使用。

## English

`v2.1.0-rc.1` introduces a stable provider boundary. Windows female speech, OpenAI text-to-speech, and the Azure Speech preview enter through one explicit registry. Lip sync, volume, completion signals, expression state, and fallback keep their existing single authoritative paths.

Persisted settings use locale-independent IDs and migrate legacy Traditional Chinese, Simplified Chinese, and English labels. Windows female local speech remains the first fallback when Realtime is offline, a cloud request fails, a key is missing, or a provider is unknown. MoHan reports the absence of a verified female Windows voice instead of silently selecting a male voice.

Azure Speech requires the user's own Speech resource key and matching region. The key is encrypted separately with Windows DPAPI and is never stored in the database, logs, or GitHub. The UI exposes only Microsoft-listed female Traditional Chinese, Simplified Chinese, and English voices. Missing settings cause no network request; a service failure retries the same utterance once through Windows female local speech. Automated coverage verifies endpoint restrictions, SSML escaping, the female allowlist, secret-safe errors, completion, and fallback. The integration remains labelled Preview until a real Azure account completes end-to-end playback validation.

Create a Speech resource in Microsoft Azure, select Azure Speech (Preview) on MoHan's Voice page, enter that resource's region and one key, choose a female voice, and use Preview. MoHan calls the HTTPS REST endpoint directly and does not add the Azure SDK. Never paste the key into GitHub, chat history, or screenshots.

Future candidates include ElevenLabs, Google Cloud Text-to-Speech, Amazon Polly, and local Sherpa-ONNX, Piper, or Kokoro deployments. Each provider requires separate validation for Windows, all three UI languages, female voice policy, latency, interruption, lip sync, package size, privacy, and commercial licensing. Code and voice-model licenses must be reviewed independently.

## Microsoft 官方參考 / Microsoft official references

- [Speech pricing and free tier](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [Speech service regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)
- [Text-to-speech REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [Language and voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
