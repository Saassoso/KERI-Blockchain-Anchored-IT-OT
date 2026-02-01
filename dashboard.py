import ctypes
import json
import os
<<<<<<< Updated upstream
import pandas as pd
import paho.mqtt.client as mqtt
import ctypes
from ctypes.util import find_library
from dotenv import load_dotenv, find_dotenv

# CONFIG
=======
import time
from ctypes.util import find_library

import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st
from dotenv import find_dotenv, load_dotenv

# --- CONFIG ---
>>>>>>> Stashed changes
load_dotenv(find_dotenv(usecwd=True))
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PRIVATE_KEY_HEX = os.getenv("SCADA_PRIVATE_KEY_HEX")
ANCHOR_FILE = "dashboard_data.json"

<<<<<<< Updated upstream
# LIBSODIUM
=======
# --- LIBSODIUM LOADING ---
>>>>>>> Stashed changes
def load_crypto():
    # Search for libsodium across different OS platforms
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

<<<<<<< Updated upstream
# STATE
=======
# --- SESSION STATE ---
>>>>>>> Stashed changes
if "temp_history" not in st.session_state:
    st.session_state.temp_history = []

# COMMANDS
def send_command(cmd):
<<<<<<< Updated upstream
    if not SCADA_PRIVATE_KEY_HEX or not _sodium: return False
    try:
        sig = ctypes.create_string_buffer(64)
        msg_bytes = cmd.encode('utf-8')
        _sodium.crypto_sign_detached(sig, None, msg_bytes, ctypes.c_ulonglong(len(msg_bytes)), bytes.fromhex(SCADA_PRIVATE_KEY_HEX))
=======
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
        
        # Ed25519 Detached Signature
        _sodium.crypto_sign_detached(
            sig, None, msg, ctypes.c_ulonglong(len(msg)), sk
        )
        
>>>>>>> Stashed changes
        payload = {"cmd": cmd, "sig": sig.raw.hex(), "ts": time.time()}
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, 1883, 60)
<<<<<<< Updated upstream
        client.publish("substation/control/breaker", json.dumps(payload))
=======
        
        info = client.publish("substation/control/breaker", json.dumps(payload))
        info.wait_for_publish()
        
>>>>>>> Stashed changes
        client.disconnect()
        return True
    except: return False

<<<<<<< Updated upstream
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

=======
# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔐 Admin Controls")
if st.sidebar.button("🚨 EMERGENCY SHUTDOWN", type="primary"):
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
>>>>>>> Stashed changes
while True:
    data = {}
    if os.path.exists(ANCHOR_FILE):
        try:
<<<<<<< Updated upstream
            with open(ANCHOR_FILE, "r") as f: data = json.load(f)
        except: pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        current_temp = 0.0
=======
            with open(ANCHOR_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        current_temp = 0.0 
>>>>>>> Stashed changes
        
        if data:
            for aid, d in data.items():
                val_str = str(d.get('val', ''))
                
<<<<<<< Updated upstream
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
=======
                # PARSE SERVER DATA
                if "CPU" in val: 
                    try:
                        parts = val.split('|')
                        cpu_txt = parts[0]
                        temp_txt = parts[1]
                        # Extract numeric temperature
                        temp_val = "".join(filter(lambda x: x.isdigit() or x == '.', temp_txt))
                        current_temp = float(temp_val) if temp_val else 0.0
                        c1.metric("🖥️ Server Core", cpu_txt, temp_txt)
                    except Exception:
                        pass
                    
                # PARSE HVAC DATA
                elif "FAN" in val: 
                    c2.metric("❄️ HVAC Status", val.split('|')[0], f"SN: {d.get('sn', 'N/A')}")
                    
                # PARSE DOOR DATA
                elif any(word in val for word in ["LOCKED", "UNLOCKED"]): 
                    status = val.split('|')[0]
                    log_info = val.split('|')[1] if '|' in val else ""
                    c3.metric("🚪 Physical Access", status, log_info)
        else:
            st.info("Waiting for data from KERI Gateway...")
        
        # --- THE GRAPH ---
>>>>>>> Stashed changes
        st.divider()
        st.subheader("Server Thermal Telemetry")
        
<<<<<<< Updated upstream
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

=======
        # Update history
        st.session_state.temp_history.append(current_temp)
        if len(st.session_state.temp_history) > 100:
            st.session_state.temp_history.pop(0)
            
        chart_color = "#ff0000" if current_temp > 80 else "#0000ff"
        # We use a dataframe to ensure line chart displays correctly
        df_temp = pd.DataFrame(st.session_state.temp_history, columns=["Temperature"])
        st.line_chart(df_temp, color=chart_color)

        # --- AUDIT TABLE ---
        if data: 
            st.caption("Immutable Blockchain Log (Local Cache)")
            st.dataframe(pd.DataFrame.from_dict(data, orient='index'), use_container_width=True)
            
>>>>>>> Stashed changes
    time.sleep(1)