
from hl7_parser import HL7Message
from server import build_dsr_response


raw_query = (
    "MSH|^~\\&|||||20261027190000||QRY^Q02|15|P|2.3.1||||||ASCII|||\r"
    "QRD|20261027190000|R|D|1|||RD|0019|OTH|||T|\r"
    "QRF||||||RCT|COR|ALL||\r"
)

message = HL7Message(raw_query)

tests = [
    {"channel_no": 1, "test_code": "D-Bill-V"},
    {"channel_no": 2, "test_code": "AST"},
    {"channel_no": 5, "test_code": "y-GT"},
]

response = build_dsr_response(
    message=message,
    analyzer={"machine_id": 3, "name": "Mindray BS-240"},
    lab_no="0019",
    tests=tests,
)

print(response.replace("\r", "\n"))

assert "DSR^Q03" in response
assert "DSP|21||0019|||" in response
assert "DSP|29||1^^^|||" in response
assert "DSP|30||2^^^|||" in response
assert "DSP|31||5^^^|||" in response
assert "DSC||\r" in response

print("DSR builder test passed.")
