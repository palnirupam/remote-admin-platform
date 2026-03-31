# sender.py
def send_to_server(sock, message):
    try:
        sock.send(message.encode())
    except Exception as e:
        print("[SENDER ERROR]", e)
