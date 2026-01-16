#!/usr/bin/env python3
import time, can, paho.mqtt.client as mqtt, json, os
from datetime import datetime, timezone

# --- CONFIGURATION ---
MQTT_HOST = "192.168.3.50"
MQTT_PREFIX = "hawkesbay"
CAN_INTERFACE = "can0"

# --- TRACKING & GLOBALS ---
curr_batt_v = 0.0
curr_batt_a = 0.0
resting_count = 0
last_sent_val = {}
last_pub_time = {}
last_sent_state = 0

# --- INSTANT UPDATE CONFIG & TRACKERS ---
last_pub_load_w = 0.0
last_pub_input_w = 0.0
last_published_p = 0.0
zero_p_count = 0
POWER_CHANGE_THRESHOLD = 5.0
MAX_ZERO_DROPS = 15
FORCE_UPDATE_INTERVAL = 30
last_force_time = 0

STAGES = {0: "Resting", 1: "Bulk MPPT", 2: "Absorb", 3: "Float", 4: "Equalize", 5: "Float MPPT", 6: "EQ MPPT"}

# Initialize state dictionary ONCE at the top
# Initialize state dictionary ONCE at the top
state = {
    "battery": {"voltage": 0.0, "current": 0.0, "power": 0.0, "charge_stage": "Unknown"},
    "rosie": {
        "voltage": 0.0, 
        "load_watts": 0.0, 
        "input_voltage": 0.0,  # New field
        "input_amps": 0.0,     # New field
        "input_watts": 0.0,    # New field
        "input_hz": 0.0,       # New field
        "fet_temp_f": 0.0, 
        "transformer_temp_f": 0.0, 
        "batt_temp_f": 0.0
    },
    "whizbang": {"amps": 0.0},
    "pv": {"voltage": 0.0, "current": 0.0, "watts": 0.0},
    "daily": {"kwh_today": 0.0}
}

def to_signed_16(val):
    return val - 65536 if val > 32767 else val
    
def to_signed_32(val):
     if val > 0x7FFFFFFF:
        return val - 0x100000000
     return val

def pub_throttled(topic, value, threshold=0.1, interval=5.0):
    now = time.time()
    last_v = last_sent_val.get(topic, None)
    last_t = last_pub_time.get(topic, 0)
    
    if isinstance(value, str):
        if value != last_v or (now - last_t) >= interval:
            client.publish(f"{MQTT_PREFIX}/{topic}", str(value), retain=True)
            last_sent_val[topic] = value
            last_pub_time[topic] = now
    else:
        check_val = last_v if last_v is not None else -9999.0
        if abs(value - check_val) >= threshold or (now - last_t) >= interval:
            client.publish(f"{MQTT_PREFIX}/{topic}", str(value), retain=True)
            last_sent_val[topic] = value
            last_pub_time[topic] = now

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_HOST, 1883, 60)
bus = can.interface.Bus(channel=CAN_INTERFACE, interface="socketcan")

print(f"📡 Hawkes Bay Bridge Started on {CAN_INTERFACE}...")

# (Keep your state = {...} definition at the top of the file)

try:
    while True:
        msg = bus.recv(timeout=0.1)
        now = time.time()
        
        if msg:
            canid = msg.arbitration_id
            data = list(msg.data)
            reg = (canid >> 18) & 0x7FF
            dlen = len(data)

            # --- PV INPUT (0x81) ---
            if reg == 0x81 and dlen >= 2:
                v = ((data[0] << 8) | data[1]) / 10.0
                if v > 20.0:
                    state["pv"]["voltage"] = round(v, 1)
                    pub_throttled("pv/voltage", round(v, 1), 1.0)

            # --- DAILY TOTALS (0x022) ---
            elif reg == 0x022 and dlen >= 4:
                k = (data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]) / 100.0
                if k > 0.1: # Only update if it's a real harvest number
                    state["daily"]["kwh_today"] = round(k, 2)
                    pub_throttled("daily/kwh_today", round(k, 2), 0.01)

            # --- WHIZBANG JR (0x2A3) - Keep it Raw/Sensitive ---
            elif reg == 0x2A3 and dlen >= 4:
                wb_amps = to_signed_16(data[2] << 8 | data[3]) / 10.0
                state["whizbang"]["amps"] = wb_amps
                pub_throttled("whizbang/amps", wb_amps, 0.1)

