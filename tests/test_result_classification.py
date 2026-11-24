
from datetime import datetime

from result_processor import store_prepared_results

BASE_RECORD = {
    "MachineId": 3,
    "HostComputerName": "AdroitHost",
    "LabNo": "69275",
    "TestCode": "AST",
    "Result": "25.168010",
    "ResultDateTime": datetime(2026, 10, 21, 10, 34),
    "Reviewed": False,
    "ResultTransmitted": False,
    "Status": True,
    "LastModifiedDate": None,
    "AnalyzerTestName": "Aspartate Aminotransferase",
    "AnalyzerUnit": "U/L",
    "ConfiguredUnit": "U/L",
    "ChannelNo": 2,
}


def run_case(label, record):
    print(f"\n--- {label} ---")

    inserted, duplicates, conflicts, errors = (
        store_prepared_results([record])
    )

    print("Inserted:", len(inserted))
    print("Duplicates:", len(duplicates))
    print("Conflicts:", len(conflicts))
    print("Errors:", len(errors))

    if errors:
        print("Error details:", errors)

    assert not inserted, "Unexpected insert in classification test"
    assert not errors, "Database lookup or storage error occurred"

    return duplicates, conflicts


# Case 1: Same result and timestamp as the existing AST record.
duplicates, conflicts = run_case(
    "Identical retransmission",
    BASE_RECORD.copy(),
)

assert len(duplicates) == 1
assert len(conflicts) == 0


# Case 2: Same sample/test, but a different result.
different_result = BASE_RECORD.copy()
different_result["Result"] = "26.000000"

duplicates, conflicts = run_case(
    "Conflicting result value",
    different_result,
)

assert len(duplicates) == 0
assert len(conflicts) == 1


# Case 3: Same result, but a different timestamp.
different_timestamp = BASE_RECORD.copy()
different_timestamp["ResultDateTime"] = datetime(
    2026, 10, 21, 11, 34
)

duplicates, conflicts = run_case(
    "Conflicting result timestamp",
    different_timestamp,
)

assert len(duplicates) == 0
assert len(conflicts) == 1



print("\nAll classification tests passed.")
