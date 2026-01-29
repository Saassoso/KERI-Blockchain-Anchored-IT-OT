import json
import time
import base64
import ctypes
from ctypes.util import find_library
import paho.mqtt.client as mqtt

<<<<<<< Updated upstream
# ==========================================
#  GATEWAY CRYPTO (Verifier)
# ==========================================
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib:
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    return ctypes.cdll.LoadLibrary(lib)
=======
# --- 1. CONFIG & SETUP ---
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

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PUBLIC_KEY_HEX = os.getenv("SCADA_PUBLIC_KEY_HEX")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ANCHOR_FILE = "dashboard_data.json"

CONTRACT_ABI = [
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}], "name": "authorizeDevice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "string", "name": "aid", "type": "string"}, {"internalType": "uint256", "name": "sequence", "type": "uint256"}, {"internalType": "string", "name": "hash", "type": "string"}], "name": "registerAnchor", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

# --- 2. CRYPTO ---
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib: lib = ctypes.util.find_library('libsodium.dll')
    return ctypes.cdll.LoadLibrary(lib) if lib else None
>>>>>>> Stashed changes

_sodium = load_crypto()

def from_cesr_key(cesr_key):
    """ Extracts raw bytes from CESR Key (Drops 'D' prefix) """
    if cesr_key.startswith("D"):
        try:
            return base64.urlsafe_b64decode(cesr_key[1:] + "==")
        except:
            return None
    return None

def from_cesr_sig(cesr_sig):
    """ Extracts raw bytes from CESR Sig (Drops '0B' prefix) """
    if cesr_sig.startswith("0B"):
        try:
            return base64.urlsafe_b64decode(cesr_sig[2:] + "==")
        except:
            return None
    return None

def verify_ed25519(pk_raw, msg, sig_raw):
    msg_bytes = msg.encode('utf-8')
    if len(sig_raw) != 64: return False
    try:
        rc = _sodium.crypto_sign_verify_detached(
            sig_raw, 
            msg_bytes, 
            ctypes.c_ulonglong(len(msg_bytes)), 
            pk_raw
        )
        return rc == 0
    except:
        return False

<<<<<<< Updated upstream
# ==========================================
#  GATEWAY LOGIC (Witness/Guardian)
# ==========================================
=======
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

# --- 3. GATEWAY CLASS ---
>>>>>>> Stashed changes
class SecureGateway:
    def __init__(self):
        # Local KEL Registry
        # { "AID": { "pk": bytes, "last_sn": 0, "status": "ACTIVE" } }
        self.kel_registry = {} 
<<<<<<< Updated upstream
        
=======
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GATEWAY] - %(message)s')
        logging.info("Initializing Gateway...")

        self.w3 = None
        self.account = None
        self.tx_nonce = -1 # Track nonce locally to prevent collisions
        
        if CONTRACT_ADDRESS and ADMIN_PRIVATE_KEY:
            try:
                self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
                if self.w3.is_connected():
                    logging.info(f" Connected to Blockchain: {CONTRACT_ADDRESS}")
                    self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
                    self.account = self.w3.eth.account.from_key(ADMIN_PRIVATE_KEY)
                    # Initialize Nonce
                    self.tx_nonce = self.w3.eth.get_transaction_count(self.account.address)
                else:
                    logging.error(" Blockchain Connection Failed")
            except Exception as e:
                logging.error(f"Web3 Init Error: {e}")
        else:
            logging.warning("⚠️  Running WITHOUT Blockchain")

>>>>>>> Stashed changes
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Gateway")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

<<<<<<< Updated upstream
    def start(self):
        print("🛡️  GATEWAY ONLINE. Waiting for KERI Bootstraps...")
        self.client.connect("localhost", 1883, 60)
