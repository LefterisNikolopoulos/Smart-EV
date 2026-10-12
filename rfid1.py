import socket
import time
import json
import sys
import os
import glob

# Διαμόρφωση Σύνδεσης Waveshare
WAVESHARE_IP = "192.168.0.220"
WAVESHARE_PORT = 502

# Διεύθυνση του Reader (Default 0x01, θα αλλάξει αυτόματα αν ανιχνευθεί άλλη στο πακέτο)
READER_ADDRESS = 0x01

# Χρόνος τελευταίου σκαναρίσματος για την αποφυγή διπλού χτυπήματος (Cool-down 10 δευτερολέπτων)
LAST_SWIPE_TIME = 0.0

# Φάκελος για τα αρχεία confirmation (ο Node-RED γράφει εδώ - στη RAM)
ACK_DIR = "/dev/shm/rfid_ack"
# Μέγιστος χρόνος αναμονής για confirmation (δευτερόλεπτα)
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

# Ανιχνευμένο CRC init (None κατά την εκκίνηση, 0x0000 ή 0xFFFF στη συνέχεια)
CURRENT_CRC_INIT = None

def send_netronix_cmd(s, cmd, params):
    """Στέλνει την εντολή στον reader. Χρησιμοποιεί το ανιχνευμένο CRC (CURRENT_CRC_INIT) 
    αν υπάρχει, αλλιώς στέλνει και τις δύο εκδοχές (0x0000 και 0xFFFF) με μικρή καθυστέρηση 
    για να αποτραπούν οι συγκρούσεις (collisions)."""
    global READER_ADDRESS, CURRENT_CRC_INIT
    
    if CURRENT_CRC_INIT is not None:
        # Γνωρίζουμε το σωστό CRC, στέλνουμε μόνο μία φορά
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
        # Fallback (μόνο στην αρχή): Αποστολή και των δύο εκδόσεων
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
            
    # Εξασφάλιση quiet time στο RS485 μετά από κάθε αποστολή
    time.sleep(0.05)

def configure_reader(s):
    """Ρυθμίζει τις θύρες KOLOR0 (Green), KOLOR3 (Red), KOLOR2 (White), KOLOR1 (Blue) και BUZZER (Ήχος)
    να ελέγχονται από τις σειριακές πηγές RS_0, RS_1, RS_3, Source '0', RS_2 αντίστοιχα,
    και απενεργοποιεί τον αυτόματο ήχο σκαναρίσματος."""
    print("Configuring RFID Reader ports...", file=sys.stderr, flush=True)
    # KOLOR0 (Green LED) -> RS_0 (Source 4)
    send_netronix_cmd(s, 0x50, [0x01, 0x00, 0x04])
    # KOLOR3 (Red LED) -> RS_1 (Source 5)
    send_netronix_cmd(s, 0x50, [0x04, 0x00, 0x05])
    # KOLOR2 (White/Orange LED) -> RS_3 (Source 7)
    send_netronix_cmd(s, 0x50, [0x03, 0x00, 0x07])
    # KOLOR1 (Blue LED) -> Source '0' (Source 0 - Always OFF to disable Button LED)
    send_netronix_cmd(s, 0x50, [0x02, 0x00, 0x00])
    # BUZZER (Ήχος) -> RS_2 (Source 6)
    send_netronix_cmd(s, 0x50, [0x05, 0x00, 0x06])
    # ATrig=0x01 (Permanently ON), AOfflineTime=0x14, ASerial=0x01, AMode=0x40, ABuzz=0x00 (NO BEEP), AMulti=0x0F (All types), AInterface=0x01 (RS485 interface!)
    send_netronix_cmd(s, 0x58, [0x01, 0x14, 0x01, 0x40, 0x00, 0x0F, 0x01])

def parse_packets_from_buffer(buf: bytearray):
    """Σκανάρει τον buffer για έγκυρα Netronix πακέτα βάσει CRC.
    Ανιχνεύει αυτόματα το κατάλληλο CRC init (0x0000 ή 0xFFFF)."""
    global CURRENT_CRC_INIT
    packets = []
    i = 0
    while i < len(buf):
        if i + 5 > len(buf):
            break
        length = buf[i+1]
        # Το λογικό μήκος πακέτου Netronix για τις ανάγκες μας είναι μεταξύ 5 και 64 bytes
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
            
    # Αφαιρούμε τα bytes που επεξεργαστήκαμε από τον buffer
    if i > 0:
        del buf[:i]
    return packets

