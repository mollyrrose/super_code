#!/usr/bin/env python3
"""Password-authenticated SSH client for the GPU rig.

Why this exists instead of plain `ssh`: OpenSSH deliberately refuses to take a
password from a pipe, a file or an environment variable -- it insists on a real
terminal. Tool-driven sessions have no terminal, so a password-only host is
unreachable through `ssh`. paramiko speaks the same protocol from Python and CAN
take the password programmatically.

The password is read from RIG_PASSWORD. It is never printed, never written to
disk, and is redacted out of any error message before it is shown.

Usage:
    python scripts/rig_ssh.py --probe              # connect, report host + GPUs
    python scripts/rig_ssh.py -- nvidia-smi        # run a command
    python scripts/rig_ssh.py --json -- <command>
    python scripts/rig_ssh.py --install-key        # switch to key auth, no more password

Env:
    RIG_PASSWORD  (required)  password for RIG_USER
    RIG_HOST      default 100.85.73.31
    RIG_USER      default rig
    RIG_PORT      default 22

KILL SWITCH: unset RIG_PASSWORD, or delete this file. It keeps no state and
starts no daemon.
"""

import argparse
import json
import os
import posixpath
import sys
from pathlib import Path

DEFAULT_HOST = "100.85.73.31"
DEFAULT_USER = "rig"
DEFAULT_PORT = 22

# Well-known SID of the local Administrators group.
ADMIN_SID = "S-1-5-32-544"
ADMIN_KEYS = "C:/ProgramData/ssh/administrators_authorized_keys"


def _redact(text: str, secret: str) -> str:
    """Never let the password surface through an exception string."""
    return text.replace(secret, "***") if secret else text


def connect(timeout: int = 30):
    """Return a connected paramiko SSHClient, or exit with a clean message."""
    try:
        import paramiko
    except ImportError:
        raise SystemExit(
            "rig_ssh: paramiko is not installed. Install it into the ComfyUI venv (the one with CUDA torch):\n"
            "  uv pip install --python ai_video/comfyui/.venv/Scripts/python.exe paramiko"
        )

    password = os.environ.get("RIG_PASSWORD", "")
    if not password:
        raise SystemExit(
            "rig_ssh: RIG_PASSWORD is not set. Set it for this shell only:\n"
            '  bash:       export RIG_PASSWORD="..."\n'
            '  PowerShell: $env:RIG_PASSWORD = "..."'
        )

    client = paramiko.SSHClient()
    # Trust-on-first-use, done properly: load known_hosts BEFORE connecting and
    # save it after, so the host key is actually pinned. Without the load/save
    # pair, AutoAddPolicy silently accepts a NEW key on every single connection
    # -- which reads like first-contact trust but is really no verification at
    # all, and a swapped server key would never be noticed.
    known_hosts = Path.home() / ".ssh" / "known_hosts"
    try:
        client.load_host_keys(str(known_hosts))
    except IOError:
        pass  # no known_hosts yet -- it gets created on save below
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=os.environ.get("RIG_HOST", DEFAULT_HOST),
            port=int(os.environ.get("RIG_PORT", DEFAULT_PORT)),
            username=os.environ.get("RIG_USER", DEFAULT_USER),
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
    except Exception as e:
        raise SystemExit(f"rig_ssh: connect failed: {_redact(str(e), password)}")

    try:
        known_hosts.parent.mkdir(parents=True, exist_ok=True)
        client.save_host_keys(str(known_hosts))
    except (IOError, OSError):
        pass  # pinning is best-effort; never fail a working connection over it
    return client


def run(client, command: str, timeout: int = 600) -> dict:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    stdin.close()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    return {"exit_code": code, "stdout": out, "stderr": err}


def _read_remote(sftp, path: str) -> str:
    try:
        with sftp.open(path, "r") as fh:
            return fh.read().decode("utf-8", "replace")
    except IOError:
        return ""


