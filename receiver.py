"""Reliable UDP file receiver with duplicate handling and SHA-256 checking."""

import hashlib
import json
import os
import re
import socket

HOST = "0.0.0.0"
PORT = 5001
BUFFER_SIZE = 8192
RECEIVE_TIMEOUT = 30
POST_TRANSFER_TIMEOUT = 2
OUTPUT_FOLDER = "received_files"


def send_ack(sock, address, seq):
    ack = {"type": "ACK", "seq": seq}
    sock.sendto(json.dumps(ack).encode("utf-8"), address)


def valid_metadata(metadata):
    """Validate metadata before allocating or accepting transfer data."""
    if not isinstance(metadata, dict) or metadata.get("type") != "META":
        return False

    filename = metadata.get("filename")
    file_size = metadata.get("size")
    chunk_size = metadata.get("chunk_size")
    total_chunks = metadata.get("total_chunks")
    expected_hash = metadata.get("sha256")

    if not isinstance(filename, str) or not os.path.basename(filename):
        return False
    if not isinstance(file_size, int) or isinstance(file_size, bool) or file_size < 0:
        return False
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        return False
    if not 0 < chunk_size <= 512:
        return False
    if not isinstance(total_chunks, int) or isinstance(total_chunks, bool):
        return False

    expected_chunks = (file_size + chunk_size - 1) // chunk_size
    if total_chunks != expected_chunks:
        return False
    if not isinstance(expected_hash, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_hash
    ):
        return False

    return True


def missing_sequences(received_chunks, total_chunks):
    return [seq for seq in range(total_chunks) if seq not in received_chunks]


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    received_chunks = {}
    duplicate_data_packets = 0
    duplicate_metadata_packets = 0
    transfer_complete = False

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind((HOST, PORT))
        receiver.settimeout(RECEIVE_TIMEOUT)
        print(f"Receiver listening on {HOST}:{PORT}...")

        try:
            data, sender_address = receiver.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            print("Timed out waiting for file metadata.")
            return 1

        try:
            metadata = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            print("Invalid metadata received: malformed JSON.")
            return 1

        if not valid_metadata(metadata):
            print("Invalid metadata received: invalid metadata fields.")
            return 1

        filename = os.path.basename(metadata["filename"])
        file_size = metadata["size"]
        chunk_size = metadata["chunk_size"]
        total_chunks = metadata["total_chunks"]
        expected_hash = metadata["sha256"].lower()

        # ACK the initial META packet. If this ACK is lost, the sender will
        # retransmit META; the main loop below must ACK it again without
        # resetting any data already received.
        send_ack(receiver, sender_address, -1)
        print("Incoming file:", filename)
        print("Expected size:", file_size, "bytes")
        print("Expected packets:", total_chunks)

        while True:
            try:
                packet_data, source = receiver.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                if transfer_complete:
                    print("Finished waiting for duplicate END packets.")
                    print("Duplicate DATA packets ignored:", duplicate_data_packets)
                    print("Duplicate META packets re-acknowledged:", duplicate_metadata_packets)
                    return 0

                missing = missing_sequences(received_chunks, total_chunks)
                print("Transfer timed out while waiting for packets.")
                if missing:
                    print("Missing sequence numbers:", missing)
                return 1

            if source != sender_address:
                continue

            try:
                packet = json.loads(packet_data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                print("Ignored malformed UDP packet.")
                continue

            if not isinstance(packet, dict):
                print("Ignored packet with invalid JSON structure.")
                continue

            packet_type = packet.get("type")

            # META packets intentionally have no sequence number. Handle
            # retransmitted metadata before validating DATA/END sequence IDs.
            if packet_type == "META":
                # Re-ACK only an exact repeat from the same sender. Do not
                # erase chunks or restart the current transfer.
                if packet == metadata:
                    duplicate_metadata_packets += 1
                    send_ack(receiver, sender_address, -1)
                    print("Duplicate META received; ACK -1 resent.")
                else:
                    print("Ignored unexpected or changed META packet.")
                continue

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
                    print(f"Ignored out-of-range DATA sequence: {seq}")
                    continue

                try:
                    encoded_chunk = packet.get("data")
                    if not isinstance(encoded_chunk, str):
                        raise ValueError("DATA payload must be hexadecimal text")
                    chunk = bytes.fromhex(encoded_chunk)
                except (TypeError, ValueError):
                    print(f"Ignored malformed DATA packet: {seq}")
                    continue

                expected_length = (
                    chunk_size if seq < total_chunks - 1
                    else file_size - chunk_size * (total_chunks - 1)
                )
                if len(chunk) != expected_length:
                    print(f"Ignored DATA packet {seq}: incorrect chunk length.")
                    continue

                if seq in received_chunks:
                    duplicate_data_packets += 1
                    print(f"Duplicate packet detected: {seq}; duplicate ignored.")
                else:
                    received_chunks[seq] = chunk
                    print(
                        f"Received packet {seq + 1}/{total_chunks}; "
                        f"{len(received_chunks)}/{total_chunks} unique packets stored."
                    )

                # ACK duplicates too, so a lost ACK does not stall the sender.
                send_ack(receiver, sender_address, seq)

            elif packet_type == "END" and seq == total_chunks:
                missing = missing_sequences(received_chunks, total_chunks)
                if missing:
                    print("END received before all data packets.")
                    print("Missing sequence numbers:", missing)
                    # Do not ACK END. Sender will retry according to its
                    # timeout/retransmission policy.
                    continue

                received_data = b"".join(
                    received_chunks[index] for index in range(total_chunks)
                )
                if len(received_data) != file_size:
                    print("Integrity check failed: file size mismatch.")
                    return 1

                actual_hash = hashlib.sha256(received_data).hexdigest()
                if actual_hash != expected_hash:
                    print("Integrity check failed: SHA-256 mismatch.")
                    print("Expected SHA-256:", expected_hash)
                    print("Received SHA-256:", actual_hash)
                    return 1

                output_path = os.path.join(OUTPUT_FOLDER, filename)
                temp_path = output_path + ".part"
                with open(temp_path, "wb") as output_file:
                    output_file.write(received_data)
                os.replace(temp_path, output_path)

                # ACK only after the verified file has been safely saved.
                send_ack(receiver, sender_address, total_chunks)
                print("\nFile reconstructed successfully!")
                print("Saved to:", output_path)
                print("Total bytes saved:", len(received_data))
                print("Original SHA-256:", expected_hash)
                print("Received SHA-256:", actual_hash)
                print("SHA-256 verification: PASSED")
                print("Duplicate DATA packets ignored:", duplicate_data_packets)
                print("Duplicate META packets re-acknowledged:", duplicate_metadata_packets)

                transfer_complete = True
                receiver.settimeout(POST_TRANSFER_TIMEOUT)


if __name__ == "__main__":
    raise SystemExit(main())
