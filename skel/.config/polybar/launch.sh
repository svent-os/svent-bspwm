#!/usr/bin/env bash
set -eu
cd "$HOME/.config/polybar"
command -v polybar >/dev/null || { printf 'Polybar is required\n' >&2; exit 1; }
state="${XDG_RUNTIME_DIR:-$HOME/.cache}/polybar-z1rov"
mkdir -p "$state"
if [[ -r "$state/pid" ]]; then
 read -r oldpid < "$state/pid" || true
 if [[ "${oldpid:-}" =~ ^[0-9]+$ ]] && [[ "$(cat "/proc/$oldpid/comm" 2>/dev/null || true)" == polybar ]]; then
  kill "$oldpid" 2>/dev/null || true
  for ((i=0;i<30;i++)); do
   kill -0 "$oldpid" 2>/dev/null || break
   sleep 0.1
  done
 fi
fi
polybar --reload -c "$HOME/.config/polybar/config.ini" z1rov-bar > "$state/bar.log" 2>&1 &
printf '%s\n' "$!" > "$state/pid"
