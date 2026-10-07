#!/usr/bin/env python3
import ipaddress
import json
import os
import subprocess
import sys
from pathlib import Path

ICONS = {'vpn': '󰖂', 'ethernet': '󰌘', 'wifi': '󰖩', 'other': '󰩠'}
PRIORITY = {'vpn': 0, 'ethernet': 1, 'wifi': 2, 'other': 3}
TUNNELS = {'wireguard', 'tun', 'tap', 'tuntap', 'ppp', 'vti', 'vti6', 'xfrm', 'ovpn', 'ovpn-dco',
           'gre', 'gretap', 'ip6gre', 'ip6gretap', 'ipip', 'ip6tnl', 'sit',
           'l2tp', 'l2tpeth', 'ip6tunnel', 'ip6_vti', 'tunnel', 'ip/tunnel'}
INFRASTRUCTURE = {'bridge', 'veth', 'dummy', 'docker', 'vxlan', 'geneve',
                  'vrf', 'ifb', 'nlmon', 'netdevsim', 'netkit', 'erspan',
                  'ip6erspan', 'bareudp', 'can', 'vcan', 'vxcan'}
LAYERED = {'vlan', 'macvlan', 'macvtap', 'ipvlan', 'ipvtap', 'macsec'}
BAD_ADDRESS_FLAGS = {'tentative', 'deprecated', 'dadfailed', 'optimistic'}


def read_ip(*args):
    try:
        result = subprocess.run(['ip', '-j', *args], capture_output=True,
                                text=True, timeout=3, check=True)
        data = json.loads(result.stdout)
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def flags_of(item):
    flags = item.get('flags', [])
    return set(flags) if isinstance(flags, list) and all(isinstance(f, str) for f in flags) else set()


def valid_name(name):
    
    return (isinstance(name, str) and 0 < len(name.encode('utf-8')) <= 15
            and name not in ('.', '..')
            and not any(c.isspace() or c in '/:\x00' for c in name))


def kind_of(device):
    info = device.get('linkinfo', {})
    return str(info.get('info_kind', '')).lower() if isinstance(info, dict) else ''


def parent_of(device, devices):
    reference = device.get('link_index', device.get('link'))
    for parent in devices:
        if reference is not None and reference in (parent.get('ifindex'), parent.get('ifname')):
            return parent
    return None


def classify(device, devices=(), sysroot='/sys/class/net', seen=None):
    name = device.get('ifname', '')
    if not valid_name(name):
        return 'other'
    seen = set() if seen is None else set(seen)
    if name in seen:
        return 'other'
    seen.add(name)
    kind = kind_of(device)
    link_type = str(device.get('link_type', '')).lower()
    flags = flags_of(device)
    if kind in TUNNELS or link_type in TUNNELS:
        return 'vpn'
    if kind in INFRASTRUCTURE or 'LOOPBACK' in flags or link_type == 'loopback':
        return 'other'
    if kind in LAYERED:
        parent = parent_of(device, devices)
        if parent is not None:
            return classify(parent, devices, sysroot, seen)
    interface_path = Path(sysroot) / name
    if (device.get('wireless') or kind in {'wlan', 'wireless', 'virt_wifi'}
            or (interface_path / 'wireless').exists()
            or (interface_path / 'phy80211').exists()):
        return 'wifi'
    if kind in {'bond', 'team', 'hsr'}:
        return 'ethernet'
    
    
    if not kind and ('POINTOPOINT' in flags or
                     name.startswith(('tun', 'tap', 'wg', 'ppp', 'vpn', 'tailscale', 'zt'))):
        if 'POINTOPOINT' in flags or link_type not in {'ether'}:
            return 'vpn'
        
        if (interface_path / 'tun_flags').exists() or name.startswith(('tailscale', 'zt', 'tap')):
            return 'vpn'
    if not kind and not link_type and name.startswith(('wl', 'wlan')):
        return 'wifi'
    if link_type == 'ether' or kind in LAYERED:
        return 'ethernet'
    if not kind and not link_type and name.startswith(('en', 'eth')):
        return 'ethernet'
    return 'other'


