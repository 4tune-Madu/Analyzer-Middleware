
import server

analyzer = {
    "name": "Test BS-240",
    "machine_id": 3,
}

# Mock database functions — no database access.
server.get_samples_by_lab_no = lambda lab_no: [
    {
        "LabSampleId": 1,
        "LabNo": lab_no,
        "ServiceId": 100,
        "MachineId": None,
    }
]

server.get_machine_tests_for_services = lambda service_ids, machine_id: [
    {"test_id": 1, "channel_no": 1},
    {"test_id": 2, "channel_no": 2},
]

# Capture responses instead of sending them over a socket.
sent_responses = []

def mock_send(connection, response):
    sent_responses.append(response)

server.send_hl7_response = mock_send

query_text = (
    "MSH|^~\\&|||||20261027190000||QRY^Q02|15|P|2.3.1||||||ASCII|||\r"
    "QRD|20261027190000|R|D|1|||RD|0019|OTH|||T|\r"
    "QRF||||||RCT|COR|ALL||\r"
)

# Simulate the MLLP-framed message body passed to handle_message().
fake_connection = object()

server.handle_message(
    query_text.encode("utf-8"),
    analyzer,
    fake_connection,
)

assert len(sent_responses) == 2, (
    f"Expected 2 responses, got {len(sent_responses)}"
)

assert "QCK^Q02" in sent_responses[0]
assert "QAK|SR|OK|" in sent_responses[0]

assert "DSR^Q03" in sent_responses[1]
assert "DSP|21||0019|||" in sent_responses[1]

print("\nPASS: handle_message sent QCK first and DSR second.")
print("PASS: No socket or database access was needed.")
