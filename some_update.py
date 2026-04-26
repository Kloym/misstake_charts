import pandas as pd
import numpy as np
import time
import os
import glob
from datetime import datetime
import re
import traceback
from test_utils import ANESTHESIA_DICT, DIFFICULT_DEPARTMENTS, debug_print, generate_html_report


# --- ФУНКЦИИ ГЕНЕРАЦИИ ПОДСКАЗОК ---

def _get_hints_for_msmkbe(mes_code, ref_msmkbe):
    mes_code_str = str(mes_code).strip()
    valid = ref_msmkbe[ref_msmkbe['Код медицинской услуги'] == mes_code_str]
    if valid.empty:
        return "<span class='no-hint'>В справочнике базовых диагнозов нет вариантов для этого МЭС.</span>"
    unique_mkb = valid['Код диагноза (шифр по МКБ-10)'].dropna().unique()
    hints = [f"<li><b>Допустимый диагноз:</b> <span class='hl-diag'>{mkb}</span></li>" for mkb in unique_mkb[:15]]
    return f'<details class="hint-details"><summary>💡 Показать допустимые диагнозы ({len(unique_mkb)})</summary><div class="hint-content"><ul>{"".join(hints)}</ul></div></details>'

def _get_hints_for_reeskp(mes_code, ref_reeskp):
    mes_code_str = str(mes_code).strip()
    valid = ref_reeskp[ref_reeskp['Код услуги'] == mes_code_str]
    if valid.empty:
        return "<span class='no-hint'>В справочнике СКП нет вариантов для этого МЭС.</span>"
    unique_mkb = valid['код диагноза'].dropna().unique()
    hints = [f"<li><b>Допустимый диагноз (СКП):</b> <span class='hl-diag'>{mkb}</span></li>" for mkb in unique_mkb[:15]]
    return f'<details class="hint-details"><summary>💡 Показать допустимые диагнозы СКП ({len(unique_mkb)})</summary><div class="hint-content"><ul>{"".join(hints)}</ul></div></details>'

def _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs=None):
    mes_code_str = str(mes_code).strip()
    valid_mes = ref_mscrit[ref_mscrit['temp_mes_str'] == mes_code_str]
    
    if valid_mes.empty:
        return "<span class='no-hint'>Для этого МЭС операции в справочнике не предусмотрены.</span>"
        
    if search_mkbs:
        valid_mkb = valid_mes[valid_mes['Код диагноза'].isin(search_mkbs)]
        if not valid_mkb.empty:
            unique_ops = valid_mkb['Код хирургической операции'].drop_duplicates().head(15)
            hints = []
            for oper in unique_ops:
                oper_display = "A00.00 (Любая операция)" if oper == 'A00.00' else oper
                hints.append(f"<li><b>Допустимая операция:</b> <span class='hl-oper'>{oper_display}</span></li>")
            return f'<details class="hint-details"><summary>💡 Показать допустимые операции для диагноза ({len(unique_ops)})</summary><div class="hint-content"><ul>{"".join(hints)}</ul></div></details>'

    unique_combos = valid_mes[['Код диагноза', 'Код хирургической операции']].drop_duplicates().head(15)
    hints = []
    for _, row in unique_combos.iterrows():
        diag = row['Код диагноза']
        oper = row['Код хирургической операции']
        oper_display = "A00.00 (Любая операция)" if oper == 'A00.00' else oper
        hints.append(f"<li><b>Диагноз:</b> <span class='hl-diag'>{diag}</span> | <b>Операция:</b> <span class='hl-oper'>{oper_display}</span></li>")
    return f'<details class="hint-details"><summary>💡 Показать правильные связки операций ({len(unique_combos)})</summary><div class="hint-content"><ul>{"".join(hints)}</ul></div></details>'

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def load_and_merge_data(mov_path, disch_path, op_path):
    df_mov = pd.read_excel(mov_path)
    df_disch = pd.read_excel(disch_path)
    df_op = pd.read_excel(op_path)
    
    if 'Код' in df_mov.columns and 'Код прерывания госпитализации' not in df_mov.columns:
        df_mov.rename(columns={'Код': 'Код прерывания госпитализации'}, inplace=True)

    if 'Дата перевода/выписки' in df_mov.columns and 'Дата выбытия' not in df_mov.columns:
        df_mov.rename(columns={'Дата перевода/выписки': 'Дата выбытия'}, inplace=True)
    elif 'Дата перевода/выбытия' in df_mov.columns and 'Дата выбытия' not in df_mov.columns:
        df_mov.rename(columns={'Дата перевода/выбытия': 'Дата выбытия'}, inplace=True)
        
    df_mov['ИБ_clean'] = df_mov['Номер ИБ'].astype(str).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_disch['ИБ_clean'] = df_disch['ИБ. Номер'].astype(str).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_op['ИБ_clean'] = df_op['ИБ. Номер'].astype(str).str.replace(r'-\d{4}', '', regex=True).str.strip()
    
    df_patients = pd.merge(df_mov, df_disch, on='ИБ_clean', how='inner', suffixes=('_mov', '_disch'))
    df_full = pd.merge(df_patients, df_op, on='ИБ_clean', how='left', suffixes=('', '_op'))
    
    return df_full

