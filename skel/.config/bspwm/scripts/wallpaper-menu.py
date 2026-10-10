#!/usr/bin/env python3
import hashlib
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

BACKGROUNDS = Path("/usr/share/backgrounds/svent/landscape")
SELECTOR = Path("/usr/libexec/svent/svent-wallpaper")
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def thumbnail(source, cache):
    stat = source.stat()
    key = hashlib.sha256(f"{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()
    target = cache / (key + ".png")
    if not target.exists():
        try:
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((960, 540), Image.Resampling.LANCZOS)
                image = ImageOps.fit(image, (480, 270), Image.Resampling.LANCZOS)
                temp = target.with_suffix(".tmp")
                image.save(temp, format="PNG", compress_level=1)
                temp.replace(target)
        except (OSError, ValueError):
            return source
    return target


def entries(backgrounds, custom, cache, current=None):
    files = sorted(backgrounds.glob("svent-*.png"))
    if custom.is_dir():
        files += sorted(path for path in custom.rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS)
    if current and current.is_file() and current.suffix.lower() in EXTENSIONS and current not in files:
        files.append(current)
    rows = []
    for source in files:
        if not source.is_file():
            continue
        label = source.stem.removeprefix("svent-").replace("-", " ").title() if source.parent == backgrounds else "Custom: " + source.name
        label = label.replace("\n", " ").replace("\r", " ")
        rows.append((source, label + "\0icon\x1f" + str(thumbnail(source, cache)) + "\n"))
    return rows


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
    rows = entries(BACKGROUNDS, custom, cache, current)
    if not rows:
        raise SystemExit("No wallpapers are available")
    result = subprocess.run(
        ["rofi", "-dmenu", "-i", "-p", "Wallpaper", "-show-icons", "-no-custom", "-format", "i", "-theme", str(config / "rofi/wallpaper.rasi")],
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
