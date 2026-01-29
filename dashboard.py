import streamlit as st
import json
import time
import os
import pandas as pd
import paho.mqtt.client as mqtt
import ctypes
from ctypes.util import find_library
from dotenv import load_dotenv, find_dotenv

# CONFIG
load_dotenv(find_dotenv(usecwd=True))
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PRIVATE_KEY_HEX = os.getenv("SCADA_PRIVATE_KEY_HEX")
ANCHOR_FILE = "dashboard_data.json"

# LIBSODIUM
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib: lib = ctypes.util.find_library('libsodium.dll')
    return ctypes.cdll.LoadLibrary(lib) if lib else None
_sodium = load_crypto()

st.set_page_config(page_title="Fortress NOC", layout="wide", page_icon="🏢")
st.title("Fortress-1 Data Center NOC")
st.markdown("### Zero-Trust Infrastructure Monitoring")

# STATE
if "temp_history" not in st.session_state:
    st.session_state.temp_history = []

# COMMANDS
def send_command(cmd):
    if not SCADA_PRIVATE_KEY_HEX or not _sodium: return False
    try:
        sig = ctypes.create_string_buffer(64)
        msg_bytes = cmd.encode('utf-8')
        _sodium.crypto_sign_detached(sig, None, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), bytes.fromhex(SCADA_PRIVATE_KEY_HEX))
        payload = {"cmd": cmd, "sig": sig.raw.hex(), "ts": time.time()}
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, 1883, 60)
        client.publish("substation/control/breaker", json.dumps(payload))
        client.disconnect()
        return True
    except: return False

# SIDEBAR
st.sidebar.header("Security Override")
st.sidebar.warning("Use only in case of physical breach or thermal runaway.")
if st.sidebar.button("⛔ INITIATE LOCKDOWN (KILL)", type="primary"):
    send_command("OPEN_BREAKER") # Mapped to Lockdown logic
    st.toast("⛔ LOCKDOWN PROTOCOL INITIATED")

if st.sidebar.button("✅ RESTORE SYSTEMS"):
    send_command("CLOSE_BREAKER")
    st.toast("✅ RESTORING SYSTEMS")

# MAIN VIEW
placeholder = st.empty()

while True:
    data = {}
    if os.path.exists(ANCHOR_FILE):
        try:
            with open(ANCHOR_FILE, "r") as f: data = json.load(f)
        except: pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        current_temp = 0.0
        
        if data:
            for aid, d in data.items():
                val_str = str(d.get('val', ''))
                
                # PARSING LOGIC FOR NEW DATA FORMAT
                if "CPU" in val_str:
                    # Format: CPU:80%|Temp:45.0C
                    try:
                        parts = val_str.split('|')
                        cpu = parts[0].split(':')[1]
                        temp = parts[1].split(':')[1].replace('C','')
                        current_temp = float(temp)
                        
                        # Dynamic Color for Temp
                        temp_delta = f"SN: {d['sn']}"
                        if current_temp > 80: temp_delta = "CRITICAL"
                        
                        c1.metric("🖥️ RACK-99 CORE", f"{cpu} Load", temp_delta)
                        c1.metric("🌡️ Core Temp", f"{temp}°C")
                    except: pass
                    
                elif "FAN" in val_str:
                    # Format: FAN:5000RPM|PWR:Active
                    try:
                        fan = val_str.split('|')[0].split(':')[1]
                        c2.metric(" HVAC MASTER", fan, f"SN: {d['sn']}")
                    except: pass
                    
                elif "LOCKED" in val_str or "UNLOCKED" in val_str:
                    # Format: LOCKED|Log:User
                    try:
                        state = val_str.split('|')[0]
                        c3.metric(" BIO-MANTRAP", state, f"SN: {d['sn']}")
                    except: pass
        else:
            st.info("⏳ Connecting to Secure Gateway...")

        # GRAPH
        st.divider()
        st.subheader("Server Thermal Telemetry")
        
        st.session_state.temp_history.append(current_temp)
        if len(st.session_state.temp_history) > 100:
            st.session_state.temp_history.pop(0)
        
        # Color chart red if high temp
        color = "#ff0000" if current_temp > 75 else "#00ff00"
        st.line_chart(st.session_state.temp_history, color=color)

        # TABLE
        if data:
            st.caption("Immutable Blockchain Audit Log (KERI Anchors)")
            df = pd.DataFrame.from_dict(data, orient='index')
            st.dataframe(df)

    time.sleep(1)