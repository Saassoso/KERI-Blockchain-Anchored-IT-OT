import time
import json
import random
import os
import ctypes
import base64
import threading
import paho.mqtt.client as mqtt

# --- 1. CRYPTO LIB ---
from scripts.utils import load_libsodium
load_libsodium() # Injects keri-env/Scripts/ into the Windows DLL search path

def load_crypto():
    try:
        # Load directly now that the path is resolved
        return ctypes.cdll.LoadLibrary('libsodium.dll')
    except OSError:
        from ctypes.util import find_library
        lib = find_library('sodium') or find_library('libsodium')
        return ctypes.cdll.LoadLibrary(lib) if lib else None

_sodium = load_crypto()

if _sodium is None:
    print("CRITICAL: Libsodium failed to load. Check keri-env/Scripts/libsodium.dll")
    os._exit(1)

def generate_keypair():
    pk = ctypes.create_string_buffer(32)
    sk = ctypes.create_string_buffer(64)
    _sodium.crypto_sign_keypair(pk, sk)
    return pk.raw, sk.raw

def sign_data(msg, sk):
    sig = ctypes.create_string_buffer(64)
    msg_bytes = msg.encode('utf-8')
    _sodium.crypto_sign_detached(sig, None, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), sk)
    return sig.raw

def to_cesr(raw_bytes, code="0B"):
    b64 = base64.urlsafe_b64encode(raw_bytes).decode('utf-8').rstrip('=')
    return f"{code}{b64}"

# --- 2. KERI IDENTITY ---
class KeriController:
    def __init__(self, alias):
        self.alias = alias
        self.keystore = f"{alias}_keystore.json"
        self.load_or_create_identity()

    def load_or_create_identity(self):
        if os.path.exists(self.keystore):
            with open(self.keystore, "r") as f:
                data = json.load(f)
                self.pk = bytes.fromhex(data["pk"])
                self.sk = bytes.fromhex(data["sk"])
                self.aid = data["aid"]
                print(f"[{self.alias}] 💾 Identity Loaded: {self.aid}")
        else:
            print(f"[{self.alias}] ⚙️ Provisioning Identity...")
            self.pk, self.sk = generate_keypair()
            self.aid = to_cesr(self.pk, code="D")
            with open(self.keystore, "w") as f:
                json.dump({"pk": self.pk.hex(), "sk": self.sk.hex(), "aid": self.aid}, f)

    def make_inception_event(self):
        event = {"v": "KERI10JSON000000", "t": "icp", "d": "", "i": self.aid, "s": "0", "kt": "1", "k": [to_cesr(self.pk, "D")], "n": "", "wt": "0", "w": [], "c": []}
        raw_event = json.dumps(event, sort_keys=True)
        sig_raw = sign_data(raw_event, self.sk)
        return event, to_cesr(sig_raw, "0B")

    def sign_telemetry(self, val, sn):
        timestamp = time.time()
        payload = f"{self.aid}|{val}|{sn}|{timestamp}"
        sig_raw = sign_data(payload, self.sk)
        return {"type": "telemetry", "payload": payload, "sig": to_cesr(sig_raw, "0B")}

# --- 3. SHARED PHYSICS STATE ---
SYSTEM_LOCKDOWN = False
HVAC_RUNNING = True  
HVAC_SETPOINT = 22.0

