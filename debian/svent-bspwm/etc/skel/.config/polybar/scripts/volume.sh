#!/usr/bin/env bash
set -u
command -v pactl >/dev/null || exit 0
volume() { pactl get-sink-volume @DEFAULT_SINK@ | awk 'match($0,/[0-9]+%/) {print substr($0,RSTART,RLENGTH-1);exit}'; }
case "${1:-status}" in
 status)
  value=$(volume)
  if pactl get-sink-mute @DEFAULT_SINK@ | grep -q yes; then
   printf '%%{F#7E8995}%%{T2}󰖁%%{T-} %s%%%%{F-}\n' "${value:-0}"
  else
   printf '%%{T2}󰕾%%{T-} %s%%\n' "${value:-0}"
  fi ;;
 slider)
  theme="$HOME/.config/rofi/polybar-z1rov/volume.rasi"
  choice=$(printf 'Mute\n25%%\n50%%\n75%%\n100%%\n' | rofi -no-config -theme "$theme" -dmenu -no-custom -format i -mesg "Current volume $(volume)%") || exit 0
  case "$choice" in
   0) pactl set-sink-mute @DEFAULT_SINK@ toggle; exit ;;
   1) level=25 ;;
   2) level=50 ;;
   3) level=75 ;;
   4) level=100 ;;
   *) exit 0 ;;
  esac
  pactl set-sink-volume @DEFAULT_SINK@ "${level}%"
  pactl set-sink-mute @DEFAULT_SINK@ 0
  ;;
esac
