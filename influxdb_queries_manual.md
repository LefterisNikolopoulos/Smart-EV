# InfluxDB & Grafana Queries Manual - EV Smart Parking

This manual details the InfluxDB database schema and provides ready-to-use InfluxQL queries for building professional monitoring dashboards in Grafana.

---

## 📊 Database Schema Reference

All real-time telemetry from EV Smart Parking is stored under the measurement **`smart_ev`**.

### 1. Tags (Indexed fields - used for filtering and grouping)
| Tag Key | Description | Example Values |
| :--- | :--- | :--- |
| `zone_id` | Floor / Zone identifier | `1A`, `1B`, `2A`, `2B` |
| `charger_id` | Unique charger identifier | `victron`, `easee_1`, `goe_1`, `solax_1` |
| `spot` | Parking spot number | `1`, `2`, `3`, `4` |

### 2. Fields (Telemetry metrics)
| Field Key | Type | Description |
| :--- | :--- | :--- |
| `power` | Float | Active charging power in **kW** |
| `session_energy` | Float | Energy consumed in current charging session in **kWh** |
| `current_limit` | Float | Configured maximum current limit in **Amperes (A)** |
| `online` | Boolean | **`true`** if charger is online, **`false`** if offline |
| `is_occupied` | Boolean | **`true`** if EV is connected / plugged in |
| `is_charged` | Boolean | **`true`** if EV charging session has completed |
| `is_offline` | Boolean | Inverted online flag (*use `online` for simpler logic*) |

---

## ⏱️ Real-Time Status Queries (Table Panels)

These queries are optimized for **Grafana Table** visualization (ensure **Format as: Table** is selected in Grafana's Query Editor).

### A. General Overview Table (All Spots)
Displays current status across all chargers and parking spots:
```sql
SELECT last("online") AS "Online",
       last("is_occupied") AS "Connected",
       last("is_charged") AS "Completed",
       last("power") AS "Power (kW)",
       last("session_energy") AS "Energy (kWh)",
       last("current_limit") AS "Limit (A)"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### B. Connected Vehicles Only (Hides Empty Spots)
Displays only spots where a vehicle is currently plugged in:
```sql
SELECT last("is_charged") AS "Completed",
       last("power") AS "Power (kW)",
       last("session_energy") AS "Energy (kWh)",
       last("current_limit") AS "Limit (A)"
FROM "smart_ev"
WHERE "is_occupied" = true AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### C. Fully Charged Vehicles
Displays vehicles that finished charging but remain connected:
```sql
SELECT last("session_energy") AS "Energy (kWh)",
       last("power") AS "Power (kW)"
FROM "smart_ev"
WHERE "is_occupied" = true AND "is_charged" = true AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### D. Offline Chargers Only
Quickly detects any chargers that lost communication with the system:
```sql
SELECT last("online") AS "Online"
FROM "smart_ev"
WHERE "online" = false AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

---

## 📈 Time-Series & Trend Queries (Graph Panels)

These queries are optimized for **Time-Series Graph** panels (select **Format as: Time Series** in the Query Editor).

### A. Total Charging Power by Floor Over Time
Visualizes total power demand (kW) grouped by zone/floor (`zone_id`):
```sql
SELECT sum("power") AS "Floor Power"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY time($__interval), "zone_id" fill(0)
```

### B. Current Limit vs. Actual Power (e.g. for charger `victron`)
Compares active charging power (kW) against configured current limit (Amperes) over time:
```sql
SELECT mean("power") AS "Actual Power (kW)", 
       mean("current_limit") AS "Limit (A)"
FROM "smart_ev"
WHERE "charger_id" = 'victron' AND $timeFilter
GROUP BY time($__interval) fill(null)
```

### C. Total Daily Consumed Energy (kWh) by Charger
Displays energy consumed per 24 hours for each charging station:
```sql
SELECT max("session_energy") AS "Daily Energy"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY time(24h), "charger_id", "spot" fill(0)
```

---

## 🎨 Grafana Design Recommendations

To achieve a clean, professional aesthetic for your dashboard panels:

### 1. Value Mapping (Translate Booleans to Labels & Icons)
In panel settings under **Value mappings** on the right side:
* **For `online`:**
  * `true` $\rightarrow$ **`Online 🟢`**
  * `false` $\rightarrow$ **`Offline 🔴`**
* **For `is_occupied`:**
  * `true` $\rightarrow$ **`Connected 🔌`**
  * `false` $\rightarrow$ **`Empty ⚪`**
* **For `is_charged`:**
  * `true` $\rightarrow$ **`Completed 🔋`**
  * `false` $\rightarrow$ **`Charging ⚡`**

### 2. Thresholds (Color Rules)
* **For `power` (kW):**
  * Base $\rightarrow$ **Gray** (`0 kW`)
  * `> 0.1` $\rightarrow$ **Blue** or **Green** (actively charging).
