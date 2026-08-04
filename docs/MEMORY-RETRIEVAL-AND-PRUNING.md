# Long-term memory retrieval and safe pruning

## 繁體中文

墨寒會在本機建立確定性、離線的多語文字向量索引。文字問答只取回與本次問題最相關的記憶，並綜合重要度與最近使用時間排序；記憶內容不會為了建立索引而傳送到第三方服務。

索引採延遲建立與內容指紋快取。新增、編輯、刪除或還原記憶後會自動失效，下次查詢才重建。1,000 則記憶的暖索引基準測試納入測試工具，目標維持互動所需的毫秒級回應。

自動整理只處理來源為對話、重要度 1–2 的記憶：

- 語意高度近似的內容會以可追溯的文字片段合併。
- 超過 500 則時，才會把 90 天以上未使用的低重要度對話記憶整理至 400 則。
- 手動保存、重要度 3–5、人物與其他受保護內容不會因容量自動移除。
- 自動整理不是永久刪除；原始快照會進入本機封存區，可由「查看已封存記憶」還原。

## 简体中文

墨寒会在本机建立确定性、离线的多语言文字向量索引。文字问答只取回与当前问题相关的记忆，并结合重要度与最近使用时间排序；建立索引不会把记忆上传到第三方服务。

自动整理只处理来源为对话、重要度 1–2 的内容。超过容量时，仅封存 90 天以上未使用的低重要度对话记忆；手动保存及重要度 3–5 的记忆不会被自动移除。所有自动整理内容都会先保存本机快照，并可从封存界面还原。

## English

MoHan builds a deterministic, offline multilingual text-vector index on the local computer. Text conversations retrieve only memories relevant to the current query, with importance and recency used as secondary ranking signals. Memory content is not sent to a third-party embedding service.

The index is lazy and fingerprint-cached. Memory changes invalidate it, and the next query rebuilds only changed entries. A warm-index benchmark for 1,000 memories is included to preserve interactive, millisecond-scale retrieval.

Automatic maintenance is deliberately conservative. It considers only conversation-sourced memories with importance levels 1–2. Capacity pruning starts above 500 active memories and archives eligible items older than 90 days until the active set reaches 400. Manual memories and importance levels 3–5 are protected. Every automatically removed record is stored as a recoverable local snapshot and can be restored from the archive dialog.
