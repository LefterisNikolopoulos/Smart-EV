# Smart EV Backend & Smart Parking System

This repository contains the backend codebase for the **Smart EV** & Smart Parking management system:
1. **Chargers Poller & RFID Daemons** (`chargers_poller.py`, `rfid1.py`): Python scripts to interface with chargers (Victron, Easee, Go-e) via Modbus/API and handle RFID card events.
2. **Node-RED Flows** (`flows.json`): The automation orchestrator.
3. **Self-Contained Installer** (`deploy.sh`): An automated shell script to deploy Node-RED, Mosquitto MQTT, dependencies, and unpack Python scripts on target systems (e.g., Raspberry Pi).

---

## Project Structure

```
Smart-EV/
├── chargers_poller.py       # Python script to poll Victron/Easee/Go-e chargers
├── rfid1.py                 # Python RFID scanner service
├── flows.json               # Orchestration flows (Node-RED)
├── smart-parking-config.json # Parking config file (generated during deployment)
└── deploy.sh                # Self-contained installer script
```

---

## 🚀 System Deployment (`deploy.sh`)

The deployment process uses the self-contained installer `deploy.sh` which packages all Python scripts and Node-RED configurations.

### How to Run Installer on the Target Server (e.g., Raspberry Pi)

1. Transfer `deploy.sh` to the target system.
2. Make `deploy.sh` executable:
   ```bash
   chmod +x deploy.sh
   ```
3. Run the installer with `sudo`:
   ```bash
   sudo ./deploy.sh
   ```
   *The script will prompt for the target Linux username and credentials for the Node-RED UI.*

---

## 🔒 Security Notice

All sensitive Easee API credentials in flow JSON files have been replaced with placeholders:
* **Username:** `YOUR_EASEE_USERNAME`
* **Password:** `YOUR_EASEE_PASSWORD`

Ensure you update these variables inside your Node-RED dashboard nodes or flows upon deploying.