def process_parsed_packet(packet: bytes):
    """Επεξεργάζεται ένα έγκυρο πακέτο. Αν είναι σκανάρισμα κάρτας, επιστρέφει το ID, αλλιώς None."""
    global READER_ADDRESS
    # Card scan opcode is 0x13, minimum length is 8 (Addr, Len, Op, 2 bytes info, 1 byte status, 2 bytes CRC)
    if len(packet) >= 8 and packet[2] == 0x13:
        status = packet[-3]
        if status == 0xFF: # OC_Successful
            # Card ID is located between header info and status byte
            id_bytes = packet[5 : -3]
            card_id = id_bytes.hex().upper()
            
            # Δυναμική ενημέρωση διεύθυνσης reader
            detected_addr = packet[0]
            if detected_addr != READER_ADDRESS:
                print(f"Ανιχνεύθηκε νέα διεύθυνση Reader: 0x{detected_addr:02X} (προηγούμενη: 0x{READER_ADDRESS:02X})", file=sys.stderr, flush=True)
                READER_ADDRESS = detected_addr
                
            return card_id
    return None

CONFIG_PATH_CACHE = None
CONFIG_DATA_CACHE = None
CONFIG_MTIME_CACHE = 0.0

def is_card_registered(card_id):
    """Φορτώνει δυναμικά το smart-parking-config.json και ελέγχει αν η κάρτα είναι εγγεγραμμένη, με caching στη μνήμη."""
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
    """Καθαρίζει παλιά ack files (>60 δευτερολέπτων) για να μην γεμίσει ο /tmp"""
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
    """Διαβάζει και απορρίπτει όλα τα δεδομένα που εκκρεμούν στο buffer του socket."""
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
    """Περιμένει μέχρι ο Node-RED να γράψει ένα ack file, ή μέχρι το timeout.
    Επιστρέφει 'ok' αν εγκρίθηκε, 'lock' αν απορρίφθηκε/κλειδώθηκε, ή 'timeout'."""
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
                # Διαβάζουμε το περιεχόμενο του ack file για να ανιχνεύσουμε γρήγορη απόρριψη
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
        time.sleep(0.05)  # Έλεγχος κάθε 50ms για άμεση απόκριση
    return "timeout"