def _check_mscrit_operation_rules(op_row, mscrit_req, ib_num, canal, is_skp):
    errors = []
    op_code = str(op_row.get('Код', '')).strip()
    op_type = str(op_row.get('Основная/сопутст', op_row.get('Основная/сопутствующая', ''))).strip()
        
    req_main = mscrit_req['Обязательность отметки операции как основной']
    if req_main == 1 and op_type != 'Основная':
        errors.append(f"ИБ {ib_num}: Статус операции: в данной связке операция <b>{op_code}</b> обязана быть 'Основной', а у вас указана '<b>{op_type}</b>'.")

    anesthesia_name = str(op_row.get('Анестезия', '')).strip()

    if anesthesia_name.lower() not in ['nan', 'none', '']:
        req_anesth = mscrit_req['Код типа анестезии']
        actual_anesth_val = ANESTHESIA_DICT.get(anesthesia_name)
        
        if actual_anesth_val is None:
            errors.append(f"ИБ {ib_num}: Тип анестезии: указана неизвестная анестезия <b>'{anesthesia_name}'</b>. Проверьте опечатку.")
        elif req_anesth == 1 and actual_anesth_val != 1:
            errors.append(f"ИБ {ib_num}: Тип анестезии: для этой операции обязательна анестезия <b>Общая</b>, но у вас указана <b>'{anesthesia_name}'</b> (Это местная).")
    if not is_skp:
        samotek_allowed = mscrit_req.get('Допустимость госпитализации "самотёк"', 1)
        canal_clean = str(canal).strip().lower() 
        if canal_clean in ['самотек', 'самотёк', '103 поликлиника']:
            if samotek_allowed != 1:
                errors.append(f"ИБ {ib_num}: Канал поступления: пациент поступил как '<b>{canal}</b>', но для данной связки госпитализация самотеком запрещена.")
                
    return errors