def install_key(client) -> dict:
    """Authorize the local public key on the rig so the password is no longer needed.

    Windows OpenSSH has a trap here: for a user in the Administrators group the
    server reads C:/ProgramData/ssh/administrators_authorized_keys and IGNORES
    that user's own ~/.ssh/authorized_keys. Writing only the latter looks like it
    worked and still fails every login. So: detect admin membership first and
    write whichever file sshd will actually read.

    The file is written over SFTP rather than by echoing into a shell, because
    an OpenSSH public key contains characters that quoting through two nested
    shells mangles.
    """
    pub_path = Path.home() / ".ssh" / "id_ed25519.pub"
    if not pub_path.is_file():
        return {"ok": False, "error": f"no public key at {pub_path}"}
    pub = pub_path.read_text(encoding="utf-8").strip()

    groups = run(client, "whoami /groups")
    is_admin = ADMIN_SID in groups["stdout"]

    sftp = client.open_sftp()
    try:
        if is_admin:
            target = ADMIN_KEYS
        else:
            home = run(client, "echo %USERPROFILE%")["stdout"].strip()
            home = home.replace("\\", "/")
            ssh_dir = posixpath.join(home, ".ssh")
            try:
                sftp.stat(ssh_dir)
            except IOError:
                sftp.mkdir(ssh_dir)
            target = posixpath.join(ssh_dir, "authorized_keys")

        existing = _read_remote(sftp, target)
        if pub in existing:
            added = False
        else:
            body = existing
            if body and not body.endswith("\n"):
                body += "\n"
            body += pub + "\n"
            with sftp.open(target, "w") as fh:
                fh.write(body.encode("utf-8"))
            added = True
    finally:
        sftp.close()

    acl_note = ""
    if is_admin:
        # sshd refuses administrators_authorized_keys outright if anyone beyond
        # Administrators and SYSTEM can write it -- so this is not optional.
        acl = run(
            client,
            'icacls "C:\\ProgramData\\ssh\\administrators_authorized_keys" '
            "/inheritance:r /grant Administrators:F /grant SYSTEM:F",
        )
        acl_note = "acl ok" if acl["exit_code"] == 0 else f"acl failed: {acl['stderr'][:200]}"

    return {
        "ok": True,
        "added": added,
        "admin": is_admin,
        "target": target,
        "acl": acl_note,
    }


PROBE_COMMANDS = [
    ("whoami", "whoami"),
    ("os", "powershell -NoProfile -Command (Get-CimInstance Win32_OperatingSystem).Caption"),
    ("gpus", "nvidia-smi --query-gpu=index,name,memory.total,compute_cap --format=csv,noheader"),
    ("driver", "nvidia-smi --query-gpu=driver_version --format=csv,noheader"),
    ("python", "python --version"),
    ("cuda", "nvcc --version"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true",
                    help="connect and report host identity, GPUs, driver, python")
    ap.add_argument("--install-key", action="store_true",
                    help="authorize the local public key so no password is needed again")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("command", nargs="*", help="command to run on the rig")
    args = ap.parse_args()

    client = connect()
    try:
        if args.probe:
            result = {}
            for key, cmd in PROBE_COMMANDS:
                res = run(client, cmd)
                result[key] = (res["stdout"].strip() or res["stderr"].strip()
                               or f"(exit {res['exit_code']})")
            if args.json:
                json.dump(result, sys.stdout, ensure_ascii=False)
                sys.stdout.write("\n")
            else:
                for key, value in result.items():
                    first, *rest = value.splitlines() or [""]
                    print(f"{key:8} {first}")
                    for line in rest:
                        print(f"{'':8} {line}")
            return 0

        if args.install_key:
            res = install_key(client)
            if args.json:
                json.dump(res, sys.stdout, ensure_ascii=False)
                sys.stdout.write("\n")
            else:
                if not res.get("ok"):
                    print(f"key install FAILED: {res.get('error')}")
                else:
                    state = "added" if res["added"] else "already present"
                    scope = "admin account" if res["admin"] else "standard account"
                    print(f"key install OK ({state}, {scope}) -> {res['target']} {res['acl']}")
            return 0 if res.get("ok") else 1

        if not args.command:
            ap.error("give a command, or use --probe / --install-key")
        res = run(client, " ".join(args.command), timeout=args.timeout)
        if args.json:
            json.dump(res, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            if res["stdout"]:
                sys.stdout.write(res["stdout"])
            if res["stderr"]:
                sys.stderr.write(res["stderr"])
        return res["exit_code"]
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
