#!/usr/bin/python3
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from defaults import initialize

BASE = Path('/usr/libexec/svent/bspwm')


def main():
    os.umask(0o077)
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
    state = Path(os.environ.get('XDG_STATE_HOME', str(home / '.local/state')))
    os.environ['XDG_CONFIG_HOME'] = str(config)
    initialize(Path('/usr/share/svent/bspwm/defaults'), home, config, state)
    logs = state / 'sv-bspwm/logs'
    logs.mkdir(parents=True, exist_ok=True)
    display = ''.join(c if c.isalnum() else '_' for c in os.environ.get('DISPLAY', ''))
    lock = open(logs / ('session-' + display + '.lock'), 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('A Svent bspwm session already owns this display.', file=sys.stderr)
        return 1
    children = []
    handles = []
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, stop)

    def start(name, argv):
        handle = open(logs / (name + '.log'), 'w')
        handles.append(handle)
        try:
            child = subprocess.Popen(argv, stdout=handle, stderr=handle,
                                     start_new_session=True)
        except OSError as exc:
            print(f'{name}: {exc}', file=sys.stderr)
            return None
        children.append(child)
        return child

    wm = None
    try:
        wm = start('bspwm', ['bspwm', '-c', str(config / 'bspwm/bspwmrc')])
        if wm is None:
            return 1
        
        for _ in range(100):
            if stopped or wm.poll() is not None:
                return wm.returncode or 1
            try:
                ready = subprocess.run(['bspc', 'query', '-M'],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=1)
                if ready.returncode == 0:
                    break
            except subprocess.TimeoutExpired:
                pass
            time.sleep(0.05)
        else:
            print('bspwm did not become ready.', file=sys.stderr)
            return 1
        start('sxhkd', ['sxhkd', '-c', str(config / 'sxhkd/sxhkdrc')])
        start('dunst', ['dunst', '-config', str(config / 'dunst/dunstrc')])
        start('picom', ['picom', '--config', str(config / 'picom/picom.conf')])
        start('polybar', ['bash', str(config / 'polybar/launch.sh')])
        start('battery', [str(BASE / 'battery-loop'),
                          str(config / 'dunst/scripts/battery-watch.py')])
        
        start('monitors', [str(BASE / 'monitor-watch')])
        while not stopped and wm.poll() is None:
            time.sleep(0.25)
        return wm.returncode or 0
    finally:
        for child in reversed(children):
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 3
        for child in reversed(children):
            try:
                child.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        for handle in handles:
            handle.close()
        lock.close()


if __name__ == '__main__':
    sys.exit(main())
