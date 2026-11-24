
import server

# Mock result preparation.
server.prepare_result_records = lambda message, machine_id: (
    [
        {
            "id": 101,
            "LabNo": "0019",
            "TestCode": "AST",
            "Result": "25.168010",
        }
    ],
    [],
    [],
)

# Mock storage.
server.store_prepared_results = lambda records: (
    records,  # inserted
    [],       # duplicates
    [],       # conflicts
    [],       # storage errors
)

hl7_text = (
    "MSH|^~\\&|||||20261031100000||ORU^R01|501|P|2.3.1||||||ASCII|||\r"
    "OBR|1|0019||||||20261031100000\r"
    "OBX|1|NM|AST^Aspartate Aminotransferase||25.168010|||||F||||20261031100000\r"
)

message = server.HL7Message(hl7_text)

analyzer = {
    "name": "Test BS-240",
    "machine_id": 3,
}

result = server.handle_result_message(message, analyzer)

success, ack_code, message_text, status_code = result

assert success is True
assert ack_code == "AA"
assert status_code == 0

print("\nPASS: Valid result was prepared and stored.")
print("PASS: Handler returned positive acknowledgement.")
print("All result-handler flow tests passed.")