def kill_other_instances():
    """Σκοτώνει άλλες παλαιότερες εκδόσεις του script που τρέχουν στο background για να μην υπάρχουν συγκρούσεις."""
    import subprocess
    import signal
    current_pid = os.getpid()
    try:
        # Αναζήτηση για rfid1.py και rfid.py
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
    # Σκοτώνουμε τυχόν παλαιότερα instances για να μην υπάρχουν συγκρούσεις
    kill_other_instances()
    
    print("Ξεκίνησε το RFID scanner (Robust TCP & CRC Auto-Detect)...", file=sys.stderr, flush=True)
    
    # Δημιουργούμε τον φάκελο ack αν δεν υπάρχει
    os.makedirs(ACK_DIR, exist_ok=True)

    while True:
        try:
            CURRENT_CRC_INIT = None  # Επαναφορά της ανίχνευσης CRC σε κάθε νέα σύνδεση
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Ενεργοποίηση TCP Keep-Alive σε επίπεδο OS
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                try:
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                except AttributeError:
                    pass

                s.settimeout(1.0)  # Μικρό timeout για γρήγορο loop και έλεγχο watchdog
                s.connect((WAVESHARE_IP, WAVESHARE_PORT))

                # Αρχική ρύθμιση του reader
                configure_reader(s)

                # Μνήμη (Buffer) για να ενώνει τα κομμένα TCP πακέτα!
                buf = bytearray()
                last_activity_time = time.time()
                unanswered_pings = 0

                while True:
                    try:
                        data = s.recv(1024)
                        if not data:
                            print("Connection closed by remote host.", file=sys.stderr, flush=True)
                            break # Έκλεισε η σύνδεση
                        
                        # Τυπώνουμε τα raw bytes που ήρθαν από το Waveshare για έλεγχο (σχολιασμένο για μείωση εγγραφών στην SD κάρτα)
                        # print(f"Raw socket bytes received: {data.hex().upper()}", file=sys.stderr, flush=True)
                        buf.extend(data)
                        last_activity_time = time.time()  # Ενημέρωση χρόνου δραστηριότητας
                        
                    except socket.timeout:
                        # Watchdog ping αν δεν υπάρχει δραστηριότητα για πάνω από 30 δευτερόλεπτα
                        if time.time() - last_activity_time > 30.0:
                            if unanswered_pings >= 3:
                                # Ο reader δεν απαντάει!
                                print("Ο reader δεν απαντάει στα pings. Επιχείρηση αποστολής Remote Reset (C_Reset 0xD0)...", file=sys.stderr, flush=True)
                                try:
                                    # Στέλνουμε C_Reset (0xD0) στον reader για reboot
                                    send_netronix_cmd(s, 0xD0, [])
                                    time.sleep(0.5)
                                except Exception as e:
                                    print(f"Σφάλμα κατά την αποστολή C_Reset: {e}", file=sys.stderr, flush=True)
                                print("Κλείσιμο σύνδεσης για επανασύνδεση...", file=sys.stderr, flush=True)
                                break # Σπάμε το loop για να γίνει reconnect

                            print(f"Sending watchdog ping #{unanswered_pings + 1} (C_FirmwareVersion)...", file=sys.stderr, flush=True)
                            send_netronix_cmd(s, 0xFE, [])
                            unanswered_pings += 1
                            last_activity_time = time.time()
                        continue

                    # Επεξεργασία όλων των έγκυρων πακέτων που βρέθηκαν στον buffer
                    packets = parse_packets_from_buffer(buf)
                    if packets:
                        # Κάθε έγκυρο πακέτο από τον reader μηδενίζει τα αναπάντητα pings
                        unanswered_pings = 0
                    for packet in packets:
                        card_id = process_parsed_packet(packet)
                        if card_id:
                            # Βρήκαμε κάρτα!
                            global LAST_SWIPE_TIME
                            current_time = time.time()
                            if current_time - LAST_SWIPE_TIME < 10.0:
                                print(f"Card swiped during 10s cool-down period. Ignoring completely...", file=sys.stderr, flush=True)
                                flush_socket(s)
                                continue

                            # Θέτουμε τον χρόνο της τελευταίας έγκυρης ανάγνωσης
                            LAST_SWIPE_TIME = current_time

                            # Έλεγχος αν η κάρτα είναι εγγεγραμμένη
                            registered = is_card_registered(card_id)

                            if not registered:
                                # Unauthorized: Κόκκινο LED + Error beep ΑΜΕΣΩΣ
                                print(f"Card {card_id} is UNAUTHORIZED. Triggering Red LED and Error double beep...", file=sys.stderr, flush=True)
                                # Κόκκινο LED (RS_1) ON για 600ms (0x3C)
                                send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])
                                # Διπλό Beep (Error Beep)
                                send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08]) # Beep 1: 80ms
                                time.sleep(0.12)
                                send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08]) # Beep 2: 80ms
                            else:
                                # Registered: Στέλνουμε πρώτα στο Node-RED, ΠΕΡΙΜΕΝΟΥΜΕ ACK
                                print(f"Card {card_id} is REGISTERED. Sending to Node-RED and waiting for ACK...", file=sys.stderr, flush=True)
                                
                                # Καθαρίζουμε τυχόν παλιό ack πριν στείλουμε
                                cleanup_old_ack_files()
                                ack_file = os.path.join(ACK_DIR, f"ack_{card_id}")
                                try:
                                    if os.path.exists(ack_file):
                                        os.remove(ack_file)
                                except:
                                    pass

                            # Στέλνουμε το card_id στο Node-RED (μέσω stdout)
                            output = {"card_id": card_id}
                            print(json.dumps(output, ensure_ascii=False), flush=True)

                            if registered:
                                # Περιμένουμε ACK από τον Node-RED (max 3 δευτερόλεπτα)
                                ack_status = wait_for_ack(card_id)
                                
                                if ack_status == "ok":
                                    # ✅ ACK received! Πράσινο LED + Beep (SUCCESS)
                                    print(f"Card {card_id}: ACK received from Node-RED! Green LED + Beep.", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x04, 0x01, 0x1E])  # Πράσινο LED 300ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x1E])  # Buzzer 300ms
                                elif ack_status == "lock":
                                    # ❌ Locked! Κόκκινο LED + Error beep (LOCKED)
                                    print(f"Card {card_id}: Ignored by Node-RED (session locked)! Red LED.", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])  # Κόκκινο LED 600ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 1
                                    time.sleep(0.12)
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 2
                                else:
                                    # ❌ Timeout! Κόκκινο LED + Error beep (FAILED)
                                    print(f"Card {card_id}: NO ACK from Node-RED after {ACK_TIMEOUT}s! Red LED (command failed).", file=sys.stderr, flush=True)
                                    send_netronix_cmd(s, 0x70, [0x05, 0x01, 0x3C])  # Κόκκινο LED 600ms
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 1
                                    time.sleep(0.12)
                                    send_netronix_cmd(s, 0x70, [0x06, 0x01, 0x08])  # Beep 2

                            # Αποφυγή πολλαπλών αναγνώσεων (debounce) με socket flush
                            flush_socket(s)
                            time.sleep(1.5)
                            flush_socket(s)

                    # Προστασία από συσσώρευση μεγάλου όγκου δεδομένων/θορύβου στον buffer
                    if len(buf) > 1024:
                        buf.clear()

        except (socket.timeout, ConnectionRefusedError, socket.error) as e:
            print(f"Σύνδεση/Socket σφάλμα: {e}. Επανασύνδεση σε 3 δευτερόλεπτα...", file=sys.stderr, flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"Σφάλμα στο Python script: {e}. Επανασύνδεση σε 3 δευτερόλεπτα...", file=sys.stderr, flush=True)
            time.sleep(3)

if __name__ == "__main__":
    main()
