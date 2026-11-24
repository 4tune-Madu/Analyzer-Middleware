
from unittest.mock import patch

from server import handle_result_message


analyzer = {
    "name": "Mindray BS-240 Test",
    "machine_id": 3,
}


class FakeMessage:
    def get_observation_results(self):
        return []

    def get_lab_no(self):
        return "69275"

    def get_result_datetime(self):
        return "20261021103400"


def run_case(
    label,
    prepared_records,
    expected_success,
    expected_ack_code,
    expected_status_code,
    preparation_errors=None,
    skipped_placeholders=None,
    storage_result=None,
    preparation_exception=None,
    storage_exception=None,
):
    preparation_errors = preparation_errors or []
    skipped_placeholders = skipped_placeholders or []

    with (
        patch("server.prepare_result_records") as mock_prepare,
        patch("server.store_prepared_results") as mock_store,
    ):
        if preparation_exception:
            mock_prepare.side_effect = preparation_exception
        else:
            mock_prepare.return_value = (
                prepared_records,
                skipped_placeholders,
                preparation_errors,
            )

        if storage_exception:
            mock_store.side_effect = storage_exception
        else:
            mock_store.return_value = storage_result or (
                [], [], [], []
            )

        outcome = handle_result_message(
            FakeMessage(),
            analyzer,
        )

    success, ack_code, message_text, status_code = outcome

    print(f"\n--- {label} ---")
    print("Success:", success)
    print("ACK code:", ack_code)
    print("Message:", message_text)
    print("Status code:", status_code)

    assert success == expected_success
    assert ack_code == expected_ack_code
    assert status_code == expected_status_code

    print("PASS")
    return outcome


# Case 1: Successfully stored.
run_case(
    "Successful storage",
    prepared_records=[{"TestCode": "AST"}],
    expected_success=True,
    expected_ack_code="AA",
    expected_status_code=0,
    storage_result=(
        [{
            "id": 9001,
            "LabNo": "69275",
            "TestCode": "AST",
            "Result": "25.168010",
        }],
        [],
        [],
        [],
    ),
)

# Case 2: Identical duplicate.
run_case(
    "Identical duplicate",
    prepared_records=[{"TestCode": "AST"}],
    expected_success=True,
    expected_ack_code="AA",
    expected_status_code=0,
    storage_result=(
        [],
        [{
            "LabNo": "69275",
            "TestCode": "AST",
            "ExistingId": 561398,
        }],
        [],
        [],
    ),
)

# Case 3: Placeholders only; nothing needs storing.
run_case(
    "No eligible records",
    prepared_records=[],
    expected_success=True,
    expected_ack_code="AA",
    expected_status_code=0,
    skipped_placeholders=[{
        "obx_index": 1,
        "test_name": "AST",
        "result": "-268435455.000000",
    }],
)

# Case 4: Preparation/mapping error.
run_case(
    "Preparation error",
    prepared_records=[],
    expected_success=False,
    expected_ack_code="AE",
    expected_status_code=101,
    preparation_errors=["No active mapping for test."],
)

# Case 5: Database failure.
run_case(
    "Storage failure",
    prepared_records=[{"TestCode": "AST"}],
    expected_success=False,
    expected_ack_code="AR",
    expected_status_code=207,
    storage_exception=RuntimeError(
        "Simulated database failure"
    ),
)

# Case 6: Mixed valid and invalid observations.
# Valid results should be stored, but the message receives AE.
with (
    patch("server.prepare_result_records") as mock_prepare,
    patch("server.store_prepared_results") as mock_store,
):
    mock_prepare.return_value = (
        [{"TestCode": "AST", "Result": "25.168010"}],
        [],
        ["OBX #2: No active mapping for 'UNKNOWN TEST'."],
    )

    mock_store.return_value = (
        [{
            "id": 9002,
            "LabNo": "69275",
            "TestCode": "AST",
            "Result": "25.168010",
        }],
        [],
        [],
        [],
    )

    outcome = handle_result_message(FakeMessage(), analyzer)

success, ack_code, message_text, status_code = outcome

print("\n--- Mixed valid and invalid observations ---")
print("Success:", success)
print("ACK code:", ack_code)
print("Message:", message_text)
print("Status code:", status_code)

assert success is False
assert ack_code == "AE"
assert status_code == 101

mock_store.assert_called_once()

print("PASS")

print("\nACK handler test cases completed.")
