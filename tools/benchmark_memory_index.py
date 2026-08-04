from __future__ import annotations

import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_index import MemoryVectorIndex


def main() -> None:
    now = datetime.now().isoformat(timespec="seconds")
    rows = [
        {
            "id": index,
            "category": "工作流程",
            "title": f"專案項目 {index}",
            "content": f"墨寒本機長期記憶效能資料 token-{index * 7919}",
            "importance": (index % 5) + 1,
            "updated_at": now,
        }
        for index in range(1, 1001)
    ]
    index = MemoryVectorIndex()
    index.rank("建立暖索引", rows, 24)
    samples: list[float] = []
    for sequence in range(100):
        started = time.perf_counter()
        index.rank(f"墨寒記憶專案 {sequence * 17}", rows, 24)
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print(
        "MEMORY_INDEX_BENCHMARK_OK "
        f"mean_ms={statistics.mean(samples):.2f} "
        f"p95_ms={p95:.2f} max_ms={max(samples):.2f}"
    )


if __name__ == "__main__":
    main()
