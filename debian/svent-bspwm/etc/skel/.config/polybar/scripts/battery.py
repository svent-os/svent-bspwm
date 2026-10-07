#!/usr/bin/env python3
import argparse
import os
import sys
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
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", type=int)
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    state = Path(os.environ.get("POLYBAR_BATTERY_DEMO_FILE", str(Path.home() / ".cache/polybar_battery_demo")))
    if args.real:
        state.unlink(missing_ok=True)
        print("Battery simulation disabled")
        raise SystemExit(0)
    if args.simulate is not None:
        if not 0 <= args.simulate <= 100:
            parser.error("Battery percentage must be between 0 and 100")
        state.parent.mkdir(parents=True, exist_ok=True)
        temporary = state.with_name(state.name + "." + str(os.getpid()) + ".tmp")
        temporary.write_text(str(args.simulate) + "\n", encoding="utf-8")
        temporary.replace(state)
        print("Battery simulation enabled: " + str(args.simulate) + "%")
        raise SystemExit(0)
    simulated = None
    try:
        simulated = int(state.read_text().strip())
        if not 0 <= simulated <= 100:
            simulated = None
    except (OSError, ValueError):
        pass
    value = simulated if simulated is not None else get_battery("/sys/class/power_supply", os.environ.get("POLYBAR_BATTERY", ""))
    if value is None:
        print("%{F#7E8995}%{T2}󰁹%{T-} --%{F-}")
    else:
        print("%{T2}󰁹%{T-} " + str(value) + "%" + (" demo" if simulated is not None else ""))
