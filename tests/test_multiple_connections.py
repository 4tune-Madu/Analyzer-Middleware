
import socket
import time

HOST = "127.0.0.1"
PORT = 17118  # Use your server's actual PORT value.

# Open first connection.
connection_a = socket.create_connection((HOST, PORT))
print("Analyzer A connected.")

time.sleep(1)

# Open second connection while A is still connected.
connection_b = socket.create_connection((HOST, PORT))
print("Analyzer B connected.")

time.sleep(2)

# Close only connection A.
connection_a.close()
print("Analyzer A disconnected.")

time.sleep(2)

# Confirm B is still connected.
try:
    connection_b.sendall(b"\x0b")
    print("Analyzer B connection is still active.")
except OSError as error:
    print(f"Analyzer B connection failed: {error}")

connection_b.close()
print("Analyzer B disconnected.")
