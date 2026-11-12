import os
import sys
import json
import base64
import subprocess
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 1. Load Configurations and Histories
cfg_file = '/home/smartev/smart-parking-config.json' if os.path.exists('/home/smartev/smart-parking-config.json') else '/home/lefteris/Documents/DegerHellas/Smart Ev/smart-parking-config.json'
hist_file = '/home/smartev/charging-history.json' if os.path.exists('/home/smartev/charging-history.json') else '/home/lefteris/Documents/DegerHellas/Smart Ev/charging-history.json'
logo_file = '/home/lefteris/Documents/DegerHellas/Smart Ev/degerhellas_logo.png'

with open(cfg_file, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

with open(hist_file, 'r', encoding='utf-8') as f:
    raw_history = json.load(f)

logo_b64 = ""
if os.path.exists(logo_file):
    with open(logo_file, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode('utf-8')

building_name = cfg.get('PROJECT_NAME', 'Kolonaki International Center')
building_addr = cfg.get('PROJECT_ADDRESS', 'Βασιλίσσης Σοφίας 23Α, Αθήνα')
tariff_kwh = float(cfg.get('TARIFF_EUR_PER_KWH', 0.20))
max_power_kw = float(cfg.get('TOTAL_POWER', cfg.get('maxPower', 420.0)))

# Map user name / ID to company
user_company_map = {}
for uid, u in cfg.get('USERS', {}).items():
    uname = u.get('name', '').strip()
    ucomp = u.get('company', '').strip() or 'Διαχείριση Κτιρίου'
    if uname:
        user_company_map[uname] = ucomp
    user_company_map[uid] = ucomp

# Process History
df = pd.DataFrame(raw_history)
if df.empty:
    print("Warning: history is empty!")
    sys.exit(1)

df['energyKWh'] = pd.to_numeric(df['energyKWh'], errors='coerce').fillna(0.0)
df['durationMinutes'] = pd.to_numeric(df['durationMinutes'], errors='coerce').fillna(0)

# Filter out zero sessions if they were just plug-in disconnect without charging
df_charged = df[df['energyKWh'] > 0.05].copy()
if df_charged.empty:
    df_charged = df.copy()

df_charged['company'] = df_charged['name'].map(user_company_map).fillna('Κοινόχρηστο / Επισκέπτες')
df_charged['cost_eur'] = df_charged['energyKWh'] * tariff_kwh

total_kwh = float(df_charged['energyKWh'].sum())
total_sessions = len(df_charged)
total_duration_hours = float(df_charged['durationMinutes'].sum()) / 60.0
avg_kwh = (total_kwh / total_sessions) if total_sessions > 0 else 0.0
avg_dur_h = (total_duration_hours / total_sessions) if total_sessions > 0 else 0.0
total_cost_eur = total_kwh * tariff_kwh

# Parse dates
df_charged['dt'] = pd.to_datetime(df_charged['timestamp'], errors='coerce')
valid_dates = df_charged['dt'].dropna()
if not valid_dates.empty:
    min_date_str = valid_dates.min().strftime('%d/%m/%Y')
    max_date_str = valid_dates.max().strftime('%d/%m/%Y')
    period_str = f"{min_date_str} – {max_date_str}"
else:
    period_str = "Τρέχουσα Περίοδος 2026"

# 2. Charts Generation
chart_dir = "/home/lefteris/Documents/DegerHellas/Smart Ev"
os.makedirs(chart_dir, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8

# Chart 1: Company Energy Bar Chart
comp_grp = df_charged.groupby('company').agg(
    kwh=('energyKWh', 'sum'),
    sessions=('energyKWh', 'count'),
    hours=('durationMinutes', lambda x: x.sum() / 60.0),
    cost=('cost_eur', 'sum')
).reset_index().sort_values('kwh', ascending=True)

fig, ax = plt.subplots(figsize=(8.5, 3.2), dpi=200)
y_pos = np.arange(len(comp_grp))
bars = ax.barh(y_pos, comp_grp['kwh'], color='#1e3d59', height=0.55)
ax.set_yticks(y_pos)
ax.set_yticklabels(comp_grp['company'], fontsize=9, fontweight='bold', color='#1e293b')
ax.set_xlabel('Κατανάλωση (kWh)', fontsize=9, color='#64748b')
ax.grid(axis='x', linestyle='--', alpha=0.4)

for bar, val in zip(bars, comp_grp['kwh']):
    ax.text(val + max(comp_grp['kwh'])*0.02, bar.get_y() + bar.get_height()/2, f'{val:,.1f} kWh', va='center', ha='left', fontsize=8.5, fontweight='bold', color='#0f2b48')

plt.title('Κατανομή Ενέργειας ανά Μισθώτρια Εταιρία (kWh)', fontsize=10.5, fontweight='bold', pad=10, loc='left', color='#0f2b48')
plt.tight_layout()
chart_comp_path = os.path.join(chart_dir, "chart_custom_company.png")
plt.savefig(chart_comp_path)
plt.close()

# Chart 2: Charger Distribution Bar Chart
ch_grp = df_charged.groupby('chargerId').agg(
    kwh=('energyKWh', 'sum'),
    sessions=('energyKWh', 'count'),
    hours=('durationMinutes', lambda x: x.sum() / 60.0)
).reset_index().sort_values('kwh', ascending=False)

fig, ax = plt.subplots(figsize=(8.5, 2.8), dpi=200)
x_pos = np.arange(len(ch_grp))
ax.bar(x_pos, ch_grp['kwh'], color='#17b978', width=0.5)
ax.set_xticks(x_pos)
ax.set_xticklabels(ch_grp['chargerId'], fontsize=9, fontweight='bold', color='#1e293b')
ax.set_ylabel('kWh', fontsize=9, color='#64748b')
ax.grid(axis='y', linestyle='--', alpha=0.4)
for i, v in enumerate(ch_grp['kwh']):
    ax.text(i, v + max(ch_grp['kwh'])*0.02, f'{v:,.0f}', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#0f2b48')
plt.title('Συνολική Ενέργεια ανά Σημείο Φόρτισης (kWh)', fontsize=10.5, fontweight='bold', pad=10, loc='left', color='#0f2b48')
plt.tight_layout()
chart_ch_path = os.path.join(chart_dir, "chart_custom_chargers.png")
plt.savefig(chart_ch_path)
plt.close()

# 3. HTML Generation for Professional PDF
comp_table_rows = ""
for _, r in comp_grp.iloc[::-1].iterrows():
    share_pct = (r['kwh'] / total_kwh * 100.0) if total_kwh > 0 else 0.0
    comp_table_rows += f"""
    <tr>
        <td><strong>{r['company']}</strong></td>
        <td style="text-align:center;">{int(r['sessions'])}</td>
        <td style="text-align:right;">{r['kwh']:,.1f} kWh</td>
        <td style="text-align:right;">{r['hours']:,.1f} h</td>
        <td style="text-align:right;">{share_pct:.1f}%</td>
        <td style="text-align:right; font-weight:bold; color:#0f2b48;">{r['cost']:,.2f} €</td>
    </tr>
    """

charger_table_rows = ""
for _, r in ch_grp.iterrows():
    c_cost = r['kwh'] * tariff_kwh
    c_share = (r['kwh'] / total_kwh * 100.0) if total_kwh > 0 else 0.0
    charger_table_rows += f"""
    <tr>
        <td><strong>{r['chargerId']}</strong></td>
        <td>Υπόγειος Σταθμός</td>
        <td style="text-align:center;">{int(r['sessions'])}</td>
        <td style="text-align:right;">{r['kwh']:,.1f} kWh</td>
        <td style="text-align:right;">{r['hours']:,.1f} h</td>
        <td style="text-align:right;">{c_share:.1f}%</td>
        <td style="text-align:right; font-weight:bold;">{c_cost:,.2f} €</td>
    </tr>
    """

# Recent Sessions (Top 12)
recent_sessions_rows = ""
for _, s in df_charged.sort_values('timestamp', ascending=False).head(12).iterrows():
    ts_fmt = s['timestamp'][:16].replace('T', ' ') if isinstance(s['timestamp'], str) else str(s['timestamp'])
    recent_sessions_rows += f"""
    <tr>
        <td>{ts_fmt}</td>
        <td><strong>{s['name']}</strong></td>
        <td>{s['company']}</td>
        <td>{s['chargerId']}</td>
        <td style="text-align:right;">{s['durationMinutes']} min</td>
        <td style="text-align:right; font-weight:bold; color:#059669;">{s['energyKWh']:,.2f} kWh</td>
        <td style="text-align:right;">{s['cost_eur']:,.2f} €</td>
    </tr>
    """

logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="height:38px; object-fit:contain;" />' if logo_b64 else '<div class="brand-title">DegerHellas</div>'

html_content = f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
  @page {{
    size: A4 portrait;
    margin: 12mm 14mm 12mm 14mm;
  }}
  body {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1e293b;
    margin: 0;
    padding: 0;
    font-size: 9pt;
    line-height: 1.45;
    background: #ffffff;
  }}
  .page {{
    page-break-after: always;
    height: 270mm;
    position: relative;
    box-sizing: border-box;
  }}
  .page:last-child {{
    page-break-after: avoid;
  }}
  .header-bar {{
    border-bottom: 2px solid #0f2b48;
    padding-bottom: 8px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .brand-sub {{
    font-size: 8pt;
    font-weight: 700;
    color: #0f2b48;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}
  .footer-bar {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid #cbd5e1;
    padding-top: 8px;
    font-size: 8pt;
    color: #475569;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  h1 {{ font-size: 20pt; color: #0f2b48; margin: 0 0 8px 0; font-weight: 800; letter-spacing: -0.5px; }}
  h2 {{ font-size: 13pt; color: #0f2b48; margin: 16px 0 8px 0; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 4px; font-weight: 700; }}
  
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0;
  }}
  .kpi-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 14px;
    border-left: 4px solid #0f2b48;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  }}
  .kpi-title {{ font-size: 7pt; color: #64748b; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; }}
  .kpi-val {{ font-size: 16pt; font-weight: 800; color: #0f2b48; margin: 3px 0; }}
  .kpi-sub {{ font-size: 7pt; color: #94a3b8; }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 8.5pt;
    border-radius: 6px;
    overflow: hidden;
  }}
  th {{
    background: #0f2b48;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 7px 10px;
    font-size: 7.5pt;
    letter-spacing: 0.3px;
  }}
  td {{
    padding: 6.5px 10px;
    border-bottom: 1px solid #edf2f7;
  }}
  tr:nth-child(even) {{ background: #f8fafc; }}

  .chart-img {{
    width: 100%;
    max-height: 76mm;
    object-fit: contain;
    margin: 8px 0;
    border-radius: 6px;
    border: 1px solid #f1f5f9;
  }}
  .cover-box {{
    background: linear-gradient(135deg, #0f2b48 0%, #1e3d59 100%);
    color: white;
    padding: 30px;
    border-radius: 10px;
    margin: 20px 0;
    box-shadow: 0 4px 12px rgba(15,43,72,0.12);
  }}
  .cover-box h1 {{ color: white; }}
  .cover-meta {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    background: rgba(255,255,255,0.08);
    padding: 14px 18px;
    border-radius: 8px;
    margin-top: 18px;
    font-size: 9pt;
  }}
</style>
</head>
<body>

<!-- PAGE 1: COVER & EXECUTIVE SUMMARY -->
<div class="page">
  <div class="header-bar">
    <div>{logo_img_tag}</div>
    <div style="text-align:right;">
      <div class="brand-sub">DegerHellas · Astradigital — energoskopio</div>
      <div style="font-size:8pt; color:#64748b; font-weight:600;">{building_name}</div>
    </div>
  </div>

  <div class="cover-box">
    <div style="font-size:9.5pt; text-transform:uppercase; letter-spacing:1.5px; opacity:0.85; margin-bottom:6px;">Μηνιαία Αναφορά & Επιμερισμός Κοινοχρήστων</div>
    <h1>Κατανάλωση Ηλεκτρικών Οχημάτων<br><span style="font-size:14pt; font-weight:500; opacity:0.9;">Ανά Μισθώτρια Εταιρία & Σημείο Φόρτισης</span></h1>
    <div class="cover-meta">
      <div><strong>Κτίριο:</strong> {building_name}</div>
      <div><strong>Περίοδος:</strong> {period_str}</div>
      <div><strong>Τιμολόγιο Ενέργειας:</strong> {tariff_kwh:.2f} €/kWh</div>
      <div><strong>Συνολικό Κόστος Φόρτισης:</strong> {total_cost_eur:,.2f} €</div>
    </div>
  </div>

  <h2>1. Συνοπτικοί Δείκτες Περιόδου</h2>
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-title">Συνολική Ενέργεια</div>
      <div class="kpi-val">{total_kwh:,.1f} kWh</div>
      <div class="kpi-sub">Πραγματική κατανάλωση</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Συνεδρίες Φόρτισης</div>
      <div class="kpi-val">{total_sessions}</div>
      <div class="kpi-sub">Καταγεγραμμένες εκκινήσεις</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Μέση Συνεδρία</div>
      <div class="kpi-val">{avg_kwh:.1f} kWh</div>
      <div class="kpi-sub">Μέση διάρκεια: {avg_dur_h:.1f} h</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Κόστος προς Επιμερισμό</div>
      <div class="kpi-val">{total_cost_eur:,.2f} €</div>
      <div class="kpi-sub">Βάσει τιμολογίου {tariff_kwh:.2f} €/kWh</div>
    </div>
  </div>

  <div class="footer-bar">
    <div>DegerHellas · Astradigital — energoskopio</div>
    <div>Σελίδα 1 / 4</div>
  </div>
</div>

<!-- PAGE 2: COMPANY BILLING (ΚΟΙΝΟΧΡΗΣΤΑ) -->
<div class="page">
  <div class="header-bar">
    <div>{logo_img_tag}</div>
    <div style="text-align:right;">
      <div class="brand-sub">DegerHellas · Astradigital — energoskopio</div>
      <div style="font-size:8pt; color:#64748b;">Επιμερισμός Κοινοχρήστων</div>
    </div>
  </div>

  <h2>2. Επιμερισμός Κόστους Κοινοχρήστων ανά Εταιρία</h2>
  <p style="font-size:8.5pt; color:#475569; margin-bottom:10px;">
    Κάθε κιλοβατώρα αποδίδεται επακριβώς στην κάρτα RFID του εξουσιοδοτημένου χρήστη και στην αντίστοιχη εταιρία, επιτρέποντας την αυτόματη έκδοση των κοινοχρήστων.
  </p>

  <table>
    <thead>
      <tr>
        <th>Μισθώτρια Εταιρία</th>
        <th style="text-align:center;">Συνεδρίες</th>
        <th style="text-align:right;">Ενέργεια (kWh)</th>
        <th style="text-align:right;">Ώρες Φόρτισης</th>
        <th style="text-align:right;">Μερίδιο (%)</th>
        <th style="text-align:right;">Χρέωση Κοινοχρήστων (€)</th>
      </tr>
    </thead>
    <tbody>
      {comp_table_rows}
      <tr style="background:#edf2f7; font-weight:bold;">
        <td>ΣΥΝΟΛΟ</td>
        <td style="text-align:center;">{total_sessions}</td>
        <td style="text-align:right;">{total_kwh:,.1f} kWh</td>
        <td style="text-align:right;">{total_duration_hours:,.1f} h</td>
        <td style="text-align:right;">100,0%</td>
        <td style="text-align:right;">{total_cost_eur:,.2f} €</td>
      </tr>
    </tbody>
  </table>

  <img src="{chart_comp_path}" class="chart-img">

  <div class="footer-bar">
    <div>DegerHellas · Astradigital — energoskopio</div>
    <div>Σελίδα 2 / 4</div>
  </div>
</div>

<!-- PAGE 3: INFRASTRUCTURE & CHARGERS -->
<div class="page">
  <div class="header-bar">
    <div>{logo_img_tag}</div>
    <div style="text-align:right;">
      <div class="brand-sub">DegerHellas · Astradigital — energoskopio</div>
      <div style="font-size:8pt; color:#64748b;">Σημεία Φόρτισης</div>
    </div>
  </div>

  <h2>3. Ενεργειακή Απόδοση ανά Φορτιστή</h2>
  <table>
    <thead>
      <tr>
        <th>Κωδικός Φορτιστή</th>
        <th>Τοποθεσία</th>
        <th style="text-align:center;">Συνεδρίες</th>
        <th style="text-align:right;">Κατανάλωση (kWh)</th>
        <th style="text-align:right;">Ώρες Λειτουργίας</th>
        <th style="text-align:right;">Μερίδιο (%)</th>
        <th style="text-align:right;">Κόστος Ενέργειας (€)</th>
      </tr>
    </thead>
    <tbody>
      {charger_table_rows}
    </tbody>
  </table>

  <img src="{chart_ch_path}" class="chart-img">

  <div class="footer-bar">
    <div>DegerHellas · Astradigital — energoskopio</div>
    <div>Σελίδα 3 / 4</div>
  </div>
</div>

<!-- PAGE 4: DETAILED SESSION AUDIT LOG -->
<div class="page">
  <div class="header-bar">
    <div>{logo_img_tag}</div>
    <div style="text-align:right;">
      <div class="brand-sub">DegerHellas · Astradigital — energoskopio</div>
      <div style="font-size:8pt; color:#64748b;">Μητρώο Συνεδριών</div>
    </div>
  </div>

  <h2>4. Αναλυτικό Μητρώο Πρόσφατων Συνεδριών (Audit Trail)</h2>
  <table>
    <thead>
      <tr>
        <th>Ημερομηνία / Ώρα</th>
        <th>Όνομα Χρήστη</th>
        <th>Εταιρία</th>
        <th>Φορτιστής</th>
        <th style="text-align:right;">Διάρκεια</th>
        <th style="text-align:right;">kWh</th>
        <th style="text-align:right;">Κόστος</th>
      </tr>
    </thead>
    <tbody>
      {recent_sessions_rows}
    </tbody>
  </table>

  <div class="footer-bar">
    <div>DegerHellas · Astradigital — energoskopio</div>
    <div>Σελίδα 4 / 4</div>
  </div>
</div>

</body>
</html>
"""

html_out = "/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_monthly_report.html"
pdf_out = "/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_monthly_report_oct2026.pdf"

with open(html_out, "w", encoding="utf-8") as f:
    f.write(html_content)

cmd = [
    "google-chrome",
    "--headless=new",
    "--no-pdf-header-footer",
    "--disable-gpu",
    "--no-sandbox",
    f"--print-to-pdf={pdf_out}",
    html_out
]
subprocess.run(cmd, check=True)

print(f"Generated Clean Professional DegerHellas PDF ({os.path.getsize(pdf_out)} bytes)")
