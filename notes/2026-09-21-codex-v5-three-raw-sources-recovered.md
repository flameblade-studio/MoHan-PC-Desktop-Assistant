# V5 三個全身外部原圖缺口結案（2026-09-21）

本輪 session `codex-20260921-v5-provenance-followup-22`。前一輪七姿勢漢服正式接入與 336 張 runtime 驗證維持原狀。本輪只處理 `yaw+045-pitch+00`、`yaw-045-pitch+00`、`yaw-060-pitch+00` 的來源血緣；正式 PNG 像素沒有改動。

## 來源與比對

先前只掃描擁有者 V5 素顏資料夾及一個生成批次，留下三個 Git blob 等級缺口。本輪另掃描擁有者桌面專案資料夾 2,258 張影像（其中 603 張同尺寸，0 筆精確命中，1 筆無關圖片解碼失敗），以及本機 `C:\Users\USERNAME\.codex\generated_images` 的 1,914 張影像（997 張同尺寸，三個缺口各有 1 筆精確命中，0 筆解碼失敗）。搜尋紀錄分別在 `scratchpad/mohan-v2-final-runtime-matrix-160/desktop-external-raw-search-22.json` 與 `generated-cache-external-raw-search-22.json`。兩次掃描的退出碼均為 0。

三張原始 PNG 為 RGB、1024×1536，已逐位元組複製封存至 `scratchpad/mohan-v2-final-runtime-matrix-160/recovered-external-raw-22/`，複製前後 SHA-256 一致：

| 角度 | 封存原圖 SHA-256 | 正式圖完全不透明像素數 | RGB 差異像素 |
| --- | --- | ---: | ---: |
| `yaw+045-pitch+00` | `71e05a50ec81b9f1c7d68ad6d86d23e20ac5523002f4f5c115ad8ae9e1c47c7e` | 222,832 | 0 |
| `yaw-045-pitch+00` | `3353338de591d913df4fdb5df236843b3367ec59251c28a23ef44157455cf787` | 228,672 | 0 |
| `yaw-060-pitch+00` | `4eb872e817ed1a88e9c87849619241516f86baee4e25d3c7735ee6970a6cdda8` | 197,022 | 0 |

比對方式是對正式 RGBA 中 alpha=255 的所有像素逐點比對 RGB；這不主張半透明邊界或整張檔案完全相同。正式圖 SHA-256 在更新前後未改動，原 Git commit/blob 證據保留在新的 authority 紀錄。來源快取目錄只以相對 locator 寫入正式清單；封存副本可在專案中獨立重驗。

## 正式安裝與回歸

`close_three_raw_sources_22.py` 對三張封存原圖重新做全量不透明像素比對，退出碼 0；預檢 `approved_asset_install.py` 的兩個目標，退出碼 0；原子安裝 `SOURCE-PROVENANCE.json`、`BUILD-METADATA.json`，退出碼 0，receipt 在 `scratchpad/mohan-v2-final-runtime-matrix-160/raw-source-recovery-install-22/receipt.json`，SHA-256 `74547a94bfd649da539550785e78c1e7a9d56a1851aade92b03e9db01992b126`。安裝後正式來源清單 SHA-256 `2da3b50e675ad9182766590c21016213ecd659a10f70b01c21ea2cc5c82fa266`，建置中繼資料 SHA-256 `bedea6f9e27a6878b2cac158fd67ee80762680c7dbd3d1e5102fce82d61820a0`。

來源契約、全身資產證據、PNG 完整性、生成血緣、核准安裝相關 pytest 共 25 passed，退出碼 0。新腳本 Ruff 退出碼 0。全專案 Ruff 退出碼 1，僅六個既有 `.pytest-v5-*` 測試暫存 `probe.py`／`product.py` 的 `unused-import`；未變更或刪除那些既有暫存檔。

目前 24 個正式全身角度的來源等級為 22 個外部原圖不透明 RGB 精確吻合、2 個 ±90° 擁有者採用及安裝收據，外部原圖缺口為 0。此結論是技術來源血緣，並不把兩個 ±90° 說成有外部原圖，也不等同新的美術驗收或軟體發佈。
