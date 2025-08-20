Описание по коду, функциональности, отладке (Windows) и переносу (Linux), 
а также практические инструкции по зависимостям, установке и запуску. 
Формулировки увязаны с макетами интерфейса (демо и «Copernicus‑ориентированный»).

1) Краткая архитектура и состав функций

Backend (FastAPI):

Прокси WMTS: /wmts/capabilities, /wmts/tile — фоновые тайлы Copernicus на карту.

Доступ к данным через Copernicus Marine Toolbox (CLI):

/api/timeseries — тайм‑серии для волн (VHM0/VMDR/…)/физики (thetao/…)/льда (SIC/SIT).

/api/currents-grid — разреженный грид uo/vo для стрелок течений.

/api/ice-timeseries — интегрированная выдача SIC(%) и SIT(m), опционально дрейф (u/v).

Конфиг через .env: логин CMDS, ID датасетов Waves/Physics/Ice, базовый WMTS‑эндпойнт.

Frontend (Angular + OpenLayers + Chart.js):

Карта OL с фоновым WMTS (подключение через backend‑прокси).

Панели: «Волны», «Температура», «Лёд», «Течения». Графики Chart.js, карточки метрик, алерты.

Стрелки течений (VectorLayer) строятся из /api/currents-grid.

UI повторяет логику ваших HTML‑макетов (статус API, выбор региона/lat/lon/глубины, метрики и графики).

Утилита «ленты»: скрипт парсит публикацию вида --- FILE: path --- и раскладывает её по папкам (Windows/Linux), умеет EOL, ZIP и защиту от выхода за корень.

Практика публикации: соблюдение «правил 12.06.2025» — только полный исходный код, без заглушек, с контрольным отчётом.

2) Отладка в Windows
2.1. Подготовка среды

Python 3.10+, pip, Git (по желанию), Node 18+ для Angular.

Создать корневую папку проекта (если нет): C:\Projects\GidroMeteo.

Разложить файлы «лентой»:

Вариант А: через вашу утилиту — python tools\apply_published_code_GidroMeteo.py --input published_code.txt --root C:\Projects\GidroMeteo --eol crlf.

Вариант Б: руками/из архива в ту же структуру.

2.2. Backend

cd C:\Projects\GidroMeteo\backend

run_windows.bat:

создаст venv, поставит зависимости, попытается выполнить copernicusmarine login при наличии COPERNICUSMARINE_USERNAME/COPERNICUSMARINE_PASSWORD в .env, поднимет Uvicorn на http://localhost:8000.

В .env заполнить:

COPERNICUSMARINE_USERNAME=NNSmetanin@gmail.com

COPERNICUSMARINE_PASSWORD=<ваш_пароль_или_токен>

Проверка:

GET http://localhost:8000/health — видны ключи wmts, datasets.

GET /wmts/capabilities → XML (200).

Ошибки CLI (copernicusmarine не найден) и авторизации — возвращаются как понятный 5xx/4xx.

2.3. Frontend

В вашем Angular‑проекте: npm i ol chart.js

Импортировать модуль и вставить компонент <app-hydrometeo-map> на страницу.

(Опционально) указать адрес API:
в index.html добавить <script>window.__HYDROMETEO_API__='http://localhost:8000'</script>.

Открыть приложение:

Проверить индикатор статуса API, фоновый WMTS.

Клик по карте в режимах «Волны/Температура/Лёд» строит графики и карточки метрик.

Кнопка «Показать течения» — добавляет стрелки, реагируют на зум/панораму.

Визуальное соответствие «не хуже» HTML‑макетов: присутствуют метрики/алерты/графики/статусы (дизайн без «глянца», но структура и информативность сохранены).

3) Перенос и эксплуатация в Linux
3.1. Развёртывание

cd /opt/hydrometeo/backend && ./run_linux.sh

Создаст venv, установит зависимости, попытается copernicusmarine login (если есть учётка в .env), запустит Uvicorn.

Сервис/Unit: можно обернуть в systemd или Docker (по вашему регламенту).

Сетевые требования: исходящий доступ к WMTS и к API CMDS/Toolbox.

3.2. Кэш/cron

backend/cron/sync_baltic.sh — ежечасная выгрузка последних 48 ч по Балтике (waves/physics/ice) в NetCDF‑кэш; включить через crontab по примеру.

Логи перенаправлять в /var/log/hydrometeo_sync.log.

3.3. Отличия Windows↔Linux

Пути/регистр: в коде сведены к относительным (через .env/переменные).

Окончания строк: «лента» поддерживает --eol lf|crlf. На Linux используйте lf.

