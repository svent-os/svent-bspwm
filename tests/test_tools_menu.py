import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tools_menu', ROOT / 'libexec/tools-menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class MenuTests(unittest.TestCase):
    def test_cancel_does_not_select_tool(self):
        with patch.object(menu.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '')):
            self.assertIsNone(menu.choose(['nmap'], 'Tool'))

    def test_invalid_index_is_rejected(self):
        for value in ('-1', '5', '$(command)', ''):
            with self.subTest(value=value), patch.object(menu.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], 0, value)):
                self.assertIsNone(menu.choose(['nmap'], 'Tool'))

    def test_label_cannot_add_another_menu_row(self):
        with patch.object(menu.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '0')) as call:
            self.assertEqual(menu.choose(['name\nextra row'], 'Tool'), 0)
            self.assertEqual(call.call_args.kwargs['input'], 'name extra row\n')
            self.assertNotIn('shell', call.call_args.kwargs)

    def test_removed_package_is_not_considered_installed(self):
        with patch.object(menu.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'rc ')):
            self.assertFalse(menu.installed('sv-example'))
