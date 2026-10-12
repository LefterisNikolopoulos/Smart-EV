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
    home_dir = os.path.expanduser("~")
    candidates = [
        os.path.join(home_dir, ".node-red", "smart-parking-config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart-parking-config.json"),
        "/data/smart-parking-config.json"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

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
active_threads = {}      # { cid: {"ip": ..., "type": ..., "gen": N, "thread": t, "last_poll": ts} }
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

def safe_connect(ip, port=502, timeout=2):
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
    consecutive_errors = 0

    while running:
        entry = active_threads.get(cid)
        if entry is None or entry.get("gen") != my_gen:
            break

        if client is None:
            client = safe_connect(ip, timeout=2)
            if client is None:
                consecutive_errors += 1
                retry_delay = min(1.0 * (1.5 ** min(consecutive_errors, 5)), 10.0)
                if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                    logger.warning(f"[Watchdog] {cid} (Victron) Connection Failed to {ip}. Retry #{consecutive_errors} in {retry_delay:.1f}s")
                time.sleep(retry_delay)
                continue

        try:
            res_status = client.read_holding_registers(address=5009, count=13)
            if res_status is None or res_status.isError():
                raise IOError("Status registers read error")

            regs = res_status.registers
            amp_val = regs[7] if len(regs) >= 8 and regs[7] > 0 else 16
            energy_val = [regs[12]] if len(regs) >= 13 else [0]

            if consecutive_errors > 0:
                logger.info(f"[Watchdog] {cid} (Victron) connection self-healed and resumed normal polling.")
                consecutive_errors = 0

            if cid in active_threads:
                active_threads[cid]["last_poll"] = time.time()

            print(json.dumps({
                "type": "victron_status",
                "chargerId": cid,
                "payload": regs,
                "amp": amp_val
            }, ensure_ascii=False), flush=True)

            print(json.dumps({
                "type": "victron_energy",
                "chargerId": cid,
                "payload": energy_val
            }, ensure_ascii=False), flush=True)

        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                logger.warning(f"[Watchdog] {cid} (Victron) Error: {str(e)} — Auto-closing socket for recovery (err count: {consecutive_errors})")
            safe_close(client)
            client = None
            time.sleep(min(0.5 * consecutive_errors, 5.0))
            continue

        time.sleep(0.3)

    safe_close(client)


def poll_goe(cid, info, my_gen):
    global goe_states
    ip = info.get("ip")
    if not ip:
        return

    client = None
    consecutive_errors = 0

    while running:
        entry = active_threads.get(cid)
        if entry is None or entry.get("gen") != my_gen:
            break

        if client is None:
            client = safe_connect(ip, timeout=1.5)
            if client is None:
                consecutive_errors += 1
                retry_delay = min(1.0 * (1.5 ** min(consecutive_errors, 5)), 10.0)
                if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                    logger.warning(f"[Watchdog] {cid} (Go-E) Connection Failed to {ip}. Retry #{consecutive_errors} in {retry_delay:.1f}s")
                time.sleep(retry_delay)
                continue

        try:
            # Fast batch reading for Go-E
            # CAR_STATE (100) & POWER_TOTAL (120-121)
            res_car = client.read_input_registers(address=100, count=1)
            if res_car is None or res_car.isError():
                raise IOError("CAR_STATE read error")

            res_pwr = client.read_input_registers(address=120, count=2)
            if res_pwr is None or res_pwr.isError():
                raise IOError("POWER_TOTAL read error")

            # ALLOW_CHARGING (201)
            allow_charging = 1
            try:
                res_allow = client.read_holding_registers(address=201, count=1)
                if res_allow is not None and not res_allow.isError() and len(res_allow.registers) >= 1:
                    allow_charging = res_allow.registers[0]
            except Exception:
                pass

            raw_car = res_car.registers[0]
            raw_pwr_w = (res_pwr.registers[0] * 65536 + res_pwr.registers[1]) // 100
            if raw_pwr_w > 30000:
                raw_pwr_w = 0

            volatile_amp = None
            eeprom_amp = None
            
            try:
                res_amp = client.read_holding_registers(address=299, count=2)
                if res_amp is not None and not res_amp.isError() and len(res_amp.registers) >= 2:
                    volatile_amp = res_amp.registers[0]
                    eeprom_amp = res_amp.registers[1]
            except Exception:
                pass
                
            if volatile_amp is None and eeprom_amp is None:
                volatile_amp = 16
                eeprom_amp = 16
            elif volatile_amp is None:
                volatile_amp = eeprom_amp
            elif eeprom_amp is None:
                eeprom_amp = volatile_amp

            if consecutive_errors > 0:
                logger.info(f"[Watchdog] {cid} (Go-E) connection self-healed and resumed normal polling.")
                consecutive_errors = 0

            if cid in active_threads:
                active_threads[cid]["last_poll"] = time.time()

            if cid not in goe_states:
                goe_states[cid] = {
                    "last_volatile": volatile_amp,
                    "last_eeprom": eeprom_amp,
                    "last_reported": volatile_amp if volatile_amp > 0 else eeprom_amp
                }

            state = goe_states[cid]
            amp_val = state["last_reported"]

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
            consecutive_errors += 1
            if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                logger.warning(f"[Watchdog] {cid} (Go-E) Error: {str(e)} — Auto-closing socket for recovery (err count: {consecutive_errors})")
            safe_close(client)
            client = None
            time.sleep(min(0.5 * consecutive_errors, 5.0))
            continue

        # Ultra-fast 300ms poll interval for real-time responsiveness
        time.sleep(0.3)

    safe_close(client)


def poll_solax(cid, info, my_gen):
    ip = info.get("ip")
    if not ip:
        return

    consecutive_errors = 0

    while running:
        entry = active_threads.get(cid)
        if entry is None or entry.get("gen") != my_gen:
            break

        client = None
        try:
            client = safe_connect(ip, timeout=1.5)
            if client is None:
                consecutive_errors += 1
                retry_delay = min(1.0 * (1.5 ** min(consecutive_errors, 5)), 10.0)
                if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                    logger.warning(f"[Watchdog] {cid} (SolaX) Connection Failed to {ip}. Retry #{consecutive_errors} in {retry_delay:.1f}s")
                time.sleep(retry_delay)
                continue

            # Read Input Registers 0x0000..0x0011 (count=18) using FC 0x04
            try:
                res_input = client.read_input_registers(address=0, count=18, slave=1)
            except TypeError:
                res_input = client.read_input_registers(address=0, count=18, unit=1)

            if res_input is None or res_input.isError() or len(res_input.registers) < 18:
                raise IOError("SolaX input registers read error")

            regs = res_input.registers
            v1 = round(regs[0] / 100.0, 2)
            v2 = round(regs[1] / 100.0, 2)
            v3 = round(regs[2] / 100.0, 2)
            i1 = round(regs[4] / 100.0, 2)
            i2 = round(regs[5] / 100.0, 2)
            i3 = round(regs[6] / 100.0, 2)
            p1 = regs[8]
            p2 = regs[9]
            p3 = regs[10]
            total_power_w = regs[11]
            total_power_kw = round(total_power_w / 1000.0, 2)
            single_energy_kwh = round(regs[15] / 10.0, 2)
            total_energy_kwh = round((regs[16] + (regs[17] << 16)) / 10.0, 2)

            # Read State from Input Register 0x0106 (address 262)
            raw_state = 0
            try:
                try:
                    res_state = client.read_input_registers(address=262, count=1, slave=1)
                except TypeError:
                    res_state = client.read_input_registers(address=262, count=1, unit=1)
                if res_state is not None and not res_state.isError() and len(res_state.registers) >= 1:
                    raw_state = res_state.registers[0]
            except Exception:
                pass

            # Read Holding Register 0x0628 (address 1576) for current limit setting
            amp_val = 16
            try:
                try:
                    res_amp = client.read_holding_registers(address=1576, count=1, slave=1)
                except TypeError:
                    res_amp = client.read_holding_registers(address=1576, count=1, unit=1)
                if res_amp is not None and not res_amp.isError() and len(res_amp.registers) >= 1:
                    if res_amp.registers[0] >= 600:
                        amp_val = int(round(res_amp.registers[0] / 100.0))
                    elif 6 <= res_amp.registers[0] <= 32:
                        amp_val = res_amp.registers[0]
            except Exception:
                pass

            safe_close(client)
            client = None

            if consecutive_errors > 0:
                logger.info(f"[Watchdog] {cid} (SolaX) connection self-healed and resumed normal polling.")
                consecutive_errors = 0

            if cid in active_threads:
                active_threads[cid]["last_poll"] = time.time()

            print(json.dumps({
                "type": "solax_status",
                "chargerId": cid,
                "payload": {
                    "v1": v1, "v2": v2, "v3": v3,
                    "i1": i1, "i2": i2, "i3": i3,
                    "p1": p1, "p2": p2, "p3": p3,
                    "powerW": total_power_w,
                    "power": total_power_kw,
                    "singleEnergy": single_energy_kwh,
                    "totalEnergy": total_energy_kwh,
                    "rawStatus": raw_state
                },
                "amp": amp_val
            }, ensure_ascii=False), flush=True)

        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors == 1 or consecutive_errors % 10 == 0:
                logger.warning(f"[Watchdog] {cid} (SolaX) Error: {str(e)} (err count: {consecutive_errors})")
            if client:
                safe_close(client)
                client = None

        # Clean 1.5 second pause between polls to leave socket completely free for control commands
        time.sleep(1.5)


def start_charger_thread(cid, info):
    ip = info.get("ip")
    ctype = info.get("type", "").lower()
    if not ip and ctype not in ("wallbox", "easee"):
        return None

    gen = next_gen()
    t = None

    if ctype == "victron":
        t = threading.Thread(target=poll_victron, args=(cid, info, gen), daemon=True, name=f"poller-{cid}")
    elif ctype in ("go-e", "goe"):
        t = threading.Thread(target=poll_goe, args=(cid, info, gen), daemon=True, name=f"poller-{cid}")
    elif ctype in ("solax", "solax_evc", "solax_1"):
        t = threading.Thread(target=poll_solax, args=(cid, info, gen), daemon=True, name=f"poller-{cid}")
    elif ctype in ("wallbox", "easee"):
        logger.info(f"{cid} ({ctype}) uses API — no Modbus TCP thread needed")
        return None

    if t:
        active_threads[cid] = {
            "ip": ip,
            "type": ctype,
            "gen": gen,
            "thread": t,
            "last_poll": time.time(),
            "info": info
        }
        t.start()
        logger.info(f"[Watchdog] {cid} ({ctype}) thread started gen={gen} [IP: {ip}]")
    return t


def manage_threads(current_chargers):
    for cid, info in current_chargers.items():
        ip = info.get("ip")
        ctype = info.get("type", "").lower()
        if not ip and ctype not in ("wallbox", "easee"):
            continue

        existing = active_threads.get(cid)
        if existing and existing.get("ip") == ip and existing.get("thread") and existing["thread"].is_alive():
            continue

        start_charger_thread(cid, info)

    for cid in list(active_threads.keys()):
        if cid not in current_chargers:
            logger.info(f"Removing inactive charger {cid}")
            del active_threads[cid]


def watchdog_supervisor(current_chargers):
    """Monitors thread liveness and restarts any dropped threads automatically."""
    for cid, info in current_chargers.items():
        ctype = info.get("type", "").lower()
        if ctype in ("wallbox", "easee"):
            continue
        ip = info.get("ip")
        if not ip:
            continue

        entry = active_threads.get(cid)
        if entry is None or entry.get("thread") is None or not entry["thread"].is_alive():
            logger.warning(f"[Watchdog] Charger {cid} ({ctype}) poller thread is NOT running. Auto-healing / Respawning thread...")
            start_charger_thread(cid, info)


def main():
    kill_other_instances()
    global previous_chargers_cfg
    logger.info("Chargers poller with Auto-Healing Watchdog started")

    while running:
        try:
            current_cfg = get_chargers_from_config()

            if not current_cfg and previous_chargers_cfg:
                time.sleep(2)
                continue

            if current_cfg != previous_chargers_cfg:
                logger.info("Config changed — reloading threads")
                manage_threads(current_cfg)
                previous_chargers_cfg = current_cfg
            else:
                # Periodic watchdog check for thread liveness
                watchdog_supervisor(current_cfg)

        except Exception as e:
            logger.error(f"[Watchdog] Supervisor error: {e}")

        time.sleep(2)


if __name__ == "__main__":
    main()
