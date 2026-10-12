import socket
import time
import json
import sys
import os
import glob

# Waveshare Connection Configuration
WAVESHARE_IP = "192.168.0.220"
WAVESHARE_PORT = 502

# Reader Address (Default 0x01, updates dynamically if detected in packet)
READER_ADDRESS = 0x01

# Timestamp of last scan to avoid double swipes (10s cool-down)
LAST_SWIPE_TIME = 0.0

# Directory for confirmation files (Node-RED writes here - in RAM)
ACK_DIR = "/dev/shm/rfid_ack"
# Max wait timeout for confirmation (seconds)
ACK_TIMEOUT = 3.0

def crc16_ccitt(data: bytes, init=0x0000):
    crc = init
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

# Detected CRC init (None at start, 0x0000 or 0xFFFF thereafter)
CURRENT_CRC_INIT = None

def send_netronix_cmd(s, cmd, params):
    """Sends command to reader. Uses detected CRC or tries both versions."""
    global READER_ADDRESS, CURRENT_CRC_INIT
    
    if CURRENT_CRC_INIT is not None:
        # Known valid CRC, send once
        frame = bytearray([READER_ADDRESS, len(params) + 5, cmd]) + bytearray(params)
        crc = crc16_ccitt(bytes(frame), CURRENT_CRC_INIT)
        crch = (crc >> 8) & 0xFF
        crcl = crc & 0xFF
        full_frame = frame + bytearray([crch, crcl])
        try:
            s.sendall(full_frame)
        except Exception as e:
            print(f"Error sending command: {e}", file=sys.stderr, flush=True)
    else:
        # Fallback (startup only): send both CRC variants
        for init_crc in [0x0000, 0xFFFF]:
            frame = bytearray([READER_ADDRESS, len(params) + 5, cmd]) + bytearray(params)
            crc = crc16_ccitt(bytes(frame), init_crc)
            crch = (crc >> 8) & 0xFF
            crcl = crc & 0xFF
            full_frame = frame + bytearray([crch, crcl])
            try:
                s.sendall(full_frame)
            except Exception as e:
                print(f"Error sending command: {e}", file=sys.stderr, flush=True)
            time.sleep(0.05)
            
    # Ensure quiet time on RS485 after each transmission
    time.sleep(0.05)

def configure_reader(s):
    """Configures reader LED ports and buzzer."""
    print("Configuring RFID Reader ports...", file=sys.stderr, flush=True)
    # KOLOR0 (Green LED) -> RS_0 (Source 4)
    send_netronix_cmd(s, 0x50, [0x01, 0x00, 0x04])
    # KOLOR3 (Red LED) -> RS_1 (Source 5)
    send_netronix_cmd(s, 0x50, [0x04, 0x00, 0x05])
    # KOLOR2 (White/Orange LED) -> RS_3 (Source 7)
    send_netronix_cmd(s, 0x50, [0x03, 0x00, 0x07])
    # KOLOR1 (Blue LED) -> Source '0' (Source 0 - Always OFF to disable Button LED)
    send_netronix_cmd(s, 0x50, [0x02, 0x00, 0x00])
    # BUZZER -> RS_2 (Source 6)
    send_netronix_cmd(s, 0x50, [0x05, 0x00, 0x06])
    # ATrig=0x01 (Permanently ON), AOfflineTime=0x14, ASerial=0x01, AMode=0x40, ABuzz=0x00 (NO BEEP), AMulti=0x0F (All types), AInterface=0x01 (RS485 interface!)
    send_netronix_cmd(s, 0x58, [0x01, 0x14, 0x01, 0x40, 0x00, 0x0F, 0x01])

