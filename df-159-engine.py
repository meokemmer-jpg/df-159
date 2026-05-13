"""OPS-Email-Backlog-Tracker DF-159 engine."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone


DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-159.lock")
DF_ID = "159"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-159"
    iso_timestamp: str = field(default="")
    source: str = "mock"
    emails_total: int = 0
    emails_unread: int = 0
    oldest_unread_days: int = 0
    daily_volume: int = 0
    response_rate_24h: float = 0


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        return (time.time() - p.stat().st_mtime) >= min_age_sec
    except OSError:
        return False


def acquire_lock_with_identity() -> bool:
    now = time.time()
    stale_after_sec = 6 * 60 * 60

    if LOCK_DIR.exists():
        try:
            age = now - LOCK_DIR.stat().st_mtime
            if age > stale_after_sec:
                for child in LOCK_DIR.iterdir():
                    if child.is_file() or child.is_symlink():
                        child.unlink(missing_ok=True)
                LOCK_DIR.rmdir()
        except OSError:
            return False

    try:
        LOCK_DIR.mkdir(mode=0o700)
        identity = {
            "df_id": DF_ID,
            "pid": os.getpid(),
            "created_at": iso_now(),
            "cwd": str(Path.cwd()),
        }
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def release_lock() -> None:
    try:
        if LOCK_DIR.exists():
            for child in LOCK_DIR.iterdir():
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
            LOCK_DIR.rmdir()
    except OSError:
        pass


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    env_tag = os.environ.get("DF_159_ENV_TAG", "local")

    for anchor in anchors or []:
        value = str(anchor)
        if value.startswith("env:"):
            key = value[4:]
            if not os.environ.get(key):
                missing.append(value)
            continue

        path = Path(value)
        if not path.is_absolute():
            path = DF_DIR / path
        if not path.exists():
            missing.append(value)

    return {
        "ok": not missing,
        "missing_anchors": missing,
        "env_tag": env_tag,
    }


def _is_real_api_enabled() -> bool:
    value = os.environ.get("DF_159_REAL_API_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    seen = []
    for match in DECISION_KEYWORDS_REGEX.finditer(str(text)):
        token = match.group(0)
        if token.lower() not in {item.lower() for item in seen}:
            seen.append(token)
    return seen


def assert_no_decision_keywords(output) -> None:
    if not isinstance(output, str):
        output = json.dumps(output, ensure_ascii=True, sort_keys=True)
    hits = scan_output_for_decision_keywords(output)
    if hits:
        raise ValueError("Q_0/K_0 keyword block triggered: " + ", ".join(hits))


def _env_int(name: str, default: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float = 0) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def collect_tracker_output() -> TrackerOutput:
    source = "mock"
    if _is_real_api_enabled():
        source = "mock_real_api_flag_on"

    return TrackerOutput(
        iso_timestamp=iso_now(),
        source=source,
        emails_total=_env_int("DF_159_EMAILS_TOTAL", 0),
        emails_unread=_env_int("DF_159_EMAILS_UNREAD", 0),
        oldest_unread_days=_env_int("DF_159_OLDEST_UNREAD_DAYS", 0),
        daily_volume=_env_int("DF_159_DAILY_VOLUME", 0),
        response_rate_24h=_env_float("DF_159_RESPONSE_RATE_24H", 0),
    )


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        anchors_raw = os.environ.get("DF_159_K17_ANCHORS", "")
        anchors = [item.strip() for item in anchors_raw.split(",") if item.strip()]
        pav = k17_pre_action_verification(anchors)

        if not pav["ok"]:
            return 3

        tracker = collect_tracker_output()
        payload = asdict(tracker)
        payload["k17_pre_action_verification"] = pav

        serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        assert_no_decision_keywords(serialized)

        reports_dir = DF_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_path = reports_dir / f"df-159-{report_date}.json"
        report_path.write_text(serialized + "\n", encoding="utf-8")

        return 0
    except (OSError, ValueError, TypeError):
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())