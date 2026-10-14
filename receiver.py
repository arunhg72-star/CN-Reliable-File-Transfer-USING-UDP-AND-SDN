
import socket


HOST = "0.0.0.0"
PORT = 5001


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:

    
    receiver.bind((HOST, PORT))

    print(f"Receiver is listening on port {PORT}...")

    
    data, sender_address = receiver.recvfrom(2048)

    
    message = data.decode("utf-8")
    print("Message received:", message)
    print("Sender address:", sender_address)