def parse_packets_from_buffer(buf: bytearray):
    """Scans buffer for valid Netronix packets based on CRC."""
    global CURRENT_CRC_INIT
    packets = []
    i = 0
    while i < len(buf):
        if i + 5 > len(buf):
            break
        length = buf[i+1]
        # Valid Netronix packet length is between 5 and 64 bytes
        if length < 5 or length > 64:
            i += 1
            continue
        if i + length > len(buf):
            # Incomplete packet, wait for more data
            break
            
        packet_bytes = buf[i : i + length]
        frame_to_check = packet_bytes[:-2]
        received_crc = (packet_bytes[-2] << 8) | packet_bytes[-1]
        
        matched_init = None
        for init in [0x0000, 0xFFFF]:
            if crc16_ccitt(bytes(frame_to_check), init) == received_crc:
                matched_init = init
                break
                
        if matched_init is not None:
            if CURRENT_CRC_INIT is None:
                CURRENT_CRC_INIT = matched_init
                print(f"Auto-detected working CRC init: 0x{matched_init:04X}", file=sys.stderr, flush=True)
            packets.append(packet_bytes)
            i += length
        else:
            i += 1
            
    # Remove processed bytes from buffer
    if i > 0:
        del buf[:i]
    return packets

def process_parsed_packet(packet: bytes):
    """Processes valid packet. Returns card ID if swipe, else None."""
    global READER_ADDRESS
    # Card scan opcode is 0x13, minimum length is 8 (Addr, Len, Op, 2 bytes info, 1 byte status, 2 bytes CRC)
    if len(packet) >= 8 and packet[2] == 0x13:
        status = packet[-3]
        if status == 0xFF: # OC_Successful
            # Card ID is located between header info and status byte
            id_bytes = packet[5 : -3]
            card_id = id_bytes.hex().upper()
            
            # Dynamic reader address update
            detected_addr = packet[0]
            if detected_addr != READER_ADDRESS:
                print(f"Detected new Reader address: 0x{detected_addr:02X} (previous: 0x{READER_ADDRESS:02X})", file=sys.stderr, flush=True)
                READER_ADDRESS = detected_addr
                
            return card_id
    return None

CONFIG_PATH_CACHE = None
CONFIG_DATA_CACHE = None
CONFIG_MTIME_CACHE = 0.0

def is_card_registered(card_id):
    """Dynamically loads smart-parking-config.json and checks card registration."""
    global CONFIG_PATH_CACHE, CONFIG_DATA_CACHE, CONFIG_MTIME_CACHE
    
    if CONFIG_PATH_CACHE is None:
        home_dir = os.path.expanduser("~")
        candidates = [
            os.path.join(home_dir, ".node-red", "smart-parking-config.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart-parking-config.json"),
            "/data/smart-parking-config.json"
        ]
        config_path = candidates[0]
        for c in candidates:
            if os.path.exists(c):
                config_path = c
                break
        CONFIG_PATH_CACHE = config_path
        
    try:
        if os.path.exists(CONFIG_PATH_CACHE):
            mtime = os.path.getmtime(CONFIG_PATH_CACHE)
            if CONFIG_DATA_CACHE is None or mtime > CONFIG_MTIME_CACHE:
                with open(CONFIG_PATH_CACHE, "r", encoding="utf-8") as f:
                    CONFIG_DATA_CACHE = json.load(f)
                CONFIG_MTIME_CACHE = mtime
                print(f"Loaded config from {CONFIG_PATH_CACHE} (mtime: {mtime})", file=sys.stderr, flush=True)
            
            users = CONFIG_DATA_CACHE.get("USERS", {})
            return card_id in users
    except Exception as e:
        print(f"Error checking card registration: {e}", file=sys.stderr, flush=True)
    return False

def cleanup_old_ack_files():
    """Cleans old ack files (>60s) to keep storage clean."""
    try:
        os.makedirs(ACK_DIR, exist_ok=True)
        for f in glob.glob(os.path.join(ACK_DIR, "ack_*")):
            try:
                if time.time() - os.path.getmtime(f) > 60:
                    os.remove(f)
            except:
                pass
    except:
        pass

