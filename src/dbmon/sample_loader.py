from __future__ import annotations

import json
from typing import Iterable


def read_jsonl(path: str) -> list[dict]:
    events = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            events.append(json.loads(line))
    return events


def chunked(items: list[dict], size: int = 200) -> Iterable[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
