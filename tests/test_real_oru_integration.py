
from hl7_parser import HL7Message
from server import handle_result_message, build_ack_response

raw_message = (
    "MSH|^~\\&|BS240|LAB|LIS|LAB|20261031120000||ORU^R01|TEST-ORU-001|P|2.3.1\r"
    "PID|||69275||TEST PATIENT\r"
    "OBR|1|69275|||CHEMISTRY\r"
    "OBX|1|NM|ALB II|Albumin|42.5|g/L|||||F||0.000000|20261031120000\r"
)

message = HL7Message(raw_message)

analyzer = {
    "machine_id": 3,
    "name": "Mindray BS-240",
    "ip_address": "10.0.14.36"
}

print("\n--- PROCESSING ORU MESSAGE ---")

success, ack_code, message_text, status_code = (
    handle_result_message(message, analyzer)
)

print("\n--- RESULT ---")
print("Success:", success)
print("ACK code:", ack_code)
print("Message:", message_text)
print("Status:", status_code)

print("\n--- GENERATED ACK ---")

ack = build_ack_response(
    message,
    ack_code,
    message_text,
    status_code
)

print(ack)
