import json

# --- НАСТРОЙКИ И СЛОВАРИ ---
DEBUG_MODE = False 

ANESTHESIA_DICT = {
    "Местная": 0, "Аппликационная": 0, "Инфильтрационная": 0, "Инфильрационная": 0,  
    "Комбинированная общая анестезия с миорелаксантами и ИВЛ": 1,
    "Тотальная внутривенная анестезия с миорелаксантами и ИВЛ": 1,
    "Ингаляционная анестезия с сохранением спонтанного дыхания": 1,
    "Внутривенная анестезия с сохранением спонтанного дыхания": 1,
    "Мониторинг анестезиологом с контролем седации и анальгезии (МАКС)": 1,
    "Спинальная анестезия": 1, "Эпидуральная анестезия": 1,
    "Спинально-эпидуральная анастезия": 1, "Спинально-эпидуральная анестезия": 1, 
    "Проводниковая": 1, "Межфасциальная блокада": 0
}

DIFFICULT_DEPARTMENTS = [
    "хирургическое отделение", "травматологическое отделение", 
    "терапевтическое отделение", "отделение гнойной хирургии",
    "отделение сосудистой хирургии",
]

def debug_print(msg):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

# --- ФУНКЦИЯ ГЕНЕРАЦИИ HTML ---
def generate_html_report(errors_data, recs_dict, checked_data, output_path):
    # --- Сортировка первой вкладки ---
    errors_data = sorted(errors_data, key=lambda x: "Клинические рекомендации:" in x['message'])
    
    unique_depts_err = sorted(list(set([err['department'] for err in errors_data])))
    dept_checkboxes_err = ""
    for d in unique_depts_err:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes_err += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb-err" checked onchange="filterErrTable()"> {d}</label></li>\n'
    
    # --- Подготовка для второй вкладки ---
    # 1. Отделения
    unique_depts_chk = sorted(list(set([str(row.get('Отделение', '')) for row in checked_data if str(row.get('Отделение', ''))])))
    dept_checkboxes_chk = ""
    for d in unique_depts_chk:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes_chk += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb-chk" checked onchange="filterChkTable()"> {d}</label></li>\n'
        
    # 2. Даты выбытия
    raw_dates = list(set([str(row.get('Дата выбытия', '')) for row in checked_data if str(row.get('Дата выбытия', ''))]))
    
    def date_sort_key(d):
        if d == 'Нет даты': return '00000000'
        parts = d.split('.')
        if len(parts) == 3: return f"{parts[2]}{parts[1]}{parts[0]}"
        return d
        
    unique_dates_chk = sorted(raw_dates, key=date_sort_key, reverse=True)
    
    date_checkboxes_chk = ""
    for dt in unique_dates_chk:
        safe_val = dt.replace('"', '&quot;')
        date_checkboxes_chk += f'<li><label><input type="checkbox" value="{safe_val}" class="date-cb-chk" checked onchange="filterChkTable()"> {dt}</label></li>\n'

    recs_json = json.dumps(recs_dict, ensure_ascii=False)
    checked_json = json.dumps(checked_data, ensure_ascii=False)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Отчет: Ошибки и Проверки</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 30px 20px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            
            /* Секретный заголовок для Excel */
            h1 {{ margin: 0 0 20px 0; font-size: 1.5em; color: #2c3e50; }}
            .secret-export {{ cursor: default; user-select: none; }}
            
            /* ВКЛАДКИ */
            .tabs-nav {{ display: flex; gap: 20px; border-bottom: 2px solid #e0e0e0; margin-bottom: 20px; }}
            .tab-btn {{ background: none; border: none; padding: 10px 15px; font-size: 16px; font-weight: bold; color: #7f8c8d; cursor: pointer; border-bottom: 3px solid transparent; transition: 0.3s; }}
            .tab-btn:hover {{ color: #3498db; }}
            .tab-btn.active {{ color: #3498db; border-bottom-color: #3498db; }}
            .tab-content {{ display: none; animation: fadein 0.4s; }}
            .tab-content.active {{ display: block; }}
            
            .controls, .export-panel {{ background: #fdfdfd; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin-bottom: 20px; }}
            
            .stats-container {{ display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap; }}
            .stat-badge {{ padding: 8px 15px; border-radius: 6px; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .stat-badge.total {{ background: #f8f9f9; color: #2c3e50; border: 1px solid #d5dbdb; }}
            .stat-badge.err {{ background: #fdedec; color: #c0392b; border: 1px solid #fadbd8; }}
            .stat-badge.rec {{ background: #f4ecf8; color: #8e44ad; border: 1px solid #e8daef; }}
            .stat-badge.success {{ background: #eafaf1; color: #27ae60; border: 1px solid #d5f5e3; }}
            .stat-badge span {{ font-size: 16px; font-weight: bold; background: rgba(255,255,255,0.8); padding: 2px 8px; border-radius: 4px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }}
            
            .filters-grid {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }}
            .filter-group {{ display: flex; flex-direction: column; gap: 5px; flex: 1 1 200px; min-width: 0; }}
            .filter-group label {{ font-size: 0.85em; font-weight: 600; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; }}
            input[type="text"] {{ box-sizing: border-box; width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; outline: none; }}
            input[type="text"]:focus {{ border-color: #3498db; }}
            
            .dropdown-check-list {{ display: block; position: relative; width: 100%; }}
            .dropdown-check-list .anchor {{ box-sizing: border-box; width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fff; cursor: pointer; display: block; font-size: 14px; color: #333; }}
            .dropdown-check-list .anchor:after {{ content: '▼'; float: right; font-size: 10px; color: #7f8c8d; margin-top: 4px; }}
            .dropdown-check-list .items {{ padding: 8px; display: none; position: absolute; background: #fff; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 100%; z-index: 100; max-height: 250px; overflow-y: auto; list-style: none; margin: 0; box-sizing: border-box;}}
            .dropdown-check-list.visible .items {{ display: block; }}
            .dropdown-check-list ul.items li label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px; border-radius: 4px; font-size: 13px; }}
            
            .export-panel {{ display: flex; justify-content: space-between; align-items: stretch; flex-wrap: wrap; gap: 15px; }}
            .export-controls {{ flex-grow: 1; display: flex; gap: 15px; align-items: stretch; min-width: 300px; }}
            #summaryText {{ flex-grow: 1; padding: 10px 15px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 13px; resize: vertical; min-height: 40px; box-sizing: border-box; }}
            .btn-copy {{ background: #27ae60; color: white; border: none; padding: 0 20px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 14px; white-space: nowrap; }}
            
            .table-container {{ overflow-x: auto; max-height: 70vh; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px; }}
            table.main-table {{ width: 100%; border-collapse: collapse; background: #fff; min-width: 800px; }}
            .main-table th, .main-table td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; vertical-align: middle; font-size: 14px; }}
            .main-table th {{ background-color: #3498db; color: #ffffff; position: sticky; top: 0; z-index: 50; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .main-table tbody tr:hover {{ background-color: #fcfcfc; }}
            .fixed-row td {{ text-decoration: line-through; opacity: 0.5; background-color: #f9f9f9; }}
            .hidden-row {{ display: none !important; }}
            
            .clickable-mes {{ background: #8e44ad; color: white; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: bold; cursor: pointer; text-decoration: none; transition: 0.2s; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .clickable-mes:hover {{ background: #9b59b6; transform: translateY(-1px); box-shadow: 0 3px 6px rgba(0,0,0,0.15); }}
            
            /* Модальное окно */
            .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); }}
            .modal-content {{ background-color: #fff; margin: 5% auto; padding: 25px; border-radius: 8px; width: 95%; max-width: 1400px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); animation: fadein 0.3s; overflow-x: auto; }}
            .close-btn {{ color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
            .close-btn:hover {{ color: #333; text-decoration: none; }}
            .rec-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .rec-table th, .rec-table td {{ border: 1px solid #e0e0e0; padding: 12px; font-size: 13px; line-height: 1.5; }}
            .rec-table th {{ background-color: #f8f9f9; }}
            
            .limit-warning {{ text-align: center; color: #7f8c8d; padding: 15px; font-size: 13px; font-style: italic; background: #fdfdfd; }}
            @keyframes fadein {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- СЕКРЕТНАЯ КНОПКА (onclick на значок) -->
            <h1><span class="secret-export" onclick="exportSecretExcel()">📝</span> Ошибки и карты для врачей</h1>
            
            <!-- Навигация по вкладкам -->
            <div class="tabs-nav">
                <button class="tab-btn active" onclick="switchTab('tab-errors', this)">Ошибки и Критерии ({len(errors_data)})</button>
                <button class="tab-btn" onclick="switchTab('tab-checked', this)">Проверенные карты ({len(checked_data)})</button>
            </div>
            
            <!-- ВКЛАДКА 1: ОШИБКИ И РЕКОМЕНДАЦИИ -->
            <div id="tab-errors" class="tab-content active">
                <div class="controls">
                    <div class="stats-container">
                        <div class="stat-badge total">Всего записей: <span id="countTotalErr">0</span></div>
                        <div class="stat-badge err">🔴 Ошибок: <span id="countErr">0</span></div>
                        <div class="stat-badge rec">🟣 Рекомендаций: <span id="countRec">0</span></div>
                    </div>
                    
                    <div class="filters-grid">
                        <div class="filter-group">
                            <label>Отделение:</label>
                            <div id="deptCheckListErr" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('deptCheckListErr')">Выбраны все отделения</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDeptsErr" checked onchange="toggleAllDepts('dept-cb-err', this, 'deptCheckListErr'); filterErrTable()"> <b>(Выбрать все)</b></label></li>
                                    {dept_checkboxes_err}
                                </ul>
                            </div>
                        </div>
                        <div class="filter-group"><label>Поиск по ИБ:</label><input type="text" id="ibFilterErr" onkeyup="filterErrTable()"></div>
                        <div class="filter-group"><label>Поиск по тексту:</label><input type="text" id="textFilterErr" onkeyup="filterErrTable()"></div>
                    </div>
                </div>
                
                <div class="export-panel">
                    <div class="export-controls">
                        <textarea id="summaryText" readonly placeholder="Отметьте галочками исправленные ИБ в таблице ниже и отправьте операторам..."></textarea>
                        <button class="btn-copy" onclick="copySummary()" id="copyBtn">Скопировать</button>
                    </div>
                </div>
                
                <div class="table-container">
                    <table class="main-table" id="errorsTable">
                        <thead><tr>
                            <th width="5%">Испр.</th>
                            <th width="20%">Отделение</th>
                            <th width="15%">Врач</th>
                            <th width="15%">Номер ИБ</th>
                            <th>Описание ошибки / Подсказка</th>
                        </tr></thead>
                        <tbody>
    """
    
    for i, err_dict in enumerate(errors_data):
        dept = err_dict.get('department', 'Неизвестно')
        doc = err_dict.get('doctor', 'Не указан')
        err_msg = err_dict.get('message', '')
        
        parts = err_msg.split(':', 1)
        if len(parts) == 2:
            ib_text = parts[0].strip().replace("ИБ ", "") 
            error_text = parts[1].strip()
        else:
            ib_text = "Неизвестно"
            error_text = err_msg
            
        row_type = "rec" if "Клинические рекомендации:" in error_text else "err"
        error_text = error_text.replace("[СКП]", "<span style='padding:2px 6px; border-radius:3px; font-size:0.85em; font-weight:bold; background-color:#f39c12; color:white;'>СКП</span>")
        error_text = error_text.replace("[Реанимация]", "<span style='padding:2px 6px; border-radius:3px; font-size:0.85em; font-weight:bold; background-color:#e74c3c; color:white;'>Реанимация</span>")
            
        if "<div class='hint-wrapper'>" in error_text:
            main_err, hint_html = error_text.split("<div class='hint-wrapper'>", 1)
            hint_html = "<div class='hint-wrapper'>" + hint_html
        else:
            main_err = error_text
            hint_html = ""
            
        safe_dept = dept.replace("'", "\\'")
            
        html_content += f"""
            <tr id="row_{i}" class="err-data-row" data-dept="{safe_dept}" data-type="{row_type}">
                <td><input type="checkbox" class="checkbox-custom" id="check_{i}" onclick="toggleFix({i}, '{ib_text}', '{safe_dept}')"></td>
                <td style="color:#7f8c8d; font-size:13px; font-weight:500;">{dept}</td>
                <td style="color:#34495e; font-size:13px; font-weight:600;">{doc}</td>
                <td style="font-weight:bold; color:#d35400;">{ib_text}</td>
                <td style="color:#333; line-height:1.5;">{main_err}{hint_html}</td>
            </tr>
        """
        
    html_content += f"""
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- ВКЛАДКА 2: ПРОВЕРЕННЫЕ КАРТЫ -->
            <div id="tab-checked" class="tab-content">
                <div class="controls">
                    <div class="stats-container">
                        <div class="stat-badge success">✅ Найдено записей: <span id="countTotalChk">0</span></div>
                    </div>
                    
                    <div class="filters-grid">
                        <div class="filter-group">
                            <label>Отделение:</label>
                            <div id="deptCheckListChk" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('deptCheckListChk')">Выбраны все отделения</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDeptsChk" checked onchange="toggleAllDepts('dept-cb-chk', this, 'deptCheckListChk'); filterChkTable()"> <b>(Выбрать все)</b></label></li>
                                    {dept_checkboxes_chk}
                                </ul>
                            </div>
                        </div>
                        
                        <div class="filter-group">
                            <label>Дата выбытия:</label>
                            <div id="dateCheckListChk" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('dateCheckListChk')">Выбраны все даты</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDatesChk" checked onchange="toggleAllDepts('date-cb-chk', this, 'dateCheckListChk'); filterChkTable()"> <b>(Выбрать все)</b></label></li>
                                    {date_checkboxes_chk}
                                </ul>
                            </div>
                        </div>
                        
                        <!-- НОВЫЙ ФИЛЬТР: ПОИСК ПО СОТРУДНИКУ -->
                        <div class="filter-group"><label>Поиск по сотруднику:</label><input type="text" id="docFilterChk" onkeyup="filterChkTable()"></div>

                        <div class="filter-group"><label>Поиск по ИБ:</label><input type="text" id="ibFilterChk" onkeyup="filterChkTable()"></div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table class="main-table" id="checkedTable">
                        <thead><tr>
                            <th width="15%">№ ИБ</th>
                            <th width="20%">Отделение</th>
                            <th width="20%">Сотрудник</th>
                            <th width="15%">Тип пациента</th>
                            <th width="15%">Дата выбытия</th>
                            <th width="15%">Статус</th>
                        </tr></thead>
                        <tbody id="checkedTbody">
                        </tbody>
                    </table>
                    <div id="limitWarning" class="limit-warning hidden-row">Показаны первые 500 записей для быстрой работы. Уточните поиск, чтобы найти остальные.</div>
                </div>
            </div>
        </div>

        <!-- Модальное окно -->
        <div id="recModal" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
                <h2 class="modal-header" id="modalTitle">Клинические критерии</h2>
                <div id="modalBody"></div>
            </div>
        </div>

        <script>
            const recsData = {recs_json};
            const checkedData = {checked_json}; 
            const modal = document.getElementById("recModal");

            function switchTab(tabId, btnElement) {{
                document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                btnElement.classList.add('active');
            }}
            
            function toggleDrop(listId) {{ 
                document.getElementById(listId).classList.toggle('visible'); 
            }}
            
            document.addEventListener('click', function(event) {{ 
                document.querySelectorAll('.dropdown-check-list').forEach(list => {{
                    if (!list.contains(event.target)) list.classList.remove('visible');
                }});
            }});

            function toggleAllDepts(cbClass, sourceCheckbox, listId) {{
                document.querySelectorAll('.' + cbClass).forEach(cb => cb.checked = sourceCheckbox.checked);
                updateDropdownLabel(cbClass, listId);
            }}

            function initCheckboxes(cbClass, selectAllId, listId, filterFunc) {{
                document.querySelectorAll('.' + cbClass).forEach(cb => {{
                    cb.addEventListener('change', function() {{
                        const total = document.querySelectorAll('.' + cbClass).length;
                        const checked = document.querySelectorAll('.' + cbClass + ':checked').length;
                        document.getElementById(selectAllId).checked = (total === checked);
                        updateDropdownLabel(cbClass, listId);
                        filterFunc();
                    }});
                }});
            }}

            function updateDropdownLabel(cbClass, listId) {{
                const total = document.querySelectorAll('.' + cbClass).length;
                const checked = document.querySelectorAll('.' + cbClass + ':checked').length;
                const anchor = document.getElementById(listId).querySelector('.anchor');
                
                let prefix = cbClass.includes('dept') ? "отделения" : "даты";
                
                if (checked === total) anchor.innerText = `Выбраны все ${{prefix}}`;
                else if (checked === 0) anchor.innerText = "Ничего не выбрано";
                else anchor.innerText = `Выбрано: ${{checked}}`;
            }}

            initCheckboxes('dept-cb-err', 'selectAllDeptsErr', 'deptCheckListErr', filterErrTable);
            initCheckboxes('dept-cb-chk', 'selectAllDeptsChk', 'deptCheckListChk', filterChkTable);
            initCheckboxes('date-cb-chk', 'selectAllDatesChk', 'dateCheckListChk', filterChkTable);

            // --- ФИЛЬТР ВКЛАДКИ 1 (Ошибки) ---
            function filterErrTable() {{
                const ibSearch = document.getElementById("ibFilterErr").value.toLowerCase();
                const errSearch = document.getElementById("textFilterErr").value.toLowerCase();
                const checkedDepts = new Set(Array.from(document.querySelectorAll('.dept-cb-err:checked')).map(cb => cb.value));
                const rows = document.getElementsByClassName("err-data-row");
                
                let totalCount = 0; let errCount = 0; let recCount = 0;
                
                for (let i = 0; i < rows.length; i++) {{
                    const row = rows[i];
                    const dept = row.getAttribute("data-dept");
                    const type = row.getAttribute("data-type");
                    
                    // Обновленные индексы ячеек, так как добавился "Врач"
                    const ib = row.cells[3].textContent.toLowerCase();
                    const err = row.cells[4].textContent.toLowerCase();
                    
                    if (checkedDepts.has(dept) && ib.includes(ibSearch) && err.includes(errSearch)) {{
                        row.classList.remove("hidden-row");
                        totalCount++;
                        if (type === "err") errCount++;
                        if (type === "rec") recCount++;
                    }} else {{ 
                        row.classList.add("hidden-row"); 
                    }}
                }}
                document.getElementById("countTotalErr").innerText = totalCount;
                document.getElementById("countErr").innerText = errCount;
                document.getElementById("countRec").innerText = recCount;
            }}

            // --- ФИЛЬТР ВКЛАДКИ 2 (С ДАТАМИ И СОТРУДНИКОМ) ---
            function filterChkTable() {{
                const ibSearch = document.getElementById("ibFilterChk").value.toLowerCase();
                const docSearch = document.getElementById("docFilterChk").value.toLowerCase(); // Поиск по врачу
                const checkedDepts = new Set(Array.from(document.querySelectorAll('.dept-cb-chk:checked')).map(cb => cb.value));
                const checkedDates = new Set(Array.from(document.querySelectorAll('.date-cb-chk:checked')).map(cb => cb.value));
                
                const filteredData = checkedData.filter(row => {{
                    const dept = String(row['Отделение'] || '');
                    const mk = String(row['№ МК'] || '').toLowerCase();
                    const date = String(row['Дата выбытия'] || '');
                    const emp = String(row['Сотрудник'] || '').toLowerCase();
                    
                    // Добавлено условие поиска по сотруднику
                    return checkedDepts.has(dept) && checkedDates.has(date) && mk.includes(ibSearch) && emp.includes(docSearch);
                }});

                const renderLimit = 500;
                const dataToRender = filteredData.slice(0, renderLimit);
                
                const htmlArray = dataToRender.map(row => {{
                    const mk = String(row['№ МК'] || '');
                    const dept = String(row['Отделение'] || '');
                    const emp = String(row['Сотрудник'] || '');
                    const ptype = String(row['Тип пациента'] || '');
                    const date = String(row['Дата выбытия'] || '');
                    
                    return `<tr>
                                <td style="font-weight:bold; color:#2c3e50;">${{mk}}</td>
                                <td style="color:#7f8c8d; font-size:13px;">${{dept}}</td>
                                <td>${{emp}}</td>
                                <td>${{ptype}}</td>
                                <td style="font-family:monospace; color:#8e44ad; font-weight:bold;">${{date}}</td>
                                <td style="color:#27ae60; font-weight:bold;">Проверено ✅</td>
                            </tr>`;
                }});

                document.getElementById('checkedTbody').innerHTML = htmlArray.join('');
                document.getElementById("countTotalChk").innerText = filteredData.length;
                
                const warning = document.getElementById('limitWarning');
                if (filteredData.length > renderLimit) {{
                    warning.classList.remove('hidden-row');
                }} else {{
                    warning.classList.add('hidden-row');
                }}
            }}

            // --- ЭКСПОРТ И МОДАЛКА ---
            let fixedIBs = new Map();
            function toggleFix(index, ibNumber, deptName) {{
                const row = document.getElementById('row_' + index);
                const checkbox = document.getElementById('check_' + index);
                const textLine = ibNumber + " (" + deptName + ")";
                if (checkbox.checked) {{ row.classList.add('fixed-row'); fixedIBs.set(index, textLine); }} 
                else {{ row.classList.remove('fixed-row'); fixedIBs.delete(index); }}
                updateSummary();
            }}
            
            function updateSummary() {{
                const summaryInput = document.getElementById('summaryText');
                summaryInput.value = fixedIBs.size === 0 ? "" : "Поправили:\\n" + Array.from(new Set(fixedIBs.values())).join("\\n");
            }}
            
            function copySummary() {{
                if (fixedIBs.size === 0) return alert("Сначала отметьте исправленные записи!");
                const copyText = document.getElementById("summaryText");
                copyText.select(); document.execCommand("copy");
                const btn = document.getElementById('copyBtn');
                btn.innerText = "✅ Скопировано!";
                setTimeout(() => btn.innerText = "Скопировать", 2000);
            }}

            function openModal(mesCode) {{
                const dataList = recsData[mesCode];
                if(dataList && dataList.length > 0) {{
                    document.getElementById("modalTitle").innerText = "Клинические критерии для МЭС " + mesCode;
                    const modalBody = document.getElementById("modalBody");
                    modalBody.innerHTML = ''; 
                    const table = document.createElement('table'); table.className = 'rec-table';
                    table.innerHTML = '<thead><tr><th width="15%">Обязательность</th><th width="40%">Критерии экспертизы</th><th width="20%">Документ</th><th width="25%">Поле документа</th></tr></thead>';
                    const tbody = document.createElement('tbody');
                    let lastCells = {{ req: null, crit: null, doc: null, field: null }};
                    
                    dataList.forEach(row => {{
                        let tr = document.createElement('tr');
                        const cols = [
                            {{ key: 'req', text: (row['Обязательность'] || '').toString().trim() }},
                            {{ key: 'crit', text: (row['Критерии экспертизы'] || '').toString().trim() }},
                            {{ key: 'doc', text: (row['Документ'] || '').toString().trim() }},
                            {{ key: 'field', text: (row['Поле документа'] || '').toString().trim() }}
                        ];
                        
                        cols.forEach(col => {{
                            let val = col.text;
                            if (val === '' || val === 'nan' || val === 'None') {{
                                if (lastCells[col.key]) {{ lastCells[col.key].rowSpan += 1; }} 
                                else {{ let td = document.createElement('td'); tr.appendChild(td); lastCells[col.key] = td; }}
                            }} else {{
                                let td = document.createElement('td'); td.innerHTML = val.replace(/\\n/g, '<br>');
                                tr.appendChild(td); lastCells[col.key] = td;
                            }}
                        }});
                        tbody.appendChild(tr);
                    }});
                    table.appendChild(tbody); modalBody.appendChild(table); modal.style.display = "block";
                }}
            }}
            function closeModal() {{ modal.style.display = "none"; }}
            window.onclick = function(event) {{ if (event.target == modal) closeModal(); }}
            
            // --- СЕКРЕТНАЯ ВЫГРУЗКА В EXCEL ---
            function exportSecretExcel() {{
                const table = document.getElementById("errorsTable");
                const cloneTable = table.cloneNode(true);
                const rows = cloneTable.rows;
                
                for (let i = rows.length - 1; i >= 0; i--) {{
                    if (rows[i].classList.contains("hidden-row")) {{
                        cloneTable.deleteRow(i);
                    }} else {{
                        rows[i].deleteCell(0); // Удаляем столбец с галочками, чтобы Excel был чистым
                    }}
                }}
                
                const htmlTemplate = `
                    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
                    <head>
                        <meta charset="utf-8">
                        <style>
                            table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }}
                            th, td {{ border: 1px solid #dddddd; padding: 8px; text-align: left; vertical-align: top; }}
                            th {{ background-color: #3498db; color: #ffffff; font-weight: bold; }}
                            .hint-wrapper {{ color: #555555; font-size: 12px; margin-top: 5px; }}
                        </style>
                    </head>
                    <body>
                        ${{cloneTable.outerHTML}}
                    </body>
                    </html>
                `;
                
                const blob = new Blob([htmlTemplate], {{ type: 'application/vnd.ms-excel' }});
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "Сводка_ошибок.xls";
                
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }}

            window.onload = function() {{ 
                filterErrTable(); 
                filterChkTable(); 
            }};
        </script>
    </body>
    </html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n[УСПЕХ] HTML-отчет успешно сгенерирован: {output_path}")