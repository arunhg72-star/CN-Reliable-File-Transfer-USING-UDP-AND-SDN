# Reliable File Transfer over UDP + SDN

## Project Overview

This project implements reliable file transfer using UDP sockets and Software Defined Networking (SDN).

The system uses acknowledgements, sequence numbers, retransmissions and SHA-256 verification to ensure reliable file delivery. Mininet creates the network topology, while a POX controller manages forwarding and rerouting when a network link fails.

## Team Contributions

### Person 1 – Basic UDP File Transfer
- Implemented UDP sender and receiver.
- Implemented file metadata transmission.
- Divided files into chunks.
- Reconstructed and saved received files.

### Person 2 – Reliable File Transfer
- Implemented sequence numbers.
- Added acknowledgements (ACK).
- Added timeout and retransmission mechanisms.
- Implemented SHA-256 integrity verification.

### Person 3 – SDN Integration
- Created the Mininet network topology.
- Integrated the POX SDN controller.
- Implemented link failure detection.
- Implemented alternate-path routing.
- Tested file transfer during link failure.

## Project Files

- `sender.py` – Reliable UDP sender.
- `receiver.py` – Reliable UDP receiver.
- `topology.py` – Mininet network topology.
- `controller.py` – POX SDN controller.
- `test_files/` – Sample test files.
- `received_files/` – Directory for received files.

## Requirements

- Ubuntu / WSL
- Python 3
- Mininet
- Open vSwitch
- POX controller
- Git

## Running the Project

Make sure the POX extension symlink is configured:

    ln -sf ~/CN-Reliable-File-Transfer-USING-UDP-AND-SDN/controller.py ~/pox/ext/reroute.py

### Step 1 – Start the POX Controller

Open Terminal 1:

    cd ~/pox
    ./pox.py openflow.of_01 openflow.discovery reroute

Keep this terminal running.

### Step 2 – Start Mininet

Open Terminal 2:

    cd ~/CN-Reliable-File-Transfer-USING-UDP-AND-SDN
    sudo mn --custom topology.py --topo udptopology --controller=remote,ip=127.0.0.1,port=6633 --switch ovs,protocols=OpenFlow10

### Step 3 – Check Connectivity

At the Mininet prompt:

    pingall

The hosts should be able to communicate.

### Step 4 – Start the Receiver

At the Mininet prompt:

    h2 python3 /home/arthi/CN-Reliable-File-Transfer-USING-UDP-AND-SDN/receiver.py &

### Step 5 – Send a File

At the same Mininet prompt:

    h1 python3 /home/arthi/CN-Reliable-File-Transfer-USING-UDP-AND-SDN/sender.py /home/arthi/CN-Reliable-File-Transfer-USING-UDP-AND-SDN/test_files/sample.txt

### Step 6 – Test Link Failure and Rerouting

At the Mininet prompt, bring down the direct link:

    link s1 s3 down

Check connectivity again after the network converges:

    pingall

The controller should select the alternate path through switch s2.

Repeat the receiver and sender commands from Steps 4 and 5 to test file transfer over the alternate route.

### Step 7 – Restore the Link

At the Mininet prompt:

    link s1 s3 up
    pingall

The original direct route should become available again.

## Features

- UDP socket-based file transfer.
- Packet acknowledgements and retransmissions.
- SHA-256 file integrity verification.
- Mininet-based SDN topology.
- POX controller route discovery.
- Alternate-path routing after link failure.
- File transfer while the direct network link is unavailable.

## Testing and Results

The following tests were successfully performed:

- Normal connectivity between h1 and h2: 0% packet loss.
- Direct s1-s3 link failure tested.
- Alternate route through s2 successfully selected.
- Connectivity restored after the direct link was brought back up.
- Sample file of 3092 bytes transferred successfully.
- All 7 data packets received.
- 9 UDP datagrams sent and 9 ACKs received in the observed transfer.
- SHA-256 verification passed; original and received file hashes matched.
- File transfer succeeded while the direct s1-s3 link was down.

One observed successful transfer over the alternate route completed in approximately 0.098 seconds, with zero retransmissions.

## Notes

- The first ping test after a link failure may show packet loss while the controller detects the change and updates forwarding rules. Repeat the test after convergence.
- Restart the receiver before another transfer if it has exited after completing the previous transfer.
- POX may display a Python version compatibility warning in newer Python environments. The tested controller started and operated successfully in the project environment.
