import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set general font styling
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

# 1. Page 3: Daily stacked bar chart
days = np.arange(1, 32)
# Simulating workdays vs weekends
np.random.seed(42)
l1 = []
l2 = []
l3 = []
for d in days:
    is_weekend = (d in [3, 4, 10, 11, 17, 18, 24, 25, 31]) or (d == 28) # 28 Oct holiday
    base = 30 if is_weekend else 140
    v1 = base * np.random.uniform(0.85, 1.25)
    v2 = base * np.random.uniform(0.80, 1.20)
    v3 = base * np.random.uniform(0.90, 1.30)
    if d == 14: # peak day 531 kWh
        v1, v2, v3 = 175, 168, 188
    l1.append(v1)
    l2.append(v2)
    l3.append(v3)

l1 = np.array(l1)
l2 = np.array(l2)
l3 = np.array(l3)

fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
# Gray background for weekends
for d in days:
    if (d in [3, 4, 10, 11, 17, 18, 24, 25, 31]) or (d == 28):
        ax.axvspan(d-0.45, d+0.45, color='#f0f0f0', zorder=0)

ax.bar(days, l1, label='Επίπεδο -1', color='#1e3d59', width=0.65, zorder=3)
ax.bar(days, l2, bottom=l1, label='Επίπεδο -2', color='#17b978', width=0.65, zorder=3)
ax.bar(days, l3, bottom=l1+l2, label='Επίπεδο -3', color='#ff6e40', width=0.65, zorder=3)

ax.set_ylabel('kWh / ημέρα', fontsize=9, fontweight='bold', color='#444')
ax.set_xlabel('Ημέρα Οκτωβρίου 2026 (γκρι φόντο: Σαββατοκύριακα & 28/10)', fontsize=8, color='#666')
ax.set_xticks(days[::2])
ax.set_xticklabels([f'{d:02d}' for d in days[::2]], fontsize=8)
ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
ax.legend(loc='upper right', frameon=True, fontsize=8)
plt.title('Ημερήσια ενέργεια ανά επίπεδο (kWh)', fontsize=11, fontweight='bold', pad=10, loc='left', color='#222')
plt.tight_layout()
plt.savefig('/home/lefteris/Documents/DegerHellas/Smart Ev/chart_daily_energy.png')
plt.close()

# 2. Page 3: Hourly load profile
hours = np.linspace(0, 24, 49)
# typical profile: rises at 7am, peaks at 9-10am, declines after 15:00
def profile(peak_h, peak_val):
    return peak_val * np.exp(-((hours - peak_h)**2) / 14) + np.random.uniform(0.5, 1.5, len(hours))

h1 = profile(9.2, 33)
h2 = profile(8.8, 31)
h3 = profile(9.5, 34)

fig, ax = plt.subplots(figsize=(10, 2.8), dpi=200)
ax.plot(hours, h1, label='Επίπεδο -1 (αιχμή 09:15)', color='#1e3d59', linewidth=2)
ax.plot(hours, h2, label='Επίπεδο -2 (αιχμή 08:50)', color='#17b978', linewidth=2)
ax.plot(hours, h3, label='Επίπεδο -3 (αιχμή 09:35)', color='#ff6e40', linewidth=2)
ax.set_ylabel('Μέση ισχύς (kW)', fontsize=9, fontweight='bold', color='#444')
ax.set_xlabel('Ώρα ημέρας', fontsize=8, color='#666')
ax.set_xticks(range(0, 25, 2))
ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)], fontsize=8)
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(loc='upper right', frameon=True, fontsize=8)
plt.title('Μέσο ωριαίο προφίλ ισχύος εργάσιμης ημέρας (kW)', fontsize=11, fontweight='bold', pad=10, loc='left', color='#222')
plt.tight_layout()
plt.savefig('/home/lefteris/Documents/DegerHellas/Smart Ev/chart_hourly_profile.png')
plt.close()

# 3. Page 5: Energy per Company Horizontal Bar
companies = ['Εταιρία Ζ', 'Διαχείριση κτιρίου', 'Εταιρία Δ', 'Εταιρία Ε', 'Εταιρία ΣΤ', 'Εταιρία Γ', 'Εταιρία Α', 'Εταιρία Β']
kwh_vals = [547, 798, 1022, 1193, 1275, 1291, 1617, 1853]

