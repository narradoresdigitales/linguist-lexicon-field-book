from datetime import timedelta

def normalize_timestamp(ts: str) -> str:
    """
    Accepts 'mm:ss' or 'hh:mm:ss' or plain seconds and returns 'hh:mm:ss'.
    """
    if not ts:
        return ""
    ts = ts.strip()
    if ts.isdigit():
        s = int(ts)
        return str(timedelta(seconds=s))
    parts = ts.split(":")
    parts = [p.zfill(2) for p in parts]
    if len(parts) == 2:
        parts = ["00"] + parts
    return ":".join(parts[-3:])
