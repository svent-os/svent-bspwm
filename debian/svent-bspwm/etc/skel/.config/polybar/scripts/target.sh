#!/usr/bin/env bash
set -u

file="$HOME/.cache/target_ip"
theme="$HOME/.config/rofi/polybar-z1rov/target.rasi"

valid_ip() {
    python3 -c '
import ipaddress
import sys

try:
    ipaddress.ip_address(sys.argv[1])
except ValueError:
    sys.exit(1)
' "$1" 2>/dev/null
}

current=""
if [[ -r "$file" ]]; then
    IFS= read -r current < "$file" || :
fi

if [[ -n "$current" ]] && ! valid_ip "$current"; then
    current=""
fi

copy_target() {
    [[ -n "$current" ]] || return 0

    if command -v xclip >/dev/null 2>&1; then
        printf '%s' "$current" | xclip -selection clipboard
    elif command -v xsel >/dev/null 2>&1; then
        printf '%s' "$current" | xsel --clipboard --input
    else
        printf 'Install xclip or xsel to copy the target.\n' >&2
        return 1
    fi
}

edit_target() {
    local value status
    local input="$current"
    local message="IPv4 or IPv6 address"

    while :; do
        value=$(rofi -no-config \
            -theme "$theme" \
            -dmenu \
            -p "Target" \
            -filter "$input" \
            -kb-custom-1 "Control+Delete" \
            -mesg "$message" \
            < /dev/null)
        status=$?

        case "$status" in
            10)
                rm -f -- "$file"
                return 0
                ;;
            0)
                value=$(printf '%s' "$value" | tr -d '[:space:]')

                if [[ -z "$value" ]]; then
                    rm -f -- "$file"
                    return 0
                fi

                if valid_ip "$value"; then
                    mkdir -p "$HOME/.cache" || return 1
                    (
                        umask 077
                        printf '%s\n' "$value" > "$file"
                    ) || return 1
                    chmod 600 "$file"
                    return 0
                fi

                input="$value"
                message="Invalid address. Use a valid IPv4 or IPv6 address."
                ;;
            *)
                # Preserve the saved target on cancellation or error.
                return 0
                ;;
        esac
    done
}

case "${1:-left}" in
    left)
        if [[ -n "$current" ]]; then
            copy_target
        else
            edit_target
        fi
        ;;
    edit|right)
        edit_target
        ;;
    copy)
        copy_target
        ;;
    clear)
        rm -f -- "$file"
        ;;
    *)
        printf 'Usage: %s {left|edit|copy|clear}\n' "$0" >&2
        exit 2
        ;;
esac
