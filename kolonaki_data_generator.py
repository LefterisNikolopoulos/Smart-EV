import json
import random
from datetime import datetime, timedelta

with open('/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki-config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# Seed for repeatable, consistent report numbers matching the sample
random.seed(42)

chargers_list = list(cfg['CHARGERS'].keys())

# Let's create the synthetic charging history for October 2026 matching exactly 493 sessions and 9597 kWh
sessions = []
# Base stats matching the report
# -1: 3216 kWh, 167 sessions
# -2: 2985 kWh, 155 sessions
# -3: 3395 kWh, 171 sessions
# Total: 9597 kWh, 493 sessions

level_targets = {
    '-1': {'kwh': 3216.0, 'sessions': 167},
    '-2': {'kwh': 2985.0, 'sessions': 155},
    '-3': {'kwh': 3395.0, 'sessions': 171}
}

start_date = datetime(2026, 10, 1, 6, 0, 0)
end_date = datetime(2026, 10, 31, 22, 0, 0)

for lvl, tgt in level_targets.items():
    lvl_chargers = [c for c in chargers_list if c.startswith(lvl)]
    num_sessions = tgt['sessions']
    total_kwh = tgt['kwh']
    
    # generate random distribution of kwh per session
    weights = [random.uniform(0.5, 1.5) for _ in range(num_sessions)]
    total_w = sum(weights)
    kwhs = [(w / total_w) * total_kwh for w in weights]
    
    for i in range(num_sessions):
        ch = random.choice(lvl_chargers)
        co = cfg['CHARGERS'][ch]['company']
        
        # Day 1 to 31
        day = random.randint(1, 31)
        # Hour biased towards morning 08:00 - 10:00
        if random.random() < 0.7:
            hour = random.randint(8, 10)
        else:
            hour = random.randint(11, 19)
        minute = random.randint(0, 59)
        
        dt_start = datetime(2026, 10, day, hour, minute)
        duration_min = int(kwhs[i] / 11.0 * 60 * random.uniform(1.1, 1.4))
        if duration_min < 15: duration_min = 15
        dt_end = dt_start + timedelta(minutes=duration_min)
        
        sessions.append({
            "chargerId": ch,
            "level": lvl,
            "company": co,
            "card": f"RFID-{random.randint(1000, 9999)}",
            "kwh": round(kwhs[i], 1),
            "durationMinutes": duration_min,
            "startTime": dt_start.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": dt_end.strftime("%Y-%m-%d %H:%M:%S")
        })

with open('/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_sessions_oct2026.json', 'w', encoding='utf-8') as f:
    json.dump(sessions, f, ensure_ascii=False, indent=2)

print(f"Generated {len(sessions)} sessions, total kWh: {sum(s['kwh'] for s in sessions):.1f}")
