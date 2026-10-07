#!/usr/bin/python3
import subprocess
import sys

sys.path.insert(0, '/usr/lib/svent')


def choose(labels, prompt):
    labels = [str(label).replace('\n', ' ').replace('\r', ' ') for label in labels]
    result = subprocess.run(['rofi', '-dmenu', '-i', '-no-custom', '-format', 'i',
                             '-p', prompt], input='\n'.join(labels) + '\n',
                            text=True, capture_output=True)
    if result.returncode != 0:
        return None
    try:
        index = int(result.stdout.strip())
        return index if 0 <= index < len(labels) else None
    except ValueError:
        return None


def installed(package):
    result = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Abbrev}', package],
                            capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.startswith('ii')


def main():
    from svent import catalog
    try:
        data = catalog.load()
    except catalog.CatalogError as exc:
        subprocess.run(['rofi', '-e', str(exc)])
        return 1
    tools = [t for t in data['tools'] if installed(t['package'])]
    groups = [g for g in data['groups'] if any(t['group'] == g for t in tools)]
    if not groups:
        subprocess.run(['rofi', '-e', 'No Svent tools are installed.'])
        return 0
    index = choose([data['groups'][g]['name'] for g in groups], 'Svent tools')
    if index is None:
        return 0
    entries = [t for t in tools if t['group'] == groups[index]]
    index = choose([t['name'] + ' — ' + t['description'] for t in entries], 'Tool')
    if index is None:
        return 0
    tool = entries[index]
    exe_index = 0
    if len(tool['executables']) > 1:
        exe_index = choose(tool['executables'], 'Executable')
        if exe_index is None:
            return 0
    
    subprocess.Popen(['kitty', '--', 'svent-run', tool['executables'][exe_index]],
                     start_new_session=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
