#!/bin/sh
SEL=/usr/libexec/svent/svent-wallpaper
[ -x "$SEL" ] || exit 0
BG=/usr/share/backgrounds/svent/landscape
USERDIR="$HOME/Pictures/Wallpapers"
THEME="$HOME/.config/rofi/wallpaper.rasi"
CACHE="$HOME/.cache/svent/wallpapers"
mkdir -p "$CACHE"

thumb() {
  src="$1"; key="$2"; out="$CACHE/$key.png"
  if command -v magick >/dev/null 2>&1; then
    [ -f "$out" ] && [ "$out" -nt "$src" ] || magick "$src" -thumbnail 480x270^ -gravity center -extent 480x270 "$out" 2>/dev/null
    [ -f "$out" ] && { printf '%s' "$out"; return; }
  elif command -v convert >/dev/null 2>&1; then
    [ -f "$out" ] && [ "$out" -nt "$src" ] || convert "$src" -thumbnail 480x270^ -gravity center -extent 480x270 "$out" 2>/dev/null
    [ -f "$out" ] && { printf '%s' "$out"; return; }
  fi
  printf '%s' "$src"
}

entries() {
  i=0
  for f in "$BG"/svent-*.png; do
    [ -e "$f" ] || continue
    i=$((i + 1))
    b=$(basename "$f" .png)
    printf 'Environment %s\0icon\x1f%s\n' "$i" "$(thumb "$f" "${b#svent-}")"
  done
  [ -d "$USERDIR" ] || return 0
  for f in "$USERDIR"/*; do
    [ -f "$f" ] || continue
    case "$f" in
      *.png | *.jpg | *.jpeg | *.PNG | *.JPG | *.JPEG) ;;
      *) continue ;;
    esac
    n=$(basename "$f")
    printf 'Custom: %s\0icon\x1f%s\n' "$n" "$(thumb "$f" "custom-$n")"
  done
}

choice=$(entries | rofi -dmenu -i -p "Wallpaper" -show-icons -theme "$THEME")
[ -n "$choice" ] || exit 0
case "$choice" in
  "Custom: "*)
    "$SEL" --file "$USERDIR/${choice#Custom: }"
    ;;
  "Environment "*)
    want="${choice#Environment }"
    j=0
    for f in "$BG"/svent-*.png; do
      [ -e "$f" ] || continue
      j=$((j + 1))
      if [ "$j" = "$want" ]; then
        b=$(basename "$f" .png)
        "$SEL" --set "${b#svent-}"
        break
      fi
    done
    ;;
esac