class VirtualDevice:
    def __init__(self, name, device_type):
        self.name, self.device_type = name, device_type
        self.keri = KeriController(name)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sn = 0
        
        # Initial Physics State
        self.cpu_load = 30.0 
        self.temp = 35.0     
        self.fan_rpm = 4000

    def on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe("control/broadcast")

    def on_message(self, client, userdata, msg):
        global SYSTEM_LOCKDOWN, HVAC_RUNNING
        try:
            payload = json.loads(msg.payload.decode())
            if "cmd" in payload:
                cmd = payload["cmd"]
                
                # --- COMMAND: LOCKDOWN (Kill Switch) ---
                if cmd == "OPEN_BREAKER": 
                    if not SYSTEM_LOCKDOWN:
                        print(f"\n[{self.name}] 🛡️ COMMAND RECEIVED: INITIATING LOCKDOWN (Shedding Load)\n")
                        SYSTEM_LOCKDOWN = True
                        if self.device_type == "HVAC": HVAC_RUNNING = True 

                # --- COMMAND: RESTORE (Reset) ---
                elif cmd == "CLOSE_BREAKER":
                    if SYSTEM_LOCKDOWN:
                        print(f"\n[{self.name}] 🔄 COMMAND RECEIVED: RESTORING OPERATIONS\n")
                        SYSTEM_LOCKDOWN = False
                        if self.device_type == "HVAC": HVAC_RUNNING = True
        except: pass

    def start(self):
        global HVAC_RUNNING, SYSTEM_LOCKDOWN
        
        self.client.connect("localhost", 1883, 60)
        self.client.subscribe("control/broadcast")
        self.client.loop_start()
        
        # KERI BOOTSTRAP
        event, sig = self.keri.make_inception_event()
        self.client.publish("keri/bootstrap", json.dumps({"type": "icp", "event": event, "sig": sig}), qos=2)
        time.sleep(2)

        while True:
            self.sn += 1
            payload_val = ""
            
            # === PHYSICS ENGINE ===
            
            if self.device_type == "SERVER":
                # 1. Determine Load
                if SYSTEM_LOCKDOWN:
                    target_load = 5.0 # Idle state
                else:
                    target_load = 65.0 # Normal heavy banking load
                
                # Smooth transition
                if self.cpu_load < target_load: self.cpu_load += 5
                elif self.cpu_load > target_load: self.cpu_load -= 5
                
                self.cpu_load += random.uniform(-2, 2)
                self.cpu_load = max(0, min(100, self.cpu_load))

                # 2. Heat Generation
                heat_gen = (self.cpu_load / 100.0) * 1.5 

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
                is_attack = (self.sn > 20 and self.sn % 25 < 10) 
                
                if SYSTEM_LOCKDOWN:
                    HVAC_RUNNING = True
                    self.fan_rpm = 8000 
                    
                elif is_attack:
                    HVAC_RUNNING = False 
                    self.fan_rpm = 0 
                    print(f"[{self.name}] 😈 ATTACK: COOLING DISABLED (Spoofing Normal)...")
                    
                    fake_payload = "FAN:5000RPM|PWR:Normal"
                    packet = self.keri.sign_telemetry(fake_payload, 5) 
                    self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
                    time.sleep(3)
                    continue 
                    
                else:
                    HVAC_RUNNING = True
                    self.fan_rpm = int(4500 + random.uniform(-100, 100))

                payload_val = f"FAN:{self.fan_rpm}RPM|PWR:Active"

            elif self.device_type == "DOOR":
                if SYSTEM_LOCKDOWN:
                    state = "LOCKED" 
                elif self.temp > 85.0:
                    state = "UNLOCKED" # Fire Risk!
                else:
                    state = "LOCKED"
                    
                payload_val = f"{state}|Log:Secure"

            # SEND DATA
            packet = self.keri.sign_telemetry(payload_val, self.sn)
            self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
            
            # Console Status
            status = "❄️" if HVAC_RUNNING else "🔥"
            if self.device_type == "SERVER":
                print(f"[{self.name}] {status} Temp:{round(self.temp,1)}C | Load:{int(self.cpu_load)}%")
            else:
                print(f"[{self.name}] 📤 {payload_val} | sn:{self.sn}")
            
            time.sleep(3)

if __name__ == "__main__":
    print("--- 🏢 STARTING FORTRESS-1 PHYSICS SIMULATION ---")
    t1 = threading.Thread(target=VirtualDevice("RACK-99-CORE", "SERVER").start)
    t2 = threading.Thread(target=VirtualDevice("HVAC-MASTER", "HVAC").start)
    t3 = threading.Thread(target=VirtualDevice("BIO-MANTRAP", "DOOR").start)
    t1.start(); t2.start(); t3.start()