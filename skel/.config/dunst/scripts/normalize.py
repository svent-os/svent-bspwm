#!/usr/bin/env python3
import os
import re
from notify import send

summary = os.environ.get("DUNST_SUMMARY", "")
kind = "brightness" if "brightness" in summary.lower() else "volume"
match = re.search(r"([0-9]{1,3})\s*%", summary)
muted = "muted" in summary.lower() and "unmuted" not in summary.lower()
percent = int(match.group(1)) if match and 0 <= int(match.group(1)) <= 100 else None
if muted:
    send(kind, "Muted", tag=kind)
elif percent is not None:
    send(kind, str(percent) + "%", percent=percent)
else:
    cleaned = re.sub(r"^\[[+ -]\]\s*", "", summary)
    send(kind, cleaned, os.environ.get("DUNST_BODY", ""))
