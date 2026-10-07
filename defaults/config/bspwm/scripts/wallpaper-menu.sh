#!/bin/bash
set -u
selector=/usr/libexec/svent/svent-wallpaper
config="${XDG_CONFIG_HOME:-$HOME/.config}"
state="$config/svent"
userdir="$HOME/Pictures/Wallpapers"
files=()
labels=()
for file in /usr/share/backgrounds/svent/landscape/svent-*.png; do
    [[ -f "$file" ]] || continue
    files+=("$file")
    label=$(basename "$file" .png)
    labels+=("${label#svent-}")
done
for file in "$userdir"/*; do
    [[ -f "$file" ]] || continue
    case "${file,,}" in *.png|*.jpg|*.jpeg|*.webp) ;; *) continue ;; esac
    files+=("$file")
    labels+=("Custom: $(basename "$file")")
done
if (( ${#files[@]} == 0 )); then
    rofi -e 'No wallpapers found. Add images to ~/Pictures/Wallpapers.'
    exit 0
fi
entries() {
    for i in "${!files[@]}"; do
        [[ "${files[$i]}" != *$'\n'* ]] || continue
        printf '%s\0icon\x1f%s\n' "${labels[$i]//$'\n'/ }" "${files[$i]}"
    done
}
for i in "${!files[@]}"; do
    if [[ "${files[$i]}" == *$'\n'* ]]; then unset 'files[i]' 'labels[i]'; fi
done
files=("${files[@]}")
labels=("${labels[@]}")
index=$(entries | rofi -dmenu -i -p Wallpaper -show-icons -no-custom -format i -theme "$config/rofi/wallpaper.rasi") || exit 0
[[ "$index" =~ ^[0-9]+$ ]] && (( index < ${#files[@]} )) || exit 0
file="${files[$index]}"
if [[ "$file" == /usr/share/backgrounds/svent/landscape/svent-* ]]; then
    mkdir -p "$state"
    rm -f -- "$state/wallpaper.override"
    exec "$selector" --set "${labels[$index]}"
fi
exec "$selector" --file "$file"
