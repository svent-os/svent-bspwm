#!/usr/bin/env bash
set -u
script="$HOME/.config/polybar/scripts/battery.py"
theme="$HOME/.config/rofi/polybar-z1rov/battery.rasi"
choice=$(printf 'Real battery\n25%% demo\n50%% demo\n75%% demo\n100%% demo\n' | rofi -no-config -theme "$theme" -dmenu -no-custom -format i -mesg 'Battery preview') || exit 0
case "$choice" in
 0) python3 "$script" --real ;;
 1) python3 "$script" --simulate 25 ;;
 2) python3 "$script" --simulate 50 ;;
 3) python3 "$script" --simulate 75 ;;
 4) python3 "$script" --simulate 100 ;;
esac
