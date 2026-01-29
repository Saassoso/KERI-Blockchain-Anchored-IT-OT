import json
import time
import base64
import ctypes
from ctypes.util import find_library
import paho.mqtt.client as mqtt

# ==========================================
#  GATEWAY CRYPTO (Verifier)
# ==========================================
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib:
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    return ctypes.cdll.LoadLibrary(lib)

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

# ==========================================
#  GATEWAY LOGIC (Witness/Guardian)
# ==========================================
class SecureGateway:
    def __init__(self):
        # Local KEL Registry
        # { "AID": { "pk": bytes, "last_sn": 0, "status": "ACTIVE" } }
        self.kel_registry = {} 
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Gateway")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        print("🛡️  GATEWAY ONLINE. Waiting for KERI Bootstraps...")
        self.client.connect("localhost", 1883, 60)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe("keri/bootstrap")  # Listen for Inceptions
        client.subscribe("telemetry/#")     # Listen for Data

    def on_message(self, client, userdata, msg):
        try:
            packet = json.loads(msg.payload.decode())
            topic = msg.topic
            
            if topic == "keri/bootstrap":
                self.handle_inception(packet)
            elif "telemetry" in topic:
                self.handle_telemetry(packet)
                
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

        device = self.kel_registry[aid]

        # 2. Anti-Replay Check
        if sn <= device["last_sn"]:
            print(f"  REPLAY ATTACK BLOCKED for {aid}: sn {sn} <= {device['last_sn']}")
            return

        # 3. Verify Signature using STORED Key
        pk_raw = device["pk"]
        sig_raw = from_cesr_sig(sig_cesr)
        
        if verify_ed25519(pk_raw, payload, sig_raw):
            print(f" VERIFIED: {aid[:8]}... | {val} | Anchoring...")
            device["last_sn"] = sn # Update Sequence State
        else:
            print(f" SECURITY ALERT: Invalid Signature from {aid}")

if __name__ == "__main__":
    gw = SecureGateway()
    gw.start()