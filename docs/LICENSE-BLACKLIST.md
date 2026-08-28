# 墨寒專案授權黑名單（禁用・禁下載・禁引入）

擁有者 2026-08-28 裁決：任何授權有疑慮的生產工具，即使閒置未用也不得留在本機；下列項目**禁止下載、禁止安裝、禁止以任何形式進入產線**。本名單與白名單（MIT／Apache 2.0／CC0／CC BY＋BSD 等同級）互為表裡；不在白名單者一律先查證再引入，查證不過即入此名單。

## 工具類（禁裝禁用）

| 項目 | 授權 | 裁決 |
|---|---|---|
| ComfyUI | GPL-3.0 | 擁有者明令完全出局，不列任何備援（2026-08-28）；本機舊副本已刪除 |
| Stable Diffusion WebUI Forge／reForge／SD.Next | AGPL-3.0 | 比 GPL 更強傳染，禁用 |
| SwarmUI | MIT 殼＋ComfyUI 後端 | 心臟是 ComfyUI，一併禁用 |
| nvdiffrast | NVIDIA Source Code License（非商用） | 2026-08-28 盤點揪出，本機已刪除 |
| OpenPose 官方實作 | CMU 學術授權（商用年費 US$25k） | 骨架萃取改用 DWPose／RTMPose／MediaPipe（Apache） |

## 模型權重類（禁下載）

| 項目 | 授權 | 裁決 |
|---|---|---|
| FLUX.1-dev／FLUX.2-dev／FLUX.2-klein-9B 及其一切衍生模型 | flux-1-dev-non-commercial | 非商用傳染整個衍生樹 |
| XLabs／InstantX／Shakker-Labs／Jasper 的 Flux ControlNet 全系 | flux-1-dev-non-commercial（dev 衍生） | 2026-08-28 盤點確認全滅，一顆未下載 |
| Illustrious-XL／NoobAI-XL | Fair AI Public License（copyleft） | 禁用 |
| Pony Diffusion 系 | 附加商用限制 | 禁用 |
| SD3／SD3.5 | Stability Community License | 非白名單，禁用 |
| Hunyuan 影像系 | Tencent Community License | 非白名單，禁用 |

## 素材類（禁入資產鏈）

| 項目 | 裁決 |
|---|---|
| CC BY-SA | 擁有者裁決徹底移除（share-alike 傳染＋盡調成本） |
| CC BY-NC／CC BY-ND 系 | 非商用／禁改作，禁入 |
| 來源或授權不明之任何素材 | 依既有治理：不得進入正式封裝 |

## 例外欄（白名單外但經裁決許可）

| 項目 | 授權 | 理由 |
|---|---|---|
| PySide6 | LGPL-3.0 | App 執行期 UI 框架；onedir 動態連結＋About 聲明＋授權全文隨包（PR #95 完成合規三件套） |
| PyInstaller | GPL-2.0＋bootloader exception | 例外條款明文保證打包產物不受 GPL 約束；建置工具不進產物 |
| Azure Speech SDK | Microsoft 專有（可商用可再散布） | 平台 SDK，不傳染、不禁商用 |
