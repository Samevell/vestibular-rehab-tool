# Тренажёр вестибулярного аппарата

Десктопное приложение на **Python + PyQt5** с отслеживанием движений через веб-камеру. Результаты сохраняются в **MySQL**.

**Нужно:** Python 3.10+, MySQL, веб-камера.

---

## Быстрый старт (после клонирования)

Все команды — из папки проекта, в терминале.

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

### Шаг 4. База данных MySQL

**MySQL уже установлен** (обычный случай):

```bash
python setup_mysql.py --yes
```

Если пароль `root` не `pass`:

```bash
python setup_mysql.py --user root --password ВАШ_ПАРОЛЬ
```

Скрипт создаст базу `trainer`, таблицы и тестового пациента **Тест Пациент**.

**MySQL ещё нет** — терминал от имени администратора (Windows):

```bash
python install_mysql.py --install --setup --yes
```

### Шаг 5. Запуск

```bash
python run_app.py
```

Откроется окно тренажёра.

---

### Всё одной цепочкой (если MySQL уже есть, Windows)

```bash
cd ИМЯ_ПАПКИ_ПРОЕКТА
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python setup_mysql.py --yes
python run_app.py
```

---

## Подробнее про MySQL

| Скрипт | Зачем |
|--------|--------|
| `install_mysql.py` | Проверить / запустить / установить MySQL Server |
| `setup_mysql.py` | Создать базу, таблицы, пациента, `db_config.json` |

По умолчанию в проекте:

| Параметр | Значение |
|----------|----------|
| host | `127.0.0.1` |
| port | `3306` |
| database | `trainer` |
| user | `root` |
| password | `pass` |

Настройки хранятся в `db_config.json` (шаблон — `db_config.example.json`).

Полезные команды:

```bash
python install_mysql.py                  # только проверить / запустить MySQL
python setup_mysql.py                    # настройка с вопросами
python test_tables.py                    # проверка подключения к БД
```

Повторный запуск `setup_mysql.py` безопасен: существующие данные не удаляются.

---

## Структура проекта

```
├── run_app.py               # Запуск приложения
├── install_mysql.py         # Установка и запуск MySQL
├── setup_mysql.py           # Настройка базы и таблиц
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
| Ошибка подключения к MySQL | `python install_mysql.py`, проверьте пароль: `python setup_mysql.py --password ВАШ_ПАРОЛЬ` |
| `Access denied` | Неверный логин/пароль — укажите при `setup_mysql.py` |
| Камера не открывается | Закройте программы, которые используют камеру |
| Ошибки библиотек | `pip install -r requirements.txt` |

---

## Автор

[Ваше ФИО, группа, университет]
