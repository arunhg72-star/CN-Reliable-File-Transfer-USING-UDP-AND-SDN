
import socket
import json
import os
import sys

# Receiver configuration
RECEIVER_IP = "127.0.0.1"
PORT = 5001

# Maximum file data sent in one UDP datagram
CHUNK_SIZE = 1024


def main():
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = os.path.join("test_files", "sample.txt")

    
    if not os.path.isfile(file_path):
        print("Error: File not found:", file_path)
        return

    
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    
    metadata = {
        "filename": filename,
        "size": file_size
    }

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:

        sender.sendto(
            json.dumps(metadata).encode("utf-8"),
            (RECEIVER_IP, PORT)
        )

        print("Sending file:", filename)
        print("File size:", file_size, "bytes")

        bytes_sent = 0

        
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)

                if not chunk:
                    break

                
                sender.sendto(chunk, (RECEIVER_IP, PORT))
                bytes_sent += len(chunk)

        print("File data sent:", bytes_sent, "bytes")
        print("Sender finished sending the file.")


if __name__ == "__main__":
    main()

