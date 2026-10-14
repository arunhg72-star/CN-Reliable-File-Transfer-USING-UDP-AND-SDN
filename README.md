\# CN Project: Reliable File Transfer over UDP + SDN



\## Part 1 — Basic UDP File Transfer



\### 1. Objective



Develop a basic file-transfer application using Python UDP sockets. The sender reads a file, divides it into smaller chunks, and sends them to the receiver. The receiver collects the data, reconstructs the file, and saves the received copy.



\### 2. Files



\- `sender.py` — Reads an input file, sends file metadata, divides the contents into chunks, and transmits them using UDP.

\- `receiver.py` — Receives the metadata and chunks, reconstructs the file, and saves the output.

\- `test\_files/sample.txt` — Test file used to verify file transfer.

\- `.gitignore` — Excludes the generated `received\_files/` directory from Git.



\### 3. Requirements



\- Python 3

\- Two Command Prompt terminals for local testing

\- Git for version control



No additional Python packages are required for this implementation.



\### 4. How the Application Works



1\. The receiver creates a UDP socket and binds to port `5001`.

2\. The sender obtains the input file's name and size.

3\. The sender transmits the metadata as a JSON-encoded UDP datagram.

4\. The sender reads the file in chunks of up to 1,024 bytes.

5\. Each chunk is sent through a UDP socket.

6\. The receiver collects the chunks until the expected number of bytes has arrived.

7\. The receiver writes the reconstructed contents into an output file.



\### 5. How to Run the Application



Run the commands from the project directory.



\*\*Terminal 1 — Start the receiver\*\*



```cmd

python receiver.py

```



Wait for the receiver to display its listening message.



\*\*Terminal 2 — Start the sender\*\*



```cmd

python sender.py

```



The sender uses `test\_files/sample.txt` by default.



To send another file, provide its path:



```cmd

python sender.py "test\_files\\sample.txt"

```



The received file is saved at:



```text

received\_files/sample.txt

```



\### 6. Verification



After the receiver finishes, compare the original and received files:



```cmd

fc /b test\_files\\sample.txt received\_files\\sample.txt

```



Expected result:



```text

FC: no differences encountered

```



This result indicates that the original and reconstructed files are byte-for-byte identical for the tested transfer.



\### 7. Current Limitations



This is the basic UDP file-transfer implementation.



\- UDP does not guarantee packet delivery or ordering.

\- Sequence numbers and packet reordering are not implemented.

\- Acknowledgments and retransmissions are not implemented.

\- A formal checksum or hash verification mechanism is not implemented.



The current implementation assumes that the file datagrams arrive in order without loss. Additional reliability features will be added as part of Person 2's work.



\### 8. Team Responsibilities



\- \*\*Person 1:\*\* Basic UDP file transfer, chunk transmission, file reconstruction, and output saving.

\- \*\*Person 2:\*\* Reliability features, including sequence numbers, acknowledgments, timeouts, retransmissions, and integrity verification.

\- \*\*Person 3:\*\* Mininet topology, SDN controller integration, failure detection, and rerouting.



\### 9. Part 1 Progress



\- \[x] UDP sender and receiver created.

\- \[x] File metadata transmitted.

\- \[x] File divided into chunks.

\- \[x] Chunks transmitted using UDP.

\- \[x] Received data reconstructed and saved.

\- \[x] Original and reconstructed files compared successfully.

\- \[x] Source files and test file uploaded to GitHub.

\- \[x] Setup and testing instructions documented.



\*\*Scope:\*\* This README describes Person 1's basic UDP file-transfer implementation. It does not claim that the complete reliable-transfer or SDN-controlled system is finished.



