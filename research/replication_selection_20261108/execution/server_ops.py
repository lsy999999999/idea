"""Use user-provided server inventory; credentials remain in memory only."""
from pathlib import Path
import re
import sys
import paramiko

def connect(index=0):
    text = Path('/Applications/ideas/服务器.md').read_text()
    hosts = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+id[：:]\s*(\S+)\s+密码[：:]\s*(\S+)', text)
    host, user, password = hosts[index]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=15, auth_timeout=15)
    return client

def run(command, index=0, timeout=60):
    client = connect(index)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        print(stdout.read().decode(errors='replace'))
        err = stderr.read().decode(errors='replace')
        if err:
            print(err, file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()

if __name__ == '__main__':
    raise SystemExit(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0))
