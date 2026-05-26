import pandas as pd
import numpy as np
import time
import os
import glob
from datetime import datetime
import re
import traceback
from test_utils import ANESTHESIA_DICT, DIFFICULT_DEPARTMENTS, debug_print, generate_html_report


# --- ФУНКЦИИ ГЕНЕРАЦИИ ПОДСКАЗОК ПО РАЗНЫМ СПРАВОЧНИКАМ ---

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

def _get_doc(item):
    if isinstance(item, pd.DataFrame):
        if 'Врач' in item.columns:
            val = str(item['Врач'].iloc[0])
        elif 'Сотрудник' in item.columns:
            val = str(item['Сотрудник'].iloc[0])
        else:
            val = 'Не указан'
    else:
        val = str(item.get('Врач', item.get('Сотрудник', 'Не указан')))
    
    if val.lower() == 'nan' or val.strip() == '':
        return 'Не указан'
    return val.strip()

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
        
    df_mov['ИБ_clean'] = df_mov['Номер ИБ'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_disch['ИБ_clean'] = df_disch['ИБ. Номер'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    df_op['ИБ_clean'] = df_op['ИБ. Номер'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'-\d{4}', '', regex=True).str.strip()
    
    df_patients = pd.merge(df_mov, df_disch, on='ИБ_clean', how='inner', suffixes=('_mov', '_disch'))
    df_full = pd.merge(df_patients, df_op, on='ИБ_clean', how='left', suffixes=('', '_op'))
    
    if 'МЭС. Код' in df_full.columns:
        df_full['МЭС. Код'] = df_full['МЭС. Код'].astype(str).apply(
            lambda x: x.split('.')[0].strip().lstrip('0') if x.startswith('0') else x.split('.')[0].strip()
        )
    
    return df_full

def _check_mscrit_operation_rules(op_row, mscrit_req, ib_num, canal, is_skp, mes_code=""):
    errors = []

    if str(mes_code).strip() != '200513':
        op_code = str(op_row.get('Код_op', op_row.get('Код', ''))).strip()
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

    col_out = 'Дата выбытия'
    if 'Дата окончания' in unique_movs.columns: col_out = 'Дата окончания'
    elif 'Дата выбытия_mov' in unique_movs.columns: col_out = 'Дата выбытия_mov'
        
    col_in = 'Дата поступления'
    if 'Дата начала' in unique_movs.columns: col_in = 'Дата начала'
    elif 'Дата поступления_mov' in unique_movs.columns: col_in = 'Дата поступления_mov'

    if col_out in unique_movs.columns and col_in in unique_movs.columns:
        unique_movs['temp_date'] = pd.to_datetime(unique_movs[col_out], dayfirst=True, errors='coerce')
        sorted_group = unique_movs.sort_values(by=['temp_date', col_in])
    else:
        sorted_group = unique_movs.sort_values(by=col_in if col_in in unique_movs.columns else 'МЭС. Код')

    if len(sorted_group) > 1:
        for idx in range(len(sorted_group) - 1):
            current_row = sorted_group.iloc[idx]
            code = str(current_row['Код прерывания госпитализации']).split('.')[0].strip().upper()
            row_dept = str(current_row.get('Отделение', '')).strip()
            row_doc = _get_doc(current_row)
            dept_lower = row_dept.lower()
            
            if 'дневной стационар' in dept_lower:
                continue
                
            if code != '7':
                display_code = "ПУСТО" if code == 'NAN' else code
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Множественные переводы: промежуточные коды прерывания должны быть строго '<b>7</b>', а в выписке №{idx+1} указано '<b>{display_code}</b>'.")

    last_row_index = len(sorted_group) - 1
    
    for current_idx, (_, row) in enumerate(sorted_group.iterrows()):
        row_dept = str(row.get('Отделение', '')).strip()
        row_doc = _get_doc(row)
        mes_code = str(row['МЭС. Код']).split('.')[0].strip()
        code = str(row['Код прерывания госпитализации']).split('.')[0].strip().upper()

        display_code = "ПУСТО" if code == 'NAN' else code
        mes_clean = mes_code.lstrip('0') if mes_code.startswith('0') else mes_code
        is_special = mes_code in SPECIAL_PROJECT_MES or mes_clean in SPECIAL_PROJECT_MES

        is_last_row = (current_idx == last_row_index)
        if not is_last_row and code == '7':
            continue

        if is_special:
            if patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР', 'НИЛ']:
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Недопустимый МЭС: спецпроект <b>{mes_code}</b> разрешен только для 'ЗЛ', 'ИН' и 'НИЛ' (у вас '<b>{patient_type}</b>').")

            if mes_code.startswith('200'):
                if patient_type == 'НИЛ' and code in ['S', 'С', 'C']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) пациенту 'НИЛ' нельзя ставить '<b>{display_code}</b>'.")
                elif patient_type in ['ЗЛ', 'НР'] and code not in ['S', 'С', 'C']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) у пациента 'ЗЛ' должен быть '<b>S</b>', а указано '<b>{display_code}</b>'.")
                elif patient_type in ['ИН', 'ИНОГОРОДНИЙ'] and code not in ['V', 'В']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) у пациента 'ИН' должен быть '<b>V</b>', а указано '<b>{display_code}</b>'.")
            else:
                if patient_type == 'НИЛ' and code in ['S', 'С', 'C']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) пациенту 'НИЛ' нельзя ставить '<b>{display_code}</b>'.")
                elif patient_type in ['ЗЛ', 'НР'] and code not in ['S', 'С', 'C']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) у пациента 'ЗЛ' должен быть '<b>S</b>', а указано '<b>{display_code}</b>'.")

        elif mes_code.startswith('200'):
            if patient_type == 'НИЛ':
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Недопустимый МЭС: пациентам 'НИЛ' запрещено выставлять МЭС ВМП (<b>{mes_code}</b>).")
            elif patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР']:
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Недопустимый МЭС: МЭС <b>{mes_code}</b> разрешен только для 'ЗЛ' и 'ИН' (у вас '<b>{patient_type}</b>').")
            else:
                if code not in ['V', 'В']:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Код прерывания: для МЭС ВМП (<b>{mes_code}</b>) код должен быть '<b>V</b>', а указано '<b>{display_code}</b>'.")
                
    return list(dict.fromkeys(errors))

