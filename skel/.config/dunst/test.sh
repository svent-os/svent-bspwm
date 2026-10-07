#!/usr/bin/env bash
set -eu
folder="$HOME/.config/dunst/scripts"
case "${1:-normal}" in
 normal|network) python3 "$folder/notify.py" network 'Connection established' 'Wired connection is ready.' ;;
 volume) python3 "$folder/notify.py" volume --percent 40 ;;
 mute) python3 "$folder/notify.py" volume --muted ;;
 brightness) python3 "$folder/notify.py" brightness --percent 65 ;;
 battery) python3 "$folder/notify.py" battery 'Battery low: 15%' 'Connect your charger.' --percent 15 ;;
 critical) python3 "$folder/notify.py" battery 'Battery critical: 5%' 'Connect your charger now.' --percent 5 --urgency critical ;;
 charging) python3 "$folder/notify.py" battery Charging 'Power connected.' --percent 42 ;;
 download) python3 "$folder/notify.py" download 'Download complete' 'Your files are ready.' ;;
 message) python3 "$folder/notify.py" message 'New message' 'You have a new message.' ;;
 screenshot) python3 "$folder/notify.py" screenshot 'Screenshot saved' 'The image was saved to your Pictures folder.' ;;
 clipboard) python3 "$folder/notify.py" clipboard Copied 'The text was copied to the clipboard.' ;;
 error) python3 "$folder/notify.py" error 'Action failed' 'Please check the application details.' --urgency critical ;;
 legacy) notify-send -a dunstify '[+] Volume: 40%' ;;
 all)
  for kind in network volume mute brightness battery charging download message screenshot clipboard; do
   bash "$HOME/.config/dunst/test.sh" "$kind"
   sleep 3
  done ;;
 *) printf 'Usage: test.sh normal|volume|mute|brightness|battery|critical|charging|download|message|screenshot|clipboard|error|legacy|all\n' >&2; exit 1 ;;
esac
