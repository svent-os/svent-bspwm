#!/usr/bin/env bash
set -eu
cd "$HOME/.config/polybar"
command -v polybar >/dev/null || { printf 'Polybar is required\n' >&2; exit 1; }
if systemd-detect-virt --quiet 2>/dev/null; then
 export SVENT_RIGHT="target divider power"
fi
state="${XDG_RUNTIME_DIR:-$HOME/.cache}/polybar-z1rov"
mkdir -p "$state"
exec 9>"$state/launch-v2.lock"
flock 9
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
config="${SVENT_POLYBAR_CONFIG:-$HOME/.config/polybar/config.ini}"
display_id=$(printf '%s' "${DISPLAY:-}" | sha256sum | cut -c1-12)
scaled="${XDG_RUNTIME_DIR:-$HOME/.cache}/svent-display-$display_id/polybar.ini"
if [ -z "${SVENT_POLYBAR_CONFIG:-}" ] && [ -r "$scaled" ]; then
 config="$scaled"
fi
polybar --reload -c "$config" z1rov-bar 9>&- > "$state/bar.log" 2>&1 &
printf '%s\n' "$!" > "$state/pid"
