
from unittest.mock import patch

from hl7_parser import HL7Message
from result_processor import prepare_result_records


def build_message(obx_segments):
    segments = [
        "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|25|P|2.3.1",
        "PID|1|||TEST-PATIENT",
        "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
    ]
    return HL7Message("\r".join(segments + obx_segments))


def fake_mapping(machine_id, test_name):
    if test_name == "Aspartate Aminotransferase":
        return {
            "test_code": "AST",
            "result_name": "Aspartate Aminotransferase",
            "unit": "U/L",
            "channel_no": 2,
        }

    return None


valid_obx = (
    "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F"
    "||25.168010|20260921131741|||0|"
)

placeholder_obx = (
    "OBX|5|NM||Placeholder Test|-268435455.000000|U/L|-|N|||F"
    "||0.000000|19000101000000|||0|"
)


with patch(
    "result_processor.get_active_machine_test_by_result_name",
    side_effect=fake_mapping,
):
    # Case 1: A valid result plus a placeholder.
    message = build_message([valid_obx, placeholder_obx])
    records, skipped_placeholders, errors = (
        prepare_result_records(
            message,
            3,
        )
    )

    print("\n--- Valid result plus placeholder ---")
    print("Prepared records:", len(records))
    print("Skipped placeholders:", len(skipped_placeholders))
    print("Errors:", errors)

    assert errors == []
    assert len(records) == 1
    assert records[0]["TestCode"] == "AST"
    assert records[0]["Result"] == "25.168010"
    assert records[0]["AnalyzerResultDateTime"] == "20260921131741"

    print("PASS")

    # Case 2: A placeholder by itself.
    message = build_message([placeholder_obx])
    records, skipped_placeholders, errors = prepare_result_records(message, 3)

    print("\n--- Placeholder only ---")
    print("Prepared records:", len(records))
    print("Skipped placeholders:", len(skipped_placeholders))
    print("Errors:", errors)

    assert errors == []
    assert records == []
    assert len(skipped_placeholders) == 1

    print("PASS")


from unittest.mock import patch

from hl7_parser import HL7Message
from result_processor import prepare_result_records


def build_message(obx_segments):
    segments = [
        "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|25|P|2.3.1",
        "PID|1|||TEST-PATIENT",
        "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
    ]
    return HL7Message("\r".join(segments + obx_segments))


def fake_mapping(machine_id, test_name):
    if test_name == "Aspartate Aminotransferase":
        return {
            "test_code": "AST",
            "result_name": "Aspartate Aminotransferase",
            "unit": "U/L",
            "channel_no": 2,
        }

    return None


valid_obx = (
    "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F"
    "||25.168010|20260921131741|||0|"
)

placeholder_obx = (
    "OBX|5|NM||Placeholder Test|-268435455.000000|U/L|-|N|||F"
    "||0.000000|19000101000000|||0|"
)


with patch(
    "result_processor.get_active_machine_test_by_result_name",
    side_effect=fake_mapping,
):
    # Case 1: A valid result plus a placeholder.
    message = build_message([valid_obx, placeholder_obx])
    records, skipped_placeholders, errors = (
        prepare_result_records(
            message,
            3,
        )
    )

    print("\n--- Valid result plus placeholder ---")
    print("Prepared records:", len(records))
    print("Skipped placeholders:", len(skipped_placeholders))
    print("Errors:", errors)

    assert errors == []
    assert len(records) == 1
    assert records[0]["TestCode"] == "AST"
    assert records[0]["Result"] == "25.168010"
    assert records[0]["AnalyzerResultDateTime"] == "20260921131741"

    print("PASS")

    # Case 2: A placeholder by itself.
    message = build_message([placeholder_obx])
    records, skipped_placeholders, errors = prepare_result_records(message, 3)

    print("\n--- Placeholder only ---")
    print("Prepared records:", len(records))
    print("Skipped placeholders:", len(skipped_placeholders))
    print("Errors:", errors)

    assert errors == []
    assert records == []
    assert len(skipped_placeholders) == 1

    print("PASS")


    # Case 3: Valid result + unmapped observation + placeholder.
    unmapped_obx = (
        "OBX|6|NM||Unknown Analyzer Test|12.500000|U/L|-|N|||F"
        "||12.500000|20260921131841|||0|"
    )

    message = build_message([
        valid_obx,
        unmapped_obx,
        placeholder_obx,
    ])

    records, skipped_placeholders, errors = (
        prepare_result_records(message, 3)
    )

    print("\n--- Mixed valid, unmapped, and placeholder observations ---")
    print("Prepared records:", len(records))
    print("Skipped placeholders:", len(skipped_placeholders))
    print("Errors:", errors)

    assert len(records) == 1
    assert records[0]["TestCode"] == "AST"
    assert len(skipped_placeholders) == 1
    assert len(errors) == 1
    assert "Unknown Analyzer Test" in errors[0]

    print("PASS")


print("\nAll placeholder preparation tests passed.")
