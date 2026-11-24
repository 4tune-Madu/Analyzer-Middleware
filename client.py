import socket
import time


HOST = "127.0.0.1"
PORT = 7118

START_OF_MESSAGE = b"\x0b"
END_OF_MESSAGE = b"\x1c\x0d"


messages = [
    (
        "MSH|^~\\&|||||20261007090000||QRY^Q02|15|P|2.3.1\r"
        "QRD|20261007090000|R|D|1|||RD|162354|OTH|||T|\r"
        "QRF|||||RCT|COR|ALL||"
    ),
    (
        "MSH|^~\\&|||||20261007090100||QRY^Q02|16|P|2.3.1\r"
        "QRD|20261007090100|R|D|1|||RD|162355|OTH|||T|\r"
        "QRF|||||RCT|COR|ALL||"
    ),
    (
        "MSH|^~\\&|||||20261007090200||QRY^Q02|17|P|2.3.1\r"
        "QRD|20261007090200|R|D|1|||RD|69275|OTH|||T|\r"
        "QRF|||||RCT|COR|ALL||"
    ),
    (
        "MSH|^~\\&|Manufacturer|analyzer|||20261012103500||ORU^R01|18|P|2.3.1||||0||ASCII|||\r"
        "PID|1|||TEST-PATIENT\r"
        "OBR|1|69275|3|Manufacturer^BS-240|N||20261012103400\r"
        "OBX|1|NM|1^GLU||5.2|mmol/L|3.9-6.1|N|||F\r"
        "OBX|2|NM|2^UREA||4.1|mmol/L|2.5-7.1|N|||F\r"
    ),
    (
        "MSH|^~\\&|Manufacturer|analyzer|||20261021150000||ORU^R01|18|P|2.3.1||||0||ASCII|||\r"
        "PID|1|||TEST-PATIENT\r"
        "OBR|1|69275|3|Manufacturer^BS-240|N||20261021103400\r"
        "OBX|4|NM||Aspartate Aminotransferase|25.168010|U/L|-|N|||F||25.168010|20260921131741|||0|\r"
    ),
]


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:

    client_socket.connect((HOST, PORT))

    print(f"Connected to {HOST}:{PORT}")

    for number, hl7_message in enumerate(messages, start=1):

        mllp_message = (
            START_OF_MESSAGE
            + hl7_message.encode("utf-8")
            + END_OF_MESSAGE
        )

        print(f"\nSending message {number}...")
        print(f"Message type: {hl7_message.split('|')[8]}")

        client_socket.sendall(mllp_message)

        ack = client_socket.recv(1024)

        print(f"Received ACK: {ack!r}")

        time.sleep(1)

    print("\nAll messages sent.")

    time.sleep(1)

