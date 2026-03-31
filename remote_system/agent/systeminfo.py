# systeminfo.py
import platform
import socket
import os

def get_system_info():
    try:
        info = {
            "hostname": socket.gethostname(),
            "user": os.getlogin(),
            "os": platform.system(),
            "os_version": platform.version()
        }
        return str(info)
    except Exception as e:
        return f"[SYSTEMINFO ERROR] {e}"
