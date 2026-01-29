import time
import json
import random
import os
import sys
import ctypes
import hashlib
import base64
import threading
import paho.mqtt.client as mqtt
from ctypes.util import find_library

# ==========================================
#  VIRTUAL SECURE ELEMENT (Crypto Abstraction)
# ==========================================
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib:
        # Fallback for Windows/Linux
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    if not lib:
        print(" ERROR: Libsodium not found. Please install 'pysodium' or check system libraries.")
        sys.exit(1)
    return ctypes.cdll.LoadLibrary(lib)

_sodium = load_crypto()

def generate_keypair():
    """ Generates Ed25519 Keys (Simulating Hardware Keygen) """
    pk = ctypes.create_string_buffer(32)
    sk = ctypes.create_string_buffer(64)
    _sodium.crypto_sign_keypair(pk, sk)
    return pk.raw, sk.raw

def sign_data(msg, sk):
    """ Atomic Ed25519 Sign """
    sig = ctypes.create_string_buffer(64)
    msg_bytes = msg.encode('utf-8')
    _sodium.crypto_sign_detached(sig, None, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), sk)
    return sig.raw

def to_cesr(raw_bytes, code="0B"):
    """ Encodes raw bytes to KERI CESR Format (Base64URL + Prefix) """
    # 0B is the CESR code for Ed25519 attached signature
    b64 = base64.urlsafe_b64encode(raw_bytes).decode('utf-8').rstrip('=')
    return f"{code}{b64}"

# ==========================================
#  KERI EVENT ENGINE (The Identity Core)
# ==========================================
class KeriController:
    def __init__(self, alias):
        self.alias = alias
        # Each device gets its own "Secure Storage" file
        self.keystore = f"{alias}_keystore.json"
        self.load_or_create_identity()

    def load_or_create_identity(self):
        """ Manages Persistence of the KERI Identity """
        if os.path.exists(self.keystore):
            with open(self.keystore, "r") as f:
                data = json.load(f)
                self.pk = bytes.fromhex(data["pk"])
                self.sk = bytes.fromhex(data["sk"])
                self.next_pk = bytes.fromhex(data["next_pk"]) # Pre-Rotation
                self.aid = data["aid"]
                print(f"[{self.alias}] Loaded Identity: {self.aid}")
        else:
            print(f"[{self.alias}] ⚙️ Generating New KERI Identity...")
            self.pk, self.sk = generate_keypair()
            self.next_pk, _ = generate_keypair() # Generate Next Key (Pre-Rotation)
            
            # AID in Basic mode is the Public Key (Base64)
            self.aid = to_cesr(self.pk, code="D") # D = Ed25519 Public Key
            
            self.save_identity()

    def save_identity(self):
        with open(self.keystore, "w") as f:
            json.dump({
                "pk": self.pk.hex(), 
                "sk": self.sk.hex(),
                "next_pk": self.next_pk.hex(),
                "aid": self.aid
            }, f)

    def make_inception_event(self):
        """ Creates the 'icp' Event (The Root of Trust) """
        # Next Key Digest (Hashing the future key for Quantum Resistance)
        next_digest = hashlib.blake2b(self.next_pk, digest_size=32).hexdigest()
        
        # Simplified KERI Inception Event
        event = {
            "v": "KERI10JSON000000",
            "t": "icp",
            "d": "", 
            "i": self.aid,
            "s": "0",
            "kt": "1",
            "k": [to_cesr(self.pk, "D")], # Current Key
            "n": next_digest,             # Next Key Commitment
            "wt": "0",
            "w": [],
            "c": []
        }
        
        # Serialize & Sign
        raw_event = json.dumps(event, sort_keys=True)
        sig_raw = sign_data(raw_event, self.sk)
        cesr_sig = to_cesr(sig_raw, "0B") # 0B = Ed25519 Sig
        
        return event, cesr_sig

    def sign_telemetry(self, val, sn):
        """ Signs a data payload (simulating an 'ixn' anchor) """
        timestamp = time.time()
        # Payload Format: AID|Value|Sequence|Timestamp
        payload = f"{self.aid}|{val}|{sn}|{timestamp}"
        sig_raw = sign_data(payload, self.sk)
        
        packet = {
            "type": "telemetry",
            "payload": payload,
            "sig": to_cesr(sig_raw, "0B") # CESR Signature
        }
        return packet

# ==========================================
#  VIRTUAL DEVICE (Network & Physics Layer)
# ==========================================
class VirtualDevice:
    def __init__(self, name, device_type):
        self.name = name
        self.device_type = device_type
        self.keri = KeriController(name)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
        self.sn = 0 # Monotonic Sequence Number

    def start(self):
        try:
            self.client.connect("localhost", 1883, 60)
            self.client.loop_start()
        except:
            print(f"[{self.name}]  Connection Failed. Is Mosquitto running?")
            return

        # STEP 1: BOOTSTRAP (Send Inception Event)
        print(f"[{self.name}]  Broadcasting Inception Event (Bootstrap)...")
        event, sig = self.keri.make_inception_event()
        bootstrap_packet = {
            "type": "icp",
            "event": event,
            "sig": sig
        }
        self.client.publish("keri/bootstrap", json.dumps(bootstrap_packet), qos=2)
        time.sleep(2)

        # STEP 2: MAIN LOOP (Telemetry)
        while True:
            self.sn += 1
            payload_val = ""

            # --- PHYSICS ENGINE & ATTACK SIMULATION ---
            if self.device_type == "TEMP":
                # Normal: 20-25C.
                base_temp = 22.0
                noise = random.uniform(-0.5, 0.5)
                
                # == ATTACK SIMULATION ==
                # Every 10th packet, try to REPLAY an old sequence number (Attack)
                if self.sn % 10 == 0:
                     print(f"[{self.name}] 😈 SIMULATING REPLAY ATTACK: Sending old SN 5...")
                     packet = self.keri.sign_telemetry(base_temp, 5) # SN 5 is extremely old!
                     self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
                     time.sleep(3)
                     continue 

                val = round(base_temp + noise, 2)
                payload_val = f"{val}C"

            elif self.device_type == "PDU":
                # Power Distribution Unit
                val = round(230.0 + random.uniform(-1, 1), 1)
                payload_val = f"{val}V"

            elif self.device_type == "DOOR":
                # Access Control
                state = "CLOSED" if random.random() > 0.1 else "OPEN"
                payload_val = state

            # --- SIGN & SEND ---
            packet = self.keri.sign_telemetry(payload_val, self.sn)
            self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
            
            print(f"[{self.name}] 📤 Sent {payload_val} | sn:{self.sn} | 🔏 Sig:{packet['sig'][:10]}...")
            time.sleep(3)

if __name__ == "__main__":
    print("---  STARTING DATACENTER KERI SIMULATION ---")
    
    # Spawn 3 Threads for the 3 Scenario Devices
    d1 = VirtualDevice("DC-TEMP-01", "TEMP")
    d2 = VirtualDevice("DC-PDU-A", "PDU")
    d3 = VirtualDevice("DC-ACCESS-GATE", "DOOR")

    t1 = threading.Thread(target=d1.start)
    t2 = threading.Thread(target=d2.start)
    t3 = threading.Thread(target=d3.start)

    t1.start()
    t2.start()
    t3.start()