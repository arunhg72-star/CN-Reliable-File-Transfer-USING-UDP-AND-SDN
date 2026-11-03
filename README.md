# Reliable File Transfer over UDP + SDN

## Project Overview

This project implements reliable file transfer using UDP sockets and Software Defined Networking (SDN).

The system uses acknowledgements, sequence numbers, retransmissions and SHA-256 verification to ensure reliable file delivery. Mininet creates the network topology, while a POX controller manages forwarding and rerouting during link failures.

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
- Created Mininet network topology.
- Integrated the POX SDN controller.
- Implemented link failure detection.
- Implemented alternate-path routing.
- Tested file transfer during link failure.

## Project Files

- sender.py – Reliable UDP sender.
- receiver.py – Reliable UDP receiver.
- topology.py – Mininet network topology.
- controller.py – POX SDN controller.
- test_files/ – Sample and large test files.
- received_files/ – Received output files.

## Requirements

- Ubuntu / WSL
- Python 3
- Mininet
- Open vSwitch
- POX controller
- Git

## Running the Project

### Step 1 – Start the POX Controller

Open Terminal 1:

    cd ~/pox
    ./pox.py openflow.of_01 openflow.discovery reroute

### Step 2 – Start Mininet

Open Terminal 2:

    cd ~/udp-sdn-project
    sudo mn --custom topology.py --topo udptopology --controller=remote,ip=127.0.0.1,port=6633 --switch ovs,protocols=OpenFlow10

### Step 3 – Check Connectivity

At the Mininet prompt:

    pingall

### Step 4 – Start the Receiver

At the Mininet prompt:

    h2 python3 /home/arthi/udp-sdn-project/receiver.py

### Step 5 – Send a File

In another Ubuntu terminal:

    sudo mnexec -a $(pgrep -f 'mininet:h1' | head -1) python3 /home/arthi/udp-sdn-project/sender.py /home/arthi/udp-sdn-project/test_files/large.txt

### Step 6 – Test Link Failure

At the Mininet prompt:

    link s1 s3 down
    pingall

Restore the link:

    link s1 s3 up
    pingall

## Features

- UDP socket-based file transfer.
- Packet acknowledgements and retransmissions.
- SHA-256 file integrity verification.
- Mininet-based SDN topology.
- POX controller route discovery.
- Alternate-path rerouting after link failure.

## Testing and Results

- Normal network connectivity achieved 0% packet loss after convergence.
- Alternate route through switch s2 detected after direct link failure.
- Large file of 6400 bytes transferred successfully.
- All 7 packets acknowledged.
- SHA-256 verification successful.
- File transfer succeeded with the direct s1-s3 link down.
- One observed successful transfer time: 0.284 seconds.

## Notes

The first ping test after a link failure may experience packet loss while the controller detects the failure and updates forwarding. Repeat the connectivity test after convergence.

The receiver currently needs to be restarted before a new transfer if it has exited after completing the previous transfer.
