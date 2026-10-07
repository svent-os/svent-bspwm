#!/usr/bin/python3
import os
from pathlib import Path
import signal
import subprocess
import time


def main():
    config = Path(os.environ['XDG_CONFIG_HOME']) / 'polybar/config.ini'
    bars = {}
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    try:
        while not stopping:
            try:
                result = subprocess.run(['polybar', '--list-monitors'], text=True,
                                        capture_output=True, timeout=3, check=True)
                monitors = {line.split(':', 1)[0] for line in result.stdout.splitlines() if ':' in line}
            except (OSError, subprocess.SubprocessError):
                monitors = set(bars)
            for monitor in set(bars) - monitors:
                child = bars.pop(monitor)
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            for monitor in monitors:
                child = bars.get(monitor)
                if child is None or child.poll() is not None:
                    bars[monitor] = subprocess.Popen(['polybar', '--reload', '-c', str(config), 'svent-bar'],
                                                     env=dict(os.environ, MONITOR=monitor))
            for _ in range(20):
                if stopping:
                    break
                time.sleep(0.1)
    finally:
        for child in bars.values():
            if child.poll() is None:
                child.terminate()
        for child in bars.values():
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
