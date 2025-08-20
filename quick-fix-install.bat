@echo off
REM =====================================================
REM Исправление установки для Python 3.13
REM =====================================================

echo ============================================================
echo     БЫСТРОЕ ИСПРАВЛЕНИЕ УСТАНОВКИ HYDROMETEO
echo ============================================================
echo.

cd /d C:\Projects\GidroMeteo\backend

REM Активируем виртуальное окружение
call venv\Scripts\activate.bat

echo [1/5] Обновление pip и установка wheel...
python -m pip install --upgrade pip wheel setuptools

echo.
echo [2/5] Установка предкомпилированных версий пакетов...
echo.

REM Используем предкомпилированные wheel файлы для Windows
echo Установка numpy (предкомпилированная версия)...
pip install numpy

echo Установка pandas (предкомпилированная версия)...  
pip install pandas

echo Установка netCDF4 через conda-forge wheel...
pip install netCDF4 --no-build-isolation

echo Установка h5netcdf как альтернативы...
pip install h5netcdf

echo Установка copernicusmarine (последняя версия для Python 3.13)...
pip install copernicusmarine

echo.
echo [3/5] Проверка установленных пакетов...
python -c "import fastapi; print('✓ FastAPI:', fastapi.__version__)"
python -c "import uvicorn; print('✓ Uvicorn установлен')"
python -c "import httpx; print('✓ HTTPX:', httpx.__version__)"
python -c "import xarray; print('✓ XArray:', xarray.__version__)"
python -c "import numpy; print('✓ NumPy:', numpy.__version__)"
python -c "import pandas; print('✓ Pandas:', pandas.__version__)"

echo.
echo [4/5] Исправление HTML шаблона...
cd ..

REM Создаем правильный HTML файл
(
echo ^<!-- HydroMeteo Map Component Template --^>
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
echo.  
echo   ^<div class="block"^>
echo     ^<label^>Lat:^</label^>
echo     ^<input type="number" [(ngModel)]="lat" step="0.01" (change)="recenter()" /^>
echo     ^<label^>Lon:^</label^>
echo     ^<input type="number" [(ngModel)]="lon" step="0.01" (change)="recenter()" /^>
echo   ^</div^>
echo.  
echo   ^<div class="block actions"^>
echo     ^<button (click)="setMode('waves')"^>Волны^</button^>
echo     ^<button (click)="setMode('temperature')"^>Температура^</button^>
echo     ^<button (click)="setMode('ice')"^>Лёд^</button^>
echo     ^<button (click)="toggleCurrents()"^>Течения^</button^>
echo   ^</div^>
echo ^</div^>
echo.
echo ^<div id="map" class="map"^>^</div^>
echo.
echo ^<div class="panels"^>
echo   ^<div class="panel"^>
echo     ^<h3^>{{seriesTitle}}^</h3^>
echo     ^<canvas id="seriesChart"^>^</canvas^>
echo   ^</div^>
echo ^</div^>
) > frontend\src\app\hydrometeo\hydrometeo-map.component.html

echo [+] HTML шаблон восстановлен

echo.
echo [5/5] Создание упрощенного main.py для тестирования...

cd backend\app

REM Создаем минимальный рабочий main.py
(
echo # -*- coding: utf-8 -*-
echo """
echo Упрощенная версия HydroMeteo API для тестирования
echo """
echo.
echo import os
echo import json
echo from datetime import datetime, timedelta
echo from typing import Optional, List, Dict, Any
echo.
echo from fastapi import FastAPI, HTTPException
echo from fastapi.middleware.cors import CORSMiddleware
echo from fastapi.responses import JSONResponse
echo from pydantic import BaseModel, Field
echo from dotenv import load_dotenv
echo.
echo # Загрузка конфигурации
echo load_dotenv^(^)
echo.
echo # Конфигурация
echo API_HOST = os.getenv^("API_HOST", "0.0.0.0"^)
echo API_PORT = int^(os.getenv^("API_PORT", "8000"^)^)
echo CM_USER = os.getenv^("COPERNICUSMARINE_USERNAME"^)
echo CM_PASS = os.getenv^("COPERNICUSMARINE_PASSWORD"^)
echo.
echo # FastAPI приложение
echo app = FastAPI^(
echo     title="HydroMeteo CMDS API",
echo     version="1.0.0-simplified",
echo     description="Упрощенная версия API для тестирования"
echo ^)
echo.
echo # CORS
echo app.add_middleware^(
echo     CORSMiddleware,
echo     allow_origins=["*"],
echo     allow_credentials=True,
echo     allow_methods=["*"],
echo     allow_headers=["*"],
echo ^)
echo.
echo # Модели данных
echo class TimeSeriesRequest^(BaseModel^):
echo     dataset: str
echo     variable: str
echo     lat: float = Field^(..., ge=-90, le=90^)
echo     lon: float = Field^(..., ge=-180, le=180^)
echo     start_utc: Optional[str] = None
echo     end_utc: Optional[str] = None
echo.
echo class TimeSeriesResponse^(BaseModel^):
echo     times_utc: List[str]
echo     values: List[float]
echo     unit: Optional[str] = None
echo     meta: Dict[str, Any] = {}
echo.
echo # Endpoints
echo @app.get^("/health"^)
echo async def health^(^):
echo     """Проверка состояния системы"""
echo     return JSONResponse^(content={
echo         "status": "online",
echo         "version": "1.0.0-simplified",
echo         "timestamp": datetime.utcnow^(^).isoformat^(^) + "Z",
echo         "cm_user": bool^(CM_USER^),
echo         "cm_pass_set": bool^(CM_PASS^),
echo         "message": "Упрощенная версия для тестирования"
echo     }^)
echo.
echo @app.get^("/"^)
echo async def root^(^):
echo     """Корневой endpoint"""
echo     return {
echo         "name": "HydroMeteo API",
echo         "version": "1.0.0-simplified",
echo         "endpoints": ["/health", "/api/test-timeseries"]
echo     }
echo.
echo @app.post^("/api/timeseries", response_model=TimeSeriesResponse^)
echo async def timeseries^(req: TimeSeriesRequest^):
echo     """Тестовый endpoint для временных рядов"""
echo     # Генерируем тестовые данные
echo     import random
echo     
echo     now = datetime.utcnow^(^)
echo     times = []
echo     values = []
echo     
echo     for i in range^(24^):
echo         t = now - timedelta^(hours=23-i^)
echo         times.append^(t.isoformat^(^) + "Z"^)
echo         values.append^(random.uniform^(0.5, 3.5^)^)
echo     
echo     return TimeSeriesResponse^(
echo         times_utc=times,
echo         values=values,
echo         unit="m" if req.variable == "VHM0" else "°C",
echo         meta={
echo             "dataset": req.dataset,
echo             "variable": req.variable,
echo             "lat": req.lat,
echo             "lon": req.lon,
echo             "note": "Тестовые данные - CMDS не подключен"
echo         }
echo     ^)
echo.
echo if __name__ == "__main__":
echo     import uvicorn
echo     uvicorn.run^(app, host=API_HOST, port=API_PORT^)
) > main_simple.py

echo [+] Создан упрощенный main_simple.py

cd ..\..

echo.
echo ============================================================
echo              УСТАНОВКА ИСПРАВЛЕНА!
echo ============================================================
echo.
echo ЗАПУСК ТЕСТОВОГО СЕРВЕРА:
echo --------------------------
echo cd backend
echo venv\Scripts\activate
echo python app\main_simple.py
echo.
echo Или используйте готовый скрипт:
echo start_test_server.bat
echo.
pause