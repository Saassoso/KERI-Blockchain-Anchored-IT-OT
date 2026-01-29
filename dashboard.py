import streamlit as st
import json
import time
import os
import pandas as pd
import paho.mqtt.client as mqtt
import ctypes
from ctypes.util import find_library
from dotenv import load_dotenv, find_dotenv

# LOAD CONFIG
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

st.set_page_config(page_title="KERI SCADA", layout="wide", page_icon="⚡")
st.title("⚡ Secure Smart Grid SCADA")

# SESSION STATE
if "voltage_history" not in st.session_state:
    st.session_state.voltage_history = []

# COMMAND SENDER
def send_command(cmd):
    if not SCADA_PRIVATE_KEY_HEX or not _sodium:
        st.error("❌ Key Error")
        return False
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
    except Exception as e:
        st.error(f"MQTT Error: {e}")
        return False

# CONTROLS
st.sidebar.header("🔐 Admin Controls")
if st.sidebar.button("🚨 EMERGENCY OPEN (BLACKOUT)", type="primary"):
    send_command("OPEN_BREAKER")
    st.toast("🔥 Sending OPEN Command...")

if st.sidebar.button("✅ CLOSE BREAKER (RESTORE)"):
    send_command("CLOSE_BREAKER")
    st.toast("🛡️ Sending CLOSE Command...")

# DISPLAY
placeholder = st.empty()

while True:
    data = {}
    if os.path.exists(ANCHOR_FILE):
        try:
            with open(ANCHOR_FILE, "r") as f: data = json.load(f)
        except: pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        pdu_val = 0.0
        
        if data:
            keys = list(data.keys())
            for aid, d in data.items():
                val_str = str(d.get('val', ''))
                if "V" in val_str:
                    try: pdu_val = float(val_str.replace('V', ''))
                    except: pass
                    c2.metric("⚡ PDU Voltage", val_str, f"SN: {d['sn']}")
                elif "C" in val_str:
                    c1.metric("🌡️ Temperature", val_str, f"SN: {d['sn']}")
                elif "OPEN" in val_str or "CLOSED" in val_str:
                    c3.metric("🚪 Gate Status", val_str, f"SN: {d['sn']}")
        else:
            st.info("⏳ Waiting for Data...")

        # GRAPH
        st.divider()
        st.subheader("📈 Voltage Trend")
        st.session_state.voltage_history.append(pdu_val)
        if len(st.session_state.voltage_history) > 100:
            st.session_state.voltage_history.pop(0)
        st.line_chart(st.session_state.voltage_history)

        # TABLE
        if data:
            st.caption("Live Anchors")
            df = pd.DataFrame.from_dict(data, orient='index')
            st.dataframe(df)

    time.sleep(1)