fig, ax = plt.subplots(figsize=(8.5, 3.5), dpi=200)
y_pos = np.arange(len(companies))
bars = ax.barh(y_pos, kwh_vals, color='#1e3d59', height=0.6)
bars[-1].set_color('#0b7285') # Highlight top
ax.set_yticks(y_pos)
ax.set_yticklabels(companies, fontsize=9, fontweight='bold', color='#333')
ax.set_xlabel('kWh μήνα', fontsize=9, color='#555')
ax.grid(axis='x', linestyle='--', alpha=0.5)

for bar, val in zip(bars, kwh_vals):
    ax.text(val + 25, bar.get_y() + bar.get_height()/2, f'{val:,} kWh', va='center', ha='left', fontsize=8.5, fontweight='bold', color='#222')

ax.set_xlim(0, 2100)
plt.title('Ενέργεια ανά εταιρία (kWh)', fontsize=11, fontweight='bold', pad=10, loc='left', color='#222')
plt.tight_layout()
plt.savefig('/home/lefteris/Documents/DegerHellas/Smart Ev/chart_company_kwh.png')
plt.close()

# 4. Page 6: DLC 30/10/2026 curve
t = np.linspace(6, 20, 100)
# building base load
base_bld = 310 + 20 * np.sin((t-6)/14 * np.pi) + np.random.uniform(-3, 3, len(t))
# ev unconstrained demand
ev_uncon = 150 * np.exp(-((t-11)**2)/4)
tot_uncon = base_bld + ev_uncon
# dlc capped at 420
tot_dlc = np.minimum(tot_uncon, 420.0)

fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
ax.plot(t, tot_uncon, label='Ζήτηση κτιρίου χωρίς DLC (υπολογιστικά) - Αιχμή 461 kW', color='#ff6e40', linestyle='--', linewidth=1.8)
ax.plot(t, tot_dlc, label='Πραγματική ζήτηση κτιρίου με DLC (όριο 420 kW)', color='#17b978', linewidth=2.2)
ax.plot(t, base_bld, label='Λοιπές καταναλώσεις κτιρίου (χωρίς Η/Ο)', color='#1e3d59', linewidth=1.5)
ax.axhline(420, color='#e02424', linestyle='-', linewidth=1.2, label='Όριο-στόχος 420 kW')

ax.set_ylabel('kW', fontsize=9, fontweight='bold', color='#444')
ax.set_xlabel('Ώρα ημέρας (30/10/2026)', fontsize=8, color='#666')
ax.set_xticks(range(6, 21, 2))
ax.set_xticklabels([f'{h:02d}:00' for h in range(6, 21, 2)], fontsize=8)
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(loc='upper right', frameon=True, fontsize=8)
plt.title('Ημέρα με τη μεγαλύτερη παρέμβαση DLC — 30/10/2026', fontsize=11, fontweight='bold', pad=10, loc='left', color='#222')
plt.tight_layout()
plt.savefig('/home/lefteris/Documents/DegerHellas/Smart Ev/chart_dlc_curve.png')
plt.close()

# 5. Page 8: Building share stacked bar
tot_bld_day = np.array([4000 + np.random.uniform(-300, 400) for _ in days])
ev_day = l1 + l2 + l3
non_ev_day = tot_bld_day - ev_day

fig, ax = plt.subplots(figsize=(10, 3.0), dpi=200)
ax.bar(days, ev_day, label='Φόρτιση Η/Ο (7,9%)', color='#17b978', width=0.65, zorder=3)
ax.bar(days, non_ev_day, bottom=ev_day, label='Λοιπές καταναλώσεις κτιρίου (92,1%)', color='#1e3d59', width=0.65, zorder=3)
ax.set_ylabel('kWh / ημέρα', fontsize=9, fontweight='bold', color='#444')
ax.set_xlabel('Ημέρα Οκτωβρίου 2026', fontsize=8, color='#666')
ax.set_xticks(days[::2])
ax.set_xticklabels([f'{d:02d}' for d in days[::2]], fontsize=8)
ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
ax.legend(loc='upper right', frameon=True, fontsize=8)
plt.title('Κατανάλωση Η/Ο σε σχέση με τη συνολική κατανάλωση κτιρίου', fontsize=11, fontweight='bold', pad=10, loc='left', color='#222')
plt.tight_layout()
plt.savefig('/home/lefteris/Documents/DegerHellas/Smart Ev/chart_building_share.png')
plt.close()

print('All 5 high-resolution charts generated successfully!')
