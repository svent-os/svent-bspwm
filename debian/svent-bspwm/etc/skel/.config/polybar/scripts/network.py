#!/usr/bin/env python3
import ipaddress
import json
import os
import subprocess
import sys
from pathlib import Path

ICONS = {
    "vpn": "\U000f0582",
    "ethernet": "\U000f0318",
    "wifi": "\U000f05a9",
    "usb": "\U000f0287",
    "mobile": "\U000f011c",
    "virtual": "\U000f0317",
    "other": "\U000f0a60",
}
PRIORITY = {
    "vpn": 0,
    "ethernet": 1,
    "wifi": 2,
    "usb": 3,
    "mobile": 4,
    "virtual": 5,
    "other": 6,
}

VPN_KINDS = {"wireguard", "tun", "tap", "ppp", "vti", "vti6", "xfrm",
             "ipip", "sit", "gre", "gretap", "ip6gre", "ip6tnl", "wg"}
VIRTUAL_KINDS = {"bridge", "veth", "dummy", "docker", "vxlan", "bond",
                 "vlan", "macvlan", "ipvlan", "team", "ifb", "nlmon"}


def read_ip(*args):
    try:
        return json.loads(subprocess.check_output(["ip", "-j", *args],
                                                   stderr=subprocess.DEVNULL))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []


def sys_read(name, *parts):
    try:
        return Path("/sys/class/net", name, *parts).read_text().strip()
    except OSError:
        return ""


def dev_subsystem(name):
    try:
        link = os.readlink(os.path.join("/sys/class/net", name, "device", "subsystem"))
        return os.path.basename(link)
    except OSError:
        return ""


def is_wifi(name, device):
    return (device.get("wireless") is not None
            or Path("/sys/class/net", name, "wireless").exists()
            or Path("/sys/class/net", name, "phy80211").exists())


def classify(device):
    name = device.get("ifname", "")
    kind = (device.get("linkinfo", {}) or {}).get("info_kind", "")
    flags = device.get("flags", [])
    arptype = sys_read(name, "type")
    subsystem = dev_subsystem(name)

    if kind in VPN_KINDS or "POINTOPOINT" in flags or name.startswith(
            ("tun", "tap", "wg", "ppp", "vpn", "tailscale", "zt", "nordlynx", "proton", "mullvad")):
        return "vpn"
    if is_wifi(name, device):
        return "wifi"
    if name.startswith(("wwan", "wwp", "ww", "rmnet", "mbim", "qmi")) or kind == "wwan" or arptype in {"519", "530"}:
        return "mobile"
    if subsystem == "usb":
        return "usb"
    if kind in VIRTUAL_KINDS or name.startswith(
            ("docker", "br-", "br", "veth", "virbr", "vmnet", "vnet", "bond", "vlan", "cni", "flannel", "cali")):
        return "virtual"
    if device.get("link_type") == "ether" or arptype == "1" or name.startswith(
            ("en", "eth", "eno", "ens", "enp", "enx")):
        return "ethernet"
    return "other"


def select_network(devices, routes4, routes6, preferred=""):
    candidates = []
    for device in devices:
        name = device.get("ifname", "")
        if preferred and name != preferred:
            continue
        if device.get("operstate") in {"DOWN", "LOWERLAYERDOWN", "NOTPRESENT"}:
            continue
        if "flags" in device and "UP" not in device["flags"]:
            continue
        category = classify(device)
        for item in device.get("addr_info", []):
            invalid = {"tentative", "deprecated", "dadfailed"}
            if any(flag in invalid for flag in item.get("flags", [])) or any(item.get(flag) for flag in invalid):
                continue
            try:
                address = ipaddress.ip_address(item["local"])
            except (ValueError, KeyError):
                continue
            if address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified:
                continue
            if item.get("scope") not in {"global", "site"}:
                continue
            routes = routes4 if address.version == 4 else routes6
            matching = [route for route in routes if route.get("dev") == name]
            metric = min((int(route.get("metric", 0)) for route in matching), default=2147483647)
            rank = (PRIORITY[category], not bool(matching), address.version != 4,
                    metric, bool(item.get("secondary")), name, str(address))
            candidates.append((rank, {"ip": str(address), "type": category, "interface": name}))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


if __name__ == "__main__":
    addresses = read_ip("addr", "show")
    links = {item.get("ifname"): item for item in read_ip("-d", "link", "show")}
    devices = [dict(links.get(item.get("ifname"), {}), **item) for item in addresses]
    selected = select_network(devices,
                              read_ip("-4", "route", "show", "default"),
                              read_ip("-6", "route", "show", "default"),
                              os.environ.get("POLYBAR_INTERFACE", ""))
    if "--plain" in sys.argv:
        print(selected["ip"] if selected else "No host")
    else:
        if selected:
            print("%{T2}" + ICONS[selected["type"]] + "%{T-} " + selected["ip"])
        else:
            print("%{T2}" + ICONS["other"] + "%{T-} No host")
