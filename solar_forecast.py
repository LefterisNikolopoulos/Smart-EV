#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import urllib.parse
import json
import datetime
import os
import sys
import time

BASE_URL = "https://predictionpv.degertech.duckdns.org"

def load_scenario_from_config():
    home = os.path.expanduser("~")
    paths = [
        os.path.join(home, ".node-red", "smart-parking-config.json"),
        os.path.join(home, "Documents/DegerHellas/Smart Ev/smart-parking-config.json"),
        os.path.join(home, "Smart Ev/smart-parking-config.json")
    ]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths.append(os.path.join(script_dir, "smart-parking-config.json"))
    
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    scenario = cfg.get('FORECAST_SCENARIO')
                    if scenario:
                        print(f"Found scenario in config {p}: {scenario}")
                        return scenario
            except Exception as e:
                print(f"Error reading config {p}: {e}", file=sys.stderr)
    return None


def get_forecast(date_str, scenario_id=None):
    """Pure GET call to fetch forecast dynamically from the server API."""
    urls = []
    if scenario_id:
        urls.append(f"{BASE_URL}/api.php?action=forecast&id={scenario_id}&date={date_str}")
    urls.append(f"{BASE_URL}/api.php?action=forecast&date={date_str}")

    for url in urls:
        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        if data and 'daily' in data and 'hourly_series' in data:
                            return data
            except Exception as e:
                print(f"Attempt {attempt} GET failed for {date_str} ({url}): {e}", file=sys.stderr)
                if attempt < 3:
                    time.sleep(1)
    return None


def process_forecast(data):
    if not data or 'daily' not in data or 'scenario' not in data or 'hourly_series' not in data:
        return None
    
    daily = data['daily']
    scenario = data['scenario']
    hourly_series = data['hourly_series']
    
    kwp = float(scenario.get('kwp_total', 0) or 0)
    pr = float(scenario.get('pr', 0.82) or 0.82)
    
    # Process hourly values dynamically from server API response
    hourly_sums = {h: [] for h in range(24)}
    
    for pt in hourly_series:
        time_str = pt.get('time', '')
        if not time_str or 'T' not in time_str:
            continue
        try:
            time_part = time_str.split('T')[1]
            hour = int(time_part.split(':')[0])
            poa = float(pt.get('poa_actual_w_m2', 0))
            power_kw = (poa * kwp * pr) / 1000.0 if kwp > 0 else 0.0
            
            if 0 <= hour < 24:
                hourly_sums[hour].append(power_kw)
        except Exception:
            pass
            
    hourly_profile = []
    for h in range(24):
        vals = hourly_sums[h]
        avg_power = round(sum(vals) / len(vals), 2) if vals else 0.0
        hourly_profile.append({
            "hour": h,
            "power_kw": avg_power
        })
        
    return {
        "date": daily.get('date'),
        "predicted_yield_kwh": round(daily.get('yield_kwh', 0), 1),
        "unshaded_yield_kwh": round(daily.get('yield_unshaded_kwh', 0), 1),
        "shaded_yield_kwh": round(daily.get('yield_shaded_kwh', 0), 1),
        "shade_loss_pct": round(daily.get('shading_loss_percent', 0), 1),
        "cloud_loss_pct": round(daily.get('cloud_loss_percent', 0), 1),
        "temp_loss_pct": round(daily.get('temp_loss_percent', 0), 1),
        "total_loss_pct": round(daily.get('total_loss_percent', 0), 1),
        "hourly_profile": hourly_profile
    }


def main():
    scenario_id = load_scenario_from_config()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    
    today_str = today.isoformat()
    tomorrow_str = tomorrow.isoformat()
    
    print(f"Fetching today's forecast ({today_str}) dynamically from API...")
    today_raw = get_forecast(today_str, scenario_id)
    today_processed = process_forecast(today_raw)
    
    print(f"Fetching tomorrow's forecast ({tomorrow_str}) dynamically from API...")
    tomorrow_raw = get_forecast(tomorrow_str, scenario_id)
    tomorrow_processed = process_forecast(tomorrow_raw)
    
    if not today_processed:
        print("Failed to get today's forecast from API. Aborting.", file=sys.stderr)
        sys.exit(1)
        
    params = {}
    if today_raw and 'scenario' in today_raw:
        s = today_raw['scenario']
        params = {
            "lat": s.get('lat'),
            "lon": s.get('lon'),
            "system_type": s.get('system_type'),
            "kwp": s.get('kwp_total'),
            "pr": s.get('pr')
        }
        
    output_data = {
        "today": today_processed,
        "tomorrow": tomorrow_processed or {},
        "parameters": params,
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save file
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(workspace_dir, "solar-forecast.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"Saved forecast to {out_file}")
    
    # Also save to user's .node-red if it exists
    home_dir = os.path.expanduser("~")
    nodered_file = os.path.join(home_dir, ".node-red", "solar-forecast.json")
    if os.path.exists(os.path.dirname(nodered_file)):
        try:
            with open(nodered_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            print(f"Saved forecast to {nodered_file}")
        except Exception as e:
            print(f"Could not copy to .node-red: {e}")

if __name__ == "__main__":
    main()
