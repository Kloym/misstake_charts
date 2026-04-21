import pandas as pd
import numpy as np
import os
from datetime import datetime
import math

# --- НАСТРОЙКИ И СЛОВАРИ ---

DEBUG_MODE = False 

ANESTHESIA_DICT = {
    "Местная": 0,
    "Аппликационная": 0,
    "Инфильтрационная": 0, 
    "Инфильрационная": 0,  
    "Комбинированная общая анестезия с миорелаксантами и ИВЛ": 1,
    "Тотальная внутривенная анестезия с миорелаксантами и ИВЛ": 1,
    "Ингаляционная анестезия с сохранением спонтанного дыхания": 1,
    "Внутривенная анестезия с сохранением спонтанного дыхания": 1,
    "Мониторинг анестезиологом с контролем седации и анальгезии (МАКС)": 1,
    "Спинальная анестезия": 1, 
    "Эпидуральная анестезия": 1,
    "Спинально-эпидуральная анастезия": 1, 
    "Спинально-эпидуральная анестезия": 1, 
    "Проводниковая": 1,
    "Межфасциальная блокада": 0
}

DIFFICULT_DEPARTMENTS = [
    "хирургическое отделение", 
    "травматологическое отделение", 
    "терапевтическое отделение",
    "отделение гнойной хирургии",
    "отделение сосудистой хирургии",
]

def debug_print(msg):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

# --- ФУНКЦИЯ ГЕНЕРАЦИИ HTML ---

