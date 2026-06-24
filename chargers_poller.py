import json
import time
import sys
import threading
import os
import signal
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pymodbus.client import ModbusTcpClient

# Dynamic path resolution for configurations
def find_config_file():
    candidates = [
        "/home/smartev/.node-red/smart-parking-config.json",
        "/home/lefteris/.node-red/smart-parking-config.json",
        "/home/pi/.node-red/smart-parking-config.json",
        "/root/.node-red/smart-parking-config.json",
        "/data/smart-parking-config.json",
        "/home/lefteris/Documents/DegerHellas/rfid/smart-parking-config.json"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1] # fallback to workspace

CONFIG_FILE = find_config_file()

# Logging setup with Rotating File Handler (writing to RAM to protect SD card)
def setup_logging():
    log_dir = "/dev/shm"
    log_file = os.path.join(log_dir, "chargers_poller.log")
    
    handler = RotatingFileHandler(log_file, maxBytes=1*1024*1024, backupCount=1, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("chargers_poller")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logging()


previous_chargers_cfg = {}
active_threads = {}      # { cid: {"ip": ..., "type": ..., "gen": N} }
goe_states = {}          # { cid: {"last_volatile": ..., "last_eeprom": ..., "last_reported": ...} }
running = True
_gen_lock = threading.Lock()
_generation = 0          # Monotonically increasing counter

def kill_other_instances():
    current_pid = os.getpid()
    try:
        output = subprocess.check_output(["pgrep", "-f", "chargers_poller.py"]).decode('utf-8')
        pids = [int(p) for p in output.split() if p.strip().isdigit()]
        for pid in pids:
            if pid != current_pid:
                logger.info(f"Killing older instance with PID {pid}")
                os.kill(pid, signal.SIGTERM)
        time.sleep(1)
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        logger.error(f"Error killing old instances: {e}")

def next_gen():
    global _generation
    with _gen_lock:
        _generation += 1
        return _generation

def get_chargers_from_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("CHARGERS", {})
    except Exception:
        return {}

def safe_connect(ip, port=502, timeout=5):
    try:
        client = ModbusTcpClient(ip, port=port, timeout=timeout)
        if client.connect():
            return client
        client.close()
    except Exception:
        pass
    return None

def safe_close(client):
    try:
        if client:
            client.close()
    except Exception:
        pass

def poll_victron(cid, info, my_gen):
    ip = info.get("ip")
    if not ip:
        return

    client = None
    connect_delay = 10

    while running:
        entry = active_threads.get(cid)
        if entry is None or entry["gen"] != my_gen:
            break

        if client is None:
            client = safe_connect(ip)
            if client is None:
                logger.error(f"{cid} (Victron) Connection Failed to {ip}. Retrying in {connect_delay}s")
                time.sleep(connect_delay)
                connect_delay = min(connect_delay * 2, 300) # Exponential backoff max 5 mins
                continue

        try:
            res_status = client.read_holding_registers(address=5009, count=7)
            if res_status is None or res_status.isError():
                raise IOError("Status registers error")

            # Read register 5016 for SetCurrent with safety
            amp_val = 16
            try:
                res_amp = client.read_holding_registers(address=5016, count=1)
                if res_amp is not None and not res_amp.isError() and len(res_amp.registers) >= 1:
                    amp_val = res_amp.registers[0]
            except Exception:
                pass

            # Reset exponential backoff on successful read
            connect_delay = 10

            # Keep print ONLY for valid JSON payloads that Node-RED parses from stdout
            print(json.dumps({
                "type": "victron_status",
                "chargerId": cid,
                "payload": res_status.registers,
                "amp": amp_val
            }, ensure_ascii=False), flush=True)

            time.sleep(0.5)

            res_energy = client.read_holding_registers(address=5021, count=1)
            if res_energy is not None and not res_energy.isError():
                print(json.dumps({
                    "type": "victron_energy",
                    "chargerId": cid,
                    "payload": res_energy.registers
                }, ensure_ascii=False), flush=True)

        except Exception as e:
            logger.error(f"{cid} (Victron) Error: {str(e)} — reconnecting")
            safe_close(client)
            client = None

        time.sleep(1.5)

    safe_close(client)


def poll_goe(cid, info, my_gen):
    global goe_states
    ip = info.get("ip")
    if not ip:
        return

    client = None
    connect_delay = 10

    while running:
        entry = active_threads.get(cid)
        if entry is None or entry["gen"] != my_gen:
            break

        if client is None:
            client = safe_connect(ip)
            if client is None:
                logger.error(f"{cid} (Go-E) Connection Failed to {ip}. Retrying in {connect_delay}s")
                time.sleep(connect_delay)
                connect_delay = min(connect_delay * 2, 300) # Exponential backoff max 5 mins
                continue

        try:
            # CAR_STATE: Address 100
            res_car = client.read_input_registers(address=100, count=1)
            if res_car is None or res_car.isError():
                raise IOError("CAR_STATE read error")

            # POWER_TOTAL: Address 120-121
            res_pwr = client.read_input_registers(address=120, count=2)
            if res_pwr is None or res_pwr.isError():
                raise IOError("POWER_TOTAL read error")

            # ALLOW_CHARGING: Address 201
            allow_charging = 1  # Default to 1 (not allowed)
            try:
                res_allow = client.read_holding_registers(address=201, count=1)
                if res_allow is not None and not res_allow.isError() and len(res_allow.registers) >= 1:
                    allow_charging = res_allow.registers[0]
            except Exception:
                pass

            raw_car = res_car.registers[0]
            raw_pwr_w = (res_pwr.registers[0] * 65536 + res_pwr.registers[1]) // 100  # Watt
            if raw_pwr_w > 30000:
                raw_pwr_w = 0

            volatile_amp = None
            eeprom_amp = None
            
            # Block read first
            try:
                res_amp = client.read_holding_registers(address=299, count=2)
                if res_amp is not None and not res_amp.isError() and len(res_amp.registers) >= 2:
                    volatile_amp = res_amp.registers[0]
                    eeprom_amp = res_amp.registers[1]
            except Exception:
                pass
                
            # Individual fallbacks
            if volatile_amp is None or eeprom_amp is None:
                try:
                    res_v = client.read_holding_registers(address=299, count=1)
                    if res_v is not None and not res_v.isError() and len(res_v.registers) >= 1:
                        volatile_amp = res_v.registers[0]
                except Exception:
                    pass
                
                try:
                    res_e = client.read_holding_registers(address=300, count=1)
                    if res_e is not None and not res_e.isError() and len(res_e.registers) >= 1:
                        eeprom_amp = res_e.registers[0]
                except Exception:
                    pass

            if volatile_amp is None and eeprom_amp is None:
                volatile_amp = 16
                eeprom_amp = 16
            elif volatile_amp is None:
                volatile_amp = eeprom_amp
            elif eeprom_amp is None:
                eeprom_amp = volatile_amp

            # Reset exponential backoff on successful read
            connect_delay = 10

            if cid not in goe_states:
                goe_states[cid] = {
                    "last_volatile": volatile_amp,
                    "last_eeprom": eeprom_amp,
                    "last_reported": volatile_amp if volatile_amp > 0 else eeprom_amp
                }

            state = goe_states[cid]
            amp_val = state["last_reported"]

            # Change logic detection
            if state["last_eeprom"] is not None and eeprom_amp != state["last_eeprom"]:
                amp_val = eeprom_amp
            elif state["last_volatile"] is not None and volatile_amp != state["last_volatile"] and volatile_amp > 0:
                amp_val = volatile_amp
            elif volatile_amp == 0 and state["last_volatile"] != 0:
                amp_val = eeprom_amp

            state["last_volatile"] = volatile_amp
            state["last_eeprom"] = eeprom_amp
            state["last_reported"] = amp_val

            print(json.dumps({
                "type": "goe_status",
                "chargerId": cid,
                "payload": [0, 0, raw_car, allow_charging, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, raw_pwr_w],
                "amp": amp_val
            }, ensure_ascii=False), flush=True)

        except Exception as e:
            logger.error(f"{cid} (Go-E) Error: {str(e)} — reconnecting")
            safe_close(client)
            client = None

        time.sleep(1.5)

    safe_close(client)


def manage_threads(current_chargers):
    for cid, info in current_chargers.items():
        ip = info.get("ip")
        ctype = info.get("type", "").lower()
        if not ip:
            continue

        existing = active_threads.get(cid)
        if existing and existing["ip"] == ip:
            continue

        gen = next_gen()
        active_threads[cid] = {"ip": ip, "type": ctype, "gen": gen}

        if ctype == "victron":
            t = threading.Thread(target=poll_victron, args=(cid, info, gen), daemon=True)
            t.start()
            logger.info(f"{cid} (Victron) thread started gen={gen}")
        elif ctype in ("go-e", "goe"):
            t = threading.Thread(target=poll_goe, args=(cid, info, gen), daemon=True)
            t.start()
            logger.info(f"{cid} (Go-E) thread started gen={gen}")

    for cid in list(active_threads.keys()):
        if cid not in current_chargers:
            del active_threads[cid]


def main():
    kill_other_instances()
    global previous_chargers_cfg
    logger.info("Chargers poller started")

    while running:
        current_cfg = get_chargers_from_config()

        if not current_cfg and previous_chargers_cfg:
            time.sleep(3)
            continue

        if current_cfg != previous_chargers_cfg:
            logger.info("Config changed — reloading threads")
            manage_threads(current_cfg)
            previous_chargers_cfg = current_cfg

        time.sleep(3)


if __name__ == "__main__":
    main()
