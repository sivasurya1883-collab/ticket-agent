from __future__ import annotations

import time


def stream_text(text: str, chunk_size: int = 18, delay_s: float = 0.01):
    t = text or ""
    for i in range(0, len(t), chunk_size):
        yield t[i : i + chunk_size]
        time.sleep(delay_s)
