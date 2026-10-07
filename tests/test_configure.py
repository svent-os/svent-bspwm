import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure', ROOT / 'libexec/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.root = SimpleNamespace(pw_uid=0, pw_gid=0, pw_name='root', pw_dir='/root')
        self.user = SimpleNamespace(pw_uid=1001, pw_gid=1002, pw_name='z1rov', pw_dir='/srv/people/z1rov')
        self.by_uid = {0: self.root, 1001: self.user}.__getitem__
        self.by_name = {'root': self.root, 'z1rov': self.user}.__getitem__

    def targets(self, euid, environment):
        return configure.target_accounts(euid, environment, self.by_uid, self.by_name)

    def test_sudo_configures_root_and_caller(self):
        self.assertEqual(self.targets(0, {'SUDO_USER': 'z1rov', 'SUDO_UID': '1001'}), [self.root, self.user])

    def test_direct_root_configures_only_root(self):
        self.assertEqual(self.targets(0, {}), [self.root])

    def test_sudo_from_root_has_no_duplicate(self):
        self.assertEqual(self.targets(0, {'SUDO_USER': 'root', 'SUDO_UID': '0'}), [self.root])

    def test_nonroot_configures_only_self_even_with_sudo_environment(self):
        self.assertEqual(self.targets(1001, {'SUDO_USER': 'root', 'SUDO_UID': '0'}), [self.user])

    def test_mismatched_sudo_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.targets(0, {'SUDO_USER': 'z1rov', 'SUDO_UID': '999'})

    def test_missing_or_malformed_sudo_identity_is_rejected(self):
        for environ in ({'SUDO_USER': 'z1rov'}, {'SUDO_UID': '1001'},
                        {'SUDO_USER': 'z1rov', 'SUDO_UID': '-1'}):
            with self.subTest(environ=environ), self.assertRaises(ValueError):
                self.targets(0, environ)

    def test_environment_uses_account_home_not_sudo_home(self):
        from unittest.mock import patch
        from pathlib import PurePosixPath
        class AccountPath(PurePosixPath):
            def is_dir(self):
                return True
        with patch.object(configure, 'Path', AccountPath):
            argv, environment = configure.command_for(self.user)
        self.assertEqual(environment['HOME'], '/srv/people/z1rov')
        self.assertEqual(environment['XDG_CONFIG_HOME'], '/srv/people/z1rov/.config')
        self.assertEqual(argv[0], '/usr/bin/python3')
