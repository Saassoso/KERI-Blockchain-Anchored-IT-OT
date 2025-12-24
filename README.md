# KERI-Anchored IT/OT Security Gateway

This project demonstrates a proof-of-concept for securing Industrial IoT (OT) data using KERI (Key Event Receipt Infrastructure). It establishes a cryptographically verifiable "Chain of Trust" between sensor data generation and a blockchain anchor, effectively bridging the IT-OT gap.

The system assigns a decentralized identity (AID) to a simulated sensor, signs every data payload, and anchors the resulting event hash to a blockchain registry (simulated Ethereum).

## System Architecture

The project is composed of three decoupled Python scripts representing different actors in the network:

1.  **The Generator (OT Layer):**
    * Simulates an industrial sensor (e.g., Drone/PLC).
    * Maintains a local KERI Key Event Log (KEL) stored in LMDB.
    * Signs data payloads and sequences them (Event #1, #2, #3...).
    
2.  **The Bridge (Blockchain Layer):**
    * Monitors the Generator for new signed events.
    * Extracts the cryptographic digest (SAID).
    * Submits the digest to a Smart Contract (simulated) for immutability.

3.  **The Verifier (IT/Audit Layer):**
    * Acts as an external auditor.
    * Accesses the raw KERI database (LMDB) directly.
    * Verifies the cryptographic links between events to prove data integrity.

## Prerequisites

* Python 3.10+
* `libsodium` (Required for KERI cryptography)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YourUsername/KERI-Blockchain-Anchored-IT-OT.git](https://github.com/YourUsername/KERI-Blockchain-Anchored-IT-OT.git)
    cd KERI-Blockchain-Anchored-IT-OT
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv keri-env
    .\keri-env\Scripts\activate

    # Linux/Mac
    python3 -m venv keri-env
    source keri-env/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install keripy pysodium
    ```

## Usage

Run the three components in separate terminal windows to observe the data flow in real-time.

### Terminal 1: Sensor Simulation
Starts the KERI controller, initializes the identity, and begins signing data streams.
```bash
python scripts/01_anchor_generator.py
```

Creates a temporary database keri_run_<uuid> and outputs blockchain_anchor.json.

### Terminal 2: Blockchain Bridge
Watches the anchor file and "commits" new hashes to the blockchain.

```bash
python scripts/02_blockchain_bridge.py
```
Terminal 3: Integrity Verification
Reads the actual LMDB database files to audit the event chain.

```bash
python scripts/03_kel_verifier.py
```

### Note on Persistence
**Why a Temporary Database?** 
For demonstration purposes, 01_anchor_generator.py creates a unique, temporary database (keri_run_<uuid>) on every run. This ensures a "clean slate" for testing and prevents "Already Incepted" errors caused by KERI's strict identity protection rules.

**Production Implementation** In a real-world deployment, the database path would be fixed. The script would check for an existing identity on startup and Load it instead of Creating a new one. This would ensure the sensor maintains the same cryptographic Identity (AID) for its entire lifecycle, even after reboots.

### Technical Details

- Identity: Uses KERI Autonomous Identifiers (AIDs) generated via keripy.
- Storage: Local LMDB (Lightning Memory-Mapped Database) for the Key Event Log.
- Serialization: JSON for external transport; KERI-native serialization for internal signing.
- Verification: Checks cryptographic links (Sequence Number and SAID) to ensure the history cannot be tampered with.

### License
MIT License