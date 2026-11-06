"""Reliable UDP file sender with ACK/retry and transfer statistics."""

import argparse
import hashlib
import json
import os
import socket
import sys
import time

DEFAULT_RECEIVER_IP = "10.0.0.2"
DEFAULT_PORT = 5001

# DATA payload is hex-encoded in JSON, so 512 raw bytes become about 1 KB
# before JSON/IP/UDP headers. This helps avoid IP fragmentation on Ethernet.
CHUNK_SIZE = 512
ACK_TIMEOUT = 1.0
MAX_RETRIES = 10
BUFFER_SIZE = 4096


def send_reliably(sock, packet, expected_ack, address, metrics, packet_kind):
    """Send one logical packet until its matching ACK arrives or retries end.

    Unrelated packets, stale ACKs and malformed UDP datagrams are ignored
    until the current ACK timeout expires. They do not cause an immediate
    retransmission.
    """
    for attempt in range(MAX_RETRIES + 1):
        sock.sendto(packet, address)
        metrics["datagrams_sent"] += 1

        if attempt > 0:
            metrics["retransmissions"] += 1
            if packet_kind == "DATA":
                metrics["data_retransmissions"] += 1
            print(
                f"Retransmitting {packet_kind} sequence {expected_ack} "
                f"(retry {attempt}/{MAX_RETRIES})"
            )

        deadline = time.monotonic() + ACK_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            sock.settimeout(remaining)
            try:
                response, source = sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                break

            if source != address:
                continue

            try:
                ack = json.loads(response.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if (
                isinstance(ack, dict)
                and ack.get("type") == "ACK"
                and ack.get("seq") == expected_ack
            ):
                metrics["acks_received"] += 1
                return True

            # Ignore stale or unrelated ACKs and continue waiting for the
            # ACK corresponding to the packet currently being transmitted.

        if attempt < MAX_RETRIES:
            print(
                f"ACK timeout for {packet_kind} sequence {expected_ack}; "
                f"next retry {attempt + 1}/{MAX_RETRIES}"
            )

    return False


def print_transfer_statistics(file_size, elapsed, metrics, successful):
    """Print reproducible application-level transfer measurements."""
    throughput_mbps = (
        (file_size * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0.0
    )

    print("\n========== TRANSFER STATISTICS ==========")
    print("Transfer status:", "SUCCESS" if successful else "FAILED")
    print("Total UDP datagrams sent:", metrics["datagrams_sent"])
    print("ACKs received:", metrics["acks_received"])
    print("Total retransmissions:", metrics["retransmissions"])
    print("Data packet retransmissions:", metrics["data_retransmissions"])
    print(f"Transfer time: {elapsed:.6f} seconds")
    print(f"Application throughput: {throughput_mbps:.6f} Mbps")
    print("=========================================\n")


def main():
    parser = argparse.ArgumentParser(description="Reliable UDP file sender")
    parser.add_argument(
        "file",
        nargs="?",
        default=os.path.join("test_files", "sample.txt"),
        help="File to transfer (default: test_files/sample.txt)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("UDP_RECEIVER_IP", DEFAULT_RECEIVER_IP),
        help="Receiver IPv4 address (default: 10.0.0.2; can use UDP_RECEIVER_IP)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("UDP_PORT", DEFAULT_PORT)),
        help="Receiver UDP port (default: 5001; can use UDP_PORT)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print("Error: File not found:", args.file)
        return 1
    if not 1 <= args.port <= 65535:
        print("Error: Port must be between 1 and 65535.")
        return 1

    filename = os.path.basename(args.file)
    with open(args.file, "rb") as input_file:
        file_data = input_file.read()

    file_size = len(file_data)
    file_hash = hashlib.sha256(file_data).hexdigest()
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    address = (args.host, args.port)

    metadata = {
        "type": "META",
        "filename": filename,
        "size": file_size,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "sha256": file_hash,
    }

    metrics = {
        "datagrams_sent": 0,
        "acks_received": 0,
        "retransmissions": 0,
        "data_retransmissions": 0,
    }
    started_at = time.perf_counter()
    successful = False

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        print("Sending file:", filename)
        print("Receiver:", f"{args.host}:{args.port}")
        print("File size:", file_size, "bytes")
        print("Chunk size:", CHUNK_SIZE, "bytes")
        print("Total data packets:", total_chunks)

        if not send_reliably(
            sender,
            json.dumps(metadata).encode("utf-8"),
            -1,
            address,
            metrics,
            "META",
        ):
            print("Transfer failed: metadata was not acknowledged.")
            elapsed = time.perf_counter() - started_at
            print_transfer_statistics(file_size, elapsed, metrics, False)
            return 1

        for seq in range(total_chunks):
            start = seq * CHUNK_SIZE
            chunk = file_data[start:start + CHUNK_SIZE]
            packet = json.dumps({
                "type": "DATA",
                "seq": seq,
                "data": chunk.hex(),
            }).encode("utf-8")

            if not send_reliably(
                sender, packet, seq, address, metrics, "DATA"
            ):
                print(f"Transfer failed at data packet {seq}.")
                elapsed = time.perf_counter() - started_at
                print_transfer_statistics(file_size, elapsed, metrics, False)
                return 1

            print(f"Packet {seq + 1}/{total_chunks} acknowledged.")

        if not send_reliably(
            sender,
            json.dumps({"type": "END", "seq": total_chunks}).encode("utf-8"),
            total_chunks,
            address,
            metrics,
            "END",
        ):
            print("Transfer failed: completion was not acknowledged.")
            elapsed = time.perf_counter() - started_at
            print_transfer_statistics(file_size, elapsed, metrics, False)
            return 1

        successful = True
        elapsed = time.perf_counter() - started_at
        print("Transfer completed successfully.")
        print("Original SHA-256:", file_hash)
        print_transfer_statistics(file_size, elapsed, metrics, successful)

    return 0


if __name__ == "__main__":
    sys.exit(main())