def flush_socket(s):
    """Reads and drains pending socket buffer data."""
    old_timeout = s.gettimeout()
    s.settimeout(0.0) # Non-blocking mode
    try:
        while True:
            data = s.recv(4096)
            if not data:
                break
    except BlockingIOError:
        pass
    except Exception as e:
        print(f"Error flushing socket: {e}", file=sys.stderr, flush=True)
    finally:
        s.settimeout(old_timeout)

def wait_for_ack(card_id, timeout=ACK_TIMEOUT):
    """Waits for Node-RED ack file or timeout. Returns status."""
    ack_file = os.path.join(ACK_DIR, f"ack_{card_id}")
    try:
        if os.path.exists(ack_file):
            os.remove(ack_file)
    except:
        pass
    
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(ack_file):
            status = "ok"
            try:
                # Read ack file content to detect quick rejection
                with open(ack_file, "r") as f:
                    content = f.read().strip()
                    if content in ["lock", "fail", "denied"]:
                        status = "lock"
            except Exception as e:
                print(f"Error reading ack file: {e}", file=sys.stderr, flush=True)
            
            try:
                os.remove(ack_file)
            except:
                pass
            return status
        time.sleep(0.05)  # Check every 50ms for low latency
    return "timeout"

def kill_other_instances():
    """Kills older script instances running in the background."""
    import subprocess
    import signal
    current_pid = os.getpid()
    try:
        # Search for rfid1.py and rfid.py
        for pattern in ["rfid1.py", "rfid.py"]:
            output = subprocess.check_output(["pgrep", "-f", pattern]).decode('utf-8')
            pids = [int(p) for p in output.split() if p.strip().isdigit()]
            for pid in pids:
                if pid != current_pid:
                    print(f"Killing older RFID instance with PID {pid}...", file=sys.stderr, flush=True)
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except:
                        pass
        time.sleep(0.5)
    except subprocess.CalledProcessError:
        # pgrep returns non-zero exit code if no process matches, which is fine
        pass
    except Exception as e:
        print(f"Error killing old RFID instances: {e}", file=sys.stderr, flush=True)

