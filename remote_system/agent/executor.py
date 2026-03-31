# executor.py
import subprocess

def execute_command(cmd):
    try:
        output = subprocess.getoutput(cmd)
        return f"[EXECUTED] {cmd}\n{output}"
    except Exception as e:
        return f"[ERROR] {e}"

