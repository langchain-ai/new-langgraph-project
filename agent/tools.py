"""Tools for 5STARS agent.

Defines all tools that the agent can use to interact with external systems.
Enhanced with error handling, retry logic, and HITL support.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

from langchain_core.tools import tool

logger = logging.getLogger("5stars.tools")


# =============================================================================
# Configuration
# =============================================================================

WB_API_URL = os.getenv("WB_API_URL", "https://feedbacks-api.wildberries.ru/api/v1")
WB_API_TOKEN = os.getenv("WB_API_TOKEN", "")


# =============================================================================
# Error Handling Utilities
# =============================================================================


class ToolError(Exception):
    """Custom exception for tool errors."""
    
    def __init__(self, message: str, recoverable: bool = True, details: dict = None):
        super().__init__(message)
        self.recoverable = recoverable
        self.details = details or {}


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator for consistent error handling in tools."""
    
    @wraps(func)
    def wrapper(*args, **kwargs) -> dict:
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            logger.error(f"[TOOL ERROR] {func.__name__}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recoverable": e.recoverable,
                "details": e.details,
                "suggestion": "Попробуйте изменить параметры или выбрать другой подход",
            }
        except Exception as e:
            logger.exception(f"[TOOL UNEXPECTED ERROR] {func.__name__}: {e}")
            return {
                "status": "error",
                "error": f"Неожиданная ошибка: {str(e)}",
                "recoverable": False,
                "suggestion": "Рассмотрите эскалацию на менеджера",
            }
    
    return wrapper


def validate_message_length(message: str, max_length: int, field_name: str = "message") -> str:
    """Validate and truncate message if needed."""
    if not message or not message.strip():
        raise ToolError(f"Поле {field_name} не может быть пустым", recoverable=True)
    
    message = message.strip()
    if len(message) > max_length:
        logger.warning(f"Message truncated from {len(message)} to {max_length} chars")
        return message[:max_length - 3] + "..."
    return message


# =============================================================================
# Tool 1: Send Chat Message
# =============================================================================


