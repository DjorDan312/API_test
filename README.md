# API организационной структуры

REST API для управления подразделениями (дерево) и сотрудниками. Реализовано на **FastAPI**, **SQLAlchemy**, **PostgreSQL**, с миграциями **Alembic** и запуском в **Docker**.

## Запуск через Docker (рекомендуется)

```bash
docker-compose up --build
```

- **API**: http://localhost:8001  
- **OpenAPI (Swagger)**: http://localhost:8001/docs  
- **ReDoc**: http://localhost:8001/redoc  

Порт API по умолчанию — **8001** (если 8000 занят). Изменить можно в `docker-compose.yml` (секция `api.ports`).

PostgreSQL доступен на порту `5432` (логин/пароль: `postgres/postgres`, БД: `org_api`). При старте контейнера `api` автоматически выполняются миграции Alembic.

## Запуск без Docker (локально)

1. Установить и запустить PostgreSQL, создать БД `org_api`.
2. Создать виртуальное окружение и установить зависимости:

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

3. Задать переменную окружения (или создать `.env`):

```bash
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/org_api
```

4. Применить миграции и запустить приложение:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Тесты

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Тесты используют SQLite in-memory (PostgreSQL не обязателен).

## Модели и API

### Модели

- **Department** — подразделение: `id`, `name`, `parent_id` (FK на себя, дерево), `created_at`.
- **Employee** — сотрудник: `id`, `department_id`, `full_name`, `position`, `hired_at` (опционально), `created_at`.

Связи: у подразделения — список сотрудников и дочерних подразделений; у сотрудника — одно подразделение.

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/departments/` | Создать подразделение (`name`, опционально `parent_id`). |
| POST | `/departments/{id}/employees/` | Создать сотрудника в подразделении (`full_name`, `position`, опционально `hired_at`). |
| GET | `/departments/{id}` | Получить подразделение с сотрудниками и поддеревом. Query: `depth` (1–5), `include_employees`, `sort_employees` (`created_at` / `full_name`). |
| PATCH | `/departments/{id}` | Обновить подразделение (`name`, `parent_id` — опционально). |
| DELETE | `/departments/{id}` | Удалить подразделение. Query: `mode=cascade` (удалить с сотрудниками и потомками) или `mode=reassign` (перевести сотрудников и дочерние подразделения в `reassign_to_department_id`). |

### Ограничения и валидация

- Имена подразделений и сотрудников: не пустые, длина 1–200, пробелы по краям обрезаются.
- В рамках одного родителя имена подразделений уникальны.
- Нельзя сделать подразделение родителем самого себя или перенести его в своё поддерево (защита от циклов).
- При удалении в режиме `cascade` удаление каскадное (БД/ORM); в режиме `reassign` сотрудники и дочерние подразделения переназначаются на указанное подразделение.

## Структура проекта

```
├── app/
│   ├── api/           # Роуты FastAPI
│   ├── db/            # Сессия БД, Base
│   ├── models/        # Модели SQLAlchemy (Department, Employee)
│   ├── schemas/       # Схемы Pydantic (запрос/ответ)
│   ├── services/      # Бизнес-логика (создание, обновление, удаление, дерево)
│   ├── config.py
│   ├── logging_config.py
│   └── main.py
├── alembic/           # Миграции
├── tests/             # Pytest-тесты
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Технологии

- **FastAPI** — веб-фреймворк и OpenAPI
- **SQLAlchemy 2** — ORM
- **PostgreSQL** — БД (в тестах — SQLite)
- **Alembic** — миграции
- **Pydantic** — валидация и сериализация
- **Docker / docker-compose** — контейнеризация
