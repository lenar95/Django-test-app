import os
from pathlib import Path
import paramiko


FILES = [
    (Path('static/css/style.css'), '/opt/app/webapp/static/css/style.css'),
    (Path('templates/profiles/list.html'), '/opt/app/webapp/templates/profiles/list.html'),
]


def main():
    host = os.environ['VPS_HOST']
    user = os.environ.get('VPS_USER', 'root')
    password = os.environ['PASSWORD']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=30)

    sftp = client.open_sftp()
    for src, dst in FILES:
        # ensure directory exists
        remote_dir = os.path.dirname(dst)
        try:
            sftp.stat(remote_dir)
        except IOError:
            # recursively create
            parts = remote_dir.strip('/').split('/')
            cur = ''
            for p in parts:
                cur += '/' + p
                try:
                    sftp.stat(cur)
                except IOError:
                    sftp.mkdir(cur)
        sftp.put(str(src), dst)

    # collectstatic and restart gunicorn
    cmds = [
        "bash -lc 'cd /opt/app/webapp && source .venv/bin/activate && python manage.py collectstatic --noinput'",
        "systemctl restart gunicorn",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(f"sudo {cmd}")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            print(stderr.read().decode())
            raise SystemExit(code)

    sftp.close()
    client.close()
    print('Synced files and reloaded services')


if __name__ == '__main__':
    main()


