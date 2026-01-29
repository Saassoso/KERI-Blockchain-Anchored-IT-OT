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

def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib:
        lib = ctypes.util.find_library('libsodium.dll') or ctypes.util.find_library('libsodium.so')
    return ctypes.cdll.LoadLibrary(lib)

_sodium = load_crypto()

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
                print(f"[{self.alias}] 💾 Loaded Identity: {self.aid}")
        else:
            print(f"[{self.alias}] ⚙️ Generating New KERI Identity...")
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

class VirtualDevice:
    def __init__(self, name, device_type):
        self.name = name
        self.device_type = device_type
        self.keri = KeriController(name)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sn = 0
        self.breaker_open = False # Actuator State

    def on_connect(self, client, userdata, flags, rc, properties=None):
        # LISTEN FOR COMMANDS FROM GATEWAY
        client.subscribe("control/broadcast")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if "cmd" in payload:
                cmd = payload["cmd"]
                print(f"[{self.name}] ⚡ RECEIVED COMMAND: {cmd}")
                if cmd == "OPEN_BREAKER":
                    self.breaker_open = True
                    print(f"[{self.name}] 🚨 EMERGENCY SHUTDOWN INITIATED!")
                elif cmd == "CLOSE_BREAKER":
                    self.breaker_open = False
                    print(f"[{self.name}] ✅ SYSTEM RESTORED.")
        except: pass

    def start(self):
        self.client.connect("localhost", 1883, 60)
        self.client.loop_start()

        # Bootstrap
        event, sig = self.keri.make_inception_event()
        self.client.publish("keri/bootstrap", json.dumps({"type": "icp", "event": event, "sig": sig}), qos=2)
        time.sleep(2)

        while True:
            self.sn += 1
            payload_val = ""

            if self.device_type == "TEMP":
                if self.breaker_open: val = 0.0 # Shutdown
                else: val = round(22.0 + random.uniform(-0.5, 0.5), 2)
                
                # Attack Sim
                if self.sn % 20 == 0: 
                    print(f"[{self.name}] 😈 SIMULATING ATTACK...")
                    packet = self.keri.sign_telemetry(val, 5) # Old SN
                    self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
                    time.sleep(3)
                    continue 
                payload_val = f"{val}C"

            elif self.device_type == "PDU":
                if self.breaker_open: val = 0.0
                else: val = round(230.0 + random.uniform(-1, 1), 1)
                payload_val = f"{val}V"

            elif self.device_type == "DOOR":
                payload_val = "OPEN" if self.breaker_open else "CLOSED"

            packet = self.keri.sign_telemetry(payload_val, self.sn)
            self.client.publish(f"telemetry/{self.name}", json.dumps(packet))
            print(f"[{self.name}] 📤 {payload_val} | sn:{self.sn}")
            time.sleep(3)

if __name__ == "__main__":
    t1 = threading.Thread(target=VirtualDevice("DC-TEMP-01", "TEMP").start)
    t2 = threading.Thread(target=VirtualDevice("DC-PDU-A", "PDU").start)
    t3 = threading.Thread(target=VirtualDevice("DC-ACCESS-GATE", "DOOR").start)
    t1.start(); t2.start(); t3.start()