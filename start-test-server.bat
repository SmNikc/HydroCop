@echo off
REM Запуск тестового сервера HydroMeteo

echo ============================================
echo      ЗАПУСК ТЕСТОВОГО СЕРВЕРА HYDROMETEO
echo ============================================
echo.

cd /d C:\Projects\GidroMeteo\backend

REM Активация виртуального окружения
call venv\Scripts\activate.bat

echo Проверка установленных пакетов...
python -c "import fastapi, uvicorn, httpx; print('OK: Основные пакеты установлены')" 2>nul
if errorlevel 1 (
    echo.
    echo [!] Не все пакеты установлены. Устанавливаем...
    pip install fastapi uvicorn httpx python-dotenv pydantic
)

echo.
echo Проверка учетных данных CMDS...
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); u=os.getenv('COPERNICUSMARINE_USERNAME'); print(f'Username: {u if u else \"НЕ ЗАДАН\"}')"

echo.
echo ============================================
echo Запуск API на http://localhost:8000
echo.
echo Endpoints:
echo   http://localhost:8000/         - главная
echo   http://localhost:8000/health   - статус
echo   http://localhost:8000/docs     - документация
echo.
echo Нажмите Ctrl+C для остановки
echo ============================================
echo.

REM Запускаем упрощенную версию если она есть
if exist app\main_simple.py (
    echo Запуск упрощенной версии...
    python app\main_simple.py
) else (
    echo Запуск основной версии...
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)

pause