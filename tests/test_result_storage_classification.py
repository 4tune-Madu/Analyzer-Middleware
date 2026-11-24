
from datetime import datetime
from unittest.mock import MagicMock, patch

from result_processor import store_prepared_results


MACHINE_ID = 3
LAB_NO = "69275"
TEST_CODE = "AST"

EXISTING_TIMESTAMP = datetime(2026, 10, 21, 10, 34, 0)


def make_record(result, timestamp=EXISTING_TIMESTAMP):
    return {
        "MachineId": MACHINE_ID,
        "HostComputerName": "AdroitHost",
        "LabNo": LAB_NO,
        "TestCode": TEST_CODE,
        "Result": result,
        "ResultDateTime": timestamp,
        "Reviewed": False,
        "ResultTransmitted": False,
        "Status": True,
        "LastModifiedDate": None,
    }


def run_test_case(existing_records, incoming_record):
    fake_connection = MagicMock()

    with (
        patch(
            "result_processor.get_machine_result_matches",
            return_value=existing_records,
        ),
        patch(
            "result_processor.get_connection",
            return_value=fake_connection,
        ) as mock_get_connection,
        patch(
            "result_processor.insert_machine_result_in_transaction",
            return_value=999,
        ) as mock_insert,
    ):
        result = store_prepared_results([incoming_record])

    return (
        result,
        fake_connection,
        mock_get_connection,
        mock_insert,
    )


def check(label, existing_records, incoming_record,
          expected_inserted, expected_duplicates):

    (
        (inserted, duplicates, conflicts, errors),
        connection,
        get_connection,
        insert,
    ) = run_test_case(existing_records, incoming_record)

    print(f"\n--- {label} ---")
    print("Inserted:", len(inserted))
    print("Duplicates:", len(duplicates))
    print("Conflicts:", len(conflicts))
    print("Errors:", len(errors))

    assert len(inserted) == expected_inserted
    assert len(duplicates) == expected_duplicates
    assert len(conflicts) == 0
    assert len(errors) == 0

    if expected_inserted:
        insert.assert_called_once()
        connection.commit.assert_called_once()
    else:
        insert.assert_not_called()
        get_connection.assert_not_called()

    print("PASS")


# Case 1: Same numeric value and same timestamp.
# Different textual formatting must still count as a duplicate.
check(
    "Identical result",
    [{
        "id": 561398,
        "result": "25.168010",
        "result_datetime": EXISTING_TIMESTAMP,
    }],
    make_record("25.16801"),
    expected_inserted=0,
    expected_duplicates=1,
)


# Case 2: Different value, same timestamp.
# Store it; the LIS handles the changed result.
check(
    "Changed value, same timestamp",
    [{
        "id": 561398,
        "result": "25.168010",
        "result_datetime": EXISTING_TIMESTAMP,
    }],
    make_record("27.500000"),
    expected_inserted=1,
    expected_duplicates=0,
)


# Case 3: Same value, different timestamp.
# Store it as a new run.
check(
    "Same value, different timestamp",
    [{
        "id": 561398,
        "result": "25.168010",
        "result_datetime": EXISTING_TIMESTAMP,
    }],
    make_record(
        "25.168010",
        datetime(2026, 10, 21, 10, 40, 0),
    ),
    expected_inserted=1,
    expected_duplicates=0,
)


# Case 4: No existing record.
check(
    "New result",
    [],
    make_record("30.100000"),
    expected_inserted=1,
    expected_duplicates=0,
)


# Case 5: Two new results are inserted in one transaction.
def test_batch_insert_commits_once():
    records = [
        make_record("31.100000"),
        {
            **make_record("42.200000"),
            "TestCode": "ALT",
        },
    ]

    fake_connection = MagicMock()
    fake_cursor = MagicMock()
    fake_connection.cursor.return_value = fake_cursor

    with (
        patch(
            "result_processor.get_machine_result_matches",
            return_value=[],
        ),
        patch(
            "result_processor.get_connection",
            return_value=fake_connection,
        ),
        patch(
            "result_processor.insert_machine_result_in_transaction",
            side_effect=[1001, 1002],
        ) as mock_insert,
    ):
        inserted, duplicates, conflicts, errors = (
            store_prepared_results(records)
        )

    assert len(inserted) == 2
    assert [item["id"] for item in inserted] == [1001, 1002]
    assert duplicates == []
    assert conflicts == []
    assert errors == []

    assert mock_insert.call_count == 2
    fake_connection.commit.assert_called_once()
    fake_connection.rollback.assert_not_called()
    fake_connection.close.assert_called_once()

    print("\n--- Batch insert commits once ---")
    print("PASS")


# Case 6: Failure on the second insert rolls back the batch.
def test_batch_insert_rolls_back_on_failure():
    records = [
        make_record("31.100000"),
        {
            **make_record("42.200000"),
            "TestCode": "ALT",
        },
    ]

    fake_connection = MagicMock()
    fake_cursor = MagicMock()
    fake_connection.cursor.return_value = fake_cursor

    with (
        patch(
            "result_processor.get_machine_result_matches",
            return_value=[],
        ),
        patch(
            "result_processor.get_connection",
            return_value=fake_connection,
        ),
        patch(
            "result_processor.insert_machine_result_in_transaction",
            side_effect=[1001, RuntimeError("Simulated insert failure")],
        ) as mock_insert,
    ):
        inserted, duplicates, conflicts, errors = (
            store_prepared_results(records)
        )

    assert inserted == []
    assert duplicates == []
    assert conflicts == []
    assert len(errors) == 1
    assert "transaction rolled back" in errors[0]["error"]

    assert mock_insert.call_count == 2
    fake_connection.commit.assert_not_called()
    fake_connection.rollback.assert_called_once()
    fake_connection.close.assert_called_once()

    print("\n--- Batch insert rolls back on failure ---")
    print("PASS")


test_batch_insert_commits_once()
test_batch_insert_rolls_back_on_failure()

print("\nAll storage classification tests passed.")
