import socket

HOST = "0.0.0.0"
PORT = 17118

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((HOST, PORT))
server.listen(5)

print(f"Test listener running on {HOST}:{PORT}")
print("Waiting for an incoming connection...")

while True:
    conn, address = server.accept()

    print(f"Connection received from: {address}")

    conn.sendall(b"Middleware connection test successful")

    conn.close()