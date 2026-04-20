from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def utc_now_iso() -> str:
    return datetime.now(BEIJING_TZ).isoformat(timespec="milliseconds")
