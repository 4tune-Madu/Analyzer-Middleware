from hl7_parser import HL7Message


raw_message = (
    "MSH|^~\\&|||||20261007090000||QRY^Q02|15|P|2.3.1\r"
    "QRD|20261007090000|R|D|1|||RD|162354|OTH|||T|\r"
    "QRF|||||RCT|COR|ALL||"
)


message = HL7Message(raw_message)


print("Message Type:")
print(message.message_type)

print("\nControl ID:")
print(message.control_id)

print("\nQRD Segment:")
print(message.get_segment("QRD"))

print("\nQRD-8:")
print(message.get_field("QRD", 8))