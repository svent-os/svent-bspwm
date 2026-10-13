import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'posix' and Path('/proc/self/fd').exists(), 'Requires Linux process descriptors')
class BarLauncherTests(unittest.TestCase):
    def test_bar_does_not_inherit_restart_lock(self):
        folder = ROOT / ('bar-test-' + uuid.uuid4().hex)
        home = folder / 'home'
        config = home / '.config/polybar'
        commands = folder / 'bin'
        config.mkdir(parents=True)
        commands.mkdir()
        (config / 'config.ini').write_text('[bar/z1rov-bar]\n')
        records = folder / 'processes'
        fake = commands / 'polybar'
        fake.write_text("#!/usr/bin/python3\nimport ctypes, os, time\nctypes.CDLL(None).prctl(15, b'polybar', 0, 0, 0)\ntry:\n os.fstat(9); state='open'\nexcept OSError:\n state='closed'\nwith open(os.environ['BAR_TEST_RECORDS'], 'a') as stream:\n stream.write(str(os.getpid())+' '+state+'\\n')\ntime.sleep(60)\n")
        fake.chmod(0o755)
        detect = commands / 'systemd-detect-virt'
        detect.write_text('#!/bin/sh\nexit 1\n')
        detect.chmod(0o755)
        environment = {**os.environ, 'HOME': str(home), 'XDG_RUNTIME_DIR': str(folder / 'run'),
                       'PATH': str(commands) + os.pathsep + os.environ['PATH'], 'BAR_TEST_RECORDS': str(records)}
        try:
            for expected in (1, 2):
                subprocess.run(['bash', str(ROOT / 'skel/.config/polybar/launch.sh')], env=environment,
                               check=True, timeout=8, capture_output=True)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    lines = records.read_text().splitlines() if records.exists() else []
                    if len(lines) >= expected:
                        break
                    time.sleep(0.05)
                self.assertEqual(len(lines), expected)
                self.assertEqual(lines[-1].split()[1], 'closed')
        finally:
            if records.exists():
                for line in records.read_text().splitlines():
                    try:
                        os.kill(int(line.split()[0]), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            shutil.rmtree(folder)
