
import socket


RECEIVER_IP = "127.0.0.1"
PORT = 5001

MESSAGE = "Hello! UDP communication is working."


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:

    
    sender.sendto(
        MESSAGE.encode("utf-8"),
        (RECEIVER_IP, PORT)
    )

    print("Message sent successfully.")
