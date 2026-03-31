# build_bat.py
import os

# Get the script's directory and build paths relative to it
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, "output")
agent_path = os.path.join(project_root, "agent", "agent.py")

server_ip = input("Enter server IP: ")
server_port = input("Enter server port: ")

bat_content = f"""@echo off
cd /d "{os.path.join(project_root, 'agent')}"
python agent.py --server {server_ip}:{server_port}
pause
"""

os.makedirs(output_dir, exist_ok=True)
bat_file = os.path.join(output_dir, "agent.bat")
with open(bat_file, "w") as f:
    f.write(bat_content)

print(f"agent.bat created at: {bat_file}")
