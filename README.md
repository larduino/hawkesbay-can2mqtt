Hawkes Bay CAN → MQTT Bridge

Reads CANBus data from Midnite Solar charge controllers and publishes to MQTT for Home Assistant, Node-RED, or any MQTT consumer.

Table of Contents

Pi3 Standalone Setup

Pi5 IOTstack Dockerized Setup

MQTT Topics

License

Pi3 Standalone Setup

This is the original setup running directly on a Raspberry Pi 3B+.

Hardware

Raspberry Pi 3B+

Innomaker USB2CAN or CANable/CANable Pro

CAN-H & CAN-L connected to charge controller

Software

Linux with SocketCAN

Python 3.8+

MQTT broker (Mosquitto recommended)

Installation

Clone the repo:

git clone https://github.com/larduino/hawkesbay-can2mqtt.git
cd hawkesbay-can2mqtt/pi3_standalone


Install Python dependencies:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Copy the systemd service for CAN interface:

sudo cp systemd/can0.service /etc/systemd/system/can0.service
sudo systemctl daemon-reload
sudo systemctl enable can0.service
sudo systemctl start can0.service


Run the bridge:

python3 can2mqtt_hbay.py


Optionally, set up your own systemd service for the Python script to start on boot.

Pi5 IOTstack Dockerized Setup

This version runs in a Docker container within IOTstack on a Raspberry Pi 5.

Directory structure
pi5_iotstack/
├─ services/can2mqtt_hawkesbay/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ can2mqtt_hbay.py
├─ docker-compose.yml
└─ systemd/
    └─ can0.service

Prerequisites

Raspberry Pi 5 with IOTstack installed

Mosquitto container running in IOTstack

Innomaker USB2CAN plugged in

CAN Systemd Service

Copy the service file to bring up CAN0 automatically:

sudo cp systemd/can0.service /etc/systemd/system/can0.service
sudo systemctl daemon-reload
sudo systemctl enable can0.service
sudo systemctl start can0.service


can0.service contents (production-ready):

[Unit]
Description=Bring up CAN0 interface for USB2CAN
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c "sleep 5; /sbin/ip link set can0 down || true; /sbin/ip link set can0 up type can bitrate 500000"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target


Waits 5 seconds for USB2CAN enumeration

Resets CAN0 if it was already up

Brings up CAN0 at 500 kbps

Docker Container

docker-compose.yml snippet:

  can2mqtt_hawkesbay:
    container_name: can2mqtt_hawkesbay
    build: ./services/can2mqtt_hawkesbay
    restart: unless-stopped
    network_mode: "host"
    environment:
      - MQTT_BROKER=127.0.0.1
      - MQTT_PORT=1883
      - MQTT_PREFIX=hawkesbay
      - CAN_INTERFACE=can0

Build & Start
cd ~/IOTstack
docker compose build can2mqtt_hawkesbay
docker compose up -d can2mqtt_hawkesbay
docker logs -f can2mqtt_hawkesbay


Logs should show CAN metrics being published to MQTT.

network_mode: host allows container access to can0 and Mosquitto.

MQTT Topics

All topics are under the prefix hawkesbay/.... Examples:

hawkesbay/battery/voltage

hawkesbay/battery/current

hawkesbay/mppt/0/voltage

hawkesbay/mppt/0/current

hawkesbay/daily_kwh

Optional Home Assistant discovery is included if configured.

License

MIT License — see LICENSE