=======
    def send_tx(self, func_call):
        if not self.w3 or not self.account: return
        try:
            # FIX: Get 'pending' nonce or use local counter to prevent collisions
            net_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
            if self.tx_nonce < net_nonce:
                self.tx_nonce = net_nonce
            
            tx = func_call.build_transaction({
                'from': self.account.address,
                'nonce': self.tx_nonce,
                'gas': 2000000,
                'gasPrice': self.w3.to_wei('5', 'gwei')
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, ADMIN_PRIVATE_KEY)
            self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Increment nonce locally for the next immediate transaction
            self.tx_nonce += 1 
            # logging.info(" TX Sent")
            
        except Exception as e:
            logging.error(f"TX Failed: {e}")

    def start(self):
        logging.info("  GATEWAY ONLINE. Listening...")
        self.client.connect(MQTT_BROKER, 1883, 60)
>>>>>>> Stashed changes
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe("keri/bootstrap")  # Listen for Inceptions
        client.subscribe("telemetry/#")     # Listen for Data

    def on_message(self, client, userdata, msg):
        try:
<<<<<<< Updated upstream
            packet = json.loads(msg.payload.decode())
            topic = msg.topic
            
            if topic == "keri/bootstrap":
                self.handle_inception(packet)
            elif "telemetry" in topic:
                self.handle_telemetry(packet)
                
=======
            payload = json.loads(msg.payload.decode())

            # SCADA COMMAND
            if "cmd" in payload:
                logging.info(f"Received Command: {payload['cmd']}")
                if self.verify_scada_command(payload):
                    logging.info(f" COMMAND VERIFIED. Forwarding...")
                    self.client.publish("control/broadcast", json.dumps(payload))
                return

            # KERI
            if msg.topic == "keri/bootstrap":
                self.handle_inception(payload)
            elif "telemetry" in msg.topic:
                self.handle_telemetry(payload)

>>>>>>> Stashed changes
        except Exception as e:
            print(f" Error processing packet: {e}")

    def handle_inception(self, packet):
        """ Handles 'icp' events (Trust On First Use) """
        event = packet["event"]
        sig_cesr = packet["sig"]
        aid = event["i"]
        
        if aid in self.kel_registry:
            # In a real system, we'd check for Key Rotation here
            return 

        # 1. Get Public Key from Event
        pk_cesr = event["k"][0] 
        pk_raw = from_cesr_key(pk_cesr)
        
        # 2. Verify Self-Signature
        raw_event = json.dumps(event, sort_keys=True)
        sig_raw = from_cesr_sig(sig_cesr)
        
        if verify_ed25519(pk_raw, raw_event, sig_raw):
<<<<<<< Updated upstream
            print(f" INCEPTION VALIDATED. New AID Registered: {aid}")
            self.kel_registry[aid] = {
                "pk": pk_raw,
                "last_sn": 0,
                "status": "ACTIVE"
            }
        else:
            print(f" INCEPTION FAILED: Invalid Signature for {aid}")

    def handle_telemetry(self, packet):
        """ Handles Data Packets (Verifies against Local KEL) """
        payload = packet["payload"] # Format: AID|Val|SN|TS
        sig_cesr = packet["sig"]
        
        parts = payload.split("|")
        aid = parts[0]
        sn = int(parts[2])
        val = parts[1]
        
        # 1. Check Registration
        if aid not in self.kel_registry:
            print(f" UNKNOWN DEVICE: {aid}. Waiting for Bootstrap...")
            return

=======
            logging.info(f" INCEPTION VALIDATED: {aid}")
            self.kel_registry[aid] = {"pk": pk_raw, "last_sn": 0}
            if self.w3: 
                logging.info(f" Authorizing {aid[:8]} on Blockchain...")
                self.send_tx(self.contract.functions.authorizeDevice(aid))

    def handle_telemetry(self, packet):
        # Format: AID|Data|...|SN|TS
        parts = packet["payload"].split("|")
        if len(parts) < 3: return

        aid = parts[0]
        try: sn = int(parts[-2])
        except: return

        val = "|".join(parts[1:-2]) 
        
        if aid not in self.kel_registry: return
>>>>>>> Stashed changes
        device = self.kel_registry[aid]

        # 2. Anti-Replay Check
        if sn <= device["last_sn"]:
            print(f"  REPLAY ATTACK BLOCKED for {aid}: sn {sn} <= {device['last_sn']}")
            return

<<<<<<< Updated upstream
        # 3. Verify Signature using STORED Key
        pk_raw = device["pk"]
        sig_raw = from_cesr_sig(sig_cesr)
        
        if verify_ed25519(pk_raw, payload, sig_raw):
            print(f" VERIFIED: {aid[:8]}... | {val} | Anchoring...")
            device["last_sn"] = sn # Update Sequence State
        else:
            print(f" SECURITY ALERT: Invalid Signature from {aid}")
=======
        if verify_ed25519(device["pk"], packet["payload"], from_cesr_sig(packet["sig"])):
            logging.info(f" DATA VERIFIED: {val} | Anchoring...")
            device["last_sn"] = sn
            self.update_dashboard(aid, val, sn, "VERIFIED")
            if self.w3:
                h = hashlib.sha256(packet["payload"].encode()).hexdigest()
                self.send_tx(self.contract.functions.registerAnchor(aid, sn, h))
        else:
            logging.warning(f" INVALID SIG from {aid}")

    def update_dashboard(self, aid, val, sn, status):
        db_file = "dashboard_data.json"
        data = {}
        try:
            with open(db_file, "r") as f: data = json.load(f)
        except: pass
        data[aid] = {"val": val, "sn": sn, "status": status, "ts": time.time()}
        with open(db_file, "w") as f: json.dump(data, f)
>>>>>>> Stashed changes

if __name__ == "__main__":
    gw = SecureGateway()
    gw.start()