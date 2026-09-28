# V5 藍白漢服五姿勢正式接入

日期：2026-09-21

## 決定與來源

擁有者已採用五張 V5 藍白漢服候選。候選集合 SHA-256 為
`19b7c719974bafacf932ec8b4286a15cbae3e5f50031103fc0fb9b318066888c`，
採用紀錄 SHA-256 為
`697c4266ecdacfa5edba1c0c54b07a7baa018073fa9bb11e25a715ec421ef0eb`。

五個目標姿勢為 `front-crossed`、`left-neutral`、`front-mock-scold`、
`front-mock-hit` 與 `front-exasperated`。候選臉部存在已量測的生成差異，
因此正式層只取衣裝；runtime 的臉、髮與手始終使用
`scratchpad/mohan-v2-v5-seven-pose-matting-146/local-alpha-01/` 的原生 V5 RGBA。

## 抽取與隔離驗收

離線 BiRefNet HR 去背完成，收據在
`scratchpad/mohan-v5-hanfu-five-candidates-161/dressed-matting-01/receipt.json`，
記錄 exit code 0、五張 1254×1254 RGBA 與 soft alpha。抽取物為全畫布
`garment.rgba.png` 與灰階 `body-visibility.png`，正式層沒有候選臉、髮或手。

`isolated-staging-07/validation.json` 實際使用正式 runtime 類別渲染七姿勢、
四嘴型、三眼態、四妝容，共 336 張，0 failures。新五姿勢對素顏 runtime
face ROI 精確不變；既有 `cheek-rest` 與 `front-eureka` 對正式 renderer 基線
逐像素一致。

## 正式安裝與回歸

安裝計畫：`formal-installation-plan.json`。`approved_asset_install.py` 的預檢
16 個目標 exit code 0，原子安裝 16 個目標 exit code 0。receipt：
`formal-installation-03/receipt.json`，SHA-256
`a3df240712f0ef2a0ab7151487435823eb7971202c672797998d6da73231ffd4`。

正式 renderer 重載後，`formal-runtime-validation-08/validation.json` 渲染
336 張、0 failures，SHA-256
`896026e6e1767256c236b028e0fcf0a929b0709516a45a8b2bb70405701af51f`。
`tests/test_reviewed_garment_assets.py` 與
`tests/test_reviewed_garment_overlay.py` 使用 scratchpad basetemp 重跑，21 passed。

## 未解項

本輪唯讀搜尋未找回 `yaw+045-pitch+00`、`yaw-045-pitch+00`、
`yaw-060-pitch+00` 的外部原圖。三者維持 `git_history_authority`，不冒稱
外部原圖已封存。
