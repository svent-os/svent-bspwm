#!/usr/bin/env python3
import hashlib
import html
import json
import os
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

BACKGROUNDS = Path("/usr/share/backgrounds/svent/landscape")
SELECTOR = Path("/usr/libexec/svent/svent-wallpaper")
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CATALOG = Path("/usr/share/svent/artwork/wallpapers.json")


def thumbnail(source, cache):
    stat = source.stat()
    key = hashlib.sha256(f"v2:{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()
    target = cache / (key + ".png")
    if not target.exists():
        try:
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((960, 540), Image.Resampling.LANCZOS)
                image = ImageOps.pad(image, (480, 270), Image.Resampling.LANCZOS, color="#242a2e")
                temp = target.with_suffix(".tmp")
                image.save(temp, format="PNG", compress_level=1)
                temp.replace(target)
        except (OSError, ValueError):
            return source
    return target


def entries(backgrounds, custom, cache, current=None, catalog=None):
    labels = {}
    aliases = set()
    if catalog is not None and catalog.is_file():
        data = json.loads(catalog.read_text(encoding="utf-8"))
        labels = {item["id"]: item["name"] for item in data["wallpapers"]}
        aliases = set(data.get("aliases", {}))
    files = sorted(backgrounds.glob("svent-*.png"))
    files = [path for path in files if path.stem.removeprefix("svent-") not in aliases]
    if custom.is_dir():
        files += sorted(path for path in custom.rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS)
    if current and current.is_file() and current.suffix.lower() in EXTENSIONS and current not in files:
        files.append(current)
    rows = []
    for source in files:
        if not source.is_file():
            continue
        identifier = source.stem.removeprefix("svent-")
        label = labels.get(identifier, identifier.replace("-", " ").title()) if source.parent == backgrounds else "Custom: " + source.name
        label = label.replace("\n", " ").replace("\r", " ")
        rows.append((source, label + "\0icon\x1f" + str(thumbnail(source, cache)) + "\n"))
    return rows


def monitor_size():
    try:
        focused = subprocess.run(["bspc", "query", "-M", "-m", "focused", "--names"], capture_output=True, text=True, check=False).stdout.strip()
        output = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=False).stdout
        monitors = []
        for line in output.splitlines():
            match = re.match(r"(\S+) connected (?:primary )?(\d+)x(\d+)\+[-\d]+\+[-\d]+", line)
            if match:
                size = (int(match[2]), int(match[3]))
                if match[1] == focused:
                    return size
                monitors.append(size)
        if monitors:
            return monitors[0]
    except OSError:
        pass
    return 1280, 720


def grid_theme(count, width, height):
    visible = max(1, min(5, count))
    available = int(width * 0.9)
    image_size = min(190, max(40, (available - 36 - (visible - 1) * 14) // visible - 16),
                     max(40, int(height * 0.75 - 92)))
    cell_width = image_size + 16
    cell_height = image_size + 16
    window_width = visible * cell_width + (visible - 1) * 14 + 36
    window_height = cell_height + 76
    return (f"window {{ width: {window_width}px; height: {window_height}px; }} "
            f"listview {{ columns: 1; lines: {visible}; height: {cell_height}px; }} "
            f"element {{ width: {cell_width}px; height: {cell_height}px; }} "
            f"element-icon {{ size: {image_size}px; }}")


def apply_selection(source, backgrounds, selector, state):
    if source.parent == backgrounds:
        (state / "wallpaper.override").unlink(missing_ok=True)
        command = [str(selector), "--set", source.stem.removeprefix("svent-")]
    else:
        command = [str(selector), "--file", str(source)]
    subprocess.run(command, check=True)


def main():
    if not SELECTOR.is_file():
        raise SystemExit("The SventOS wallpaper selector is unavailable")
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "svent/wallpapers"
    cache.mkdir(parents=True, exist_ok=True)
    pictures = subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True, text=True, check=False)
    custom = Path(pictures.stdout.strip() or str(Path.home() / "Pictures")) / "Wallpapers"
    custom.mkdir(parents=True, exist_ok=True)
    state = config / "svent"
    override = state / "wallpaper.override"
    current = None
    if override.is_file():
        current = Path(override.read_text().strip())
    rows = entries(BACKGROUNDS, custom, cache, current, CATALOG)
    if not rows:
        raise SystemExit("No wallpapers are available")
    width, height = monitor_size()
    help_text = "← → Browse · Enter Apply · Esc Close\nAdd images: " + html.escape(str(custom))
    result = subprocess.run(
        ["rofi", "-dmenu", "-i", "-p", "Wallpaper", "-show-icons", "-no-custom", "-format", "i", "-mesg", help_text,
         "-scroll-method", "1", "-no-cycle", "-monitor", "-1",
         "-kb-move-char-back", "", "-kb-move-char-forward", "",
         "-kb-row-up", "Left,Up,Control+p", "-kb-row-down", "Right,Down,Control+n",
         "-theme", str(config / "rofi/wallpaper.rasi"), "-theme-str", grid_theme(len(rows), width, height)],
        input="".join(row for _, row in rows), capture_output=True, text=True, check=False,
    )
    if result.returncode or not result.stdout.strip().isdigit():
        return
    index = int(result.stdout.strip())
    if index >= len(rows):
        return
    source = rows[index][0]
    apply_selection(source, BACKGROUNDS, SELECTOR, state)


if __name__ == "__main__":
    main()
