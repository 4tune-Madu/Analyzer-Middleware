
import socket
import threading

import server


HOST = "127.0.0.1"

# Mock database lookups. No SQL Server access.
server.get_machine_by_ip = lambda ip: {
    "name": "Test BS-240",
    "machine_id": 3,
}

server.get_samples_by_lab_no = lambda lab_no: [
    {
        "LabSampleId": 1,
        "LabNo": lab_no,
        "ServiceId": 100,
        "MachineId": None,
    }
]

server.get_machine_tests_for_services = (
    lambda service_ids, machine_id: [
        {"test_id": 1, "channel_no": 1},
        {"test_id": 2, "channel_no": 2},
    ]
)


def build_query(lab_no, control_id):
    return (
        f"MSH|^~\\&|||||20261031100000||QRY^Q02|"
        f"{control_id}|P|2.3.1||||||ASCII|||\r"
        f"QRD|20261031100000|R|D|1|||RD|{lab_no}|OTH|||T|\r"
        "QRF||||||RCT|COR|ALL||\r"
    )


def send_query(connection, lab_no, control_id):
    message = build_query(lab_no, control_id).encode("ascii")

    connection.sendall(
        server.START_OF_MESSAGE
        + message
        + server.END_OF_MESSAGE
    )


def receive_two_responses(connection):
    buffer = b""
    responses = []

    while len(responses) < 2:
        data = connection.recv(4096)

        if not data:
            raise ConnectionError("Connection closed before both responses arrived.")

        buffer += data

        while True:
            start = buffer.find(server.START_OF_MESSAGE)

            if start == -1:
                break

            end = buffer.find(
                server.END_OF_MESSAGE,
                start + len(server.START_OF_MESSAGE),
            )

            if end == -1:
                break

            payload_start = start + len(server.START_OF_MESSAGE)
            payload = buffer[payload_start:end]

            responses.append(payload.decode("ascii"))

            buffer = buffer[
                end + len(server.END_OF_MESSAGE):
            ]

            if len(responses) == 2:
                break

    return responses


listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind((HOST, 0))
listener.listen(2)

port = listener.getsockname()[1]

workers = []


def accept_clients():
    for _ in range(2):
        connection, address = listener.accept()

        worker = threading.Thread(
            target=server.handle_client_connection,
            args=(connection, address),
        )

        workers.append(worker)
        worker.start()


accept_thread = threading.Thread(target=accept_clients)
accept_thread.start()

client_a = socket.create_connection((HOST, port))
client_b = socket.create_connection((HOST, port))

print("Both test analyzers connected.")

try:
    # Both analyzers send queries while connected.
    send_query(client_a, "0019", "101")
    send_query(client_b, "0020", "202")

    print("Both HL7 queries sent.")

    responses_a = receive_two_responses(client_a)
    responses_b = receive_two_responses(client_b)

    # Verify Analyzer A responses.
    assert "QCK^Q02" in responses_a[0]
    assert "QAK|SR|OK|" in responses_a[0]
    assert "MSA|AA|101|" in responses_a[0]

    assert "DSR^Q03" in responses_a[1]
    assert "DSP|21||0019|||" in responses_a[1]

    # Verify Analyzer B responses.
    assert "QCK^Q02" in responses_b[0]
    assert "QAK|SR|OK|" in responses_b[0]
    assert "MSA|AA|202|" in responses_b[0]

    assert "DSR^Q03" in responses_b[1]
    assert "DSP|21||0020|||" in responses_b[1]

    print("\nPASS: Analyzer A received its own QCK and DSR.")
    print("PASS: Analyzer B received its own QCK and DSR.")
    print("PASS: Responses were not mixed between connections.")
    print("\nAll simultaneous HL7 tests passed.")

finally:
    client_a.close()
    client_b.close()

    accept_thread.join(timeout=5)

    for worker in workers:
        worker.join(timeout=5)

    listener.close()
