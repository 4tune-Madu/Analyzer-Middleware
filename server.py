
import socket
import threading
from analyzer import identify_analyzer
from config import (
    HOST,
    PORT,
    START_OF_MESSAGE,
    END_OF_MESSAGE,
)
from database import (
    get_machine_by_ip,
    get_samples_by_lab_no,
    get_machine_tests_for_services,
)
from hl7_parser import HL7Message
from result_processor import (
    prepare_result_records,
    store_prepared_results,
)

# Tracks DSR messages awaiting analyzer acknowledgement.
# Key: (MachineId, DSR control ID)
# Value: LabNo

pending_dsr_acknowledgements = {}

pending_dsr_lock = threading.Lock()

def receive_mllp_messages(connection):
    buffer = b""

    while True:
        data = connection.recv(1024)

        if not data:
            break

        buffer += data

        while True:
            start_index = buffer.find(START_OF_MESSAGE)

            if start_index == -1:
                break

            end_index = buffer.find(
                END_OF_MESSAGE,
                start_index + len(START_OF_MESSAGE),
            )

            if end_index == -1:
                break

            message_start = (
                start_index + len(START_OF_MESSAGE)
            )

            hl7_message = buffer[message_start:end_index]

            buffer = buffer[
                end_index + len(END_OF_MESSAGE):
            ]

            yield hl7_message


def send_hl7_response(connection, response):
    """Send an HL7 response using MLLP framing."""

    framed_response = (
        START_OF_MESSAGE
        + response.encode("ascii")
        + END_OF_MESSAGE
    )

    connection.sendall(framed_response)


def build_qck_response(message, status):
    """Build the BS-240 QCK^Q02 response."""

    control_id = message.control_id
    timestamp = message.get_field("MSH", 6)

    response = (
        "MSH|^~\\&|||||"
        f"{timestamp}||QCK^Q02|{control_id}|P|2.3.1||||||ASCII|||\r"
        f"MSA|AA|{control_id}|Message accepted|||0|\r"
        "ERR|0|\r"
        f"QAK|SR|{status}|\r"
    )

    return response

def handle_query_message(message, analyzer):
    """Handle analyzer sample queries and build QCK/DSR responses."""

    lab_no = message.get_field("QRD", 8)

    if not lab_no:
        print("ERROR: LabNo not found in QRD-8.")
        return None

    print(f"Lab No      : {lab_no}")

    try:
        samples = get_samples_by_lab_no(lab_no)

        if not samples:
            print(f"No sample records found for LabNo {lab_no}.")
            return [build_qck_response(message, "NF")]

        print(f"Records found: {len(samples)}")

        service_ids = list(dict.fromkeys(
            sample["ServiceId"]
            for sample in samples
            if sample.get("ServiceId") is not None
        ))

        if not service_ids:
            print("ERROR: No service IDs found for this sample.")
            return [build_qck_response(message, "AE")]

        machine_id = analyzer["machine_id"]

        tests = get_machine_tests_for_services(
            service_ids,
            machine_id,
        )

        if not tests:
            print(
                f"No active analyzer test mappings found for "
                f"LabNo {lab_no}, MachineId {machine_id}."
            )
            return [build_qck_response(message, "AE")]

        dsr_response = build_dsr_response(
            message,
            analyzer,
            lab_no,
            tests,
        )

        dsr_msh = next(
            segment
            for segment in dsr_response.split("\r")
            if segment.startswith("MSH|")
        )

        dsr_control_id = dsr_msh.split("|")[9]

        with pending_dsr_lock:
            pending_dsr_acknowledgements[
                (analyzer["machine_id"], dsr_control_id)
            ] = lab_no

        print(
            f"Awaiting ACK^Q03: "
            f"MachineId={analyzer['machine_id']} | "
            f"DSR Control ID={dsr_control_id} | "
            f"LabNo={lab_no}"
        )

        # Only report OK when the DSR has been built successfully.
        qck_response = build_qck_response(message, "OK")

        print(f"Mapped services: {len(service_ids)}")
        print(f"Mapped tests   : {len({t['test_id'] for t in tests})}")

        return [qck_response, dsr_response]

    except Exception as error:
        print(f"Query processing failed: {error}")
        return [build_qck_response(message, "AE")]




