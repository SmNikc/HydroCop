#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тестовый скрипт для проверки работы HydroMeteo API"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_health():
    """Тест health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Health check: {data.get('status')}")
    return data

def test_timeseries():
    """Тест получения временных рядов"""
    payload = {
        "dataset": "waves",
        "variable": "VHM0",
        "lat": 59.5,
        "lon": 24.8,
        "start_utc": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
        "end_utc": datetime.utcnow().isoformat() + "Z"
    }
    
    response = requests.post(f"{BASE_URL}/api/timeseries", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Timeseries: получено {len(data.get('values', []))} точек")
        if data.get('values'):
            print(f"   Последнее значение: {data['values'][-1]} {data.get('unit')}")
    else:
        print(f"❌ Timeseries failed: {response.status_code}")
        print(f"   {response.text}")
    
def test_ice():
    """Тест данных по льду"""
    payload = {
        "lat": 65.0,  # Северная часть Балтики
        "lon": 23.0,
        "start_utc": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
        "end_utc": datetime.utcnow().isoformat() + "Z"
    }
    
    response = requests.post(f"{BASE_URL}/api/ice-timeseries", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Ice data: SIC={len(data.get('siconc', []))} точек, SIT={len(data.get('sithick', []))} точек")
    else:
        print(f"❌ Ice data failed: {response.status_code}")

if __name__ == "__main__":
    print("ТЕСТИРОВАНИЕ HYDROMETEO API")
    print("=" * 40)
    
    try:
        # Проверка доступности
        health_data = test_health()
        
        # Если API доступен и есть учетные данные
        if health_data.get("cm_user"):
            print("\n📊 Тестирование с реальными данными...")
            test_timeseries()
            test_ice()
        else:
            print("\n⚠️ Учетные данные CMDS не настроены")
            print("   Заполните COPERNICUSMARINE_USERNAME и COPERNICUSMARINE_PASSWORD в backend/.env")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к API")
        print("   Убедитесь, что backend запущен: cd backend && run_windows.bat")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
