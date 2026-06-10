from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    raise TypeError(f"Unsupported received_at value: {value!r}")


def _get_field(message: Any, field: str) -> Any:
    if isinstance(message, Mapping):
        return message[field]
    return getattr(message, field)


def compute_backlog_metrics(
    messages: Iterable[Any],
    vip_senders: Iterable[str] | None = None,
    now: datetime | date | str | None = None,
    history_unread_counts: Iterable[int] | None = None,
) -> dict[str, int]:
    current_time = _to_datetime(now or datetime.utcnow())
    vip_set = set(vip_senders or [])

    unread_count = 0
    vip_unread_count = 0
    oldest_unread_age_days = 0
    oldest_unread_seen = None

    for message in messages:
        unread = bool(_get_field(message, "unread"))
        if not unread:
            continue

        unread_count += 1
        sender = _get_field(message, "sender")
        if sender in vip_set:
            vip_unread_count += 1

        received_at = _to_datetime(_get_field(message, "received_at"))
        age_days = (current_time.date() - received_at.date()).days
        if oldest_unread_seen is None or age_days > oldest_unread_seen:
            oldest_unread_seen = age_days
            oldest_unread_age_days = age_days

    history = list(history_unread_counts or [])
    backlog_trend_7d = history[-1] - history[0] if len(history) >= 2 else 0

    return {
        "unread_count": unread_count,
        "oldest_unread_age_days": oldest_unread_age_days,
        "backlog_trend_7d": backlog_trend_7d,
        "vip_sender_unread_count": vip_unread_count,
    }


def build_report(
    messages: Iterable[Any],
    vip_senders: Iterable[str] | None = None,
    now: datetime | date | str | None = None,
    history_unread_counts: Iterable[int] | None = None,
) -> dict[str, Any]:
    current_time = _to_datetime(now or datetime.utcnow())
    metrics = compute_backlog_metrics(
        messages=messages,
        vip_senders=vip_senders,
        now=current_time,
        history_unread_counts=history_unread_counts,
    )
    return {
        "factory": "df-159",
        "domain": "OPS",
        "generated_at": current_time.isoformat(),
        **metrics,
    }


def write_report(
    report: Mapping[str, Any],
    report_dir: str | Path = "reports",
    now: datetime | date | str | None = None,
) -> Path:
    current_time = _to_datetime(now or datetime.utcnow())
    target_dir = Path(report_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"df-159-{current_time.date().isoformat()}.json"
    target_path.write_text(json.dumps(dict(report), indent=2, sort_keys=True), encoding="utf-8")
    return target_path


def should_stop(stop_flag: str | Path = "/tmp/df-159.stop") -> bool:
    return Path(stop_flag).exists()
# [CRUX-MK]
