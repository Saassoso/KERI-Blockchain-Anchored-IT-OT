# main.py
import sys
import json
import time
import logging
import argparse
from scripts.utils import load_libsodium # Import the new utility

# Load Libsodium before KERI imports
load_libsodium()

from keri.app import habbing

class DroneSensor:
    def __init__(self, sensor_id):
        self.sensor_id = sensor_id
        self.name = f"drone_sensor_{sensor_id}"
        self.db_name = "keri_drones_db"
        self.anchor_file = f"blockchain_anchor_{self.name}.json"
        
        logging.basicConfig(
            level=logging.INFO, 
            format=f'%(asctime)s - [{self.name.upper()}] - %(message)s'
        )

    def run(self):
        logging.info(f"Initializing {self.name}...")
        
        # 1. Initialize KERI environment FIRST
        #    (This decides where the DB actually goes)
        hby = habbing.Habery(name="controller", base=self.db_name)
        
        # 2. NOW save the REAL DB path for the verifier
        #    (hby.db.path tells us exactly where KERI put it)
        real_db_path = hby.db.path
        logging.info(f"Database location: {real_db_path}")
        
        with open(f"current_db_path_{self.name}.txt", "w") as f:
            f.write(real_db_path)

        try:
            # Create or Load Identity (AID)
            sensor = hby.habByName(name=self.name)
            if sensor is None:
                sensor = hby.makeHab(name=self.name, isith="1", icount=1)
                logging.info(f"Created new Identity (AID): {sensor.pre}")
            else:
                logging.info(f"Loaded Identity (AID): {sensor.pre}")

            cycle = 0
            while True:
                cycle += 1
                payload = {
                    "sensor": self.name,
                    "cycle": cycle,
                    "temp": 45 + (cycle % 10),
                    "status": "ACTIVE"
                }
                
                # Sign Data & Commit to KEL
                sensor.interact(data=[payload])
                
                # Export Anchor
                self._export_anchor(sensor, payload)
                
                time.sleep(3)
                
        except KeyboardInterrupt:
            logging.info("Stopping...")
        finally:
            hby.close()

    def _export_anchor(self, sensor, payload):
        # Fetch latest event from DB
        log = list(sensor.db.clonePreIter(pre=sensor.pre, fn=0))
        raw_bytes = bytes(log[-1])
        
        # FIXED: Use raw_decode to handle attached signatures/attachments
        try:
            raw_str = raw_bytes.decode('utf-8')
            # raw_decode returns the JSON and ignores the rest (signatures)
            event_data, _ = json.JSONDecoder().raw_decode(raw_str)
        except Exception:
            # Fallback
            event_data = json.loads(raw_bytes)
        
        anchor = {
            "aid": sensor.pre,
            "seq": int(event_data['s'], 16),
            "said": event_data['d'],
            "payload": payload
        }
        
        with open(self.anchor_file, "w") as f:
            json.dump(anchor, f, indent=4)
        logging.info(f"Committed Event #{anchor['seq']} (SAID: {anchor['said']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True, help="Sensor ID (1, 2, 3...)")
    args = parser.parse_args()
    
    DroneSensor(args.id).run()