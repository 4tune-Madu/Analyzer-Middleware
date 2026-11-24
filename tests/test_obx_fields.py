
from hl7_parser import HL7Message


raw_message = "\r".join([
    "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|18|P|2.3.1",
    "PID|1|||TEST-PATIENT",
    "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
    "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F||25.168010|20260921131741|||0|",
    "OBX|5|NM||Placeholder Test|-268435455.000000|U/L|-|N|||F||0.000000|19000101000000|||0|",
])

message = HL7Message(raw_message)
observations = message.get_observation_results()

for observation in observations:
    print("\nTest:", observation["test_name"])
    print("Result:", observation["result"])
    print("Original result:", observation["original_result"])
    print("OBX-14 timestamp:", observation["result_datetime"])
    print("Placeholder:", observation["is_placeholder"])

assert observations[0]["result_datetime"] == "20260921131741"
assert observations[0]["is_placeholder"] is False

assert observations[1]["result_datetime"] == "19000101000000"
assert observations[1]["is_placeholder"] is True

print("\nOBX field extraction tests passed.")
