Hawkes Bay CAN → MQTT Bridge
Purpose

Read raw CANBus frames from Midnite Solar charge controllers (Hawkes Bay, Barcelona, experimental Rosie), decode metrics, and publish them to MQTT for Home Assistant, Node-RED, or any MQTT consumer.

Pi3 vs Pi5 Setup Comparison
Feature 	Pi3 Standalone 	Pi5 IOTstack (Docker)
Raspberry Pi Model 	3B+ 	5
Python 	Local install (3.8+) 	Docker container (python 3.11-slim)
CAN Adapter 	Innomaker USB2CAN / CANable 	Innomaker USB2CAN / CANable
CAN Interface 	SocketCAN (can0) 	SocketCAN (can0)
CAN Startup 	systemd + udev 	systemd CAN service
MQTT Broker 	Local or network Mosquitto 	IOTstack Mosquitto
Script Execution 	systemd service 	Docker container
Auto Restart 	systemd 	Docker restart policy
GitHub Branch 	main / master 	pi5_iotstack
Docker Required 	❌ 	✅
Hardware

Raspberry Pi (3B+ standalone or 5 with IOTstack)

Innomaker USB2CAN (preferred) or CANable / CANable Pro

CAN-H and CAN-L connected to Midnite Solar charge controller

Software

Linux with SocketCAN

Python 3.8+ (Pi3) or Docker (Pi5)

MQTT broker (Mosquitto recommended)

GitHub Branches

main / master – Pi3 standalone installation (no Docker), now contains all Pi5 updates.

pi5_iotstack – Deprecated; merged into main.

Pi3 Standalone Setup

Install dependencies:

sudo apt install python3 python3-pip can-utils -y
pip3 install paho-mqtt python-can


Configure MQTT settings inside can2mqtt_hbay.py.

Enable systemd service:

sudo systemctl daemon-reload
sudo systemctl enable can2mqtt_hbay.service
sudo systemctl start can2mqtt_hbay.service

Pi5 IOTstack Docker Setup

Directory Structure

pi5_iotstack/
├── services/
│   └── can2mqtt_hawkesbay/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── can2mqtt_hbay.py
├── systemd/
│   └── can0.service
└── docker-compose.yml


MQTT Configuration (inside can2mqtt_hbay.py)

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_PREFIX = "hawkesbay"
DISCOVERY_PREFIX = "homeassistant"
CAN_INTERFACE = "can0"


Build and Run Container

cd ~/IOTstack
docker compose build can2mqtt_hawkesbay
docker compose up -d can2mqtt_hawkesbay


Verify Operation

docker ps
docker logs -f can2mqtt_hawkesbay
mosquitto_sub -h 127.0.0.1 -t "hawkesbay/#" -v


CAN Interface Startup (Recommended)

sudo systemctl daemon-reload
sudo systemctl enable can0.service
sudo systemctl start can0.service

Published Metrics

Battery voltage, current, power

Charge stage

PV MPPT voltages and currents

Whizbang Jr current and power

Daily kWh (frame 0x022)

Note: Some experimental support for Barcelona or Rosie exists but may be commented out.

Home Assistant Dashboard Example

A fully working Lovelace card for Hawkes Bay sensors is provided here:

examples/ha_cards/hawkesbay_overview_card.yaml


Includes gauges and entities for:

Battery voltage, current, power, and charge stage

PV MPPT voltages and currents

Whizbang Jr current and power

Daily energy (kWh)

Debug / raw JSON states

Notes

MQTT topics are published under hawkesbay/...

Home Assistant unique ID issue fixed in can2mqtt_hbay.py (all sensors now use unique IDs)

_2 suffix on some sensors is required if old entities exist

License

MIT License
