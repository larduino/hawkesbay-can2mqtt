#!/usr/bin/env python3
"""
can2mqtt_hbay.py — Hawkes Bay CAN → MQTT bridge (InnoMaker)

Features:
 - Reads battery voltage, current, power, and charge stage
 - Reads MPPT info
 - Reads Whizbang Jr current
 - Reads daily cumulative kWh (0x022)
 - Publishes MQTT topics and full JSON state
 - Throttled publishing for battery, MPPT, Whizbang, and JSON output
 - Waits for can0 automatically
"""

import os
import time
import can
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# ----------------------------
# Configuration from environment
# ----------------------------
MQTT_BROKER = os.getenv("CAN2MQTT_MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("CAN2MQTT_MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("CAN2MQTT_MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("CAN2MQTT_MQTT_PASSWORD", None)
MQTT_PREFIX = os.getenv("CAN2MQTT_MQTT_PREFIX", "hawkesbay")
DISCOVERY_PREFIX = os.getenv("CAN2MQTT_DISCOVERY_PREFIX", "homeassistant")
CAN_INTERFACE = os.getenv("CAN2MQTT_CAN_INTERFACE", "can0")


# Throttle intervals (seconds)
BATTERY_INTERVAL = 1.0
MPPT_INTERVAL = 1.0
WHIZBANG_INTERVAL = 2.0
STATE_INTERVAL = 5.0

# ----------------------------
# MQTT setup
# ----------------------------
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ----------------------------
# Wait for can0
# ----------------------------
print("⏳ Waiting for can0 interface...")
while not os.path.exists(f"/sys/class/net/{CAN_INTERFACE}"):
    time.sleep(1)
print(f"✅ {CAN_INTERFACE} detected, starting CAN bus...")

# ----------------------------
# CAN bus setup
# ----------------------------
bus = can.interface.Bus(channel=CAN_INTERFACE, interface="socketcan")
print("📡 Hawkes Bay CAN → MQTT Bridge running via InnoMaker USB2CAN...")

# ----------------------------
# Helper: Publish MQTT
# ----------------------------
def pub(topic, value, retain=True):
    full = f"{MQTT_PREFIX}/{topic}"
    payload = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    client.publish(full, payload, retain=retain)

# ----------------------------
# Helper: Home Assistant discovery
# ----------------------------
def ha_discovery(sensor_id, name, unit, topic, device_class=None, state_class=None):
    cfg_topic = f"{DISCOVERY_PREFIX}/sensor/midnite_hawkes_bay_{sensor_id}/config"
    payload = {
        "name": name,
        "uniq_id": f"midnite_hawkes_bay_{sensor_id}",
        "state_topic": f"{MQTT_PREFIX}/{topic}",
        "unit_of_measurement": unit,
        "device": {
            "identifiers": ["midnite_hawkes_bay"],
            "name": "Midnite Hawkes Bay",
            "model": "Hawke's Bay",
            "manufacturer": "Midnite Solar"
        }
    }
    if device_class:
        payload["device_class"] = device_class
    if state_class:
        payload["state_class"] = state_class
    client.publish(cfg_topic, json.dumps(payload), retain=True)

# ----------------------------
# Publish HA discovery
# ----------------------------
def publish_all_discovery():
    ha_discovery("battery_voltage", "Battery Voltage", "V", "battery/voltage", "voltage", "measurement")
    ha_discovery("battery_current", "Battery Current", "A", "battery/current", "current", "measurement")
    ha_discovery("battery_power", "Battery Power", "W", "battery/power", "power", "measurement")
    ha_discovery("battery_charge_stage", "Battery Charge Stage", "", "battery/charge_stage")
    ha_discovery("pv_voltage_mppt2", "PV Voltage MPPT2", "V", "pv/voltage_mppt2", "voltage", "measurement")
    ha_discovery("pv_current_mppt2", "PV Current MPPT2", "A", "pv/current_mppt2", "current", "measurement")
    # Optional Barcelona MPPT #1 discovery (commented out)
    # ha_discovery("pv_voltage_mppt0", "PV Voltage MPPT0", "V", "pv/voltage_mppt0", "voltage", "measurement")
    # ha_discovery("pv_current_mppt0", "PV Current MPPT0", "A", "pv/current_mppt0", "current", "measurement")
    ha_discovery("whizbang_jr_amps", "Whizbang Jr Amps", "A", "whizbang/amps", "current", "measurement")
    ha_discovery("daily_kwh_today", "Daily KWh Today", "kWh", "daily/kwh_today", "energy", "total")
    ha_discovery("state_json", "Full HB JSON", "", "state", None, None)

publish_all_discovery()

# ----------------------------
# Main state object
# ----------------------------
state = {"battery": {}, "pv": {}, "whizbang": {}, "daily": {}, "mppt": {}}

# ----------------------------
# Throttle timers
# ----------------------------
last_battery = last_mppt = last_whizbang = last_state = 0

# ----------------------------
# Battery Charge Stage mapping
# ----------------------------
CHARGE_STAGE = {
    0: "Resting",
    1: "Bulk MPPT",
    2: "Absorb",
    3: "Float",
    4: "Equalize",
    5: "Float MPPT",
    6: "EQ MPPT"
}

# ----------------------------
# Main loop
# ----------------------------
try:
    while True:
        msg = bus.recv()
        if not msg:
            time.sleep(0.01)
            continue

        now = time.time()
        canid = msg.arbitration_id
        data = list(msg.data)
        register = (canid >> 18) & 0x7FF

        # ----------------------------
        # Battery V/A/P (0x0A0)
        # ----------------------------
        if register == 0x0A0 and len(data) >= 4:
            voltage = (data[0] << 8 | data[1]) / 10.0
            current = (data[2] << 8 | data[3]) / 10.0
            power = voltage * current
            state["battery"].update({"voltage": voltage, "current": current, "power": power})
            if now - last_battery >= BATTERY_INTERVAL:
                pub("battery/voltage", voltage)
                pub("battery/current", current)
                pub("battery/power", power)
                last_battery = now

        # ----------------------------
        # Battery Charge Stage (0x0A3)
        # ----------------------------
        elif register == 0x0A3 and len(data) >= 1:
            stage = data[0] & 0x0F
            stage_str = CHARGE_STAGE.get(stage, f"Unknown({stage})")
            state["battery"]["charge_stage"] = stage_str
            pub("battery/charge_stage", stage_str)

        # ----------------------------
        # MPPT #2 voltage/current (0x081)
        # ----------------------------
        elif register == 0x081 and len(data) >= 4:
            mppt_v = (data[0] << 8 | data[1]) / 10.0
            mppt_i = (data[2] << 8 | data[3]) / 10.0
            state["pv"].update({"mppt2_voltage": mppt_v, "mppt2_current": mppt_i})
            if now - last_mppt >= MPPT_INTERVAL:
                pub("pv/voltage_mppt2", mppt_v)
                pub("pv/current_mppt2", mppt_i)
                last_mppt = now

        # ----------------------------
        # Optional MPPT #1 for Barcelona (0x080)
        # ----------------------------
        # elif register == 0x080 and len(data) >= 4:
        #     mppt0_v = (data[0] << 8 | data[1]) / 10.0
        #     mppt0_i = (data[2] << 8 | data[3]) / 10.0
        #     state["pv"].update({"mppt0_voltage": mppt0_v, "mppt0_current": mppt0_i})
        #     pub("pv/voltage_mppt0", mppt0_v)
        #     pub("pv/current_mppt0", mppt0_i)

        # ----------------------------
        # Whizbang Jr (0x2A3)
        # ----------------------------
        elif register == 0x2A3 and len(data) >= 4:
            raw = (data[2] << 8 | data[3])
            if raw & 0x8000:
                raw -= 0x10000
            amps = raw / 10.0
            status = data[0]
            mode = data[1]
            state["whizbang"].update({"amps": amps, "status": status, "mode": mode})
            if now - last_whizbang >= WHIZBANG_INTERVAL:
                pub("whizbang/amps", amps)
                pub("whizbang/status", status)
                pub("whizbang/mode", mode)
                last_whizbang = now

        # ----------------------------
        # Daily kWh (0x022)
        # ----------------------------
        elif register == 0x022 and len(data) >= 4:
            raw = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
            kwh = raw / 100.0
            state["daily"]["today"] = kwh
            pub("daily/kwh_today", round(kwh, 3))

        # ----------------------------
        # Publish full JSON state
        # ----------------------------
        if now - last_state >= STATE_INTERVAL:
            state["timestamp"] = datetime.utcnow().isoformat() + "Z"
            pub("state", state)
            last_state = now

        client.loop(0.01)

except KeyboardInterrupt:
    print("Stopped by user")

except Exception as e:
    print("Unhandled exception:", e)
    raise
