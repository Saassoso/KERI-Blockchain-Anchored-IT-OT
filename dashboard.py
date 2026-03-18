import os
import json
import time
import ctypes
from ctypes.util import find_library
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st
from dotenv import load_dotenv, find_dotenv

# --- CONFIG ---
load_dotenv(find_dotenv(usecwd=True))
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PRIVATE_KEY_HEX = os.getenv("SCADA_PRIVATE_KEY_HEX")
ANCHOR_FILE = "dashboard_data.json"

# --- LIBSODIUM LOADING ---
def load_crypto():
    lib_path = find_library('sodium') or find_library('libsodium')
    if not lib_path and os.name == 'nt':
        lib_path = 'libsodium.dll'
    
    if lib_path:
        try:
            return ctypes.cdll.LoadLibrary(lib_path)
        except Exception:
            return None
    return None

_sodium = load_crypto()

# --- APP SETUP ---
st.set_page_config(page_title="Fortress NOC", layout="wide", page_icon="🏢")
st.title("Fortress-1 Data Center NOC")
st.markdown("### Zero-Trust Infrastructure Monitoring")

# --- SESSION STATE ---
if "temp_history" not in st.session_state:
    st.session_state.temp_history = []

def send_command(cmd):
    if not _sodium:
        st.error("Libsodium not found. Cannot sign commands.")
        return False
    if not SCADA_PRIVATE_KEY_HEX:
        st.error("Private Key missing in .env")
        return False
        
    try:
        sig = ctypes.create_string_buffer(64)
        msg = cmd.encode('utf-8')
        sk = bytes.fromhex(SCADA_PRIVATE_KEY_HEX)
        
        _sodium.crypto_sign_detached(
            sig, None, msg, ctypes.c_ulonglong(len(msg)), sk
        )
        
        payload = {"cmd": cmd, "sig": sig.raw.hex(), "ts": time.time()}
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, 1883, 60)
        
        info = client.publish("substation/control/breaker", json.dumps(payload))
        info.wait_for_publish()
        
        client.disconnect()
        return True
    except: return False

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔐 Admin Controls")
st.sidebar.warning("Use only in case of physical breach or thermal runaway.")

if st.sidebar.button("🚨 INITIATE LOCKDOWN (KILL)", type="primary"):
    if send_command("OPEN_BREAKER"):
        st.toast("🔥 Shutdown Command Sent")

if st.sidebar.button("✅ RESTORE OPERATIONS"):
    if send_command("CLOSE_BREAKER"):
        st.toast("✅ Restore Command Sent")

st.sidebar.divider()
if st.sidebar.button("🔓 UNLOCK DOOR (Manual)"):
    if send_command("OPEN_DOOR"):
        st.toast("🔓 Door Unlock Command Sent")

# --- MONITORING UI ---
placeholder = st.empty()

# --- AUTO-REFRESH LOOP ---
while True:
    data = {}
    if os.path.exists(ANCHOR_FILE):
        try:
            with open(ANCHOR_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        current_temp = 0.0 
        
        if data:
            for aid, d in data.items():
                val_str = str(d.get('val', ''))
                
                if "CPU" in val_str:
                    try:
                        parts = val_str.split('|')
                        cpu = parts[0].split(':')[1]
                        temp = parts[1].split(':')[1].replace('C','')
                        current_temp = float(temp)
                        
                        temp_delta = f"SN: {d['sn']}"
                        if current_temp > 80: temp_delta = "CRITICAL"
                        
                        c1.metric("🖥️ RACK-99 CORE", f"{cpu} Load", temp_delta)
                        c1.metric("🌡️ Core Temp", f"{temp}°C")
                    except Exception: pass
                    
                elif "FAN" in val_str:
                    try:
                        fan = val_str.split('|')[0].split(':')[1]
                        c2.metric("❄️ HVAC Status", fan, f"SN: {d['sn']}")
                    except Exception: pass
                    
                elif "LOCKED" in val_str or "UNLOCKED" in val_str:
                    try:
                        state = val_str.split('|')[0]
                        c3.metric("🚪 Physical Access", state, f"SN: {d['sn']}")
                    except Exception: pass
        else:
            st.info("⏳ Waiting for data from KERI Gateway...")

        # --- THE GRAPH ---
        st.divider()
        st.subheader("Server Thermal Telemetry")
        
        st.session_state.temp_history.append(current_temp)
        if len(st.session_state.temp_history) > 100:
            st.session_state.temp_history.pop(0)
            
        chart_color = "#ff0000" if current_temp > 80 else "#0000ff"
        df_temp = pd.DataFrame(st.session_state.temp_history, columns=["Temperature"])
        st.line_chart(df_temp, color=chart_color)

        # --- AUDIT TABLE ---
        if data: 
            st.caption("Immutable Blockchain Log (Local Cache)")
            st.dataframe(pd.DataFrame.from_dict(data, orient='index'), use_container_width=True)
            
    time.sleep(1)