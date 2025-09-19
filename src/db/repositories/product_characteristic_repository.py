from src.db.mongodb_client import get_database
from src.models.product_catalog import ProductCharacteristic

from typing import Any

COLLECTION_NAME = "product_characteristic"

class ProductCharacteristicRepository:
    @staticmethod
    async def upsert_characteristic(char: ProductCharacteristic) -> Any:
        db = get_database()
        data = char.model_dump(by_alias=True, exclude_none=True)
        result = await db[COLLECTION_NAME].update_one(
            {"id": char.id},
            {"$set": data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_characteristic_by_id(id: str) -> ProductCharacteristic | None:
        db = get_database()
        doc = await db[COLLECTION_NAME].find_one({"id": id})
        if doc:
            return ProductCharacteristic.model_validate(doc)
        return None

    @staticmethod
    async def list_characteristics() -> list[ProductCharacteristic]:
        db = get_database()
        cursor = db[COLLECTION_NAME].find()
        chars = []
        async for doc in cursor:
            chars.append(ProductCharacteristic.model_validate(doc))
        return chars

    @staticmethod
    async def filter_characteristics(filter_dict: dict) -> list[ProductCharacteristic]:
        """
        Filter product characteristics by arbitrary MongoDB query dict.
        Example: {"isBundle": True, "name": "foo"}
        """
        db = get_database()
        cursor = db[COLLECTION_NAME].find(filter_dict)
        results = []
        async for doc in cursor:
            results.append(ProductCharacteristic.model_validate(doc))
        return results
