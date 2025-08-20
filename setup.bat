@echo off
REM =====================================================
REM Полная установка и настройка HydroMeteo
REM =====================================================

setlocal enabledelayedexpansion
set PROJECT_ROOT=C:\Projects\GidroMeteo
cd /d %PROJECT_ROOT%

echo ============================================================
echo        УСТАНОВКА И НАСТРОЙКА HYDROMETEO
echo ============================================================
echo.

REM 1. Создание виртуального окружения Python
echo [1/6] Создание виртуального окружения Python...
if not exist "backend\venv" (
    python -m venv backend\venv
    echo   [+] Виртуальное окружение создано
) else (
    echo   [*] Виртуальное окружение уже существует
)

REM 2. Активация venv и установка зависимостей
echo.
echo [2/6] Установка Python зависимостей...
call backend\venv\Scripts\activate.bat

REM Обновляем pip
python -m pip install --upgrade pip --quiet

REM Устанавливаем зависимости
cd backend
pip install fastapi==0.112.2
pip install "uvicorn[standard]==0.30.6"
pip install httpx==0.27.0
pip install python-dotenv==1.0.1
pip install xarray==2024.06.0
pip install netCDF4==1.7.1
pip install numpy==2.0.1
pip install pandas==2.2.2
pip install copernicusmarine==1.3.2
pip install aiofiles==24.1.0

echo   [+] Python зависимости установлены
cd ..

REM 3. Создание .env файла
echo.
echo [3/6] Настройка конфигурации...
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env"
    echo   [+] Создан файл backend\.env
    echo.
    echo   ВАЖНО: Откройте backend\.env и заполните:
    echo   - COPERNICUSMARINE_USERNAME = ваш email
    echo   - COPERNICUSMARINE_PASSWORD = ваш пароль
) else (
    echo   [*] Файл .env уже существует
)

REM 4. Исправление HTML компонента (был только 1 строка)
echo.
echo [4/6] Восстановление HTML шаблона...
(
echo ^<div class="api-status"^> 
echo   ^<strong^>Статус API:^</strong^> 
echo   ^<span [class.status-online]="apiOnline" [class.status-offline]="!apiOnline" class="status-indicator"^>^</span^>
echo   ^<span class="api-status-text"^>{{apiStatusText}}^</span^>
echo ^</div^>
echo.
echo ^<div class="toolbar"^>
echo   ^<div class="block"^>
echo     ^<label^>Регион:^</label^>
echo     ^<select [(ngModel)]="regionId" (change)="applyRegion()"^>
echo       ^<option value="baltic"^>Балтийское море^</option^>
echo       ^<option value="north_sea"^>Северное море^</option^>
echo       ^<option value="mediterranean"^>Средиземное море^</option^>
echo       ^<option value="black_sea"^>Черное море^</option^>
echo       ^<option value="arctic"^>Арктика^</option^>
echo     ^</select^>
echo   ^</div^>
echo   
echo   ^<div class="block"^>
echo     ^<label^>Lat:^</label^>
echo     ^<input type="number" [(ngModel)]="lat" step="0.01" (change)="recenter()" /^>
echo     ^<label^>Lon:^</label^>
echo     ^<input type="number" [(ngModel)]="lon" step="0.01" (change)="recenter()" /^>
echo     ^<label^>Глубина:^</label^>
echo     ^<select [(ngModel)]="depth"^>
echo       ^<option value="surface"^>Поверхность^</option^>
echo       ^<option value="10m"^>10м^</option^>
echo       ^<option value="30m"^>30м^</option^>
echo     ^</select^>
echo   ^</div^>
echo   
echo   ^<div class="block actions"^>
echo     ^<button (click)="setMode('waves')"^>Волны^</button^>
echo     ^<button (click)="setMode('temperature')"^>Температура^</button^>
echo     ^<button (click)="setMode('ice')"^>Лёд^</button^>
echo     ^<button (click)="toggleCurrents()"^>{{currentsVisible ? 'Скрыть течения' : 'Показать течения'}}^</button^>
echo   ^</div^>
echo ^</div^>
echo.
echo ^<div id="map" class="map"^>^</div^>
echo.
echo ^<div class="panels"^>
echo   ^<div class="panel"^>
echo     ^<h3^>{{seriesTitle}}^</h3^>
echo     ^<div class="metrics"^>
echo       ^<div class="metric"^>^<span^>Lat:^</span^>{{lastPoint?.lat?.toFixed(4)}}^</div^>
echo       ^<div class="metric"^>^<span^>Lon:^</span^>{{lastPoint?.lon?.toFixed(4)}}^</div^>
echo       ^<div class="metric" *ngIf="lastUnit"^>^<span^>Ед. изм.:^</span^>{{lastUnit}}^</div^>
echo       ^<div class="metric" *ngIf="iceLast"^>^<span^>Лёд, %%:^</span^>{{iceLast.sic}}^</div^>
echo       ^<div class="metric" *ngIf="iceLast"^>^<span^>Толщина, м:^</span^>{{iceLast.sit}}^</div^>
echo     ^</div^>
echo     ^<div class="alerts" *ngIf="alerts.length"^>
echo       ^<div class="alert" *ngFor="let a of alerts"^>{{a}}^</div^>
echo     ^</div^>
echo     ^<canvas id="seriesChart"^>^</canvas^>
echo   ^</div^>
echo ^</div^>
) > "frontend\src\app\hydrometeo\hydrometeo-map.component.html"
echo   [+] HTML шаблон восстановлен

REM 5. Проверка установки Node.js модулей
echo.
echo [5/6] Проверка Node.js зависимостей...
cd frontend
if not exist "node_modules" (
    echo   [!] node_modules не найден. Выполните:
    echo       cd frontend ^&^& npm install
    echo       npm install ol chart.js
) else (
    if not exist "node_modules\ol" (
        npm install ol --save
        echo   [+] OpenLayers установлен
    )
    if not exist "node_modules\chart.js" (
        npm install chart.js --save
        echo   [+] Chart.js установлен
    )
)
cd ..

REM 6. Создание скрипта быстрого запуска
echo.
echo [6/6] Создание скрипта запуска...
(
echo @echo off
echo echo ============================================
echo echo       ЗАПУСК HYDROMETEO BACKEND
echo echo ============================================
echo cd /d C:\Projects\GidroMeteo\backend
echo call venv\Scripts\activate.bat
echo echo.
echo echo Проверка учетных данных CMDS...
echo python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); u=os.getenv('COPERNICUSMARINE_USERNAME'); p=os.getenv('COPERNICUSMARINE_PASSWORD'); print(f'Username: {u}'); print('Password: ***' if p else 'Password: НЕ ЗАДАН!')"
echo echo.
echo echo Запуск API на http://localhost:8000
echo echo Нажмите Ctrl+C для остановки
echo echo.
echo uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) > "start_backend.bat"
echo   [+] Создан start_backend.bat

echo.
echo ============================================================
echo              УСТАНОВКА ЗАВЕРШЕНА!
echo ============================================================
echo.
echo СЛЕДУЮЩИЕ ШАГИ:
echo ----------------
echo 1. Откройте backend\.env и добавьте учетные данные CMDS
echo.
echo 2. Запустите backend:
echo    start_backend.bat
echo.
echo 3. В новом терминале проверьте API:
echo    python test_api.py
echo.
echo 4. Для Angular frontend:
echo    cd frontend
echo    ng serve
echo.
echo 5. Откройте браузер: http://localhost:4200
echo.
pause