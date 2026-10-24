
import socket
import json
import os
import hashlib

HOST = "0.0.0.0"
PORT = 5001
BUFFER_SIZE = 8192
RECEIVE_TIMEOUT = 30
OUTPUT_FOLDER = "received_files"


def send_ack(sock, address, seq):
    ack = {"type": "ACK", "seq": seq}
    sock.sendto(json.dumps(ack).encode("utf-8"), address)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind((HOST, PORT))
        receiver.settimeout(RECEIVE_TIMEOUT)

        print(f"Receiver listening on port {PORT}...")

        try:
            data, sender_address = receiver.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            print("Timed out waiting for file metadata.")
            return

        try:
            metadata = json.loads(data.decode("utf-8"))
            if metadata.get("type") != "META":
                raise ValueError("Expected META packet")

            filename = os.path.basename(metadata["filename"])
            file_size = int(metadata["size"])
            chunk_size = int(metadata["chunk_size"])
            total_chunks = int(metadata["total_chunks"])
            expected_hash = metadata["sha256"]

            expected_chunks = (
                (file_size + chunk_size - 1) // chunk_size
                if chunk_size > 0 else -1
            )

            if (
                not filename or file_size < 0 or chunk_size <= 0
                or total_chunks != expected_chunks
                or not isinstance(expected_hash, str)
                or len(expected_hash) != 64
            ):
                raise ValueError("Invalid metadata values")

        except (
            UnicodeDecodeError, json.JSONDecodeError,
            KeyError, TypeError, ValueError
        ):
            print("Invalid metadata received.")
            return

        send_ack(receiver, sender_address, -1)
        print("Incoming file:", filename)
        print("Expected size:", file_size, "bytes")
        print("Expected packets:", total_chunks)

        received_chunks = {}
        transfer_complete = False

        while True:
            try:
                packet_data, source = receiver.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                if transfer_complete:
                    print("Finished waiting for duplicate END packets.")
                else:
                    print("Transfer timed out while waiting for packets.")
                return

            if source != sender_address:
                continue

            try:
                packet = json.loads(packet_data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            packet_type = packet.get("type")
            seq = packet.get("seq")

            if not isinstance(seq, int) or isinstance(seq, bool):
                continue

            if transfer_complete:
                if packet_type == "END" and seq == total_chunks:
                    send_ack(receiver, sender_address, total_chunks)
                    print("Re-acknowledged duplicate END packet.")
                continue

            if packet_type == "DATA":
                if not 0 <= seq < total_chunks:
                    continue

                try:
                    chunk = bytes.fromhex(packet["data"])
                except (KeyError, TypeError, ValueError):
                    continue

                expected_length = (
                    chunk_size if seq < total_chunks - 1
                    else file_size - chunk_size * (total_chunks - 1)
                )
                if len(chunk) != expected_length:
                    continue

                if seq not in received_chunks:
                    received_chunks[seq] = chunk

                send_ack(receiver, sender_address, seq)
                print(
                    f"Received packet {seq + 1}/{total_chunks}; "
                    f"{len(received_chunks)}/{total_chunks} "
                    "unique packets stored."
                )

            elif packet_type == "END" and seq == total_chunks:
                if len(received_chunks) != total_chunks:
                    continue

                received_data = b"".join(
                    received_chunks[i] for i in range(total_chunks)
                )

                if len(received_data) != file_size:
                    print("Integrity check failed: file size mismatch.")
                    return

                actual_hash = hashlib.sha256(received_data).hexdigest()
                if actual_hash != expected_hash:
                    print("Integrity check failed: SHA-256 mismatch.")
                    return

                os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                output_path = os.path.join(OUTPUT_FOLDER, filename)

                with open(output_path, "wb") as output_file:
                    output_file.write(received_data)

                send_ack(receiver, sender_address, total_chunks)
                print("\nFile reconstructed successfully!")
                print("Saved to:", output_path)
                print("Total bytes saved:", len(received_data))
                print("SHA-256 verification passed:", actual_hash)

                transfer_complete = True
                receiver.settimeout(2)


if __name__ == "__main__":
    main()
