import pandas as pd
import os
import time
import tkinter as tk
from tkinter import filedialog
import traceback
import ctypes
import sys

def main():
    # --- МАГИЯ 1: СДВИГАЕМ ЧЕРНОЕ ОКНО КОНСОЛИ ВЛЕВО ---
    if sys.platform == 'win32':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.MoveWindow(hwnd, 20, 20, 800, 600, True)
        except Exception:
            pass

    root = tk.Tk()
    root.geometry('0x0-50+50')
    root.attributes('-alpha', 0.0) 
    root.attributes('-topmost', True)

    print("=" * 70)
    print(" 🛠️ ПРОГРАММА ДЛЯ СЛИЯНИЯ ТАБЛИЦ (ПРОВЕРЕННЫЕ КАРТЫ) 🛠️ ")
    print("=" * 70)
    print("\nШаг 1: Окно выбора файлов открылось в правой части экрана.")
    print("Пожалуйста, выделите все таблицы от сотрудников, которые нужно объединить.")
    print("(Можно выделить сразу несколько файлов мышкой или с зажатой клавишей Ctrl)\n")
    
    time.sleep(1.5)
    
    file_paths = filedialog.askopenfilenames(
        parent=root,
        title="Выберите таблицы для слияния",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    
    root.destroy()

    if not file_paths:
        print("❌ Вы не выбрали ни одного файла. Программа завершает работу.")
        input("\nНажмите Enter для выхода...")
        return

    print(f"✅ Выбрано файлов: {len(file_paths)}\n")
    print("Начинаю обработку и слияние...\n")

    TARGET_COLS = ['№ МК', 'Отделение', 'Сотрудник', 'Тип пациента']
    
    all_dataframes = []
    success_count = 0

    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        print(f"Обработка файла: {file_name} ... ", end="")
        
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                print("⚠️ Файл пустой (пропущен).")
                continue

            df.columns = df.columns.astype(str).str.strip()

            df = df.iloc[:-1]

            if '№ МК' in df.columns:
                df = df.dropna(subset=['№ МК'])
                df = df[~df['№ МК'].astype(str).str.contains('Количество', case=False, na=False)]

            missing_cols = [col for col in TARGET_COLS if col not in df.columns]
            if missing_cols:
                print("\n" + "❗" * 50)
                print(f"❌ ОШИБКА В ФАЙЛЕ: {file_name}")
                print(f"ПРИЧИНА: В таблице нет нужных столбцов: {missing_cols}")
                print("📸 ПОЖАЛУЙСТА, СДЕЛАЙТЕ СКРИНШОТ И ОТПРАВЬТЕ РАЗРАБОТЧИКУ 📸")
                print("❗" * 50 + "\n")
                continue

            df_clean = df[TARGET_COLS].copy()
            
            all_dataframes.append(df_clean)
            success_count += 1
            print(f"Готово! (Строк: {len(df_clean)})")

        except Exception as e:
            error_msg = str(e)
            print("\n\n" + "❗" * 70)
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЧТЕНИИ ФАЙЛА: {file_name}")
            
            if "unpack requires a buffer of 4 bytes" in error_msg:
                print("ПРИЧИНА: Файл сохранен некорректно (как веб-страница).")
                print("РЕШЕНИЕ: Откройте его вручную в Excel, нажмите 'Сохранить как' -> 'Книга Excel (*.xlsx)'.")
            else:
                print("ТЕХНИЧЕСКИЕ ДЕТАЛИ ДЛЯ РАЗРАБОТЧИКА:")
                print(traceback.format_exc())
            
            print("📸 ПОЖАЛУЙСТА, СДЕЛАЙТЕ СКРИНШОТ ЭТОГО ЭКРАНА И ОТПРАВЬТЕ РАЗРАБОТЧИКУ 📸")
            print("❗" * 70 + "\n")

    print("\n" + "=" * 70)
    
    if not all_dataframes:
        print("⚠️ Не удалось успешно обработать ни одного файла. Слияние отменено.")
        input("\nНажмите Enter для выхода...")
        return

    try:
        final_df = pd.concat(all_dataframes, ignore_index=True)
        final_df = final_df.fillna('')

        output_filename = "Проверенные.xlsx"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        final_df.to_excel(output_path, index=False)
        
        print("🎉 СЛИЯНИЕ УСПЕШНО ЗАВЕРШЕНО! 🎉")
        print(f"Всего обработано файлов без ошибок: {success_count} из {len(file_paths)}")
        print(f"Общее количество записей: {len(final_df)}")
        print(f"\n📁 Итоговый файл сохранен рядом с программой: {output_filename}")

    except PermissionError:
        print("\n" + "❗" * 70)
        print("❌ ОШИБКА СОХРАНЕНИЯ: НЕТ ДОСТУПА К ФАЙЛУ!")
        print(f"ПРИЧИНА: Файл '{output_filename}' сейчас открыт в Excel или другой программе.")
        print("РЕШЕНИЕ: Закройте этот файл и запустите программу слияния заново.")
        print("❗" * 70 + "\n")
    except Exception as e:
        print("\n" + "❗" * 70)
        print("❌ НЕИЗВЕСТНАЯ ОШИБКА ПРИ СОХРАНЕНИИ ИТОГОВОГО ФАЙЛА:")
        print(traceback.format_exc())
        print("📸 ПОЖАЛУЙСТА, СДЕЛАЙТЕ СКРИНШОТ И ОТПРАВЬТЕ РАЗРАБОТЧИКУ 📸")
        print("❗" * 70 + "\n")

    print("=" * 70)
    input("\nНажмите Enter, чтобы закрыть программу...")

if __name__ == "__main__":
    main()