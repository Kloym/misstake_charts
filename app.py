import pandas as pd
import numpy as np
import os
from datetime import datetime

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
    "Проводниковая": 0,
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
    options_html = "".join([f'<option value="{d}">{d}</option>' for d in unique_depts])
    
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Отчет по ошибкам (mscrit)</title>
        <style>
            /* --- CSS ПЕРЕМЕННЫЕ (СВЕТЛАЯ ТЕМА ПО УМОЛЧАНИЮ) --- */
            :root {
                --bg-color: #f4f7f6;
                --container-bg: #ffffff;
                --text-color: #333333;
                --text-muted: #7f8c8d;
                --border-color: #bdc3c7;
                --panel-bg: #e8f4f8;
                --panel-border: #d5dbdb;
                --table-header-bg: #3498db;
                --table-header-text: #ffffff;
                --table-hover: #f9fbfb;
                --table-stripe: #fcfcfc;
                --accent-blue: #2980b9;
                --accent-orange: #d35400;
                --hint-bg: #fff;
                --hint-summary-bg: #eafaf1;
                --hint-summary-hover: #d5f5e3;
                --hint-text: #27ae60;
                --input-bg: #f4f6f6;
                --shadow: 0 8px 16px rgba(0,0,0,0.08);
                --transition-speed: 0.3s;
            }

            /* --- ТЕМНАЯ ТЕМА --- */
            [data-theme="dark"] {
                --bg-color: #121212;
                --container-bg: #1e1e1e;
                --text-color: #e0e0e0;
                --text-muted: #a0aab2;
                --border-color: #333333;
                --panel-bg: #2a2a2a;
                --panel-border: #444444;
                --table-header-bg: #1a1a1a;
                --table-header-text: #bb86fc;
                --table-hover: #2c2c2c;
                --table-stripe: #242424;
                --accent-blue: #64b5f6;
                --accent-orange: #ffb74d;
                --hint-bg: #252525;
                --hint-summary-bg: #1e3329;
                --hint-summary-hover: #274538;
                --hint-text: #69f0ae;
                --input-bg: #2c2c2c;
                --shadow: 0 8px 16px rgba(0,0,0,0.5);
            }

            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background-color: var(--bg-color); 
                color: var(--text-color); 
                margin: 0; 
                padding: 30px 20px; 
                transition: background-color var(--transition-speed) ease, color var(--transition-speed) ease;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto; 
                background: var(--container-bg); 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: var(--shadow); 
                transition: background-color var(--transition-speed) ease, box-shadow var(--transition-speed) ease;
            }
            
            /* --- ШАПКА И ПЕРЕКЛЮЧАТЕЛЬ --- */
            .header-wrap {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid var(--accent-blue);
                padding-bottom: 15px;
                margin-bottom: 20px;
            }
            h1 { color: var(--text-color); margin: 0; font-size: 1.8em; }
            
            /* КРУТОЙ СВИТЧЕР ТЕМЫ */
            .theme-switch-wrapper { display: flex; align-items: center; gap: 10px; }
            .theme-switch { display: inline-block; height: 34px; position: relative; width: 66px; }
            .theme-switch input { display: none; }
            .slider {
                background-color: #ccc; bottom: 0; cursor: pointer; left: 0; position: absolute; right: 0; top: 0; transition: .4s; border-radius: 34px;
            }
            .slider:before {
                background-color: #fff; bottom: 4px; content: "☀️"; display: flex; align-items: center; justify-content: center; font-size: 14px; height: 26px; left: 4px; position: absolute; transition: .4s; width: 26px; border-radius: 50%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            input:checked + .slider { background-color: #34495e; }
            input:checked + .slider:before { transform: translateX(32px); content: "🌙"; background-color: #1e1e1e; }
            
            /* --- ПАНЕЛИ УПРАВЛЕНИЯ --- */
            .controls { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: var(--panel-bg); padding: 15px 20px; border-radius: 8px; border: 1px solid var(--panel-border); }
            .stats { font-weight: bold; color: var(--accent-blue); font-size: 1.1em; }
            .filter-box { display: flex; align-items: center; gap: 10px; }
            select { padding: 10px 15px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 15px; min-width: 250px; cursor: pointer; outline: none; background: var(--input-bg); color: var(--text-color); transition: border var(--transition-speed); }
            select:focus { border-color: var(--accent-blue); }
            
            .export-panel { background: var(--container-bg); border: 1px solid var(--panel-border); padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
            .export-panel strong { color: var(--text-color); display: block; margin-bottom: 12px; font-size: 1.1em;}
            .export-controls { display: flex; gap: 12px; }
            #summaryText { flex-grow: 1; padding: 12px 15px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--input-bg); font-family: monospace; font-size: 14px; color: var(--text-muted); outline: none; transition: color var(--transition-speed); }
            .btn-copy { background: #27ae60; color: white; border: none; padding: 12px 25px; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.2s; box-shadow: 0 4px 6px rgba(39, 174, 96, 0.3); }
            .btn-copy:hover { background: #2ecc71; transform: translateY(-1px); box-shadow: 0 6px 8px rgba(39, 174, 96, 0.4); }
            .btn-copy:active { transform: translateY(1px); box-shadow: 0 2px 4px rgba(39, 174, 96, 0.3); }
            
            /* --- ТАБЛИЦА --- */
            table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; border-radius: 8px; overflow: hidden; border: 1px solid var(--panel-border); }
            th, td { padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--panel-border); transition: background-color var(--transition-speed); }
            th { background-color: var(--table-header-bg); color: var(--table-header-text); position: sticky; top: 0; z-index: 10; font-weight: 600; text-transform: uppercase; font-size: 0.9em; letter-spacing: 0.5px; }
            tbody tr:nth-child(even) { background-color: var(--table-stripe); }
            tbody tr:hover { background-color: var(--table-hover); }
            tbody tr:last-child td { border-bottom: none; }
            
            .dept-col { font-weight: 500; color: var(--text-muted); font-size: 0.95em; }
            .ib-col { font-weight: bold; color: var(--accent-orange); width: 12%; font-size: 1.05em; }
            
            /* --- ПОДСКАЗКИ --- */
            .hint-wrapper { margin-top: 12px; }
            .hint-details { background: var(--container-bg); border: 1px solid var(--panel-border); border-radius: 6px; overflow: hidden; display: inline-block; min-width: 85%; transition: box-shadow 0.2s; }
            .hint-details:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
            .hint-details summary { background: var(--hint-summary-bg); padding: 10px 15px; cursor: pointer; font-weight: 600; color: var(--hint-text); outline: none; user-select: none; font-size: 0.95em; transition: background var(--transition-speed); }
            .hint-details summary:hover { background: var(--hint-summary-hover); }
            .hint-content { padding: 12px 18px; border-top: 1px solid var(--panel-border); background: var(--hint-bg); max-height: 250px; overflow-y: auto; }
            .hint-content ul { margin: 0; padding-left: 20px; color: var(--text-color); font-size: 0.95em; line-height: 1.6; }
            .hint-content li { margin-bottom: 6px; }
            .hl-diag { color: #8e44ad; font-weight: bold; }
            [data-theme="dark"] .hl-diag { color: #d7b4f3; }
            .hl-oper { color: var(--accent-blue); font-weight: bold; }
            .no-hint { color: #e74c3c; font-size: 0.9em; display: inline-block; margin-top: 5px; background: rgba(231, 76, 60, 0.1); padding: 6px 10px; border-radius: 4px;}
            
            /* --- ЭЛЕМЕНТЫ UI --- */
            .fixed-row td { text-decoration: line-through; color: var(--text-muted); background-color: var(--panel-bg); opacity: 0.6; }
            .checkbox-custom { width: 22px; height: 22px; cursor: pointer; accent-color: var(--hint-text); }
            .hidden-row { display: none; }
            
            .context-tag { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; margin-bottom: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .tag-skp { background-color: #f39c12; color: white; }
            .tag-rean { background-color: #e74c3c; color: white; }
            .tag-missing { background-color: #9b59b6; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-wrap">
                <h1>📋 Отчет по ошибкам заполнения МЭС</h1>
                <div class="theme-switch-wrapper">
                    <span style="font-size: 14px; font-weight: bold; color: var(--text-muted);">Тема:</span>
                    <label class="theme-switch" for="checkbox">
                        <input type="checkbox" id="checkbox" />
                        <div class="slider round"></div>
                    </label>
                </div>
            </div>
            
            <div class="controls">
                <div class="stats" id="statsCount">Всего найдено ошибок: {total_errors}</div>
                <div class="filter-box">
                    <label for="deptFilter" style="color: var(--text-muted);"><b>Отделение:</b></label>
                    <select id="deptFilter" onchange="filterTable()">
                        <option value="all">Все отделения</option>
                        {dept_options}
                    </select>
                </div>
            </div>
            
            <div class="export-panel">
                <strong>📝 Готовый ответ для оператора:</strong>
                <div class="export-controls">
                    <input type="text" id="summaryText" readonly value="Поправили: (отметьте галочками исправленные ИБ)">
                    <button class="btn-copy" onclick="copySummary()" id="copyBtn">📋 Скопировать</button>
                </div>
            </div>
            
            <table id="errorsTable">
                <thead>
                    <tr>
                        <th width="5%">Испр.</th>
                        <th width="20%">Отделение</th>
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
        error_text = error_text.replace("🚨", "<span class='context-tag tag-missing'>Внимание</span>")
            
        safe_dept = dept.replace("'", "\\'")
            
        html_content += f"""
                    <tr id="row_{i}" class="data-row" data-dept="{dept}">
                        <td><input type="checkbox" class="checkbox-custom" id="check_{i}" onclick="toggleFix({i}, '{ib_text}', '{safe_dept}')"></td>
                        <td class="dept-col">{dept}</td>
                        <td class="ib-col">{ib_text}</td>
                        <td>{error_text}</td>
                    </tr>
        """
        
    html_content += """
                </tbody>
            </table>
        </div>

        <script>
            // --- ЛОГИКА ТЕМНОЙ ТЕМЫ ---
            const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
            const currentTheme = localStorage.getItem('theme');

            if (currentTheme) {
                document.documentElement.setAttribute('data-theme', currentTheme);
                if (currentTheme === 'dark') {
                    toggleSwitch.checked = true;
                }
            }

            function switchTheme(e) {
                if (e.target.checked) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.documentElement.setAttribute('data-theme', 'light');
                    localStorage.setItem('theme', 'light');
                }    
            }
            toggleSwitch.addEventListener('change', switchTheme, false);


            // --- ЛОГИКА ТАБЛИЦЫ И КОПИРОВАНИЯ ---
            let fixedIBs = new Set();

            function toggleFix(index, ibNumber, deptName) {
                var row = document.getElementById('row_' + index);
                var checkbox = document.getElementById('check_' + index);
                var entry = ibNumber + " (" + deptName + ")";
                
                if (checkbox.checked) {
                    row.classList.add('fixed-row');
                    fixedIBs.add(entry);
                } else {
                    row.classList.remove('fixed-row');
                    
                    var rows = document.getElementsByClassName('data-row');
                    var stillHasChecked = false;
                    for(var i=0; i<rows.length; i++) {
                        var cb = rows[i].querySelector('.checkbox-custom');
                        var rowIb = rows[i].querySelector('.ib-col').innerText;
                        var rowDept = rows[i].getAttribute('data-dept');
                        var checkEntry = rowIb + " (" + rowDept + ")";
                        
                        if(cb.checked && checkEntry === entry) {
                            stillHasChecked = true;
                            break;
                        }
                    }
                    if(!stillHasChecked) {
                        fixedIBs.delete(entry);
                    }
                }
                updateSummary();
            }
            
            function updateSummary() {
                var summaryInput = document.getElementById('summaryText');
                if (fixedIBs.size === 0) {
                    summaryInput.value = "Поправили: (отметьте галочками исправленные ИБ)";
                    summaryInput.style.color = "var(--text-muted)";
                } else {
                    let ibArray = Array.from(fixedIBs);
                    summaryInput.value = "Поправили: " + ibArray.join(", ");
                    summaryInput.style.color = "var(--text-color)";
                }
                document.getElementById('copyBtn').innerText = "📋 Скопировать";
            }
            
            function copySummary() {
                if (fixedIBs.size === 0) {
                    alert("Сначала отметьте галочками исправленные ошибки в таблице!");
                    return;
                }
                var copyText = document.getElementById("summaryText");
                copyText.select();
                copyText.setSelectionRange(0, 99999); 
                document.execCommand("copy");
                
                var btn = document.getElementById('copyBtn');
                btn.innerText = "✅ Скопировано!";
                setTimeout(function() {
                    if(btn.innerText === "✅ Скопировано!") {
                        btn.innerText = "📋 Скопировать";
                    }
                }, 2000);
            }
            
            function filterTable() {
                var filter = document.getElementById("deptFilter").value;
                var rows = document.getElementsByClassName("data-row");
                var visibleCount = 0;
                
                for (var i = 0; i < rows.length; i++) {
                    var rowDept = rows[i].getAttribute("data-dept");
                    if (filter === "all" || rowDept === filter) {
                        rows[i].classList.remove("hidden-row");
                        visibleCount++;
                    } else {
                        rows[i].classList.add("hidden-row");
                    }
                }
                
                var statsText = filter === "all" ? "Всего найдено ошибок: " : "Ошибок в выбранном отделении: ";
                document.getElementById("statsCount").innerText = statsText + visibleCount;
            }
        </script>
    </body>
    </html>
    """
    
    final_html = html_content.replace("{total_errors}", str(len(errors_data))).replace("{dept_options}", options_html)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
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
    
    df_mov['ИБ_clean'] = df_mov['Номер ИБ'].astype(str).str.split('-').str[0].str.strip()
    df_disch['ИБ_clean'] = df_disch['ИБ. Номер'].astype(str).str.strip()
    df_op['ИБ_clean'] = df_op['ИБ. Номер'].astype(str).str.strip()
    
    df_patients = pd.merge(df_mov, df_disch, on='ИБ_clean', how='inner', suffixes=('_mov', '_disch'))
    df_full = pd.merge(df_patients, df_op, on='ИБ_clean', how='left', suffixes=('', '_op'))
    
    return df_full

def _check_mscrit_operation_rules(op_row, mscrit_req, ib_num, canal, is_skp):
    errors = []
    op_code = op_row['Код']
    op_type = op_row.get('Основная/сопутст', op_row.get('Основная/сопутствующая'))
    anesthesia_name = op_row['Анестезия']
    
    req_main = mscrit_req['Обязательность отметки операции как основной']
    if req_main == 1 and op_type != 'Основная':
        errors.append(f"ИБ {ib_num}: Статус операции: в данной связке операция <b>{op_code}</b> обязана быть 'Основной', а у вас указана '<b>{op_type}</b>'.")
        
    req_anesth = mscrit_req['Код типа анестезии']
    actual_anesth_val = ANESTHESIA_DICT.get(anesthesia_name)
    
    if actual_anesth_val is None:
        errors.append(f"ИБ {ib_num}: Тип анестезии: указана неизвестная анестезия <b>'{anesthesia_name}'</b>. Проверьте опечатку.")
    elif req_anesth == 1 and actual_anesth_val != 1:
        errors.append(f"ИБ {ib_num}: Тип анестезии: для этой операции обязательна анестезия <b>1-го типа</b>, но указана <b>'{anesthesia_name}'</b> (это тип {actual_anesth_val}).")
        
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
        if patient_type != 'ЗЛ':
            errors.append(f"ИБ {ib_num}: Недопустимый МЭС: спецпроект <b>{mes_code}</b> разрешен только для пациентов '<b>ЗЛ</b>' (у вас '<b>{patient_type}</b>').")
    elif mes_code.startswith('200'):
        if patient_type not in ['ЗЛ', 'ИН', 'ИНОГОРОДНИЙ']:
            errors.append(f"ИБ {ib_num}: Недопустимый МЭС: МЭС <b>{mes_code}</b> разрешен только для '<b>ЗЛ</b>' и '<b>ИН</b>' (у вас '<b>{patient_type}</b>').")

    unique_movs = group.drop_duplicates(subset=['Дата поступления', 'Отделение', 'Код прерывания госпитализации'])
    sorted_group = unique_movs.sort_values(by='Дата поступления').dropna(subset=['Код прерывания госпитализации'])
    
    if sorted_group.empty:
        return errors

    if len(sorted_group) > 1:
        for idx in range(len(sorted_group) - 1):
            code = str(sorted_group.iloc[idx]['Код прерывания госпитализации']).split('.')[0].strip().upper()
            if code != '7' and code != 'NAN':
                errors.append(f"ИБ {ib_num}: Множественные переводы: промежуточные коды прерывания должны быть строго '<b>7</b>', а в выписке №{idx+1} указан '<b>{code}</b>'.")

    last_row = sorted_group.iloc[-1]
    last_dept = str(last_row.get('Отделение', '')).lower()
    last_code = str(last_row['Код прерывания госпитализации']).split('.')[0].strip().upper()
    
    if last_code != 'NAN':
        if mes_code in SPECIAL_PROJECT_MES:
            if last_code not in ['S', 'С']:
                errors.append(f"ИБ {ib_num}: Код прерывания: для спецпроекта (МЭС <b>{mes_code}</b>) код последнего движения должен быть '<b>S</b>', а указан '<b>{last_code}</b>'.")
        elif mes_code.startswith('200'):
            if last_code not in ['V', 'В']:
                errors.append(f"ИБ {ib_num}: Код прерывания: для МЭС <b>{mes_code}</b> код последнего движения должен быть '<b>V</b>', а указан '<b>{last_code}</b>'.")
        elif 'реанимац' in last_dept:
            if last_code not in ['3', '5']:
                errors.append(f"ИБ {ib_num}: Код прерывания: последнее движение было в реанимации, ожидался код '<b>3</b>' или '<b>5</b>', а указан '<b>{last_code}</b>'.")
                
    return errors

# --- ЛОГИКА ИСКЛЮЧЕНИЙ И ПАЦИЕНТОВ ---

def check_reanimation_logic(group, ib_num):
    errors = []
    mes_code = str(group['МЭС. Код'].iloc[0]).split('.')[0].strip()
    
    try:
        if 'Дата выбытия' not in group.columns:
            return [f"ИБ {ib_num}: [Реанимация] В таблице 'Движение' нет столбца 'Дата выбытия' для расчета дней."]
            
        unique_movs = group.drop_duplicates(subset=['Дата поступления', 'Дата выбытия', 'Отделение'])
        rean_rows = unique_movs[unique_movs['Отделение'].astype(str).str.lower().str.contains('реанимац', na=False)]
        
        if rean_rows.empty:
            rean_rows = unique_movs 
            
        total_hours = 0
        has_dates = False
        
        for _, row in rean_rows.iterrows():
            if pd.notna(row['Дата поступления']) and pd.notna(row['Дата выбытия']):
                d_in = pd.to_datetime(row['Дата поступления'], dayfirst=True)
                d_out = pd.to_datetime(row['Дата выбытия'], dayfirst=True)
                hours = (d_out - d_in).total_seconds() / 3600.0
                if hours < 0: hours = 0
                total_hours += hours
                has_dates = True
                
        if not has_dates:
            return [f"ИБ {ib_num}: [Реанимация] Нет данных о дате поступления/выбытия, невозможно рассчитать время."]

        days = int(total_hours // 24)
        
        if total_hours < 12:
            expected_codes = ['056029', '56029']
            time_str = f"{round(total_hours, 1)} часов"
        elif days <= 2:
            expected_codes = ['083010', '183010', '83010']
            time_str = f"{round(total_hours, 1)} часов (до 2 дней)" if days == 0 else f"{days} дней"
        elif 3 <= days <= 4:
            expected_codes = ['083020', '183020', '83020']
            time_str = f"{days} дней"
        elif 5 <= days <= 6:
            expected_codes = ['083030', '183030', '83030']
            time_str = f"{days} дней"
        elif 7 <= days <= 8:
            expected_codes = ['083040', '183040', '83040']
            time_str = f"{days} дней"
        else:
            expected_codes = ['083050', '183050', '83050']
            time_str = f"{days} дней"
            
        if mes_code not in expected_codes:
            errors.append(f"ИБ {ib_num}: [Реанимация] Пациент лежал <b>{time_str}</b>. По правилам ожидался один из МЭС: <b>{expected_codes}</b>, но у вас указан <b>'{mes_code}'</b>.")
            
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
    
    msmkbe_match = ref_msmkbe[
        (ref_msmkbe['Код медицинской услуги'] == mes_code) & 
        (ref_msmkbe['Код диагноза (шифр по МКБ-10)'].isin(search_mkbs))
    ]
    if msmkbe_match.empty:
        has_diag_error = True
        mes_exists = not ref_msmkbe[ref_msmkbe['Код медицинской услуги'] == mes_code].empty
        if not mes_exists:
            error_msg = f"ИБ {ib_num}: Базовая проверка: МЭС <b>{mes_code}</b> не найден в справочнике msmkbe."
        else:
            error_msg = f"ИБ {ib_num}: Базовая проверка диагноза: {diag_err_reason}."
            
        if department in DIFFICULT_DEPARTMENTS:
            hint_html = _get_hints_for_msmkbe(mes_code, ref_msmkbe)
            error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
        errors.append(error_msg)
        
    # --- БЛОК ОПЕРАЦИЙ (МЯГКАЯ ЛОГИКА: ДОСТАТОЧНО ОДНОЙ ПРАВИЛЬНОЙ) ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', ''] or interruption == '9':
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
            error_msg = f"ИБ {ib_num}: Ошибка операции: ни одна из проведенных операций (<b>{op_codes_str}</b>) не предусмотрена справочником mscrit для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b>."
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
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
    
    search_mkbs = [mkb_code, 'XXX.X', 'ХХХ.Х']
    is_invalid_extension = False
    
    if mkb_code in ref_mkb10['Шифр'].values:
        search_mkbs.append(mkb_base)
    elif '.' in mkb_code and mkb_base in ref_mkb10['Шифр'].values:
        is_invalid_extension = True
        
    diag_err_reason = f"расширение <b>{mkb_code}</b> не предусмотрено справочником МКБ-10 (используйте базовый <b>{mkb_base}</b>)" if is_invalid_extension else f"указанный МКБ <b>{mkb_code}</b> не подходит для МЭС <b>{mes_code}</b>"
    
    is_skp = 'стационар кратковременного пребывания' in mes_name
    has_diag_error = False

    if is_skp:
        reeskp_match = ref_reeskp[
            (ref_reeskp['Код услуги'] == mes_code) & 
            (ref_reeskp['код диагноза'].isin(search_mkbs))
        ]
        if reeskp_match.empty:
            has_diag_error = True
            mes_exists = not ref_reeskp[ref_reeskp['Код услуги'] == mes_code].empty
            if not mes_exists:
                error_msg = f"ИБ {ib_num}: [СКП] Базовая проверка: МЭС <b>{mes_code}</b> не найден в справочнике reeskp."
            else:
                error_msg = f"ИБ {ib_num}: [СКП] Проверка диагноза: для стационара кратковременного пребывания {diag_err_reason}."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_reeskp(mes_code, ref_reeskp)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
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
                error_msg = f"ИБ {ib_num}: Базовая проверка: МЭС <b>{mes_code}</b> не найден в справочнике mscrit."
            else:
                error_msg = f"ИБ {ib_num}: Базовая проверка диагноза: {diag_err_reason}."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
                
    # --- БЛОК ОПЕРАЦИЙ ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', ''] or interruption == '9':
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
            error_msg = f"ИБ {ib_num}: Ошибка операции: ни одна из проведенных операций (<b>{op_codes_str}</b>) не предусмотрена справочником mscrit для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b>."
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
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
    
    search_mkbs = [mkb_code, 'XXX.X', 'ХХХ.Х']
    is_invalid_extension = False
    
    if mkb_code in ref_mkb10['Шифр'].values:
        search_mkbs.append(mkb_base)
    elif '.' in mkb_code and mkb_base in ref_mkb10['Шифр'].values:
        is_invalid_extension = True
        
    diag_err_reason = f"расширение <b>{mkb_code}</b> не предусмотрено справочником МКБ-10 (используйте базовый <b>{mkb_base}</b>)" if is_invalid_extension else f"указанный МКБ <b>{mkb_code}</b> не подходит для МЭС <b>{mes_code}</b>"

    is_skp = 'стационар кратковременного пребывания' in mes_name
    has_diag_error = False

    if is_skp:
        reeskp_match = ref_reeskp[
            (ref_reeskp['Код услуги'] == mes_code) & 
            (ref_reeskp['код диагноза'].isin(search_mkbs))
        ]
        if reeskp_match.empty:
            has_diag_error = True
            mes_exists = not ref_reeskp[ref_reeskp['Код услуги'] == mes_code].empty
            if not mes_exists:
                error_msg = f"ИБ {ib_num}: [СКП ЗЛ] Базовая проверка: МЭС <b>{mes_code}</b> не найден в справочнике reeskp."
            else:
                error_msg = f"ИБ {ib_num}: [СКП ЗЛ] Проверка диагноза: для стационара кратковременного пребывания {diag_err_reason}."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_reeskp(mes_code, ref_reeskp)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
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
                error_msg = f"ИБ {ib_num}: Базовая проверка: МЭС <b>{mes_code}</b> не найден в справочнике mscrit."
            else:
                error_msg = f"ИБ {ib_num}: Базовая проверка диагноза: {diag_err_reason}."
                
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)

    # --- БЛОК ОПЕРАЦИЙ ---
    performed_ops = []
    seen = set()
    for idx, row in group.iterrows():
        op_code = str(row.get('Код', '')).strip()
        op_type = str(row.get('Основная/сопутст', row.get('Основная/сопутствующая', ''))).strip()
        anesth = str(row.get('Анестезия', '')).strip()
        interruption = str(row.get('Код прерывания госпитализации', '')).split('.')[0]
        
        if op_code.lower() in ['nan', ''] or interruption == '9':
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
            error_msg = f"ИБ {ib_num}: Ошибка операции: ни одна из проведенных операций (<b>{op_codes_str}</b>) не предусмотрена справочником mscrit для МЭС <b>{mes_code}</b> и диагноза <b>{mkb_code}</b>."
            if department in DIFFICULT_DEPARTMENTS:
                hint_html = _get_hints_for_mscrit(mes_code, ref_mscrit, search_mkbs)
                error_msg += f"<div class='hint-wrapper'>{hint_html}</div>"
            errors.append(error_msg)
        else:
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
        
        grouped = df_merged.groupby('ИБ_clean')
        print(f"Обнаружено пациентов (ИБ): {len(grouped)}. Начинаю проверку...")
        
        for ib, group in grouped:
            patient_type = str(group['ПУМП. Тип пациента'].iloc[0]).strip().upper()
            mes_name = str(group['МЭС. Название'].iloc[0]).lower()
            mes_code = str(group['МЭС. Код'].iloc[0]).strip()
            department = str(group['Отделение'].iloc[0]).strip() 
            
            if patient_type == 'NAN' or patient_type == '':
                continue
                
            temp_errors = []
            
            if 'реанимация' in mes_name or mes_code in reanimation_target_codes:
                temp_errors = check_reanimation_logic(group, ib)
            elif patient_type == 'НИЛ':
                temp_errors = check_nil_patient(group, ref_msmkbe, ref_mscrit, ref_mkb10)
            elif patient_type in ['ИН', 'ИНОГОРОДНИЙ']: 
                temp_errors = check_in_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10)
            elif patient_type == 'ЗЛ':
                temp_errors = check_zl_patient(group, ref_msmkbe, ref_mscrit, ref_reeskp, ref_mkb10)
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