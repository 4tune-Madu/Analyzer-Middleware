
import server
import result_processor

# Mock only the analyzer test mapping.
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

hl7_text = (
    "MSH|^~\\&|||||20261031100000||ORU^R01|501|P|2.3.1||||||ASCII|||\r"
    "OBR|1|0019||||||20261031100000\r"
    "OBX|1|NM|AST|Aspartate Aminotransferase|25.168010|U/L|||||F||0.000000|20261031100000\r"
)


message = server.HL7Message(hl7_text)

records, placeholders, errors = (
    result_processor.prepare_result_records(
        message,
        machine_id=3,
    )
)

print("\nPrepared records:", records)
print("Placeholders:", placeholders)
print("Errors:", errors)

assert len(records) == 1
assert records[0]["LabNo"] == "0019"
assert records[0]["TestCode"] == "AST"
assert records[0]["Result"] == "25.168010"

assert len(placeholders) == 0
assert len(errors) == 0

print("\nPASS: Actual HL7 parser and result preparation work.")
