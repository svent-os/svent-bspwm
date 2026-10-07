import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'defaults/config/polybar/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StatusTests(unittest.TestCase):
    def test_vm_with_no_battery(self):
        with tempfile.TemporaryDirectory() as path:
            self.assertIsNone(load('battery').get_battery(path))

    def test_battery_is_read_without_a_fixed_device_name(self):
        with tempfile.TemporaryDirectory() as path:
            battery = Path(path) / 'BAT7'
            battery.mkdir()
            (battery / 'type').write_text('Battery\n')
            (battery / 'capacity').write_text('48\n')
            self.assertEqual(load('battery').get_battery(path), 48)

    def test_vpn_is_preferred_over_ethernet(self):
        network = load('network')
        def device(name, address):
            return {'ifname': name, 'flags': ['UP'], 'operstate': 'UP',
                    'addr_info': [{'local': address, 'scope': 'global'}]}
        chosen = network.select_network([device('eth0', '192.168.1.4'),
                                         device('tun0', '10.10.14.2')],
                                        [{'dev': 'eth0'}], [])
        self.assertEqual(chosen['interface'], 'tun0')

    def test_link_local_is_not_shown_as_host_address(self):
        network = load('network')
        chosen = network.select_network([{'ifname': 'eth0', 'flags': ['UP'],
                                          'addr_info': [{'local': 'fe80::1', 'scope': 'link'}]}], [], [])
        self.assertIsNone(chosen)
