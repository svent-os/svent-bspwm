import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name != 'posix', 'Shell syntax is checked on Debian')
class ShellSyntaxTests(unittest.TestCase):
    def test_all_shell_scripts_parse(self):
        paths = [p for p in ROOT.rglob('*') if p.is_file() and
                 (p.suffix in ('.sh', '.postinst') or p.name in ('bspwmrc', 'svent-bspwm-session', 'svent-bspwm-configure',
                  'wallpaper-apply', 'screenshot', 'battery-loop', 'monitor-watch',
                  'normalize-notification'))]
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                first = path.read_text(encoding='utf-8').splitlines()[0]
                shell = 'bash' if 'bash' in first else 'sh'
                subprocess.run([shell, '-n', str(path)], check=True)
        subprocess.run(['zsh', '-n', str(ROOT / 'defaults/zshrc')], check=True)
