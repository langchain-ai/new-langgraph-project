"""Tools for 5STARS agent.

Defines all tools that the agent can use to interact with external systems.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger("5stars.tools")


# =============================================================================
# Tool 1: Send Chat Message
# =============================================================================


@tool
def send_chat_message(
    chat_id: str,
    message: str,
) -> dict:
    """Отправить личное сообщение клиенту в чате Wildberries.
    
    Используй этот инструмент когда нужно:
    - Уточнить детали проблемы у клиента
    - Предложить решение или компенсацию приватно
    - Продолжить диалог с клиентом
    
    Args:
        chat_id: ID чата в Wildberries
        message: Текст сообщения (макс. 1000 символов)

    Returns:
        dict с статусом отправки
    """
    logger.info(f"[TOOL] send_chat_message to chat {chat_id}: {message[:50]}...")

    # TODO: Implement actual WB API call
    # response = requests.post(
    #     f"{WB_API_URL}/chats/{chat_id}/messages",
    #     json={"message": message},
    #     headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    # )
    
    return {
        "status": "success",
        "message": "Сообщение отправлено в чат",
        "chat_id": chat_id,
        "message_preview": message[:100],
    }


# =============================================================================
# Tool 2: Send Public Review Reply
# =============================================================================


@tool
def send_review_reply(
    review_id: str,
    reply_text: str,
) -> dict:
    """Отправить публичный ответ на отзыв Wildberries.
    
    Используй этот инструмент когда нужно:
    - Публично ответить на отзыв клиента
    - Показать другим покупателям, что продавец заботится о клиентах
    - Дать официальный ответ от имени магазина
    
    ВАЖНО: Ответ будет виден всем! Максимум 300 символов.
    Не указывай конкретные суммы компенсаций публично.
    
    Args:
        review_id: ID отзыва в Wildberries
        reply_text: Текст публичного ответа (макс. 300 символов)

    Returns:
        dict с статусом отправки
    """
    # Truncate if too long
    if len(reply_text) > 300:
        reply_text = reply_text[:297] + "..."
        
    logger.info(f"[TOOL] send_review_reply to review {review_id}: {reply_text[:50]}...")

    # TODO: Implement actual WB API call
    # response = requests.post(
    #     f"{WB_API_URL}/reviews/{review_id}/reply",
    #     json={"text": reply_text},
    #     headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    # )
    
    return {
        "status": "success",
        "message": "Публичный ответ на отзыв опубликован",
        "review_id": review_id,
        "reply_preview": reply_text[:100],
    }


# =============================================================================
# Tool 3: Escalate to Manager
# =============================================================================


@tool
def escalate_to_manager(
    case_id: str,
    reason: str,
    urgency: str = "normal",
    summary: str = "",
) -> dict:
    """Эскалировать кейс на менеджера для ручной обработки.
    
    Используй этот инструмент когда:
    - Клиент требует связи с руководством
    - Ситуация слишком сложная для автоматического решения
    - Есть юридические риски или угрозы
    - Клиент недоволен после нескольких попыток решения
    - Требуется компенсация более 1000₽
    
    Args:
        case_id: ID кейса
        reason: Причина эскалации (кратко)
        urgency: Срочность - "low", "normal", "high", "critical"
        summary: Краткое резюме ситуации для менеджера

    Returns:
        dict с информацией об эскалации
    """
    logger.warning(f"[TOOL] ESCALATION case_id={case_id}, reason={reason}, urgency={urgency}")

    # TODO: Implement actual escalation logic
    # - Create task in manager dashboard
    # - Send Telegram notification
    # - Update case status in DB
    
    return {
        "status": "escalated",
        "message": f"Кейс передан менеджеру. Срочность: {urgency}",
        "case_id": case_id,
        "reason": reason,
        "assigned_manager": "manager_on_duty",
    }


# =============================================================================
# Tool 4: Search Similar Cases
# =============================================================================


@tool
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
    
    Args:
        issue_description: Описание проблемы для поиска
        rating: Фильтр по рейтингу отзыва (1-5)
        limit: Максимальное количество результатов

    Returns:
        dict со списком похожих кейсов и их решений
    """
    logger.info(f"[TOOL] search_similar_cases: {issue_description[:50]}...")

    # TODO: Implement actual vector search in Milvus/PostgreSQL
    # - Create embedding from issue_description
    # - Search in vector DB
    # - Return similar cases with resolutions
    
    # Placeholder response
    similar_cases = [
        {
            "case_id": "case_001",
            "issue": "Товар пришёл с браком",
            "rating": 2,
            "resolution": "Предложена замена товара или возврат средств",
            "compensation": 500,
            "outcome": "Клиент изменил оценку на 5 звёзд",
            "success": True,
        },
        {
            "case_id": "case_002", 
            "issue": "Долгая доставка",
            "rating": 3,
            "resolution": "Извинения + промокод на следующую покупку",
            "compensation": 200,
            "outcome": "Клиент удовлетворён",
            "success": True,
        },
    ]
    
    return {
        "status": "success",
        "found_cases": len(similar_cases),
        "similar_cases": similar_cases[:limit],
        "recommendation": "На основе похожих кейсов рекомендуется предложить компенсацию 300-500₽",
    }


# =============================================================================
# Tool Registry for Agent
# =============================================================================


# List of all tools available to the agent
AGENT_TOOLS = [
    send_chat_message,
    send_review_reply,
    escalate_to_manager,
    search_similar_cases,
]


def get_agent_tools() -> list:
    """Get all tools available to the 5STARS agent.
    
    Returns:
        list of LangChain tools
    """
    return AGENT_TOOLS
