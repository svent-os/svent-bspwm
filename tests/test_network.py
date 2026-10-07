import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('network', ROOT / 'defaults/config/polybar/scripts/network.py')
network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(network)


def device(name, address='192.168.10.2', kind='', link_type='ether', state='UP', **kwargs):
    result = {'ifname': name, 'link_type': link_type, 'operstate': state, 'flags': ['UP'],
              'addr_info': [{'local': address, 'scope': 'global'}]}
    if kind:
        result['linkinfo'] = {'info_kind': kind}
    return dict(result, **kwargs)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sysroot = self.temp.name

    def select(self, devices, routes4=(), routes6=(), preferred=''):
        return network.select_network(devices, routes4, routes6, preferred, self.sysroot)

    def test_arbitrarily_named_tunnel_kinds(self):
        for kind in ('wireguard', 'tun', 'tap', 'ppp', 'vti', 'vti6', 'xfrm',
                     'gre', 'gretap', 'ip6gre', 'ip6gretap', 'ipip', 'ip6tnl', 'sit', 'l2tp', 'ovpn', 'ovpn-dco'):
            with self.subTest(kind=kind):
                selected = self.select([device('lab-net', '10.42.0.2', kind, state='UNKNOWN')])
                self.assertEqual(selected['type'], 'vpn')

    def test_all_priority_classes_and_split_tunnel(self):
        wifi = device('wifi-lab', wireless=True)
        ethernet = device('uplink9')
        tunnel = device('remote7', '10.4.0.2', 'wireguard', state='UNKNOWN')
        bridge = device('br0', '172.17.0.1', 'bridge')
        routes = [{'dev': 'uplink9', 'metric': 1}]
        self.assertEqual(self.select([bridge, wifi, ethernet, tunnel], routes)['interface'], 'remote7')
        self.assertEqual(self.select([bridge, wifi, ethernet], routes)['interface'], 'uplink9')
        self.assertEqual(self.select([bridge, wifi])['type'], 'wifi')
        self.assertEqual(self.select([bridge])['type'], 'other')

    def test_no_physical_name_allowlist(self):
        self.assertEqual(self.select([device('office-nic')])['type'], 'ethernet')
        self.assertEqual(self.select([device('wg-backup')])['type'], 'ethernet')

    def test_wireless_sysfs_with_arbitrary_name(self):
        (Path(self.sysroot) / 'radio9/phy80211').mkdir(parents=True)
        self.assertEqual(self.select([device('radio9')])['type'], 'wifi')

    def test_layered_nics_inherit_parent_category(self):
        parent = device('radio9', wireless=True, ifindex=4)
        for kind in ('vlan', 'macvlan', 'macvtap', 'ipvlan', 'ipvtap', 'macsec'):
            with self.subTest(kind=kind):
                child = device('child9', kind=kind, link_index=4)
                self.assertEqual(network.classify(child, [parent, child], self.sysroot), 'wifi')

    def test_parent_cycle_terminates(self):
        first = device('first', kind='vlan', ifindex=1, link_index=2)
        second = device('second', kind='vlan', ifindex=2, link_index=1)
        self.assertEqual(network.classify(first, [first, second], self.sysroot), 'other')

    def test_bridges_containers_and_overlays_are_other(self):
        for kind in ('bridge', 'veth', 'dummy', 'vxlan', 'geneve', 'vrf', 'ifb', 'netkit'):
            with self.subTest(kind=kind):
                self.assertEqual(self.select([device('generic0', kind=kind)])['type'], 'other')

    def test_bond_team_and_unknown_transport(self):
        for kind in ('bond', 'team', 'hsr'):
            self.assertEqual(self.select([device('agg0', kind=kind)])['type'], 'ethernet')
        self.assertEqual(self.select([device('fabric0', kind='ipoib', link_type='infiniband')])['type'], 'other')

    def test_down_links_and_no_carrier_are_filtered(self):
        for state in ('DOWN', 'LOWERLAYERDOWN', 'DORMANT', 'NOTPRESENT'):
            self.assertIsNone(self.select([device('bad0', state=state)]))
        self.assertIsNone(self.select([device('bad0', flags=[])]))
        self.assertIsNone(self.select([device('bad0', protodown=True)]))
        path = Path(self.sysroot) / 'bad0'
        path.mkdir()
        (path / 'carrier').write_text('0\n')
        self.assertIsNone(self.select([device('bad0')]))

    def test_loopback_and_invalid_interface_names(self):
        for name in ('lo', '../root', 'bad name', 'bad/name', 'bad:0', '', 'a' * 16):
            self.assertIsNone(self.select([device(name)]))

    def test_unusable_addresses_and_lifetimes(self):
        for address in ('127.0.0.1', '::1', '169.254.1.2', 'fe80::1',
                        'ff02::1', '224.0.0.1', '0.0.0.0', '::', '255.255.255.255', 'bad', 42):
            with self.subTest(address=address):
                self.assertIsNone(self.select([device('nic0', address)]))
        for flag in ('tentative', 'deprecated', 'dadfailed', 'optimistic'):
            item = device('nic0')
            item['addr_info'][0]['flags'] = [flag]
            self.assertIsNone(self.select([item]))
        for key in ('valid_life_time', 'preferred_life_time'):
            item = device('nic0')
            item['addr_info'][0][key] = 0
            self.assertIsNone(self.select([item]))

    def test_ipv6_only_vpn_still_beats_ipv4_ethernet(self):
        self.assertEqual(self.select([device('nic0'), device('secure0', 'fd00::2', 'wireguard')])['ip'], 'fd00::2')

    def test_default_route_and_lower_metric_win_within_class(self):
        devices = [device('first0'), device('second0', '192.168.20.2')]
        self.assertEqual(self.select(devices, [{'dev': 'second0'}])['interface'], 'second0')
        self.assertEqual(self.select(devices, [{'dev': 'first0', 'metric': 200},
                                               {'dev': 'second0', 'metric': 10}])['interface'], 'second0')

    def test_invalid_and_dead_routes_do_not_crash_or_win(self):
        devices = [device('first0'), device('second0', '192.168.20.2')]
        routes = [None, {'dev': 'first0', 'type': 'blackhole'},
                  {'dev': 'first0', 'flags': ['linkdown']},
                  {'dev': 'first0', 'metric': 'invalid'},
                  {'dev': 'second0', 'metric': 10}]
        self.assertEqual(self.select(devices, routes)['interface'], 'second0')

    def test_ecmp_next_hops_and_ipv6_routes(self):
        devices = [device('first0', 'fd00::2'), device('second0', 'fd00::3')]
        routes = [{'dst': '::/0', 'nexthops': [{'dev': 'first0', 'flags': ['dead']}, {'dev': 'second0'}]}]
        self.assertEqual(self.select(devices, routes6=routes)['interface'], 'second0')

    def test_primary_and_route_preferred_source(self):
        item = device('nic0')
        item['addr_info'] = [{'local': '192.168.1.4', 'scope': 'global', 'flags': ['secondary']},
                             {'local': '192.168.1.5', 'scope': 'global'}]
        self.assertEqual(self.select([item])['ip'], '192.168.1.5')
        self.assertEqual(self.select([item], [{'dev': 'nic0', 'prefsrc': '192.168.1.4'}])['ip'], '192.168.1.4')

    def test_explicit_override_is_validated(self):
        devices = [device('nic0'), device('tun0', '10.4.0.2', 'tun')]
        self.assertEqual(self.select(devices, preferred='nic0')['interface'], 'nic0')
        self.assertIsNone(self.select(devices, preferred='missing'))
        self.assertIsNone(self.select([device('nic0', state='DOWN')], preferred='nic0'))

    def test_malformed_json_and_command_failure(self):
        for output in ('{broken', '{}', '[1, null]'):
            with patch.object(network.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output)):
                self.assertEqual(network.read_ip('addr', 'show'), [])
        with patch.object(network.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ip', 3)):
            self.assertEqual(network.read_ip('addr', 'show'), [])

    def test_bad_topology_and_address_objects_are_ignored(self):
        malformed = device('bad0', addr_info=[None, {'local': '192.0.2.2', 'scope': 'global', 'prefixlen': 'bad'}])
        self.assertIsNone(self.select([None, malformed]))
        malformed['addr_info'] = [{'local': '192.0.2.2', 'scope': []}]
        self.assertIsNone(self.select([malformed]))