def usable_link(device, category, sysroot):
    name = device.get('ifname', '')
    flags = flags_of(device)
    if not valid_name(name) or name == 'lo' or 'LOOPBACK' in flags:
        return False
    if str(device.get('link_type', '')).lower() == 'loopback':
        return False
    if device.get('protodown') in (True, 1, 'on'):
        return False
    state = str(device.get('operstate', 'UNKNOWN')).upper()
    if state in {'DOWN', 'LOWERLAYERDOWN', 'NOTPRESENT', 'DORMANT'}:
        return False
    if 'flags' in device and 'UP' not in flags:
        return False
    
    
    if category in {'ethernet', 'wifi'}:
        try:
            if (Path(sysroot) / name / 'carrier').read_text().strip() == '0':
                return False
        except OSError:
            pass
    return True


def usable_address(item):
    if not isinstance(item, dict):
        return None
    if BAD_ADDRESS_FLAGS & flags_of(item) or any(item.get(flag) for flag in BAD_ADDRESS_FLAGS):
        return None
    if item.get('valid_life_time') in (0, '0') or item.get('preferred_life_time') in (0, '0'):
        return None
    if not isinstance(item.get('local'), str):
        return None
    try:
        address = ipaddress.ip_address(item['local'])
        if '%' in str(address):
            return None
        if item.get('family') not in (None, 'inet' if address.version == 4 else 'inet6'):
            return None
        if 'prefixlen' in item:
            prefix = item['prefixlen']
            if not isinstance(prefix, int) or isinstance(prefix, bool) or not 0 <= prefix <= address.max_prefixlen:
                return None
    except (ValueError, TypeError, KeyError):
        return None
    if (address.is_loopback or address.is_link_local or address.is_multicast
            or address.is_unspecified or str(address) == '255.255.255.255'):
        return None
    scope = item.get('scope')
    if not isinstance(scope, str) or scope not in {'global', 'site'} or str(address) == item.get('broadcast'):
        return None
    return address


def route_metric(route):
    try:
        metric = int(route.get('metric', 0))
        return metric if metric >= 0 else 2147483647
    except (ValueError, TypeError, OverflowError):
        return 2147483647


def default_routes_for(routes, name, version):
    matches = []
    for route in routes:
        if not isinstance(route, dict) or route.get('type', 'unicast') != 'unicast':
            continue
        if route.get('dst', 'default') not in ('default', '0.0.0.0/0' if version == 4 else '::/0'):
            continue
        if {'dead', 'linkdown'} & flags_of(route):
            continue
        hops = route.get('nexthops')
        if isinstance(hops, list):
            for hop in hops:
                if isinstance(hop, dict) and hop.get('dev') == name and not ({'dead', 'linkdown'} & flags_of(hop)):
                    matches.append(dict(route, dev=name))
        elif route.get('dev') == name:
            matches.append(route)
    return matches


def select_network(devices, routes4, routes6, preferred='', sysroot='/sys/class/net'):
    devices = [d for d in devices if isinstance(d, dict)]
    candidates = []
    for device in devices:
        name = device.get('ifname', '')
        if preferred and name != preferred:
            continue
        category = classify(device, devices, sysroot)
        if not usable_link(device, category, sysroot):
            continue
        addresses = device.get('addr_info', [])
        if not isinstance(addresses, list):
            continue
        for item in addresses:
            address = usable_address(item)
            if address is None:
                continue
            routes = default_routes_for(routes4 if address.version == 4 else routes6, name, address.version)
            metric = min((route_metric(route) for route in routes), default=2147483647)
            preferred_source = any(str(address) == route.get('prefsrc') for route in routes)
            
            
            
            rank = (PRIORITY[category], not bool(routes), metric, address.version != 4,
                    not preferred_source, bool(item.get('secondary')) or 'secondary' in flags_of(item),
                    name, int(address))
            candidates.append((rank, {'ip': str(address), 'type': category, 'interface': name}))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def collect_devices():
    addresses = read_ip('addr', 'show')
    links = {item.get('ifname'): item for item in read_ip('-d', 'link', 'show') if valid_name(item.get('ifname'))}
    return [dict(links.get(item.get('ifname'), {}), **item) for item in addresses]


if __name__ == '__main__':
    selected = select_network(collect_devices(),
                              read_ip('-4', 'route', 'show', 'table', 'all', 'default'),
                              read_ip('-6', 'route', 'show', 'table', 'all', 'default'),
                              os.environ.get('POLYBAR_INTERFACE', ''))
    if '--json' in sys.argv:
        print(json.dumps(selected))
    elif '--plain' in sys.argv:
        print(selected['ip'] if selected else 'No host')
    else:
        print('%{T2}' + ICONS[selected['type']] + '%{T-} ' + selected['ip']
              if selected else '%{T2}󰩠%{T-} No host')