def handle_dsr_acknowledgement(message, analyzer):
    """Process the analyzer's ACK^Q03 response to a DSR."""

    machine_id = analyzer["machine_id"]

    ack_code = message.get_field("MSA", 1)
    dsr_control_id = message.get_field("MSA", 2)
    ack_text = message.get_field("MSA", 3)
    status_code = message.get_field("MSA", 6)

    if not dsr_control_id:
        print("ERROR: ACK^Q03 has no MSA-2 control ID.")
        return

    key = (machine_id, dsr_control_id)

    with pending_dsr_lock:
        lab_no = pending_dsr_acknowledgements.pop(key, None)

    if lab_no is None:
        print(
            "WARNING: Received ACK^Q03 for an unknown or "
            "already acknowledged DSR. "
            f"MachineId={machine_id}, "
            f"DSR Control ID={dsr_control_id}"
        )
        return

    if ack_code == "AA":
        print(
            f"DSR ACCEPTED by analyzer: "
            f"LabNo={lab_no}, "
            f"MachineId={machine_id}, "
            f"DSR Control ID={dsr_control_id}"
        )

    elif ack_code in ("AE", "AR"):
        print(
            f"DSR REJECTED by analyzer: "
            f"LabNo={lab_no}, "
            f"MachineId={machine_id}, "
            f"DSR Control ID={dsr_control_id}, "
            f"ACK={ack_code}, "
            f"Status={status_code}, "
            f"Message={ack_text}"
        )

    else:
        print(
            f"WARNING: Unknown ACK^Q03 acknowledgement code: "
            f"{ack_code}"
        )


def handle_result_message(message, analyzer):
    """
    Validate, prepare, and store analyzer results.

    Returns:
        (success, ack_code, message_text, status_code)
    """

    print("Received ORU^R01 analyzer result message.")
    print(f"Analyzer: {analyzer['name']}")

    machine_id = analyzer["machine_id"]

    print("Parsed observations:")
    for result in message.get_observation_results():
        print(result)

    print(f"LabNo: {message.get_lab_no()}")
    print("OBR-7 DateTime:", message.get_result_datetime())

    # Step 1: Validate the message and prepare result records.
    try:
        records, skipped_placeholders, errors = (
            prepare_result_records(
                message,
                machine_id,
            )
        )

        print(f"Prepared records: {len(records)}")
        print(f"Skipped placeholders: {len(skipped_placeholders)}")

        for placeholder in skipped_placeholders:
            print(
                f"PLACEHOLDER SKIPPED: OBX #{placeholder['obx_index']} | "
                f"Test={placeholder['test_name']!r} | "
                f"Result={placeholder['result']!r}"
            )
    except Exception as exc:
        print(f"Unexpected preparation error: {exc}")
        return (
            False,
            "AR",
            "Application internal error",
            207,
        )

    if errors:
        print("Result validation or mapping errors:")
        for error in errors:
            print(f" - {error}")

        print(
            f"Continuing with {len(records)} valid prepared "
            "record(s)."
        )

        # If nothing is eligible for storage, reject the message.
        if not records:
            return (
                False,
                "AE",
                "Required field missing",
                101,
            )

    # A message containing only placeholders has no records to store.
    # It was processed successfully, provided validation found no errors.
    if not records:
        print("No eligible result records. Nothing to store.")
        return (
            True,
            "AA",
            "Message accepted",
            0,
        )

    print(f"Prepared records: {len(records)}")

    # Step 2: Store new results and skip identical duplicates.
    try:
        inserted, duplicates, conflicts, storage_errors = (
            store_prepared_results(records)
        )
    except Exception as exc:
        print(f"Unexpected storage error: {exc}")
        return (
            False,
            "AR",
            "Application internal error",
            207,
        )

    # Step 3: Report inserted results.
    for record in inserted:
        print(
            f"STORED: ID={record['id']} | "
            f"LabNo={record['LabNo']} | "
            f"TestCode={record['TestCode']} | "
            f"Result={record['Result']}"
        )

    # Step 4: Report identical duplicates.
    for record in duplicates:
        print(
            f"IDENTICAL RESULT ALREADY STORED: "
            f"LabNo={record['LabNo']} | "
            f"TestCode={record['TestCode']} | "
            f"ExistingId={record.get('ExistingId')}"
        )

    # Step 5: Report any unexpected conflicts.
    # The agreed storage policy is to insert changed results.
    for record in conflicts:
        print(
            "UNEXPECTED RESULT CONFLICT: "
            f"LabNo={record['LabNo']} | "
            f"TestCode={record['TestCode']} | "
            f"IncomingResult={record['Result']} | "
            f"ExistingRecords={record['ExistingRecords']}"
        )

    # Step 6: Report storage errors.
    for error in storage_errors:
        print(f"STORAGE ERROR: {error}")

    # Only acknowledge success when storage completed without errors.
    if conflicts or storage_errors:
        print(
            "Storage incomplete. Positive ACK withheld."
        )

        return (
            False,
            "AR",
            "Application internal error",
            207,
        )

    print(
        f"Storage complete: {len(inserted)} inserted, "
        f"{len(duplicates)} identical duplicates skipped."
    )

    if errors:
        print(
            "Some observations failed validation or mapping. "
            "Returning a negative ACK."
        )
        return (
            False,
            "AE",
            "One or more observations failed validation",
            101,
        )

    return (
        True,
        "AA",
        "Message accepted",
        0,
    )


