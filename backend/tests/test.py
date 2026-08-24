from pathlib import Path
import pandas as pd

def find_file(filename="ticket.xlsx"):
    # Search upward from test.py location until ticket.xlsx is located
    current = Path(__file__).resolve().parent
    for _ in range(4):
        candidate = current / filename
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError(f"Could not locate {filename} in project tree.")

FILE_PATH = find_file("ticket.xlsx")

def clean_itil_categories(file_path):
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    
    standard_categories = [
        'Wincar', 'Messagerie', 'Citrix', 'Matériel', 'Internet',
        'Logiciel Système', 'Sage', 'Windows', 'APPCC', 'Réseau',
        'Outillages SAV', 'GestorNet', 'CRM', 'Auto Naps', 'Poste IP Phone',
        'Reporting', 'Ligne VPN', 'Consommable', 'Ligne Téléphonique', 'GSM',
        'Moovapps', 'PayRoll', 'RIAPP', 'Qalitel Doc', 'GDoc',
        'Contrat de Vente', 'Sage Paie & RH', 'Microsoft Teams', 'WebEX',
        'GENERAFI', 'Site Web', 'AppGCMA', 'VPN_FortiClient', 'Fidélisation',
        'Optimmo', 'SMS', 'SRM', 'Qalitel Compar', 'Antivirus', 'VOXCO',
        'SLV', 'Intranet', 'Devopps', 'C.Conformité', 'eSeller', 'TPE', 'OPEL'
    ]
    
    cat_lookup = {cat.lower(): cat for cat in standard_categories}
    
    raw_cats = df['itilcategory_name'].astype(str).str.strip().str.lower()
    df['clean_category'] = raw_cats.map(cat_lookup)
    
    summary = df['clean_category'].value_counts().reset_index()
    summary.columns = ['ITIL Category', 'Ticket Count']
    
    return summary, df['clean_category'].isna().sum()

if __name__ == "__main__":
    category_df, unmapped_count = clean_itil_categories(FILE_PATH)
    print(f"Validated Categories Found: {len(category_df)}")
    print(f"Unmapped / Overflow Noise Rows: {unmapped_count}\n")
    print(category_df.to_string(index=False))