# --- BATTERY DATA (0xA0) - Filter the Heartbeats ---
            elif reg == 0xA0 and dlen >= 8:
                v_calc = ((data[0] << 8) | data[1]) / 10.0
                a_raw = to_signed_16((data[2] << 8) | data[3]) / 10.0
                p_raw = ((data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]) / 100.0
                
                current_time = time.time()
                p_to_send = p_raw
                
                # --- SMART ZERO-DROP FILTER ---
                current_stage = state["battery"]["charge_stage"]
                is_producing_stage = current_stage in ["Bulk MPPT", "Absorb", "Float", "Float MPPT"]

                if p_raw == 0 and last_published_p > 10.0 and is_producing_stage:
                    zero_p_count += 1
                    if zero_p_count <= MAX_ZERO_DROPS:
                        p_to_send = last_published_p
                        # Optional: log so you know it's working
                        # print(f"BRIDGE: Hiding 30s Sweep. Stage: {current_stage}")
                    else:
                        p_to_send = 0
                else:
                    zero_p_count = 0
                    p_to_send = p_raw
                
                # --- INSTANT DELTA LOGIC ---
                delta = abs(p_to_send - last_published_p)
                time_since_last = current_time - last_force_time

                if delta >= POWER_CHANGE_THRESHOLD or time_since_last > FORCE_UPDATE_INTERVAL:
                    # Send to MQTT immediately
                    client.publish(f"{MQTT_PREFIX}/battery/power", round(p_to_send, 1))
                    
                    # Update trackers
                    last_published_p = p_to_send
                    last_force_time = current_time

                # Still use throttled for Voltage/Current to keep them from being too noisy
                pub_throttled("battery/voltage", v_calc, 0.5)
                pub_throttled("battery/current", a_raw, 0.5)
                    
            # --- CHARGE STAGE (0xA3) ---
            elif reg == 0xA3 and dlen >= 1:
                raw_stage = data[0]
                if raw_stage == 0:
                    resting_count += 1
                else:
                    resting_count = 0
                    stage_name = STAGES.get(raw_stage, f"Unknown ({raw_stage})")
                    state["battery"]["charge_stage"] = stage_name
                    pub_throttled("battery/charge_stage", stage_name, 0)
                
                if resting_count >= 10:
                    state["battery"]["charge_stage"] = "Resting"
                    pub_throttled("battery/charge_stage", "Resting", 0)

            # --- ROSIE TEMPERATURES ---
            elif reg in [0x331, 0x261] and dlen >= 4:
                f1 = round((to_signed_16((data[0] << 8) | data[1]) / 10.0 * 1.8) + 32, 1)
                f2 = round((to_signed_16((data[2] << 8) | data[3]) / 10.0 * 1.8) + 32, 1)
                if f1 > 0: # Filter out bogus zero reads
                    state["rosie"]["fet_temp_f"] = f1
                    state["rosie"]["transformer_temp_f"] = f2
                    pub_throttled("rosie/fet_temp", f1, 1.0)
                    pub_throttled("rosie/transformer_temp", f2, 1.0)

            elif reg == 0x2A4 and dlen >= 4:
                bt_f = round((to_signed_16((data[2] << 8) | data[3]) / 10.0 * 1.8) + 32, 1)
                if bt_f > 0:
                    state["rosie"]["batt_temp_f"] = bt_f
                    pub_throttled("rosie/batt_temp", bt_f, 1.0)

# --- ROSIE AC OUTPUT (LOAD) ---
            elif reg == 0x040 and dlen >= 2:
                ac_v = to_signed_16((data[0] << 8) | data[1]) / 10.0
                state["rosie"]["voltage"] = ac_v
                pub_throttled("rosie/voltage", ac_v, 0.5)

            elif reg == 0x041 and dlen >= 4:
                raw_w = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
                ac_w = to_signed_32(raw_w) / 100.0
                state["rosie"]["load_watts"] = ac_w
                
                if abs(ac_w - last_pub_load_w) > POWER_CHANGE_THRESHOLD:
                    pub_throttled("rosie/load_watts", ac_w, 0.1)
                    last_pub_load_w = ac_w

# --- ROSIE AC INPUT (0x101) ---
            elif reg == 0x101 and dlen >= 6:
                in_v = to_signed_16((data[0] << 8) | data[1]) / 10.0
                in_a = to_signed_16((data[2] << 8) | data[3]) / 10.0
                # Using / 100.0 and rounding to 2 digits for clean Hz
                in_hz = round(to_signed_16((data[4] << 8) | data[5]) / 100.0, 2)
                
                state["rosie"]["input_voltage"] = in_v
                state["rosie"]["input_amps"] = in_a
                state["rosie"]["input_hz"] = in_hz
                
                pub_throttled("rosie/input_voltage", in_v, 1.0)
                pub_throttled("rosie/input_amps", in_a, 0.5)
                pub_throttled("rosie/input_hz", in_hz, 0.1)

            # --- ROSIE AC INPUT WATTS (0x102) ---
            elif reg == 0x102 and dlen >= 4:
                raw_in_w = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
                # Changed from / 10.0 to / 100.0 to fix the extra digit
                in_w = round(to_signed_32(raw_in_w) / 100.0, 1)
                
                state["rosie"]["input_watts"] = in_w
                
                if abs(in_w - last_pub_input_w) > POWER_CHANGE_THRESHOLD:
                    pub_throttled("rosie/input_watts", in_w, 0.1)
                    last_pub_input_w = in_w
                                                        
        # --- PERIODIC JSON STATE UPDATE ---
        if now - last_sent_state >= 10:
            state["timestamp"] = datetime.now(timezone.utc).isoformat()
            client.publish(f"{MQTT_PREFIX}/state", json.dumps(state), retain=True)
            last_sent_state = now
        
        client.loop(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    client.disconnect()
    bus.shutdown()