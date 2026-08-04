# Pluggable speech providers / 可插拔語音供應器 / 可插拔语音供应器

## 繁體中文

`v2.1.0-rc.1` 建立語音供應器的穩定邊界，但不把尚未完成實機驗證的第三方服務顯示成可用功能。現有 Windows 本機女聲與 OpenAI 文字語音透過同一個登錄層接入，嘴型、音量、播放完成訊號與表情狀態仍由既有單一權威流程管理。

資料庫只保存不受翻譯影響的穩定代號；舊版繁中、簡中與英文名稱會自動遷移。Realtime 離線、雲端失敗、金鑰缺漏或未知供應器都優先回到使用者選定的 Windows 女性本機語音。若 Windows 沒有任何明確標示為女性的聲音，程式會說明原因，不會暗中改用男性聲音。

未來候選包含 Azure Speech、ElevenLabs、Google Cloud Text-to-Speech、Amazon Polly、OpenAI Speech，以及 Sherpa-ONNX、Piper、Kokoro 等本地方案。加入任何候選前都必須逐一驗證 Windows、繁中、簡中、英文、女性聲線、延遲、中斷、嘴型同步、封裝體積、隱私與商用授權；程式授權與聲音模型授權必須分開檢查。

## 简体中文

`v2.1.0-rc.1` 先建立稳定的语音供应器边界，不会把未经实机验证的第三方服务伪装成可用功能。Windows 本地女声仍是 Realtime 离线、云端失败、密钥缺失或未知供应器时的第一回退。旧版保存的多语言显示名称会迁移为不受翻译影响的稳定代号。

未来供应器必须分别验证女性声线、三种界面语言、延迟、中断、嘴型同步、隐私、安装体积及商业授权。程序许可证不代表每一个声音模型也允许商业使用。

## English

`v2.1.0-rc.1` introduces a stable provider boundary without advertising unverified third-party integrations as finished features. Existing Windows female speech and OpenAI text-to-speech enter through one explicit registry. Lip sync, volume, completion signals, and expression state keep their existing single authoritative paths.

Persisted settings use locale-independent IDs and migrate legacy Traditional Chinese, Simplified Chinese, and English labels. Windows female local speech remains the first fallback when Realtime is offline, a cloud request fails, a key is missing, or a provider is unknown. MoHan reports the absence of a verified female Windows voice instead of silently selecting a male voice.

Future candidates include Azure Speech, ElevenLabs, Google Cloud Text-to-Speech, Amazon Polly, OpenAI Speech, and local Sherpa-ONNX, Piper, or Kokoro deployments. Each provider requires separate validation for Windows, all three UI languages, female voice policy, latency, interruption, lip sync, package size, privacy, and commercial licensing. Code and voice-model licenses must be reviewed independently.
