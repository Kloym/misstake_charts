FROM cdrx/pyinstaller-windows:python3

USER root

WORKDIR /app

# Копируем все файлы проекта в контейнер
COPY . .

# Обновляем pip
RUN python -m pip install --upgrade pip

# Устанавливаем PyInstaller (оставляю твои проверенные версии для совместимости с этим образом)
RUN python -m pip install "pyinstaller==5.13.2" "setuptools<65.0.0" "wheel" "pefile"

# Устанавливаем наши зависимости
RUN pip install -r requirements.txt

# Собираем .exe файл
RUN pyinstaller --onefile --clean \
    --name "Mscrit_Checker" \
    --hidden-import "pandas" \
    --hidden-import "openpyxl" \
    --hidden-import "xlrd" \
    app.py