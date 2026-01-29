import time
import json
import random
import os
<<<<<<< Updated upstream
import sys
import ctypes
import hashlib
=======
>>>>>>> Stashed changes
import base64
import ctypes
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
<<<<<<< Updated upstream
                print(f"[{self.alias}] Loaded Identity: {self.aid}")
        else:
            print(f"[{self.alias}] ⚙️ Generating New KERI Identity...")
=======
                print(f"[{self.alias}]  Identity Loaded: {self.aid}")
        else:
            print(f"[{self.alias}]  Provisioning Identity...")
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        
        packet = {
            "type": "telemetry",
            "payload": payload,
            "sig": to_cesr(sig_raw, "0B") # CESR Signature
        }
        return packet
=======
        return {"type": "telemetry", "payload": payload, "sig": to_cesr(sig_raw, "0B")}

# --- 3. SHARED PHYSICS STATE ---
# Global flags affecting all threads
SYSTEM_LOCKDOWN = False
HVAC_RUNNING = True
SECURITY_IMMUNITY = 0 # Counter to block attacks after admin command
>>>>>>> Stashed changes

# ==========================================
#  VIRTUAL DEVICE (Network & Physics Layer)
# ==========================================
class VirtualDevice:
    def __init__(self, name, device_type):
        self.name = name
        self.device_type = device_type
        self.keri = KeriController(name)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
<<<<<<< Updated upstream
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
=======
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sn = 0
        
        # Physics State
        self.cpu_load = 30.0 
        self.temp = 35.0     
        self.fan_rpm = 4000

    def on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe("control/broadcast")

    def on_message(self, client, userdata, msg):
        global SYSTEM_LOCKDOWN, HVAC_RUNNING, SECURITY_IMMUNITY
        try:
            payload = json.loads(msg.payload.decode())
            if "cmd" in payload:
                cmd = payload["cmd"]
                
                # --- COMMAND: LOCKDOWN (Kill Switch) ---
                if cmd == "OPEN_BREAKER": 
                    print(f"\n[{self.name}]  COMMAND RECEIVED: INITIATING LOCKDOWN!\n")
                    SYSTEM_LOCKDOWN = True
                    SECURITY_IMMUNITY = 30 # Grant 30 ticks of immunity
                    if self.device_type == "HVAC": HVAC_RUNNING = True 

                # --- COMMAND: RESTORE (Reset) ---
                elif cmd == "CLOSE_BREAKER":
                    print(f"\n[{self.name}]  COMMAND RECEIVED: RESTORING OPERATIONS.\n")
                    SYSTEM_LOCKDOWN = False
                    SECURITY_IMMUNITY = 30 # Grant 30 ticks of immunity
                    if self.device_type == "HVAC": HVAC_RUNNING = True
        except: pass

    def start(self):
        global HVAC_RUNNING, SYSTEM_LOCKDOWN, SECURITY_IMMUNITY
        
        self.client.connect("localhost", 1883, 60)
        self.client.loop_start()
        
        # KERI BOOTSTRAP
>>>>>>> Stashed changes
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
            if SECURITY_IMMUNITY > 0: SECURITY_IMMUNITY -= 1 # Countdown immunity
            
            payload_val = ""
<<<<<<< Updated upstream

            # --- PHYSICS ENGINE & ATTACK SIMULATION ---
            if self.device_type == "TEMP":
                # Normal: 20-25C.
                base_temp = 22.0
                noise = random.uniform(-0.5, 0.5)
=======
            
            # === PHYSICS ENGINE ===
            
            if self.device_type == "SERVER":
                # 1. Determine Load
                if SYSTEM_LOCKDOWN:
                    target_load = 5.0 # Idle
                else:
                    target_load = 65.0 # Normal
>>>>>>> Stashed changes
                
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

<<<<<<< Updated upstream
            elif self.device_type == "PDU":
                # Power Distribution Unit
                val = round(230.0 + random.uniform(-1, 1), 1)
                payload_val = f"{val}V"

            elif self.device_type == "DOOR":
                # Access Control
                state = "CLOSED" if random.random() > 0.1 else "OPEN"
                payload_val = state
=======
                # 3. Cooling
                if HVAC_RUNNING:
                    cooling_power = (self.temp - 20.0) * 0.05 
                else:
                    cooling_power = (self.temp - 20.0) * 0.005 

                # 4. Apply Physics
                self.temp = self.temp + heat_gen - cooling_power
                self.temp = max(20.0, self.temp)

                payload_val = f"CPU:{int(self.cpu_load)}%|Temp:{round(self.temp, 1)}C"

            elif self.device_type == "HVAC":
                # Attack Logic: Every 25 ticks
                is_attack_window = (self.sn > 20 and self.sn % 25 < 10) 
                
                # Only Attack if NO Immunity and NOT Lockdown
                is_attack_active = is_attack_window and not SYSTEM_LOCKDOWN and SECURITY_IMMUNITY == 0

                if is_attack_active:
                    HVAC_RUNNING = False 
                    self.fan_rpm = 0 
                    print(f"[{self.name}]  ATTACK: COOLING DISABLED (Spoofing Normal)...")
                    
                    fake_payload = "FAN:5000RPM|PWR:Normal"
                    packet = self.keri.sign_telemetry(fake_payload, 5) 
                    self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
                    time.sleep(3)
                    continue 
                    
                else:
                    # Normal Operation (or Immunity Active)
                    HVAC_RUNNING = True
                    self.fan_rpm = int(4500 + random.uniform(-100, 100))

                payload_val = f"FAN:{self.fan_rpm}RPM|PWR:Active"

            elif self.device_type == "DOOR":
                if SYSTEM_LOCKDOWN:
                    state = "LOCKED" 
                elif self.temp > 95.0: # Raised threshold slightly
                    state = "UNLOCKED" # Fire Risk!
                else:
                    state = "LOCKED"
                    
                payload_val = f"{state}|Log:Secure"
>>>>>>> Stashed changes

            # --- SIGN & SEND ---
            packet = self.keri.sign_telemetry(payload_val, self.sn)
            self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
            
<<<<<<< Updated upstream
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
=======
            # Console Status
            status = "❄️" if HVAC_RUNNING else "🔥"
            if self.device_type == "SERVER":
                print(f"[{self.name}] {status} Temp:{round(self.temp,1)}C | Load:{int(self.cpu_load)}%")
            else:
                print(f"[{self.name}]  {payload_val} | sn:{self.sn}")
            
            time.sleep(3)

if __name__ == "__main__":
    print("---  STARTING FORTRESS-1 PHYSICS SIMULATION ---")
    t1 = threading.Thread(target=VirtualDevice("RACK-99-CORE", "SERVER").start)
    t2 = threading.Thread(target=VirtualDevice("HVAC-MASTER", "HVAC").start)
    t3 = threading.Thread(target=VirtualDevice("BIO-MANTRAP", "DOOR").start)
    t1.start(); t2.start(); t3.start()
>>>>>>> Stashed changes
