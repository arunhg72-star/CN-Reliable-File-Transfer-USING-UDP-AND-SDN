
import socket
import json
import os


HOST = "0.0.0.0"
PORT = 5001


BUFFER_SIZE = 2048


RECEIVE_TIMEOUT = 5


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:

        receiver.bind((HOST, PORT))
        print(f"Receiver listening on port {PORT}...")

        
        data, sender_address = receiver.recvfrom(BUFFER_SIZE)

        try:
            metadata = json.loads(data.decode("utf-8"))
            filename = os.path.basename(metadata["filename"])
            file_size = int(metadata["size"])

            if file_size < 0 or not filename:
                raise ValueError("Invalid file metadata")

        except (UnicodeDecodeError, json.JSONDecodeError,
                KeyError, TypeError, ValueError):
            print("Error: Invalid file metadata received.")
            return

        print("Incoming file:", filename)
        print("Expected size:", file_size, "bytes")

        received_data = bytearray()
        receiver.settimeout(RECEIVE_TIMEOUT)

        
        while len(received_data) < file_size:
            try:
                chunk, source = receiver.recvfrom(BUFFER_SIZE)

            except socket.timeout:
                print(
                    "Transfer incomplete:",
                    len(received_data), "of",
                    file_size, "bytes received."
                )
                print("No retransmission is implemented in this version.")
                return

            
            if source != sender_address:
                continue

            remaining = file_size - len(received_data)
            received_data.extend(chunk[:remaining])

            print(
                "Received:",
                len(received_data), "/", file_size, "bytes"
            )

        
        output_folder = "received_files"
        os.makedirs(output_folder, exist_ok=True)

        output_path = os.path.join(output_folder, filename)

        
        with open(output_path, "wb") as output_file:
            output_file.write(received_data)

        print("\nFile reconstructed successfully!")
        print("Saved to:", output_path)
        print("Total bytes saved:", len(received_data))


if __name__ == "__main__":
    main()

