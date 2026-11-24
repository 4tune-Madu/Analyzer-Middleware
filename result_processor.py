
from datetime import datetime


from database import (
    get_active_machine_test_by_result_name,
    machine_result_exists,
    get_machine_result_matches,
    get_connection,
    insert_machine_result_in_transaction,
)



def prepare_result_records(message, machine_id):
    """
    Prepare eligible observations independently.

    Does not insert or update database records.

    Returns:
        (prepared_records, skipped_placeholders, errors)
    """

    message_errors = message.validate_result_message()

    if message_errors:
        return [], [], message_errors

    lab_no = message.get_lab_no()
    observations = message.get_observation_results()

    prepared_records = []
    skipped_placeholders = []
    errors = []

    for index, observation in enumerate(observations, start=1):

        # Step 1: Ignore documented analyzer placeholders.
        if observation.get("is_placeholder", False):
            skipped_placeholders.append({
                "obx_index": index,
                "test_name": observation.get("test_name"),
                "result": observation.get("result"),
            })
            continue

        test_name = (observation.get("test_name") or "").strip()

        if not test_name:
            errors.append(
                f"OBX #{index}: Missing analyzer test name."
            )
            continue

        # Step 2: Only process final results.
        if observation.get("status") != "F":
            errors.append(
                f"OBX #{index}: Result is not final "
                f"(status: {observation.get('status')!r})."
            )
            continue

        # Step 3: Validate OBX-14 timestamp.
        timestamp_text = (
            observation.get("result_datetime") or ""
        ).strip()

        try:
            result_datetime = datetime.strptime(
                timestamp_text,
                "%Y%m%d%H%M%S",
            )
        except (ValueError, TypeError):
            errors.append(
                f"OBX #{index}: Invalid or missing OBX-14 "
                f"timestamp: {timestamp_text!r}."
            )
            continue

        # Step 4: Validate result value.
        result_value = observation.get("result")

        if result_value is None or not str(result_value).strip():
            errors.append(
                f"OBX #{index}: Missing result value."
            )
            continue

        result_value = str(result_value).strip()

        if len(result_value) > 30:
            errors.append(
                f"OBX #{index}: Result exceeds 30 characters."
            )
            continue

        # Only validate numeric results as numbers.
        if observation.get("value_type") == "NM":
            from decimal import Decimal, InvalidOperation

            try:
                numeric_value = Decimal(result_value)
                if not numeric_value.is_finite():
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                errors.append(
                    f"OBX #{index}: Invalid numeric result "
                    f"{result_value!r}."
                )
                continue

        # Step 5: Find active LIS mapping.
        mapping = get_active_machine_test_by_result_name(
            machine_id,
            test_name,
        )

        if mapping is None:
            errors.append(
                f"OBX #{index}: No active mapping for "
                f"{test_name!r} on MachineId {machine_id}."
            )
            continue

        test_code = mapping.get("test_code")

        if not test_code:
            errors.append(
                f"OBX #{index}: Mapping has no TestCode."
            )
            continue

        # Step 6: Prepare record.
        prepared_records.append({
            "MachineId": machine_id,
            "HostComputerName": "AdroitHost",
            "LabNo": lab_no,
            "TestCode": test_code,
            "Result": result_value,
            "ResultDateTime": result_datetime,
            "Reviewed": False,
            "ResultTransmitted": False,
            "Status": True,
            "LastModifiedDate": None,

            # Diagnostics only; not destination columns.
            "AnalyzerTestName": test_name,
            "AnalyzerUnit": observation.get("unit"),
            "ConfiguredUnit": mapping.get("unit"),
            "ChannelNo": mapping.get("channel_no"),
            "OriginalResult": observation.get("original_result"),
            "AnalyzerResultDateTime": timestamp_text,
        })

    return prepared_records, skipped_placeholders, errors


def check_result_duplicates(records):
    """
    Classify prepared records without writing to the database.

    Returns:
        (new_candidates, potential_duplicates)
    """

    new_candidates = []
    potential_duplicates = []

    for record in records:
        exists = machine_result_exists(
            record["MachineId"],
            record["LabNo"],
            record["TestCode"],
        )

        if exists:
            potential_duplicates.append(record)
        else:
            new_candidates.append(record)

    return new_candidates, potential_duplicates




def store_prepared_results(records):
    """
    Skip exact duplicates and insert new runs in one transaction.

    Different result values are stored for the LIS to handle.
    Returns:
        inserted, skipped_duplicates, conflicts, errors
    """

    from decimal import Decimal, InvalidOperation

    inserted = []
    skipped_duplicates = []
    conflicts = []
    errors = []
    candidates = []

    # Step 1: Find exact duplicates.
    for record in records:
        try:
            existing_records = get_machine_result_matches(
                record["MachineId"],
                record["LabNo"],
                record["TestCode"],
            )
        except Exception as exc:
            errors.append({
                "LabNo": record["LabNo"],
                "TestCode": record["TestCode"],
                "error": f"Database lookup failed: {exc}",
            })
            continue

        duplicate = False

        try:
            incoming_value = Decimal(str(record["Result"]).strip())
        except (InvalidOperation, ValueError):
            errors.append({
                "LabNo": record["LabNo"],
                "TestCode": record["TestCode"],
                "error": f"Invalid numeric result: {record['Result']!r}",
            })
            continue

        incoming_timestamp = record["ResultDateTime"]

        for existing in existing_records:
            try:
                existing_value = Decimal(
                    str(existing["result"]).strip()
                )
            except (InvalidOperation, ValueError):
                # An existing non-numeric result cannot be an exact
                # numeric duplicate of this incoming result.
                continue

            existing_timestamp = existing["result_datetime"]

            if (
                existing_value == incoming_value
                and existing_timestamp == incoming_timestamp
            ):
                skipped_duplicates.append({
                    **record,
                    "ExistingId": existing["id"],
                })
                duplicate = True
                break

        if not duplicate:
            candidates.append(record)

    # Avoid inserting a partial batch if a lookup or value error occurred.
    if errors:
        return inserted, skipped_duplicates, conflicts, errors

    if not candidates:
        return inserted, skipped_duplicates, conflicts, errors

    # Step 2: Insert all candidates in one transaction.
    connection = None
    pending_insertions = []
    current_record = candidates[0]

    try:
        connection = get_connection()
        cursor = connection.cursor()

        for current_record in candidates:
            inserted_id = insert_machine_result_in_transaction(
                cursor,
                current_record,
            )

            pending_insertions.append({
                "id": inserted_id,
                "LabNo": current_record["LabNo"],
                "TestCode": current_record["TestCode"],
                "Result": current_record["Result"],
            })

        connection.commit()
        inserted = pending_insertions

    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception as rollback_exc:
                errors.append({
                    "error": f"Transaction rollback failed: {rollback_exc}",
                })

        errors.append({
            "LabNo": current_record["LabNo"],
            "TestCode": current_record["TestCode"],
            "error": f"Batch insertion failed; transaction rolled back: {exc}",
        })

    finally:
        if connection is not None:
            connection.close()

    return inserted, skipped_duplicates, conflicts, errors
