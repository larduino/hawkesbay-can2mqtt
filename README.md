# HawkesBay CAN → MQTT Bridge

CAN → MQTT bridge for Midnite Solar Hawkes Bay, Barcelona, and potentially Rosie charge controllers.

---

## 📡 Overview
This project reads raw CANBus frames from Midnite Solar charge controllers and publishes decoded metrics to MQTT. It allows you to view full system telemetry in:

- Home Assistant  
- Node-RED  
- MQTT Explorer  
- Any MQTT-compatible system  

This project uses:

- InnoMaker USB2CAN (preferred, automatically detected as `can0`)  
- SocketCAN on Linux / Raspberry Pi  
- Python script (`can2mqtt_hbay.py`) to decode CAN frames  

Supported controllers:

- ✔ Hawkes Bay  
- ✔ Barcelona *(commented-out code, can be enabled for Barcelona users)*  
- ⚠ Rosie *(experimental — needs frame captures)*

---

## 🚀 Features

- Reads CANBus frames via SocketCAN (`can0`)  
- Decodes:  
  - Battery voltage, current, power  
  - State of charge / charge stage  
  - Temperatures  
  - PV MPPT voltage & current  
  - Whizbang Jr current  
  - Daily kWh production  
- Throttled MQTT publishing to reduce traffic  
- Clean MQTT topic structure  
- Optional Home Assistant discovery  
- Optional systemd service  

---

## 🔧 Requirements

### Hardware
- Raspberry Pi  
- InnoMaker USB2CAN (preferred)  
- CAN-H & CAN-L wired to charge controller (pin 4 = CAN High, pin 5 = CAN Low)


### Software
- Linux with SocketCAN  
- Python 3.8+  
- MQTT broker (Mosquitto recommended)

---

## 📦 Install Required Packages

### Install CAN utilities
```
sudo apt install can-utils

Python dependencies

pip3 install paho-mqtt python-can

📥 Installation
1. Clone the repository

git clone https://github.com/<your-username>/hawkesbay-canbus-mqtt.git
cd hawkesbay-canbus-mqtt

🔌 Enable SocketCAN
Innomaker USB2CAN (preferred)

sudo ip link set can0 down
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

### If using CANable (candleLight)
```bash
sudo ip link set can0 up type can bitrate 250000
```
### If using Innomaker 
'''
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
'''

Optional: Monitor CAN live


candump can0

Verify interface

ifconfig can0

▶️ Running the Script
Run directly

python3 can2mqtt_hbay.py

Optional: fix ownership

sudo chown pi:pi can2mqtt_hbay.py

Optional: make executable

chmod +x can2mqtt_hbay.py

🛠 systemd Service (optional)
Install service

sudo cp can2mqtt_hbay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now can2mqtt_hbay.service

View logs

sudo journalctl -fu can2mqtt_hbay.service

📡 Example MQTT Topics

hawkesbay/battery/voltage
hawkesbay/battery/current
hawkesbay/battery/power
hawkesbay/battery/charge_stage
hawkesbay/pv/voltage_mppt2
hawkesbay/pv/current_mppt2
hawkesbay/daily/kwh_today
hawkesbay/whizbang/amps
hawkesbay/whizbang/status
hawkesbay/whizbang/mode
hawkesbay/state

Optional Barcelona topics (commented-out in code)

hawkesbay/pv/voltage_mppt0
hawkesbay/pv/current_mppt0

🏠 Home Assistant Example

sensor:
  - platform: mqtt
    name: "HB Battery Voltage"
    state_topic: "hawkesbay/battery/voltage"
    unit_of_measurement: "V"

  - platform: mqtt
    name: "HB PV Watts"
    state_topic: "hawkesbay/pv/watts"
    unit_of_measurement: "W"

🔌 Wiring Diagram

Charge Controller      Raspberry Pi / USB2CAN
-------------          -------------------
Pin 4 CAN High   -->   CAN-H
Pin 5 CAN Low    -->   CAN-L
GND              -->   GND
5V / 3.3V        -->   USB power for USB2CAN (if needed)

📝 Notes

    Barcelona MPPT #1 section is left commented for future users.

    Rosie decoding is experimental.

    PRs welcome for new CAN frame IDs, controller support, or documentation improvements.

🤝 Contributing

PRs welcome — especially:

    New CAN frame IDs

    Expanded controller support

    Documentation improvements

📜 License

MIT License
📬 Contact

Open a GitHub Issue for questions, improvements, or contributions.
