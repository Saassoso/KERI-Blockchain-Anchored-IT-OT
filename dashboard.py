import streamlit as st
import json
import time
import os
import paho.mqtt.client as mqtt
from scripts.utils import load_libsodium

<<<<<<< Updated upstream
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
=======
# --- CONFIG ---
load_dotenv(find_dotenv(usecwd=True))
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
SCADA_PRIVATE_KEY_HEX = os.getenv("SCADA_PRIVATE_KEY_HEX")
ANCHOR_FILE = "dashboard_data.json"

# --- LIBSODIUM ---
def load_crypto():
    lib = ctypes.util.find_library('sodium') or ctypes.util.find_library('libsodium')
    if not lib: lib = ctypes.util.find_library('libsodium.dll')
    return ctypes.cdll.LoadLibrary(lib) if lib else None
_sodium = load_crypto()

st.set_page_config(page_title="Fortress NOC", layout="wide", page_icon="🏢")
st.title("🏢 Fortress-1 Data Center NOC")

# --- SESSION STATE (FOR GRAPH) ---
if "temp_history" not in st.session_state:
    st.session_state.temp_history = []

# --- COMMANDS ---
def send_command(cmd):
    if not _sodium: return
    try:
        sig = ctypes.create_string_buffer(64)
        _sodium.crypto_sign_detached(sig, None, cmd.encode('utf-8'), ctypes.c_ulonglong(len(cmd)), bytes.fromhex(SCADA_PRIVATE_KEY_HEX))
        payload = {"cmd": cmd, "sig": sig.raw.hex(), "ts": time.time()}
        
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, 1883, 60)
        
        # FIX: Wait for publish confirmation
        info = client.publish("substation/control/breaker", json.dumps(payload))
        info.wait_for_publish()
        
        client.disconnect()
        return True
    except Exception as e:
        st.error(f"Command Error: {e}")
        return False

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔐 Admin Controls")
if st.sidebar.button("🚨 EMERGENCY SHUTDOWN", type="primary"):
    send_command("OPEN_BREAKER")
    st.toast("🔥 Shutdown Command Sent")

if st.sidebar.button("✅ RESTORE OPERATIONS"):
    send_command("CLOSE_BREAKER")
    st.toast("✅ Restore Command Sent")

st.sidebar.divider()
if st.sidebar.button("🔓 UNLOCK DOOR (Manual)"):
    send_command("OPEN_DOOR")
    st.toast("🔓 Door Unlock Command Sent")

# --- MONITORING LOOP ---
placeholder = st.empty()
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
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
=======
    data = {}
    try:
        with open(ANCHOR_FILE, "r") as f: data = json.load(f)
    except: pass
    
    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        current_temp = 0.0 # Default if no data
        
        if data:
            for aid, d in data.items():
                val = str(d.get('val', ''))
                
                # PARSE SERVER DATA (CPU & TEMP)
                if "CPU" in val: 
                    # Format: "CPU:45%|Temp:50.5C"
                    try:
                        parts = val.split('|')
                        cpu_txt = parts[0]
                        temp_txt = parts[1]
                        
                        # Extract float for graph
                        current_temp = float(temp_txt.replace('Temp:', '').replace('C', ''))
                        
                        c1.metric("🖥️ Server Core", cpu_txt, temp_txt)
                    except: pass
                    
                # PARSE HVAC DATA
                elif "FAN" in val: 
                    c2.metric("❄️ HVAC Status", val.split('|')[0], f"SN: {d['sn']}")
                    
                # PARSE DOOR DATA
                elif "LOCKED" in val or "UNLOCKED" in val: 
                    c3.metric("🚪 Physical Access", val.split('|')[0], val.split('|')[1])
        else:
            st.info("Waiting for Data...")
        
        # --- THE GRAPH (RESTORED) ---
        st.divider()
        st.subheader("🔥 Live Server Temperature")
        
        # Append data
        st.session_state.temp_history.append(current_temp)
        
        # Keep graph moving (last 100 ticks)
        if len(st.session_state.temp_history) > 100:
            st.session_state.temp_history.pop(0)
            
        # Dynamic Color: Red if hot, Blue if cool
        chart_color = "#ff0000" if current_temp > 80 else "#0000ff"
        st.line_chart(st.session_state.temp_history, color=chart_color)

        # --- AUDIT TABLE ---
        if data: 
            st.caption("Immutable Blockchain Log")
            st.dataframe(pd.DataFrame.from_dict(data, orient='index'))
            
    time.sleep(1)
>>>>>>> Stashed changes