def _check_department_rules(group, ib_num):
    errors = []
    reanimation_target_codes = ['056029', '56029']
    unique_movs = group.drop_duplicates(subset=['Отделение', 'МЭС. Код'])
    
    for _, row in unique_movs.iterrows():
        mes_code = str(row.get('МЭС. Код', '')).split('.')[0].strip()
        row_dept = str(row.get('Отделение', '')).strip()
        row_doc = _get_doc(row)
        dept_lower = row_dept.lower()

        is_diag_or_np = 'коечное отделение нп' in dept_lower or 'диагностическ' in dept_lower
        is_mes_84_95 = mes_code.startswith(('95', '095', '84', '084'))

        if is_mes_84_95 and not is_diag_or_np:
            errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Коечном отделении НП или диагностическом (у вас '<b>{row_dept}</b>').")
        elif is_diag_or_np and not is_mes_84_95:
            errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Ошибка МЭС: в '<b>{row_dept}</b>' разрешены только МЭС, начинающиеся на 84 или 95 (у вас указан '<b>{mes_code}</b>').")

        elif mes_code.startswith('183'):
            if 'новорожден' not in dept_lower:
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Отделении реанимации для новорожденных (у вас '<b>{row_dept}</b>').")

        elif mes_code.startswith(('83', '083')) or mes_code in reanimation_target_codes:
            if 'реанимац' not in dept_lower:
                errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в отделениях реанимации (у вас '<b>{row_dept}</b>').")

    return list(dict.fromkeys(errors))

