
from datetime import datetime

from database import (
    insert_machine_result,
    get_existing_machine_results,
)

record = {
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
}

inserted_id = insert_machine_result(record)
print(f"Inserted row ID: {inserted_id}")

results = get_existing_machine_results("69275", 3)

for result in results:
    if result["Id"] == inserted_id:
        print("Verified inserted record:")
        print(result)
        break
else:
    print("WARNING: Inserted record was not found during verification.")
