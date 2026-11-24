
from hl7_parser import HL7Message
from server import build_ack_response

raw_message = "\r".join([
    "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|6|P|2.3.1",
    "PID|1|||TEST-PATIENT",
    "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
    "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F||25.168010|20260921131741|||0|",
])

message = HL7Message(raw_message)

positive_ack = build_ack_response(message)

negative_ack = build_ack_response(
    message,
    acknowledgment_code="AR",
    message_text="Application internal error",
    status_code=207,
)

print("POSITIVE ACK:")
print(repr(positive_ack))

print("\nNEGATIVE ACK:")
print(repr(negative_ack))

assert "ACK^R01|6|" in positive_ack
assert "MSA|AA|6|Message accepted|||0|" in positive_ack

assert "ACK^R01|6|" in negative_ack
assert (
    "MSA|AR|6|Application internal error|||207|"
    in negative_ack
)

print("\nACK construction tests passed.")
