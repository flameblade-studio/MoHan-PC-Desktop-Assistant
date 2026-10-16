### 鎖定墨寒角色包並驗證公開素材一致性／锁定墨寒角色包并验证公开素材一致性／Lock the MoHan character pack and verify public-asset parity／墨寒キャラクターパックを固定し公開素材との一致を検証

- 新增可重現角色包鎖定、逐檔差異報告與無密鑰一致性工作，既有執行期與公開素材維持不變／新增可重现角色包锁定、逐文件差异报告和无密钥一致性工作，现有运行时与公开素材保持不变／Add a reproducible character-pack lock, per-file drift reports, and a credential-free consistency job while preserving the runtime and public assets／再現可能なキャラクターパック固定、ファイル単位の差分報告、資格情報不要の整合性ジョブを追加し既存ランタイムと公開素材を維持
- 新增免金鑰的公開 Release 下載器，完整核對封存檔與角色包後才原子安裝／新增免密钥的公开 Release 下载器，完整核对归档和角色包后才原子安装／Add a credential-free public Release fetcher that installs atomically only after complete archive and pack validation／資格情報不要の公開 Release 取得器を追加し、アーカイブとパックの完全検証後にのみ原子的に導入
