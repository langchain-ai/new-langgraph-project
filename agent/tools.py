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
                "suggestion": "Попробуй изменить параметры или выбрать другой подход",
            }
        except Exception as e:
            logger.exception(f"[TOOL UNEXPECTED ERROR] {func.__name__}: {e}")
            return {
                "status": "error",
                "error": f"Неожиданная ошибка: {str(e)}",
                "recoverable": False,
                "suggestion": "Рассмотри вызов менеджера для ручного решения",
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
    - Предложить решение или компенсацию
    - Продолжить диалог с клиентом
    
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
    
    Используй этот инструмент когда:
    - Клиент выполнил условия и исправил отзыв, проблема решена
    - Клиент оставил отзыв 5 звезд, позитив
    - Нужно завершить кейс и отправить публичный ответ
    
    ВАЖНО:
    - НЕ указывай наличие компенсаций или суммы в публичном ответе
    - МЯГКО отрицай негатив и предлагай связаться в чате для деталей
    
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
    prohibited_patterns = ["₽", "руб", "компенсац", "деньги"]
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
        "message": "Публичный ответ на отзыв отправлен",
        "action_type": "review_reply",
        "review_id": review_id,
        "reply_text": reply_text[:100],
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Tool 3: Call the Manager (передача кейса менеджеру)
# =============================================================================


@tool
@handle_tool_errors
def call_the_manager(
    case_id: str,
    reason: str,
    action_required: str = "escalation",
    compensation_amount: int = 0,
    summary: str = "",
) -> dict:
    """Передать кейс менеджеру для дальнейшей обработки.
    
    Используй этот инструмент когда:
    - Клиент согласился на компенсацию, чтобы менеджер выплатил
    - Ситуация слишком сложная для автоматического решения
    - Клиент требует связи с руководством (человеком)
    - Обнаружены конкретные юридические риски или угрозы
    - Клиент очень недоволен после нескольких попыток решения
    
    Args:
        case_id: ID кейса
        reason: Причина передачи менеджеру
        action_required: Требуемое действие ("compensation" - выплата или "escalation" - эскалация)
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
# Tool 4: Confirm WB Return
# =============================================================================


@tool
@handle_tool_errors
def confirm_wb_return(
    order_id: str,
    reason: str = "Договоренность с клиентом",
    notes: str = "",
) -> dict:
    """Подтвердить возможность возврата товара клиенту в Wildberries.
    
    Используй этот инструмент когда:
    - Клиент выполнил условия договоренности (исправил отзыв, добавил положительный)
    - В чате достигнута договоренность о возврате товара
    - Клиент запросил возврат после решения проблемы
    - Нужно одобрить возврат, чтобы клиент мог оставить заявку в ЛК WB
    
    ВАЖНО:
    - Используй только после достижения договоренности с клиентом
    - После вызова инструмента можно сообщать клиенту об одобрении возврата
    - Клиент сможет оформить заявку на возврат в своем личном кабинете WB
    
    Args:
        order_id: ID заказа в Wildberries
        reason: Причина подтверждения возврата
        notes: Дополнительные заметки для внутреннего использования

    Returns:
        dict с информацией о подтверждении возврата
    """
    # Validation
    if not order_id:
        raise ToolError("order_id обязателен", recoverable=True)
    
    if not reason or len(reason.strip()) < 5:
        raise ToolError(
            "Укажите причину подтверждения возврата (минимум 5 символов)",
            recoverable=True
        )
    
    reason = reason.strip()
    notes = notes.strip() if notes else ""
    
    logger.info(f"[TOOL] confirm_wb_return for order {order_id}: {reason[:50]}...")

    # TODO: Implement actual WB API call
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"{WB_API_URL}/returns/{order_id}/confirm",
    #         json={"reason": reason, "notes": notes},
    #         headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    #     )
    #     response.raise_for_status()
    
    return {
        "status": "success",
        "message": "✅ Возврат подтвержден. Клиент может оформить заявку в ЛК Wildberries",
        "action_type": "return_confirmed",
        "order_id": order_id,
        "reason": reason,
        "notes": notes,
        "return_window_days": 14,  # Placeholder: срок для оформления возврата
        "timestamp": datetime.now().isoformat(),
        "client_instruction": "Теперь вы можете оформить заявку на возврат в личном кабинете Wildberries в разделе 'Мои заказы'",
    }


# =============================================================================
# Tool 5: Search Internet
# =============================================================================


@tool
@handle_tool_errors
def search_internet(
    query: str,
    max_results: int = 3,
) -> dict:
    """Поиск информации в интернете для решения проблем клиентов.
    
    Используй этот инструмент когда:
    - Нужна актуальная информация о товаре или проблеме
    - Клиент задает вопрос, требующий специфических знаний
    - Нужно найти инструкции или решения проблем
    - Требуется проверить информацию о продукте
    
    ВАЖНО:
    - Используй конкретные поисковые запросы
    - Результаты помогут дать более точный ответ клиенту
    - Не передавай клиенту ссылки, используй найденную информацию для формирования ответа
    
    Args:
        query: Поисковый запрос (чем конкретнее, тем лучше)
        max_results: Максимальное количество результатов (1-10)

    Returns:
        dict с результатами поиска
    """
    # Validation
    if not query or len(query.strip()) < 3:
        raise ToolError(
            "Укажите поисковый запрос (минимум 3 символа)",
            recoverable=True
        )
    
    max_results = max(1, min(10, max_results))
    query = query.strip()
    
    logger.info(f"[TOOL] search_internet: {query[:50]}...")

    # TODO: Implement actual internet search (e.g., using Tavily, SerpAPI, or similar)
    # from tavily import TavilyClient
    # client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    # response = client.search(query, max_results=max_results)
    
    # Placeholder response with realistic data structure
    search_results = [
        {
            "title": "Как правильно стирать изделия из хлопка",
            "url": "https://example.com/wash-cotton",
            "snippet": "Хлопковые изделия рекомендуется стирать при температуре не выше 40°C. Используйте мягкие моющие средства без отбеливателя. Сушите в естественных условиях.",
            "relevance_score": 0.95,
        },
        {
            "title": "Уход за одеждой: полное руководство",
            "url": "https://example.com/clothing-care",
            "snippet": "Перед стиркой проверяйте этикетки с инструкциями. Разделяйте белое и цветное белье. Деликатные ткани стирайте отдельно.",
            "relevance_score": 0.87,
        },
        {
            "title": "Проблемы после стирки: как избежать",
            "url": "https://example.com/washing-problems",
            "snippet": "Если изделие село после стирки, возможно была превышена температура. Следуйте рекомендациям производителя для каждого типа ткани.",
            "relevance_score": 0.82,
        },
    ]
    
    # Filter results based on max_results
    search_results = search_results[:max_results]
    
    # Format summary
    summary = " ".join([r["snippet"] for r in search_results])
    
    return {
        "status": "success",
        "query": query,
        "results_count": len(search_results),
        "search_results": search_results,
        "summary": summary[:500],  # Краткая сводка для быстрого анализа
        "timestamp": datetime.now().isoformat(),
        "suggestion": "Используй найденную информацию для формирования более точного ответа клиенту",
    }


# =============================================================================
# Tool 6: Send Instruction
# =============================================================================


@tool
@handle_tool_errors
def send_instruction(
    chat_id: str,
    instruction_type: str,
    additional_message: str = "",
) -> dict:
    """Отправить инструкцию (изображение) клиенту в чат.
    
    Используй этот инструмент когда:
    - Нужно показать клиенту, как изменить отзыв
    - Требуется инструкция по оформлению возврата
    - Клиент не понимает, как выполнить действие
    - После подтверждения возврата нужно показать шаги
    
    Доступные типы инструкций:
    - "change_review" - Как изменить отзыв на WB
    - "return_process" - Как оформить возврат в ЛК WB
    - "add_review" - Как добавить новый отзыв
    - "contact_support" - Как связаться с поддержкой WB
    
    Args:
        chat_id: ID чата в Wildberries
        instruction_type: Тип инструкции (см. список выше)
        additional_message: Дополнительное текстовое сообщение к инструкции

    Returns:
        dict с информацией об отправке инструкции
    """
    # Validation
    if not chat_id:
        raise ToolError("chat_id обязателен", recoverable=True)
    
    valid_instruction_types = [
        "change_review",
        "return_process",
        "add_review",
        "contact_support"
    ]
    
    if instruction_type not in valid_instruction_types:
        raise ToolError(
            f"Неверный тип инструкции. Доступные: {', '.join(valid_instruction_types)}",
            recoverable=True,
            details={"valid_types": valid_instruction_types}
        )
    
    additional_message = additional_message.strip() if additional_message else ""
    
    logger.info(f"[TOOL] send_instruction to chat {chat_id}: type={instruction_type}")

    # TODO: Implement actual file sending through WB API
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     # Get instruction image from storage
    #     instruction_file = get_instruction_image(instruction_type)
    #     
    #     # Upload file to WB
    #     response = await client.post(
    #         f"{WB_API_URL}/chats/{chat_id}/files",
    #         files={"file": instruction_file},
    #         data={"message": additional_message},
    #         headers={"Authorization": f"Bearer {WB_API_TOKEN}"}
    #     )
    #     response.raise_for_status()
    
    # Map instruction types to file names (for future implementation)
    instruction_files = {
        "change_review": "instructions/how_to_change_review.png",
        "return_process": "instructions/how_to_return.png",
        "add_review": "instructions/how_to_add_review.png",
        "contact_support": "instructions/how_to_contact_support.png",
    }
    
    instruction_titles = {
        "change_review": "Как изменить отзыв на Wildberries",
        "return_process": "Как оформить возврат товара",
        "add_review": "Как добавить новый отзыв",
        "contact_support": "Как связаться с поддержкой Wildberries",
    }
    
    return {
        "status": "success",
        "message": "✅ Инструкция отправлена в чат",
        "action_type": "instruction_sent",
        "chat_id": chat_id,
        "instruction_type": instruction_type,
        "instruction_title": instruction_titles[instruction_type],
        "file_path": instruction_files[instruction_type],
        "additional_message": additional_message,
        "timestamp": datetime.now().isoformat(),
        "next_step": "Дождись подтверждения от клиента, что инструкция понятна",
    }


# =============================================================================
# Tool 7: Search Similar Cases
# =============================================================================


@tool
@handle_tool_errors
def search_similar_cases(
    issue_description: str,
    rating: Optional[int] = None,
    limit: int = 3,
) -> dict:
    """Найти похожие кейсы из истории.
    
    Используй этот инструмент когда:
    - Нужно понять, как решались похожие проблемы ранее
    - Ищешь оптимальную стратегию ответа
    - Сомневаешься в правильности подхода
    
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
        recommendation = "Похожих кейсов не найдено. Продолжай с базовой стратегией."
    
    return {
        "status": "success",
        "found_cases": len(similar_cases),
        "similar_cases": similar_cases[:limit],
        "recommendation": recommendation,
        "search_query": issue_description[:100],
        "filters_applied": {"rating": rating} if rating else {},
    }


# =============================================================================
# Tool Registry for Agent
# =============================================================================


# All tools available to the agent
# Agent decides which tools to use based on the situation
AGENT_TOOLS = [
    send_chat_message,
    send_review_reply,
    confirm_wb_return,
    send_instruction,
    search_internet,
    call_the_manager,
    search_similar_cases,
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
                "Рассмотри вызов менеджера для ручного решения."
            )
    
    return (
        f"Непредвиденная ошибка: {str(error)}. "
        "Попробуйте другой подход или рассмотри вызов менеджера для ручного решения."
    )
