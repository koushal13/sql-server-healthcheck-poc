from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from dbmon.explainer import explain_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_rules(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data.get("rules", [])


def _compare(value: Any, op: str, threshold: Any) -> bool:
    if value is None:
        return False
    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold
    if op == "==":
        return value == threshold
    if op == "!=" :
        return value != threshold
    return False


def evaluate_rules(events: list[dict], rules: list[dict[str, Any]]) -> list[dict]:
    alerts: list[dict] = []
    for event in events:
        payload = event.get("payload", {})
        for rule in rules:
            if event.get("event_type") != rule.get("event_type"):
                continue
            field = rule.get("field")
            op = rule.get("op")
            threshold = rule.get("value")
            if _compare(payload.get(field), op, threshold):
                explanation = explain_event(event)
                alerts.append(
                    {
                        "@timestamp": _now_iso(),
                        "alert_id": rule.get("id"),
                        "severity": rule.get("severity", "medium"),
                        "message": rule.get("message"),
                        "event": event,
                        "explanation": explanation,
                        "recommendations": rule.get("recommendations", []),
                    }
                )
    return alerts
