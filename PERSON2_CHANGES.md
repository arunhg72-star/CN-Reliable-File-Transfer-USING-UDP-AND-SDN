# Person 2 - Reliable UDP Changes

This update modifies only `sender.py` and `receiver.py`. It does not change the Mininet topology or SDN controller.

## Changes made

1. **Duplicate META recovery:** If the first META acknowledgement is lost, the receiver recognizes an identical retransmitted META packet from the same sender and resends ACK `-1` without resetting already received chunks.
2. **ACK waiting:** The sender waits for the matching ACK until the current timeout expires. Malformed datagrams, ACKs from other sources, and stale/unrelated ACKs are ignored rather than immediately consuming a retry.
3. **Retransmission statistics:** The sender reports total UDP datagrams, ACKs received, total retransmissions, and DATA retransmissions.
4. **Performance statistics:** The sender measures transfer duration and application throughput in Mbps. Throughput is calculated as original file bits divided by elapsed transfer time.
5. **Duplicate/missing reporting:** The receiver reports duplicate DATA packets (and ignores their payload) and reports missing sequence numbers when the transfer times out or an END arrives before all chunks.
6. **Smaller chunks:** The sender uses 512-byte file chunks because the DATA payload is hex-encoded in JSON. This reduces the likelihood of IP fragmentation compared with 1024-byte raw chunks.
7. **Flexible sender destination:** The sender accepts `--host` and `--port`, and supports `UDP_RECEIVER_IP` and `UDP_PORT` environment variables. Defaults remain `10.0.0.2:5001` for the Mininet h2 host.
8. **Safe output save:** The receiver writes to a temporary `.part` file and renames it only after the size and SHA-256 checks pass.

## Run in Mininet

Start the receiver on h2 first:

```bash
python3 receiver.py
```

Then start the sender on h1:

```bash
python3 sender.py test_files/sample.txt
```

The default receiver is `10.0.0.2:5001`. If your Mininet receiver uses a different address or port, pass `--host` and `--port` explicitly.

## Localhost test (not the final Mininet demonstration)

Terminal 1:

```bash
python3 receiver.py
```

Terminal 2:

```bash
python3 sender.py test_files/sample.txt --host 127.0.0.1
```

## Verification

After the receiver saves the file, compare the hashes:

```bash
sha256sum test_files/sample.txt received_files/sample.txt
```

The two hash values must match.

## Validation performed for this update

- Python compilation passed for `sender.py` and `receiver.py`.
- Normal local UDP transfer passed for the repository's 3,092-byte sample file. With 512-byte chunks it used 7 DATA packets, and the original and received SHA-256 values matched.
- A local UDP fault-injection test deliberately dropped the first META ACK, the first DATA sequence 0 packet, and the first ACK for DATA sequence 0. The updated sender retried successfully; the receiver re-acknowledged duplicate META, ignored duplicate DATA, reconstructed the file, and SHA-256 matched.

These tests were local UDP tests. The updated files still need to be tested in the team's Ubuntu/Mininet/POX environment to verify packet loss and SDN link-failure integration.
