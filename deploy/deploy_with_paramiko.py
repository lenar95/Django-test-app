import os
import sys
import time
import socket
from pathlib import Path

import paramiko


def run(client: paramiko.SSHClient, cmd: str, use_sudo: bool = False):
    if use_sudo and not cmd.startswith('sudo '):
        cmd = f"sudo {cmd}"
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if exit_status != 0:
        raise RuntimeError(f"Command failed ({exit_status}): {cmd}\n{err}")
    return out


def sftp_put_dir(sftp: paramiko.SFTPClient, local_dir: Path, remote_dir: str, excludes=None):
    exclude_dirs = {'.venv', '.git', '__pycache__'}
    exclude_files = {'*.pyc', 'db.sqlite3'}
    if excludes:
        # allow caller to extend
        for pat in excludes:
            if pat.startswith('*.'):
                exclude_files.add(pat)
            else:
                exclude_dirs.add(pat)

    def should_skip_dir(rel_path: str) -> bool:
        segments = [seg for seg in rel_path.split(os.sep) if seg and seg != '.']
        return any(seg in exclude_dirs for seg in segments)

    def should_skip_file(path: Path) -> bool:
        if any(seg in exclude_dirs for seg in path.parts):
            return True
        return any(path.match(pat) for pat in exclude_files)

    def ensure_dir(remote_path: str):
        # recursively create directories
        try:
            sftp.stat(remote_path)
            return
        except IOError:
            parent = os.path.dirname(remote_path.rstrip('/'))
            if parent and parent != remote_path:
                try:
                    sftp.stat(parent)
                except IOError:
                    ensure_dir(parent)
            sftp.mkdir(remote_path)

    ensure_dir(remote_dir)

    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        if rel == '.':
            rel = ''
        if should_skip_dir(rel):
            continue
        rdir = f"{remote_dir}/{rel}" if rel else remote_dir
        ensure_dir(rdir)
        for f in files:
            p = Path(root) / f
            if should_skip_file(p):
                continue
            sftp.put(str(p), f"{rdir}/{f}")


def main():
    host = os.environ.get('VPS_HOST')
    user = os.environ.get('VPS_USER', 'root')
    password = os.environ.get('PASSWORD')
    domain = os.environ.get('DOMAIN', host)
    app_dir = os.environ.get('APP_DIR', '/opt/app/webapp')

    if not (host and password):
        print('Set VPS_HOST and PASSWORD env vars', file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=30)

    run(client, f"mkdir -p {app_dir}")
    run(client, "apt update && apt install -y python3-venv python3-pip nginx", use_sudo=True)

    sftp = client.open_sftp()
    sftp_put_dir(sftp, Path('.'), app_dir, excludes={'*.pyc', '__pycache__', '.venv', '.git', 'db.sqlite3'})

    run(client, f"python3 -m venv {app_dir}/.venv")
    run(client, f"bash -lc 'source {app_dir}/.venv/bin/activate && pip install --upgrade pip && pip install -r {app_dir}/requirements.txt'")

    # .env
    secret_key_cmd = "python3 - <<PY\nimport secrets; print(secrets.token_urlsafe(50))\nPY\n"
    secret = run(client, secret_key_cmd).strip()
    env_content = f"""
DJANGO_SECRET_KEY={secret}
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS={domain},{host}
DJANGO_CSRF_TRUSTED_ORIGINS=https://{domain}
""".strip()
    # write .env via SFTP to avoid heredoc issues
    with sftp.open(f"{app_dir}/.env", 'w') as f:
        f.write(env_content + "\n")

    run(client, f"bash -lc 'cd {app_dir} && source .venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput'" )

    # systemd
    unit = f"""
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory={app_dir}
EnvironmentFile={app_dir}/.env
ExecStart={app_dir}/.venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8001 --workers 3

[Install]
WantedBy=multi-user.target
"""
    # write systemd unit via SFTP
    with sftp.open("/etc/systemd/system/gunicorn.service", 'w') as f:
        f.write(unit)
    run(client, "systemctl daemon-reload && systemctl enable --now gunicorn", use_sudo=True)

    # nginx
    nginx = f"""
server {{
    listen 80;
    server_name {domain} {host};

    location /static/ {{ alias {app_dir}/staticfiles/; }}
    location /media/  {{ alias {app_dir}/media/; }}

    location / {{
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    with sftp.open("/etc/nginx/sites-available/webapp", 'w') as f:
        f.write(nginx)
    run(client, "ln -sf /etc/nginx/sites-available/webapp /etc/nginx/sites-enabled/webapp && nginx -t && systemctl reload nginx", use_sudo=True)

    sftp.close()
    client.close()
    print('Deploy complete.')


if __name__ == '__main__':
    main()