@tool
@handle_tool_errors
def send_chat_message(
    chat_id: str,
    message: str,
) -> dict:
    """Отправить личное сообщение клиенту в чате Wildberries.
    
    Используй этот инструмент когда нужно:
    - Уточнить детали проблемы у клиента
    - Предложить решение или компенсацию приватно
    - Продолжить диалог с клиентом
    
    ВАЖНО: Это приватное сообщение, видимое только клиенту.
    
    Args:
        chat_id: ID чата в Wildberries
        message: Текст сообщения (макс. 1000 символов)

    Returns:
        dict с статусом отправки
    """
    # Validation
    if not chat_id:
        raise ToolError("chat_id обязателен", recoverable=True)
    
    message = validate_message_length(message, 1000)
    
    logger.info(f"[TOOL] send_chat_message to chat {chat_id}: {message[:50]}...")

    # TODO: Implement actual WB API call
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"{WB_API_URL}/chats/{chat_id}/messages",
    #         json={"message": message},
    #         headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    #     )
    #     response.raise_for_status()
    
    return {
        "status": "success",
        "message": "Сообщение отправлено в чат",
        "chat_id": chat_id,
        "message_preview": message[:100],
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Tool 2: Send Public Review Reply
# =============================================================================


@tool
@handle_tool_errors
def send_review_reply(
    review_id: str,
    reply_text: str,
) -> dict:
    """Отправить публичный ответ на отзыв Wildberries.
    
    Используй этот инструмент когда нужно:
    - Публично ответить на отзыв клиента
    - Показать другим покупателям, что продавец заботится о клиентах
    - Дать официальный ответ от имени магазина
    
    ВАЖНО: 
    - Ответ будет виден ВСЕМ покупателям!
    - Максимум 300 символов!
    - НЕ указывай конкретные суммы компенсаций публично
    - НЕ раскрывай личные данные клиента
    
    Args:
        review_id: ID отзыва в Wildberries
        reply_text: Текст публичного ответа (макс. 300 символов)

    Returns:
        dict с статусом отправки
    """
    # Validation
    if not review_id:
        raise ToolError("review_id обязателен", recoverable=True)
    
    reply_text = validate_message_length(reply_text, 300, "reply_text")
    
    # Check for prohibited content
    prohibited_patterns = ["₽", "руб", "компенсац", "возврат средств"]
    for pattern in prohibited_patterns:
        if pattern.lower() in reply_text.lower():
            raise ToolError(
                f"Публичный ответ не должен содержать '{pattern}'. "
                "Суммы и компенсации обсуждаются только в личном чате.",
                recoverable=True
            )
        
    logger.info(f"[TOOL] send_review_reply to review {review_id}: {reply_text[:50]}...")

    # TODO: Implement actual WB API call
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"{WB_API_URL}/feedbacks/{review_id}/reply",
    #         json={"text": reply_text},
    #         headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    #     )
    #     response.raise_for_status()
    
    return {
        "status": "success",
        "message": "✅ Публичный ответ на отзыв отправлен",
        "action_type": "review_reply",
        "review_id": review_id,
        "reply_text": reply_text,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Tool 3: Call the Human (передача кейса человеку)
# =============================================================================


@tool
@handle_tool_errors
def call_the_human(
    case_id: str,
    reason: str,
    action_required: str = "review",
    compensation_amount: int = 0,
    summary: str = "",
) -> dict:
    """Передать кейс человеку-менеджеру для дальнейшей обработки.
    
    Используй этот инструмент когда:
    - Клиент согласился на компенсацию → менеджер выплатит и закроет кейс
    - Ситуация слишком сложная для автоматического решения
    - Клиент требует связи с руководством/живым человеком
    - Есть юридические риски или угрозы
    - Клиент недоволен после нескольких попыток решения
    - Требуется нестандартное решение
    
    Args:
        case_id: ID кейса
        reason: Причина передачи человеку (кратко, но информативно)
        action_required: Требуемое действие - "compensation" (выплата), "review" (анализ), "escalation" (эскалация руководству)
        compensation_amount: Сумма компенсации в рублях (если action_required="compensation")
        summary: Краткое резюме ситуации и рекомендации для менеджера

    Returns:
        dict с информацией о передаче кейса
    """
    # Validation
    if not case_id:
        raise ToolError("case_id обязателен", recoverable=True)
    
    if not reason or len(reason.strip()) < 10:
        raise ToolError(
            "Укажите подробную причину передачи (минимум 10 символов)",
            recoverable=True
        )
    
    valid_actions = ["compensation", "review", "escalation"]
    if action_required not in valid_actions:
        logger.warning(f"Invalid action_required '{action_required}', defaulting to 'review'")
        action_required = "review"
    
    if action_required == "compensation" and compensation_amount <= 0:
        raise ToolError(
            "Укажите сумму компенсации (compensation_amount > 0)",
            recoverable=True
        )
    
    logger.info(f"[TOOL] CALL_THE_HUMAN case_id={case_id}, action={action_required}, reason={reason}")

    # Determine priority based on action
    priority_map = {
        "escalation": "high",
        "compensation": "normal",
        "review": "normal",
    }

    return {
        "status": "success",
        "message": f"✅ Кейс передан менеджеру. Действие: {action_required}",
        "action_type": "human_handoff",
        "case_id": case_id,
        "reason": reason,
        "action_required": action_required,
        "compensation_amount": compensation_amount if action_required == "compensation" else 0,
        "summary": summary or reason,
        "priority": priority_map.get(action_required, "normal"),
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Tool 4: Search Similar Cases
# =============================================================================


@tool
@handle_tool_errors
def search_similar_cases(
    issue_description: str,
    rating: Optional[int] = None,
    limit: int = 3,
) -> dict:
    """Найти похожие кейсы из истории для анализа лучших практик.
    
    Используй этот инструмент когда:
    - Нужно понять, как решались похожие проблемы ранее
    - Ищешь оптимальную стратегию ответа
    - Хочешь узнать типичную компенсацию для такого типа проблем
    - Сомневаешься в правильном подходе
    
    Args:
        issue_description: Описание проблемы для поиска (чем подробнее, тем лучше)
        rating: Фильтр по рейтингу отзыва (1-5), опционально
        limit: Максимальное количество результатов (1-10)

    Returns:
        dict со списком похожих кейсов и рекомендациями
    """
    # Validation
    if not issue_description or len(issue_description.strip()) < 5:
        raise ToolError(
            "Опишите проблему подробнее (минимум 5 символов)",
            recoverable=True
        )
    
    if rating is not None and not (1 <= rating <= 5):
        logger.warning(f"Invalid rating {rating}, ignoring filter")
        rating = None
    
    limit = max(1, min(10, limit))
    
    logger.info(f"[TOOL] search_similar_cases: {issue_description[:50]}...")

    # TODO: Implement actual vector search in Milvus/PostgreSQL
    # from langchain_openai import OpenAIEmbeddings
    # embeddings = OpenAIEmbeddings()
    # query_embedding = embeddings.embed_query(issue_description)
    # results = vector_store.similarity_search(query_embedding, k=limit)
    
    # Placeholder response with realistic data structure
    similar_cases = [
        {
            "case_id": "case_2024_001",
            "similarity_score": 0.92,
            "issue": "Товар пришёл с браком (царапины на корпусе)",
            "rating": 2,
            "resolution": "Предложена замена товара или возврат средств",
            "response_template": "Добрый день! Приносим извинения за доставленные неудобства. Мы готовы заменить товар или оформить возврат.",
            "compensation": 1000,
            "outcome": "Клиент выбрал замену, изменил оценку на 5★",
            "success": True,
            "days_to_resolve": 2,
        },
        {
            "case_id": "case_2024_002", 
            "similarity_score": 0.85,
            "issue": "Долгая доставка, товар шёл 2 недели",
            "rating": 3,
            "resolution": "Извинения + промокод на следующую покупку",
            "response_template": "Здравствуйте! Благодарим за обратную связь. Сроки доставки зависят от логистики, но мы передали информацию для улучшения.",
            "compensation": 200,
            "outcome": "Клиент удовлетворён, оценку не изменил",
            "success": True,
            "days_to_resolve": 1,
        },
        {
            "case_id": "case_2024_003",
            "similarity_score": 0.78,
            "issue": "Не соответствует описанию (цвет отличается)",
            "rating": 2,
            "resolution": "Возврат средств + извинения",
            "response_template": "Добрый день! Сожалеем, что товар не оправдал ожиданий. Оформим возврат и компенсируем неудобства.",
            "compensation": 300,
            "outcome": "Клиент оформил возврат, оценку изменил на 4★",
            "success": True,
            "days_to_resolve": 3,
        },
    ]
    
    # Filter by rating if specified
    if rating is not None:
        similar_cases = [c for c in similar_cases if c["rating"] == rating]
    
    # Calculate recommendation based on similar cases
    if similar_cases:
        avg_compensation = sum(c["compensation"] for c in similar_cases) / len(similar_cases)
        success_rate = sum(1 for c in similar_cases if c["success"]) / len(similar_cases)
        recommendation = f"На основе {len(similar_cases)} похожих кейсов: средняя компенсация {avg_compensation:.0f}₽, успешность {success_rate:.0%}"
    else:
        recommendation = "Похожих кейсов не найдено. Рекомендуется стандартный подход."
    
    return {
        "status": "success",
        "found_cases": len(similar_cases),
        "similar_cases": similar_cases[:limit],
        "recommendation": recommendation,
        "search_query": issue_description[:100],
        "filters_applied": {"rating": rating} if rating else {},
    }


# =============================================================================
# Tool 5: Get Case Details (воспоминания о кейсе)
# =============================================================================


@tool
@handle_tool_errors
def get_case_details(
    case_id: str,
) -> dict:
    """Получить полную информацию (воспоминания) о текущем кейсе.
    
    Используй этот инструмент ПЕРВЫМ при начале работы с кейсом!
    
    Возвращает:
    - Информацию об отзыве (если есть)
    - Историю чата с клиентом
    - Предыдущие действия агента
    - Данные о заказе и товаре
    - Результаты анализа из Analysis node — поле "analysis"
    
    ВАЖНО про анализ:
    - Поле "analysis" всегда заполнено, так как Analysis node запускается первым
    - Анализ обновляется при каждом запуске графа (новый триггер)
    - Анализ помнит о предыдущих анализах и всей истории кейса
    
    Args:
        case_id: ID кейса

    Returns:
        dict с полной информацией о кейсе включая результаты анализа
    """
    if not case_id:
        raise ToolError("case_id обязателен", recoverable=True)
    
    logger.info(f"[TOOL] get_case_details: {case_id}")
    
    # TODO: Implement actual database/API call to fetch case history
    # This should retrieve from state/database:
    # - Review data (if exists)
    # - Chat history
    # - Previous agent actions
    # - Order details
    # - Saved analysis results from state.analysis
    
    # Placeholder response - в реальности данные берутся из state и БД
    # Поле analysis будет заполнено если ранее вызывался request_analysis
    return {
        "status": "success",
        "case_id": case_id,
        
        # Review info (if exists)
        "review": {
            "exists": True,
            "rating": 2,
            "text": "Товар пришёл с браком",
            "pros": "",
            "cons": "Царапины на корпусе, не включается",
            "date": "2024-01-18",
            "our_reply": None,
        },
        
        # Order info
        "order": {
            "order_id": "WB-123456",
            "order_date": "2024-01-15",
            "delivery_date": "2024-01-17",
            "product_name": "Смартфон Samsung Galaxy",
            "price": 25000,
            "return_eligible": True,
        },
        
        # Chat history
        "chat_history": [
            {"role": "customer", "message": "Здравствуйте, товар бракованный", "timestamp": "2024-01-18T10:00:00"},
            {"role": "agent", "message": "Добрый день! Приносим извинения. Можете описать проблему подробнее?", "timestamp": "2024-01-18T10:05:00"},
        ],
        
        # Previous actions by agent
        "previous_actions": [
            {"action": "chat_message", "status": "sent", "timestamp": "2024-01-18T10:05:00"},
        ],
        
        # Saved analysis from state (всегда заполнено, так как Analysis первая нода)
        # Анализ обновляется при каждом запуске графа
        "analysis": None,  # будет dict с результатами анализа из Analysis node
        
        # Case metadata
        "created_at": "2024-01-18T10:00:00",
        "last_activity": "2024-01-18T10:05:00",
        "status": "in_progress",
        "customer_name": "Иван",
    }


# =============================================================================
# =============================================================================
# Tool Registry for Agent
# =============================================================================


# All tools available to the agent
# Agent decides which tools to use based on the situation
AGENT_TOOLS = [
    send_chat_message,
    send_review_reply,
    call_the_human,
    search_similar_cases,
    get_case_details,
]

def get_agent_tools() -> list:
    """Get all tools available to the 5STARS agent.
    
    All tools are always available. Agent decides which to use based on context.
    
    Returns:
        list of LangChain tools
    """
    logger.info(f"[get_agent_tools] Loaded {len(AGENT_TOOLS)} tools")
    return AGENT_TOOLS


def get_tool_error_handler(error: Exception) -> str:
    """Handle tool errors gracefully.
    
    This function is used with ToolNode's handle_tool_errors parameter.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Error message for the LLM to process
    """
    if isinstance(error, ToolError):
        if error.recoverable:
            return (
                f"Ошибка инструмента: {str(error)}. "
                "Попробуйте изменить параметры или выбрать другой подход."
            )
        else:
            return (
                f"Критическая ошибка: {str(error)}. "
                "Рекомендуется эскалировать на менеджера."
            )
    
    return (
        f"Непредвиденная ошибка: {str(error)}. "
        "Попробуйте другой подход или эскалируйте на менеджера."
    )
