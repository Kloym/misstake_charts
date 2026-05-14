import pandas as pd
import os, glob

def debug_ib():
    TARGET_IB = '69656'
    print(f"\n{'='*50}\n 🕵️ ИЩЕЙКА ДЛЯ ИБ: {TARGET_IB}\n{'='*50}")
    
    INPUT_DIR = 'input_data/'
    mov_files = glob.glob(os.path.join(INPUT_DIR, '*Движение*.xls*'))
    disch_files = glob.glob(os.path.join(INPUT_DIR, '*Выписанные*.xls*'))
    op_files = glob.glob(os.path.join(INPUT_DIR, '*Операции*.xls*'))
    
    if not mov_files or not disch_files or not op_files:
        print("❌ Не найдены таблицы в input_data!")
        return
        
    df_mov = pd.read_excel(mov_files[0])
    df_disch = pd.read_excel(disch_files[0])
    df_op = pd.read_excel(op_files[0])
    
    # Очистка и удаление .0
    df_mov['ИБ_clean'] = df_mov['Номер ИБ'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_disch['ИБ_clean'] = df_disch['ИБ. Номер'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_op['ИБ_clean'] = df_op['ИБ. Номер'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    
    df_patients = pd.merge(df_mov, df_disch, on='ИБ_clean', how='inner', suffixes=('_mov', '_disch'))
    df_full = pd.merge(df_patients, df_op, on='ИБ_clean', how='left', suffixes=('', '_op'))
    
    # Универсальное удаление ведущих нулей у МЭС
    if 'МЭС. Код' in df_full.columns:
        df_full['МЭС. Код'] = df_full['МЭС. Код'].astype(str).apply(
            lambda x: x.split('.')[0].strip().lstrip('0') if x.startswith('0') else x.split('.')[0].strip()
        )
    
    group = df_full[df_full['ИБ_clean'] == TARGET_IB]
    
    if group.empty:
        print(f"\n❌ ИБ {TARGET_IB} полностью исчезла! Проблема в названиях колонок или данных.")
    else:
        print(f"\n✅ ИБ {TARGET_IB} успешно дошла до финала слияния.\n")
        
        # --- НОВАЯ ЛОГИКА ПЕРЕБОРА ВСЕХ ДВИЖЕНИЙ ---
        unique_movements = group.drop_duplicates(subset=['МЭС. Код', 'Отделение'])
        print(f"🔍 Найдено уникальных этапов лечения (МЭС + Отделение): {len(unique_movements)}")
        
        for i, (idx, mov_row) in enumerate(unique_movements.iterrows(), 1):
            mes_code = str(mov_row['МЭС. Код']).strip()
            department = str(mov_row['Отделение']).strip()
            
            print(f"\n   [{i}] ЭТАП:")
            print(f"       МЭС: {mes_code}")
            print(f"       Отделение: {department}")
            
            # Смотрим операции только для этого конкретного МЭСа
            sub_group = group[group['МЭС. Код'] == mov_row['МЭС. Код']]
            
            ops = set()
            for _, r in sub_group.iterrows():
                op_code = str(r.get('Код_op', r.get('Код', ''))).strip()
                if op_code and op_code != 'nan':
                    ops.add(op_code)
            
            print(f"       Извлеченные операции:")
            if ops:
                for op in ops:
                    print(f"        - {op}")
            else:
                print("        - НЕТ ОПЕРАЦИЙ")

    print("\n" + "="*50)
    input("Нажмите Enter...")

if __name__ == "__main__":
    debug_ib()