def handle_message(hl7_bytes, analyzer, connection):
    """Parse and dispatch incoming HL7 messages."""

    hl7_text = hl7_bytes.decode(
        "utf-8",
        errors="replace",
    )

    message = HL7Message(hl7_text)

    print("\nHL7 MESSAGE")
    print("--------------------------------")
    print(hl7_text)
    print("--------------------------------")

    print(f"Analyzer    : {analyzer['name']}")
    print(f"Machine ID  : {analyzer['machine_id']}")
    print(f"Message Type: {message.message_type}")
    print(f"Control ID  : {message.control_id}")

    if message.message_type == "QRY^Q02":
        responses = handle_query_message(message, analyzer)

        if responses:
            for response in responses:
                send_hl7_response(connection, response)

    elif message.message_type == "ORU^R01":
        (
            success,
            ack_code,
            message_text,
            status_code,
        ) = handle_result_message(message, analyzer)

        response = build_ack_response(
            message,
            acknowledgment_code=ack_code,
            message_text=message_text,
            status_code=status_code,
        )

        send_hl7_response(connection, response)
    elif message.message_type == "ACK^Q03":
        handle_dsr_acknowledgement(message, analyzer)
    else:
        print(
            f"Unsupported message type: "
            f"{message.message_type}"
        )

def build_ack_response(
    message,
    acknowledgment_code="AA",
    message_text="Message accepted",
    status_code=0,
):
    """Build the BS-240 ACK^R01 response."""

    control_id = message.control_id
    timestamp = message.get_field("MSH", 6)

    return (
        "MSH|^~\\&|||Company|Product|"
        f"{timestamp}||ACK^R01|{control_id}|P|2.3.1|||0||ASCII|||\r"
        f"MSA|{acknowledgment_code}|{control_id}|"
        f"{message_text}|||{status_code}|\r"
    )


