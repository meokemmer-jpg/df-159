# DF-159 OPS-Email-Backlog-Tracker [CRUX-MK]

**Status:** SKELETON-CONDITIONAL (Welle-51 W51-B Skeleton-Wave-2)
**Domain:** OPS (Operational Inbox-Hygiene)
**Welle:** 25

## Mission

Email-Inbox-Backlog-Tracking. Tracking:
- Unread-Count
- Oldest-Unread-Age-Days
- Backlog-Trend-7d
- VIP-Sender-Unread-Count

**NIEMALS Email-Send, Delete oder Archive.**

## Usage

```bash
cd ~/Projects/dark-factories/df-159
python df-159-engine.py        # Mock-Mode default
pytest tests/                   # Existing tests
```

## Output

- Reports: `reports/df-159-{date}.json`
- STOP-Flag: `/tmp/df-159.stop`

[CRUX-MK]
