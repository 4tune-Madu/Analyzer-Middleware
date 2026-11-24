
from hl7_parser import HL7Message
from database import get_machine_test_by_result_name
from result_processor import (
    prepare_result_records,
    store_prepared_results,
)


raw_message = "\r".join([
    "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|18|P|2.3.1",
    "PID|1|||TEST-PATIENT",
    "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400",
    "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F||25.168010|20260921131741|||0|",
])

message = HL7Message(raw_message)


# STEP 1: Validate the HL7 message
errors = message.validate_result_message()

if errors:
    print("Validation failed:")
    for error in errors:
        print(f" - {error}")
    raise SystemExit(1)

print("Result validation passed.")


# STEP 2: Inspect the incoming result and its mapping
lab_no = message.get_lab_no()
result_datetime = message.get_result_datetime()
observations = message.get_observation_results()

print(f"LabNo: {lab_no}")
print(f"Result DateTime: {result_datetime}")

for observation in observations:
    test_name = observation["test_name"]

    mapping = get_machine_test_by_result_name(3, test_name)

    print(f"\nAnalyzer test: {test_name}")
    print(f"Result: {observation['result']}")
    print(f"Status: {observation['status']}")

    if mapping is None:
        print("Mapping not found.")
        continue

    print(f"TestCode: {mapping['test_code']}")
    print(f"Channel: {mapping['channel_no']}")
    print(f"Mapped result name: {mapping['result_name']}")
    print(f"Configured unit: {mapping['unit']}")


# STEP 3: Prepare records for storage
records, skipped_placeholders, errors = (
    prepare_result_records(
        message,
        3,
    )
)

print("\nPreparation errors:", errors)
print("Prepared record count:", len(records))
print("Skipped placeholders:", len(skipped_placeholders))

for record in records:
    print(record)

for placeholder in skipped_placeholders:
    print(
        f"PLACEHOLDER SKIPPED: OBX #{placeholder['obx_index']} | "
        f"Test={placeholder['test_name']!r} | "
        f"Result={placeholder['result']!r}"
    )


# STEP 4: Test duplicate detection, conflict detection, and insertion
print("\n--- Storage Test ---")

if errors:
    print("Storage skipped: preparation failed.")
    raise SystemExit(1)

if not records:
    print("Storage skipped: no prepared records.")
    raise SystemExit(1)

inserted, duplicates, conflicts, storage_errors = (
    store_prepared_results(records)
)


# STEP 5: Display inserted records
print("\nInserted:", len(inserted))

for record in inserted:
    print(
        "INSERTED:",
        record["id"],
        record["LabNo"],
        record["TestCode"],
        record["Result"],
    )


# STEP 6: Display skipped duplicates
print("\nSkipped duplicates:", len(duplicates))

for record in duplicates:
    print(
        "DUPLICATE:",
        record["LabNo"],
        record["TestCode"],
        record["Result"],
        "ExistingId:",
        record["ExistingId"],
    )


# STEP 7: Display conflicting results
print("\nConflicts:", len(conflicts))

for record in conflicts:
    print(
        "CONFLICT:",
        record["LabNo"],
        record["TestCode"],
        record["Result"],
        "ExistingRecords:",
        record["ExistingRecords"],
    )


# STEP 8: Display storage errors
print("\nStorage errors:", len(storage_errors))

for error in storage_errors:
    print("ERROR:", error)


# STEP 9: Report the outcome
if storage_errors or conflicts:
    raise SystemExit(1)

print("\nStorage pipeline completed.")
