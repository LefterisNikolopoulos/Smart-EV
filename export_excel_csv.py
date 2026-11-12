import json
import pandas as pd

# Load sessions
with open('/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_sessions_oct2026.json', 'r', encoding='utf-8') as f:
    sessions = json.load(f)

df = pd.DataFrame(sessions)
df['cost_eur'] = (df['kwh'] * 0.20).round(2)

csv_path = '/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_charging_oct2026.csv'
xlsx_path = '/home/lefteris/Documents/DegerHellas/Smart Ev/kolonaki_charging_oct2026.xlsx'

df.to_csv(csv_path, index=False, encoding='utf-8-sig')

with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Συνεδρίες Φόρτισης', index=False)
    
    # Summary per company
    company_summary = df.groupby('company').agg(
        Συνεδρίες=('kwh', 'count'),
        kWh=('kwh', 'sum'),
        Κόστος_EUR=('cost_eur', 'sum')
    ).reset_index()
    company_summary.to_excel(writer, sheet_name='Κοινόχρηστα ανά Εταιρία', index=False)
    
    # Summary per charger
    charger_summary = df.groupby(['level', 'chargerId', 'company']).agg(
        Συνεδρίες=('kwh', 'count'),
        kWh=('kwh', 'sum'),
        Κόστος_EUR=('cost_eur', 'sum')
    ).reset_index()
    charger_summary.to_excel(writer, sheet_name='Ανά Φορτιστή', index=False)

print(f"Exported CSV: {csv_path}")
print(f"Exported Excel: {xlsx_path}")
