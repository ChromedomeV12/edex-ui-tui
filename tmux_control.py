"""Best-effort read-only tmux queries.

A busy server or VM scheduling pause is not a renderer failure. Callers keep
their last confirmed state/frame and retry later. Never retry input mutations:
repeating send-keys could execute a key twice.
"""
import subprocess


def query(*args, timeout=.5):
    try:
        result=subprocess.run(['tmux',*args],capture_output=True,text=True,timeout=timeout)
    except (subprocess.TimeoutExpired,OSError):
        return None
    return result.stdout.strip() if result.returncode==0 else None
