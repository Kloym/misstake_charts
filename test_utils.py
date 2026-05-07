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
def generate_html_report(errors_data, recs_dict, output_path):
    errors_data = sorted(errors_data, key=lambda x: "Клинические рекомендации:" in x['message'])
    
    unique_depts = sorted(list(set([err['department'] for err in errors_data])))
    dept_checkboxes = ""
    for d in unique_depts:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb" checked onchange="filterTable()"> {d}</label></li>\n'
    
    recs_json = json.dumps(recs_dict, ensure_ascii=False)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Отчет по ошибкам (mscrit)</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 30px 20px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            h1 {{ margin: 0 0 20px 0; font-size: 1.5em; color: #2c3e50; }}
            
            .controls, .export-panel {{ background: #fdfdfd; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin-bottom: 20px; }}
            
            /* НОВЫЕ БЕЙДЖИ СТАТИСТИКИ */
            .stats-container {{ display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap; }}
            .stat-badge {{ padding: 8px 15px; border-radius: 6px; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .stat-badge.total {{ background: #f8f9f9; color: #2c3e50; border: 1px solid #d5dbdb; }}
            .stat-badge.err {{ background: #fdedec; color: #c0392b; border: 1px solid #fadbd8; }}
            .stat-badge.rec {{ background: #f4ecf8; color: #8e44ad; border: 1px solid #e8daef; }}
            .stat-badge span {{ font-size: 16px; font-weight: bold; background: rgba(255,255,255,0.8); padding: 2px 8px; border-radius: 4px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }}
            
            .filters-grid {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }}
            .filter-group {{ display: flex; flex-direction: column; gap: 5px; flex: 1 1 250px; min-width: 0; }}
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
            
            /* СТИЛИ ДЛЯ ПОДСКАЗОК ПО ОПЕРАЦИЯМ И ДИАГНОЗАМ */
            .hint-details {{ margin-top: 10px; border: 1px solid #eee; border-radius: 4px; overflow: hidden; background: #fafafa; }}
            .hint-details summary {{ padding: 8px 12px; cursor: pointer; font-weight: 600; color: #2980b9; font-size: 13px; outline: none; user-select: none; }}
            .hint-details summary:hover {{ background: #f0f0f0; }}
            .hint-content {{ padding: 10px 15px; border-top: 1px solid #eee; background: #fff; max-height: 250px; overflow-y: auto; font-size: 13px; color: #555; }}
            .hint-content ul {{ margin: 0; padding-left: 20px; }}
            .hint-content li {{ margin-bottom: 4px; }}
            .hl-diag {{ background: #e8f8f5; color: #2980b9; padding: 2px 5px; border-radius: 3px; font-family: monospace; font-weight: bold; }}
            .hl-oper {{ background: #fdf2e9; color: #d35400; padding: 2px 5px; border-radius: 3px; font-family: monospace; font-weight: bold; }}
            .no-hint {{ color: #e74c3c; font-style: italic; font-size: 13px; }}
            
            /* СТИЛЬ КЛИКАБЕЛЬНОГО МЭСА ДЛЯ КЛИН. РЕКОМЕНДАЦИЙ */
            .clickable-mes {{ background: #8e44ad; color: white; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: bold; cursor: pointer; text-decoration: none; transition: 0.2s; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .clickable-mes:hover {{ background: #9b59b6; transform: translateY(-1px); box-shadow: 0 3px 6px rgba(0,0,0,0.15); }}
            
            /* Модальное окно */
            .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); }}
            .modal-content {{ background-color: #fff; margin: 5% auto; padding: 25px; border-radius: 8px; width: 95%; max-width: 1400px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); animation: fadein 0.3s; overflow-x: auto; }}
            .close-btn {{ color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
            .close-btn:hover {{ color: #333; text-decoration: none; }}
            .modal-header {{ border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 15px; color: #2c3e50; }}
            
            .rec-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .rec-table th, .rec-table td {{ border: 1px solid #e0e0e0; padding: 12px; font-size: 13px; color: #333; line-height: 1.5; vertical-align: middle; }}
            .rec-table th {{ background-color: #f8f9f9; color: #2c3e50; font-weight: bold; text-transform: none; }}
            
            @keyframes fadein {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📝 Отчет по ошибкам и критериям для врачей</h1>
            
            <div class="controls">
                <div class="stats-container">
                    <div class="stat-badge total">Всего записей: <span id="countTotal">0</span></div>
                    <div class="stat-badge err">🔴 Ошибок: <span id="countErr">0</span></div>
                    <div class="stat-badge rec">🟣 Рекомендаций: <span id="countRec">0</span></div>
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
                    <div class="filter-group"><label>Поиск по ИБ:</label><input type="text" id="ibFilter" onkeyup="filterTable()"></div>
                    <div class="filter-group"><label>Поиск по тексту:</label><input type="text" id="errorFilter" onkeyup="filterTable()"></div>
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
                    <thead><tr><th width="5%">Испр.</th><th width="25%">Отделение</th><th width="15%">Номер ИБ</th><th>Описание ошибки / Подсказка</th></tr></thead>
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
            <tr id="row_{i}" class="data-row" data-dept="{dept}" data-type="{row_type}">
                <td><input type="checkbox" class="checkbox-custom" id="check_{i}" onclick="toggleFix({i}, '{ib_text}', '{safe_dept}')"></td>
                <td style="color:#7f8c8d; font-size:13px; font-weight:500;">{dept}</td>
                <td style="font-weight:bold; color:#d35400;">{ib_text}</td>
                <td style="color:#333; line-height:1.5;">{main_err}{hint_html}</td>
            </tr>
        """
        
    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>

        <div id="recModal" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
                <h2 class="modal-header" id="modalTitle">Клинические критерии</h2>
                <div id="modalBody"></div>
            </div>
        </div>

        <script>
            const recsData = {recs_json};
            const modal = document.getElementById("recModal");
            
            function openModal(mesCode) {{
                const dataList = recsData[mesCode];
                if(dataList && dataList.length > 0) {{
                    document.getElementById("modalTitle").innerText = "Клинические критерии для МЭС " + mesCode;
                    const modalBody = document.getElementById("modalBody");
                    modalBody.innerHTML = ''; 
                    
                    const table = document.createElement('table');
                    table.className = 'rec-table';
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
                                let td = document.createElement('td');
                                td.innerHTML = val.replace(/\\n/g, '<br>');
                                tr.appendChild(td);
                                lastCells[col.key] = td;
                            }}
                        }});
                        tbody.appendChild(tr);
                    }});
                    
                    table.appendChild(tbody);
                    modalBody.appendChild(table);
                    modal.style.display = "block";
                }}
            }}
            
            function closeModal() {{ modal.style.display = "none"; }}
            window.onclick = function(event) {{ if (event.target == modal) closeModal(); }}

            const checkList = document.getElementById('deptCheckList');
            function toggleDeptDrop() {{ checkList.classList.toggle('visible'); }}
            document.addEventListener('click', function(event) {{ if (!checkList.contains(event.target) && !event.target.closest('.dropdown-check-list')) checkList.classList.remove('visible'); }});

            function toggleAllDepts(source) {{
                document.querySelectorAll('.dept-cb').forEach(cb => cb.checked = source.checked);
                updateDeptLabel(); filterTable();
            }}

            document.querySelectorAll('.dept-cb').forEach(cb => {{
                cb.addEventListener('change', function() {{
                    const allChecked = document.querySelectorAll('.dept-cb:checked').length === document.querySelectorAll('.dept-cb').length;
                    document.getElementById('selectAllDepts').checked = allChecked;
                    updateDeptLabel(); filterTable();
                }});
            }});

            function updateDeptLabel() {{
                const total = document.querySelectorAll('.dept-cb').length;
                const checked = document.querySelectorAll('.dept-cb:checked').length;
                const anchor = checkList.querySelector('.anchor');
                if (checked === total) anchor.innerText = "Выбраны все отделения";
                else if (checked === 0) anchor.innerText = "Ничего не выбрано";
                else anchor.innerText = `Выбрано отделений: ${{checked}}`;
            }}

            function filterTable() {{
                const ibSearch = document.getElementById("ibFilter").value.toLowerCase();
                const errSearch = document.getElementById("errorFilter").value.toLowerCase();
                const checkedDepts = Array.from(document.querySelectorAll('.dept-cb:checked')).map(cb => cb.value);
                const rows = document.getElementsByClassName("data-row");
                
                let totalCount = 0;
                let errCount = 0;
                let recCount = 0;
                
                for (let i = 0; i < rows.length; i++) {{
                    const row = rows[i];
                    const dept = row.getAttribute("data-dept");
                    const type = row.getAttribute("data-type");
                    const ib = row.cells[2].innerText.toLowerCase();
                    const err = row.cells[3].innerText.toLowerCase();
                    
                    if (checkedDepts.includes(dept) && ib.includes(ibSearch) && err.includes(errSearch)) {{
                        row.classList.remove("hidden-row");
                        totalCount++;
                        if (type === "err") errCount++;
                        if (type === "rec") recCount++;
                    }} else {{ 
                        row.classList.add("hidden-row"); 
                    }}
                }}
                
                document.getElementById("countTotal").innerText = totalCount;
                document.getElementById("countErr").innerText = errCount;
                document.getElementById("countRec").innerText = recCount;
            }}

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
            
            window.onload = function() {{ filterTable(); }};
        </script>
    </body>
    </html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n[УСПЕХ] HTML-отчет успешно сгенерирован: {output_path}")