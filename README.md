
## 📡 Overview
This project reads raw CANBus frames from Midnite Solar charge controllers and publishes decoded metrics to MQTT for Home Assistant, Node-RED, and other consumers.

Uses:
- CANable / CANable Pro (candleLight firmware)
- SocketCAN on Linux / Raspberry Pi
- Python script (`can2mqtt_hbay.py`) to decode CAN frames

Supported controllers:
- Hawkes Bay
- Barcelona
- Rosie *(experimental)*

---

## 🚀 Features
- Reads CANBus frames from `can0`
- Decodes:
  - Battery voltage, current, power
  - State of charge
  - Temperatures
  - PV MPPT voltage & current
  - Whizbang Jr current
  - Daily kWh  
- Throttled MQTT publishing
- Clean MQTT topic structure
- Optional Home Assistant Discovery
- Optional systemd service

---

## 🔧 Requirements

### Hardware
- Raspberry Pi
- started with CANable / CANable Pro (candleLight firmware)
- but now using Innomaker USB2CAN ( shows up as Can0 without a lot of setup) 
- CAN-H & CAN-L wired to charge controller pin 4 Can High pin 5 Can Low

### Software
- Linux with SocketCAN
- Python 3.8+
- MQTT broker (Mosquitto recommended)

---

## 📦 Install Required Packages

### Install CAN utilities
```bash
sudo apt install can-utils
```

### Python dependencies
```bash
pip3 install paho-mqtt python-can
```

---

## 📥 Installation

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/hawkesbay-canbus-mqtt.git
cd hawkesbay-canbus-mqtt
```

---

## 🔌 Enable SocketCAN

### If using CANable (candleLight)
```bash
sudo ip link set can0 up type can bitrate 250000
```

Verify:
```bash
ifconfig can0
```

Monitor live CAN:
```bash
candump can0
```

---

## ▶️ Running the Script

### Run directly
```bash
python3 can2mqtt_hbay.py
```

### Optional: fix ownership
```bash
sudo chown pi:pi can2mqtt_hbay.py
```

### Optional: make executable
```bash
chmod +x can2mqtt_hbay.py
```

---

## 🛠 systemd Service (optional)

### Install service
```bash
sudo cp can2mqtt_hbay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now can2mqtt_hbay.service
```

### View logs
```bash
sudo journalctl -fu can2mqtt_hbay.service
```

---

## 📡 Example MQTT Topics
```
hawkesbay/battery/voltage
hawkesbay/battery/current
hawkesbay/battery/power
hawkesbay/pv/voltage_mppt2
hawkesbay/pv/current_mppt2
hawkesbay/daily/kwh_today
hawkesbay/whizbang/amps
hawkesbay/state
```

---

## 🏠 Home Assistant Example

```yaml
sensor:
  - platform: mqtt
    name: "HB Battery Voltage"
    state_topic: "hawkesbay/battery/voltage"
    unit_of_measurement: "V"

  - platform: mqtt
    name: "HB PV Watts"
    state_topic: "hawkesbay/pv/watts"
    unit_of_measurement: "W"
```

---

## 📝 Notes
- Barcelona and Rosie decoding may require refining.
- PRs welcome for new CAN frame IDs or captured logs.

---

## 🤝 Contributing
PRs welcome — especially:
- New CAN frame IDs
- Expanded controller support
- Documentation improvements

---

## 📜 License
MIT License

---

## 📬 Contact
Open a GitHub Issue for questions, improvements, or contributions.
=======
hawkesbay-canbus-mqtt

CAN → MQTT bridge for Midnite Solar Hawkes Bay, Barcelona, and potentially Rosie charge controllers.

📡 Overview

This project reads raw CANBus frames from Midnite Solar charge controllers and publishes decoded metrics to MQTT. It allows you to view full system telemetry in:

Home Assistant

Node-RED

MQTT Explorer

Any MQTT-compatible system

This project uses:

A CANable / CANable Pro flashed with candleLight firmware

SocketCAN on Raspberry Pi / Linux

A Python script (can2mqtt_hbay.py) that decodes CAN frames and publishes MQTT topics

Supported controllers:

✔ Hawkes Bay

✔ Barcelona

⚠ Rosie (experimental — needs frame captures)

🚀 Features

Reads CANBus frames via SocketCAN (can0)

Decodes:

Battery voltage, current, power

State of charge

Temperatures

PV (MPPT) voltage & current

Whizbang Jr current readings

Daily kWh production

Throttled publishing to reduce MQTT noise

Clean MQTT topic structure:

