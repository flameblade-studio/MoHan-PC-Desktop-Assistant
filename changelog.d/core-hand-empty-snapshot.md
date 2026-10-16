### 固定沒有手部遮罩的組裝狀態／固定没有手部遮罩的组装状态／Preserve absent hand-mask snapshots／手部マスクがない状態を固定

- 組裝入口已確認沒有手部遮罩時，所有合成器共用該結果；稍後新增遮罩須重新建立組裝入口才生效。直接建立合成器且未指定提供者時仍自動載入。／组装入口已确认没有手部遮罩时，所有合成器共用该结果；稍后新增遮罩须重新建立组装入口才生效。直接建立合成器且未指定提供者时仍自动加载。／All compositors share a composition root's confirmed absence of hand masks. Masks added later take effect after rebuilding the composition root. Direct construction still loads masks automatically when no provider is supplied.／組み立て入口で手部マスクがないと確認した結果を全合成器で共有します。後から追加したマスクは組み立て入口の再作成後に反映されます。提供元を指定せず合成器を直接作成する場合は引き続き自動読み込みします。
