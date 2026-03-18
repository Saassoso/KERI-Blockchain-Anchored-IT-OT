import json
import time
import base64
import ctypes
import hashlib
import logging
import os
import paho.mqtt.client as mqtt
from ctypes.util import find_library
from dotenv import load_dotenv, find_dotenv
from web3 import Web3

# --- 1. CONFIG & SETUP ---
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ANCHOR_FILE = "dashboard_data.json"
SCADA_PUBLIC_KEY_HEX = os.getenv("SCADA_PUBLIC_KEY_HEX") 

CONTRACT_ABI = [
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}], "name": "authorizeDevice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}, {"internalType": "uint256", "name": "sequence", "type": "uint256"}, {"internalType": "string", "name": "hash", "type": "string"}], "name": "registerAnchor", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib: 
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    return ctypes.cdll.LoadLibrary(lib) if lib else None

_sodium = load_crypto()

def from_cesr_key(cesr_key):
    if cesr_key and cesr_key.startswith("D"):
        try: return base64.urlsafe_b64decode(cesr_key[1:] + "==")
        except: return None
    return None

def from_cesr_sig(cesr_sig):
    if cesr_sig and cesr_sig.startswith("0B"):
        try: return base64.urlsafe_b64decode(cesr_sig[2:] + "==")
        except: return None
    return None

def verify_ed25519(pk_raw, msg, sig_raw):
    if not _sodium: return False
    msg_bytes = msg.encode('utf-8')
    if not sig_raw or len(sig_raw) != 64: return False
    try:
        rc = _sodium.crypto_sign_verify_detached(sig_raw, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), pk_raw)
        return rc == 0
    except: return False

class SecureGateway:
    def __init__(self):
        self.kel_registry = {} 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GATEWAY] - %(message)s')
        logging.info("Initializing Gateway Components...")

        self.w3 = None
        self.account = None
        
        if SCADA_PUBLIC_KEY_HEX:
            self.admin_pk = bytes.fromhex(SCADA_PUBLIC_KEY_HEX)
        else:
            logging.warning("⚠️ SCADA_PUBLIC_KEY_HEX not found! Commands cannot be verified.")
            self.admin_pk = None

        if CONTRACT_ADDRESS and ADMIN_PRIVATE_KEY:
            try:
                self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
                if self.w3.is_connected():
                    self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
                    self.account = self.w3.eth.account.from_key(ADMIN_PRIVATE_KEY)
                    logging.info(f"✅ Connected to Blockchain. Account: {self.account.address[:10]}...")
                else:
                    logging.error(" Blockchain Connection Failed (Is Hardhat Running?)")
            except Exception as e: logging.error(f"Web3 Error: {e}")
        else:
            logging.warning(" Running WITHOUT Blockchain (Missing .env keys)")

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Gateway")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def send_tx(self, func_call):
        if not self.w3 or not self.account: return
        try:
            current_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
            tx = func_call.build_transaction({
                'from': self.account.address,
                'nonce': current_nonce,
                'gas': 2000000,
                'gasPrice': self.w3.to_wei('10', 'gwei')
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, ADMIN_PRIVATE_KEY)
            self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        except Exception as e: 
            logging.error(f"TX Failed: {e}")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        logging.info("Connected to MQTT. Listening...")
        client.subscribe("keri/bootstrap")
        client.subscribe("telemetry/#")
        client.subscribe("substation/control/breaker")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if "cmd" in payload:
                cmd_str = payload["cmd"]
                sig_hex = payload.get("sig")
                
                if not self.admin_pk:
                    logging.error("❌ Cannot verify command: Missing SCADA_PUBLIC_KEY_HEX")
                    return
                if not sig_hex:
                    logging.warning(f"❌ BLOCKED: Unsigned Command '{cmd_str}'")
                    return
                try:
                    sig_raw = bytes.fromhex(sig_hex)
                except:
                    logging.warning("❌ BLOCKED: Invalid Hex Signature")
                    return
                    
                if verify_ed25519(self.admin_pk, cmd_str, sig_raw):
                    logging.info(f"✅ COMMAND VERIFIED: {cmd_str} (Forwarding to OT)")
                    self.client.publish("control/broadcast", json.dumps(payload))
                else:
                    logging.warning(f"⛔ BLOCKED: Fake Admin Command '{cmd_str}' (Invalid Signature)")
                return

            if msg.topic == "keri/bootstrap":
                self.handle_inception(payload)
            elif "telemetry" in msg.topic:
                self.handle_telemetry(payload)
                
        except Exception as e: 
            logging.error(f"Processing Error: {e}")

    def handle_inception(self, packet):
        event = packet["event"]
        aid = event["i"]
        if aid in self.kel_registry: return
        
        try:
            pk_raw = from_cesr_key(event["k"][0])
            sig_raw = from_cesr_sig(packet["sig"])
            if verify_ed25519(pk_raw, json.dumps(event, sort_keys=True), sig_raw):
                self.kel_registry[aid] = {"pk": pk_raw, "last_sn": 0}
                logging.info(f"🆕 NEW IDENTITY REGISTERED: {aid[:8]}...")
                if self.w3: self.send_tx(self.contract.functions.authorizeDevice(aid))
        except Exception as e: logging.error(f"Inception Error: {e}")

    def handle_telemetry(self, packet):
        try:
            payload = packet["payload"] 
            parts = payload.split("|")
            if len(parts) < 3: return

            aid = parts[0]
            try:
                sn = int(parts[-2])
            except ValueError:
                logging.error(f"Failed to parse SN from: {parts}")
                return

            val = "|".join(parts[1:-2]) 
            
            if aid not in self.kel_registry: 
                logging.warning(f"⛔ UNKNOWN DEVICE: {aid}")
                return
            
            device = self.kel_registry[aid]

            if sn <= device["last_sn"]:
                logging.warning(f"🔄 REPLAY BLOCKED: {aid[:8]} (SN {sn})")
                return

            if verify_ed25519(device["pk"], payload, from_cesr_sig(packet["sig"])):
                logging.info(f"✅ DATA VERIFIED: {val} | Anchoring...")
                device["last_sn"] = sn
                self.update_dashboard(aid, val, sn, "VERIFIED")
                if self.w3:
                    h = hashlib.sha256(payload.encode()).hexdigest()
                    self.send_tx(self.contract.functions.registerAnchor(aid, sn, h))
            else:
                logging.warning(f"❌ INVALID SIG from {aid}")
        except Exception as e:
            logging.error(f"Telemetry Error: {e}")

    def update_dashboard(self, aid, val, sn, status):
        data = {}
        try:
            if os.path.exists(ANCHOR_FILE):
                with open(ANCHOR_FILE, "r") as f: data = json.load(f)
        except: pass
        data[aid] = {"val": val, "sn": sn, "status": status, "ts": time.time()}
        with open(ANCHOR_FILE, "w") as f: json.dump(data, f)

    def start(self):
        logging.info("GATEWAY ONLINE. Listening on MQTT...")
        self.client.connect(MQTT_BROKER, 1883, 60)
        self.client.loop_forever()

if __name__ == "__main__":
    SecureGateway().start()