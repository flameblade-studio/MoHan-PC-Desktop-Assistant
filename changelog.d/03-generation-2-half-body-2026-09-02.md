### 未發布 — 半身素體二代（2026-09-02）

* 半身素體重製為二代素顏版：`assets/expressions/` 下 113 張表情、75 張分層與 21 張 `v120_*` 物理切層全部由工作室自有產線自 `assets/pose-atlas/v5-base/` 重新生成，不再含一代外部授權美術；外袍、髮型、髮飾與妝容改為執行期圖層。`v120_*` 的頭髮、袖子與髮飾切層依契約為全透明（`tests/test_v120_asset_integrity.py` 的 `LICENSED_EMPTY`），臉部偏移表改為實測值；無程式載入的 `physics_*` 與 `skeptical_front.png` 共 22 張已移除。

### 未发布 — 半身素体二代（2026-09-02）

* 半身素体重制为二代素颜版：`assets/expressions/` 下 113 张表情、75 张分层与 21 张 `v120_*` 物理切层全部由工作室自有产线自 `assets/pose-atlas/v5-base/` 重新生成，不再包含一代外部授权美术；外袍、发型、发饰与妆容改为运行时图层。`v120_*` 的头发、袖子与发饰切层按契约为全透明（`tests/test_v120_asset_integrity.py` 的 `LICENSED_EMPTY`），脸部偏移表改为实测值；无程序加载的 `physics_*` 与 `skeptical_front.png` 共 22 张已移除。

### Unreleased — generation-2 half-body base (2026-09-02)

* The half-body base is regenerated bare-faced on generation 2: the 113 expressions, 75 layers and 21 `v120_*` physics cutouts under `assets/expressions/` are all rebuilt by the studio's own pipeline from `assets/pose-atlas/v5-base/` and no longer contain generation-1 externally licensed artwork; robe, hairstyle, hairpiece and makeup are now runtime layers. The `v120_*` hair, sleeve and ornament cutouts are fully transparent by contract (`LICENSED_EMPTY` in `tests/test_v120_asset_integrity.py`), the face-offset tables now hold measured values, and the 22 `physics_*` and `skeptical_front.png` files that no code loaded are removed.

### 未リリース — 半身素体の第二世代化（2026-09-02）

* 半身素体を第二世代の素顔版として作り直しました。`assets/expressions/` 配下の表情 113 枚、レイヤー 75 枚、`v120_*` 物理切り出し 21 枚はすべてスタジオ自前のパイプラインが `assets/pose-atlas/v5-base/` から再生成したもので、第一世代の外部ライセンス美術は含みません。外衣、髪型、髪飾り、化粧は実行時レイヤーになりました。`v120_*` の髪・袖・髪飾りの切り出しは契約上完全に透明で（`tests/test_v120_asset_integrity.py` の `LICENSED_EMPTY`）、顔オフセット表は実測値に更新し、どのコードも読み込まない `physics_*` と `skeptical_front.png` の計 22 枚を削除しました。