def _check_missing_operation_and_samotek(group, mscrit_match, ib_num, mes_code, mkb_code, canal, department, ref_mscrit, search_mkbs, doctor):
    errors = []

    if str(canal).strip().lower() in ['самотек', 'самотёк', '103 поликлиника']:
        samotek_col = 'Допустимость госпитализации "самотёк"'
        samotek_val = 1
        if samotek_col in mscrit_match.columns:
            val = mscrit_match[samotek_col].iloc[0]
            samotek_val = int(val) if pd.notna(val) else 1
            
        if samotek_val == 0:
            errors.append(f"META::{department}::{doctor}::ИБ {ib_num}: Ошибка канала поступления: госпитализация 'самотёк' невозможна под МЭС <b>{mes_code}</b> и диагноз <b>{mkb_code}</b>.")

    if str(mes_code).strip() == '200513':
        return errors

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
            error_msg = f"META::{department}::{doctor}::ИБ {ib_num}: Ошибка: для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b> обязательна хирургическая операция, но она отсутствует."
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
            
    return errors

# --- НОВАЯ ФУНКЦИЯ ДЛЯ БЛОКА ОПЕРАЦИЙ ---

def _validate_operations_and_diagnoses(group, ref_mscrit, ref_msmkbe, ref_reeskp, mes_code, mkb_code, search_mkbs, ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, patient_type, doctor):
    errors = []
    performed_ops = []
    seen = set()
    
    for row in group.to_dict('records'):
        op_code = str(row.get('Код_op', row.get('Код', row.get('Код операции', '')))).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        
        if op_code.lower() in ['nan', '', 'none']:
            continue
            
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
                op_code = str(row.get('Код_op', row.get('Код', ''))).strip()
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
                    (ref_mscrit['Код хирургической операции'] == op_code)
                ]
                if not mscrit_match.empty:
                    valid_candidates.append((row, mscrit_match.iloc[0]))
                    
            if not valid_candidates:
                for row in performed_ops:
                    op_code = str(row.get('Код_op', row.get('Код', ''))).strip()
                    fallback_match = ref_mscrit[
                        (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                        (ref_mscrit['Код хирургической операции'] == op_code)
                    ]
                    if not fallback_match.empty:
                        valid_candidates.append((row, fallback_match.iloc[0]))
        
        if not valid_candidates:
            op_codes_str = ", ".join(sorted(list(set([str(r.get('Код_op', r.get('Код', ''))).strip() for r in performed_ops]))))
            if has_diag_error:
                error_msg = f"META::{department}::{doctor}::ИБ {ib_num}: 🚨 <b style='color:var(--error-border);'>ДВОЙНАЯ ОШИБКА:</b> Базовая проверка диагноза ({diag_error_msg}), И ни одна из операций (<b>{op_codes_str}</b>) не подходит."
            else:
                error_msg = f"META::{department}::{doctor}::ИБ {ib_num}: Ошибка операции: ни одна из проведенных операций (<b>{op_codes_str}</b>) не предусмотрена справочником mscrit для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b>."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
            if has_diag_error:
                error_msg = f"META::{department}::{doctor}::ИБ {ib_num}: Базовая проверка диагноза: {diag_error_msg}."
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
                op_errs = _check_mscrit_operation_rules(row, mscrit_req, ib_num, canal, is_skp, mes_code)
                if not op_errs:
                    perfect_match_found = True
                    break
                else:
                    formatted_op_errs = [f"META::{department}::{doctor}::{e}" if not e.startswith("META::") else e for e in op_errs]
                    candidate_errors.extend(formatted_op_errs)
                    
            if not perfect_match_found:
                unique_candidate_errors = list(dict.fromkeys(candidate_errors))
                errors.extend(unique_candidate_errors)
    else:
        if has_diag_error:
            error_msg = f"META::{department}::{doctor}::ИБ {ib_num}: Базовая проверка диагноза: {diag_error_msg}."
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
                        group, mscrit_match, ib_num, mes_code, mkb_code, canal, department, ref_mscrit, search_mkbs, doctor
                    )
                    errors.extend(missing_op_errors)

    return errors

