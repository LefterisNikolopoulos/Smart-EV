#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# build_deploy.py - Generates a self-contained deploy.sh installer
# Reads local project files, encodes them as base64, and inserts them into deploy.sh
# ==============================================================================

import os
import sys
import json
import base64

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

RFID_PY_PATH = os.path.join(WORKSPACE_DIR, "rfid1.py")
if not os.path.exists(RFID_PY_PATH):
    RFID_PY_PATH = os.path.join(WORKSPACE_DIR, "rfid.py")

POLLER_PY_PATH = os.path.join(WORKSPACE_DIR, "chargers_poller.py")
FORECAST_PY_PATH = os.path.join(WORKSPACE_DIR, "solar_forecast.py")
FLOWS_JSON_PATH = os.path.join(WORKSPACE_DIR, "flows.json")
CONFIG_JSON_PATH = os.path.join(WORKSPACE_DIR, "smart-parking-config.json")
CARS_JSON_PATH = os.path.join(WORKSPACE_DIR, "cars-config.json")
FORECAST_JSON_PATH = os.path.join(WORKSPACE_DIR, "solar-forecast.json")
HTML_PATH = os.path.join(WORKSPACE_DIR, "smart parking.html")
DEPLOY_SH_PATH = os.path.join(WORKSPACE_DIR, "deploy.sh")

