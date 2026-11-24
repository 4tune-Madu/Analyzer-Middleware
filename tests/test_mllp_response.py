
from server import send_hl7_response

class FakeConnection:
    def __init__(self):
        self.sent_data = []

    def sendall(self, data):
        self.sent_data.append(data)


connection = FakeConnection()
response = "MSA|AA|15|Message accepted|||0|\r"

send_hl7_response(connection, response)

assert len(connection.sent_data) == 1

framed = connection.sent_data[0]

assert framed.startswith(b"\x0b")
assert framed.endswith(b"\x1c\x0d")
assert framed[1:-2] == response.encode("ascii")

print("PASS: MLLP start byte is correct.")
print("PASS: MLLP end bytes are correct.")
print("PASS: HL7 payload is preserved.")
print("All MLLP response framing tests passed.")
