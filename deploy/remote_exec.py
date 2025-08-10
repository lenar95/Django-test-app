import os
import sys
import paramiko


def main():
    host = os.environ.get('VPS_HOST')
    user = os.environ.get('VPS_USER', 'root')
    password = os.environ.get('PASSWORD')
    cmd = os.environ.get('CMD')
    if not (host and password and cmd):
        print('Set VPS_HOST, PASSWORD and CMD env vars', file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=30)

    full_cmd = f"bash -lc '{cmd}'"
    stdin, stdout, stderr = client.exec_command(full_cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    if exit_status != 0:
        print(err, file=sys.stderr)
        sys.exit(exit_status)
    client.close()


if __name__ == '__main__':
    main()


