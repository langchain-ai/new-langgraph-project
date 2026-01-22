# 5STARS Agent

Multi-agent система для автоматизированной работы с отзывами на Wildberries, построенная на LangGraph.

## 🏗️ Архитектура

```
START
  │
  └─► Master Agent (Оркестратор)
         │
         ├─► Memory Agent (Память)
         │       │
         │       ├─► Review Agent (Анализ)
         │       │       │
         │       │       └─► Dialog Agent
         │       │               │
         │       │               └─► Action Executor → END
         │       │
         │       └─► Dialog Agent (Прямой)
         │               │
         │               └─► Action Executor → END
         │
         └─► Escalation Handler (При необходимости)
                 │
                 └─► Action Executor → END
```

## 🤖 Агенты

| Агент | Роль | LLM |
|-------|------|-----|
| **Master Agent** | Оркестратор, определяет стратегию | Gemini Pro |
| **Memory Agent** | Управление контекстом и памятью | Gemini Flash |
| **Review Agent** | Анализ отзывов | Gemini Flash |
| **Dialog Agent** | Генерация ответов клиентам | Gemini Pro |
| **Action Executor** | Выполнение действий | - |
| **Escalation Handler** | Передача менеджеру | Gemini Flash |

## 📦 Установка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd 5stars-1

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

# Установить зависимости
pip install -e ".[dev]"

# Настроить переменные окружения
cp .env.example .env
# Заполнить .env своими ключами
```

## ⚙️ Конфигурация

Создайте `.env` файл на основе `.env.example`:

```env
# Обязательно
GOOGLE_API_KEY=your_google_api_key

# Опционально (для мониторинга)
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=5stars
```

## 🚀 Использование

### Как библиотека

```python
import asyncio
from agent import process_case, CaseStage

async def main():
    result = await process_case(
        case_id=1,
        review_text="Товар не соответствует описанию!",
        rating=2,
        chat_id="wb_chat_123",
        customer_name="Иван",
    )
    
    print(f"Ответ: {result['ai_response']}")
    print(f"Следующий этап: {result['next_stage']}")

asyncio.run(main())
```

### Как LangGraph сервер

```bash
# Запуск локального сервера
langgraph dev

# Сервер будет доступен на http://localhost:8123
```

### API вызовы

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8123")

# Создать thread
thread = await client.threads.create()

# Запустить агента
run = await client.runs.create(
    thread["thread_id"],
    "agent",
    input={
        "case_id": 1,
        "review_text": "Ужасное качество!",
        "rating": 1,
        "chat_id": "chat_123",
    }
)
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Только unit тесты
pytest tests/unit_tests/

# Только интеграционные тесты (требуют API ключи)
pytest tests/integration_tests/

# С покрытием
pytest --cov=agent
```

## 📁 Структура проекта

```
5stars-1/
├── src/
│   └── agent/
│       ├── __init__.py      # Публичный API
│       ├── graph.py         # Определение графа
│       ├── state.py         # TypedDict состояния
│       ├── nodes.py         # Функции узлов
│       ├── tools.py         # Инструменты агентов
│       ├── prompts.py       # Промпт-шаблоны
│       └── logging.py       # Логирование
├── tests/
│   ├── unit_tests/
│   └── integration_tests/
├── examples/
│   └── usage_example.py
├── langgraph.json           # Конфиг LangGraph
├── pyproject.toml           # Зависимости Python
└── README.md
```

## 🔧 Инструменты (Tools)

| Инструмент | Описание |
|------------|----------|
| `send_wb_message` | Отправка сообщения в чат WB |
| `send_telegram_notification` | Уведомление менеджера в Telegram |
| `escalate_to_manager` | Эскалация кейса |
| `get_customer_history` | История клиента |
| `get_product_info` | Информация о товаре |
| `search_similar_cases` | Поиск похожих кейсов |
| `analyze_sentiment` | Анализ тональности |
| `save_to_memory` | Сохранение в память |
| `search_memory` | Поиск в памяти |

## 📊 Мониторинг

Интеграция с LangSmith для отслеживания:
- Все вызовы LLM (input, output, tokens, стоимость)
- Граф выполнения
- State на каждом шаге
- Ошибки и время выполнения

Dashboard: https://smith.langchain.com/

## 🔄 Этапы обработки (Stages)

1. **RECEIVED** - Новый отзыв получен
2. **ANALYSIS** - Анализ отзыва
3. **COMPENSATION_OFFER** - Предложение компенсации
4. **WAITING_RESPONSE** - Ожидание ответа
5. **WAITING_FIX** - Ожидание исправления отзыва
6. **ESCALATION** - Передано менеджеру
7. **RESOLVED** - Решено
8. **CLOSED** - Закрыто

## 🔗 Ссылки

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith](https://smith.langchain.com/)
- [LangChain](https://python.langchain.com/)

## 📝 Лицензия

MIT
