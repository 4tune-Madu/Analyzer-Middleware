
import server

analyzer = {
    "name": "Test BS-240",
    "machine_id": 3,
}

# Simulate a DSR awaiting acknowledgement.
with server.pending_dsr_lock:
    server.pending_dsr_acknowledgements[
        (3, "1793125142")
    ] = "0019"

ack_text = (
    "MSH|^~\\&|||Company|Product|"
    "20261031100000||ACK^Q03|501|P|2.3.1||||||ASCII|||\r"
    "MSA|AA|1793125142|Message accepted|||0|\r"
    "ERR|0|\r"
)

message = server.HL7Message(ack_text)

assert message.message_type == "ACK^Q03"

server.handle_dsr_acknowledgement(message, analyzer)

# Confirm the pending acknowledgement was removed.
with server.pending_dsr_lock:
    assert (
        3, "1793125142"
    ) not in server.pending_dsr_acknowledgements

print("\nPASS: ACK^Q03 was recognized.")
print("PASS: DSR control ID was correlated.")
print("PASS: Pending acknowledgement was cleared.")

# Test a negative acknowledgement.
with server.pending_dsr_lock:
    server.pending_dsr_acknowledgements[
        (3, "1793125143")
    ] = "0020"

negative_ack_text = (
    "MSH|^~\\&|||Company|Product|"
    "20261031100000||ACK^Q03|502|P|2.3.1||||||ASCII|||\r"
    "MSA|AR|1793125143|Sample information rejected|||206|\r"
    "ERR|206|\r"
)

negative_message = server.HL7Message(negative_ack_text)

server.handle_dsr_acknowledgement(
    negative_message,
    analyzer,
)

with server.pending_dsr_lock:
    assert (
        3, "1793125143"
    ) not in server.pending_dsr_acknowledgements

print("PASS: Negative ACK^Q03 was processed.")
print("\nAll ACK^Q03 tests passed.")
