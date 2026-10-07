#!/usr/bin/env bash
set -u
folder="${XDG_CONFIG_HOME:-$HOME/.config}/rofi/polybar-svent"
choice=$(printf 'Power off\0icon\x1f%s/icons/power.svg\nRestart\0icon\x1f%s/icons/restart.svg\nLog out\0icon\x1f%s/icons/logout.svg\nLock\0icon\x1f%s/icons/lock.svg\n' "$folder" "$folder" "$folder" "$folder" | rofi -no-config -theme "$folder/power.rasi" -dmenu -show-icons -no-custom -format i) || exit 0
case "$choice" in
 0) action='systemctl poweroff'; title='Power off' ;;
 1) action='systemctl reboot'; title='Restart' ;;
 2) action='bspc quit'; title='Log out' ;;
 3) exec bash "${XDG_CONFIG_HOME:-$HOME/.config}/polybar/scripts/lock.sh" ;;
 *) exit 0 ;;
esac
confirm=$(printf 'Cancel\nConfirm\n' | rofi -no-config -theme "$folder/confirm.rasi" -dmenu -no-custom -mesg "$title" -format i) || exit 0
[[ "$confirm" == 1 ]] || exit 0
exec $action
