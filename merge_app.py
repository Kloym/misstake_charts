import pandas as pd
import os
import time
import traceback
import ctypes
import sys
import glob

def main():
    if sys.platform == 'win32':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.MoveWindow(hwnd, 20, 20, 900, 600, True)
        except Exception:
            pass

    print("=" * 75)
    print(" 🛠️  АВТОМАТИЧЕСКИЙ СБОРЩИК ТАБЛИЦ (5 КОЛОНОК) 🛠️ ")
    print("=" * 75)
    
    current_dir = os.getcwd()
    output_filename = "Проверенные.xlsx"
    
    print(f"\n📂 Сканирую папку: {current_dir}")
    
    all_excel_files = glob.glob(os.path.join(current_dir, "*.xls*"))

    input_files = [
        f for f in all_excel_files 
        if os.path.basename(f) != output_filename and not os.path.basename(f).startswith("~$")
    ]

    if not input_files:
        print("\n❌ ОШИБКА: В папке не найдено ни одной таблицы для слияния!")
        print(f"Положите файлы сотрудников рядом с этой программой.")
        input("\nНажмите Enter для выхода...")
        return

    print(f"🔎 Найдено таблиц для обработки: {len(input_files)}")
    for f in input_files:
        print(f"  - {os.path.basename(f)}")
    
    print("\nНачинаю обработку...\n" + "-"*40)

    TARGET_COLS = ['№ МК', 'Отделение', 'Сотрудник', 'Тип пациента', 'Дата окончания']
    all_dataframes = []
    success_count = 0

    for file_path in input_files:
        file_name = os.path.basename(file_path)
        print(f"📄 Читаю {file_name} ... ", end="")
        
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                print("⚠️  Пустой файл.")
                continue

            df.columns = df.columns.astype(str).str.strip()

            df = df.iloc[:-1]

            if '№ МК' in df.columns:
                df = df.dropna(subset=['№ МК'])
                df = df[~df['№ МК'].astype(str).str.contains('Количество', case=False, na=False)]

            missing_cols = [col for col in TARGET_COLS if col not in df.columns]
            if missing_cols:
                print("\n" + "❗" * 30)
                print(f"❌ ОШИБКА В ФАЙЛЕ: {file_name}")
                print(f"Отсутствуют колонки: {missing_cols}")
                print("Сделайте скриншот этого окна для Алексея!")
                print("❗" * 30 + "\n")
                continue

            df_clean = df[TARGET_COLS].copy()
            all_dataframes.append(df_clean)
            success_count += 1
            print(f"✅ Готово (строк: {len(df_clean)})")

        except Exception as e:
            error_msg = str(e)
            print("\n" + "❗" * 50)
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В ФАЙЛЕ: {file_name}")
            if "unpack requires a buffer of 4 bytes" in error_msg:
                print("Причина: Файл сохранен как HTML.")
                print("Решение: Пересохраните файл в Excel как 'Книга Excel (.xlsx)'.")
            else:
                print(traceback.format_exc())
            print("📸 СДЕЛАЙТЕ СКРИНШОТ!")
            print("❗" * 50 + "\n")

    print("-" * 40)
    
    if not all_dataframes:
        print("\n⚠️  Слияние не удалось. Итоговый файл не создан.")
        input("\nНажмите Enter для выхода...")
        return

    try:
        final_df = pd.concat(all_dataframes, ignore_index=True)
        final_df = final_df.fillna('')

        output_path = os.path.join(current_dir, output_filename)
        final_df.to_excel(output_path, index=False)
        
        print(f"\n🎉 УСПЕХ! Слияние завершено.")
        print(f"📈 Склеили файлов: {success_count} из {len(input_files)}")
        print(f"📊 Всего строк: {len(final_df)}")
        print(f"\n💾 Создан файл: {output_filename}")

    except PermissionError:
        print("\n" + "❗" * 50)
        print(f"❌ ОШИБКА: Файл '{output_filename}' открыт в Excel!")
        print("Закройте его и запустите программу снова.")
        print("❗" * 50)
    except Exception:
        print("\n" + "❗" * 50)
        print("❌ ОШИБКА ПРИ СОХРАНЕНИИ:")
        print(traceback.format_exc())
        print("❗" * 50)

    print("\n" + "=" * 75)
    input("Нажмите Enter, чтобы закрыть программу...")

if __name__ == "__main__":
    main()