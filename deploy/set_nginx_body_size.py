import os
import sys
import paramiko


CONF_PATH = "/etc/nginx/conf.d/body_size.conf"
CONF_CONTENT = "client_max_body_size 20M;\n"


def main():
    host = os.environ.get('VPS_HOST')
    user = os.environ.get('VPS_USER', 'root')
    password = os.environ.get('PASSWORD')

    if not (host and password):
        print('Set VPS_HOST and PASSWORD env vars', file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=30)

    sftp = client.open_sftp()
    try:
        # ensure conf.d exists
        try:
            sftp.stat('/etc/nginx/conf.d')
        except IOError:
            # create directory via sudo (not possible via sftp) — fallback: ignore, most distros have it
            pass
        # write config
        with sftp.open(CONF_PATH, 'w') as f:
            f.write(CONF_CONTENT)
    finally:
        sftp.close()

    # test and reload nginx
    for cmd in ["nginx -t", "systemctl reload nginx"]:
        stdin, stdout, stderr = client.exec_command(f"sudo {cmd}")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            print(stderr.read().decode(), file=sys.stderr)
            sys.exit(code)

    client.close()
    print('nginx: client_max_body_size set to 20M and reloaded')


if __name__ == '__main__':
    main()


