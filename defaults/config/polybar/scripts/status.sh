#!/usr/bin/env bash
set -u
get_ip() {
 python3 "${XDG_CONFIG_HOME:-$HOME/.config}/polybar/scripts/network.py" --plain
}
get_target() {
 local value=''
 [[ -r "$HOME/.cache/target_ip" ]] && IFS= read -r value < "$HOME/.cache/target_ip"
 value=$(printf '%s' "$value" | tr -cd '[:alnum:].:_ -' | cut -c1-36)
 printf '%s' "${value:-No target}"
}
copy_text() {
 if command -v xclip >/dev/null; then printf '%s' "$1" | xclip -selection clipboard
 elif command -v xsel >/dev/null; then printf '%s' "$1" | xsel --clipboard --input; fi
}
case "${1:-}" in
 ip) python3 "${XDG_CONFIG_HOME:-$HOME/.config}/polybar/scripts/network.py" ;;
 copy-ip) value=$(get_ip); [[ "$value" == "No host" ]] || copy_text "$value" ;;
 target) get_target; printf '\n' ;;
 copy-target) value=$(get_target); [[ "$value" == "No target" ]] || copy_text "$value" ;;
 battery) python3 "${XDG_CONFIG_HOME:-$HOME/.config}/polybar/scripts/battery.py" ;;
esac
