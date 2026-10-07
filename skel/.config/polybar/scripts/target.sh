#!/usr/bin/env bash
set -u
file="$HOME/.cache/target_ip"
theme="$HOME/.config/rofi/polybar-z1rov/target.rasi"
valid() { python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1].strip())' "$1" 2>/dev/null; }
current=''
[[ -r "$file" ]] && IFS= read -r current < "$file"
case "${1:-edit}" in
  clear)
    rm -f -- "$file"
    exit 0
    ;;
  copy)
    [[ -n "$current" ]] && valid "$current" || exit 0
    if command -v xclip >/dev/null; then printf '%s' "$current" | xclip -selection clipboard
    elif command -v xsel >/dev/null; then printf '%s' "$current" | xsel --clipboard --input; fi
    exit 0
    ;;
esac
value=$(rofi -no-config -theme "$theme" -dmenu -p "Target" -filter "$current" -mesg "Enter IPv4/IPv6 - empty to clear" < /dev/null) || exit 0
value=$(printf '%s' "$value" | tr -d '[:space:]')
if [[ -z "$value" ]]; then
  rm -f -- "$file"
  exit 0
fi
valid "$value" || exit 0
mkdir -p "$HOME/.cache"
printf '%s\n' "$value" > "$file"
chmod 600 "$file"
