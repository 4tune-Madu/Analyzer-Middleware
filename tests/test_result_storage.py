
from database import get_existing_machine_results
from result_processor import store_prepared_results

record = {
    "MachineId": 3,
    "HostComputerName": "AdroitHost",
    "LabNo": "69275",
    "TestCode": "AST",
    "Result": "25.168010",
    "ResultDateTime": None,
    "Reviewed": False,
    "ResultTransmitted": False,
    "Status": True,
    "LastModifiedDate": None,
}

before = get_existing_machine_results("69275", 3)
print("Records before:", len(before))

inserted, duplicates, errors = store_prepared_results([record])

after = get_existing_machine_results("69275", 3)
print("Records after:", len(after))

print("Inserted:", len(inserted))
print("Skipped duplicates:", len(duplicates))
print("Errors:", errors)

assert len(inserted) == 0
assert len(duplicates) == 1
assert len(after) == len(before)

print("Duplicate handling test passed.")