Локали/UTC: все запросы формируются в UTC; браузерные часовые пояса не влияют на API.

4) Зависимости и конфигурация
4.1. Backend (pip)

fastapi, uvicorn, httpx, python-dotenv

xarray, netCDF4, numpy, pandas

copernicusmarine (CLI + Python пакет) — необходим для subset.

4.2. Секреты/переменные

.env:

COPERNICUSMARINE_USERNAME, COPERNICUSMARINE_PASSWORD — логин CMDS.

CMDS_WMTS_BASE — базовый WMTS (оставьте по умолчанию).

CMDS_DATASET_WAV, CMDS_DATASET_PHY, CMDS_DATASET_ICE — ID наборов (меняются со временем — актуализировать через copernicusmarine describe).

CACHE_DIR — путь к кэшу NetCDF.

4.3. Frontend (npm)

ol, chart.js

Angular: достаточно CommonModule и FormsModule в модуле компонента.

5) Диагностика и типовые проблемы

WMTS 401/403/5xx: проверить креды CMDS в .env; /wmts/capabilities возвращает текст ошибки в detail.

Нет CLI: ошибка /api/timeseries → 500 с CLI 'copernicusmarine' not found — установить пакет в текущий venv.

Пустые массивы: выбранная точка вне покрываемой области или переменная отсутствует в датасете — проверить dataset/variable и bbox.

Производительность: ограничивайте окна времени, используйте «узкий бокс» вокруг точки; для фронтенда — WMTS как фон, а точные значения через API.

6) Соответствие макетам и выходные формы

Реализованы секции/метрики «Волны/Температура/Лёд/Течения», в т.ч. двойная ось для льда (SIC%/SIT m) и алерты — уровень информативности «не хуже» обоих HTML‑макетов.

Статус API/подключения и подсказки об ошибках — как в макетах (сообщения/индикаторы).

7) Рекомендации по отладке (Windows → Linux)

Smoke:

/health → 200; /wmts/capabilities → 200 (XML).

Клик по карте: графики строятся, карточки обновляются, стрелки появляются.

API‑контракты:

Сверить поля и единицы: VHM0 (m), thetao (°C), siconc (%), sithick (m).

Надёжность:

Принудительно «ломаем» креды WMTS — фронтенд должен показать оффлайн‑статус, backend вернуть 4xx/5xx без падения.

Временно переименовать copernicusmarine — получить 500 с понятным detail.

Perf:

10 параллельных /api/timeseries (1–2 точки) — отклик <5 c (95‑й перцентиль).

Cron:

Ручной запуск sync_baltic.sh — создать свежие baltic_*.nc в кэше.

8) Дорожная карта улучшений

Короткий горизонт (1–2 недели):

Кластер тайлов WMTS (несколько URL) и локальный кэш Capabilities.

Адаптер «быстрых точек» — замена subset на get/describe при известной сетке (минимизация IO).

Легенда/скейлбар для стрелок течений; вектор‑слой по скорости/направлению с цветовой шкалой.

Средний горизонт (1–2 месяца):

Docker‑сборки (backend+cron) + compose‑профили для dev/prod (Windows buildx).

QGIS‑плагин отображения тех же WMTS/векторов (для офлайн‑валидации оператором).

Сервис слоёв для «выходных форм» (экспорт PNG/SVG/CSV по клику, автоподпись координат/единиц).

Длинный горизонт:

Исторический архив (Zarr) и статистические профили (климатология/аномалии).

Ролевой доступ/аудит (Keycloak), журнал действий оператора.

Модуль прогнозирования дрейфа/зоны поиска (IAMSAR) с автоматическими входными полями из CMDS.

9) Инструкция по установке/запуску (пошагово)

Сборка проекта «лентой» (Windows):

python tools\apply_published_code_GidroMeteo.py --input published_code.txt --root C:\Projects\GidroMeteo --eol crlf
(утилита поддерживает BOM/CRLF/защиту от «вылазов», умеет собрать ZIP)

Backend:

cd C:\Projects\GidroMeteo\backend && run_windows.bat

В .env заполнить CMDS‑креды; перезапустить.

Проверить http://localhost:8000/health.

Frontend:

В вашем Angular: npm i ol chart.js; подключить модуль/компонент; при необходимости указать window.__HYDROMETEO_API__.

Открыть страницу — проверить фон/графики/алерты/стрелки.

Linux‑эксплуатация:

/opt/hydrometeo/backend/run_linux.sh; настроить cron/sync_baltic.sh.

Регламент кода:

Любые обновления публикуем «полными файлами», без заглушек, с коротким отчётом об изменениях (согласно правилам 12.06.2025).
