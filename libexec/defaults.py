#!/usr/bin/python3
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.svent-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def has_symlink(path):
    return any(item.is_symlink() for item in (path, *path.parents))


def initialize(source, home, config, state):
    manifest = state / 'sv-bspwm/defaults.json'
    if has_symlink(manifest):
        raise RuntimeError('Refusing a symlinked defaults manifest')
    try:
        previous = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    current = dict(previous)
    changed = []
    items = [(f'config/{p.relative_to(source / "config").as_posix()}', p,
              config / p.relative_to(source / 'config'))
             for p in sorted((source / 'config').rglob('*')) if p.is_file()]
    items.append(('zshrc', source / 'zshrc', home / '.zshrc'))
    for key, origin, target in items:
        if has_symlink(target) or (target.exists() and not target.is_file()):
            continue
        new_hash = digest(origin)
        actual = digest(target) if target.exists() else None
        if actual == new_hash:
            current[key] = new_hash
            continue
        if actual is not None and actual != previous.get(key):
            
            continue
        executable = origin.name == 'bspwmrc' or origin.suffix in ('.sh', '.py')
        atomic_write(target, origin.read_bytes(), 0o755 if executable else 0o644)
        current[key] = new_hash
        changed.append(key)
    atomic_write(manifest, (json.dumps(current, indent=2) + '\n').encode())
    return changed


if __name__ == '__main__':
    home = Path.home()
    initialize(Path('/usr/share/svent/bspwm/defaults'), home,
               Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))),
               Path(os.environ.get('XDG_STATE_HOME', str(home / '.local/state'))))
