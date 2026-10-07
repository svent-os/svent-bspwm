#!/usr/bin/env bash
set -u
if [[ -n "${POLYBAR_LOCK_COMMAND:-}" ]]; then
 exec bash -c "$POLYBAR_LOCK_COMMAND"
elif command -v betterlockscreen >/dev/null; then
 exec betterlockscreen -l
elif command -v i3lock >/dev/null; then
 exec i3lock -c 191D22
elif command -v xsecurelock >/dev/null; then
 exec xsecurelock
elif command -v slock >/dev/null; then
 exec slock
else
 rofi -no-config -theme "$HOME/.config/rofi/polybar-z1rov/confirm.rasi" -e 'Install i3lock or configure POLYBAR_LOCK_COMMAND'
 exit 1
fi