def _check_interruption_code(group, ib_num):
    errors = []
    if 'Код прерывания госпитализации' not in group.columns:
        return errors
        
    patient_type = str(group['ПУМП. Тип пациента'].iloc[0]).strip().upper() if 'ПУМП. Тип пациента' in group.columns else 'UNKNOWN'
    SPECIAL_PROJECT_MES = ['200531', '79550', '79018', '200627', '79008', '66213', '66212', '200031', '200510', '66275', '200625', '200626', '200664', '200667', '72044', '200088', '72039', '76951', '82031', '82044', '82045', '82055', '200665', '200711']

    unique_movs = group.drop_duplicates(subset=['МЭС. Код', 'Код прерывания госпитализации']).copy()
    
    if unique_movs.empty:
        return errors

    if 'Дата выбытия' in unique_movs.columns:
        unique_movs['temp_date'] = pd.to_datetime(unique_movs['Дата выбытия'], dayfirst=True, errors='coerce')
        sorted_group = unique_movs.sort_values(by=['temp_date', 'Дата поступления'])
    else:
        sorted_group = unique_movs.sort_values(by='Дата поступления')

    if len(sorted_group) > 1:
        for idx in range(len(sorted_group) - 1):
            current_row = sorted_group.iloc[idx]
            code = str(current_row['Код прерывания госпитализации']).split('.')[0].strip().upper()
            row_dept = str(current_row.get('Отделение', '')).strip()
            dept_lower = row_dept.lower()
            
            if 'дневной стационар' in dept_lower:
                continue
                
            if code != '7':
                display_code = "ПУСТО" if code == 'NAN' else code
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Множественные переводы: промежуточные коды прерывания должны быть строго '<b>7</b>', а в выписке №{idx+1} указано '<b>{display_code}</b>'.")

    for _, row in sorted_group.iterrows():
        row_dept = str(row.get('Отделение', '')).strip()
        mes_code = str(row['МЭС. Код']).split('.')[0].strip()
        code = str(row['Код прерывания госпитализации']).split('.')[0].strip().upper()

        display_code = "ПУСТО" if code == 'NAN' else code

        mes_clean = mes_code.lstrip('0') if mes_code.startswith('0') else mes_code
        is_special = mes_code in SPECIAL_PROJECT_MES or mes_clean in SPECIAL_PROJECT_MES

        if is_special:
            if patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР', 'НИЛ']:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Недопустимый МЭС: спецпроект <b>{mes_code}</b> разрешен только для 'ЗЛ', 'ИН' и 'НИЛ' (у вас '<b>{patient_type}</b>').")

            if mes_code.startswith('200'):
                if patient_type == 'НИЛ' and code in ['S', 'С', 'C']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) пациенту 'НИЛ' нельзя ставить '<b>{display_code}</b>'.")
                elif patient_type in ['ЗЛ', 'НР'] and code not in ['S', 'С', 'C']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) у пациента 'ЗЛ' должен быть '<b>S</b>', а указано '<b>{display_code}</b>'.")
                elif patient_type in ['ИН', 'ИНОГОРОДНИЙ'] and code not in ['V', 'В']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) у пациента 'ИН' должен быть '<b>V</b>', а указано '<b>{display_code}</b>'.")
            else:
                if patient_type == 'НИЛ' and code in ['S', 'С', 'C']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) пациенту 'НИЛ' нельзя ставить '<b>{display_code}</b>'.")
                elif patient_type in ['ЗЛ', 'НР'] and code not in ['S', 'С', 'C']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) у пациента 'ЗЛ' должен быть '<b>S</b>', а указано '<b>{display_code}</b>'.")

        elif mes_code.startswith('200'):
            if patient_type == 'НИЛ':
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Недопустимый МЭС: пациентам 'НИЛ' запрещено выставлять МЭС ВМП (<b>{mes_code}</b>).")
            elif patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР']:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Недопустимый МЭС: МЭС <b>{mes_code}</b> разрешен только для 'ЗЛ' и 'ИН' (у вас '<b>{patient_type}</b>').")
            else:
                if code not in ['V', 'В']:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Код прерывания: для МЭС ВМП (<b>{mes_code}</b>) код должен быть '<b>V</b>', а указано '<b>{display_code}</b>'.")
                
    return list(dict.fromkeys(errors))

def _check_department_rules(group, ib_num):
    errors = []
    reanimation_target_codes = ['056029', '56029']
    unique_movs = group.drop_duplicates(subset=['Отделение', 'МЭС. Код'])
    
    for _, row in unique_movs.iterrows():
        mes_code = str(row.get('МЭС. Код', '')).split('.')[0].strip()
        row_dept = str(row.get('Отделение', '')).strip()
        dept_lower = row_dept.lower()

        if mes_code.startswith(('95', '095', '84', '084')):
            if 'коечное отделение нп' not in dept_lower and 'диагностическ' not in dept_lower:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Коечном отделении НП или диагностическом (у вас '<b>{row_dept}</b>').")

        elif mes_code.startswith('183'):
            if 'новорожден' not in dept_lower:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Отделении реанимации для новорожденных (у вас '<b>{row_dept}</b>').")

        elif mes_code.startswith(('83', '083')) or mes_code in reanimation_target_codes:
            if 'реанимац' not in dept_lower:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в отделениях реанимации (у вас '<b>{row_dept}</b>').")

    return list(dict.fromkeys(errors))

def _check_missing_operation_and_samotek(group, mscrit_match, ib_num, mes_code, mkb_code, canal, department, ref_mscrit, search_mkbs):
    errors = []

    if str(canal).strip().lower() in ['самотек', 'самотёк', '103 поликлиника']:
        samotek_col = 'Допустимость госпитализации "самотёк"'
        samotek_val = 1
        if samotek_col in mscrit_match.columns:
            val = mscrit_match[samotek_col].iloc[0]
            samotek_val = int(val) if pd.notna(val) else 1
            
        if samotek_val == 0:
            errors.append(f"ИБ {ib_num}: Ошибка канала поступления: госпитализация 'самотёк' невозможна под МЭС <b>{mes_code}</b> и диагноз <b>{mkb_code}</b>.")

    a00_match = mscrit_match[mscrit_match['Код хирургической операции'] == 'A00.00']
    if a00_match.empty:
        sorted_g = group.dropna(subset=['Код прерывания госпитализации']).copy()
        if 'Дата выбытия' in sorted_g.columns:
            sorted_g['temp_date'] = pd.to_datetime(sorted_g['Дата выбытия'], dayfirst=True, errors='coerce')
            sorted_g = sorted_g.sort_values(by=['temp_date', 'Дата поступления'])
        else:
            sorted_g = sorted_g.sort_values(by='Дата поступления')
            
        last_c = str(sorted_g.iloc[-1]['Код прерывания госпитализации']).split('.')[0].strip() if not sorted_g.empty else 'NAN'
        
        EXEMPT_9_CODES = ['068030', '068050', '068090', '068180', '073110', '073150', '073180', '079002', '079010', '079020', '079040', '079060', '079061', '079070', '079080', '079090', '079100', '079110', '079120', '079122', '079300', '079320', '079330', '082001', '082003', '082024', '085008', '085051', '085060', '085081', '086010']

        if mes_code.zfill(6) in EXEMPT_9_CODES and last_c == '9':
            pass 
        else:
            error_msg = f"ИБ {ib_num}: Ошибка: для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b> обязательна хирургическая операция, но она отсутствует."
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
            
    return errors

