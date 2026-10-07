#!/usr/bin/env python3
import json
import os
from pathlib import Path
from notify import send

def read_battery(root="/sys/class/power_supply"):
    preferred = os.environ.get("POLYBAR_BATTERY", "")
    for device in sorted(Path(root).glob("*")):
        try:
            if preferred and device.name != preferred:
                continue
            if (device / "type").read_text().strip() != "Battery":
                continue
            percent = int((device / "capacity").read_text().strip())
            status = (device / "status").read_text().strip()
            if 0 <= percent <= 100:
                return {"device": device.name, "percent": percent, "status": status}
        except (OSError, ValueError):
            continue
    return None

def choose_event(current, previous):
    percent = current["percent"]
    status = current["status"]
    same = previous.get("device") == current["device"]
    if status == "Discharging":
        band = 2 if percent <= 5 else 1 if percent <= 15 else 0
        old = (2 if previous.get("percent", 100) <= 5 else 1 if previous.get("percent", 100) <= 15 else 0) if same and previous.get("status") == "Discharging" else 0
        if band > old:
            return ("Battery critical: " if band == 2 else "Battery low: ") + str(percent) + "%", "Connect your charger.", "critical" if band == 2 else "normal"
    if status == "Charging" and same and previous.get("status") not in ("Charging", "Full"):
        return "Charging", "Power connected. Battery is at " + str(percent) + "%.", "low"
    if status == "Full" and same and previous.get("status") != "Full":
        return "Battery full", "Battery is fully charged.", "low"
    return None

if __name__ == "__main__":
    current = read_battery()
    if current is None:
        raise SystemExit(0)
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "svent-battery/battery.json"
    try:
        previous = json.loads(state.read_text())
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    event = choose_event(current, previous)
    if event:
        send("battery", event[0], event[1], current["percent"], event[2])
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = state.with_suffix(".tmp")
    temporary.write_text(json.dumps(current), encoding="utf-8")
    temporary.replace(state)
