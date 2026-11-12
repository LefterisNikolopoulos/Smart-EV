import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4 portrait;
    margin: 15mm 15mm 15mm 15mm;
    @bottom-right {
      content: "Σελίδα " counter(page) " / 8";
      font-size: 8pt;
      color: #666;
    }
  }
  body {
    font-family: 'DejaVu Sans', 'Liberation Sans', Helvetica, Arial, sans-serif;
    color: #2d3748;
    margin: 0;
    padding: 0;
    font-size: 9.5pt;
    line-height: 1.45;
  }
  .page {
    page-break-after: always;
    height: 260mm;
    position: relative;
    box-sizing: border-box;
  }
  .page:last-child {
    page-break-after: avoid;
  }
  .header-top {
    border-bottom: 2px solid #1e3d59;
    padding-bottom: 6px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  .brand-title {
    font-size: 11pt;
    font-weight: bold;
    color: #1e3d59;
    letter-spacing: 0.5px;
  }
  .brand-sub {
    font-size: 7.5pt;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .footer-bottom {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid #e2e8f0;
    padding-top: 5px;
    font-size: 7.5pt;
    color: #718096;
    display: flex;
    justify-content: space-between;
  }
  h1 { font-size: 18pt; color: #1e3d59; margin: 0 0 10px 0; }
  h2 { font-size: 14pt; color: #1e3d59; margin: 0 0 8px 0; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 4px; }
  h3 { font-size: 10.5pt; color: #2b6cb0; margin: 12px 0 6px 0; }
  
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin: 14px 0;
  }
  .kpi-card {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px;
    border-left: 3.5px solid #1e3d59;
  }
  .kpi-title { font-size: 7.5pt; color: #4a5568; text-transform: uppercase; font-weight: bold; }
  .kpi-val { font-size: 14pt; font-weight: bold; color: #1e3d59; margin: 3px 0; }
  .kpi-sub { font-size: 7pt; color: #718096; }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 8pt;
  }
  th {
    background: #1e3d59;
    color: #ffffff;
    font-weight: bold;
    text-align: left;
    padding: 5px 6px;
    font-size: 7.5pt;
  }
  td {
    padding: 4.5px 6px;
    border-bottom: 1px solid #e2e8f0;
  }
  tr:nth-child(even) { background: #f8fafc; }
  tr.highlight-fault { background: #fff5f5; color: #c53030; font-weight: bold; }
  .tag-ok { color: #22543d; font-weight: bold; }
  .tag-fail { color: #9b2c2c; font-weight: bold; }

  .chart-img {
    width: 100%;
    max-height: 82mm;
    object-fit: contain;
    margin: 6px 0;
    border-radius: 4px;
    border: 1px solid #edf2f7;
  }
  .cover-box {
    background: linear-gradient(135deg, #1e3d59 0%, #17b978 100%);
    color: white;
    padding: 30px;
    border-radius: 8px;
    margin-top: 30px;
    margin-bottom: 30px;
  }
  .cover-box h1 { color: white; font-size: 24pt; margin-bottom: 15px; }
  .cover-meta {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    background: rgba(255,255,255,0.12);
    padding: 15px;
    border-radius: 6px;
    margin-top: 20px;
    font-size: 9pt;
  }
</style>
</head>
<body>

<!-- PAGE 1: COVER -->
<div class="page">
  <div class="header-top">
    <div>
      <div class="brand-title">DegerHellas · Astradigital — Ενεργοσκόπιο</div>
      <div class="brand-sub">OCPP • Modbus • RFID Ορόφου • Dynamic Load Control • Επιμερισμός Κόστους</div>
    </div>
    <div style="font-size:8pt; color:#4a5568;">Βασιλίσσης Σοφίας 23Α, Αθήνα</div>
  </div>

  <div class="cover-box">
    <div style="font-size:11pt; text-transform:uppercase; letter-spacing:1.5px; opacity:0.9;">Μηνιαία Αναφορά Ενεργειακής Διαχείρισης</div>
    <h1>Φόρτιση Ηλεκτρικών Οχημάτων<br><span style="font-size:16pt; font-weight:normal; opacity:0.95;">ανά Όροφο, Πεδίο, Φορτιστή & Χρήστη</span></h1>
    <p style="font-size:10pt; line-height:1.6; opacity:0.95;">
      Ολοκληρωμένη αρχιτεκτονική Edge Computing τοπικού βιομηχανικού ελεγκτή με αδιάλειπτη λειτουργία, 
      πλήρη διασταύρωση υπομετρητών Legrand EMDX³, δυναμικό έλεγχο φορτίου (DLC) και αυτόματο επιμερισμό κοινοχρήστων.
    </p>
    <div class="cover-meta">
      <div><strong>Κτίριο:</strong> Kolonaki International Center</div>
      <div><strong>Περίοδος:</strong> Οκτώβριος 2026 (01/10 – 31/10)</div>
      <div><strong>Υποδομή:</strong> 36 Φορτιστές · 11 kW ανά σημείο</div>
      <div><strong>Ηλεκτρική Εγκατάσταση:</strong> 3 Επίπεδα × (9 + 3) Αναχωρήσεις · 850 kVA</div>
    </div>
  </div>

  <div style="margin-top: 25px; padding: 16px; background: #edf2f7; border-radius: 6px; font-size:8.5pt; color:#4a5568;">
    <strong>Προδιαγραφή Συστήματος:</strong><br>
    Η αναφορά παράγεται αυτόματα στο τέλος κάθε μήνα από την κεντρική μονάδα <strong>Solarbrain</strong> και την πλατφόρμα <strong>Ενεργοσκόπιο (energoskopio.gr)</strong>. 
    Τα δεδομένα συλλέγονται τοπικά στο κτίριο από τους 36 φορτιστές (OCPP / Modbus TCP), τους αναγνώστες RFID ορόφου και τους πιστοποιημένους μετρητές Legrand EMDX³. 
    Η Διαχείριση λαμβάνει την παρούσα αναφορά και αναλυτικά δεδομένα ανά 5 λεπτά σε CSV/Excel.
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Μεγάλου Αλεξάνδρου 169, Αγ. Ανάργυροι | Astradigital</div>
    <div>Σελίδα 1 / 8</div>
  </div>
</div>

<!-- PAGE 2: EXECUTIVE SUMMARY -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">1. Σύνοψη μήνα — Kolonaki International Center</div>
    <div class="brand-sub">Οκτώβριος 2026</div>
  </div>

  <p style="margin: 4px 0 10px 0; font-size:9pt;">
    Τον Οκτώβριο οι 36 φορτιστές παρέδωσαν <strong>9.597 kWh</strong> σε <strong>493 συνεδρίες</strong>. 
    Το κόστος ενέργειας προς επιμερισμό στα κοινόχρηστα είναι <strong>1.919,34 €</strong> (με παραδοχή 0,20 €/kWh).
  </p>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Ενέργεια φόρτισης</div>
      <div class="kpi-val">9.597 kWh</div>
      <div class="kpi-sub">36 φορτιστές σε λειτουργία</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Συνεδρίες φόρτισης</div>
      <div class="kpi-val">493</div>
      <div class="kpi-sub">71 κάρτες RFID σε χρήση</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Μέση ενέργεια / συνεδρία</div>
      <div class="kpi-val">19,5 kWh</div>
      <div class="kpi-sub">Μέση διάρκεια: 2,8 ώρες</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Κόστος προς επιμερισμό</div>
      <div class="kpi-val">1.919,34 €</div>
      <div class="kpi-sub">Με τιμολόγιο 0,20 €/kWh</div>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Μέγιστη ισχύς φόρτισης</div>
      <div class="kpi-val">170,9 kW</div>
      <div class="kpi-sub">Σύνολο 3 επιπέδων</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Μέγιστη ζήτηση κτιρίου</div>
      <div class="kpi-val">420,0 kW</div>
      <div class="kpi-sub">Όριο 420 kW · Χωρίς DLC 466 kW</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Μερίδιο Η/Ο στο κτίριο</div>
      <div class="kpi-val">7,9%</div>
      <div class="kpi-sub">Από 120.955 kWh κτιρίου</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Διαθεσιμότητα φορτιστών</div>
      <div class="kpi-val">100,0%</div>
      <div class="kpi-sub">1 συμβάν βλάβης (RCBO 6h)</div>
    </div>
  </div>

  <h3>Ανάλυση ανά επίπεδο στάθμευσης</h3>
  <table>
    <thead>
      <tr>
        <th>Επίπεδο</th>
        <th>Φορτιστές</th>
        <th>Ενέργεια (kWh)</th>
        <th>Συνεδρίες</th>
        <th>Μέγιστη Ισχύς (kW)</th>
        <th>Μερίδιο (%)</th>
        <th>Κόστος (€)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Επίπεδο -1</strong></td>
        <td>12</td>
        <td>3.216,0</td>
        <td>167</td>
        <td>69,8 kW</td>
        <td>33,5%</td>
        <td>643,28 €</td>
      </tr>
      <tr>
        <td><strong>Επίπεδο -2</strong></td>
        <td>12</td>
        <td>2.985,0</td>
        <td>155</td>
        <td>69,7 kW</td>
        <td>31,1%</td>
        <td>597,06 €</td>
      </tr>
      <tr>
        <td><strong>Επίπεδο -3</strong></td>
        <td>12</td>
        <td>3.395,0</td>
        <td>171</td>
        <td>73,4 kW</td>
        <td>35,4%</td>
        <td>678,98 €</td>
      </tr>
      <tr style="background:#edf2f7; font-weight:bold;">
        <td>ΣΥΝΟΛΟ</td>
        <td>36</td>
        <td>9.596,0</td>
        <td>493</td>
        <td>170,9 kW</td>
        <td>100,0%</td>
        <td>1.919,34 €</td>
      </tr>
    </tbody>
  </table>

  <div style="font-size:7.5pt; color:#718096; margin-top:8px;">
    * Σημείωση: Η ικανότητα κάθε Πεδίου Διανομής (γενικός διακόπτης 250A) είναι ≈173 kVA, υπερκαλύπτοντας τη μέγιστη ισχύ επιπέδου (73,4 kW).
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 2 / 8</div>
  </div>
</div>

<!-- PAGE 3: CONSUMPTION PER FLOOR & PROFILES -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">2. Κατανάλωση ανά όροφο & ωριαία προφίλ</div>
    <div class="brand-sub">Οκτώβριος 2026</div>
  </div>

  <p style="font-size:8.5pt; margin-bottom:4px;">
    Η κατανάλωση μοιράζεται ισόρροπα στα τρία επίπεδα. Η αιχμή εμφανίζεται τις εργάσιμες ημέρες με την άφιξη των στελεχών μεταξύ 08:00–10:00.
  </p>

  <img src="chart_daily_energy.png" class="chart-img">
  <img src="chart_hourly_profile.png" class="chart-img">

  <div style="font-size:7.5pt; color:#718096;">
    * Οι καμπύλες βασίζονται σε καταγραφές Modbus TCP ανά 1 δευτερόλεπτο και αποθήκευση σε τοπική βάση χρονοσειρών.
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 3 / 8</div>
  </div>
</div>

<!-- PAGE 4: DETAILED 36 CHARGERS TABLE -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">3. Ανάλυση ανά πεδίο & ανά φορτιστή (36 Σημεία)</div>
    <div class="brand-sub">Π1 = Πεδίο Διανομής (9 αναχωρήσεις) · Δ1 = Δορυφορικό (3 αναχωρήσεις)</div>
  </div>

  <table style="font-size:7pt;">
    <thead>
      <tr>
        <th>Κωδικός</th>
        <th>Πεδίο</th>
        <th>Μισθωτής / Εταιρία</th>
        <th>Κάρτες</th>
        <th>kWh</th>
        <th>Συνεδρ.</th>
        <th>Ώρες</th>
        <th>Διαθεσιμότητα</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>-1/Π1/01</td><td>Πεδίο Διανομής</td><td>Εταιρία Γ</td><td>3</td><td>197,0</td><td>13</td><td>29,4</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/02</td><td>Πεδίο Διανομής</td><td>Εταιρία Α</td><td>1</td><td>416,8</td><td>18</td><td>67,3</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/03</td><td>Πεδίο Διανομής</td><td>Εταιρία Ε</td><td>1</td><td>244,9</td><td>14</td><td>33,4</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/04</td><td>Πεδίο Διανομής</td><td>Εταιρία Δ</td><td>1</td><td>361,7</td><td>18</td><td>50,8</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/05</td><td>Πεδίο Διανομής</td><td>Εταιρία Β</td><td>2</td><td>226,4</td><td>14</td><td>23,8</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/06</td><td>Πεδίο Διανομής</td><td>Εταιρία Γ</td><td>3</td><td>387,8</td><td>21</td><td>52,5</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/07</td><td>Πεδίο Διανομής</td><td>Εταιρία Δ</td><td>2</td><td>73,0</td><td>5</td><td>17,2</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/08</td><td>Πεδίο Διανομής</td><td>Εταιρία Β</td><td>1</td><td>337,0</td><td>18</td><td>43,7</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Π1/09</td><td>Πεδίο Διανομής</td><td>Εταιρία Δ</td><td>2</td><td>320,0</td><td>15</td><td>35,0</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Δ1/10</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Β</td><td>2</td><td>379,7</td><td>17</td><td>58,1</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Δ1/11</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Β</td><td>3</td><td>168,5</td><td>10</td><td>26,9</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-1/Δ1/12</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Γ</td><td>2</td><td>103,7</td><td>4</td><td>12,8</td><td class="tag-ok">100,0%</td></tr>

      <tr><td>-2/Π1/01</td><td>Πεδίο Διανομής</td><td>Εταιρία ΣΤ</td><td>2</td><td>213,8</td><td>10</td><td>27,7</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/02</td><td>Πεδίο Διανομής</td><td>Εταιρία Γ</td><td>2</td><td>266,9</td><td>14</td><td>44,8</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/03</td><td>Πεδίο Διανομής</td><td>Εταιρία Β</td><td>2</td><td>291,9</td><td>14</td><td>46,2</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/04</td><td>Πεδίο Διανομής</td><td>Εταιρία Α</td><td>1</td><td>262,7</td><td>15</td><td>37,9</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/05</td><td>Πεδίο Διανομής</td><td>Εταιρία Ζ</td><td>2</td><td>133,3</td><td>5</td><td>13,8</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/06</td><td>Πεδίο Διανομής</td><td>Εταιρία Γ</td><td>1</td><td>335,5</td><td>19</td><td>41,2</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/07</td><td>Πεδίο Διανομής</td><td>Εταιρία Ε</td><td>2</td><td>376,2</td><td>21</td><td>60,2</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/08</td><td>Πεδίο Διανομής</td><td>Εταιρία Β</td><td>2</td><td>227,5</td><td>12</td><td>30,1</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Π1/09</td><td>Πεδίο Διανομής</td><td>Εταιρία Α</td><td>1</td><td>360,0</td><td>18</td><td>60,5</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-2/Δ1/10</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Α</td><td>2</td><td>129,4</td><td>10</td><td>16,6</td><td class="tag-ok">100,0%</td></tr>
      <tr class="highlight-fault"><td>-2/Δ1/11</td><td>Δορυφορικό Πεδίο</td><td>Διαχείριση κτιρίου</td><td>1</td><td>182,5</td><td>8</td><td>21,2</td><td class="tag-fail">99,2% (Βλάβη)</td></tr>
      <tr><td>-2/Δ1/12</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Α</td><td>3</td><td>205,8</td><td>9</td><td>37,0</td><td class="tag-ok">100,0%</td></tr>

      <tr><td>-3/Π1/01</td><td>Πεδίο Διανομής</td><td>Εταιρία Β</td><td>2</td><td>222,0</td><td>12</td><td>29,3</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/02</td><td>Πεδίο Διανομής</td><td>Εταιρία Ε</td><td>3</td><td>211,4</td><td>11</td><td>27,7</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/03</td><td>Πεδίο Διανομής</td><td>Εταιρία Α</td><td>3</td><td>242,5</td><td>13</td><td>34,3</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/04</td><td>Πεδίο Διανομής</td><td>Εταιρία Ζ</td><td>1</td><td>166,1</td><td>11</td><td>28,8</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/05</td><td>Πεδίο Διανομής</td><td>Εταιρία ΣΤ</td><td>3</td><td>112,3</td><td>9</td><td>16,1</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/06</td><td>Πεδίο Διανομής</td><td>Διαχείριση κτιρίου</td><td>1</td><td>375,0</td><td>17</td><td>56,0</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/07</td><td>Πεδίο Διανομής</td><td>Εταιρία Ε</td><td>3</td><td>360,8</td><td>16</td><td>48,0</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/08</td><td>Πεδίο Διανομής</td><td>Εταιρία ΣΤ</td><td>3</td><td>474,3</td><td>23</td><td>69,3</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Π1/09</td><td>Πεδίο Διανομής</td><td>Εταιρία Ζ</td><td>1</td><td>247,9</td><td>13</td><td>29,9</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Δ1/10</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία ΣΤ</td><td>3</td><td>474,9</td><td>26</td><td>80,3</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Δ1/11</td><td>Δορυφορικό Πεδίο</td><td>Εταιρία Δ</td><td>2</td><td>267,1</td><td>13</td><td>37,1</td><td class="tag-ok">100,0%</td></tr>
      <tr><td>-3/Δ1/12</td><td>Δορυφορικό Πεδίο</td><td>Διαχείριση κτιρίου</td><td>2</td><td>240,6</td><td>7</td><td>30,6</td><td class="tag-ok">100,0%</td></tr>
    </tbody>
  </table>

  <div style="font-size:7.5pt; color:#c53030; font-weight:bold; margin-top:4px;">
    * Επισημασμένη γραμμή: Βλάβη 16/10 10:00–16:00 (πτώση ασφαλειοδιακόπτη RCBO). Ειδοποιήθηκε αυτόματα η Reception και το συνεργείο συντήρησης.
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 4 / 8</div>
  </div>
</div>

<!-- PAGE 5: PER COMPANY & USER RFID BREAKDOWN -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">4. Ανάλυση ανά εταιρία & χρήστη RFID (Κοινόχρηστα)</div>
    <div class="brand-sub">Οκτώβριος 2026</div>
  </div>

  <p style="font-size:8.5pt; margin-bottom:4px;">
    Κάθε kWh αποδίδεται επακριβώς στην κάρτα RFID που ενεργοποίησε τη φόρτιση και στην εταιρία του κατόχου της. Έτσι το ποσό περνά απευθείας στα κοινόχρηστα.
  </p>

  <img src="chart_company_kwh.png" style="width:100%; max-height:48mm; object-fit:contain;">

  <table style="font-size:7.5pt; margin-top:4px;">
    <thead>
      <tr>
        <th>Εταιρία / Μισθωτής</th>
        <th>Φορτιστές</th>
        <th>Κάρτες</th>
        <th>Συνεδρίες</th>
        <th>kWh</th>
        <th>Μερίδιο</th>
        <th>Χρέωση Κοινοχρήστων (€)</th>
      </tr>
    </thead>
    <tbody>
      <tr><td><strong>Εταιρία Β</strong></td><td>7</td><td>14</td><td>97</td><td>1.853,0</td><td>19,3%</td><td><strong>370,58 €</strong></td></tr>
      <tr><td><strong>Εταιρία Α</strong></td><td>6</td><td>11</td><td>83</td><td>1.617,0</td><td>16,9%</td><td><strong>323,42 €</strong></td></tr>
      <tr><td><strong>Εταιρία Γ</strong></td><td>5</td><td>11</td><td>71</td><td>1.291,0</td><td>13,5%</td><td><strong>258,18 €</strong></td></tr>
      <tr><td><strong>Εταιρία ΣΤ</strong></td><td>4</td><td>11</td><td>68</td><td>1.275,0</td><td>13,3%</td><td><strong>255,06 €</strong></td></tr>
      <tr><td><strong>Εταιρία Ε</strong></td><td>4</td><td>9</td><td>62</td><td>1.193,0</td><td>12,4%</td><td><strong>238,66 €</strong></td></tr>
      <tr><td><strong>Εταιρία Δ</strong></td><td>4</td><td>7</td><td>51</td><td>1.022,0</td><td>10,6%</td><td><strong>204,38 €</strong></td></tr>
      <tr><td><strong>Διαχείριση κτιρίου</strong></td><td>3</td><td>4</td><td>32</td><td>798,0</td><td>8,3%</td><td><strong>159,61 €</strong></td></tr>
      <tr><td><strong>Εταιρία Ζ</strong></td><td>3</td><td>4</td><td>29</td><td>547,0</td><td>5,7%</td><td><strong>109,45 €</strong></td></tr>
      <tr style="background:#edf2f7; font-weight:bold;">
        <td>ΣΥΝΟΛΟ</td><td>36</td><td>71</td><td>493</td><td>9.596,0</td><td>100%</td><td>1.919,34 €</td>
      </tr>
    </tbody>
  </table>

  <h3 style="margin-top:6px;">Παράδειγμα ανάλυσης χρηστών — Εταιρία Β (14 Κάρτες)</h3>
  <table style="font-size:7pt;">
    <thead>
      <tr><th>Χρήστης</th><th>Κάρτα RFID</th><th>Θέση Φορτιστή</th><th>Συνεδρίες</th><th>kWh</th><th>Ώρες</th><th>Κόστος (€)</th></tr>
    </thead>
    <tbody>
      <tr><td>Χρήστης B-03</td><td>RFID-9009</td><td>-1/Π1/08</td><td>18</td><td>337,0</td><td>43,7</td><td>67,40 €</td></tr>
      <tr><td>Χρήστης B-04</td><td>RFID-9246</td><td>-1/Δ1/10</td><td>12</td><td>287,2</td><td>41,1</td><td>57,44 €</td></tr>
      <tr><td>Χρήστης B-09</td><td>RFID-9043</td><td>-2/Π1/03</td><td>8</td><td>156,8</td><td>18,7</td><td>31,36 €</td></tr>
      <tr><td>Χρήστης B-12</td><td>RFID-6787</td><td>-2/Π1/08</td><td>6</td><td>138,8</td><td>17,1</td><td>27,76 €</td></tr>
      <tr><td>Χρήστης B-10</td><td>RFID-4404</td><td>-2/Π1/03</td><td>6</td><td>135,0</td><td>27,6</td><td>27,00 €</td></tr>
      <tr><td>Χρήστης B-02</td><td>RFID-7391</td><td>-1/Π1/05</td><td>7</td><td>118,7</td><td>13,1</td><td>23,74 €</td></tr>
      <tr><td>Χρήστης B-13</td><td>RFID-5635</td><td>-3/Π1/01</td><td>5</td><td>116,2</td><td>11,0</td><td>23,24 €</td></tr>
      <tr><td>Χρήστης B-01</td><td>RFID-5870</td><td>-1/Π1/05</td><td>7</td><td>107,7</td><td>10,7</td><td>21,54 €</td></tr>
      <tr><td>Χρήστης B-14</td><td>RFID-4585</td><td>-3/Π1/01</td><td>7</td><td>105,7</td><td>18,3</td><td>21,14 €</td></tr>
      <tr><td>Χρήστης B-05</td><td>RFID-1628</td><td>-1/Δ1/10</td><td>5</td><td>92,5</td><td>17,0</td><td>18,50 €</td></tr>
    </tbody>
  </table>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 5 / 8</div>
  </div>
</div>

<!-- PAGE 6: DYNAMIC LOAD CONTROL (DLC) -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">5. Δυναμική Διαχείριση Φορτίου (Dynamic Load Control)</div>
    <div class="brand-sub">Όριο-Στόχος Κτιρίου: 420 kW · Χωρίς DLC: 466 kW</div>
  </div>

  <p style="font-size:8.5pt; margin-bottom:4px;">
    Το Solarbrain μετρά συνεχώς τη ζήτηση του κτιρίου και μοιράζει στους φορτιστές μόνο την ισχύ που περισσεύει. 
    Ο περιορισμός ενεργοποιήθηκε σε <strong>17 ημέρες</strong>, συνολικά <strong>1.385 λεπτά</strong>, χωρίς να μείνει κανένα όχημα αφόρτιστο.
  </p>

  <img src="chart_dlc_curve.png" class="chart-img">

  <h3>Μεγαλύτερα συμβάντα περιορισμού (Throttling Events)</h3>
  <table style="font-size:7.5pt;">
    <thead>
      <tr>
        <th>Ημέρα</th>
        <th>Χρονικό Διάστημα</th>
        <th>Διάρκεια (min)</th>
        <th>Ζήτηση Η/Ο (kW)</th>
        <th>Διαθέσιμη Ισχύς (kW)</th>
        <th>Μείωση (%)</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>30/10</td><td>10:05 – 12:35</td><td>150 min</td><td>143,4 kW</td><td>51,1 kW</td><td style="color:#c53030; font-weight:bold;">−64%</td></tr>
      <tr><td>02/10</td><td>09:20 – 11:10</td><td>110 min</td><td>187,3 kW</td><td>68,9 kW</td><td style="color:#c53030; font-weight:bold;">−63%</td></tr>
      <tr><td>08/10</td><td>10:20 – 11:50</td><td>90 min</td><td>117,7 kW</td><td>50,0 kW</td><td style="color:#c53030; font-weight:bold;">−58%</td></tr>
      <tr><td>12/10</td><td>10:50 – 12:20</td><td>90 min</td><td>106,7 kW</td><td>53,4 kW</td><td style="color:#c53030; font-weight:bold;">−50%</td></tr>
      <tr><td>15/10</td><td>10:00 – 11:30</td><td>90 min</td><td>132,2 kW</td><td>64,0 kW</td><td style="color:#c53030; font-weight:bold;">−52%</td></tr>
      <tr><td>29/10</td><td>09:45 – 11:15</td><td>90 min</td><td>168,8 kW</td><td>75,6 kW</td><td style="color:#c53030; font-weight:bold;">−55%</td></tr>
      <tr><td>09/10</td><td>11:20 – 12:45</td><td>85 min</td><td>81,2 kW</td><td>52,5 kW</td><td style="color:#c53030; font-weight:bold;">−35%</td></tr>
      <tr><td>01/10</td><td>10:35 – 11:50</td><td>75 min</td><td>110,4 kW</td><td>60,5 kW</td><td style="color:#c53030; font-weight:bold;">−45%</td></tr>
    </tbody>
  </table>

  <div style="font-size:7.5pt; color:#718096; margin-top:6px;">
    * Η ισχύς μοιράζεται αναλογικά και ισότιμα σε όλους τους ενεργούς φορτιστές σε πραγματικό χρόνο (< 500ms).
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 6 / 8</div>
  </div>
</div>

<!-- PAGE 7: SECURITY AUDIT TRAIL & RECEPTION -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">6. Πρόσβαση, Ασφάλεια & Συμβάντα (Audit Trail)</div>
    <div class="brand-sub">Αλληλασφάλιση 4 Βημάτων · Ειδοποίηση Reception σε Πραγματικό Χρόνο</div>
  </div>

  <p style="font-size:8.5pt; margin-bottom:4px;">
    Η φόρτιση ξεκινά αυστηρά με την ακολουθία: <em>Σύνδεση καλωδίου (CP B) &rarr; Ανάγνωση RFID ορόφου &rarr; Επαλήθευση αντιστοίχισης χρήστη-φορτιστή &rarr; Ενεργοποίηση & ειδοποίηση Reception</em>.
  </p>

  <h3>Απόσπασμα αρχείου πρόσβασης — 21/10/2026</h3>
  <table style="font-size:7pt;">
    <thead>
      <tr>
        <th>Ώρα</th>
        <th>Χρήστης</th>
        <th>Κάρτα</th>
        <th>Φορτιστής</th>
        <th>Βήμα Ελέγχου</th>
        <th>Λεπτομέρεια</th>
        <th>Αποτέλεσμα</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>07:42:10</td><td>D-02</td><td>RFID-3445</td><td>-1/Π1/07</td><td>Σύνδεση καλωδίου</td><td>Ανίχνευση οχήματος (CP state B)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>07:42:31</td><td>D-02</td><td>RFID-3445</td><td>-1/Π1/07</td><td>Ανάγνωση RFID</td><td>Αναγνώστης Επιπέδου -1</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>07:42:32</td><td>D-02</td><td>RFID-3445</td><td>-1/Π1/07</td><td>Επαλήθευση ζεύγους</td><td>Τοπική βάση (Edge Offline)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>07:42:33</td><td>D-02</td><td>RFID-3445</td><td>-1/Π1/07</td><td>Ενεργοποίηση φόρτισης</td><td>Ειδοποίηση Reception (σε αναμονή sync)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>08:05:14</td><td>Z-01</td><td>RFID-9687</td><td>-2/Π1/05</td><td>Σύνδεση καλωδίου</td><td>Ανίχνευση οχήματος (CP state B)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>08:05:40</td><td>Z-01</td><td>RFID-9687</td><td>-2/Π1/05</td><td>Ανάγνωση RFID</td><td>Αναγνώστης Επιπέδου -2</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>08:05:41</td><td>Z-01</td><td>RFID-9687</td><td>-2/Π1/05</td><td>Επαλήθευση ζεύγους</td><td>Τοπική βάση (Edge Offline)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr><td>08:05:42</td><td>Z-01</td><td>RFID-9687</td><td>-2/Π1/05</td><td>Ενεργοποίηση φόρτισης</td><td>Ειδοποίηση Reception (σε αναμονή sync)</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
      <tr style="background:#ebf8ff;"><td>08:56:03</td><td>Σύστημα</td><td>—</td><td>Κεντρικός Controller</td><td>Αποκατάσταση Internet</td><td>Αυτόματος συγχρονισμός 9 συνεδριών</td><td style="color:#2b6cb0; font-weight:bold;">ℹ Πληροφορία</td></tr>
      <tr class="highlight-fault"><td>09:12:18</td><td>S-07</td><td>RFID-5429</td><td>-3/Π1/08</td><td>Ανάγνωση RFID</td><td>Καλώδιο συνδεδεμένο σε άλλο φορτιστή</td><td class="tag-fail">✖ Απορρίφθηκε</td></tr>
      <tr class="highlight-fault"><td>09:12:19</td><td>S-07</td><td>RFID-5429</td><td>-3/Π1/08</td><td>Απόρριψη ενεργοποίησης</td><td>Μήνυμα: «Λάθος θέση φόρτισης»</td><td class="tag-fail">✖ Απορρίφθηκε</td></tr>
      <tr><td>09:13:02</td><td>S-07</td><td>RFID-5429</td><td>-3/Π1/08</td><td>Ενεργοποίηση φόρτισης</td><td>Ορθός φορτιστής μετά από νέα σύνδεση</td><td class="tag-ok">✔ Εγκρίθηκε</td></tr>
    </tbody>
  </table>

  <div style="display:flex; gap:12px; margin-top:8px;">
    <div style="flex:1;">
      <h3>Απορριφθείσες προσπάθειες μήνα (Σύνολο: 13)</h3>
      <table style="font-size:7pt;">
        <thead><tr><th>Αιτία Απόρριψης</th><th>Πλήθος</th></tr></thead>
        <tbody>
          <tr><td>Κάρτα σε φορτιστή άλλου χρήστη</td><td>3</td></tr>
          <tr><td>Καλώδιο σε λάθος φορτιστή</td><td>7</td></tr>
          <tr><td>Μη καταχωρημένη κάρτα RFID</td><td>2</td></tr>
          <tr><td>Απενεργοποιημένη κάρτα (αποχώρηση)</td><td>1</td></tr>
        </tbody>
      </table>
    </div>
    <div style="flex:1;">
      <h3>Λειτουργία Offline (Χωρίς Internet)</h3>
      <div style="background:#f7fafc; border:1px solid #e2e8f0; padding:8px; border-radius:4px; font-size:7.5pt;">
        Στις <strong>21/10, 07:40–08:55</strong>, το κτίριο έμεινε χωρίς εξωτερική σύνδεση internet.<br>
        Ο τοπικός βιομηχανικός ελεγκτής εκτέλεσε απρόσκοπτα <strong>9 φορτίσεις</strong> από την τοπική βάση. 
        Με την επαναφορά, όλες οι εγγραφές συγχρονίστηκαν αυτόματα. <strong>Καμία απώλεια δεδομένων.</strong>
      </div>
    </div>
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο</div>
    <div>Σελίδα 7 / 8</div>
  </div>
</div>

<!-- PAGE 8: LEGRAND EMDX3 SUBMETERS RECONCILIATION -->
<div class="page">
  <div class="header-top">
    <div class="brand-title">7. Μέτρηση ενέργειας & διασταύρωση Legrand EMDX³</div>
    <div class="brand-sub">Συνολικό Μερίδιο Η/Ο στο Κτίριο: 7,9% (9.597 kWh / 120.955 kWh)</div>
  </div>

  <img src="chart_building_share.png" class="chart-img">

  <h3>Πίνακας Πιστοποιημένων Μετρητών Legrand EMDX³</h3>
  <table style="font-size:7.5pt;">
    <thead>
      <tr>
        <th>Κωδικός</th>
        <th>Θέση Μετρητή</th>
        <th>Επίπεδο</th>
        <th>Καταγραφή Μήνα (kWh)</th>
        <th>Σημειώσεις & Διασταύρωση</th>
      </tr>
    </thead>
    <tbody>
      <tr style="background:#edf2f7; font-weight:bold;">
        <td>Μ-0</td>
        <td>Γενική παροχή κτιρίου</td>
        <td>Πεδίο Χ.Τ. (Ισόγειο)</td>
        <td>120.955 kWh</td>
        <td>Συνολική κατανάλωση κτιρίου Kolonaki Center</td>
      </tr>
      <tr>
        <td><strong>Μ-1</strong></td>
        <td>Πεδίο Διανομής Φόρτισης -1</td>
        <td>Επίπεδο -1</td>
        <td>3.216 kWh</td>
        <td>Περιλαμβάνει και το δορυφορικό πεδίο Δ1</td>
      </tr>
      <tr>
        <td><strong>Μ-2</strong></td>
        <td>Πεδίο Διανομής Φόρτισης -2</td>
        <td>Επίπεδο -2</td>
        <td>2.986 kWh</td>
        <td>Περιλαμβάνει και το δορυφορικό πεδίο Δ1 (Απόκλιση < 0.03%)</td>
      </tr>
      <tr>
        <td><strong>Μ-3</strong></td>
        <td>Πεδίο Διανομής Φόρτισης -3</td>
        <td>Επίπεδο -3</td>
        <td>3.395 kWh</td>
        <td>Περιλαμβάνει και το δορυφορικό πεδίο Δ1</td>
      </tr>
      <tr>
        <td>Μ-1Δ</td>
        <td>Δορυφορικό Πεδίο -1</td>
        <td>Επίπεδο -1</td>
        <td>652 kWh</td>
        <td>Υπομετρητής αναχωρήσεων 10, 11, 12</td>
      </tr>
      <tr>
        <td>Μ-2Δ</td>
        <td>Δορυφορικό Πεδίο -2</td>
        <td>Επίπεδο -2</td>
        <td>518 kWh</td>
        <td>Υπομετρητής αναχωρήσεων 10, 11, 12</td>
      </tr>
      <tr>
        <td>Μ-3Δ</td>
        <td>Δορυφορικό Πεδίο -3</td>
        <td>Επίπεδο -3</td>
        <td>983 kWh</td>
        <td>Υπομετρητής αναχωρήσεων 10, 11, 12</td>
      </tr>
    </tbody>
  </table>

  <div style="background:#f7fafc; border:1px solid #e2e8f0; padding:10px; border-radius:6px; font-size:8pt; margin-top:8px;">
    <strong>Διασταύρωση & Διαφάνεια Χρεώσεων (Reconciliation):</strong><br>
    Οι ενδείξεις των ενσωματωμένων μετρητών των φορτιστών διασταυρώνονται σε πραγματικό χρόνο με τους πιστοποιημένους μετρητές MID Legrand EMDX³. 
    Η απόκλιση του μηνός ήταν <strong>&plusmn;0,02%</strong>, εξασφαλίζοντας απόλυτη νομική και λογιστική εγκυρότητα στην έκδοση κοινοχρήστων.
  </div>

  <div class="footer-bottom">
    <div>DegerHellas · Astradigital — Ενεργοσκόπιο (energoskopio.gr)</div>
    <div>Σελίδα 8 / 8</div>
  </div>
</div>

</body>
</html>
"""

html_path = "/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_monthly_report.html"
pdf_path = "/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_monthly_report_oct2026.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML report saved. Converting to PDF via headless Google Chrome...")
cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--print-to-pdf-no-header",
    f"--print-to-pdf={pdf_path}",
    html_path
]
subprocess.run(cmd, check=True)
print(f"Generated PDF successfully: {pdf_path}")
