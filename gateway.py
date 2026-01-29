import json
import time
import logging
import paho.mqtt.client as mqtt
import os
import ctypes
import hashlib
import base64
from ctypes.util import find_library
from dotenv import load_dotenv, find_dotenv
from web3 import Web3

# --- 1. ROBUST ENV LOADING ---
print(" Looking for .env file...")
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path:
    for p in ["../../.env", "../../../.env", "../../../../.env", ".env"]:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), p))
        if os.path.exists(path):
            dotenv_path = path
            break

if dotenv_path:
    print(f" Loaded .env from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print(" CRITICAL: .env file NOT FOUND. Web3 will fail.")

# --- 2. CONFIG ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PUBLIC_KEY_HEX = os.getenv("SCADA_PUBLIC_KEY_HEX")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ANCHOR_FILE = "dashboard_data.json"

# Minimal ABI
CONTRACT_ABI = [
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}], "name": "authorizeDevice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}, {"internalType": "uint256", "name": "sequence", "type": "uint256"}, {"internalType": "string", "name": "hash", "type": "string"}], "name": "registerAnchor", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

# --- 3. CRYPTO ---
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib:
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    return ctypes.cdll.LoadLibrary(lib) if lib else None

_sodium = load_crypto()

def verify_ed25519(pk_raw, msg, sig_raw):
    if not _sodium: return False
    msg_bytes = msg.encode('utf-8')
    if len(sig_raw) != 64: return False
    try:
        rc = _sodium.crypto_sign_verify_detached(sig_raw, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), pk_raw)
        return rc == 0
    except: return False

def from_cesr_sig(cesr_sig):
    if cesr_sig.startswith("0B"):
        try: return base64.urlsafe_b64decode(cesr_sig[2:] + "==")
        except: return None
    return None

def from_cesr_key(cesr_key):
    if cesr_key.startswith("D"):
        try: return base64.urlsafe_b64decode(cesr_key[1:] + "==")
        except: return None
    return None

# --- 4. MAIN CLASS ---
class SecureGateway:
    def __init__(self):
        self.kel_registry = {} 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GATEWAY] - %(message)s')
        logging.info("Initializing Gateway Components...")

        # Web3 Setup
        self.w3 = None
        self.account = None
        
        if CONTRACT_ADDRESS and ADMIN_PRIVATE_KEY:
            try:
                self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
                if self.w3.is_connected():
                    logging.info(f" Connected to Blockchain: {CONTRACT_ADDRESS}")
                    self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
                    self.account = self.w3.eth.account.from_key(ADMIN_PRIVATE_KEY)
                else:
                    logging.error(" Blockchain Connection Failed (Is Hardhat Running?)")
            except Exception as e:
                logging.error(f"Web3 Init Error: {e}")
        else:
            logging.warning(" Running WITHOUT Blockchain (Missing .env keys)")

        # MQTT Setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Gateway")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def send_tx(self, func_call):
        if not self.w3 or not self.account: return
        try:
            tx = func_call.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,
                'gasPrice': self.w3.to_wei('10', 'gwei')
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, ADMIN_PRIVATE_KEY)
            self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        except Exception as e:
            logging.error(f"TX Failed: {e}")

    def start(self):
        logging.info("  GATEWAY ONLINE. Listening on MQTT...")
        self.client.connect(MQTT_BROKER, 1883, 60)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe("keri/bootstrap")
        client.subscribe("telemetry/#")
        client.subscribe("substation/control/#")

    def verify_scada_command(self, payload):
        if not SCADA_PUBLIC_KEY_HEX: return True 
        try:
            cmd = payload.get("cmd")
            sig = payload.get("sig")
            return verify_ed25519(bytes.fromhex(SCADA_PUBLIC_KEY_HEX), cmd, bytes.fromhex(sig))
        except: return False

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            # SCADA COMMAND
            if "cmd" in payload:
                logging.info(f"Received Command: {payload['cmd']}")
                if self.verify_scada_command(payload):
                    logging.info(f" COMMAND VERIFIED. Forwarding...")
                    self.client.publish("control/broadcast", json.dumps(payload))
                return

            # KERI TELEMETRY
            if msg.topic == "keri/bootstrap":
                self.handle_inception(payload)
            elif "telemetry" in msg.topic:
                self.handle_telemetry(payload)

        except Exception as e:
            logging.error(f"Packet Error: {e}")

    def handle_inception(self, packet):
        event = packet["event"]
        aid = event["i"]
        if aid in self.kel_registry: return 

        pk_raw = from_cesr_key(event["k"][0])
        sig_raw = from_cesr_sig(packet["sig"])
        raw_event = json.dumps(event, sort_keys=True)
        
        if verify_ed25519(pk_raw, raw_event, sig_raw):
            logging.info(f" INCEPTION VALIDATED: {aid}")
            self.kel_registry[aid] = {"pk": pk_raw, "last_sn": 0}
            if self.w3: self.send_tx(self.contract.functions.authorizeDevice(aid))

    def handle_telemetry(self, packet):
        payload = packet["payload"] # Format: AID|Data|Data...|SN|TS
        parts = payload.split("|")
        
        # --- FIXED PARSING LOGIC ---
        # We know SN is always second to last, and TS is last.
        # AID is first. Everything in between is "val".
        if len(parts) < 3: return

        aid = parts[0]
        try:
            sn = int(parts[-2]) # Grab SN from the end
        except ValueError:
            logging.error(f"Failed to parse SN from: {parts}")
            return

        # Reassemble the data part (it might contain | symbols)
        val = "|".join(parts[1:-2]) 
        
        if aid not in self.kel_registry: return
        device = self.kel_registry[aid]

        if sn <= device["last_sn"]:
            logging.warning(f" REPLAY BLOCKED: {aid[:8]} (SN {sn})")
            return

        if verify_ed25519(device["pk"], payload, from_cesr_sig(packet["sig"])):
            logging.info(f" DATA VERIFIED: {val} | Anchoring...")
            device["last_sn"] = sn
            self.update_dashboard(aid, val, sn, "VERIFIED")
            if self.w3:
                h = hashlib.sha256(payload.encode()).hexdigest()
                self.send_tx(self.contract.functions.registerAnchor(aid, sn, h))
        else:
            logging.warning(f" INVALID SIG from {aid}")

    def update_dashboard(self, aid, val, sn, status):
        db_file = "dashboard_data.json"
        data = {}
        if os.path.exists(db_file):
            try:
                with open(db_file, "r") as f: data = json.load(f)
            except: pass
        data[aid] = {"val": val, "sn": sn, "status": status, "ts": time.time()}
        with open(db_file, "w") as f: json.dump(data, f)

if __name__ == "__main__":
    print(" Starting Gateway Instance...")
    gw = SecureGateway()
    gw.start()