def _validate_operations_and_diagnoses(group, ref_mscrit, ref_msmkbe, ref_reeskp, mes_code, mkb_code, search_mkbs, ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, patient_type):
    errors = []
    performed_ops = []
    seen = set()
    
    for row in group.to_dict('records'):
        op_code = str(row.get('Код', '')).strip()
        
        if op_code.lower() in ['nan', '']:
            continue

        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        
        sig = (op_code, op_type, anesth)
        if sig not in seen:
            seen.add(sig)
            performed_ops.append(row)
            
    if performed_ops:
        a00_match = ref_mscrit[
            (ref_mscrit['Код медицинской услуги'] == mes_code) & 
            (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
            (ref_mscrit['Код хирургической операции'] == 'A00.00')
        ]
        
        valid_candidates = []
        
        if not a00_match.empty:
            for row in performed_ops:
                valid_candidates.append((row, a00_match.iloc[0]))
        else:
            for row in performed_ops:
                op_code = str(row.get('Код', '')).strip()
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
                    (ref_mscrit['Код хирургической операции'] == op_code)
                ]
                if not mscrit_match.empty:
                    valid_candidates.append((row, mscrit_match.iloc[0]))
                    
            if not valid_candidates:
                for row in performed_ops:
                    op_code = str(row.get('Код', '')).strip()
                    fallback_match = ref_mscrit[
                        (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                        (ref_mscrit['Код хирургической операции'] == op_code)
                    ]
                    if not fallback_match.empty:
                        valid_candidates.append((row, fallback_match.iloc[0]))
        
        if not valid_candidates:
            op_codes_str = ", ".join(sorted(list(set([str(r.get('Код', '')).strip() for r in performed_ops]))))
            if has_diag_error:
                error_msg = f"ИБ {ib_num}: 🚨 <b style='color:var(--error-border);'>ДВОЙНАЯ ОШИБКА:</b> Базовая проверка диагноза ({diag_error_msg}), И ни одна из операций (<b>{op_codes_str}</b>) не подходит."
            else:
                error_msg = f"ИБ {ib_num}: Ошибка операции: ни одна из проведенных операций (<b>{op_codes_str}</b>) не предусмотрена справочником mscrit для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b>."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
            if has_diag_error:
                error_msg = f"ИБ {ib_num}: Базовая проверка диагноза: {diag_error_msg}."
                if department in DIFFICULT_DEPARTMENTS:
                    if patient_type == 'НИЛ':
                        hint_html = _get_hints_for_msmkbe(mes_code, ref_msmkbe)
                    else:
                        hint_html = _get_hints_for_reeskp(mes_code, ref_reeskp) if is_skp else _get_hints_for_mscrit(mes_code, ref_mscrit)
                    error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
                errors.append(error_msg)
                
            perfect_match_found = False
            candidate_errors = []
            
            for row, mscrit_req in valid_candidates:
                op_errs = _check_mscrit_operation_rules(row, mscrit_req, ib_num, canal, is_skp)
                if not op_errs:
                    perfect_match_found = True
                    break
                else:
                    candidate_errors.extend(op_errs)
                    
            if not perfect_match_found:
                unique_candidate_errors = list(dict.fromkeys(candidate_errors))
                errors.extend(unique_candidate_errors)
    else:
        if has_diag_error:
            error_msg = f"ИБ {ib_num}: Базовая проверка диагноза: {diag_error_msg}."
            if department in DIFFICULT_DEPARTMENTS:
                if patient_type == 'НИЛ':
                    hint_html = _get_hints_for_msmkbe(mes_code, ref_msmkbe)
                else:
                    hint_html = _get_hints_for_reeskp(mes_code, ref_reeskp) if is_skp else _get_hints_for_mscrit(mes_code, ref_mscrit)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
            if not is_skp:
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs))
                ]
                if not mscrit_match.empty:
                    missing_op_errors = _check_missing_operation_and_samotek(
                        group, mscrit_match, ib_num, mes_code, mkb_code, canal, department, ref_mscrit, search_mkbs
                    )
                    errors.extend(missing_op_errors)

    return errors

