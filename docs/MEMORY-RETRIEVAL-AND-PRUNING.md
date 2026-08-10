# 長期記憶檢索與安全剪枝／长期记忆检索与安全剪枝／Long-Term Memory Retrieval and Safe Pruning／長期記憶の検索と安全な剪定

## 繁體中文

墨寒會在本機建立確定性、離線的多語文字向量索引。文字問答只取回與本次問題
最相關的記憶，並綜合重要度與最近使用時間排序；記憶內容不會為了建立索引而
傳送到第三方服務。

索引採延遲建立與內容指紋快取。新增、編輯、刪除或還原記憶後會自動失效，
下次查詢才重建。1,000 則記憶的暖索引基準測試納入測試工具，目標維持互動
所需的毫秒級回應。

自動整理只處理來源為對話、重要度 1–2 的記憶：

- 語意高度近似的內容會以可追溯的文字片段合併。
- 超過 500 則時，才會把 90 天以上未使用的低重要度對話記憶整理至 400 則。
- 手動保存、重要度 3–5、人物與其他受保護內容不會因容量自動移除。
- 自動整理不是永久刪除；原始快照會進入本機封存區，可由「查看已封存記憶」還原。

## 简体中文

墨寒会在本机建立确定性、离线的多语言文字向量索引。文字问答只取回与当前问题
最相关的记忆，并综合重要度与最近使用时间排序；记忆内容不会为了建立索引而
发送到第三方服务。

索引采用延迟建立与内容指纹缓存。新增、编辑、删除或还原记忆后，索引会自动失效，
直到下次查询时才重建。测试工具包含 1,000 条记忆的暖索引基准测试，目标是维持
交互所需的毫秒级响应。

自动整理只处理来源为对话、重要度 1–2 的记忆：

- 语义高度近似的内容会使用可追溯的文字片段合并。
- 超过 500 条时，才会把 90 天以上未使用的低重要度对话记忆整理至 400 条。
- 手动保存、重要度 3–5、人物与其他受保护内容不会因为容量而自动移除。
- 自动整理不是永久删除；原始快照会进入本机归档区，可从“查看已归档记忆”还原。

## English

MoHan builds a deterministic, offline multilingual text-vector index on the local computer.
Text conversations retrieve only memories most relevant to the current query and combine
importance with most-recent use for ranking; memory content is not sent to a third-party
service to build the index.

The index is built lazily and uses content-fingerprint caching. Adding, editing, deleting,
or restoring a memory automatically invalidates it, and it is rebuilt only on the next query.
The test tools include a warm-index benchmark for 1,000 memories, with a target of preserving
the millisecond-scale response required for interaction.

Automatic maintenance processes only conversation-sourced memories with importance levels 1–2:

- Semantically very similar content is merged with traceable text fragments.
- Only when the active set exceeds 500 memories are low-importance conversation memories unused
  for more than 90 days reduced until 400 remain.
- Manually saved memories, importance levels 3–5, people, and other protected content are not
  automatically removed because of capacity.
- Automatic maintenance is not permanent deletion; original snapshots enter a local archive and
  can be restored through “View archived memories.”

## 日本語

墨寒は、ローカル環境に決定的かつオフラインの多言語テキストベクトル索引を
構築します。テキスト対話では現在の質問に最も関連する記憶だけを取得し、重要度と
直近の利用時刻を組み合わせて順位付けします。索引を構築するために記憶内容を
第三者サービスへ送信することはありません。

索引は遅延構築と内容フィンガープリントのキャッシュを使用します。記憶を追加、編集、
削除、復元すると索引は自動的に無効化され、次回の問い合わせ時にだけ再構築されます。
テストツールには 1,000 件の記憶を対象とするウォーム索引ベンチマークが含まれ、
対話に必要なミリ秒単位の応答を維持することを目標とします。

自動整理が処理するのは、対話を出所とする重要度 1–2 の記憶だけです：

- 意味が非常に近い内容は、追跡可能なテキスト断片を用いて統合されます。
- 500 件を超えた場合に限り、90 日を超えて使われていない重要度の低い対話記憶を
  400 件になるまで整理します。
- 手動保存、重要度 3–5、人物、その他の保護対象は、容量を理由に自動削除されません。
- 自動整理は永久削除ではありません。元のスナップショットはローカルアーカイブに入り、
  「アーカイブ済み記憶を表示」から復元できます。