def sync_html_to_flows():
    if os.path.exists(HTML_PATH) and os.path.exists(FLOWS_JSON_PATH):
        try:
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                html_code = f.read()
            with open(FLOWS_JSON_PATH, "r", encoding="utf-8") as f:
                flows_data = json.load(f)
            updated = False
            for node in flows_data:
                if node.get("id") == "62e55f923ff54c1e":
                    if node.get("format") != html_code:
                        node["format"] = html_code
                        updated = True
                    break
            if updated:
                with open(FLOWS_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(flows_data, f, indent=4, ensure_ascii=False)
                print("Updated flows.json with latest 'smart parking.html'")
            else:
                print("flows.json is already in sync with 'smart parking.html'")
        except Exception as e:
            print(f"Warning syncing HTML to flows.json: {e}")

sync_html_to_flows()

def get_base64_content(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Required file not found: {filepath}", file=sys.stderr)
        return ""
    with open(filepath, "rb") as f:
        data = f.read()
        print(f"  Encoded {os.path.basename(filepath)}: {len(data):,} bytes")
        return base64.b64encode(data).decode("utf-8")

print("\nEncoding project assets to Base64...")
rfid_b64 = get_base64_content(RFID_PY_PATH)
poller_b64 = get_base64_content(POLLER_PY_PATH)
forecast_py_b64 = get_base64_content(FORECAST_PY_PATH)
nodered_b64 = get_base64_content(FLOWS_JSON_PATH)
config_b64 = get_base64_content(CONFIG_JSON_PATH)
cars_b64 = get_base64_content(CARS_JSON_PATH)
forecast_json_b64 = get_base64_content(FORECAST_JSON_PATH)

deploy_template = r"""#!/bin/bash
# ==============================================================================
# Smart EV Charging System - Standalone Self-Contained Auto-Deployer
# Supports: Node-RED, Mosquitto, Pymodbus, Dashboard, Security, Local Storage,
# Network Bridge (NAT), Multi-charger control (Victron, Easee, Go-e, SolaX).
# ==============================================================================

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[31mError: Please run this script with sudo (e.g., sudo ./deploy.sh)\e[0m"
  exit 1
fi

echo -e "\e[32m======================================================================\e[0m"
echo -e "\e[32m🚀 Starting Smart EV Standalone Self-Contained Deployment...\e[0m"
echo -e "\e[32m======================================================================\e[0m"

# Parse CLI arguments for non-interactive or unattended execution
UNATTENDED=false
CLI_USER=""
CLI_PASS=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --unattended|-y) UNATTENDED=true; shift ;;
    --user) CLI_USER="$2"; shift 2 ;;
    --password|-p) CLI_PASS="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# 1. Target Linux Username
DEFAULT_USER="$SUDO_USER"
if [ -z "$DEFAULT_USER" ] || [ "$DEFAULT_USER" = "root" ]; then
    if id "smartev" &>/dev/null; then
        DEFAULT_USER="smartev"
    elif id "pi" &>/dev/null; then
        DEFAULT_USER="pi"
    else
        DEFAULT_USER="smartev"
    fi
fi

if [ -n "$CLI_USER" ]; then
    TARGET_USER="$CLI_USER"
elif [ "$UNATTENDED" = "true" ]; then
    TARGET_USER="$DEFAULT_USER"
else
    read -p "Enter target Linux system username [$DEFAULT_USER]: " TARGET_USER
    TARGET_USER=${TARGET_USER:-$DEFAULT_USER}
fi

# Auto-create user if not found
if ! id "$TARGET_USER" &>/dev/null; then
    echo "User '$TARGET_USER' does not exist. Creating system user '$TARGET_USER'..."
    useradd -m -s /bin/bash "$TARGET_USER"
    usermod -aG sudo,dialout "$TARGET_USER" 2>/dev/null || true
    echo "$TARGET_USER:Deger" | chpasswd
    echo "Created user '$TARGET_USER' with default password 'Deger'."
else
    usermod -aG dialout "$TARGET_USER" 2>/dev/null || true
fi

USER_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
USER_HOME=${USER_HOME:-/home/$TARGET_USER}
ND_DIR="$USER_HOME/.node-red"

# 2. Node-RED Credentials
NR_ADMIN="admin"
if [ -n "$CLI_PASS" ]; then
    NR_PASS1="$CLI_PASS"
elif [ "$UNATTENDED" = "true" ]; then
    NR_PASS1="Deger"
else
    read -p "Enter desired Node-RED Admin Username [admin]: " NR_ADMIN
    NR_ADMIN=${NR_ADMIN:-admin}
    while true; do
        read -s -p "Enter Node-RED Admin Password [default: Deger]: " NR_PASS1
        echo
        NR_PASS1=${NR_PASS1:-Deger}
        read -s -p "Confirm Node-RED Admin Password: " NR_PASS2
        echo
        NR_PASS2=${NR_PASS2:-$NR_PASS1}
        if [ "$NR_PASS1" = "$NR_PASS2" ]; then
            break
        else
            echo -e "\e[31mPasswords do not match. Please try again.\e[0m"
        fi
    done
fi

# 3. Install System Packages
echo -e "\n\e[34m[1/9] Installing System Packages (Node.js, Mosquitto, Python, iptables)...\e[0m"
apt update
apt install -y curl git nodejs npm mosquitto mosquitto-clients python3 python3-pip python3-serial iptables iptables-persistent

# Install python3-pymodbus (apt or pip fallback)
apt install -y python3-pymodbus 2>/dev/null || true
if ! python3 -c "import pymodbus" &>/dev/null; then
    echo "Installing pymodbus via pip..."
    pip3 install --break-system-packages pymodbus 2>/dev/null || pip3 install pymodbus 2>/dev/null || true
fi

# 4. Install Node-RED
echo -e "\n\e[34m[2/9] Checking Node-RED installation...\e[0m"
if ! command -v node-red &>/dev/null; then
    echo "Node-RED not found. Running official installation script..."
    curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered | bash -s -- --yes --unattended --user="$TARGET_USER"
else
    echo "Node-RED is already installed."
fi

# Stop Node-RED service during configuration
systemctl stop nodered &>/dev/null || true
systemctl stop node-red &>/dev/null || true

# 5. Install Node-RED Contrib Packages & Dark Splash Screen
echo -e "\n\e[34m[3/9] Installing Node-RED contrib packages and Dark Splash screen...\e[0m"
mkdir -p "$ND_DIR"
cd "$ND_DIR"
npm install --no-audit --no-fund bcryptjs node-red-dashboard@3.6.6 node-red-contrib-modbus@5.45.2 node-red-contrib-influxdb@0.7.0

# Dark splash loader patch
cat << 'EOFSPLASH' > /tmp/loading_splash.html
<div style="position:fixed;inset:0;background:#070a13;z-index:2147483647;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,'Inter',Roboto,sans-serif;color:#f8fafc;">
    <div style="position:relative;width:64px;height:64px;margin-bottom:18px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;border:3px solid rgba(56,189,248,0.12);border-top:3px solid #00d68f;border-right:3px solid #38bdf8;border-radius:50%;animation:evSpin 0.9s cubic-bezier(0.4,0,0.2,1) infinite;"></div>
        <svg style="width:28px;height:28px;fill:#00d68f;filter:drop-shadow(0 0 8px rgba(0,214,143,0.7));" viewBox="0 0 24 24">
            <path d="M7 2v11h3v9l7-12h-4l4-8z"/>
        </svg>
    </div>
    <div style="font-size:16px;font-weight:800;letter-spacing:1.5px;color:#f8fafc;text-transform:uppercase;">SMART EV SYSTEM</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:6px;font-weight:500;">Connecting to Live Telemetry...</div>
</div>
<style>
    html, body { background-color: #070a13 !important; background: #070a13 !important; margin: 0; padding: 0; }
    @keyframes evSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
EOFSPLASH

for d in "$ND_DIR/node_modules/node-red-dashboard/dist" "/usr/lib/node_modules/node-red-dashboard/dist" "/usr/local/lib/node_modules/node-red-dashboard/dist"; do
    if [ -d "$d" ]; then
        cp /tmp/loading_splash.html "$d/loading.html"
        if [ -f "$d/index.html" ]; then
            python3 -c "
with open('$d/index.html', 'r', encoding='utf-8') as f:
    c = f.read()
if 'critical-head-dark' not in c:
    c = c.replace('<head>', '<head><style id=\"critical-head-dark\">html,body{background:#070a13!important;color:#f8fafc!important;margin:0;padding:0;}</style>')
    with open('$d/index.html', 'w', encoding='utf-8') as f:
        f.write(c)
" 2>/dev/null || true
        fi
    fi
done

# 6. Configure settings.js (Security, localfilesystem, net module)
echo -e "\n\e[34m[4/9] Configuring settings.js (Security, localfilesystem storage, net module)...\e[0m"
if [ ! -f "$ND_DIR/settings.js" ]; then
    if [ -f /usr/lib/node_modules/node-red/settings.js ]; then
        cp /usr/lib/node_modules/node-red/settings.js "$ND_DIR/settings.js"
    elif [ -f /usr/local/lib/node_modules/node-red/settings.js ]; then
        cp /usr/local/lib/node_modules/node-red/settings.js "$ND_DIR/settings.js"
    else
        timeout 5s node-red &>/dev/null || true
    fi
fi

HASH_CMD="const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync('$NR_PASS1', 8));"
NR_HASH=$(node -e "$HASH_CMD" 2>/dev/null)
if [ -z "$NR_HASH" ] || [ "$NR_HASH" = "error" ]; then
    NR_HASH=$(npx node-red-admin hash-pw "$NR_PASS1" 2>/dev/null | tail -n 1)
fi

cat << 'EOF' > update_settings.py
import sys, re

settings_path = sys.argv[1]
username = sys.argv[2]
password_hash = sys.argv[3]

with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure flowFile: 'flows.json'
content = re.sub(r"//\s*flowFile:\s*'flows\.json',", "flowFile: 'flows.json',", content)
if 'flowFile:' not in content:
    content = content.replace('module.exports = {', "module.exports = {\n    flowFile: 'flows.json',")

# credentialSecret: false
active_cred_pattern = r'credentialSecret:\s*(?:false|true|["\'].*?["\'])\s*,?'
cred_pattern = r'//\s*credentialSecret:\s*["\'].*?["\'],?'
cred_block = 'credentialSecret: false,'
if re.search(active_cred_pattern, content):
    content = re.sub(active_cred_pattern, cred_block, content, 1)
elif re.search(cred_pattern, content):
    content = re.sub(cred_pattern, cred_block, content, 1)
else:
    content = content.replace('module.exports = {', "module.exports = {\n    " + cred_block)

# adminAuth
admin_auth_block = 'adminAuth: {\n    type: "credentials",\n    users: [{\n        username: "' + username + '",\n        password: "' + password_hash + '",\n        permissions: "*"\n    }]\n},'
active_auth_pattern = r'adminAuth:\s*\{.*?\},?'
commented_auth_pattern = r'//\s*adminAuth:\s*\{.*?//\s*\},?'
if re.search(active_auth_pattern, content, re.DOTALL):
    content = re.sub(active_auth_pattern, admin_auth_block, content, 1, re.DOTALL)
elif re.search(commented_auth_pattern, content, re.DOTALL):
    content = re.sub(commented_auth_pattern, admin_auth_block, content, 1, re.DOTALL)
else:
    content = content.replace('module.exports = {', "module.exports = {\n    " + admin_auth_block)

# contextStorage: default -> localfilesystem
context_storage_block = 'contextStorage: {\n    default: {\n        module: "localfilesystem"\n    }\n},'
active_cs_pattern = r'contextStorage:\s*\{.*?default:\s*\{.*?module:\s*["\'].*?["\'].*?\},?\s*\},?'
commented_cs_pattern = r'//\s*contextStorage:\s*\{.*?//\s*default:\s*\{.*?//\s*module:\s*["\']localfilesystem["\'].*?//\s*\},?\s*//\s*\},?'
if re.search(active_cs_pattern, content, re.DOTALL):
    content = re.sub(active_cs_pattern, context_storage_block, content, 1, re.DOTALL)
elif re.search(commented_cs_pattern, content, re.DOTALL):
    content = re.sub(commented_cs_pattern, context_storage_block, content, 1, re.DOTALL)
else:
    content = content.replace('module.exports = {', "module.exports = {\n    " + context_storage_block)

# functionGlobalContext with os, fs, path, child_process, net
fgc_block = "functionGlobalContext: {\n        os: require('os'),\n        fs: require('fs'),\n        path: require('path'),\n        child_process: require('child_process'),\n        net: require('net')\n    },"
active_fgc_pattern = r'functionGlobalContext:\s*\{[^}]*\}\s*,?'
commented_fgc_pattern = r'//\s*functionGlobalContext:\s*\{.*?//\s*\}\s*,?'
if re.search(active_fgc_pattern, content, re.DOTALL):
    content = re.sub(active_fgc_pattern, fgc_block, content, 1, re.DOTALL)
elif re.search(commented_fgc_pattern, content, re.DOTALL):
    content = re.sub(commented_fgc_pattern, fgc_block, content, 1, re.DOTALL)
else:
    content = content.replace('module.exports = {', "module.exports = {\n    " + fgc_block)

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Successfully configured settings.js!')
EOF

python3 update_settings.py "$ND_DIR/settings.js" "$NR_ADMIN" "$NR_HASH"
rm -f update_settings.py

# 7. Unpack Embedded Project Files & Flows
echo -e "\n\e[34m[5/9] Deploying embedded flows, scripts, and configurations...\e[0m"

# Create directories
mkdir -p "$USER_HOME/smart-ev"
mkdir -p "$USER_HOME/Documents/DegerHellas/Smart Ev"

# 1. RFID daemon scripts
echo "{{RFID_B64}}" | base64 -d > "$USER_HOME/rfid1.py"
echo "{{RFID_B64}}" | base64 -d > "$USER_HOME/rfid.py"
echo "{{RFID_B64}}" | base64 -d > "$USER_HOME/smart-ev/rfid1.py"
echo "{{RFID_B64}}" | base64 -d > "$USER_HOME/smart-ev/rfid.py"

# 2. Chargers Poller
echo "{{POLLER_B64}}" | base64 -d > "$USER_HOME/chargers_poller.py"
echo "{{POLLER_B64}}" | base64 -d > "$USER_HOME/smart-ev/chargers_poller.py"

# 3. Solar Forecast Python
echo "{{FORECAST_PY_B64}}" | base64 -d > "$USER_HOME/solar_forecast.py"
echo "{{FORECAST_PY_B64}}" | base64 -d > "$USER_HOME/smart-ev/solar_forecast.py"
echo "{{FORECAST_PY_B64}}" | base64 -d > "$USER_HOME/Documents/DegerHellas/Smart Ev/solar_forecast.py"

chmod +x "$USER_HOME"/rfid*.py "$USER_HOME/chargers_poller.py" "$USER_HOME/solar_forecast.py" "$USER_HOME/Documents/DegerHellas/Smart Ev/solar_forecast.py" "$USER_HOME/smart-ev"/*.py 2>/dev/null || true

# 4. Smart Parking Config JSON
echo "{{CONFIG_B64}}" | base64 -d > "$ND_DIR/smart-parking-config.json"
echo "{{CONFIG_B64}}" | base64 -d > "$USER_HOME/smart-ev/smart-parking-config.json"
echo "{{CONFIG_B64}}" | base64 -d > "$USER_HOME/Documents/DegerHellas/Smart Ev/smart-parking-config.json"

# 5. Cars Config JSON
echo "{{CARS_B64}}" | base64 -d > "$ND_DIR/cars-config.json"
echo "{{CARS_B64}}" | base64 -d > "$USER_HOME/smart-ev/cars-config.json"
echo "{{CARS_B64}}" | base64 -d > "$USER_HOME/Documents/DegerHellas/Smart Ev/cars-config.json"

# 6. Solar Forecast JSON
echo "{{FORECAST_JSON_B64}}" | base64 -d > "$ND_DIR/solar-forecast.json"
echo "{{FORECAST_JSON_B64}}" | base64 -d > "$USER_HOME/solar-forecast.json"
echo "{{FORECAST_JSON_B64}}" | base64 -d > "$USER_HOME/smart-ev/solar-forecast.json"
echo "{{FORECAST_JSON_B64}}" | base64 -d > "$USER_HOME/Documents/DegerHellas/Smart Ev/solar-forecast.json"

# 7. Clean State Files (Fresh start for history and notifications)
echo "[]" > "$ND_DIR/charging-history.json"
echo "[]" > "$ND_DIR/rfid-notifications.json"
echo "{}" > "$ND_DIR/last-ui-states.json"

# 8. Node-RED Flows JSON
echo "{{NODERED_B64}}" | base64 -d > "$ND_DIR/flows.json"

# Auto-adjust any /home/XXX/ paths in flows.json to match target user
echo "Adjusting paths in flows.json to /home/$TARGET_USER/..."
sed -i -E "s|/home/[a-zA-Z0-9_.-]+/|/home/$TARGET_USER/|g" "$ND_DIR/flows.json"

# Remove any old conflicting standalone systemd units if they exist
systemctl disable --now smartev-poller smartev-forecast 2>/dev/null || true
rm -f /etc/systemd/system/smartev-poller.service /etc/systemd/system/smartev-forecast.service 2>/dev/null || true
systemctl daemon-reload 2>/dev/null || true

# 8. Mosquitto Broker Configuration
echo -e "\n\e[34m[6/9] Configuring Mosquitto MQTT Broker...\e[0m"
mkdir -p /etc/mosquitto/conf.d
cat << 'EOF' > /etc/mosquitto/conf.d/smartev.conf
listener 1883
allow_anonymous true
EOF
systemctl restart mosquitto 2>/dev/null || true

# 9. Network Bridge (eth0 192.168.0.1 <-> wlan0 NAT)
echo -e "\n\e[34m[7/9] Setting up Network Bridge (eth0 192.168.0.1 <-> wlan0 NAT)...\e[0m"

# Static IP for eth0
if command -v nmcli &>/dev/null; then
    WIRED_CON=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null | grep ethernet | head -1 | cut -d: -f1)
    if [ -n "$WIRED_CON" ]; then
        echo "Configuring '$WIRED_CON' with static IP 192.168.0.1/24 via nmcli..."
        nmcli connection modify "$WIRED_CON" ipv4.addresses 192.168.0.1/24 ipv4.routes "192.168.0.220/32" ipv4.method manual 2>/dev/null || true
        nmcli connection up "$WIRED_CON" 2>/dev/null || true
    fi
elif [ -f /etc/dhcpcd.conf ]; then
    if ! grep -q "interface eth0" /etc/dhcpcd.conf; then
        echo -e "\n# Smart Parking - Static IP for eth0\ninterface eth0\nstatic ip_address=192.168.0.1/24" >> /etc/dhcpcd.conf
    fi
fi

# Enable IP forwarding permanently
sysctl -w net.ipv4.ip_forward=1 >/dev/null
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
else
    sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
fi

# Setup iptables NAT/Masquerade rules
mkdir -p /etc/iptables
iptables -t nat -D POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || true
iptables -D FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i eth0 -o wlan0 -j ACCEPT 2>/dev/null || true

iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT

iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

# 10. Fix Permissions
echo -e "\n\e[34m[8/9] Setting permissions for user '$TARGET_USER'...\e[0m"
chown -R "$TARGET_USER:$TARGET_USER" "$USER_HOME"

# 11. Enable and start Node-RED
echo -e "\n\e[34m[9/9] Enabling and starting Node-RED service...\e[0m"
systemctl enable nodered 2>/dev/null || systemctl enable node-red 2>/dev/null || true
systemctl restart nodered 2>/dev/null || systemctl restart node-red 2>/dev/null || true

MY_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
MY_IP=${MY_IP:-localhost}

echo -e "\n\e[32m======================================================================\e[0m"
echo -e "\e[32m✔ SMART EV CHARGING SYSTEM SUCCESSFULLY INSTALLED AND RUNNING!\e[0m"
echo -e "\e[32m======================================================================\e[0m"
echo -e "Dashboard UI:  \e[1;36mhttp://${MY_IP}:1880/ui\e[0m"
echo -e "Node-RED Flow: \e[1;36mhttp://${MY_IP}:1880/\e[0m"
echo -e "Admin User:    \e[1;33m$NR_ADMIN\e[0m"
echo -e "Admin Pass:    \e[1;33m$NR_PASS1\e[0m"
echo -e "Target System: User \e[1;32m$TARGET_USER\e[0m at \e[1;32m$USER_HOME\e[0m"
echo -e "Network:       eth0 (192.168.0.1/24) <-> wlan0 (NAT Masquerade)"
echo -e "\e[32m======================================================================\e[0m\n"
"""

# Replace base64 placeholders
print("\nInjecting assets into deployment script...")
deploy_template = deploy_template.replace("{{RFID_B64}}", rfid_b64)
deploy_template = deploy_template.replace("{{POLLER_B64}}", poller_b64)
deploy_template = deploy_template.replace("{{FORECAST_PY_B64}}", forecast_py_b64)
deploy_template = deploy_template.replace("{{NODERED_B64}}", nodered_b64)
deploy_template = deploy_template.replace("{{CONFIG_B64}}", config_b64)
deploy_template = deploy_template.replace("{{CARS_B64}}", cars_b64)
deploy_template = deploy_template.replace("{{FORECAST_JSON_B64}}", forecast_json_b64)

# Write deploy.sh
with open(DEPLOY_SH_PATH, "w", encoding="utf-8") as f:
    f.write(deploy_template)

os.chmod(DEPLOY_SH_PATH, 0o755)
file_size = os.path.getsize(DEPLOY_SH_PATH)
print(f"Generated standalone deploy.sh successfully: {file_size:,} bytes")
print("Finished!\n")
