
from unittest.mock import patch

from hl7_parser import HL7Message
from server import handle_result_message


ANALYZER = {
    "name": "Mindray BS-240 Test",
    "machine_id": 3,
}


def build_message():
    segments = [
        "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|MIXED001|P|2.3.1",
        "PID|1|||TEST-PATIENT",
        "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
        (
            "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F"
            "||25.168010|20260921131741|||0|"
        ),
        (
            "OBX|6|NM||Unknown Analyzer Test|12.500000|U/L|-|N|||F"
            "||12.500000|20260921131841|||0|"
        ),
        (
            "OBX|5|NM||Placeholder Test|-268435455.000000|U/L|-|N|||F"
            "||0.000000|19000101000000|||0|"
        ),
    ]
    return HL7Message("\r".join(segments))


def fake_mapping(machine_id, test_name):
    if (
        machine_id == 3
        and test_name == "Aspartate Aminotransferase"
    ):
        return {
            "test_code": "AST",
            "result_name": "Aspartate Aminotransferase",
            "unit": "U/L",
            "channel_no": 2,
        }

    return None


def main():
    message = build_message()

    # Mock mapping and storage-related database access.
    with (
        patch(
            "result_processor.get_active_machine_test_by_result_name",
            side_effect=fake_mapping,
        ),
        patch(
            "server.store_prepared_results",
            return_value=(
                [{
                    "id": 9003,
                    "LabNo": "69275",
                    "TestCode": "AST",
                    "Result": "25.168010",
                }],
                [],
                [],
                [],
            ),
        ) as mock_store,
    ):
        outcome = handle_result_message(message, ANALYZER)

    success, ack_code, message_text, status_code = outcome

    print("\n--- Combined mixed-result flow ---")
    print("Outcome:", outcome)

    assert mock_store.call_count == 1

    stored_records = mock_store.call_args.args[0]
    assert len(stored_records) == 1
    assert stored_records[0]["TestCode"] == "AST"
    assert stored_records[0]["LabNo"] == "69275"

    assert success is False
    assert ack_code == "AE"
    assert status_code == 101

    print("PASS: Valid result reached mocked storage.")
    print("PASS: Unmapped observation was reported.")
    print("PASS: Placeholder was skipped.")
    print("PASS: Mixed message returned AE.")
    print("No real database writes were performed.")


if __name__ == "__main__":
    main()
