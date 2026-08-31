# Candidate3 formal-controls bundle

這是 geometry control 隔離包，不是正式美術。它不改動舊 controls，只把已驗證的反號映射複製為正式 view-id 檔名。

映射規則：`source_renderer_yaw = -formal_yaw`；formal `-180` 使用 source `-180`。

嚴格閘門：

- 24 個正式 view-id。
- 每視角 silhouette/depth/normal 三檔。
- 精確 72 個 PNG。
- 全部 1024×1536。
- silhouette/depth 為 `L`，normal 為 `RGB`。
- 每個複製檔 SHA-256 必須等於對應來源。
- 任一缺檔、多檔、檔名、尺寸、mode 或 hash 錯誤即 exit 4。