def check_reanimation_logic(group, ib_num):
    errors = []
    try:
        if 'Дата выбытия' not in group.columns:
            return [f"ИБ {ib_num}: [Реанимация] В таблице 'Движение' нет столбца 'Дата выбытия' для расчета дней."]
            
        unique_movs = group.drop_duplicates(subset=['Дата поступления', 'Дата выбытия', 'Отделение'])
        rean_rows = unique_movs[unique_movs['Отделение'].astype(str).str.lower().str.contains('реанимац', na=False)]
        
        if rean_rows.empty:
            rean_rows = unique_movs 

        for _, row in rean_rows.iterrows():
            mes_code = str(row.get('МЭС. Код', group['МЭС. Код'].iloc[0])).split('.')[0].strip()
            row_dept = str(row.get('Отделение', 'Реанимации')).strip()

            reanimation_target_codes = ['056029', '56029', '083010', '083020', '083030', '083040', '083050', '183010', '183020', '183030', '183040', '183050', '83010', '83020', '83030', '83040', '83050']
            
            if mes_code not in reanimation_target_codes:
                errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: [Реанимация] Ошибка МЭС: в '{row_dept}' указан непрофильный МЭС <b>{mes_code}</b>. Для нахождения в реанимации требуется специальный МЭС.")
                continue 

            if pd.notna(row['Дата поступления']) and pd.notna(row['Дата выбытия']):
                d_in = pd.to_datetime(row['Дата поступления'], dayfirst=True)
                d_out = pd.to_datetime(row['Дата выбытия'], dayfirst=True)

                hours = (d_out - d_in).total_seconds() / 3600.0
                if hours <= 0: 
                    continue

                days = (d_out.date() - d_in.date()).days
                if days == 0: days = 1

                if hours < 12:
                    expected_codes = ['053029', '53029', '056029', '56029']
                    time_str = f"{round(hours, 1)} часов"
                elif days <= 2:
                    expected_codes = ['083010', '83010']
                    time_str = f"{days} дней"
                elif 3 <= days <= 4:
                    expected_codes = ['083020', '83020']
                    time_str = f"{days} дней"
                elif 5 <= days <= 6:
                    expected_codes = ['083030', '83030']
                    time_str = f"{days} дней"
                elif 7 <= days <= 8:
                    expected_codes = ['083040', '83040']
                    time_str = f"{days} дней"
                else:
                    expected_codes = ['083050', '83050']
                    time_str = f"{days} дней"
                    
                if mes_code not in expected_codes:
                    errors.append(f"DEPT::{row_dept}::ИБ {ib_num}: [Реанимация] В '{row_dept}' пациент находился <b>{time_str}</b>. По правилам ожидался один из МЭС: <b>{expected_codes}</b>, но у вас указан <b>'{mes_code}'</b>.")

    except Exception as e:
        errors.append(f"ИБ {ib_num}: [Реанимация] Программная ошибка при расчете времени ({e}).")

    return errors

