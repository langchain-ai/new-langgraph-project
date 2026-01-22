"""Example usage of 5STARS agent.

Demonstrates how to use the agent for processing Wildberries reviews.
"""

import asyncio
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def example_process_new_review():
    """Example: Process a new negative review."""
    from agent import CaseStage, process_case

    print("=" * 60)
    print("Example 1: Processing a new negative review")
    print("=" * 60)

    result = await process_case(
        case_id=1001,
        review_text="""
        Очень разочарован покупкой! Заказал кроссовки 43 размера,
        пришли маломерки, даже 44 размер был бы мал. Качество тоже
        оставляет желать лучшего - подошва уже начала отклеиваться.
        Не рекомендую данный товар!
        """,
        rating=1,
        chat_id="wb_chat_12345",
        customer_name="Алексей",
    )

    print(f"\nCase ID: {result.get('case_id')}")
    print(f"Next Stage: {result.get('next_stage')}")
    print(f"Strategy: {result.get('strategy')}")
    print(f"Should Escalate: {result.get('should_escalate')}")
    print(f"AI Response: {result.get('ai_response', 'N/A')[:200]}...")
    print(f"Actions: {result.get('actions')}")


async def example_process_medium_review():
    """Example: Process a medium rating review."""
    from agent import process_case

    print("\n" + "=" * 60)
    print("Example 2: Processing a medium rating review")
    print("=" * 60)

    result = await process_case(
        case_id=1002,
        review_text="""
        В целом товар нормальный, но есть нюансы. Цвет немного
        отличается от фото на сайте - более блеклый. За эту цену
        ожидал лучшего качества упаковки. Доставка быстрая.
        """,
        rating=3,
        chat_id="wb_chat_67890",
        customer_name="Мария",
    )

    print(f"\nCase ID: {result.get('case_id')}")
    print(f"Next Stage: {result.get('next_stage')}")
    print(f"Strategy: {result.get('strategy')}")
    print(f"Review Analysis: {result.get('review_context')}")
    print(f"AI Response: {result.get('ai_response', 'N/A')[:200]}...")


async def example_process_with_context():
    """Example: Process review with full context."""
    from agent import CaseStage, process_case

    print("\n" + "=" * 60)
    print("Example 3: Processing with full context")
    print("=" * 60)

    result = await process_case(
        case_id=1003,
        review_text="Товар бракованный, пуговицы отвалились после первой стирки!",
        rating=2,
        chat_id="wb_chat_11111",
        customer_name="Елена",
        # Additional context
        product_context={
            "product_id": "prod_555",
            "product_name": "Блузка женская",
            "category": "Одежда",
            "price": 1500.0,
            "seller_id": "seller_777",
        },
        customer_context={
            "customer_id": "cust_999",
            "customer_name": "Елена",
            "total_orders": 15,
            "total_reviews": 8,
            "average_rating": 4.5,
        },
    )

    print(f"\nCase ID: {result.get('case_id')}")
    print(f"Review Context: {result.get('review_context')}")
    print(f"AI Response: {result.get('ai_response', 'N/A')}")
    print(f"Execution Results: {result.get('execution_results')}")


async def example_continue_dialog():
    """Example: Continue dialog with customer response."""
    from agent import CaseStage, process_case, process_message

    print("\n" + "=" * 60)
    print("Example 4: Continuing dialog after customer response")
    print("=" * 60)

    # First, process initial review
    initial_result = await process_case(
        case_id=1004,
        review_text="Размер не подошёл, хочу вернуть товар.",
        rating=2,
        chat_id="wb_chat_22222",
        customer_name="Дмитрий",
    )

    print(f"Initial AI Response: {initial_result.get('ai_response', 'N/A')[:150]}...")

    # Customer responds
    updated_result = await process_message(
        case_id=1004,
        message="А можно просто обмен на другой размер сделать?",
        current_state=initial_result,
    )

    print(f"\nAfter customer response:")
    print(f"New AI Response: {updated_result.get('ai_response', 'N/A')[:200]}...")


async def main():
    """Run all examples."""
    # Check for required environment variables
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY not set. Examples may fail.")
        print("Please set it in .env file or environment.")
        return

    try:
        await example_process_new_review()
        await example_process_medium_review()
        await example_process_with_context()
        await example_continue_dialog()

    except Exception as e:
        print(f"\nError running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
