
import server
import result_processor

# Mock only the mapping lookup.
result_processor.get_active_machine_test_by_result_name = (
    lambda machine_id, result_name: {
        "test_code": "AST",
        "unit": "U/L",
        "channel_no": 2,
        "result_name": result_name,
    }
    if result_name == "Aspartate Aminotransferase"
    else None
)

# Mock database storage.
server.store_prepared_results = lambda records: (
    [
        {
            "id": 101,
            "LabNo": record["LabNo"],
            "TestCode": record["TestCode"],
            "Result": record["Result"],
        }
        for record in records
    ],
    [],
    [],
    [],
)

hl7_text = (
    "MSH|^~\\&|||||20261031100000||ORU^R01|501|P|2.3.1||||||ASCII|||\r"
    "OBR|1|0019||||||20261031100000\r"
    "OBX|1|NM|AST|Aspartate Aminotransferase|25.168010|U/L|||||F||0.000000|20261031100000\r"
)

message = server.HL7Message(hl7_text)

analyzer = {
    "name": "Test BS-240",
    "machine_id": 3,
}

success, ack_code, message_text, status_code = (
    server.handle_result_message(message, analyzer)
)

ack = server.build_ack_response(
    message,
    acknowledgment_code=ack_code,
    message_text=message_text,
    status_code=status_code,
)

print("\nGenerated ACK:")
print(ack.replace("\r", "\n"))

assert success is True
assert ack_code == "AA"
assert status_code == 0

assert "ACK^R01" in ack
assert "MSA|AA|501|" in ack

print("PASS: ORU result processing succeeded.")
print("PASS: Correct ACK^R01 was generated.")
print("All ORU acknowledgement tests passed.")