# --- ЛОГИКА ПАЦИЕНТОВ ---

def check_reanimation_logic(group, ib_num):
    errors = []
    try:
        col_in = 'Дата поступления'
        col_out = 'Дата выбытия'
        
        if 'Дата начала' in group.columns: col_in = 'Дата начала'
        elif 'Дата поступления_mov' in group.columns: col_in = 'Дата поступления_mov'
        
        if 'Дата окончания' in group.columns: col_out = 'Дата окончания'
        elif 'Дата выбытия_mov' in group.columns: col_out = 'Дата выбытия_mov'

        if col_out not in group.columns or col_in not in group.columns:
            return [f"ИБ {ib_num}: [Реанимация] В таблицах не найдены колонки дат перевода для расчета дней."]
            
        unique_movs = group.drop_duplicates(subset=[col_in, col_out, 'Отделение']).copy()
        unique_movs['temp_date'] = pd.to_datetime(unique_movs[col_out], dayfirst=True, errors='coerce')
        sorted_movs = unique_movs.sort_values(by=['temp_date', col_in])
        last_mov_idx = sorted_movs.index[-1] if not sorted_movs.empty else None
        
        rean_rows = unique_movs[unique_movs['Отделение'].astype(str).str.lower().str.contains('реанимац', na=False)]
        
        if rean_rows.empty:
            rean_rows = unique_movs 

        for idx, row in rean_rows.iterrows():
            mes_code = str(row.get('МЭС. Код', group['МЭС. Код'].iloc[0])).split('.')[0].strip()
            row_dept = str(row.get('Отделение', 'Реанимации')).strip()
            row_doc = _get_doc(row)

            reanimation_target_codes = ['056029', '56029', '083010', '083020', '083030', '083040', '083050', '183010', '183020', '183030', '183040', '183050', '83010', '83020', '83030', '83040', '83050']

            is_last_movement = (idx == last_mov_idx)
            
            if mes_code not in reanimation_target_codes:
                if is_last_movement:
                    continue
                else:
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: [Реанимация] Ошибка МЭС: в '{row_dept}' указан непрофильный МЭС <b>{mes_code}</b>. Для нахождения в реанимации требуется специальный МЭС.")
                    continue 

            if pd.notna(row[col_in]) and pd.notna(row[col_out]):
                d_in = pd.to_datetime(row[col_in], dayfirst=True)
                d_out = pd.to_datetime(row[col_out], dayfirst=True)

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
                    errors.append(f"META::{row_dept}::{row_doc}::ИБ {ib_num}: [Реанимация] В '{row_dept}' пациент находился <b>{time_str}</b>. По правилам ожидался один из МЭС: <b>{expected_codes}</b>, но у вас указан <b>'{mes_code}'</b>.")

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
    doctor = _get_doc(group)
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
        ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, 'НИЛ', doctor
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
    doctor = _get_doc(group)
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
                    errors.append(f"META::{department}::{doctor}::ИБ {ib_num}: [СКП] Ошибка признака оплаты: для иногородних он должен быть '<b>1</b>', а у вас стоит '<b>{priznak}</b>'.")
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
        ib_num, department, canal, is_skp, has_diag_error, diag_error_msg, patient_type, doctor
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
        
        # --- ЗАГРУЗКА КЛИНИЧЕСКИХ РЕКОМЕНДАЦИЙ ---
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
        
        # --- ЗАГРУЗКА РЕКОМЕНДАЦИЙ ДЛЯ ЭКСТРЕННОЙ ГОСПИТАЛИЗАЦИИ ---
        emerg_file = os.path.join(REF_DIR, 'emergency_recs.xlsx')
        emerg_dict = {}
        if os.path.exists(emerg_file):
            emerg_df = pd.read_excel(emerg_file)
            emerg_df.columns = emerg_df.columns.astype(str).str.replace('\n', '').str.replace('\r', '').str.strip()
            
            if 'Код услуги' in emerg_df.columns and 'Код по МКБ-10' in emerg_df.columns:
                emerg_df['Код услуги'] = emerg_df['Код услуги'].astype(str).str.split('.').str[0].str.strip().str.lstrip('0')
                emerg_df['Код по МКБ-10'] = emerg_df['Код по МКБ-10'].astype(str).str.strip().str.upper()
                emerg_df = emerg_df.fillna('')
                
                for _, r in emerg_df.iterrows():
                    m = r['Код услуги']
                    d = r['Код по МКБ-10']
                    key = f"{m}_{d}"
                    if key not in emerg_dict:
                        emerg_dict[key] = []

                    emerg_dict[key].append({
                        '№ п/п': r.get('№ п/п', ''),
                        'Код услуги': m,
                        'Наименование услуги': r.get('Наименование услуги', ''),
                        'Код по МКБ-10': d,
                        'Критерии': r.get('Критерии экстренной госпитализации', ''),
                        'Профиль': r.get('Профиль', '')
                    })
        else:
            print("⚠️ Файл emergency_recs.xlsx не найден в папке references. Подсказки по экстренной госпитализации будут отключены.")

        all_errors = []
        criteria_set = set()
        
        reanimation_target_codes = ['056029', '56029', '083010', '083020', '083030', '083040', '083050', '183010', '183020', '183030', '183040', '183050', '83010', '83020', '83030', '83040', '83050']
        
        if 'Тип оплаты' in df_merged.columns:
            excluded_types = [
                'ПМУ', 
                'ПМУ (С ФИЗ.ЛИЦОМ)', 
                'ПМУ (С ЮР.ЛИЦОМ)', 
                'ДМС', 
                'БЮДЖЕТ', 
                'ГОС. ЗАДАНИЕ'
            ]
            
            df_merged = df_merged[~df_merged['Тип оплаты'].astype(str).str.upper().str.strip().isin(excluded_types)]

        grouped = df_merged.groupby('ИБ_clean')
        print(f"Обнаружено пациентов (ИБ): {len(grouped)}. Начинаю проверку...")

        for ib, group in grouped:
            debug_print(f"--- Обработка ИБ: {ib} ---")

            dept_errors = _check_department_rules(group, ib)
            if dept_errors:
                for err in dept_errors:
                    if err.startswith("META::"):
                        _, spec_dept, spec_doc, msg = err.split("::", 3)
                        all_errors.append({'department': spec_dept, 'doctor': spec_doc, 'message': msg})
                    else:
                        department_fallback = str(group['Отделение'].iloc[0]).strip()
                        doc_fallback = _get_doc(group)
                        all_errors.append({'department': department_fallback, 'doctor': doc_fallback, 'message': err})
                continue 
                
            temp_errors = []
            
            has_rean_dept = group['Отделение'].astype(str).str.lower().str.contains('реанимац', na=False).any()
            mes_names = " ".join(group['МЭС. Название'].astype(str).str.lower().unique())
            has_rean_mes = any(str(mc).strip() in reanimation_target_codes for mc in group['МЭС. Код'].unique())
            
            if has_rean_dept or ('реанимация' in mes_names) or has_rean_mes:
                temp_errors.extend(check_reanimation_logic(group, ib))
                
            temp_errors.extend(_check_interruption_code(group, ib))

            unique_movements = group.drop_duplicates(subset=['МЭС. Код', 'Отделение'])
            
            for _, mov_row in unique_movements.iterrows():
                mes_code = str(mov_row['МЭС. Код']).strip()
                mes_clean = mes_code.lstrip('0') if mes_code.startswith('0') else mes_code
                is_pure_rean_mes = (mes_code in reanimation_target_codes) or (mes_clean in reanimation_target_codes)
                
                department = str(mov_row['Отделение']).strip()
                doctor = _get_doc(mov_row)

                target_mes = mes_code.lstrip('0') if mes_code.startswith('0') else mes_code

                if mes_code in recs_dict or target_mes in recs_dict:
                    found_mes = mes_code if mes_code in recs_dict else target_mes
                    temp_errors.append(f"META::{department}::{doctor}::ИБ {ib}: 💡 <b>Клинические рекомендации:</b> для МЭС <span class='clickable-mes' onclick='openModal(\"{found_mes}\")'>{mes_code}</span> имеются обязательные критерии. Кликните на номер МЭС для просмотра.")

                sub_group = group[group['МЭС. Код'] == mov_row['МЭС. Код']]
                canal = str(sub_group['Канал по ДЗМ-56'].iloc[0]).strip().lower() if 'Канал по ДЗМ-56' in sub_group.columns else ''

                if canal in ['самотек', 'самотёк', '103 поликлиника']:
                    mkb_code_full = str(sub_group['Диагноз. МКБ-10'].iloc[0]).strip().upper() if 'Диагноз. МКБ-10' in sub_group.columns else ''
                    mkb_base = mkb_code_full.split('.')[0]
                    
                    key_full = f"{target_mes}_{mkb_code_full}"
                    key_base = f"{target_mes}_{mkb_base}"
                    
                    found_emerg_key = None
                    if key_full in emerg_dict: found_emerg_key = key_full
                    elif key_base in emerg_dict: found_emerg_key = key_base
                    elif f"{mes_code}_{mkb_code_full}" in emerg_dict: found_emerg_key = f"{mes_code}_{mkb_code_full}"
                    elif f"{mes_code}_{mkb_base}" in emerg_dict: found_emerg_key = f"{mes_code}_{mkb_base}"
                    
                    if found_emerg_key:
                        temp_errors.append(f"META::{department}::{doctor}::ИБ {ib}: 💡 <b>Экстренная госпитализация:</b> Этот пациент поступил по каналу 'самотёк'. Для МЭС <span class='clickable-mes' style='background:#e67e22;' onclick='openEmergModal(\"{found_emerg_key}\")'>{mes_code}</span> и диагноза <b>{mkb_code_full}</b> есть критерии экстренности. Кликните на МЭС для просмотра.")

                if not is_pure_rean_mes:
                    patient_type = str(sub_group['ПУМП. Тип пациента'].iloc[0]).strip().upper() if 'ПУМП. Тип пациента' in sub_group.columns else 'UNKNOWN'
                    
                    if patient_type == 'НР':
                        mother_ib = str(ib).split('/')[0].strip()
                        if mother_ib in grouped.groups:
                            mother_group = grouped.get_group(mother_ib)
                            patient_type = str(mother_group['ПУМП. Тип пациента'].iloc[0]).strip().upper()
                            
                    if patient_type == 'NAN' or patient_type == '':
                        continue
                        
                    if patient_type == 'НИЛ':
                        debug_print(f"ИБ {ib}: Проверка НИЛ (МЭС {mes_code})")
                        temp_errors.extend(check_nil_patient(sub_group, ref_msmkbe, ref_mscrit, ref_mkb10))
                    elif patient_type in ['ИН', 'ИНОГОРОДНИЙ', 'ЗЛ', 'НР']: 
                        debug_print(f"ИБ {ib}: Проверка Стандарт (МЭС {mes_code})")
                        temp_errors.extend(check_standard_patient(sub_group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10, patient_type))
                    else:
                        temp_errors.append(f"META::{department}::{doctor}::ИБ {ib}: Невозможно классифицировать пациента (тип: <b>'{patient_type}'</b>).")
            
            # 3. СБОР И ОЧИСТКА ОШИБОК
            unique_temp_errors = list(dict.fromkeys(temp_errors))
            
            for err in unique_temp_errors:
                if err.startswith("META::"):
                    parts = err.split("::", 3)
                    if len(parts) == 4:
                        _, spec_dept, spec_doc, msg = parts
                        all_errors.append({'department': spec_dept, 'doctor': spec_doc, 'message': msg})
                    else:
                        all_errors.append({'department': 'Неизвестно', 'doctor': 'Не указан', 'message': err})
                else:
                    department_fallback = str(group['Отделение'].iloc[-1]).strip()
                    doctor_fallback = _get_doc(group.iloc[-1])
                    all_errors.append({'department': department_fallback, 'doctor': doctor_fallback, 'message': err})
                
        print("\n" + "="*50)
        print(f"ПРОВЕРКА ЗАВЕРШЕНА. НАЙДЕНО ОШИБОК И ПОДСКАЗОК: {len(all_errors)}")
        print("="*50)

        for err_dict in all_errors:
            clean_msg = re.sub(r'<[^>]+>', '', err_dict['message'])
            print(f"[{err_dict['department']} | {err_dict['doctor']}] {clean_msg}")

        checked_data = []
        try:
            checked_files = glob.glob(os.path.join(INPUT_DIR, '*Проверенные*.xls*'))
            if checked_files:
                checked_file_path = checked_files[0]
                df_checked = pd.read_excel(checked_file_path)

                df_checked.columns = df_checked.columns.str.strip()

                target_cols = ['№ МК', 'Отделение', 'Сотрудник', 'Тип пациента', 'Дата окончания', 'ИД ПУМП']

                actual_cols = [col for col in target_cols if col in df_checked.columns]
                
                if len(actual_cols) >= 4:
                    df_clean = df_checked[actual_cols].fillna('')

                    if 'ИД ПУМП' in df_clean.columns:
                        df_clean = df_clean[
                            (df_clean['ИД ПУМП'].astype(str).str.strip() != '0') & 
                            (df_clean['ИД ПУМП'].astype(str).str.strip() != '0.0') & 
                            (df_clean['ИД ПУМП'].astype(str).str.strip() != 'nan') & 
                            (df_clean['ИД ПУМП'].astype(str).str.strip() != '')
                        ]

                    if 'Дата окончания' in df_clean.columns:
                        def format_ru_date(val):
                            val = str(val).strip()
                            if not val or val.lower() == 'nan': return 'Нет даты'
                            date_part = val.split(' ')[0]
                            if '-' in date_part and len(date_part) == 10:
                                parts = date_part.split('-')
                                if len(parts[0]) == 4:
                                    return f"{parts[2]}.{parts[1]}.{parts[0]}"
                            return date_part.replace('-', '.')
                        
                        df_clean['Дата выбытия'] = df_clean['Дата окончания'].apply(format_ru_date)
                    else:
                        df_clean['Дата выбытия'] = 'Нет даты'

                    final_html_cols = ['№ МК', 'Отделение', 'Сотрудник', 'Тип пациента', 'Дата выбытия']
                    html_cols_to_keep = [c for c in final_html_cols if c in df_clean.columns]

                    checked_data = df_clean[html_cols_to_keep].to_dict('records')
                    print(f"✅ Успешно загружено проверенных карт (ИД ПУМП > 0): {len(checked_data)}")
                else:
                    print(f"⚠️ В файле {checked_file_path} не найдены нужные колонки.")
            else:
                print("⚠️ Файл с проверенными картами (*Проверенные*.xls*) не найден в input_data.")
        except Exception as e:
            print(f"⚠️ Ошибка при обработке файла проверенных карт: {e}")

        if all_errors or checked_data:
            current_time = datetime.now().strftime("%d.%m.%Y_%H-%M")
            report_name = f"report_{current_time}.html"
            generate_html_report(all_errors, recs_dict, checked_data, emerg_dict, output_path=os.path.join(INPUT_DIR, report_name))

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