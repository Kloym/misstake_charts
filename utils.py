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
def generate_html_report(errors_data, recs_dict, checked_data, emerg_dict, output_path):
    def clean_dept_name(name):
        if not name or str(name).lower() == 'nan': 
            return "Неизвестно"
        return " ".join(str(name).replace('\xa0', ' ').strip().split()).capitalize()

    for err in errors_data:
        err['department'] = clean_dept_name(err.get('department', 'Неизвестно'))

    for row in checked_data:
        if 'Отделение' in row and row['Отделение']:
            row['Отделение'] = clean_dept_name(row['Отделение'])

    errors_data = sorted(errors_data, key=lambda x: ("Клинические рекомендации:" in x['message'] or "Экстренная госпитализация:" in x['message']))
    
    unique_depts_err = sorted(list(set([err['department'] for err in errors_data])))
    dept_checkboxes_err = ""
    for d in unique_depts_err:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes_err += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb-err" checked onchange="filterErrTable()"> {d}</label></li>\n'
    
    # --- Подготовка для второй вкладки ---
    unique_depts_chk = sorted(list(set([str(row.get('Отделение', '')) for row in checked_data if str(row.get('Отделение', ''))])))
    dept_checkboxes_chk = ""
    for d in unique_depts_chk:
        safe_val = d.replace('"', '&quot;')
        dept_checkboxes_chk += f'<li><label><input type="checkbox" value="{safe_val}" class="dept-cb-chk" checked onchange="filterChkTable()"> {d}</label></li>\n'
        
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
    emerg_json = json.dumps(emerg_dict, ensure_ascii=False)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Отчет: Ошибки и Проверки</title>
        <style>
            :root {{
                --primary: #4f46e5;
                --primary-hover: #4338ca;
                --bg-color: #f3f4f6;
                --card-bg: #ffffff;
                --text-main: #1f2937;
                --text-muted: #6b7280;
                --border-color: #e5e7eb;
                --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                --radius: 12px;
            }}

            body {{ font-family: system-ui, -apple-system, sans-serif; background-color: var(--bg-color); color: var(--text-main); margin: 0; padding: 2rem 1rem; line-height: 1.5; }}
            .container {{ max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }}
            
            /* Хедер */
            .header-panel {{ display: flex; justify-content: space-between; align-items: center; background: var(--card-bg); padding: 1.5rem 2rem; border-radius: var(--radius); box-shadow: var(--shadow-md); }}
            h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 10px; }}
            
            /* Секретная кнопка экспорта */
            .secret-export {{ cursor: default; user-select: none; }}
            .info-icon {{ cursor: pointer; color: var(--text-muted); display: flex; align-items: center; transition: 0.2s; margin-left: 5px; }}
            .info-icon:hover {{ color: var(--primary); transform: scale(1.1); }}
            
            /* ВКЛАДКИ */
            .tabs-nav {{ display: flex; gap: 10px; margin-bottom: 0.5rem; }}
            .tab-btn {{ background: var(--card-bg); border: 1px solid var(--border-color); padding: 0.75rem 1.5rem; font-size: 0.95rem; font-weight: 600; color: var(--text-muted); cursor: pointer; border-radius: 8px; transition: all 0.2s ease; box-shadow: var(--shadow-sm); display: flex; align-items: center; gap: 8px; }}
            .tab-btn:hover {{ color: var(--text-main); border-color: #d1d5db; }}
            .tab-btn.active {{ background: var(--primary); color: white; border-color: var(--primary); box-shadow: var(--shadow-md); }}
            
            .tab-content {{ display: none; animation: fadein 0.3s ease-out; }}
            .tab-content.active {{ display: block; }}
            
            /* Панель управления (карточка) */
            .controls-card {{ background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); box-shadow: var(--shadow-md); margin-bottom: 1.5rem; }}
            
            .stats-container {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border-color); }}
            
            /* ЯРКИЕ СЧЕТЧИКИ */
            .stat-badge {{ padding: 0.75rem 1.25rem; border-radius: 8px; font-weight: 600; font-size: 0.95rem; display: flex; align-items: center; gap: 12px; transition: 0.2s; border: 2px solid transparent; background: var(--card-bg); box-shadow: var(--shadow-sm); }}
            
            .stat-badge.total {{ border-color: #d1d5db; color: #374151; }}
            .stat-badge.total span {{ background: #f3f4f6; color: #1f2937; }}

            .stat-badge.err {{ border-color: #fca5a5; color: #991b1b; background: #fef2f2; }}
            .stat-badge.err span {{ background: #ef4444; color: white; }}

            .stat-badge.rec {{ border-color: #d8b4fe; color: #581c87; background: #faf5ff; }}
            .stat-badge.rec span {{ background: #9333ea; color: white; }}

            .stat-badge.success {{ border-color: #86efac; color: #166534; background: #f0fdf4; }}
            .stat-badge.success span {{ background: #22c55e; color: white; }}

            .stat-badge span {{ font-family: inherit; font-size: 1rem; font-weight: 400; padding: 0.2rem 0.8rem; border-radius: 6px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }}

            .clickable-badge {{ cursor: pointer; user-select: none; }}
            .clickable-badge:hover {{ filter: brightness(0.95); transform: translateY(-2px); box-shadow: var(--shadow-md); }}
            .clickable-badge.active-filter {{ transform: scale(0.98); box-shadow: inset 0 2px 4px rgba(0,0,0,0.1); border-width: 2px; }}
            
            .filter-alert {{ display: none; padding: 1rem; border-radius: 8px; font-size: 0.9rem; margin-bottom: 1.5rem; animation: fadein 0.3s; font-weight: 500; display: flex; align-items: center; gap: 10px; }}
            .filter-alert.err-mode {{ background: #fef2f2; color: #991b1b; border-left: 4px solid #ef4444; }}
            .filter-alert.rec-mode {{ background: #faf5ff; color: #6b21a8; border-left: 4px solid #a855f7; }}
            
            /* Сетки фильтров */
            .filters-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.25rem; }}
            .filter-group {{ display: flex; flex-direction: column; gap: 0.5rem; }}
            .filter-group label {{ font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
            
            input[type="text"] {{ width: 100%; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); font-size: 0.95rem; outline: none; transition: 0.2s; box-sizing: border-box; background: #f9fafb; }}
            input[type="text"]:focus {{ border-color: var(--primary); background: white; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }}
            
            /* Выпадающий список и выравнивание чекбоксов */
            .dropdown-check-list {{ position: relative; width: 100%; }}
            .dropdown-check-list .anchor {{ width: 100%; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); background: #f9fafb; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; transition: 0.2s; box-sizing: border-box; }}
            .dropdown-check-list .anchor:hover {{ border-color: var(--text-muted); }}
            .dropdown-check-list .anchor::after {{
                content: "";
                width: 16px;
                height: 16px;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                transition: transform 0.2s ease;
            }}
            .dropdown-check-list.visible .anchor::after {{
                transform: rotate(180deg);
            }}
            .dropdown-check-list .items {{ display: none; position: absolute; top: 100%; left: 0; background: white; border: 1px solid var(--border-color); border-radius: 8px; box-shadow: var(--shadow-lg); width: 100%; z-index: 100; max-height: 300px; overflow-y: auto; padding: 0.5rem; margin-top: 0.5rem; list-style: none; box-sizing: border-box; }}
            .dropdown-check-list.visible .items {{ display: block; animation: slideDown 0.2s ease-out; }}
            .dropdown-check-list ul.items li {{ margin-bottom: 2px; }}
            .dropdown-check-list ul.items li label {{ display: flex; align-items: flex-start; gap: 10px; cursor: pointer; padding: 0.5rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; color: var(--text-main); transition: 0.2s; line-height: 1.4; border-bottom: 1px solid transparent; }}
            .dropdown-check-list ul.items li input[type="checkbox"] {{ width: 16px; height: 16px; margin: 0; margin-top: 3px; cursor: pointer; accent-color: var(--primary); flex-shrink: 0; border-radius: 4px; }}
            .dropdown-check-list ul.items li label:hover {{ background: var(--bg-color); }}
            
            /* Панель копирования */
            .export-panel {{ background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); box-shadow: var(--shadow-md); margin-bottom: 1.5rem; display: flex; gap: 1rem; align-items: stretch; }}
            #summaryText {{ flex-grow: 1; padding: 0.75rem 1rem; border: 1px solid var(--border-color); border-radius: 8px; font-family: ui-monospace, monospace; font-size: 0.85rem; resize: vertical; min-height: 45px; background: #f9fafb; outline: none; }}
            #summaryText:focus {{ border-color: var(--primary); }}
            .btn-copy {{ background: var(--primary); color: white; border: none; padding: 0 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.95rem; transition: 0.2s; white-space: nowrap; }}
            .btn-copy:hover {{ background: var(--primary-hover); box-shadow: var(--shadow-sm); }}
            
            /* ТАБЛИЦА */
            .table-container {{ background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow-md); overflow-x: auto; max-height: 75vh; overflow-y: auto; border: 1px solid var(--border-color); }}
            table.main-table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
            .main-table th, .main-table td {{ padding: 1rem; text-align: left; border-bottom: 1px solid var(--border-color); vertical-align: middle; font-size: 0.9rem; }}
            .main-table th {{ background: rgba(249, 250, 251, 0.95); backdrop-filter: blur(4px); color: var(--text-muted); position: sticky; top: 0; z-index: 50; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; border-bottom: 2px solid var(--border-color); }}
            .main-table tbody tr {{ transition: background 0.2s; }}
            .main-table tbody tr:hover {{ background-color: #f8fafc; }}
            .fixed-row td {{ text-decoration: line-through; opacity: 0.4; background-color: #f9fafb; }}
            
            .hidden-row {{ display: none !important; }}

            .hint-details {{ margin-top: 12px; }}
            .hint-details summary {{ 
                display: inline-block; 
                cursor: pointer; 
                background: #eff6ff; 
                color: #4338ca; 
                padding: 6px 14px; 
                border-radius: 8px; 
                font-size: 0.85rem; 
                font-weight: 600; 
                border: 1px solid #c7d2fe; 
                transition: all 0.2s ease; 
                user-select: none; 
            }}
            .hint-details summary:hover {{ 
                background: #e0e7ff; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
            }}
            /* Убираем стандартный черный контур при клике */
            .hint-details summary:focus {{ outline: none; }}
            
            /* Блок с самим текстом подсказки внутри */
            .hint-content {{ 
                margin-top: 8px; 
                padding: 12px 16px; 
                background: #f8fafc; 
                border: 1px dashed #cbd5e1; 
                border-radius: 8px; 
                font-size: 0.85rem; 
                color: var(--text-main);
            }}
            .hint-content ul {{ margin: 0; padding-left: 20px; }}
            .hint-content li {{ margin-bottom: 6px; }}
            
            /* Подсветка диагнозов и операций внутри подсказки */
            .hl-diag {{ font-weight: 700; color: #b91c1c; background: #fef2f2; padding: 1px 4px; border-radius: 4px; }}
            .hl-oper {{ font-weight: 700; color: #0f766e; background: #f0fdf4; padding: 1px 4px; border-radius: 4px; }}
            
            .checkbox-wrapper {{ text-align: center; vertical-align: middle; }}
            input.checkbox-custom {{ width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary); border-radius: 4px; margin: 0; vertical-align: middle; }}
            
            /* Клиника и МЭС бейджи */
            .clickable-mes {{ background: var(--primary); color: white; padding: 0.2rem 0.5rem; border-radius: 6px; font-family: ui-monospace, monospace; font-weight: bold; cursor: pointer; transition: 0.2s; display: inline-block; box-shadow: var(--shadow-sm); font-size: 0.85rem; }}
            .clickable-mes:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-md); }}
            
            /* Заглушка пустого поиска */
            #emptyStateErr, #emptyStateChk {{ display: none; text-align: center; padding: 4rem 2rem; color: var(--text-muted); }}
            .empty-icon {{ font-size: 3rem; margin-bottom: 1rem; opacity: 0.5; }}
            
            /* Модалка */
            .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(17, 24, 39, 0.7); backdrop-filter: blur(4px); }}
            .modal-content {{ background: var(--card-bg); margin: 5vh auto; padding: 2rem; border-radius: 16px; width: 95%; max-width: 1200px; box-shadow: var(--shadow-lg); animation: slideUp 0.3s ease-out; max-height: 85vh; overflow-y: auto; position: relative; }}
            .close-btn {{ position: absolute; right: 1.5rem; top: 1.5rem; background: var(--bg-color); border: none; width: 32px; height: 32px; border-radius: 50%; font-size: 1.2rem; cursor: pointer; color: var(--text-muted); display: flex; align-items: center; justify-content: center; transition: 0.2s; }}
            .close-btn:hover {{ background: #e5e7eb; color: var(--text-main); }}
            .modal-header {{ margin-top: 0; color: var(--text-main); padding-right: 2rem; border-bottom: 2px solid var(--bg-color); padding-bottom: 1rem; margin-bottom: 1.5rem; }}
            .modal-footer {{ margin-top: 25px; padding-top: 15px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; }}
            .btn-close-bottom {{ background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; padding: 0.6rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; font-size: 0.95rem; }}
            .btn-close-bottom:hover {{ background: #e5e7eb; border-color: #9ca3af; }}

            .rec-table {{ width: 100%; border-collapse: collapse; }}
            .rec-table th, .rec-table td {{ border: 1px solid var(--border-color); padding: 0.75rem; font-size: 0.85rem; }}
            .rec-table th {{ background: var(--bg-color); font-weight: 600; color: var(--text-main); }}
            
            @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            @keyframes slideDown {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            @keyframes slideUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}

            /* Мобильная адаптация */
            @media (max-width: 768px) {{
                body {{ padding: 1rem 0.5rem; }}
                .container {{ gap: 1rem; }}
                .header-panel {{ flex-direction: column; gap: 1rem; align-items: flex-start; padding: 1.25rem; }}
                
                .tabs-nav {{ width: 100%; flex-wrap: wrap; }}
                .tab-btn {{ flex: 1 1 calc(50% - 5px); text-align: center; padding: 0.75rem; font-size: 0.85rem; justify-content: center; }}
                
                .stats-container {{ flex-direction: column; gap: 0.75rem; }}
                .stat-badge {{ justify-content: space-between; }}
                
                .export-panel {{ flex-direction: column; }}
                .btn-copy {{ padding: 1rem; }}
                
                .modal-content {{ padding: 1.5rem 1rem; margin: 2vh auto; width: 100%; border-radius: 12px 12px 0 0; min-height: 50vh; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            
            <div class="header-panel">
                <h1>
                    <span class="secret-export" onclick="exportSecretExcel()" title="Скрытый экспорт в Excel">📝</span> Ошибки и карты для врачей
                    <span class="info-icon" onclick="openInfoModal()" title="Справочник по работе системы">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </span>
                </h1>
            </div>
            
            <div class="tabs-nav">
                <button class="tab-btn active" onclick="switchTab('tab-errors', this)">🔴 Ошибки ({len(errors_data)})</button>
                <button class="tab-btn" onclick="switchTab('tab-checked', this)">✅ Проверенные ({len(checked_data)})</button>
            </div>
            
            <div id="tab-errors" class="tab-content active">
                
                <div class="controls-card">
                    <div class="stats-container">
                        <div class="stat-badge total">Всего записей: <span id="countTotalErr">0</span></div>
                        <div class="stat-badge err clickable-badge" id="badgeErr" onclick="toggleTypeFilter('err')" title="Оставить только ошибки">Ошибок: <span id="countErr">0</span></div>
                        <div class="stat-badge rec clickable-badge" id="badgeRec" onclick="toggleTypeFilter('rec')" title="Оставить только рекомендации">Рекомендаций: <span id="countRec">0</span></div>
                    </div>
                    
                    <div id="filterAlert" class="filter-alert" style="display: none;">
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <span id="filterAlertText"></span>
                    </div>
                    
                    <div class="filters-grid">
                        <div class="filter-group">
                            <label>Отделение</label>
                            <div id="deptCheckListErr" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('deptCheckListErr')">Все отделения</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDeptsErr" checked onchange="toggleAllDepts('dept-cb-err', this, 'deptCheckListErr'); filterErrTable()"> <b>(Выбрать все)</b></label></li>
                                    {dept_checkboxes_err}
                                </ul>
                            </div>
                        </div>
                        <div class="filter-group"><label>Поиск по номеру ИБ</label><input type="text" id="ibFilterErr" placeholder="Например: 12345" onkeyup="filterErrTable()"></div>
                        <div class="filter-group"><label>Поиск по тексту ошибки</label><input type="text" id="textFilterErr" placeholder="Например: МЭС 72030" onkeyup="filterErrTable()"></div>
                    </div>
                </div>
                
                <div class="export-panel">
                    <textarea id="summaryText" readonly placeholder="Отметьте галочками исправленные ИБ в таблице ниже, чтобы сгенерировать текст для отправки операторам..."></textarea>
                    <button class="btn-copy" onclick="copySummary()" id="copyBtn">Скопировать текст</button>
                </div>
                
                <div class="table-container">
                    <table class="main-table" id="errorsTable">
                        <thead><tr>
                            <th width="5%" style="text-align: center;">✓</th>
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
            
        row_type = "rec" if ("Клинические рекомендации:" in error_text or "Экстренная госпитализация:" in error_text) else "err"
        
        error_text = error_text.replace("[СКП]", "<span style='padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold; background-color:#f59e0b; color:white;'>СКП</span>")
        error_text = error_text.replace("[Реанимация]", "<span style='padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold; background-color:#ef4444; color:white;'>Реанимация</span>")
            
        if "<div class='hint-wrapper'>" in error_text:
            main_err, hint_html = error_text.split("<div class='hint-wrapper'>", 1)
            hint_html = "<div class='hint-wrapper' style='margin-top: 10px;'>" + hint_html
        else:
            main_err = error_text
            hint_html = ""
            
        safe_dept = dept.replace("'", "\\'")
            
        html_content += f"""
            <tr id="row_{i}" class="err-data-row" data-dept="{safe_dept}" data-type="{row_type}">
                <td class="checkbox-wrapper"><input type="checkbox" class="checkbox-custom" id="check_{i}" onclick="toggleFix({i}, '{ib_text}', '{safe_dept}')"></td>
                <td style="color:var(--text-muted); font-weight:500;">{dept}</td>
                <td style="color:var(--text-main); font-weight:600;">{doc}</td>
                <td style="font-weight:700; color:var(--primary);">{ib_text}</td>
                <td style="color:var(--text-main);">{main_err}{hint_html}</td>
            </tr>
        """
        
    html_content += f"""
                        </tbody>
                    </table>
                    <div id="emptyStateErr">
                        <div class="empty-icon">🔍</div>
                        <h3>Ничего не найдено</h3>
                        <p>Попробуйте изменить параметры фильтра или очистить строку поиска.</p>
                    </div>
                </div>
            </div>

            <div id="tab-checked" class="tab-content">
                <div class="controls-card">
                    <div class="stats-container">
                        <div class="stat-badge success">Найдено записей: <span id="countTotalChk">0</span></div>
                    </div>
                    
                    <div class="filters-grid">
                        <div class="filter-group">
                            <label>Отделение</label>
                            <div id="deptCheckListChk" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('deptCheckListChk')">Все отделения</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDeptsChk" checked onchange="toggleAllDepts('dept-cb-chk', this, 'deptCheckListChk'); filterChkTable()"> <b>(Выбрать все)</b></label></li>
                                    {dept_checkboxes_chk}
                                </ul>
                            </div>
                        </div>
                        
                        <div class="filter-group">
                            <label>Дата выбытия</label>
                            <div id="dateCheckListChk" class="dropdown-check-list" tabindex="100">
                                <span class="anchor" onclick="toggleDrop('dateCheckListChk')">Все даты</span>
                                <ul class="items">
                                    <li><label><input type="checkbox" id="selectAllDatesChk" checked onchange="toggleAllDepts('date-cb-chk', this, 'dateCheckListChk'); filterChkTable()"> <b>(Выбрать все)</b></label></li>
                                    {date_checkboxes_chk}
                                </ul>
                            </div>
                        </div>
                        
                        <div class="filter-group"><label>Сотрудник</label><input type="text" id="docFilterChk" placeholder="ФИО врача" onkeyup="filterChkTable()"></div>
                        <div class="filter-group"><label>Номер ИБ</label><input type="text" id="ibFilterChk" placeholder="Номер ИБ" onkeyup="filterChkTable()"></div>
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
                    <div id="emptyStateChk">
                        <div class="empty-icon">🔍</div>
                        <h3>Ничего не найдено</h3>
                        <p>По вашему запросу нет проверенных карт.</p>
                    </div>
                    <div id="limitWarning" class="limit-warning hidden-row" style="color: #b45309; background-color: #fef3c7; font-weight: 600; padding: 12px; border-bottom: 1px solid #fde68a;">
                        ⚠️ Показаны первые 500 записей. Уточните поиск, чтобы найти остальные.
                    </div>
                </div>
            </div>
        </div>

        <div id="recModal" class="modal">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal()">&times;</button>
                <h2 class="modal-header" id="modalTitle">Справочная информация</h2>
                <div id="modalBody"></div>
                <div class="modal-footer">
                    <button class="btn-close-bottom" onclick="closeModal()">Закрыть</button>
                </div>
            </div>
        </div>

        <script>
            const recsData = {recs_json};
            const checkedData = {checked_json}; 
            const emergData = {emerg_json};
            
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
                const allCheckboxes = document.querySelectorAll('.' + cbClass);
                allCheckboxes.forEach(cb => {{
                    const li = cb.closest('li');
                    // НОВОЕ: Меняем галочки только у видимых отделений
                    if (!li || li.style.display !== 'none') {{
                        cb.checked = sourceCheckbox.checked;
                    }}
                }});
                updateDropdownLabel(cbClass, listId);
            }}

            function initCheckboxes(cbClass, selectAllId, listId, filterFunc) {{
                document.querySelectorAll('.' + cbClass).forEach(cb => {{
                    cb.addEventListener('change', function() {{
                        const allCheckboxes = Array.from(document.querySelectorAll('.' + cbClass));
                        // НОВОЕ: Считаем только видимые отделения
                        const visibleCheckboxes = allCheckboxes.filter(c => {{
                            const li = c.closest('li');
                            return !li || li.style.display !== 'none';
                        }});
                        const total = visibleCheckboxes.length;
                        const checked = visibleCheckboxes.filter(c => c.checked).length;
                        
                        document.getElementById(selectAllId).checked = (total > 0 && total === checked);
                        updateDropdownLabel(cbClass, listId);
                        filterFunc();
                    }});
                }});
            }}

            function updateDropdownLabel(cbClass, listId) {{
                const allCheckboxes = Array.from(document.querySelectorAll('.' + cbClass));
                const visibleCheckboxes = allCheckboxes.filter(c => {{
                    const li = c.closest('li');
                    return !li || li.style.display !== 'none';
                }});
                
                const total = visibleCheckboxes.length;
                const checked = visibleCheckboxes.filter(c => c.checked).length;
                const anchor = document.getElementById(listId).querySelector('.anchor');
                
                if (total === 0) anchor.innerText = "Нет доступных";
                else if (checked === total) anchor.innerText = "Выбрано всё";
                else if (checked === 0) anchor.innerText = "Ничего не выбрано";
                else anchor.innerText = `Выбрано: ${{checked}}`;
            }}

            // НОВАЯ ФУНКЦИЯ: Скрывает пустые отделения в выпадающем списке
            function updateDeptDropdownVisibility() {{
                const rows = document.getElementsByClassName("err-data-row");
                const availableDepts = new Set();

                for (let i = 0; i < rows.length; i++) {{
                    const type = rows[i].getAttribute("data-type");
                    const dept = rows[i].getAttribute("data-dept");
                    
                    if (currentTypeFilter === 'all' || type === currentTypeFilter) {{
                        availableDepts.add(dept);
                    }}
                }}

                const checkboxes = document.querySelectorAll('.dept-cb-err');
                checkboxes.forEach(cb => {{
                    const li = cb.closest('li');
                    if (availableDepts.has(cb.value)) {{
                        li.style.display = ''; // Показываем
                    }} else {{
                        li.style.display = 'none'; // Скрываем
                    }}
                }});

                updateDropdownLabel('dept-cb-err', 'deptCheckListErr');
            }}

            let currentTypeFilter = 'all';

            function toggleTypeFilter(type) {{
                document.getElementById('badgeErr').classList.remove('active-filter');
                document.getElementById('badgeRec').classList.remove('active-filter');
                const alertBox = document.getElementById('filterAlert');
                const alertText = document.getElementById('filterAlertText');

                if (currentTypeFilter === type) {{
                    currentTypeFilter = 'all';
                    alertBox.style.display = 'none';
                    alertBox.className = 'filter-alert'; 
                }} else {{
                    currentTypeFilter = type;
                    alertBox.style.display = 'flex';
                    if (type === 'err') {{
                        document.getElementById('badgeErr').classList.add('active-filter');
                        alertText.innerHTML = 'Включен фильтр: <b>Только ошибки</b>. Нажмите на красную кнопку еще раз, чтобы сбросить.';
                        alertBox.className = 'filter-alert err-mode';
                    }} else if (type === 'rec') {{
                        document.getElementById('badgeRec').classList.add('active-filter');
                        alertText.innerHTML = 'Включен фильтр: <b>Только рекомендации</b>. Нажмите на фиолетовую кнопку еще раз, чтобы сбросить.';
                        alertBox.className = 'filter-alert rec-mode';
                    }}
                }}

                updateDeptDropdownVisibility();
                filterErrTable();
            }}

            function filterErrTable() {{
                const ibSearch = document.getElementById("ibFilterErr").value.toLowerCase();
                const errSearch = document.getElementById("textFilterErr").value.toLowerCase();
                const checkedDepts = new Set(Array.from(document.querySelectorAll('.dept-cb-err:checked')).map(cb => cb.value));
                const rows = document.getElementsByClassName("err-data-row");
                
                let visibleTotal = 0; 
                let actualErrCount = 0; 
                let actualRecCount = 0;
                
                for (let i = 0; i < rows.length; i++) {{
                    const row = rows[i];
                    const dept = row.getAttribute("data-dept");
                    const type = row.getAttribute("data-type");
                    
                    const ib = row.cells[3].textContent.toLowerCase();
                    const err = row.cells[4].textContent.toLowerCase();
                    
                    const matchesBase = checkedDepts.has(dept) && ib.includes(ibSearch) && err.includes(errSearch);
                    
                    if (matchesBase) {{
                        if (type === "err") actualErrCount++;
                        if (type === "rec") actualRecCount++;
                        
                        const typeMatches = (currentTypeFilter === 'all' || type === currentTypeFilter);
                        if (typeMatches) {{
                            row.classList.remove("hidden-row");
                            visibleTotal++;
                        }} else {{
                            row.classList.add("hidden-row");
                        }}
                    }} else {{ 
                        row.classList.add("hidden-row"); 
                    }}
                }}
                
                document.getElementById("countTotalErr").innerText = visibleTotal;
                document.getElementById("countErr").innerText = actualErrCount;
                document.getElementById("countRec").innerText = actualRecCount;
                
                const emptyState = document.getElementById("emptyStateErr");
                const table = document.getElementById("errorsTable");
                if (visibleTotal === 0) {{
                    emptyState.style.display = "block";
                    table.style.display = "none";
                }} else {{
                    emptyState.style.display = "none";
                    table.style.display = "table";
                }}
            }}

            function filterChkTable() {{
                const ibSearch = document.getElementById("ibFilterChk").value.toLowerCase();
                const docSearch = document.getElementById("docFilterChk").value.toLowerCase(); 
                const checkedDepts = new Set(Array.from(document.querySelectorAll('.dept-cb-chk:checked')).map(cb => cb.value));
                const checkedDates = new Set(Array.from(document.querySelectorAll('.date-cb-chk:checked')).map(cb => cb.value));
                
                const filteredData = checkedData.filter(row => {{
                    const dept = String(row['Отделение'] || '');
                    const mk = String(row['№ МК'] || '').toLowerCase();
                    const date = String(row['Дата выбытия'] || '');
                    const emp = String(row['Сотрудник'] || '').toLowerCase();
                    
                    return checkedDepts.has(dept) && checkedDates.has(date) && mk.includes(ibSearch) && emp.includes(docSearch);
                }});

                filteredData.sort((a, b) => {{
                    const parseDate = (dStr) => {{
                        if (!dStr || dStr === 'Нет даты') return 0;
                        const parts = dStr.split('.');
                        if (parts.length === 3) return new Date(`${{parts[2]}}-${{parts[1]}}-${{parts[0]}}`).getTime();
                        return 0;
                    }};
                    return parseDate(b['Дата выбытия']) - parseDate(a['Дата выбытия']);
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
                                <td style="font-weight:700; color:var(--text-main);">${{mk}}</td>
                                <td style="color:var(--text-muted);">${{dept}}</td>
                                <td>${{emp}}</td>
                                <td><span style="background:var(--bg-color); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid var(--border-color);">${{ptype}}</span></td>
                                <td style="font-family:monospace; color:var(--rec-text); font-weight:bold;">${{date}}</td>
                                <td><span style="background:#f0fdf4; color:#15803d; border: 2px solid #22c55e; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; display:inline-flex; align-items:center; gap:5px;"><svg width="16" height="16" fill="none" stroke="#16a34a" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>Проверено</span></td>
                            </tr>`;
                }});

                document.getElementById('checkedTbody').innerHTML = htmlArray.join('');
                document.getElementById("countTotalChk").innerText = filteredData.length;
                
                const warning = document.getElementById('limitWarning');
                if (filteredData.length > renderLimit) warning.classList.remove('hidden-row');
                else warning.classList.add('hidden-row');
                
                const emptyState = document.getElementById("emptyStateChk");
                const table = document.getElementById("checkedTable");
                if (filteredData.length === 0) {{
                    emptyState.style.display = "block";
                    table.style.display = "none";
                }} else {{
                    emptyState.style.display = "none";
                    table.style.display = "table";
                }}
            }}

            let fixedIBs = new Map();
            function toggleFix(index, ibNumber, deptName) {{
                const row = document.getElementById('row_' + index);
                const checkbox = document.getElementById('check_' + index);
                const type = row.getAttribute('data-type'); // Получаем тип: 'err' или 'rec'

                // Если это рекомендация и пользователь пытается поставить галочку
                if (type === 'rec' && checkbox.checked) {{
                    alert("УВЕДОМЛЕНИЕ\\n\\nДанный пункт является справочной рекомендацией, а не ошибкой. \\n\\nВам необходимо самостоятельно проверить корректность и полноту оформления медицинской документации пациента согласно указанным требованиям.\\n\\nНаправлять данный номер ИБ операторам для исправления не требуется.");
                    checkbox.checked = false; // Сбрасываем галочку обратно
                    return; // Прерываем выполнение функции
                }}

                // Стандартная логика для настоящих ошибок
                const textLine = ibNumber + " (" + deptName + ")";
                if (checkbox.checked) {{ 
                    row.classList.add('fixed-row'); 
                    fixedIBs.set(index, textLine); 
                }} else {{ 
                    row.classList.remove('fixed-row'); 
                    fixedIBs.delete(index); 
                }}
                updateSummary();
            }}
            
            function updateSummary() {{
                const summaryInput = document.getElementById('summaryText');
                summaryInput.value = fixedIBs.size === 0 ? "" : "Поправили:\\n" + Array.from(new Set(fixedIBs.values())).join("\\n");
            }}
            
            function copySummary() {{
                if (fixedIBs.size === 0) return alert("Сначала отметьте галочками исправленные записи в таблице!");
                const copyText = document.getElementById("summaryText");
                copyText.select(); document.execCommand("copy");
                const btn = document.getElementById('copyBtn');
                btn.innerHTML = "✅ Скопировано!";
                btn.style.background = "var(--success-text)";
                setTimeout(() => {{
                    btn.innerHTML = "Скопировать текст";
                    btn.style.background = "";
                }}, 2000);
            }}

            function openModal(mesCode) {{
                const dataList = recsData[mesCode];
                if(dataList && dataList.length > 0) {{
                    document.getElementById("modalTitle").innerText = "Клинические критерии: МЭС " + mesCode;
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
            
            function openEmergModal(key) {{
                const dataList = emergData[key];
                if(dataList && dataList.length > 0) {{
                    const mesCodeForTitle = key.split('_')[0];
                    document.getElementById("modalTitle").innerText = "Экстренная госпитализация: МЭС " + mesCodeForTitle;
                    
                    const modalBody = document.getElementById("modalBody");
                    modalBody.innerHTML = ''; 
                    
                    const table = document.createElement('table'); 
                    table.className = 'rec-table';
                    table.innerHTML = `<thead><tr>
                        <th>№</th><th>Код услуги</th><th>Название услуги</th>
                        <th>МКБ-10</th><th>Критерии экстренной госпитализации</th><th>Профиль</th>
                    </tr></thead>`;
                    const tbody = document.createElement('tbody');
                    
                    dataList.forEach(row => {{
                        let tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td style="text-align:center;">${{row['№ п/п'] || ''}}</td>
                            <td style="font-family:monospace; font-weight:bold;">${{row['Код услуги'] || ''}}</td>
                            <td>${{row['Наименование услуги'] || ''}}</td>
                            <td style="font-weight:bold; color:var(--primary);">${{row['Код по МКБ-10'] || ''}}</td>
                            <td style="color: var(--text-main);">${{(row['Критерии'] || '').toString().replace(/\\n/g, '<br>')}}</td>
                            <td><span style="background:var(--bg-color); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid var(--border-color); white-space: nowrap;">${{row['Профиль'] || ''}}</span></td>
                        `;
                        tbody.appendChild(tr);
                    }});
                    
                    table.appendChild(tbody); 
                    modalBody.appendChild(table); 
                    modal.style.display = "block";
                }}
            }}
            function openInfoModal() {{
                document.getElementById("modalTitle").innerText = "Руководство пользователя: Ошибок и Карт";
                const modalBody = document.getElementById("modalBody");
                
                modalBody.innerHTML = `
                    <div style="font-size: 0.95rem; line-height: 1.6; color: var(--text-main); padding-right: 10px;">
                        
                        <h3 style="color: var(--text-main); border-bottom: 2px solid var(--border-color); padding-bottom: 5px;">1. Разница между Ошибками и Рекомендациями</h3>
                        
                        <h4 style="color: #b91c1c; display: flex; align-items: center; gap: 10px; margin-top: 15px;">
                            <span style="background: #fef2f2; padding: 4px 10px; border-radius: 6px; border: 1px solid #fca5a5;">🔴 Ошибки</span>
                        </h4>
                        <p style="margin-bottom: 15px;"><b>Ошибки</b> — это критические нарушения в формировании случая лечения. К ним относятся: несоответствие кода МЭС диагнозу по МКБ-10, отсутствие обязательной хирургической операции, неверно указанный тип анестезии или нарушение правил перевода между отделениями(Код прерывания) и т.д.<br>
                        <p style="margin-bottom: 25px;">Такие случаи <b>строго подлежат исправлению</b>. Лечащему врачу необходимо внести соответствующие корректировки в медицинскую информационную систему для успешной подачи реестров на оплату.</p>

                        <h4 style="color: #6d28d9; display: flex; align-items: center; gap: 10px;">
                            <span style="background: #faf5ff; padding: 4px 10px; border-radius: 6px; border: 1px solid #d8b4fe;">🟣 Рекомендации</span>
                        </h4>
                        <p style="margin-bottom: 20px;"><b>Рекомендации</b> (клинические критерии и критерии экстренной госпитализации) — это информационные уведомления. Они указывают на то, что для выбранного кода МЭС и диагноза существуют строгие критерии оценки качества медицинской помощи.</p>
                        <p style="margin-bottom: 0;">Данные уведомления <b>не являются ошибкой</b>. Они призывают лечащего врача убедиться, что в текстовой части истории болезни (дневники, выписной эпикриз, результаты анализов) подробно описаны все показания и обоснования. Направлять такие случаи операторам для изменения кодов <b>не требуется</b>.</p>

                        <h3 style="color: var(--text-main); border-bottom: 2px solid var(--border-color); padding-bottom: 5px; margin-top: 25px;">2. Интерактивные элементы</h3>
                        <ul style="padding-left: 20px; margin-bottom: 20px;">
                            <li style="margin-bottom: 10px;"><b>Коды МЭС, которые можно нажать:</b> Если вы видите в тексте рекомендаций яркую цветную кнопку с кодом МЭС (например, <span style="background: var(--primary); color: white; padding: 2px 6px; border-radius: 4px; font-family: monospace;">72030</span>) — смело нажимайте на нее! Откроется подробный справочник с правилами и требованиями для этого кода.</li>
                            <li style="margin-bottom: 10px;"><b>Сбор отчета для операторов:</b> Отмечайте квадратики слева (✓) у тех ошибок, которые вы обработали. Система автоматически соберет номера ИБ в удобный список в текстовом поле выше. Нажмите <b>«Скопировать текст»</b> и отправьте его операторам в чат.</li>
                            <li><b>Быстрые фильтры:</b> Кликните на яркую плашку <span style="background: #fef2f2; color: #991b1b; padding: 2px 6px; border-radius: 4px; border: 1px solid #fca5a5; font-weight: bold;">Ошибок: 15</span> в верхней статистике, чтобы моментально скрыть все рекомендации и оставить на экране только строгие ошибки (нажмите еще раз для сброса).</li>
                        </ul>

                        <h3 style="color: var(--text-main); border-bottom: 2px solid var(--border-color); padding-bottom: 5px; margin-top: 25px;">3. Проверенные карты</h3>
                        <p style="margin-bottom: 15px; color: #991b1b; background: #fef2f2; padding: 10px 12px; border-radius: 6px; border: 1px solid #fca5a5;">
                            <b>⚠️ ВАЖНО: Подписывать можно только те карты, которые успешно прошли проверку и присутствуют в списке на вкладке «Проверенные»!</b>
                        </p>                        
                        <p style="margin-bottom: 10px;">Для обеспечения быстрой работы без зависаний браузера <b>одновременно отображается не более 500 записей</b>.</p>
                        <p style="margin-bottom: 0; background: #f0fdf4; color: #166534; padding: 10px 12px; border-radius: 6px; border: 1px solid #bbf7d0;">
                            <b>💡 Правильная работа с выпадающим списком:</b> По умолчанию в фильтре выбраны все отделения сразу. Чтобы быстро найти своё, сначала нажмите на главную галочку <b>(Выбрать все)</b> — это очистит весь список. После этого просто отметьте нужное вам отделение.
                        </p>                       
                        <p style="margin-bottom: 10px;"><b>Как найти нужную карту:</b> Обязательно используйте фильтры! Выберите конкретное <i>отделение</i> или введите <i>Номер ИБ / ФИО врача</i>. Система автоматически отсортирует базу и покажет самые новые выписки (последние даты) на самом верху списка.</p>                        
                    </div>

                `;
                
                modal.style.display = "block";
            }}

            function closeModal() {{ modal.style.display = "none"; }}
            window.onclick = function(event) {{ if (event.target == modal) closeModal(); }}
            window.addEventListener('keydown', function(event) {{
                if (event.key === 'Escape' || event.key === 'Esc') {{
                    closeModal();
                }}
            }});
            
            function exportSecretExcel() {{
                const table = document.getElementById("errorsTable");
                const cloneTable = table.cloneNode(true);
                const rows = cloneTable.rows;
                
                for (let i = rows.length - 1; i >= 0; i--) {{
                    if (rows[i].classList.contains("hidden-row")) {{
                        cloneTable.deleteRow(i);
                    }} else {{
                        rows[i].deleteCell(0); 
                    }}
                }}
                
                const htmlTemplate = `
                    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
                    <head>
                        <meta charset="utf-8">
                        <style>
                            table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }}
                            th, td {{ border: 1px solid #dddddd; padding: 8px; text-align: left; vertical-align: top; }}
                            th {{ background-color: #4f46e5; color: #ffffff; font-weight: bold; }}
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
                updateDeptDropdownVisibility();
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