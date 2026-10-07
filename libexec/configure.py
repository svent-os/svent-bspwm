#!/usr/bin/python3
import os
from pathlib import Path
import subprocess
import sys


def target_accounts(euid, environ, lookup_uid, lookup_name):
    if euid != 0:
        return [lookup_uid(euid)]
    targets = [lookup_uid(0)]
    username = environ.get('SUDO_USER', '')
    uid_text = environ.get('SUDO_UID', '')
    if not username and not uid_text:
        return targets
    if not username or not uid_text.isdecimal():
        raise ValueError('Incomplete sudo identity: SUDO_USER and SUDO_UID are required.')
    account = lookup_name(username)
    if account.pw_uid != int(uid_text):
        raise ValueError('SUDO_USER does not match SUDO_UID in the account database.')
    if account.pw_uid != 0:
        targets.append(account)
    return targets


def command_for(account):
    
    home = Path(account.pw_dir)
    if not home.is_absolute() or home == Path('/') or not home.is_dir():
        raise ValueError(f'Invalid home directory for {account.pw_name}: {home}')
    environment = {
        'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
        'HOME': str(home), 'USER': account.pw_name, 'LOGNAME': account.pw_name,
        'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_STATE_HOME': str(home / '.local/state'),
        'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
    }
    return ['/usr/bin/python3', '-B', '/usr/libexec/svent/bspwm/defaults.py'], environment


def main():
    import pwd
    try:
        accounts = target_accounts(os.geteuid(), os.environ, pwd.getpwuid, pwd.getpwnam)
        for account in accounts:
            argv, environment = command_for(account)
            options = {'env': environment, 'check': True}
            if os.geteuid() == 0:
                
                options.update(user=account.pw_uid, group=account.pw_gid,
                               extra_groups=os.getgrouplist(account.pw_name, account.pw_gid))
            subprocess.run(argv, **options)
            print(f'Svent defaults configured for {account.pw_name}: {account.pw_dir}')
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'svent-bspwm-configure: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
