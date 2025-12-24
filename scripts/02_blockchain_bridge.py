import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [BRIDGE]    - %(message)s')

ANCHOR_FILE = "blockchain_anchor.json"

def main():
    logging.info("Service started. Monitoring anchor file...")
    last_seq = -1

    while True:
        try:
            if not os.path.exists(ANCHOR_FILE):
                time.sleep(1)
                continue

            try:
                with open(ANCHOR_FILE, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue

            current_seq = data.get('seq')

            if current_seq is not None and current_seq > last_seq:
                # Simulate smart contract interaction
                submit_transaction(data)
                last_seq = current_seq
            
            time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Bridge service stopped.")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(1)

def submit_transaction(data):
    """
    Simulates sending the SAID (Self-Addressing Identifier) to an Ethereum Smart Contract.
    """
    aid = data['aid']
    seq = data['seq']
    said = data['said']

    logging.info(f"New Anchor Detected [Seq: {seq}]")
    # In production, web3.py calls would go here:
    # contract.functions.registerAnchor(aid, seq, said).transact()
    
    time.sleep(0.5) # Simulate network latency
    logging.info(f"TX Confirmed: {said} anchored on-chain.")

if __name__ == "__main__":
    import os
    main()