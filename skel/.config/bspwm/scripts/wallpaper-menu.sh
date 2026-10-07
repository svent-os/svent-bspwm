#!/bin/sh
# Rofi wallpaper picker for bspwm: a thumbnail grid of the Svent designs and
# the user's own wallpapers in ~/Pictures/Wallpapers. Applied by the selector.
SEL=/usr/libexec/svent/svent-wallpaper
[ -x "$SEL" ] || exit 0
BG=/usr/share/backgrounds/svent/landscape
USERDIR="$HOME/Pictures/Wallpapers"
THEME="$HOME/.config/rofi/wallpaper.rasi"

entries() {
  for f in "$BG"/svent-*.png; do
    [ -e "$f" ] || continue
    b=$(basename "$f" .png)
    printf '%s\0icon\x1f%s\n' "${b#svent-}" "$f"
  done
  [ -d "$USERDIR" ] || return 0
  for f in "$USERDIR"/*; do
    [ -f "$f" ] || continue
    case "$f" in
      *.png|*.jpg|*.jpeg|*.PNG|*.JPG|*.JPEG) ;;
      *) continue ;;
    esac
    printf 'custom:%s\0icon\x1f%s\n' "$(basename "$f")" "$f"
  done
}

choice=$(entries | rofi -dmenu -i -p "Wallpaper" -show-icons -theme "$THEME")
[ -n "$choice" ] || exit 0
case "$choice" in
  custom:*) "$SEL" --file "$USERDIR/${choice#custom:}" ;;
  *)        "$SEL" --set "$choice" ;;
esac
