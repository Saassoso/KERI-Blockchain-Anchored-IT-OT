# sim_devices.py - Simulates ESP32 #1 and ESP32 #2
import time
import json
import random
import threading
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"

# --- DEVICE A: The Voltage Sensor (Sender) ---
def run_voltage_sensor():
    client = mqtt.Client(client_id="ESP32_SENSOR_A")
    client.connect(MQTT_BROKER, 1883, 60)
    
    print("[ESP32 A] Voltage Sensor Started...")
    
    while True:
        # Simulate voltage fluctuation (220V +/- random)
        voltage = 220 + random.randint(-5, 5)
        
        payload = {
            "id": "ESP32_SENSOR_A",
            "token": "SECRET_TOKEN_123", # <--- The Key
            "type": "voltage",
            "val": voltage,
            "unit": "V"
        }
        
        client.publish("substation/monitor/voltage", json.dumps(payload))
        print(f"[ESP32 A] Sent: {voltage}V")
        time.sleep(3) # Send every 3 seconds

# --- DEVICE B: The Relay/Breaker (Receiver) ---
def run_relay_actuator():
    def on_message(client, userdata, msg):
        print(f"\n[ESP32 B] ⚡ COMMAND RECEIVED: {msg.payload.decode()}")
        print("[ESP32 B] *CLICK* -> BREAKER STATE CHANGED\n")

    client = mqtt.Client(client_id="ESP32_RELAY_B")
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe("substation/control/breaker")
    
    print("[ESP32 B] Relay Actuator Listening...")
    client.loop_forever()

if __name__ == "__main__":
    # Run both devices in parallel
    t1 = threading.Thread(target=run_voltage_sensor)
    t2 = threading.Thread(target=run_relay_actuator)
    
    t1.start()
    t2.start()