def check_nil_patient(group, ref_msmkbe, ref_mscrit, ref_mkb10):
    errors = []
    mes_code = str(group['МЭС. Код'].iloc[0]).split('.')[0].strip()
    mkb_code = str(group['Диагноз. МКБ-10'].iloc[0]).strip().upper()
    mkb_base = mkb_code.split('.')[0]
    ib_num = group['ИБ_clean'].iloc[0]
    department = str(group['Отделение'].iloc[0]).strip().lower()
    canal = group['Канал по ДЗМ-56'].iloc[0]
    mes_name = str(group['МЭС. Название'].iloc[0]).lower()
    is_skp = 'стационар кратковременного пребывания' in mes_name
    
    search_mkbs = [mkb_code, 'XXX.X', 'ХХХ.Х']
    is_invalid_extension = False
    
    if mkb_code in ref_mkb10['Шифр'].values:
        search_mkbs.append(mkb_base)
    elif '.' in mkb_code and mkb_base in ref_mkb10['Шифр'].values:
        is_invalid_extension = True
        
    diag_err_reason = f"расширение <b>{mkb_code}</b> не предусмотрено справочником МКБ-10 (используйте базовый <b>{mkb_base}</b>)" if is_invalid_extension else f"указанный МКБ <b>{mkb_code}</b> не подходит для МЭС <b>{mes_code}</b>"
    
    has_diag_error = False
    diag_error_msg = ""
    
    msmkbe_match = ref_msmkbe[
        (ref_msmkbe['Код медицинской услуги'] == mes_code) & 
        (ref_msmkbe['Код диагноза (шифр по МКБ-10)'].isin(search_mkbs))
    ]
    
    if msmkbe_match.empty:
        has_diag_error = True
        mes_exists = not ref_msmkbe[ref_msmkbe['Код медицинской услуги'] == mes_code].empty
        if not mes_exists:
            diag_error_msg = f"МЭС <b>{mes_code}</b> не найден в справочнике msmkbe"
        else:
            diag_error_msg = diag_err_reason
        
    op_errors = _validate_operations_and_diagnoses(
        group, ref_mscrit, ref_msmkbe, None, mes_code, mkb_code, search_mkbs, 
        ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, 'НИЛ'
    )
    errors.extend(op_errors)
    
    return errors


def check_standard_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10, patient_type):
    errors = []
    mes_code = str(group['МЭС. Код'].iloc[0]).split('.')[0].strip()
    mkb_code = str(group['Диагноз. МКБ-10'].iloc[0]).strip().upper()
    mkb_base = mkb_code.split('.')[0]
    ib_num = group['ИБ_clean'].iloc[0]
    canal = group['Канал по ДЗМ-56'].iloc[0]
    mes_name = str(group['МЭС. Название'].iloc[0]).lower()
    department = str(group['Отделение'].iloc[0]).strip().lower()
    is_skp = 'стационар кратковременного пребывания' in mes_name

    search_mkbs = [mkb_code, 'XXX.X', 'ХХХ.Х']
    is_invalid_extension = False
    
    if mkb_code in ref_mkb10['Шифр'].values:
        search_mkbs.append(mkb_base)
    elif '.' in mkb_code and mkb_base in ref_mkb10['Шифр'].values:
        is_invalid_extension = True
        
    diag_err_reason = f"расширение <b>{mkb_code}</b> не предусмотрено справочником МКБ-10 (используйте базовый <b>{mkb_base}</b>)" if is_invalid_extension else f"указанный МКБ <b>{mkb_code}</b> не подходит для МЭС <b>{mes_code}</b>"
    
    has_diag_error = False
    diag_error_msg = ""

    if is_skp:
        reeskp_match = ref_reeskp[
            (ref_reeskp['Код услуги'] == mes_code) & 
            (ref_reeskp['код диагноза'].isin(search_mkbs))
        ]
        if reeskp_match.empty:
            has_diag_error = True
            mes_exists = not ref_reeskp[ref_reeskp['Код услуги'] == mes_code].empty
            
            tag = "[СКП]" if patient_type in ['ИН', 'ИНОГОРОДНИЙ'] else "[СКП ЗЛ]"
            
            if not mes_exists:
                diag_error_msg = f"{tag} МЭС <b>{mes_code}</b> не найден в справочнике reeskp"
            else:
                diag_error_msg = f"{tag} {diag_err_reason}"
        else:
            if patient_type in ['ИН', 'ИНОГОРОДНИЙ']:
                priznak = reeskp_match.iloc[0]['Признак оплаты иногородним']
                if priznak != 1:
                    errors.append(f"ИБ {ib_num}: [СКП] Ошибка признака оплаты: для иногородних он должен быть '<b>1</b>', а у вас стоит '<b>{priznak}</b>'.")
    else:
        mscrit_base_match = ref_mscrit[
            (ref_mscrit['Код медицинской услуги'] == mes_code) & 
            (ref_mscrit['Код диагноза'].isin(search_mkbs))
        ]
        if mscrit_base_match.empty:
            has_diag_error = True
            mes_exists = not ref_mscrit[ref_mscrit['Код медицинской услуги'] == mes_code].empty
            if not mes_exists:
                diag_error_msg = f"МЭС <b>{mes_code}</b> не найден в справочнике mscrit"
            else:
                diag_error_msg = f"{diag_err_reason}"
                
    op_errors = _validate_operations_and_diagnoses(
        group, ref_mscrit, ref_msmkbe, ref_reeskp, mes_code, mkb_code, search_mkbs, 
        ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, patient_type
    )
    errors.extend(op_errors)
    
    return errors


