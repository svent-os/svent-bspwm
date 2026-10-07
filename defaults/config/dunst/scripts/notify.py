#!/usr/bin/env python3
import argparse
import subprocess

KINDS = ("volume", "brightness", "battery", "network", "power", "download", "message", "screenshot", "clipboard", "system", "error")

def send(kind, summary, body="", percent=None, urgency="normal", tag=None):
    command = ["notify-send", "-a", kind.title(), "-c", "svent." + kind, "-u", urgency]
    if percent is not None:
        if not 0 <= percent <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        command += ["-h", "int:value:" + str(percent)]
    if tag or kind in ("volume", "brightness", "battery"):
        command += ["-h", "string:x-dunst-stack-tag:" + (tag or kind)]
    command += ["--", summary, body]
    subprocess.run(command, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("summary", nargs="?", default="")
    parser.add_argument("body", nargs="?", default="")
    parser.add_argument("--percent", type=int)
    parser.add_argument("--muted", action="store_true")
    parser.add_argument("--urgency", choices=("low", "normal", "critical"), default="normal")
    args = parser.parse_args()
    if args.percent is not None and not 0 <= args.percent <= 100:
        parser.error("Percentage must be between 0 and 100")
    summary = args.summary
    if args.kind == "volume":
        summary = "Muted" if args.muted else (str(args.percent) + "%" if args.percent is not None else summary or "Output volume")
    elif args.kind == "brightness":
        summary = str(args.percent) + "%" if args.percent is not None else summary or "Display brightness"
    elif args.kind == "battery" and not summary:
        summary = "Battery level" + (": " + str(args.percent) + "%" if args.percent is not None else "")
    if not summary:
        parser.error("A summary is required for this notification type")
    send(args.kind, summary, args.body, None if args.muted else args.percent, args.urgency)