def main():
    global CURRENT_CRC_INIT
    # Terminate older instances to prevent conflicts
    kill_other_instances()
    
    print("Started RFID scanner (Robust TCP & CRC Auto-Detect)...", file=sys.stderr, flush=True)
    
    # Create ack directory if missing
    os.makedirs(ACK_DIR, exist_ok=True)

    while True:
        try:
            CURRENT_CRC_INIT = None  # Reset CRC detection on each new connection
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Enable OS-level TCP Keep-Alive
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                try:
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                except AttributeError:
                    pass

                s.settimeout(1.0)  # Short timeout for fast loop and watchdog check
                s.connect((WAVESHARE_IP, WAVESHARE_PORT))

                # Initial reader configuration
                configure_reader(s)

                # Buffer to concatenate fragmented TCP packets
                buf = bytearray()
                last_activity_time = time.time()
                unanswered_pings = 0

                while True:
                    try:
                        data = s.recv(1024)
                        if not data:
                            print("Connection closed by remote host.", file=sys.stderr, flush=True)
                            break # Connection closed
                        
                        # Raw bytes debugging (commented out)
                        # print(f"Raw socket bytes received: {data.hex().upper()}", file=sys.stderr, flush=True)
                        buf.extend(data)
                        last_activity_time = time.time()  # Update activity time
                        
                    except socket.timeout:
                        # Watchdog ping if idle for over 30s
                        if time.time() - last_activity_time > 30.0:
                            if unanswered_pings >= 3:
                                # Reader not responding
                                print("Reader not responding to pings. Attempting Remote Reset (C_Reset 0xD0)...", file=sys.stderr, flush=True)
                                try:
                                    # Send C_Reset (0xD0) to reboot reader
                                    send_netronix_cmd(s, 0xD0, [])
                                    time.sleep(0.5)
                                except Exception as e:
                                    print(f"Error sending C_Reset: {e}", file=sys.stderr, flush=True)
                                print("Closing connection to reconnect...", file=sys.stderr, flush=True)
                                break # Break loop to reconnect

                            print(f"Sending watchdog ping #{unanswered_pings + 1} (C_FirmwareVersion)...", file=sys.stderr, flush=True)
                            send_netronix_cmd(s, 0xFE, [])
                            unanswered_pings += 1
                            last_activity_time = time.time()
                        continue

                    # Process all valid packets in buffer
                    packets = parse_packets_from_buffer(buf)
                    if packets:
                        # Each valid packet resets unanswered pings
                        unanswered_pings = 0
                    for packet in packets:
                        card_id = process_parsed_packet(packet)
                        if card_id:
                            # Card found
                            global LAST_SWIPE_TIME
                            current_time = time.time()
                            if current_time - LAST_SWIPE_TIME < 10.0:
                                print(f"Card swiped during 10s cool-down period. Ignoring completely...", file=sys.stderr, flush=True)
                                flush_socket(s)
                                continue

                            # Set last valid swipe time
                            LAST_SWIPE_TIME = current_time

                            # Check if card is registered
                            registered = is_card_registered(card_id)

                            if not registered:
                                # Unauthorized: Red LED + Error beep immediately
                                print(f"Card {card_id} is UNAUTHORIZED. Triggering Red LED and Error double beep...", file=sys.stderr, flush=True)
                                # Red LED (RS_1) ON for 600ms (0x3C)
                                send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])
                                # Double Beep (Error Beep)
                                send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08]) # Beep 1: 80ms
                                time.sleep(0.12)
                                send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08]) # Beep 2: 80ms
                            else:
                                # Registered: Send to Node-RED, wait for ACK
                                print(f"Card {card_id} is REGISTERED. Sending to Node-RED and waiting for ACK...", file=sys.stderr, flush=True)
                                
                                # Clean up old ack before sending
                                cleanup_old_ack_files()
                                ack_file = os.path.join(ACK_DIR, f"ack_{card_id}")
                                try:
                                    if os.path.exists(ack_file):
                                        os.remove(ack_file)
                                except:
                                    pass

                            # Send card_id to Node-RED (via stdout)
                            output = {"card_id": card_id}
                            print(json.dumps(output, ensure_ascii=False), flush=True)

                            if registered:
                                # Wait for ACK from Node-RED (max 3 seconds)
                                ack_status = wait_for_ack(card_id)
                                
                                if ack_status == "ok":
                                    # ACK received! Green LED + Beep (SUCCESS)
                                    print(f"Card {card_id}: ACK received from Node-RED! Green LED + Beep.", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x04, 0x01, 0x1E])  # Green LED 300ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x1E])  # Buzzer 300ms
                                elif ack_status == "lock":
                                    # Locked! Red LED + Error beep (LOCKED)
                                    print(f"Card {card_id}: Ignored by Node-RED (session locked)! Red LED.", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])  # Red LED 600ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 1
                                    time.sleep(0.12)
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 2
                                else:
                                    # Timeout! Red LED + Error beep (FAILED)
                                    print(f"Card {card_id}: NO ACK from Node-RED after {ACK_TIMEOUT}s! Red LED (command failed).", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])  # Red LED 600ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 1
                                    time.sleep(0.12)
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 2

                            # Debounce scan with socket flush
                            flush_socket(s)
                            time.sleep(1.5)
                            flush_socket(s)

                    # Prevent buffer overflow from noise
                    if len(buf) > 1024:
                        buf.clear()

        except (socket.timeout, ConnectionRefusedError, socket.error) as e:
            print(f"Connection/Socket error: {e}. Reconnecting in 3 seconds...", file=sys.stderr, flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"Error in Python script: {e}. Reconnecting in 3 seconds...", file=sys.stderr, flush=True)
            time.sleep(3)

if __name__ == "__main__":
    main()
