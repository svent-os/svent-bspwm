import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('defaults', ROOT / 'libexec/defaults.py')
defaults = importlib.util.module_from_spec(spec)
spec.loader.exec_module(defaults)


class DefaultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.home = self.base / 'home'
        self.config = self.home / '.config'
        self.state = self.home / '.local/state'
        (self.source / 'config/bspwm').mkdir(parents=True)
        self.rc = self.source / 'config/bspwm/bspwmrc'
        self.rc.write_text('version one\n', encoding='utf-8')
        (self.source / 'zshrc').write_text('shell default\n', encoding='utf-8')

    def initialize(self):
        return defaults.initialize(self.source, self.home, self.config, self.state)

    def test_existing_root_is_seeded_without_changing_other_config(self):
        self.config.mkdir(parents=True)
        existing = self.config / 'other-app.conf'
        existing.write_text('personal\n')
        self.initialize()
        self.assertTrue((self.config / 'bspwm/bspwmrc').exists())
        self.assertEqual(existing.read_text(), 'personal\n')

    def test_upgrade_unmodified_and_preserve_modified(self):
        self.initialize()
        shell = self.home / '.zshrc'
        shell.write_text('personal shell\n')
        self.rc.write_text('version two\n')
        self.initialize()
        self.assertEqual((self.config / 'bspwm/bspwmrc').read_text(), 'version two\n')
        self.assertEqual(shell.read_text(), 'personal shell\n')

    def test_existing_untracked_config_is_preserved(self):
        target = self.config / 'bspwm/bspwmrc'
        target.parent.mkdir(parents=True)
        target.write_text('beta user config\n')
        self.initialize()
        self.assertEqual(target.read_text(), 'beta user config\n')

    def test_repeat_login_is_idempotent(self):
        self.initialize()
        self.assertEqual(self.initialize(), [])

    def test_corrupt_manifest_does_not_overwrite_existing_files(self):
        self.initialize()
        manifest = self.state / 'sv-bspwm/defaults.json'
        manifest.write_text('{broken')
        self.rc.write_text('new upstream default\n')
        self.initialize()
        self.assertEqual((self.config / 'bspwm/bspwmrc').read_text(), 'version one\n')

    def test_custom_xdg_config_location(self):
        self.config = self.home / 'custom-config'
        self.initialize()
        self.assertTrue((self.config / 'bspwm/bspwmrc').is_file())
        self.assertFalse((self.home / '.config').exists())

    def test_symlinked_config_is_not_followed(self):
        self.config.mkdir(parents=True)
        other = self.base / 'other'
        other.mkdir()
        try:
            (self.config / 'bspwm').symlink_to(other, target_is_directory=True)
        except OSError as exc:
            self.skipTest(str(exc))
        self.initialize()
        self.assertFalse((other / 'bspwmrc').exists())


if __name__ == '__main__':
    unittest.main()