def main():
    start_time = time.time()
    INPUT_DIR = 'input_data/'
    REF_DIR = 'references/'

    print("=== ЗАПУСК СКРИПТА Mscrit Checker ===")

    if not os.path.exists(INPUT_DIR) or not os.path.exists(REF_DIR):
        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(REF_DIR, exist_ok=True)
        print("Созданы папки 'input_data' и 'references'.")
        print("Пожалуйста, положите рабочие таблицы и справочники в папки и запустите программу снова.")
        input("\nНажмите Enter для выхода...")
        return

    try:
        mov_files = glob.glob(os.path.join(INPUT_DIR, '*Движение*.xls*'))
        disch_files = glob.glob(os.path.join(INPUT_DIR, '*Выписанные*.xls*'))
        op_files = glob.glob(os.path.join(INPUT_DIR, '*Операции*.xls*'))

        if not mov_files: raise FileNotFoundError("Не найден файл со словом 'Движение' в папке input_data")
        if not disch_files: raise FileNotFoundError("Не найден файл со словом 'Выписанные' в папке input_data")
        if not op_files: raise FileNotFoundError("Не найден файл со словом 'Операции' в папке input_data")

        mov_file = mov_files[0]
        disch_file = disch_files[0]
        op_file = op_files[0]

        msmkbe_file = os.path.join(REF_DIR, 'msmkbe_.csv')
        mscrit_file = os.path.join(REF_DIR, 'mscrit_.csv')
        reeskp_file = os.path.join(REF_DIR, 'reeskp_.csv')
        mkb10_file = os.path.join(REF_DIR, 'mkb10__.csv')
        
        df_merged = load_and_merge_data(mov_file, disch_file, op_file)
        
        ref_msmkbe = pd.read_csv(msmkbe_file, sep=';', encoding='windows-1251') 
        ref_mscrit = pd.read_csv(mscrit_file, sep=';', encoding='windows-1251')
        ref_reeskp = pd.read_csv(reeskp_file, sep=';', encoding='windows-1251')
        ref_mkb10 = pd.read_csv(mkb10_file, sep=';', encoding='windows-1251')

        ref_msmkbe['Код медицинской услуги'] = ref_msmkbe['Код медицинской услуги'].astype(str).str.split('.').str[0].str.strip()
        ref_msmkbe['Код диагноза (шифр по МКБ-10)'] = ref_msmkbe['Код диагноза (шифр по МКБ-10)'].astype(str).str.strip().str.upper()
        
        ref_mscrit['Код медицинской услуги'] = ref_mscrit['Код медицинской услуги'].astype(str).str.split('.').str[0].str.strip()
        ref_mscrit['temp_mes_str'] = ref_mscrit['Код медицинской услуги']
        ref_mscrit['Код диагноза'] = ref_mscrit['Код диагноза'].astype(str).str.strip().str.upper()
        ref_mscrit['Код хирургической операции'] = ref_mscrit['Код хирургической операции'].astype(str).str.strip()
        
        ref_reeskp['Код услуги'] = ref_reeskp['Код услуги'].astype(str).str.split('.').str[0].str.strip()
        ref_reeskp['код диагноза'] = ref_reeskp['код диагноза'].astype(str).str.strip().str.upper()

        ref_mkb10['Шифр'] = ref_mkb10['Шифр'].astype(str).str.strip().str.upper()
        
        recs_file = os.path.join(REF_DIR, 'recommendations.xlsx')
        recs_dict = {}
        if os.path.exists(recs_file):
            all_sheets = pd.read_excel(recs_file, sheet_name=None)
            ref_recs = pd.concat(all_sheets.values(), ignore_index=True)
            ref_recs.columns = ref_recs.columns.str.strip()
            
            if 'Код услуги' in ref_recs.columns:
                ref_recs['Код услуги'] = ref_recs['Код услуги'].ffill()
                ref_recs['Код услуги'] = ref_recs['Код услуги'].astype(str).str.split('.').str[0].str.strip()
                ref_recs = ref_recs.fillna('')
                
                for code, group_df in ref_recs.groupby('Код услуги'):
                    records = group_df[['Обязательность', 'Критерии экспертизы', 'Документ', 'Поле документа']].to_dict('records')
                    recs_dict[code] = records
        else:
            print("⚠️ Файл recommendations.xlsx не найден в папке references. Подсказки по клиническим критериям будут отключены.")
            
        all_errors = []
        
        reanimation_target_codes = ['056029', '56029', '083010', '083020', '083030', '083040', '083050', '183010', '183020', '183030', '183040', '183050', '83010', '83020', '83030', '83040', '83050']
        
        if 'Тип оплаты' in df_merged.columns:
            excluded_types = [
                'ПМУ', 'ПМУ (С ФИЗ.ЛИЦОМ)', 'ПМУ (С ЮР.ЛИЦОМ)', 
                'ДМС', 'БЮДЖЕТ', 'ГОС. ЗАДАНИЕ'
            ]
            df_merged = df_merged[~df_merged['Тип оплаты'].astype(str).str.upper().str.strip().isin(excluded_types)]

        grouped = df_merged.groupby('ИБ_clean')
        print(f"Обнаружено пациентов (ИБ): {len(grouped)}. Начинаю проверку...")
        
        for ib, group in grouped:
            debug_print(f"--- Обработка ИБ: {ib} ---")
            patient_type = str(group['ПУМП. Тип пациента'].iloc[0]).strip().upper() if 'ПУМП. Тип пациента' in group.columns else 'UNKNOWN'
            
            if patient_type == 'НР':
                mother_ib = str(ib).split('/')[0].strip()
                if mother_ib in grouped.groups:
                    mother_group = grouped.get_group(mother_ib)
                    patient_type = str(mother_group['ПУМП. Тип пациента'].iloc[0]).strip().upper()
                    
            mes_name = str(group['МЭС. Название'].iloc[0]).lower()
            mes_code = str(group['МЭС. Код'].iloc[0]).strip()
            department = str(group['Отделение'].iloc[0]).strip() 
            
            if patient_type == 'NAN' or patient_type == '':
                continue

            dept_errors = _check_department_rules(group, ib)
            if dept_errors:
                for err in dept_errors:
                    if err.startswith("DEPT::"):
                        _, spec_dept, msg = err.split("::", 2)
                        all_errors.append({'department': spec_dept, 'message': msg})
                    else:
                        all_errors.append({'department': department, 'message': err})
                continue
                
            temp_errors = []

            mes_clean = mes_code.lstrip('0') if mes_code.startswith('0') else mes_code
            is_pure_rean_mes = (mes_code in reanimation_target_codes) or (mes_clean in reanimation_target_codes)

            if not is_pure_rean_mes:
                if patient_type == 'НИЛ':
                    debug_print(f"ИБ {ib}: Направлен в блок НИЛ")
                    temp_errors.extend(check_nil_patient(group, ref_msmkbe, ref_mscrit, ref_mkb10))
                elif patient_type in ['ИН', 'ИНОГОРОДНИЙ', 'ЗЛ', 'НР']: 
                    debug_print(f"ИБ {ib}: Направлен в стандартный блок ({patient_type})")
                    temp_errors.extend(check_standard_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10, patient_type))
                else:
                    temp_errors.append(f"ИБ {ib}: Невозможно классифицировать пациента (тип: <b>'{patient_type}'</b>).")

            has_rean_dept = group['Отделение'].astype(str).str.lower().str.contains('реанимац', na=False).any()
            if has_rean_dept or ('реанимация' in mes_name) or is_pure_rean_mes:
                temp_errors.extend(check_reanimation_logic(group, ib))
                
            temp_errors.extend(_check_interruption_code(group, ib))

            for err in temp_errors:
                if err.startswith("DEPT::"):
                    _, spec_dept, msg = err.split("::", 2)
                    all_errors.append({'department': spec_dept, 'message': msg})
                else:
                    all_errors.append({'department': department, 'message': err})
                
        print("\n" + "="*50)
        print(f"ПРОВЕРКА ЗАВЕРШЕНА. НАЙДЕНО ОШИБОК: {len(all_errors)}")
        print("="*50)

        for err_dict in all_errors:
            clean_msg = re.sub(r'<[^>]+>', '', err_dict['message'])
            print(f"[{err_dict['department']}] {clean_msg}")
            
        if all_errors:
            current_time = datetime.now().strftime("%d.%m.%Y_%H-%M")
            report_name = f"report_{current_time}.html"
            generate_html_report(all_errors, recs_dict, output_path=os.path.join(INPUT_DIR, report_name))

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\n⏱️ Общее время выполнения скрипта: {execution_time:.2f} секунд ({execution_time/60:.2f} минут)")

    except Exception as e:
        print("\n" + "!"*50)
        print(f"ПРОИЗОШЛА КРИТИЧЕСКАЯ ОШИБКА:")
        print(e)
        traceback.print_exc()
        print("!"*50)
        
    input("\nНажмите Enter, чтобы закрыть программу...")

if __name__ == "__main__":
    main()