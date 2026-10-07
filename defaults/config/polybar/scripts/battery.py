#!/usr/bin/env python3
import os
from pathlib import Path

def get_battery(root, preferred=""):
    for device in sorted(Path(root).glob("*")):
        try:
            if preferred and device.name != preferred:
                continue
            if (device / "type").read_text().strip() != "Battery":
                continue
            value = int((device / "capacity").read_text().strip())
            if 0 <= value <= 100:
                return value
        except (OSError, ValueError):
            continue
    return None

if __name__ == "__main__":
    value = get_battery("/sys/class/power_supply", os.environ.get("POLYBAR_BATTERY", ""))
    print("" if value is None else "%{T2}󰁹%{T-} " + str(value) + "%")
