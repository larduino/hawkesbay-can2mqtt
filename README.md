Hawkes Bay CAN → MQTT Bridge
Purpose

Read raw CANBus frames from Midnite Solar devices (Hawkes Bay, Barcelona, Rosie Inverter, and Whizbang Jr), decode metrics, and publish them to MQTT.

This bridge is designed for stability, featuring a State Buffer that filters out heartbeat "zero" data to ensure clean, consistent history graphs in Home Assistant.
🚀 Key Improvements in this Version

    Flattened Structure: No more nested folders; code and Docker files are in the root for easier deployment.

    Data Ironcladding: The script maintains a state JSON object that ignores empty "heartbeat" packets, preventing data drops.

    Rosie Integration: Decodes AC Load Watts, FET Temperatures, and Transformer Temperatures.

    High-Voltage PV Fix: Properly targets register 0x81 for accurate Hawkes Bay PV voltage tracking.

    Throttled Updates: Publishes a full system state every 10 seconds to reduce MQTT overhead while keeping high-speed data available on individual topics.

🛠 Hardware Requirements

    Raspberry Pi: (Tested on Pi 3B+ and Pi 5).

    CAN Interface: Innomaker USB2CAN (preferred), CANable, or Waveshare RS485 CAN HAT.

    Connection: CAN-H and CAN-L connected to the Midnite Solar Battery/Comm bus.

📂 Repository Structure
Plaintext

```.
├── can2mqtt_hbay.py       # Main Python Bridge
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Example deployment
├── can2mqtt_hbay.service   # systemd unit file
└── examples/
    └── ha_cards/           # Lovelace YAML examples
```
⚙️ Installation
Option 1: Docker (Recommended for Pi 5 / IOTstack)

    Edit can2mqtt_hbay.py with your MQTT Broker IP.

    Build and launch:
    Bash

    docker compose build
    docker compose up -d 

Option 2: Standalone Linux Service

    Install dependencies:
    Bash

``` pip3 install paho-mqtt python-can ```

Enable the service:
Bash

    sudo cp can2mqtt_hbay.service /etc/systemd/system/
    sudo systemctl enable --now can2mqtt_hbay.service

📊 Home Assistant Integration
Stable State Monitoring

Instead of tracking dozens of individual topics, it is recommended to use the hawkesbay/state topic. It provides a synchronized JSON blob:
Metric	JSON Path	Description
Battery Power	state.battery.power	Total Watts (filtered)
Rosie Load	state.rosie.load_watts	AC Output Watts
FET Temp	state.rosie.fet_temp_f	Inverter Temperature
PV Volts	state.pv.voltage	High-Voltage DC Input
Daily kWh	state.daily.kwh_today	Solar harvest for today
Example Template Sensor
YAML

- name: "Hawkes Bay PV Voltage"
  unit_of_measurement: "V"
  state: "{{ state_attr('sensor.hbay_bridge_state', 'pv').voltage | float(0) }}"

📉 Example Dashboard

See examples/ha_cards/ for YAML snippets for:

    Gauges: Real-time House Load and Battery Voltage.

    ApexCharts: Tracking PV harvest vs. Battery Charge.

    Thermal Monitoring: Tracking Inverter FET and Transformer temps.

📝 License

MIT License - Created by @larduino
