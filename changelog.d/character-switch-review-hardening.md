### 加固角色切換邊界／加固角色切换边界／Harden character-switching boundaries／キャラクター切替境界を強化

- 由作用中角色來源提供已驗證的全身與半身渲染素材，缺少必要素材時明確拒絕載入／由活动角色来源提供已验证的全身与半身渲染素材，缺少必要素材时明确拒绝加载／Use the active character source for validated full-body and half-body rendering assets, and reject missing required assets explicitly／有効なキャラクターソースから検証済みの全身と半身の描画素材を取得し、必須素材がない場合は明示的に拒否します
- 由作用中角色建立新設定檔的名稱、人格、事件台詞與聲音預設，並保留使用者已儲存的覆寫值／由活动角色建立新配置文件的名称、人格、事件台词与声音默认值，并保留用户已保存的覆盖值／Initialize new profiles with the active character's name, persona, event dialogue, and voice defaults while preserving saved user overrides／有効なキャラクターの名前、人格、イベント台詞、音声を新規プロファイルの既定値にし、保存済みの利用者上書きを保持します
- 保留所有內建與已安裝角色的官方外觀包識別碼，避免角色往返切換後發生衝突／保留所有内置与已安装角色的官方外观包标识符，避免角色往返切换后发生冲突／Reserve official appearance-pack identifiers across all built-in and installed characters to prevent round-trip switching conflicts／すべての組み込みおよびインストール済みキャラクターの公式外観パック識別子を予約し、往復切替後の衝突を防ぎます
- 以私有快照完成角色封包驗證與解壓，並在發布前核對來源與 staged package hash／以私有快照完成角色包验证与解压，并在发布前核对来源与 staged package hash／Validate and extract character archives from a private snapshot, then verify the source and staged package hash before publication／非公開スナップショットでキャラクターアーカイブを検証して展開し、公開前に取得元と staged package hash を照合します
