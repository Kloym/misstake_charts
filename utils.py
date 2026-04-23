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
            h1 {{ margin: 0 0 20px 0; font-size: 1.5em; color: #2c3e50; }}
            .controls {{ background: #fdfdfd; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin-bottom: 20px; }}
            .stats {{ font-weight: bold; color: #3498db; font-size: 1.1em; margin-bottom: 15px; }}
            .filters-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
            .filter-group {{ display: flex; flex-direction: column; gap: 5px; }}
            .filter-group label {{ font-size: 0.85em; font-weight: 600; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; }}
            input[type="text"] {{ padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; outline: none; }}
            input[type="text"]:focus {{ border-color: #3498db; }}
            .dropdown-check-list {{ display: inline-block; position: relative; width: 100%; }}
            .dropdown-check-list .anchor {{ width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid #ccc; background: #fff; cursor: pointer; display: block; box-sizing: border-box; font-size: 14px; user-select: none; color: #333; }}
            .dropdown-check-list .anchor:after {{ content: '▼'; float: right; font-size: 10px; color: #7f8c8d; margin-top: 4px; }}
            .dropdown-check-list .items {{ padding: 8px; display: none; position: absolute; background: #fff; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 100%; box-sizing: border-box; z-index: 100; max-height: 250px; overflow-y: auto; margin: 0; list-style: none; }}
            .dropdown-check-list.visible .items {{ display: block; }}
            .dropdown-check-list ul.items li {{ list-style: none; margin-bottom: 5px; font-size: 13px; }}
            .dropdown-check-list ul.items li label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px; border-radius: 4px; }}
            .dropdown-check-list ul.items li label:hover {{ background: #f4f6f6; }}
            .export-panel {{ background: #fdfdfd; border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 10px; }}
            .export-panel strong {{ color: #2c3e50; font-size: 1.1em; }}
            .export-controls {{ display: flex; gap: 15px; align-items: stretch; }}
            #summaryText {{ flex-grow: 1; padding: 10px 15px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 13px; outline: none; resize: vertical; min-height: 60px; white-space: pre; color: #555; background: #fff; }}
            .btn-copy {{ background: #27ae60; color: white; border: none; padding: 0 20px; border-radius: 4px; cursor: pointer; font-weight: bold; transition: background 0.2s; white-space: nowrap; font-size: 14px; }}
            .btn-copy:hover {{ background: #2ecc71; }}
            .table-container {{ overflow-x: auto; max-height: 65vh; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px; }}
            table {{ width: 100%; border-collapse: collapse; background: #fff; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
            th {{ background-color: #3498db; color: #ffffff; position: sticky; top: 0; z-index: 50; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            tbody tr:hover {{ background-color: #fcfcfc; }}
            .ib-col {{ font-weight: bold; color: #d35400; font-size: 15px; }}
            .error-col {{ color: #333; font-size: 14px; line-height: 1.5; }}
            .error-col b {{ color: #333; }}
            .dept-col {{ color: #7f8c8d; font-size: 13px; font-weight: 500; }}
            .fixed-row td {{ text-decoration: line-through; opacity: 0.5; background-color: #f9f9f9; }}
            .checkbox-custom {{ width: 18px; height: 18px; cursor: pointer; accent-color: #27ae60; margin-top: 2px; }}
            .hidden-row {{ display: none !important; }}
            .context-tag {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; font-weight: bold; margin-bottom: 5px; background-color: #f39c12; color: white; }}
            .tag-rean {{ background-color: #e74c3c; }}
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
            <h1>📝 Отчет по ошибкам для врачей:</h1>
            
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
                    <textarea id="summaryText" readonly placeholder="Отметьте галочками исправленные ИБ в таблице ниже и отправьте появившийся текст операторам..."></textarea>
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
            const checkList = document.getElementById('deptCheckList');
            function toggleDeptDrop() { checkList.classList.toggle('visible'); }
            
            document.addEventListener('click', function(event) {
                if (!checkList.contains(event.target)) { checkList.classList.remove('visible'); }
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

            let fixedIBs = new Map();

            function toggleFix(index, ibNumber, deptName) {
                const row = document.getElementById('row_' + index);
                const checkbox = document.getElementById('check_' + index);
                const textLine = ibNumber + " (" + deptName + ")";
                
                if (checkbox.checked) {
                    row.classList.add('fixed-row');
                    fixedIBs.set(index, textLine);
                } else {
                    row.classList.remove('fixed-row');
                    fixedIBs.delete(index);
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