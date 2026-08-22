# Тренажёр вестибулярного аппарата

Десктопное приложение на **Python + PyQt5** с отслеживанием движений через веб-камеру. Результаты и пациенты хранятся в **локальном файле SQLite** — отдельный сервер баз данных не нужен.

**Нужно:** Python 3.10+, веб-камера. MySQL устанавливать не требуется.

---

## Быстрый старт (после клонирования)

Все команды — из папки проекта.

### Шаг 1. Перейти в папку проекта

```bash
cd ИМЯ_ПАПКИ_ПРОЕКТА
```

### Шаг 2. Виртуальное окружение

```bash
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### Шаг 3. Зависимости

```bash
pip install -r requirements.txt
```

### Шаг 4. Запуск

```bash
python run_app.py
```

База создаётся автоматически при первом запуске: копируется заводской файл `data/trainer.seed.db` (уже есть тестовый пациент **Тест Пациент**). Отдельная настройка БД не нужна.

---

### Всё одной цепочкой (Windows)

```bash
cd ИМЯ_ПАПКИ_ПРОЕКТА
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_app.py
```

---

## База данных

SQLite входит в Python. Рабочий файл:

| Режим | Где лежит рабочая БД |
|--------|----------------------|
| Запуск из исходников | `data/trainer.db` |
| Установленное приложение (exe) | `%APPDATA%\RehabTrainer\trainer.db` (Windows) |

Заводская копия `data/trainer.seed.db` входит в проект и в установку. Если рабочей базы ещё нет, она копируется из seed — с таблицами и тестовым пациентом. Уже существующий файл не перезаписывается.

Пересоздать заводской файл:

```bash
python storage.py
```

---

## Сборка exe и установщика (Windows)

Нужны Python 3.10 и [Inno Setup 6](https://jrsoftware.org/isinfo.php) (для `.exe`-установщика).

```powershell
venv\Scripts\activate
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

Скрипт делает:

1. PyInstaller → папка `dist\VestibularTrainer\` (готовое приложение)
2. Если установлен Inno Setup → `packaging\output\RehabTrainerSetup-1.0.0.exe`

Установщик кладёт программу в «Program Files», создаёт ярлык. База пациентов после установки живёт в `%APPDATA%\RehabTrainer\` и при удалении программы **не стирается**.

Запуск из исходников по-прежнему: `python run_app.py`.

---

## Структура проекта

```
├── run_app.py               # Точка входа
├── VestibularTrainer.spec   # Сборка PyInstaller
├── packaging\               # Иконка, Inno Setup, build.ps1
├── storage.py               # Локальная БД SQLite
├── data/trainer.seed.db     # Заводская база (тестовый пациент)
├── main.py                  # Главное окно
├── ex_2.py … ex_9.py        # Упражнения
├── analytics/               # Метрики и рекомендации
├── calibration/             # Калибровка камеры
└── requirements.txt         # Зависимости (PyQt5, OpenCV, MediaPipe, …)
```

---

## Возможные проблемы

| Проблема | Решение |
|----------|---------|
| `python` не найден | Установите Python 3.10+ с [python.org](https://www.python.org), включите **Add to PATH** |
| Камера не открывается | Закройте программы, которые используют камеру |
| Ошибки библиотек | `pip install -r requirements.txt` |
| Сбросить базу | Удалите рабочий файл (`data/trainer.db` или `%APPDATA%\RehabTrainer\trainer.db`) — при следующем запуске снова появится тестовый пациент |

---

## Автор

[Ваше ФИО, группа, университет]
