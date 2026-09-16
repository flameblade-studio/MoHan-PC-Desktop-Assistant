### 妝容設定並行一致性與容錯／妆容设置并行一致性与容错／Concurrent makeup settings consistency and recovery／メイク設定の並行整合性と復旧

* 以設定鎖保護整體與個別妝容濃度的讀改寫，讓平行滑桿更新各自保留。／使用设置锁保护整体与单项妆容浓度的读改写，让并行滑块更新各自保留。／Protect read-modify-write updates for overall and per-slot makeup intensity with a settings lock so each parallel slider update is retained.／設定ロックで全体とスロット別のメイク濃度の読み取り・変更・書き込みを保護し、並行スライダー更新をそれぞれ保持します。
* 未設通知 callback 的讀取失敗會保留後續通知；超大 JSON 整數會安全回退至上一個有效值。／未设置通知 callback 的读取失败会保留后续通知；超大 JSON 整数会安全回退到上一个有效值。／A read that has no notification callback preserves the later notification when it fails, and oversized JSON integers safely fall back to the last valid value.／通知 callback を設定していない読み取りが失敗した場合も後続通知を保持し、巨大な JSON 整数は直前の有効値へ安全にフォールバックします。
