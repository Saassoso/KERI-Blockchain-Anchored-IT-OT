import streamlit as st
import json
import time
import os
import paho.mqtt.client as mqtt
from scripts.utils import load_libsodium

# 1. Load Crypto Libs
load_libsodium()
import pysodium

# --- CONFIGURATION ---
ANCHOR_FILE = "blockchain_anchor_gateway.json"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# VOTRE CLÉ PRIVÉE (Celle de scada_commander.py)
SCADA_PRIVATE_KEY_HEX = "20ec6203f824d2544e4230d04bb62488cc3ac4cc00e1df4a1fc94c6712c82ba3e7da49932640a662a61cca5affafb16cfa523edb9e0e8bf64e8b293a49e1e1ea"

# --- SETUP PAGE ---
st.set_page_config(page_title="Secure Grid SCADA", layout="wide")
st.title("⚡ Secure Smart Grid Monitor")
st.markdown("### Zero-Trust Architecture: KERI + Blockchain Anchoring")

# --- SIDEBAR (CONTROLS) ---
st.sidebar.header("🔐 Command Center")
st.sidebar.info("Authorized Admin Only")

def send_command(cmd_string):
    try:
        # 1. Sign
        signature = pysodium.crypto_sign_detached(
            cmd_string.encode('utf-8'),
            bytes.fromhex(SCADA_PRIVATE_KEY_HEX)
        )
        
        # 2. Payload
        payload = {
            "cmd": cmd_string,
            "sig": signature.hex(),
            "timestamp": time.time()
        }
        
        # 3. Publish via MQTT
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish("substation/control/breaker", json.dumps(payload))
        client.disconnect()
        return True
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
        return False

# Control Buttons
if st.sidebar.button("🚨 EMERGENCY OPEN (BLACKOUT)", type="primary"):
    if send_command("OPEN_BREAKER"):
        st.sidebar.success("COMMAND SENT: OPEN_BREAKER")

if st.sidebar.button("✅ CLOSE BREAKER (RESTORE)"):
    if send_command("CLOSE_BREAKER"):
        st.sidebar.success("COMMAND SENT: CLOSE_BREAKER")

# --- MAIN DISPLAY (VISUALIZATION) ---
col1, col2, col3 = st.columns(3)

# Placeholder for metrics
voltage_metric = col1.empty()
status_metric = col2.empty()
seq_metric = col3.empty()

chart_placeholder = st.empty()

# Initialize Session State for Chart History
if "voltage_history" not in st.session_state:
    st.session_state.voltage_history = []

# --- AUTO-REFRESH LOOP ---
# This simulates a real-time dashboard update
while True:
    try:
        if os.path.exists(ANCHOR_FILE):
            with open(ANCHOR_FILE, "r") as f:
                data = json.load(f)
            
            # Extract Data
            snapshot = data.get("data_snapshot", {})
            voltage = snapshot.get("val", 0)
            seq = data.get("seq", 0)
            aid = data.get("aid", "Unknown")

            # Update Metrics
            voltage_metric.metric("Grid Voltage", f"{voltage} V", "Normal" if voltage > 210 else "Low")
            status_metric.success(f"✅ Blockchain Verified")
            seq_metric.metric("KERI Sequence", f"#{seq}")

            # Update Chart
            st.session_state.voltage_history.append(voltage)
            if len(st.session_state.voltage_history) > 50:
                st.session_state.voltage_history.pop(0) # Keep last 50 points
            
            chart_placeholder.line_chart(st.session_state.voltage_history)

        else:
            status_metric.warning("⚠️ Waiting for Gateway Anchor...")
            
    except Exception as e:
        status_metric.error("Read Error")
    
    time.sleep(1) # Refresh every second