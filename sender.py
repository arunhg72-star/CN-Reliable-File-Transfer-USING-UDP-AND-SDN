
import socket
import json
import os
import sys
import hashlib
import time

RECEIVER_IP = "127.0.0.1"
PORT = 5001

CHUNK_SIZE = 1024
ACK_TIMEOUT = 1.0
MAX_RETRIES = 10
BUFFER_SIZE = 4096


def send_reliably(sock, packet, expected_ack, address):
    """Send a packet and retry until its matching ACK arrives."""
    for attempt in range(MAX_RETRIES + 1):
        sock.sendto(packet, address)

        try:
            response, source = sock.recvfrom(BUFFER_SIZE)
            if source != address:
                continue

            ack = json.loads(response.decode("utf-8"))

            if ack.get("type") == "ACK" and ack.get("seq") == expected_ack:
                return True

        except (socket.timeout, UnicodeDecodeError, json.JSONDecodeError):
            pass

        print(
            f"Timeout/wrong ACK for sequence {expected_ack}; "
            f"retry {attempt + 1}/{MAX_RETRIES}"
        )

    return False


def main():
    file_path = (
        sys.argv[1] if len(sys.argv) > 1
        else os.path.join("test_files", "sample.txt")
    )

    if not os.path.isfile(file_path):
        print("Error: File not found:", file_path)
        return

    filename = os.path.basename(file_path)

    with open(file_path, "rb") as file:
        file_data = file.read()

    file_hash = hashlib.sha256(file_data).hexdigest()
    total_chunks = (len(file_data) + CHUNK_SIZE - 1) // CHUNK_SIZE

    metadata = {
        "type": "META",
        "filename": filename,
        "size": len(file_data),
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "sha256": file_hash,
    }

    address = (RECEIVER_IP, PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.settimeout(ACK_TIMEOUT)

        print("Sending file:", filename)
        print("File size:", len(file_data), "bytes")
        print("Total data packets:", total_chunks)

        if not send_reliably(
            sender, json.dumps(metadata).encode("utf-8"), -1, address
        ):
            print("Transfer failed: metadata was not acknowledged.")
            return

        for seq in range(total_chunks):
            start = seq * CHUNK_SIZE
            chunk = file_data[start:start + CHUNK_SIZE]

            packet = json.dumps({
                "type": "DATA",
                "seq": seq,
                "data": chunk.hex(),
            }).encode("utf-8")

            if not send_reliably(sender, packet, seq, address):
                print(f"Transfer failed at packet {seq}.")
                return

            print(f"Packet {seq + 1}/{total_chunks} acknowledged.")

        if not send_reliably(
            sender,
            json.dumps({"type": "END", "seq": total_chunks}).encode("utf-8"),
            total_chunks,
            address,
        ):
            print("Transfer failed: completion was not acknowledged.")
            return

        print("Transfer completed successfully.")
        print("SHA-256:", file_hash)


if __name__ == "__main__":
    main()
