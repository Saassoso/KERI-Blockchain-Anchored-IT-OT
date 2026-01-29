import json
import time
import paho.mqtt.client as mqtt
import sys
import os

# --- FIX: Load Libsodium FIRST ---
# This requires scripts/utils.py to be present in the same folder structure
from scripts.utils import load_libsodium
load_libsodium()
import pysodium
# ---------------------------------

# CONFIG
MQTT_BROKER = "localhost"

# --- YOUR PRIVATE KEY (From gen_keys.py) ---
SCADA_PRIVATE_KEY_HEX = "20ec6203f824d2544e4230d04bb62488cc3ac4cc00e1df4a1fc94c6712c82ba3e7da49932640a662a61cca5affafb16cfa523edb9e0e8bf64e8b293a49e1e1ea"

def send_command(cmd_string):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, 1883, 60)

    # 1. Sign the Command
    signature = pysodium.crypto_sign_detached(
        cmd_string.encode('utf-8'),
        bytes.fromhex(SCADA_PRIVATE_KEY_HEX)
    )

    # 2. Build Payload
    payload = {
        "cmd": cmd_string,
        "sig": signature.hex(),
        "timestamp": time.time()
    }

    # 3. Send
    topic = "substation/control/breaker"
    client.publish(topic, json.dumps(payload))
    print(f"📡 SENT SIGNED COMMAND: {cmd_string}")
    print(f"🔏 Signature: {signature.hex()[:20]}...")

if __name__ == "__main__":
    print("--- SCADA COMMAND CENTER ---")
    print("1. 🔓 OPEN BREAKER (Blackout)")
    print("2. 🔒 CLOSE BREAKER (Restore)")
    choice = input("Select Action: ")
    
    if choice == "1":
        send_command("OPEN_BREAKER")
    elif choice == "2":
        send_command("CLOSE_BREAKER")