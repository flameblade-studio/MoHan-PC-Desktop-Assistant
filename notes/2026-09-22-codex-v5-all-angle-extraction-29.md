# V5 全身統一衣裝與原生外觀隔離抽取，第 29 階段

Session：`codex-20260922-v5-all-angles-extraction-29`。起點為協作 revision 163、無鎖，重新執行 status → verify → claim 後才寫入。專案 branch 為 `integration/worktree-consolidation-20260916`，HEAD `3fe2b7dd5a03bebf92b90ba6be1b0e5e6c79a009`；開輪已有大量未提交工作，本階段未清除或覆寫。

## 實際成果與邊界

- 左側五角與正側六角均已在 `scratchpad/mohan-v5-hanfu-unified-all-164/stage-left-29-v3/`、`stage-right-29/` 隔離抽取 1024×1536 RGBA 衣層、L 二值 visibility 及原生 V5 手部候選。source-bound 保護、尺寸、模式與 SHA 檢查通過。逐張目視在頸口、裸肩、袖手或遠手處仍有缺陷，11/11 未通過外觀審核，正式安裝 0。這些檢查不是正式 runtime 驗收。
- −090 使用已採用的 +090 灰藍衣布與原生 V5 −090 頭，手部明確借用已採用 +090 的 V5 手支援鏡像（不是 −090 原圖的來源精確手）。`stage-minus090-29-v4/receipt.json` SHA `cd60504acbe9f23167f0a144f93996114f4848a5035cea94c221a62dcf85f6d1`。第一次 source-exact −090 手導致明顯衣袖黑洞，保留在 v1/v2 診斷而不採用。v4 經真 renderer 隔離渲染 52 張、機械失敗 0，`isolated-minus090-runtime-29-v2/validation.json` SHA `f36b045c0785f534b80793fa3f7a56c14d435a22870efbc8f51eddd69025ed37`；視覺仍有頸口／肩帶、原生灰色髮緣問題，未安裝。
- −090 隔離衣裝下，官方銀飾 on/off 的頭部差 657 像素、off 1 層／on 2 層，`headwear-probe.json` SHA `fc019483ceb573e5ac54d5df929793ea27e277ac7d5071bfd252c003ce561674`。這只證明隔離衣裝解除該角舊衣裝的整幀 fail-closed；正式髮飾切換仍未結案。
- −165 以原生 V5 頭手及灰藍背面衣料建立可拆隔離圖層與來源綁定，`stage-minus165-29/receipt.json` SHA `1d3f5a57e1ff989f74fdf9135b6d4f8f17a53adf31e146d3708159f8bd48122a`。真 renderer 隔離渲染 52 張、機械失敗 0，`isolated-minus165-runtime-29/validation.json` SHA `d011dfd38ca8ff1451b357e4b2266c4b13000685f9797440cda68ac2b8a4202c`。目視見左腰帶細缺口；姿態來源本身近正背，未宣稱 −165 透視已通過外觀驗收或正式安裝。
- 新的 −075、−105、−120 對位衣裝來源只作候選。−075 原圖 SHA `10157f198c819c60e830649227f22c5e6dc280f955c23de7d950a87774577c15`；領口比舊候選改善，原生 V5 手縮放、原尺寸及只移動衣袖均有袖口接合問題，最後一版裸縫約 17.788 px，超出 12 px 上限。−105 原圖 SHA `104a7fbdf46417789dfab2d9347246e33e56207095face0d895b67e5d89ac9fa`；−120 原圖 SHA `fc4e4f04a22a82e84f4fa2f35838d12bb61043cd8f558e06f9746f878b1ca45b`。兩張皆以離線 BiRefNet HR 去背，程序退出碼 0、來源 RGB 保留、alpha 0–255 256 階、邊框非零 0。隔離抽取後雖有較好的領口，仍因手旁深灰殘片、陰影與硬袖口目視退件。診斷指出舊 graft 用面積比將原生手縮至 0.7465／0.6656，二值遮罩加 `INTER_NEAREST` 遺失原生柔邊，且衣縫填補把 934／490 個生成手膚色像素填回衣料。不得把去背或原生 RGB 保留宣稱成外觀通過。
- +075 嘗試鏡像 −075 新來源仍有頸前白縫、硬邊，遠手沒有可信原生遮罩；隔離退件，見 `stage-right-29/mirror-075-29/REVIEW.md`。
- +090 銀飾隔離修正對既有正式 pack 只裁去與臉保護區相撞的 20 個 alpha 像素（bbox x560–563,y214–234），詳見 `stage-plus090-headwear-29/receipt.json`。隔離包 `inspect_outfit_pack` 通過；正式 renderer 搭配僅本程序生效的 suppress 覆寫做 on/off，差異 1909 像素全落在銀飾 alpha 內、保護區 0。這不是正式包安裝或擁有者外觀採用；原生髮緣灰邊與既有妝容貼片仍可見。
- 另定位 −090 classic/glamorous 既有正式妝容刮痕：眼妝圖層 bbox x524–567,y240–260，真正眼孔 x568–582,y224–233，零重疊。無妝影格無刮痕；妝容包與正式 pack SHA 一致，問題不是本階段衣裝引入。移位的隔離候選雖移除粗黑條，仍有眼旁虛線與臉頰／下巴貼片，暫不具安裝品質。
- 外部原圖三個歷史缺口已在 session 22 找回並正式封存。本階段唯讀重核正式 `SOURCE-PROVENANCE.json` 與收據相符：22 個 external exact、2 個擁有者採用側身 profile，`external_raw_source_gaps=[]`。沒有將 Git blob 冒充外部原圖。

## 尚未完成

擁有者本輪貼圖可與 `scratchpad/mohan-v5-hanfu-unified-all-164/yaw-090-pitch+00.hanfu-front-style-candidate-01.png` 逐位元吻合（SHA-256 `30a76ab0cb1c406e36fdfeb584c77e3d26ab1d5bcf6f32bf2615b73f855b9edb`），並明確表示「這張特別不像」。因此該整張生成候選記錄為人物外觀退件，見 `owner-rejection-yaw-090-candidate-01.json`。正式 visibility manifest 僅有 +090、−180，此 −090 候選未正式安裝。隔離 −090 v4 使用原生 V5 −090 頭部、已採用 +090 衣料鏡像及 V5 手部支援；v4 的機械渲染通過仍不代表擁有者採用，頸袖接縫仍須修正。

13 個全身角度的灰藍衣裝統一、逐角擁有者外觀判斷、正式原子安裝與 24 角聯合重載均未完成；正式 6 個裸素體回退角度不變。±090 原生髮緣灰邊、+090 銀飾保護區碰撞、正式 ±090 妝容貼片仍待修。七半身 V7、七姿勢可拆漢服與已正式安裝的 +090／−180 衣裝維持原狀。本階段未 commit、PR、merge、release 或 tag。

本階段全專案 `.venv315/Scripts/python.exe -m ruff check .` 退出碼 0。此檢查只驗證 Python 靜態規則，不替代角度外觀驗收。
