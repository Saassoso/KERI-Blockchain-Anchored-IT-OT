import time
import json
import ctypes
import threading
import paho.mqtt.client as mqtt
from ctypes.util import find_library

# --- CRYPTO SETUP ---
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib: lib = ctypes.util.find_library('libsodium.dll')
    return ctypes.cdll.LoadLibrary(lib) if lib else None

_sodium = load_crypto()

def sign(msg, sk):
    sig = ctypes.create_string_buffer(64)
    _sodium.crypto_sign_detached(sig, None, msg.encode('utf-8'), ctypes.c_ulonglong(len(msg)), sk)
    return sig.raw.hex()

# --- HACKER KEYS (Unauthorized) ---
ROGUE_PK = ctypes.create_string_buffer(32)
ROGUE_SK = ctypes.create_string_buffer(64)
if _sodium:
    _sodium.crypto_sign_keypair(ROGUE_PK, ROGUE_SK)

class AttackConsole:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="HACKER_CONSOLE")
        try:
            self.client.connect("localhost", 1883, 60)
            self.client.loop_start()
            print("💀 HACKER CONSOLE ONLINE. Connected to Grid.")
        except:
            print("❌ Connection Failed. Is Mosquitto running?")

    def attack_1_rogue_device(self):
            print("\n[ATTACK 1] 👽 Launching Rogue Device Spoofing...")
            # REMOVED "Temp:" and "SN:" labels to match gateway expectations
            payload = "AID_UNKNOWN_DEVICE|Critical|1|0"
            sig = sign(payload, ROGUE_SK)
            
            packet = {"payload": payload, "sig": sig}
            self.client.publish("telemetry/UNKNOWN", json.dumps(packet))
            print(">> 📤 Packet Sent. Check Gateway for 'UNKNOWN DEVICE'.")

    def attack_2_fake_admin(self):
        print("\n[ATTACK 2] 🕵️ Launching Privilege Escalation (Fake Admin)...")
        # We try to send a critical SCADA command (OPEN_DOOR) signed by US (Rogue), not the real Admin
        cmd_str = "OPEN_DOOR"
        sig = sign(cmd_str, ROGUE_SK) # Wrong Key!
        
        fake_cmd = {"cmd": cmd_str, "sig": sig, "ts": time.time()}
        self.client.publish("substation/control/breaker", json.dumps(fake_cmd))
        print(">> 📤 Fake Command Sent. Check Gateway for 'UNAUTHORIZED COMMAND'.")

    def attack_3_tampering(self):
        print("\n[ATTACK 3] ✂️ Launching Data Tampering (Man-in-the-Middle)...")
        # We pretend to be RACK-99 (Valid AID), but we don't have their Private Key.
        # We inject a dangerous value "Temp:FIRE" but sign it with OUR Key.
        
        target_aid = "RACK-99-CORE" # Matches your simulation name (if generated) or generic
        # If simulation is running, it generated a long KERI AID. 
        # For this demo, the Gateway will check the AID in the payload.
        # Since we don't know the Real AID from this script easily, let's use a generic one 
        # or rely on the Gateway catching the Key Mismatch.
        
        # Let's try to spoof the one from your logs if possible, or just a generic one.
        # Gateway check: if AID is unknown -> Rogue Device. 
        # So for Tampering, we usually need to capture a real packet and modify it.
        # SIMPLIFIED: We send a packet with a known format but Signed by Rogue Key.
        
        payload = "DqhTCDXc7k8dVmLzCR8stubRUD6si8kMdczwMehhDz4I|Temp:999.9C|SN:1000|TS:0" 
        # (Using a random AID that looks real)
        
        sig = sign(payload, ROGUE_SK) # Invalid Signature for that AID
        packet = {"payload": payload, "sig": sig}
        
        self.client.publish("telemetry/RACK-99", json.dumps(packet))
        print(">> 📤 Tampered Packet Sent. Check Gateway for 'INTEGRITY FAILURE'.")

    def attack_4_replay(self):
            print("\n[ATTACK 4] 🔄 Replaying old packet (SN: 1)...")
            # Ensure the payload format is AID|Value|SN|Timestamp
            payload = "DqhTCDXc7k8dVmLzCR8stubRUD6si8kMdczwMehhDz4I|22.0C|1|0"
            sig = sign(payload, ROGUE_SK)
            packet = {"payload": payload, "sig": sig}
            self.client.publish("telemetry/RACK-99", json.dumps(packet))
            print(">> 📤 Replay Sent. Gateway should log 'REPLAY BLOCKED'.")

    def run(self):
        while True:
            print("\n" + "="*40)
            print("   💀 SELECT ATTACK VECTOR 💀")
            print("="*40)
            print("1.  Rogue Device (Intrusion)")
            print("2.  Fake Admin Command (Privilege Escalation)")
            print("3.  Data Tampering (Integrity Violation)")
            print("4.  Replay Attack")
            print("5.  Exit")

            choice = input("\nSelect Option [1-5]: ")

            if choice == '1': self.attack_1_rogue_device()
            elif choice == '2': self.attack_2_fake_admin()
            elif choice == '3': self.attack_3_tampering()
            elif choice == '4': self.attack_4_replay()
            elif choice == '5': break
            else: print("Invalid Selection")
            
            time.sleep(1)

if __name__ == "__main__":
    if not _sodium:
        print(" Libsodium not found. Cannot sign packets.")
    else:
        console = AttackConsole()
        console.run()