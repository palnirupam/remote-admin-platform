# server.py
import socket
import threading

clients = []

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")
    while True:
        try:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            print(f"[{addr}] {msg}")
            conn.send("ACK".encode())
        except:
            break
    print(f"[DISCONNECTED] {addr}")
    conn.close()

def start_server(host="0.0.0.0", port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[STARTED] Server listening on {host}:{port}")
    while True:
        conn, addr = server.accept()
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
