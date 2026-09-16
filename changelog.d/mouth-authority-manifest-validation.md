### 修正嘴型中心資料驗證／修正嘴型中心数据验证／Fix mouth authority metadata validation／口形状の参照データ検証を修正

- 只採用格式正確且版本為整數的嘴型資料容器；布林值、非有限值及畫布外座標維持在有效輸入契約之外，其他有效視角持續保留，載入與嘴型位置維持穩定。／仅采用格式正确且版本为整数的嘴型数据容器；布尔值、非有限值及画布外坐标维持在有效输入契约之外，其他有效视角持续保留，加载与嘴型位置维持稳定。／Use well-formed mouth metadata containers with integer versions; keep boolean, non-finite and out-of-canvas centers outside the accepted input contract, retain other valid views, and keep loading and mouth placement stable.／形式が正しくバージョンが整数の口形状メタデータだけを使用し、真偽値・非有限値・キャンバス外の中心座標は受け入れ対象外として扱います。有効な他の視点を保持し、読み込みと口形状の配置を安定させます。
