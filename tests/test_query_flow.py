
import server

# Fake analyzer
analyzer = {
    "name": "Test BS-240",
    "machine_id": 3,
}

# Fake sample and test mappings — no database access.
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

query_text = (
    "MSH|^~\\&|||||20261027190000||QRY^Q02|15|P|2.3.1||||||ASCII|||\r"
    "QRD|20261027190000|R|D|1|||RD|0019|OTH|||T|\r"
    "QRF||||||RCT|COR|ALL||\r"
)

message = server.HL7Message(query_text)

responses = server.handle_query_message(message, analyzer)

assert len(responses) == 2
assert "QCK^Q02" in responses[0]
assert "QAK|SR|OK|" in responses[0]
assert "DSR^Q03" in responses[1]
assert "DSP|21||0019|||" in responses[1]
assert "DSP|29||1^^^|||" in responses[1]
assert "DSP|30||2^^^|||" in responses[1]

print("PASS: Sample found -> QCK OK followed by DSR.")

# Case 2: sample not found
server.get_samples_by_lab_no = lambda lab_no: []

responses = server.handle_query_message(message, analyzer)

assert len(responses) == 1
assert "QCK^Q02" in responses[0]
assert "QAK|SR|NF|" in responses[0]

print("PASS: Sample missing -> QCK NF only.")

# Case 3: sample found, but no test mappings
server.get_samples_by_lab_no = lambda lab_no: [
    {
        "LabSampleId": 1,
        "LabNo": lab_no,
        "ServiceId": 100,
        "MachineId": None,
    }
]
server.get_machine_tests_for_services = lambda service_ids, machine_id: []

responses = server.handle_query_message(message, analyzer)

assert len(responses) == 1
assert "QCK^Q02" in responses[0]
assert "QAK|SR|AE|" in responses[0]

print("PASS: No test mappings -> QCK AE only.")
print("All query-flow tests passed.")
