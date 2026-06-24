# Εγχειρίδιο Queries InfluxDB & Grafana - EV Smart Parking

Αυτό το εγχειρίδιο περιγράφει τη δομή δεδομένων του InfluxDB και παρέχει έτοιμα ερωτήματα (Queries) σε InfluxQL για τη δημιουργία επαγγελματικών Dashboards στο Grafana.

---

## 📊 Αναφορά Δομής Δεδομένων (Database Schema)

Όλα τα δεδομένα πραγματικού χρόνου του EV Smart Parking αποθηκεύονται κάτω από το όνομα Measurement **`smart_ev`**.

### 1. Tags (Πεδία ευρετηρίου - χρησιμοποιούνται για φιλτράρισμα και ομαδοποίηση)
| Tag Key | Περιγραφή | Παραδείγματα Τιμών |
| :--- | :--- | :--- |
| `zone_id` | Αναγνωριστικό Ορόφου / Ζώνης | `1A`, `1B`, `2A`, `2B` |
| `charger_id` | Μοναδικό ID του φορτιστή | `victron`, `easee_1`, `goe_1` |
| `spot` | Αριθμός θέσης στάθμευσης | `1`, `2`, `3`, `4` |

### 2. Fields (Μετρήσιμα μεγέθη τηλεμετρίας)
| Field Key | Τύπος | Περιγραφή |
| :--- | :--- | :--- |
| `power` | Float | Ενεργή ισχύς φόρτισης σε **kW** |
| `session_energy` | Float | Συνολική καταναλωθείσα ενέργεια τρέχουσας συνεδρίας σε **kWh** |
| `current_limit` | Float | Το ρυθμισμένο μέγιστο όριο ρεύματος σε **Amperes (A)** |
| `online` | Boolean | **`true`** αν ο φορτιστής είναι Online (ενεργός), **`false`** αν είναι Offline |
| `is_occupied` | Boolean | **`true`** αν υπάρχει συνδεδεμένο όχημα στην πρίζα της θέσης |
| `is_charged` | Boolean | **`true`** αν η φόρτιση του οχήματος έχει ολοκληρωθεί πλήρως |
| `is_offline` | Boolean | Αντίστροφη κατάσταση σύνδεσης (*χρησιμοποιήστε το `online` για ευκολότερη λογική*) |

---

## ⏱️ Queries Κατάστασης Πραγματικού Χρόνου (Table Panels)

Αυτά τα ερωτήματα είναι βελτιστοποιημένα για απεικόνιση σε **Grafana Table** (βεβαιωθείτε ότι έχετε επιλέξει **Format as: Table** στον Query editor του Grafana).

### Α. Γενικός Πίνακας Όλων των Θέσεων
Εμφανίζει την πλήρη τρέχουσα κατάσταση για όλους τους φορτιστές και τις θέσεις παγκοσμίως:
```sql
SELECT last("online") AS "Online",
       last("is_occupied") AS "Συνδεδεμένο",
       last("is_charged") AS "Ολοκληρώθηκε",
       last("power") AS "Ισχύς (kW)",
       last("session_energy") AS "Ενέργεια (kWh)",
       last("current_limit") AS "Όριο (A)"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### Β. Μόνο Συνδεδεμένα Οχήματα (Κρύβει τις κενές θέσεις)
Εμφανίζει μόνο τις θέσεις στις οποίες υπάρχει αυτοκίνητο στην πρίζα αυτή τη στιγμή:
```sql
SELECT last("is_charged") AS "Ολοκληρώθηκε",
       last("power") AS "Ισχύς (kW)",
       last("session_energy") AS "Ενέργεια (kWh)",
       last("current_limit") AS "Όριο (A)"
FROM "smart_ev"
WHERE "is_occupied" = true AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### Γ. Μόνο Οχήματα που Ολοκλήρωσαν τη Φόρτιση
Εμφανίζει μόνο τα οχήματα που έχουν τελειώσει τη φόρτιση αλλά παραμένουν συνδεδεμένα στη θέση τους:
```sql
SELECT last("session_energy") AS "Ενέργεια (kWh)",
       last("power") AS "Ισχύς (kW)"
FROM "smart_ev"
WHERE "is_occupied" = true AND "is_charged" = true AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

### Δ. Μόνο Φορτιστές Εκτός Σύνδεσης (Offline)
Εντοπίζει άμεσα αν κάποιος φορτιστής έχει χάσει την επικοινωνία του με το σύστημα:
```sql
SELECT last("online") AS "Online"
FROM "smart_ev"
WHERE "online" = false AND $timeFilter
GROUP BY "zone_id", "charger_id", "spot"
```

---

## 📈 Queries Ιστορικού & Διαγραμμάτων (Time-Series Panels)

Αυτά τα ερωτήματα είναι βελτιστοποιημένα για **Time-Series Graph** panels (επιλέξτε **Format as: Time Series** στον Query editor).

### Α. Συνολική Ισχύς Φόρτισης ανά Όροφο στο Χρόνο
Εμφανίζει σε διάγραμμα τη συνολική ζήτηση ισχύος (kW) ανά όροφο (zone_id):
```sql
SELECT sum("power") AS "Ισχύς Ορόφου"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY time($__interval), "zone_id" fill(0)
```

### Β. Όριο Ρεύματος έναντι Πραγματικής Ισχύος (π.χ. για τον φορτιστή `victron`)
Συγκρίνει την πραγματική ισχύ φόρτισης (kW) με το καθορισμένο όριο ρεύματος (Amperes) στο πέρασμα του χρόνου:
```sql
SELECT mean("power") AS "Πραγματική Ισχύς (kW)", 
       mean("current_limit") AS "Όριο (A)"
FROM "smart_ev"
WHERE "charger_id" = 'victron' AND $timeFilter
GROUP BY time($__interval) fill(null)
```

### Γ. Συνολική Ημερήσια Καταναλωθείσα Ενέργεια (kWh) ανά Φορτιστή
Εμφανίζει την ενέργεια που καταναλώθηκε ανά 24 ώρες για κάθε θέση φόρτισης:
```sql
SELECT max("session_energy") AS "Ημερήσια Ενέργεια"
FROM "smart_ev"
WHERE $timeFilter
GROUP BY time(24h), "charger_id", "spot" fill(0)
```

---

## 🎨 Συμβουλές Σχεδίασης στο Grafana

Για να δώσετε μια εξαιρετικά premium αισθητική στα panels σας:

### 1. Value Mapping (Μετατροπή Booleans σε Λεκτικά & Εικονίδια)
Στις ρυθμίσεις **Value mappings** στη δεξιά στήλη του Grafana panel, προσθέστε τους εξής κανόνες:
* **Για το `online`:**
  * `true` $\rightarrow$ **`Online 🟢`**
  * `false` $\rightarrow$ **`Offline 🔴`**
* **Για το `is_occupied` (Συνδεδεμένο):**
  * `true` $\rightarrow$ **`Connected 🔌`**
  * `false` $\rightarrow$ **`Empty ⚪`**
* **Για το `is_charged` (Ολοκληρώθηκε):**
  * `true` $\rightarrow$ **`Completed 🔋`**
  * `false` $\rightarrow$ **`Charging ⚡`**

### 2. Thresholds (Χρωματικές Διαβαθμίσεις)
* **Για την ισχύ `power` (kW):**
  * Base $\rightarrow$ **Γκρι** (`0 kW`)
  * `> 0.1` $\rightarrow$ **Μπλε** ή **Πράσινο** (σημαίνει ότι φορτίζει ενεργά).
