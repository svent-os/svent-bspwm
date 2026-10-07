#!/usr/bin/env bash
set -u
file="$HOME/.cache/target_ip"
theme="${XDG_CONFIG_HOME:-$HOME/.config}/rofi/polybar-svent/target.rasi"
current=''
[[ -r "$file" ]] && IFS= read -r current < "$file"
normalize() {
 python3 -c 'import ipaddress,sys; v=sys.argv[1].strip(); assert "%" not in v; print(ipaddress.ip_address(v))' "$1" 2>/dev/null
}
if [[ "${1:-click}" == click ]] && normalize "$current" >/dev/null; then
 bash "${XDG_CONFIG_HOME:-$HOME/.config}/polybar/scripts/status.sh" copy-target
 exit 0
fi
message=''
while true; do
 value=$(rofi -no-config -theme "$theme" -dmenu -p 'Enter IP address' -mesg "$message" -filter "$current" -kb-custom-1 'Control+Delete' < /dev/null)
 code=$?
 if [[ "$code" == 10 ]]; then rm -f -- "$file"; exit 0; fi
 [[ "$code" == 0 ]] || exit 0
 normalized=$(normalize "$value") || {
  current="$value"; message='Enter a valid IPv4 or IPv6 address'; continue
 }
 mkdir -p "$HOME/.cache"
 temp=$(mktemp "${file}.XXXXXX") || exit 1
 printf '%s\n' "$normalized" > "$temp"
 chmod 600 "$temp"
 mv -f -- "$temp" "$file"
 exit 0
done