def build_dsr_response(message, analyzer, lab_no, tests):
    """
    Build a single-sample DSR^Q03 response.

    The caller supplies the already-resolved analyzer tests.
    Patient/sample metadata is optional in this MVP.
    """
    from datetime import datetime

    control_id = message.control_id
    query_timestamp = message.get_field("MSH", 6)

    # Use a fresh control ID for this outgoing DSR.
    # Keep it simple for the MVP; persistent sequencing can be added later.
    dsr_control_id = str(int(datetime.now().timestamp()))

    def safe_field(value):
        """Prevent HL7 delimiters and non-ASCII text from corrupting fields."""
        if value is None:
            return ""
        value = str(value)
        value = value.replace("|", " ").replace("^", " ")
        value = value.replace("~", " ").replace("\\", " ")
        value = value.replace("&", " ")
        return value.encode("ascii", errors="replace").decode("ascii")

    # Reuse the original QRD and QRF query definitions.
    qrd = message.get_segment("QRD")
    qrf = message.get_segment("QRF")

    if not qrd:
        raise ValueError("Cannot build DSR: missing QRD segment.")

    if not qrf:
        qrf = "QRF||||||RCT|COR|ALL||"

    segments = [
        (
            "MSH|^~\\&|||Company|Product|"
            f"{datetime.now():%Y%m%d%H%M%S}||DSR^Q03|"
            f"{dsr_control_id}|P|2.3.1||||||ASCII|||"
        ),
        f"MSA|AA|{control_id}|Message accepted|||0|",
        "ERR|0|",
        "QAK|SR|OK|",
        "|".join(qrd),
        "|".join(qrf),
    ]

    # DSP items 1-20 are optional, but item positions must remain intact.
    optional_items = {
        1: "",
        2: "",
        3: "",
        4: "",
        5: "",
        6: "",
        7: "",
        8: "",
        9: "",
        10: "",
        11: "",
        12: "",
        13: "",
        14: "",
        15: "",
        16: "",
        17: "",
        18: "",
        19: "",
        20: "",
    }

    for item_number in range(1, 21):
        value = safe_field(optional_items[item_number])
        segments.append(f"DSP|{item_number}||{value}|||")

    # DSP-21 is the sample barcode.
    segments.append(f"DSP|21||{safe_field(lab_no)}|||")

    # Remaining sample metadata is optional in the MVP.
    for item_number in range(22, 29):
        segments.append(f"DSP|{item_number}|||||")

    # Test IDs are sent in DSP-29 onward as TestID^^^.
    unique_tests = {}

    for test in tests:
        channel_no = test.get("channel_no")
    
        if channel_no is None:
            raise ValueError("Mapped test has no channel_no.")
    
        unique_tests.setdefault(int(channel_no), test)
    
    for item_number, channel_no in enumerate(unique_tests, start=29):
        segments.append(
            f"DSP|{item_number}||{channel_no}^^^|||"
        )
        

    # Empty continuation pointer for a single-sample response.
    segments.append("DSC||")

    return "\r".join(segments) + "\r"


def handle_client_connection(connection, address):
    """Handle one analyzer connection independently."""

    analyzer_ip = address[0]

    try:
        print(
            f"\nConnection from "
            f"{analyzer_ip}:{address[1]}"
        )

        # Identify analyzer using its IP.
        analyzer = get_machine_by_ip(analyzer_ip)

        # Temporary fallback for localhost testing.
        if analyzer is None:
            analyzer = identify_analyzer(analyzer_ip)

        if analyzer is None:
            print(f"Unknown analyzer IP: {analyzer_ip}")
            return

        print(f"Analyzer: {analyzer['name']}")
        print(f"Machine ID: {analyzer['machine_id']}")

        for hl7_bytes in receive_mllp_messages(connection):
            handle_message(
                hl7_bytes,
                analyzer,
                connection,
            )

        print(f"Client disconnected: {analyzer['name']}")

    except Exception as error:
        print(f"Connection processing error: {error}")

    finally:
        connection.close()



def main():
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server_socket:

        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        server_socket.bind((HOST, PORT))
        server_socket.listen(10)

        print(f"MLLP server listening on {HOST}:{PORT}")

        while True:
            connection, address = server_socket.accept()

            # Give every analyzer connection its own worker.
            worker = threading.Thread(
                target=handle_client_connection,
                args=(connection, address),
                daemon=True,
            )

            worker.start()

if __name__ == "__main__":
    main()
