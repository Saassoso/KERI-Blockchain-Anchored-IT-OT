import json
import time
import logging
import paho.mqtt.client as mqtt
from scripts.utils import load_libsodium
import os

# 1. Load Libsodium FIRST (Critical for Windows)
load_libsodium()

# 2. NOW import the libraries that rely on it
import pysodium 
from keri.app import habbing

# CONFIG
MQTT_BROKER = "localhost"
MQTT_TOPIC = "substation/#"
ANCHOR_FILE = "blockchain_anchor_gateway.json"

# --- PASTE YOUR GENERATED PUBLIC KEY HERE ---
SCADA_PUBLIC_KEY_HEX = "e7da49932640a662a61cca5affafb16cfa523edb9e0e8bf64e8b293a49e1e1ea"

KNOWN_DEVICES = {
    "ESP32_SENSOR_A": "SECRET_TOKEN_123",
    "ESP32_RELAY_B":  "SECRET_TOKEN_456"
}

class SecureGateway:
    def __init__(self):
        self.name = "Gateway_Phy_1"
        self.db_name = "keri_gateway_db"
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GATEWAY] - %(message)s')
        
        self.hby = habbing.Habery(name="controller", base=self.db_name)
        self.hab = self.setup_identity()
        self.cycle_count = 0  

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def setup_identity(self):
        hab = self.hby.habByName(name=self.name)
        if hab is None:
            hab = self.hby.makeHab(name=self.name, isith="1", icount=1)
            logging.info(f"Created KERI AID: {hab.pre}")
        else:
            logging.info(f"Loaded KERI AID: {hab.pre}")
        return hab

    def on_connect(self, client, userdata, flags, rc, properties=None):
        logging.info("Connected to MQTT Broker")
        client.subscribe("substation/#")

    def check_rotation(self):
        self.cycle_count += 1
        if self.cycle_count >= 10:
            logging.info("Initiating KERI Key Rotation...")
            self.hab.rotate()
            logging.info(f"Keys Rotated! New Sequence: {self.hab.kever.sn}")
            self.cycle_count = 0

    def verify_scada_command(self, payload):
        try:
            command = payload.get("cmd")
            signature_hex = payload.get("sig")
            
            pysodium.crypto_sign_verify_detached(
                bytes.fromhex(signature_hex),
                command.encode('utf-8'),
                bytes.fromhex(SCADA_PUBLIC_KEY_HEX)
            )
            logging.info(f"SCADA Signature Verified for: {command}")
            return True
        except Exception as e:
            logging.error(f"INVALID SIGNATURE! Command Rejected: {e}")
            return False

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if "cmd" in payload:
                if self.verify_scada_command(payload):
                    print(f"EXECUTING: {payload['cmd']}")
                return

            clean_data = {k: v for k, v in payload.items() if k != 'token'}
            self.hab.interact(data=[clean_data])
            self.export_anchor(clean_data)
            
            self.check_rotation()
        except Exception as e:
            logging.error(f"Message processing error: {e}")

    def export_anchor(self, data):
        try:
            log = list(self.hab.db.clonePreIter(pre=self.hab.pre, fn=0))
            if not log:
                return

            raw_event = bytes(log[-1])
            event_str = raw_event.decode('utf-8')

            import json
            header = None
            for i in range(len(event_str)):
                try:
                    candidate = event_str[:i+1]
                    header = json.loads(candidate)
                    break 
                except json.JSONDecodeError:
                    continue
            
            if not header:
                header = json.loads(event_str)

            anchor = {
                "aid": self.hab.pre,
                "seq": int(header['s'], 16),
                "said": header['d'],
                "data_snapshot": data
            }
            
            temp_file = f"{ANCHOR_FILE}.tmp"
            with open(temp_file, "w") as f:
                json.dump(anchor, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_file, ANCHOR_FILE)
            logging.info(f"⚓ Anchor File Updated (Seq {anchor['seq']})")
                
        except Exception as e:
            logging.error(f"Export Failed: {e}")

    def run(self):
        logging.info("🚀 Gateway Active. Listening for sensors...")
        self.client.connect(MQTT_BROKER, 1883, 60)
        self.client.loop_forever()

if __name__ == "__main__":
    gw = SecureGateway()
    gw.run()