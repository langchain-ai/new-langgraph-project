from src.db.mongodb_client import get_database
from src.models.product_catalog import ProductPrice

from typing import Any

COLLECTION_NAME = "product_price"

class ProductPriceRepository:
    @staticmethod
    async def upsert_price(price: ProductPrice) -> Any:
        db = get_database()
        data = price.model_dump(by_alias=True, exclude_none=True)
        result = await db[COLLECTION_NAME].update_one(
            {"id": price.id},
            {"$set": data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_price_by_id(id: str) -> ProductPrice | None:
        db = get_database()
        doc = await db[COLLECTION_NAME].find_one({"id": id})
        if doc:
            return ProductPrice.model_validate(doc)
        return None

    @staticmethod
    async def list_prices() -> list[ProductPrice]:
        db = get_database()
        cursor = db[COLLECTION_NAME].find()
        prices = []
        async for doc in cursor:
            prices.append(ProductPrice.model_validate(doc))
        return prices

    @staticmethod
    async def filter_prices(filter_dict: dict) -> list[ProductPrice]:
        """
        Filter product prices by arbitrary MongoDB query dict.
        Example: {"priceType": "recurring"}
        """
        db = get_database()
        cursor = db[COLLECTION_NAME].find(filter_dict)
        results = []
        async for doc in cursor:
            results.append(ProductPrice.model_validate(doc))
        return results
