# 上游貢獻紀錄／上游贡献记录／Upstream contributions／上流への貢献記録

## 繁體中文

### 為什麼有這一頁

墨寒的產線踩到第三方套件的真缺陷時，修好之後多花半小時送回上游，是成本最低、也最誠實的能見度：在別人的場子裡被別人需要。這一頁是唯一的權威清單，每送出一個上游 PR 就在這裡加一列，狀態以上游頁面為準。

### 紀錄

| 日期 | 上游專案 | PR | 內容 | 狀態（2026-09-02） |
|---|---|---|---|---|
| 2026-08-28 | ostris/ai-toolkit | [#1021](https://github.com/ostris/ai-toolkit/pull/1021) | `cache_text_encoder` 缺少裝置預設分支，導致 `BaseModel` 在快取文字編碼器時失敗 | 開啟中 |
| 2026-08-29 | ostris/ai-toolkit | [#1023](https://github.com/ostris/ai-toolkit/pull/1023) | `cache_text_embeddings` 以假文字編碼器取代後，取樣階段直接崩潰；改為略過取樣 | 開啟中 |

### 流程

1. 在第三方套件遇到真缺陷，先在墨寒這邊修好並附迴歸測試。
2. 評估是否可上游：與墨寒無關、上游仍在維護、修法不綁墨寒的假設。
3. 送 PR 時附最小重現與測試，說明踩到的情境。
4. 在本頁加一列；上游合併或關閉時更新狀態。

### 閘門

- 每月至少送出一個上游 PR。
- 每個 PR 都附最小重現。
- 本頁列出全部上游貢獻，沒有例外。

## 简体中文

### 为什么有这一页

墨寒的产线踩到第三方软件包的真缺陷时，修好之后多花半小时送回上游，是成本最低、也最诚实的能见度：在别人的场子里被别人需要。这一页是唯一的权威清单，每送出一个上游 PR 就在这里加一行，状态以上游页面为准。

### 记录

| 日期 | 上游项目 | PR | 内容 | 状态（2026-09-02） |
|---|---|---|---|---|
| 2026-08-28 | ostris/ai-toolkit | [#1021](https://github.com/ostris/ai-toolkit/pull/1021) | `cache_text_encoder` 缺少设备预设分支，导致 `BaseModel` 在缓存文本编码器时失败 | 开启中 |
| 2026-08-29 | ostris/ai-toolkit | [#1023](https://github.com/ostris/ai-toolkit/pull/1023) | `cache_text_embeddings` 以假文本编码器替换后，采样阶段直接崩溃；改为跳过采样 | 开启中 |

### 流程

1. 在第三方软件包遇到真缺陷，先在墨寒这边修好并附回归测试。
2. 评估是否可上游：与墨寒无关、上游仍在维护、修法不绑墨寒的假设。
3. 送 PR 时附最小重现与测试，说明踩到的情境。
4. 在本页加一行；上游合并或关闭时更新状态。

### 闸门

- 每月至少送出一个上游 PR。
- 每个 PR 都附最小重现。
- 本页列出全部上游贡献，没有例外。

## English

### Why this page exists

When MoHan's pipeline hits a real defect in a third-party package, spending half an hour after the fix to send it upstream is the cheapest and most honest form of visibility: being needed in someone else's space. This page is the single authoritative list; every upstream PR gets a row here, and the upstream page is the source of truth for its status.

### Record

| Date | Upstream project | PR | What | Status (2026-09-02) |
|---|---|---|---|---|
| 2026-08-28 | ostris/ai-toolkit | [#1021](https://github.com/ostris/ai-toolkit/pull/1021) | `cache_text_encoder` lacked a device-preset branch, so `BaseModel` failed while caching the text encoder | Open |
| 2026-08-29 | ostris/ai-toolkit | [#1023](https://github.com/ostris/ai-toolkit/pull/1023) | after `cache_text_embeddings` swapped in a fake text encoder, sampling crashed outright; now sampling is skipped | Open |

### Process

1. Hit a real defect in a third-party package, fix it on MoHan's side first with a regression test.
2. Decide whether it can go upstream: unrelated to MoHan, upstream still maintained, fix not tied to MoHan's assumptions.
3. Send the PR with a minimal reproduction and a test, and describe the situation that triggered it.
4. Add a row here; update the status when upstream merges or closes it.

### Gates

- At least one upstream PR per month.
- Every PR carries a minimal reproduction.
- This page lists every upstream contribution, without exception.

## 日本語

### このページがある理由

墨寒のパイプラインがサードパーティ製パッケージの本物の欠陥を踏んだとき、修正後に三十分だけ余分に使って上流へ送ることは、最も安く最も誠実な可視性です。他人の場で他人に必要とされることだからです。このページが唯一の権威ある一覧であり、上流へ PR を送るたびに一行を追加し、状態は上流のページを正とします。

### 記録

| 日付 | 上流プロジェクト | PR | 内容 | 状態（2026-09-02） |
|---|---|---|---|---|
| 2026-08-28 | ostris/ai-toolkit | [#1021](https://github.com/ostris/ai-toolkit/pull/1021) | `cache_text_encoder` にデバイス既定の分岐が無く、`BaseModel` がテキストエンコーダーのキャッシュ時に失敗していた | オープン |
| 2026-08-29 | ostris/ai-toolkit | [#1023](https://github.com/ostris/ai-toolkit/pull/1023) | `cache_text_embeddings` が偽のテキストエンコーダーに差し替えた後、サンプリングがそのままクラッシュしていた。サンプリングを飛ばすように修正 | オープン |

### 手順

1. サードパーティ製パッケージで本物の欠陥を踏んだら、まず墨寒側で回帰テスト付きで修正する。
2. 上流へ送れるか判断する。墨寒に固有でないこと、上流が保守中であること、修正が墨寒の前提に縛られていないこと。
3. PR には最小再現とテストを添え、踏んだ状況を説明する。
4. このページに一行を追加し、上流で取り込みまたは却下されたら状態を更新する。

### 関門

- 毎月少なくとも一件の上流 PR を送る。
- すべての PR に最小再現を添える。
- このページに上流への貢献をすべて列挙し、例外を作らない。
