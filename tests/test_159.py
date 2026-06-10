import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib
import json
from datetime import datetime

m159 = importlib.import_module("159")
from pytest import raises


compute_backlog_metrics = m159.compute_backlog_metrics
build_report = m159.build_report
write_report = m159.write_report
should_stop = m159.should_stop


def test_ops_email_backlog_tracker_core_metrics_and_report(tmp_path):
    now = datetime(2026, 6, 9, 12, 0, 0)
    messages = [
        {"sender": "vip@corp.test", "unread": True, "received_at": "2026-06-01T09:30:00"},
        {"sender": "user@corp.test", "unread": True, "received_at": "2026-06-08T10:00:00"},
        {"sender": "vip@corp.test", "unread": False, "received_at": "2026-06-09T08:00:00"},
        {"sender": "other@corp.test", "unread": True, "received_at": "2026-06-05T18:45:00"},
    ]

    metrics = compute_backlog_metrics(
        messages=messages,
        vip_senders={"vip@corp.test"},
        now=now,
        history_unread_counts=[10, 9, 8, 8, 7, 6, 3],
    )

    assert metrics == {
        "unread_count": 3,
        "oldest_unread_age_days": 8,
        "backlog_trend_7d": -7,
        "vip_sender_unread_count": 1,
    }

    report = build_report(
        messages=messages,
        vip_senders={"vip@corp.test"},
        now=now,
        history_unread_counts=[10, 9, 8, 8, 7, 6, 3],
    )
    path = write_report(report, report_dir=tmp_path, now=now)

    assert path.name == "df-159-2026-06-09.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["factory"] == "df-159"
    assert saved["unread_count"] == 3
    assert saved["oldest_unread_age_days"] == 8
    assert saved["backlog_trend_7d"] == -7
    assert saved["vip_sender_unread_count"] == 1

    stop_flag = tmp_path / "df-159.stop"
    assert should_stop(stop_flag) is False
    stop_flag.write_text("STOP", encoding="utf-8")
    assert should_stop(stop_flag) is True


def test_rejects_invalid_received_at_type():
    with raises(TypeError):
        compute_backlog_metrics(
            messages=[{"sender": "x@test", "unread": True, "received_at": object()}],
            now="2026-06-09T12:00:00",
        )
