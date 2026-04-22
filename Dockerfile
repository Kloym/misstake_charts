FROM cdrx/pyinstaller-windows:python3

USER root

WORKDIR /app

# Копируем абсолютно ВСЕ файлы проекта (app.py, utils.py, requirements.txt и т.д.)
COPY . .

# Обновляем pip
RUN python -m pip install --upgrade pip

# Устанавливаем PyInstaller (оставляем твои проверенные версии)
RUN python -m pip install "pyinstaller==5.13.2" "setuptools<65.0.0" "wheel" "pefile"

# Устанавливаем зависимости из requirements.txt
RUN pip install -r requirements.txt

# Собираем .exe файл
RUN pyinstaller --onefile --clean \
    --name "Mscrit_Checker" \
    --hidden-import "pandas" \
    --hidden-import "openpyxl" \
    --hidden-import "xlrd" \
    app.py