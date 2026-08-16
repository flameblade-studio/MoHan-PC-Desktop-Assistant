"""Cloud connector and Home Assistant translations."""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

CLOUD_HOME_TRANSLATIONS: TranslationCatalog = frozendict({
    # Cloud connectors.
    "權杖由作業系統安全加密保存，不寫入資料庫或設定檔。": translations(
        "令牌由操作系统安全加密保存，不写入数据库或配置文件。",
        "Tokens are encrypted by the operating system and are never written to the database or configuration files.",
        "トークンは OS により安全に暗号化され、データベースや設定ファイルには保存されません。",
    ),
    "{platform} 的原生安全金鑰保存尚未完成實機驗證，因此 OAuth 連線暫停；"
    "墨寒不會改用明文保存。": translations(
        "{platform} 的原生安全密钥保存尚未完成真机验证，因此 OAuth 连接暂停；"
        "墨寒不会改用明文保存。",
        "Native secure secret storage on {platform} has not yet passed real-device verification, "
        "so OAuth connections are disabled; MoHan will not fall back to plaintext storage.",
        "{platform} のネイティブ安全保管は実機検証が未完了のため、OAuth 接続を停止しています。"
        "墨寒が平文保存へ切り替えることはありません。",
    ),
    "Google、Microsoft 與 GitHub 預設停用。連線時使用瀏覽器 OAuth；{note}": translations(
        "Google、Microsoft 与 GitHub 默认停用。连接时使用浏览器 OAuth；{note}",
        "Google, Microsoft, and GitHub are disabled by default. Browser OAuth is used for connections; {note}",
        "Google、Microsoft、GitHub は既定で無効です。接続にはブラウザー OAuth を使用します。{note}",
    ),
    "貼上你在服務商後台建立的 Desktop App Client ID": translations(
        "粘贴你在服务商后台创建的 Desktop App Client ID",
        "Paste the Desktop App Client ID created in the provider console",
        "サービス管理画面で作成した Desktop App Client ID を貼り付け",
    ),
    "若服務商提供 Client Secret 才需填寫": translations(
        "仅在服务商提供 Client Secret 时填写",
        "Enter only if the provider supplies a Client Secret",
        "サービスから Client Secret が発行された場合のみ入力",
    ),
    "開啟瀏覽器安全連線": translations(
        "打开浏览器安全连接", "Open secure browser connection", "ブラウザーで安全に接続"
    ),
    "測試選取服務": translations(
        "测试选中服务", "Test selected service", "選択したサービスをテスト"
    ),
    "撤銷選取服務": translations(
        "撤销选中服务", "Revoke selected service", "選択したサービスを解除"
    ),
    "服務": translations("服务", "Service", "サービス"),
    "授權範圍": translations("授权范围", "OAuth scopes", "認可スコープ"),
    "狀態": translations("状态", "Status", "状態"),
    "已設定服務": translations(
        "已配置服务", "Configured services", "設定済みサービス"
    ),
    "{platform} 尚無經過實機驗證的安全金鑰保存；OAuth 連線已安全停用。": translations(
        "{platform} 尚无通过真机验证的安全密钥保存；OAuth 连接已安全停用。",
        "{platform} does not yet have real-device-verified secure secret storage; OAuth connections are safely disabled.",
        "{platform} では安全な秘密情報保管の実機検証が未完了のため、OAuth 接続を安全に無効化しています。",
    ),
    "請先填入服務商後台建立的 OAuth Client ID。": translations(
        "请先填写服务商后台创建的 OAuth Client ID。",
        "Enter the OAuth Client ID created in the provider console first.",
        "サービス管理画面で作成した OAuth Client ID を先に入力してください。",
    ),
    "等待瀏覽器授權，請勿關閉墨寒……": translations(
        "等待浏览器授权，请勿关闭墨寒……",
        "Waiting for browser authorization. Do not close MoHan…",
        "ブラウザーでの認可を待っています。墨寒を閉じないでください…",
    ),
    "無法安全保存 OAuth 權杖：{error}": translations(
        "无法安全保存 OAuth 令牌：{error}",
        "Could not securely store the OAuth token: {error}",
        "OAuth トークンを安全に保存できませんでした：{error}",
    ),
    "{provider} 已安全連線": translations(
        "{provider} 已安全连接",
        "{provider} connected securely",
        "{provider} に安全に接続しました",
    ),
    "{provider} 連線失敗：{error}": translations(
        "{provider} 连接失败：{error}",
        "{provider} connection failed: {error}",
        "{provider} への接続に失敗しました：{error}",
    ),
    "測試失敗：{error}": translations(
        "测试失败：{error}", "Test failed: {error}", "テストに失敗しました：{error}"
    ),
    "測試中…": translations("测试中…", "Testing…", "テスト中…"),
    "正在分別檢查 Gmail、Google Calendar 與 Google Drive……": translations(
        "正在分别检查 Gmail、Google Calendar 与 Google Drive……",
        "Checking Gmail, Google Calendar, and Google Drive separately…",
        "Gmail、Google Calendar、Google Drive を個別に確認しています…",
    ),
    "正在檢查選取的服務……": translations(
        "正在检查选中的服务……",
        "Checking the selected service…",
        "選択したサービスを確認しています…",
    ),
    "{name}：{status}（{detail}）": translations(
        "{name}：{status}（{detail}）",
        "{name}: {status} ({detail})",
        "{name}：{status}（{detail}）",
    ),
    "正常": translations("正常", "Healthy", "正常"),
    "失敗": translations("失败", "Failed", "失敗"),
    "Google 三項服務測試": translations(
        "Google 三项服务测试", "Google Three-Service Test", "Google 3 サービスのテスト"
    ),
    "雲端服務測試": translations(
        "云端服务测试", "Cloud Service Test", "クラウドサービステスト"
    ),
    "失敗項目通常代表該 API 尚未啟用、OAuth 範圍不足，或網路暫時無法連線。": translations(
        "失败项目通常表示该 API 尚未启用、OAuth 范围不足，或网络暂时无法连接。",
        "A failed item usually means its API is not enabled, the OAuth scopes are insufficient, or the network is temporarily unavailable.",
        "失敗した項目は通常、API が未有効、OAuth スコープ不足、または一時的なネットワーク障害を示します。",
    ),
    "雲端測試超過 35 秒，已停止等待；請查看個別服務的 API 與網路狀態。": translations(
        "云端测试超过 35 秒，已停止等待；请检查各服务的 API 与网络状态。",
        "The cloud test exceeded 35 seconds and was stopped. Check each service API and the network status.",
        "クラウドテストが 35 秒を超えたため待機を停止しました。各サービスの API とネットワーク状態を確認してください。",
    ),
    "撤銷雲端服務": translations(
        "撤销云端服务", "Revoke Cloud Service", "クラウドサービスを解除"
    ),
    "確定移除 {provider} 的本機權杖？": translations(
        "确定移除 {provider} 的本地令牌？",
        "Remove the local token for {provider}?",
        "{provider} のローカルトークンを削除しますか？",
    ),
    "本機權杖已移除": translations(
        "本地令牌已移除", "Local token removed", "ローカルトークンを削除しました"
    ),
    "尚未測試": translations("尚未测试", "Not tested", "未テスト"),
    "未設定": translations("未配置", "Not configured", "未設定"),
    "已撤銷": translations("已撤销", "Revoked", "解除済み"),
    "OAuth 已連線": translations("OAuth 已连接", "OAuth connected", "OAuth 接続済み"),
    "尚未完成 OAuth 連線": translations(
        "尚未完成 OAuth 连接",
        "OAuth connection has not been completed",
        "OAuth 接続が完了していません",
    ),
    "無法安全更新 OAuth 權杖：{error}": translations(
        "无法安全更新 OAuth 令牌：{error}",
        "Could not securely update the OAuth token: {error}",
        "OAuth トークンを安全に更新できませんでした：{error}",
    ),
    "OAuth 權杖資料不完整": translations(
        "OAuth 令牌数据不完整",
        "OAuth token data is incomplete",
        "OAuth トークンのデータが不完全です",
    ),
    "Google 與 Microsoft 均已連線，請明確指定要使用哪個帳戶": translations(
        "Google 与 Microsoft 均已连接，请明确指定要使用哪个帐户",
        "Both Google and Microsoft are connected; specify which account to use",
        "Google と Microsoft の両方に接続されています。使用するアカウントを明示してください",
    ),
    "尚未連線 Google 或 Microsoft，或工具計畫未指定供應商": translations(
        "尚未连接 Google 或 Microsoft，或工具计划未指定供应商",
        "Google or Microsoft is not connected, or the tool plan did not specify a provider",
        "Google または Microsoft に未接続か、ツール計画でプロバイダーが指定されていません",
    ),
    "此工具目前只支援 google 或 microsoft": translations(
        "此工具目前仅支持 google 或 microsoft",
        "This tool currently supports only google or microsoft",
        "このツールは現在 google または microsoft のみ対応しています",
    ),
    "全部正常": translations("全部正常", "All healthy", "すべて正常"),
    "部分功能異常": translations(
        "部分功能异常", "Some features have issues", "一部の機能に問題があります"
    ),
    "主要日曆可讀取": translations(
        "主要日历可读取",
        "Primary calendar is readable",
        "メインカレンダーを読み取れます",
    ),
    "雲端硬碟中繼資料可讀取": translations(
        "云端硬盘元数据可读取",
        "Drive metadata is readable",
        "ドライブのメタデータを読み取れます",
    ),
    "Google 帳戶": translations("Google 帐户", "Google account", "Google アカウント"),
    "Microsoft 帳戶": translations(
        "Microsoft 帐户", "Microsoft account", "Microsoft アカウント"
    ),
    "GitHub 帳戶": translations("GitHub 帐户", "GitHub account", "GitHub アカウント"),
    # Home Assistant.
    "啟用 Home Assistant 整合": translations(
        "启用 Home Assistant 集成",
        "Enable Home Assistant integration",
        "Home Assistant 連携を有効化",
    ),
    "例如：http://homeassistant.local:8123": translations(
        "例如：http://homeassistant.local:8123",
        "Example: http://homeassistant.local:8123",
        "例：http://homeassistant.local:8123",
    ),
    "已由作業系統安全保存（留空不變）": translations(
        "已由操作系统安全保存（留空不变）",
        "Securely stored by the operating system (leave blank to keep it)",
        "OS により安全に保存済み（空欄なら変更なし）",
    ),
    "貼上 Home Assistant 長期存取權杖": translations(
        "粘贴 Home Assistant 长期访问令牌",
        "Paste the Home Assistant long-lived access token",
        "Home Assistant の長期アクセストークンを貼り付け",
    ),
    "驗證 HTTPS 憑證": translations(
        "验证 HTTPS 证书", "Verify HTTPS certificate", "HTTPS 証明書を検証"
    ),
    "保存連線設定": translations(
        "保存连接设置", "Save connection settings", "接続設定を保存"
    ),
    "測試連線": translations("测试连接", "Test connection", "接続をテスト"),
    "讀取裝置": translations("读取设备", "Load devices", "機器を読み取る"),
    "Home Assistant 位址": translations(
        "Home Assistant 地址", "Home Assistant address", "Home Assistant アドレス"
    ),
    "長期存取權杖": translations(
        "长期访问令牌", "Long-lived access token", "長期アクセストークン"
    ),
    "連線狀態": translations("连接状态", "Connection status", "接続状態"),
    "裝置狀態": translations("设备状态", "Device status", "機器の状態"),
    "門鎖、警報與加熱設備永遠套用高風險政策。"
    "墨寒不能因對話內容自行降低安全等級。": translations(
        "门锁、警报与加热设备始终应用高风险策略。墨寒不能因对话内容自行降低安全等级。",
        "Door locks, alarms, and heating devices always use the high-risk policy. "
        "MoHan cannot lower their security level based on conversation content.",
        "ドアロック、警報、加熱機器には常に高リスク方針を適用します。"
        "会話内容を理由に墨寒が安全レベルを下げることはできません。",
    ),
    "{platform} 的安全金鑰保存尚未完成實機驗證；Home Assistant 連線暫停，"
    "且不會儲存明文權杖。": translations(
        "{platform} 的安全密钥保存尚未完成真机验证；Home Assistant 连接暂停，"
        "且不会保存明文令牌。",
        "Secure secret storage on {platform} has not passed real-device verification; "
        "Home Assistant is disabled and plaintext tokens will not be stored.",
        "{platform} の安全な秘密情報保管は実機検証が未完了です。Home Assistant 接続を停止し、"
        "平文トークンは保存しません。",
    ),
    "請先填入連線位址。": translations(
        "请先填写连接地址。",
        "Enter the connection address first.",
        "接続先アドレスを先に入力してください。",
    ),
    "無法安全保存權杖：{error}": translations(
        "无法安全保存令牌：{error}",
        "Could not securely store the token: {error}",
        "トークンを安全に保存できませんでした：{error}",
    ),
    "設定已保存": translations("设置已保存", "Settings saved", "設定を保存しました"),
    "Home Assistant 尚未啟用": translations(
        "Home Assistant 尚未启用",
        "Home Assistant is not enabled",
        "Home Assistant は有効ではありません",
    ),
    "尚未保存 Home Assistant 權杖": translations(
        "尚未保存 Home Assistant 令牌",
        "No Home Assistant token has been saved",
        "Home Assistant トークンが保存されていません",
    ),
    "連線失敗：{error}": translations(
        "连接失败：{error}", "Connection failed: {error}", "接続に失敗しました：{error}"
    ),
    "連線正常": translations("连接正常", "Connection healthy", "接続は正常です"),
    "API 回應不正確": translations(
        "API 响应不正确", "Unexpected API response", "API 応答が正しくありません"
    ),
    "讀取失敗：{error}": translations(
        "读取失败：{error}", "Read failed: {error}", "読み取りに失敗しました：{error}"
    ),
    "未發現離線或低電量裝置": translations(
        "未发现离线或低电量设备",
        "No offline or low-battery devices found",
        "オフラインまたは低バッテリーの機器はありません",
    ),
    "已讀取 {count} 個可用項目。{issues}": translations(
        "已读取 {count} 个可用项目。{issues}",
        "Loaded {count} available items. {issues}",
        "利用可能な項目を {count} 件読み取りました。{issues}",
    ),
    "{name} 目前{state}": translations(
        "{name} 目前{state}",
        "{name} is currently {state}",
        "{name} の現在の状態：{state}",
    ),
    "{name} 電量只剩 {value}": translations(
        "{name} 电量仅剩 {value}",
        "{name} has only {value} battery remaining",
        "{name} のバッテリー残量は {value} です",
    ),
})

__all__ = ("CLOUD_HOME_TRANSLATIONS",)