def generate_html_report(errors_data, output_path):
    unique_depts = sorted(list(set([err['department'] for err in errors_data])))
    dept_checkboxes = ""
    for d in unique_depts:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb" onchange="filterTable()"> {d}</label></li>\n'
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Отчет по ошибкам (mscrit)</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 30px 20px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            
            /* --- ШАПКА И ПАНЕЛИ ФИЛЬТРОВ --- */
            h1 {{ margin: 0 0 20px 0; font-size: 1.5em; color: #2c3e50; }}
            
            .controls {{ background: #fdfdfd; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin-bottom: 20px; }}
            .stats {{ font-weight: bold; color: #3498db; font-size: 1.1em; margin-bottom: 15px; }}
            
            .filters-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
            .filter-group {{ display: flex; flex-direction: column; gap: 5px; }}
            .filter-group label {{ font-size: 0.85em; font-weight: 600; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; }}
            input[type="text"] {{ padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; outline: none; }}
            input[type="text"]:focus {{ border-color: #3498db; }}
            
            /* Мультиселект отделений */
            .dropdown-check-list {{ display: inline-block; position: relative; width: 100%; }}
            .dropdown-check-list .anchor {{ width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fff; cursor: pointer; display: block; box-sizing: border-box; font-size: 14px; user-select: none; color: #333; }}
            .dropdown-check-list .anchor:after {{ content: '▼'; float: right; font-size: 10px; color: #7f8c8d; margin-top: 4px; }}
            .dropdown-check-list .items {{ padding: 8px; display: none; position: absolute; background: #fff; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 100%; box-sizing: border-box; z-index: 100; max-height: 250px; overflow-y: auto; margin: 0; list-style: none; }}
            .dropdown-check-list.visible .items {{ display: block; }}
            .dropdown-check-list ul.items li {{ list-style: none; margin-bottom: 5px; font-size: 13px; }}
            .dropdown-check-list ul.items li label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px; border-radius: 4px; }}
            .dropdown-check-list ul.items li label:hover {{ background: #f4f6f6; }}
            
            /* --- ПАНЕЛЬ ЭКСПОРТА --- */
            .export-panel {{ background: #fdfdfd; border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 10px; }}
            .export-panel strong {{ color: #2c3e50; font-size: 1.1em; }}
            .export-controls {{ display: flex; gap: 15px; align-items: stretch; }}
            #summaryText {{ flex-grow: 1; padding: 10px 15px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 13px; outline: none; resize: vertical; min-height: 60px; white-space: pre; color: #555; background: #fff; }}
            .btn-copy {{ background: #27ae60; color: white; border: none; padding: 0 20px; border-radius: 4px; cursor: pointer; font-weight: bold; transition: background 0.2s; white-space: nowrap; font-size: 14px; }}
            .btn-copy:hover {{ background: #2ecc71; }}
            
            /* --- ТАБЛИЦА (КЛАССИЧЕСКИЙ СИНИЙ ДИЗАЙН) --- */
            .table-container {{ overflow-x: auto; max-height: 65vh; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px; }}
            table {{ width: 100%; border-collapse: collapse; background: #fff; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
            
            th {{ background-color: #3498db; color: #ffffff; position: sticky; top: 0; z-index: 50; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            
            tbody tr:hover {{ background-color: #fcfcfc; }}
            
            .ib-col {{ font-weight: bold; color: #d35400; font-size: 15px; }}
            .error-col {{ color: #333; font-size: 14px; line-height: 1.5; }}
            .error-col b {{ color: #333; }} /* Возвращаем черный цвет для жирного текста */
            .dept-col {{ color: #7f8c8d; font-size: 13px; font-weight: 500; }}
            
            .fixed-row td {{ text-decoration: line-through; opacity: 0.5; background-color: #f9f9f9; }}
            .checkbox-custom {{ width: 18px; height: 18px; cursor: pointer; accent-color: #27ae60; margin-top: 2px; }}
            .hidden-row {{ display: none !important; }}
            
            .context-tag {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; font-weight: bold; margin-bottom: 5px; background-color: #f39c12; color: white; }}
            .tag-rean {{ background-color: #e74c3c; }}
            
            /* Подсказки */
            .hint-details {{ margin-top: 10px; border: 1px solid #eee; border-radius: 4px; overflow: hidden; background: #fafafa; }}
            .hint-details summary {{ padding: 8px 12px; cursor: pointer; font-weight: 600; color: #2980b9; font-size: 13px; outline: none; user-select: none; }}
            .hint-details summary:hover {{ background: #f0f0f0; }}
            .hint-content {{ padding: 10px 15px; border-top: 1px solid #eee; background: #fff; max-height: 250px; overflow-y: auto; font-size: 13px; color: #555; }}
            .hint-content ul {{ margin: 0; padding-left: 20px; }}
            .hint-content li {{ margin-bottom: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📝 Готовый ответ для оператора:</h1>
            
            <div class="controls">
                <div class="stats-row">
                    <div class="stats" id="statsCount">Отображено ошибок: {len(errors_data)}</div>
                </div>
                
                <div class="filters-grid">
                    <div class="filter-group">
                        <label>Отделение:</label>
                        <div id="deptCheckList" class="dropdown-check-list" tabindex="100">
                            <span class="anchor" onclick="toggleDeptDrop()">Выбраны все отделения</span>
                            <ul class="items">
                                <li><label><input type="checkbox" id="selectAllDepts" checked onchange="toggleAllDepts(this)"> <b>(Выбрать все)</b></label></li>
                                {dept_checkboxes}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="filter-group">
                        <label>Поиск по ИБ:</label>
                        <input type="text" id="ibFilter" onkeyup="filterTable()" placeholder="Введите номер ИБ...">
                    </div>
                    
                    <div class="filter-group">
                        <label>Поиск по тексту:</label>
                        <input type="text" id="errorFilter" onkeyup="filterTable()" placeholder="Введите текст или код ошибки...">
                    </div>
                </div>
            </div>
            
            <div class="export-panel">
                <div class="export-controls">
                    <textarea id="summaryText" readonly placeholder="Отметьте галочками исправленные ИБ в таблице ниже..."></textarea>
                    <button class="btn-copy" onclick="copySummary()" id="copyBtn">Скопировать</button>
                </div>
            </div>
            
            <div class="table-container">
                <table id="errorsTable">
                    <thead>
                        <tr>
                            <th width="5%">Испр.</th>
                            <th width="25%">Отделение</th>
                            <th width="15%">Номер ИБ</th>
                            <th>Описание ошибки / Подсказка</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, err_dict in enumerate(errors_data):
        dept = err_dict['department']
        err_msg = err_dict['message']
        
        parts = err_msg.split(':', 1)
        if len(parts) == 2:
            ib_text = parts[0].strip().replace("ИБ ", "") 
            error_text = parts[1].strip()
        else:
            ib_text = "Неизвестно"
            error_text = err_msg
            
        error_text = error_text.replace("[СКП]", "<span class='context-tag tag-skp'>СКП</span>")
        error_text = error_text.replace("[СКП ЗЛ]", "<span class='context-tag tag-skp'>СКП ЗЛ</span>")
        error_text = error_text.replace("[Реанимация]", "<span class='context-tag tag-rean'>Реанимация</span>")
        error_text = error_text.replace("[Реанимация новорожденных]", "<span class='context-tag tag-rean'>Реанимация новорожденных</span>")
            
        if "<div class='hint-wrapper'>" in error_text:
            main_err, hint_html = error_text.split("<div class='hint-wrapper'>", 1)
            hint_html = "<div class='hint-wrapper'>" + hint_html
        else:
            main_err = error_text
            hint_html = ""
            
        # Убрали красные рамки, оставляем чистый текст
        styled_error = main_err
        safe_dept = dept.replace("'", "\\'")
            
        html_content += f"""
                        <tr id="row_{i}" class="data-row" data-dept="{dept}">
                            <td><input type="checkbox" class="checkbox-custom" id="check_{i}" onclick="toggleFix({i}, '{ib_text}', '{safe_dept}')"></td>
                            <td class="dept-col">{dept}</td>
                            <td class="ib-col">{ib_text}</td>
                            <td class="error-col">{styled_error}{hint_html}</td>
                        </tr>
        """
        
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            // --- МУЛЬТИСЕЛЕКТ ОТДЕЛЕНИЙ ---
            const checkList = document.getElementById('deptCheckList');
            function toggleDeptDrop() {
                checkList.classList.toggle('visible');
            }
            
            document.addEventListener('click', function(event) {
                if (!checkList.contains(event.target)) {
                    checkList.classList.remove('visible');
                }
            });

            function toggleAllDepts(source) {
                const checkboxes = document.querySelectorAll('.dept-cb');
                checkboxes.forEach(cb => cb.checked = source.checked);
                updateDeptLabel();
                filterTable();
            }

            document.querySelectorAll('.dept-cb').forEach(cb => {
                cb.addEventListener('change', function() {
                    const allChecked = document.querySelectorAll('.dept-cb:checked').length === document.querySelectorAll('.dept-cb').length;
                    document.getElementById('selectAllDepts').checked = allChecked;
                    updateDeptLabel();
                });
                cb.checked = true; 
            });

            function updateDeptLabel() {
                const total = document.querySelectorAll('.dept-cb').length;
                const checked = document.querySelectorAll('.dept-cb:checked').length;
                const anchor = checkList.querySelector('.anchor');
                if (checked === total) anchor.innerText = "Выбраны все отделения";
                else if (checked === 0) anchor.innerText = "Ничего не выбрано";
                else anchor.innerText = `Выбрано отделений: ${checked}`;
            }

            // --- ФИЛЬТРАЦИЯ ТАБЛИЦЫ ---
            function filterTable() {
                const ibSearch = document.getElementById("ibFilter").value.toLowerCase();
                const errSearch = document.getElementById("errorFilter").value.toLowerCase();
                
                const checkedDepts = Array.from(document.querySelectorAll('.dept-cb:checked')).map(cb => cb.value);
                const rows = document.getElementsByClassName("data-row");
                let visibleCount = 0;
                
                for (let i = 0; i < rows.length; i++) {
                    const row = rows[i];
                    const dept = row.getAttribute("data-dept");
                    const ib = row.querySelector(".ib-col").innerText.toLowerCase();
                    const err = row.querySelector(".error-col").innerText.toLowerCase();
                    
                    const matchesDept = checkedDepts.includes(dept);
                    const matchesIB = ib.includes(ibSearch);
                    const matchesErr = err.includes(errSearch);
                    
                    if (matchesDept && matchesIB && matchesErr) {
                        row.classList.remove("hidden-row");
                        visibleCount++;
                    } else {
                        row.classList.add("hidden-row");
                    }
                }
                document.getElementById("statsCount").innerText = "Отображено ошибок: " + visibleCount;
            }

            // --- ТАБЛИЦА И ЭКСПОРТ (СТОЛБИКОМ) ---
            let fixedIBs = new Map();

            function toggleFix(index, ibNumber, deptName) {
                const row = document.getElementById('row_' + index);
                const checkbox = document.getElementById('check_' + index);
                
                const textLine = ibNumber + " (" + deptName + ")";
                const entryId = index; 
                
                if (checkbox.checked) {
                    row.classList.add('fixed-row');
                    fixedIBs.set(entryId, textLine);
                } else {
                    row.classList.remove('fixed-row');
                    fixedIBs.delete(entryId);
                }
                updateSummary();
            }
            
            function updateSummary() {
                const summaryInput = document.getElementById('summaryText');
                if (fixedIBs.size === 0) {
                    summaryInput.value = "";
                } else {
                    const uniqueLines = Array.from(new Set(fixedIBs.values()));
                    summaryInput.value = "Поправили:\\n" + uniqueLines.join("\\n");
                }
            }
            
            function copySummary() {
                if (fixedIBs.size === 0) { alert("Сначала отметьте галочками исправленные ошибки в таблице!"); return; }
                const copyText = document.getElementById("summaryText");
                copyText.select();
                document.execCommand("copy");
                const btn = document.getElementById('copyBtn');
                btn.innerText = "✅ Скопировано!";
                setTimeout(() => btn.innerText = "Скопировать", 2000);
            }
        </script>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n[УСПЕХ] HTML-отчет успешно сгенерирован: {output_path}")

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

def load_and_merge_data(mov_path, disch_path, op_path):
    df_mov = pd.read_excel(mov_path)
    df_disch = pd.read_excel(disch_path)
    df_op = pd.read_excel(op_path)
    
    if 'Код' in df_mov.columns and 'Код прерывания госпитализации' not in df_mov.columns:
        df_mov.rename(columns={'Код': 'Код прерывания госпитализации'}, inplace=True)
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
        
    mes_code = str(group['МЭС. Код'].iloc[0]).split('.')[0].strip()
    patient_type = str(group['ПУМП. Тип пациента'].iloc[0]).strip().upper() if 'ПУМП. Тип пациента' in group.columns else 'UNKNOWN'
    
    SPECIAL_PROJECT_MES = ['200531', '79550', '79018', '200627', '79008', '66213', '66212', '200031', '200510', '66275', '200625', '200664', '200667', '72044', '200088', '72039', '76951', '76242', '82031', '82043', '82044', '82045', '82055', '200665', '200711']

    if mes_code in SPECIAL_PROJECT_MES:
        if patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР']:
            errors.append(f"ИБ {ib_num}: Недопустимый МЭС: спецпроект <b>{mes_code}</b> разрешен только для '<b>ЗЛ</b>' и '<b>ИН</b>' (у вас '<b>{patient_type}</b>').")
    elif mes_code.startswith('200'):
        if patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ', 'НР']:
            errors.append(f"ИБ {ib_num}: Недопустимый МЭС: МЭС <b>{mes_code}</b> разрешен только для '<b>ЗЛ</b>' и '<b>ИН</b>' (у вас '<b>{patient_type}</b>').")

    unique_movs = group.drop_duplicates(subset=['Дата поступления', 'Отделение', 'Код прерывания госпитализации'])
    sorted_group = unique_movs.sort_values(by='Дата поступления').dropna(subset=['Код прерывания госпитализации'])
    
    if sorted_group.empty:
        return errors

    
    last_row = sorted_group.iloc[-1]
    last_code = str(last_row['Код прерывания госпитализации']).split('.')[0].strip().upper()

    if last_code != 'NAN':
        if mes_code in SPECIAL_PROJECT_MES:
            if mes_code.startswith('200'):
                if patient_type in ['ИН', 'ИНОГОРОДНИЙ']:
                    if last_code not in ['S', 'С', 'C', 'V', 'В']:
                        errors.append(f"ИБ {ib_num}: Код прерывания: для МЭС ВМП спецпроекта (<b>{mes_code}</b>) у пациента 'ИН' должен быть '<b>S</b>' или '<b>V</b>', а указан '<b>{last_code}</b>'.")
                else:
                    if last_code not in ['S', 'С', 'C']:
                        errors.append(f"ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) код должен быть '<b>S</b>', а указан '<b>{last_code}</b>'.")
            else:
                if patient_type in ['ИН', 'ИНОГОРОДНИЙ']:
                    if last_code not in ['0', 'S', 'С', 'C']:
                        errors.append(f"ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) у пациента 'ИН' должен быть '<b>0</b>' или '<b>S</b>', а указан '<b>{last_code}</b>'.")
                else:
                    if last_code not in ['S', 'С', 'C']:
                        errors.append(f"ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) код должен быть '<b>S</b>', а указан '<b>{last_code}</b>'.")
                        
        elif mes_code.startswith('200'):
            if last_code not in ['V', 'В']:
                errors.append(f"ИБ {ib_num}: Код прерывания: для МЭС ВМП (<b>{mes_code}</b>) код последнего движения должен быть '<b>V</b>', а указан '<b>{last_code}</b>'.")
                
    return errors

def _check_department_rules(group, ib_num):
    errors = []

    reanimation_target_codes = ['056029', '56029']

    unique_movs = group.drop_duplicates(subset=['Отделение', 'МЭС. Код'])
    
    for _, row in unique_movs.iterrows():
        mes_code = str(row.get('МЭС. Код', '')).split('.')[0].strip()
        department = str(row.get('Отделение', '')).strip()
        dept_lower = department.lower()

        if mes_code.startswith(('95', '095', '84', '084')):
            if 'коечное отделение нп' not in dept_lower and 'диагностическ' not in dept_lower:
                errors.append(f"ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Коечном отделении НП или диагностическом (у вас '<b>{department}</b>').")

        elif mes_code.startswith('183'):
            if 'новорожден' not in dept_lower:
                errors.append(f"ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в Отделении реанимации для новорожденных (у вас '<b>{department}</b>').")

        elif mes_code.startswith(('83', '083')) or mes_code in reanimation_target_codes:
            if 'реанимац' not in dept_lower:
                errors.append(f"ИБ {ib_num}: Ошибка отделения: МЭС <b>{mes_code}</b> допустим только в отделениях реанимации (у вас '<b>{department}</b>').")

    return list(dict.fromkeys(errors))

# --- ЛОГИКА ИСКЛЮЧЕНИЙ И ПАЦИЕНТОВ ---

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

            reanimation_target_codes = ['056029', '56029', '083010', '083020', '083030', '083040', '083050', '183010', '83010', '83020', '83030', '83040', '83050']
            if mes_code not in reanimation_target_codes:
                continue

            if mes_code.startswith('183'):
                if mes_code != '183010':
                    dept = str(row.get('Отделение', 'Реанимации'))
                    errors.append(f"ИБ {ib_num}: [Реанимация новорожденных] В '{dept}' допускается только МЭС <b>183010</b>, но у вас указан <b>'{mes_code}'</b>.")
                continue 

            if pd.notna(row['Дата поступления']) and pd.notna(row['Дата выбытия']):
                d_in = pd.to_datetime(row['Дата поступления'], dayfirst=True)
                d_out = pd.to_datetime(row['Дата выбытия'], dayfirst=True)

                hours = (d_out - d_in).total_seconds() / 3600.0
                if hours <= 0: 
                    continue

                days = (d_out.date() - d_in.date()).days
                if days == 0:
                    days = 1

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
                    dept = str(row.get('Отделение', 'Реанимации'))
                    errors.append(f"ИБ {ib_num}: [Реанимация] В '{dept}' пациент находился <b>{time_str}</b>. По правилам ожидался один из МЭС: <b>{expected_codes}</b>, но у вас указан <b>'{mes_code}'</b>.")

    except Exception as e:
        errors.append(f"ИБ {ib_num}: [Реанимация] Программная ошибка при расчете времени ({e}).")

    errors.extend(_check_interruption_code(group, ib_num))
    
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
        
    # --- БЛОК ОПЕРАЦИЙ ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', '']:
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
                op_code = str(row['Код']).strip()
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
                    (ref_mscrit['Код хирургической операции'] == op_code)
                ]
                if not mscrit_match.empty:
                    valid_candidates.append((row, mscrit_match.iloc[0]))
                    
            if not valid_candidates:
                for row in performed_ops:
                    op_code = str(row['Код']).strip()
                    fallback_match = ref_mscrit[
                        (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                        (ref_mscrit['Код хирургической операции'] == op_code)
                    ]
                    if not fallback_match.empty:
                        valid_candidates.append((row, fallback_match.iloc[0]))
        
        if not valid_candidates:
            op_codes_str = ", ".join(sorted(list(set([str(r['Код']).strip() for r in performed_ops]))))
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
                    hint_html = _get_hints_for_msmkbe(mes_code, ref_msmkbe)
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
                hint_html = _get_hints_for_msmkbe(mes_code, ref_msmkbe)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
            if not is_skp:
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs))
                ]
                if not mscrit_match.empty:
                    a00_match = mscrit_match[mscrit_match['Код хирургической операции'] == 'A00.00']
                    if a00_match.empty:
                        sorted_g = group.dropna(subset=['Код прерывания госпитализации']).sort_values(by='Дата поступления')
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
                    elif str(canal).strip().lower() == 'самотек':
                        samotek_val = int(a00_match.iloc[0].get('Допустимость госпитализации "самотёк"', 1))
                        if samotek_val == 0:
                            errors.append(f"ИБ {ib_num}: Ошибка канала поступления: госпитализация 'самотёк' невозможна под МЭС <b>{mes_code}</b> и диагноз <b>{mkb_code}</b>.")
            
    errors.extend(_check_interruption_code(group, ib_num))
    return errors


def check_in_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10):
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
            if not mes_exists:
                diag_error_msg = f"[СКП] МЭС <b>{mes_code}</b> не найден в справочнике reeskp"
            else:
                diag_error_msg = f"[СКП] {diag_err_reason}"
        else:
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
                
    # --- БЛОК ОПЕРАЦИЙ ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', '']:
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
                op_code = str(row['Код']).strip()
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
                    (ref_mscrit['Код хирургической операции'] == op_code)
                ]
                if not mscrit_match.empty:
                    valid_candidates.append((row, mscrit_match.iloc[0]))
                    
            if not valid_candidates:
                for row in performed_ops:
                    op_code = str(row['Код']).strip()
                    fallback_match = ref_mscrit[
                        (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                        (ref_mscrit['Код хирургической операции'] == op_code)
                    ]
                    if not fallback_match.empty:
                        valid_candidates.append((row, fallback_match.iloc[0]))
        
        if not valid_candidates:
            op_codes_str = ", ".join(sorted(list(set([str(r['Код']).strip() for r in performed_ops]))))
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
                    a00_match = mscrit_match[mscrit_match['Код хирургической операции'] == 'A00.00']
                    if a00_match.empty:

                        sorted_g = group.dropna(subset=['Код прерывания госпитализации']).sort_values(by='Дата поступления')
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
                    elif str(canal).strip().lower() == 'самотек':
                        samotek_val = int(a00_match.iloc[0].get('Допустимость госпитализации "самотёк"', 1))
                        if samotek_val == 0:
                            errors.append(f"ИБ {ib_num}: Ошибка канала поступления: госпитализация 'самотёк' невозможна под МЭС <b>{mes_code}</b> и диагноз <b>{mkb_code}</b>.")
            
    errors.extend(_check_interruption_code(group, ib_num))
    return errors


def check_zl_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10):
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
            if not mes_exists:
                diag_error_msg = f"[СКП ЗЛ] МЭС <b>{mes_code}</b> не найден в справочнике reeskp"
            else:
                diag_error_msg = f"[СКП ЗЛ] {diag_err_reason}"
        else:
            pass
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

    # --- БЛОК ОПЕРАЦИЙ ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', '']:
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
                op_code = str(row['Код']).strip()
                mscrit_match = ref_mscrit[
                    (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                    (ref_mscrit['Код диагноза'].isin(search_mkbs)) &
                    (ref_mscrit['Код хирургической операции'] == op_code)
                ]
                if not mscrit_match.empty:
                    valid_candidates.append((row, mscrit_match.iloc[0]))
                    
            if not valid_candidates:
                for row in performed_ops:
                    op_code = str(row['Код']).strip()
                    fallback_match = ref_mscrit[
                        (ref_mscrit['Код медицинской услуги'] == mes_code) & 
                        (ref_mscrit['Код хирургической операции'] == op_code)
                    ]
                    if not fallback_match.empty:
                        valid_candidates.append((row, fallback_match.iloc[0]))
        
        if not valid_candidates:
            op_codes_str = ", ".join(sorted(list(set([str(r['Код']).strip() for r in performed_ops]))))
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
                    a00_match = mscrit_match[mscrit_match['Код хирургической операции'] == 'A00.00']
                    if a00_match.empty:
                        sorted_g = group.dropna(subset=['Код прерывания госпитализации']).sort_values(by='Дата поступления')
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
                    elif str(canal).strip().lower() == 'самотек':
                        samotek_val = int(a00_match.iloc[0].get('Допустимость госпитализации "самотёк"', 1))
                        if samotek_val == 0:
                            errors.append(f"ИБ {ib_num}: Ошибка канала поступления: госпитализация 'самотёк' невозможна под МЭС <b>{mes_code}</b> и диагноз <b>{mkb_code}</b>.")
            
    errors.extend(_check_interruption_code(group, ib_num))
    return errors


def main():
    import glob
    
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
        
        all_errors = []
        
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
                    all_errors.append({'department': department, 'message': err})
                continue 
                
            temp_errors = []
            
            if 'реанимация' in mes_name or mes_code in reanimation_target_codes:
                temp_errors.extend(check_reanimation_logic(group, ib))
            elif patient_type == 'НИЛ':
                temp_errors.extend(check_nil_patient(group, ref_msmkbe, ref_mscrit, ref_mkb10))
            elif patient_type in ['ИН', 'ИНОГОРОДНИЙ']: 
                temp_errors.extend(check_in_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10))
            elif patient_type in ['ЗЛ', 'НР']:
                temp_errors.extend(check_zl_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10))
            else:
                temp_errors.append(f"ИБ {ib}: Невозможно классифицировать пациента (тип: <b>'{patient_type}'</b>).")
                
            for err in temp_errors:
                all_errors.append({'department': department, 'message': err})
                
        print("\n" + "="*50)
        print(f"ПРОВЕРКА ЗАВЕРШЕНА. НАЙДЕНО ОШИБОК: {len(all_errors)}")
        print("="*50)
        
        import re
        for err_dict in all_errors:
            clean_msg = re.sub(r'<[^>]+>', '', err_dict['message'])
            print(f"[{err_dict['department']}] {clean_msg}")
            
        if all_errors:
            current_time = datetime.now().strftime("%d.%m.%Y_%H-%M")
            report_name = f"report_{current_time}.html"
            generate_html_report(all_errors, output_path=os.path.join(INPUT_DIR, report_name))

    except Exception as e:
        print("\n" + "!"*50)
        print(f"ПРОИЗОШЛА КРИТИЧЕСКАЯ ОШИБКА:")
        print(e)
        print("!"*50)
        
    input("\nНажмите Enter, чтобы закрыть программу...")

if __name__ == "__main__":
    main()